"""Self-hosted photo lane (operator decision 2026-09-26, option b):
upload store, temporary public link expiry, loopback photo host, board route.
"""

from __future__ import annotations

import http.client
import io
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from clawteam.media import uploads as uploads_mod
from clawteam.media.uploads import UploadStore, TOKEN_RE
from clawteam.media.photohost import make_server

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-payload" * 16
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"fake-jpeg" * 16


def write_config(data_dir, *, public_origin="https://photos.example.com",
                 port=0, ttl_hours=24.0):
    cfg = {"public_origin": public_origin, "port": port, "ttl_hours": ttl_hours}
    d = data_dir / "media"
    d.mkdir(parents=True, exist_ok=True)
    (d / "photohost.json").write_text(json.dumps(cfg), encoding="utf-8")
    return cfg


class TestUploadStore:
    def test_save_and_read_roundtrip(self, isolated_data_dir):
        write_config(isolated_data_dir)
        rec = UploadStore().save(PNG_BYTES, ext=".png", original_name="me.png")
        assert TOKEN_RE.fullmatch(rec["token"])
        assert rec["url"] == f"https://photos.example.com/{rec['token']}.png"
        assert rec["mime"] == "image/png"
        assert rec["bytes"] == len(PNG_BYTES)
        assert rec["original_name"] == "me.png"
        assert rec["expires_at"]
        hit = UploadStore().read_bytes(rec["token"])
        assert hit is not None and hit[1] == PNG_BYTES
        assert (uploads_mod.uploads_dir() / f"{rec['token']}.png").is_file()
        assert (uploads_mod.uploads_dir() / f"{rec['token']}.json").is_file()

    def test_content_must_match_extension(self, isolated_data_dir):
        write_config(isolated_data_dir)
        with pytest.raises(ValueError, match="match"):
            UploadStore().save(JPEG_BYTES, ext=".png")

    def test_bad_extension_rejected(self, isolated_data_dir):
        write_config(isolated_data_dir)
        with pytest.raises(ValueError, match="unsupported"):
            UploadStore().save(PNG_BYTES, ext=".gif")

    def test_size_cap(self, isolated_data_dir, monkeypatch):
        write_config(isolated_data_dir)
        monkeypatch.setattr(uploads_mod, "MAX_UPLOAD_BYTES", 8)
        with pytest.raises(ValueError, match="cap"):
            UploadStore().save(PNG_BYTES, ext=".png")

    def test_expired_link_fails_closed_and_sweeps(self, isolated_data_dir):
        write_config(isolated_data_dir)
        store = UploadStore(ttl_hours=0.0)  # expires immediately
        expired = store.save(PNG_BYTES, ext=".png")
        live = UploadStore().save(JPEG_BYTES, ext=".jpg")
        assert store.get(expired["token"]) is None
        assert store.expired(expired["token"]) is True
        assert store.expired(live["token"]) is False
        assert store.sweep() == 1
        assert not (uploads_mod.uploads_dir() / f"{expired['token']}.png").exists()
        assert (uploads_mod.uploads_dir() / f"{live['token']}.jpg").is_file()

    def test_no_origin_configured_gives_no_public_url(self, isolated_data_dir):
        write_config(isolated_data_dir, public_origin="")
        rec = UploadStore().save(PNG_BYTES, ext=".png")
        assert rec["url"] is None
        assert rec["local_url"].startswith("/api/media/uploads/")

    def test_token_validation_blocks_traversal(self, isolated_data_dir):
        write_config(isolated_data_dir)
        store = UploadStore()
        assert store.get("../etc/passwd") is None
        assert store.get("") is None
        assert store.read_bytes("pho-short") is None
        assert store.file_path("pho-9999999999-deadbeef/../../x") is None
        assert store.get("pho-9999999999-..\\evil") is None


@pytest.fixture()
def photo_server(isolated_data_dir):
    write_config(isolated_data_dir)
    uploads = UploadStore()
    server = make_server("127.0.0.1", 0, uploads)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server, uploads
    server.shutdown()
    server.server_close()


class TestPhotoHost:
    @staticmethod
    def _fetch(server, path):
        port = server.server_address[1]
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    @staticmethod
    def _raw_request(server, path):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        return resp.status, body

    def test_serves_live_upload(self, photo_server):
        server, uploads = photo_server
        rec = uploads.save(PNG_BYTES, ext=".png")
        port = server.server_address[1]
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/{rec['token']}.png", timeout=5) as r:
            assert r.status == 200 and r.read() == PNG_BYTES
            # expiry must cut off new fetches: never cache at the edge
            assert r.headers["Cache-Control"] == "no-store"

    def test_serves_webp_with_correct_mime(self, photo_server):
        server, uploads = photo_server
        webp = b"RIFF\x00\x00\x00\x00WEBP" + b"fake-webp" * 8
        rec = uploads.save(webp, ext=".webp")
        port = server.server_address[1]
        with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/{rec['token']}.webp", timeout=5) as r:
            assert r.status == 200
            assert r.headers["Content-Type"] == "image/webp"

    def test_unknown_token_is_404(self, photo_server):
        server, _ = photo_server
        status, _ = self._fetch(server, "/pho-9999999999-000000000000.png")
        assert status == 404

    def test_expired_token_is_410(self, photo_server):
        server, _ = photo_server
        expired_store = UploadStore(ttl_hours=0.0)
        rec = expired_store.save(PNG_BYTES, ext=".png")
        status, _ = self._fetch(server, f"/{rec['token']}.png")
        assert status == 410

    def test_traversal_and_nested_paths_rejected(self, photo_server):
        server, _ = photo_server
        assert self._raw_request(server, "/..%2f..%2fsecret.png")[0] == 400
        assert self._raw_request(server, "/sub/pho-9999999999-000000000000.png")[0] == 400

    def test_non_image_extension_404(self, photo_server):
        server, uploads = photo_server
        rec = uploads.save(PNG_BYTES, ext=".png")
        status, _ = self._fetch(server, f"/{rec['token']}.exe")
        assert status == 404
        status, _ = self._fetch(server, "/")
        assert status == 404


class TestBoardUploadRoute:
    @staticmethod
    def _handler(path, body, filename=None):
        from clawteam.board.server import BoardHandler
        handler = object.__new__(BoardHandler)
        served = {}
        handler._serve_json = lambda data: served.setdefault("data", data)
        handler.path = path + (f"?filename={filename}" if filename else "")
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        return handler, served

    def test_post_upload_saves_and_returns_public_url(self, isolated_data_dir):
        write_config(isolated_data_dir)
        handler, served = self._handler("/api/media/uploads", PNG_BYTES, "photo.png")
        handler.do_POST()
        assert served["data"]["status"] == "ok"
        up = served["data"]["upload"]
        assert up["url"].startswith("https://photos.example.com/pho-")
        assert UploadStore().read_bytes(up["token"])[1] == PNG_BYTES

    def test_post_upload_rejects_non_image_name(self, isolated_data_dir):
        write_config(isolated_data_dir)
        handler, served = self._handler("/api/media/uploads", b"binary", "evil.exe")
        handler.do_POST()
        assert served["data"]["status"] == "error"
        assert "unsupported" in served["data"]["error"]

    def test_post_upload_rejects_mislabeled_content(self, isolated_data_dir):
        write_config(isolated_data_dir)
        handler, served = self._handler("/api/media/uploads", JPEG_BYTES, "photo.png")
        handler.do_POST()
        assert served["data"]["status"] == "error"
        assert "match" in served["data"]["error"]

    def test_post_upload_without_origin_reports_error(self, isolated_data_dir):
        write_config(isolated_data_dir, public_origin="")
        handler, served = self._handler("/api/media/uploads", PNG_BYTES, "photo.png")
        handler.do_POST()
        assert served["data"]["status"] == "error"
        assert "public origin" in served["data"]["error"]

    def test_get_lists_live_uploads(self, isolated_data_dir):
        write_config(isolated_data_dir)
        from clawteam.board.server import BoardHandler
        store = UploadStore()
        store.save(PNG_BYTES, ext=".png")
        handler = object.__new__(BoardHandler)
        served = {}
        handler._serve_json = lambda data: served.setdefault("data", data)
        handler.upload_store = store
        handler.path = "/api/media/uploads"
        handler.do_GET()
        assert len(served["data"]["uploads"]) == 1

    def test_get_local_file_serves_bytes(self, isolated_data_dir):
        write_config(isolated_data_dir)
        from clawteam.board.server import BoardHandler
        store = UploadStore()
        rec = store.save(PNG_BYTES, ext=".png")
        handler = object.__new__(BoardHandler)
        handler.upload_store = store
        handler.wfile = io.BytesIO()
        handler.send_response = lambda code: None
        handler.send_header = lambda name, value: None
        handler.end_headers = lambda: None
        errors = []
        handler.send_error = lambda code, msg="": errors.append(code)
        handler.path = f"/api/media/uploads/{rec['token']}/file"
        handler.do_GET()
        assert handler.wfile.getvalue() == PNG_BYTES
        assert not errors


class TestAnimateFromVariant:
    """i2v with variant_asset_id re-hosts the library asset through the photo
    lane (fresh self-hosted temp link) and labels the scene 'variant'."""

    class _FakeMediaRouter:
        def __init__(self, assets, jobs):
            self.assets = assets
            self.jobs = jobs

        def plan(self, job):
            return {"provider": "kie", "model": "runway",
                    "estimate": {"credits": 12.0, "usd": 0.06,
                                 "pricing_table_version": "t/1", "verified": False}}

    @staticmethod
    def _character_with_variant(tmp_path):
        from clawteam.media.characters import CharacterStore
        from clawteam.media.assets import AssetStore
        assets = AssetStore(tmp_path)
        rec = assets.save(PNG_BYTES, kind="image", ext=".png")
        cs = CharacterStore()
        char = cs.new(name="Maya", source_url="https://x/p.jpg")
        cs.attach_canonical(char["id"], asset_id="ast-c", url="https://x/canon.png")
        cs.add_variant(char["id"], asset_id=rec["id"], url="https://x/v.png",
                       prompt="red jacket")
        return cs, char["id"], rec["id"], assets

    @staticmethod
    def _post_jobs(handler, body):
        import json as _json
        raw = _json.dumps(body).encode("utf-8")
        handler.path = "/api/media/jobs"
        handler.headers = {"Content-Length": str(len(raw))}
        handler.rfile = io.BytesIO(raw)
        handler.do_POST()

    def test_post_i2v_variant_rehosts_through_photo_lane(self, isolated_data_dir, tmp_path):
        write_config(isolated_data_dir)
        from clawteam.board.server import BoardHandler
        from clawteam.media.jobs import MediaJobStore
        cs, cid, vaid, assets = self._character_with_variant(tmp_path)
        router = self._FakeMediaRouter(assets, MediaJobStore(tmp_path))
        handler = object.__new__(BoardHandler)
        served = {}
        handler._serve_json = lambda data: served.setdefault("data", data)
        handler.media_router = router
        self._post_jobs(handler, {"kind": "i2v", "prompt": "waves hello",
                                  "params": {"character_id": cid,
                                             "variant_asset_id": vaid,
                                             "duration": 5, "quality": "720p"}})
        assert served["data"]["status"] == "ok"
        params = served["data"]["job"]["params"]
        assert params["source_url"].startswith("https://photos.example.com/pho-")
        assert params["source"] == "variant"
        assert "variant_asset_id" not in params
        token = params["source_url"].rsplit("/", 1)[1].rsplit(".", 1)[0]
        assert UploadStore().read_bytes(token)[1] == PNG_BYTES

    def test_post_i2v_unknown_variant_rejected(self, isolated_data_dir, tmp_path):
        write_config(isolated_data_dir)
        from clawteam.board.server import BoardHandler
        from clawteam.media.jobs import MediaJobStore
        cs, cid, vaid, assets = self._character_with_variant(tmp_path)
        router = self._FakeMediaRouter(assets, MediaJobStore(tmp_path))
        handler = object.__new__(BoardHandler)
        served = {}
        handler._serve_json = lambda data: served.setdefault("data", data)
        handler.media_router = router
        self._post_jobs(handler, {"kind": "i2v", "prompt": "waves",
                                  "params": {"character_id": cid,
                                             "variant_asset_id": "ast-nope",
                                             "duration": 5, "quality": "720p"}})
        assert served["data"]["status"] == "error"
        assert "unknown variant" in served["data"]["error"]

    def test_i2v_scene_source_label_variant(self, isolated_data_dir, tmp_path):
        from clawteam.media.router import MediaRouter
        from clawteam.media.jobs import MediaJobStore
        from clawteam.media.assets import AssetStore
        from clawteam.media.characters import CharacterStore
        from clawteam.media.providers.base import ProviderResult as R
        cs = CharacterStore()
        char = cs.new(name="Maya", source_url="https://x/p.jpg")
        cs.attach_canonical(char["id"], asset_id="ast-c", url="https://x/canon.png")

        class FakeLocal:
            name = "comfyui-local"

            def health(self):
                return {"ok": False, "detail": "down", "gates": {}}

            def capabilities(self):
                return {"kinds": [], "models": [], "limits": {}}

        class FakeCloudI2V:
            name = "kie"

            def capabilities(self):
                return {"kinds": ["t2v", "i2v"],
                        "models": [{"model": "runway", "kinds": ["t2v", "i2v"]}],
                        "limits": {}, "dormant": False}

            def health(self):
                return {"ok": True, "detail": "live", "gates": {}}

            def estimate(self, kind, model, params):
                return {"credits": 12.0, "usd": 0.06, "pricing_table_version": "t/1",
                        "verified": False}

            def default_model_for(self, kind):
                return "runway"

            def submit(self, job, input_urls):
                assert input_urls == ["https://photos.example.com/pho-x.png"]
                return "task-i2v", "runway"

            def poll(self, task_id, kind):
                return R(state="succeeded", provider_status="success",
                         output_urls=["https://x/scene.mp4"], actual_credits=12.0)

            def download(self, url):
                return b"VID", ".mp4"

        r = MediaRouter(job_store=MediaJobStore(tmp_path), asset_store=AssetStore(tmp_path),
                        local=FakeLocal(), cloud=FakeCloudI2V())
        job = r.jobs.new_job("i2v", "she waves hello",
                             params={"character_id": char["id"],
                                     "source_url": "https://photos.example.com/pho-x.png",
                                     "source": "variant"})
        r.jobs.queue(job)
        r._tick()
        r._tick()
        r._tick()
        assert r.jobs.get(job["id"])["state"] == "succeeded"
        scenes = cs.get(char["id"])["scenes"]
        assert len(scenes) == 1
        assert scenes[0]["source"] == "variant"

    def test_i2v_scene_source_label_canonical_default(self, isolated_data_dir, tmp_path):
        from clawteam.media.router import MediaRouter
        from clawteam.media.jobs import MediaJobStore
        from clawteam.media.assets import AssetStore
        from clawteam.media.characters import CharacterStore
        from clawteam.media.providers.base import ProviderResult as R
        cs = CharacterStore()
        char = cs.new(name="Ana", source_url="https://x/p.jpg")
        cs.attach_canonical(char["id"], asset_id="ast-c", url="https://x/canon.png")

        class FakeCloudCanonical:
            name = "kie"

            def capabilities(self):
                return {"kinds": ["i2v"], "models": [{"model": "runway", "kinds": ["i2v"]}],
                        "limits": {}, "dormant": False}

            def health(self):
                return {"ok": True, "detail": "live", "gates": {}}

            def estimate(self, kind, model, params):
                return {"credits": 12.0, "usd": 0.06, "pricing_table_version": "t/1"}

            def default_model_for(self, kind):
                return "runway"

            def submit(self, job, input_urls):
                assert input_urls == ["https://x/canon.png"]
                return "task-i2v2", "runway"

            def poll(self, task_id, kind):
                return R(state="succeeded", provider_status="success",
                         output_urls=["https://x/scene2.mp4"], actual_credits=12.0)

            def download(self, url):
                return b"VID", ".mp4"

        class FakeLocalDown:
            name = "comfyui-local"

            def health(self):
                return {"ok": False, "detail": "down", "gates": {}}

            def capabilities(self):
                return {"kinds": [], "models": [], "limits": {}}

        r = MediaRouter(job_store=MediaJobStore(tmp_path), asset_store=AssetStore(tmp_path),
                        local=FakeLocalDown(), cloud=FakeCloudCanonical())
        job = r.jobs.new_job("i2v", "she smiles",
                             params={"character_id": char["id"]})
        r.jobs.queue(job)
        r._tick()
        r._tick()
        r._tick()
        assert r.jobs.get(job["id"])["state"] == "succeeded"
        scenes = cs.get(char["id"])["scenes"]
        assert len(scenes) == 1
        assert scenes[0]["source"] == "canonical"


class TestRouterSweepsExpiredUploads:
    class _StubProvider:
        name = "stub"

        def health(self):
            return {"ok": False, "detail": "stub", "gates": {}}

        def capabilities(self):
            return {"kinds": [], "models": [], "limits": {}}

    def test_worker_sweep_removes_expired(self, isolated_data_dir, tmp_path):
        from clawteam.media.router import MediaRouter
        from clawteam.media.jobs import MediaJobStore
        from clawteam.media.assets import AssetStore
        write_config(isolated_data_dir)
        expired = UploadStore(ttl_hours=0.0).save(PNG_BYTES, ext=".png")
        binary = uploads_mod.uploads_dir() / f"{expired['token']}.png"
        assert binary.is_file()
        stub = self._StubProvider()
        router = MediaRouter(job_store=MediaJobStore(tmp_path),
                             asset_store=AssetStore(tmp_path),
                             local=stub, cloud=self._StubProvider())
        router.start()
        try:
            deadline = time.time() + 4
            while time.time() < deadline and binary.exists():
                time.sleep(0.1)
        finally:
            router.stop()
        assert not binary.exists()
