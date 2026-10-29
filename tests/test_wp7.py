"""WP7 — 3D character pipeline: Fal provider, forensic QA, pipeline stages.

All HTTP is faked (no live calls, no spend). Adapter payloads are pinned to
the schemas fetched 2026-10-28 from fal.ai (E6). One live E2E with real
credits is the operator's morning test; it flips verified:false pricing.
"""

from __future__ import annotations

import json

import pytest

from clawteam.media.providers import fal as falmod
from clawteam.media.providers.openrouter_qa import QaError, vision_qa
from clawteam.media.threed import ThreeDPipeline
from clawteam.media.jobs import MediaJobStore, JOB_KINDS
from clawteam.media.router import MediaRouter, CLOUD_ONLY_KINDS


RUN = "threed-tests"


# ---------------------------------------------------------------------------
# Fal client + adapters (schema pins)
# ---------------------------------------------------------------------------


class TestFalClient:
    def test_submit_builds_key_auth_and_returns_ticket(self, monkeypatch):
        calls: list[tuple[str, str, dict | None]] = []

        def fake_call(method, url, payload=None, timeout=30):
            calls.append((method, url, payload))
            if method == "POST":
                return {"request_id": "rid-1",
                        "status_url": "https://queue.fal.run/x/requests/rid-1/status",
                        "response_url": "https://queue.fal.run/x/requests/rid-1"}
            if url.endswith("/status"):
                return {"status": "COMPLETED"}
            return {"model_mesh": {"url": "https://f/m.glb"}}

        client = falmod.FalClient(key="test-key-123")
        monkeypatch.setattr(client, "_call", fake_call)
        ticket = client.submit("tripo3d/h3.1/image-to-3d", {"image_url": "https://x/p.jpg"})
        assert ticket["request_id"] == "rid-1"
        assert calls[0][1] == "https://queue.fal.run/tripo3d/h3.1/image-to-3d"
        assert calls[0][2] == {"image_url": "https://x/p.jpg"}

    def test_call_sends_key_prefix_not_bearer(self, monkeypatch):
        import urllib.request
        captured: dict = {}

        class FakeResp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b'{"ok": true}'

        def fake_urlopen(req, timeout=None):
            captured["auth"] = req.headers.get("Authorization")
            captured["url"] = req.full_url
            return FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        client = falmod.FalClient(key="k-abc")
        client.status("https://queue.fal.run/x/requests/r/status")
        assert captured["auth"] == "Key k-abc"      # fal law: Key prefix, never Bearer

    def test_submit_rejects_ticket_missing_fields(self, monkeypatch):
        client = falmod.FalClient(key="k")
        monkeypatch.setattr(client, "_call", lambda *a, **kw: {"request_id": "x"})
        with pytest.raises(falmod.FalError, match="missing status_url"):
            client.submit("m", {})


class TestFalAdapters:
    def test_tripo_payload_pinned_schema(self):
        a = falmod.TripoImageTo3DAdapter()
        payload = a.build({"kind": "to3d", "params": {}}, ["https://x/p.jpg"])
        assert payload["image_url"] == "https://x/p.jpg"
        assert payload["texture_quality"] == "detailed"    # operator: highest quality
        assert payload["geometry_quality"] == "detailed"
        assert payload["pbr"] is True and payload["texture"] is True

    def test_tripo_parse_normalizes_model_urls(self):
        a = falmod.TripoImageTo3DAdapter()
        parsed = a.parse({
            "model_mesh": {"url": "https://f/mesh.glb"},
            "model_urls": {"glb": {"url": "https://f/m.glb"},
                           "pbr_model": {"url": "https://f/pbr.glb"}},
            "rendered_image": {"url": "https://f/preview.png"},
            "task_id": "task-77",
        })
        assert "https://f/mesh.glb" in parsed["urls"]
        assert parsed["previews"] == ["https://f/preview.png"]
        assert parsed["task_ids"]["tripo"] == "task-77"

    def test_meshy_rig_payload_pinned_schema(self):
        a = falmod.MeshyRiggingAdapter()
        payload = a.build({"kind": "rig3d", "params": {}}, ["https://f/m.glb"])
        assert payload["model_url"] == "https://f/m.glb"
        assert payload["enable_animation"] is True
        assert payload["animation_action_id"] == 92

    def test_rembg_payload(self):
        a = falmod.RembgAdapter()
        assert a.build({"kind": "prep3d", "params": {}}, ["https://x/p.png"]) == \
            {"image_url": "https://x/p.png"}

    def test_provider_dispatch_and_dormant_health(self):
        live = falmod.FalProvider(client=falmod.FalClient(key="k"))
        assert live.health()["ok"] is True
        assert live.default_model_for("to3d") == "tripo3d/h3.1/image-to-3d"
        assert live.default_model_for("rig3d") == "fal-ai/meshy/rigging"
        dormant = falmod.FalProvider(client=falmod.FalClient(key=""))
        assert dormant.health()["ok"] is False
        assert "dormant" in dormant.health()["detail"]

    def test_estimate_is_usd_and_unverified(self):
        p = falmod.FalProvider(client=falmod.FalClient(key="k"))
        est = p.estimate("to3d", "tripo3d/h3.1/image-to-3d", {})
        assert est["usd"] == 0.40 and est["verified"] is False


# ---------------------------------------------------------------------------
# Forensic QA (OpenRouter vision)
# ---------------------------------------------------------------------------


class TestVisionQa:
    def _patch_openrouter(self, monkeypatch, content):
        import urllib.request
        captured: dict = {}

        class FakeResp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self):
                return json.dumps({"choices": [{"message": {"content": content}}]}).encode()

        def fake_urlopen(req, timeout=None):
            captured["auth"] = req.headers.get("Authorization")
            captured["body"] = json.loads(req.data.decode())
            return FakeResp()

        monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
        monkeypatch.setenv("OPENROUTER_API_KEY", "or-test-key")
        return captured

    def test_verdict_parse_and_request_shape(self, monkeypatch):
        captured = self._patch_openrouter(
            monkeypatch, '{"pass": true, "issues": [], "severity": "none"}')
        out = vision_qa("https://x/src.jpg", "https://x/prev.png")
        assert out["pass"] is True and out["issues"] == []
        assert captured["auth"] == "Bearer or-test-key"
        assert captured["body"]["model"] == "google/gemini-2.5-pro"
        parts = captured["body"]["messages"][0]["content"]
        assert parts[1]["image_url"]["url"] == "https://x/src.jpg"
        assert parts[2]["image_url"]["url"] == "https://x/prev.png"

    def test_fenced_verdict_still_parses(self, monkeypatch):
        self._patch_openrouter(
            monkeypatch, '```json\n{"pass": false, "issues": ["left hand merged"], '
                         '"severity": "medium"}\n```')
        out = vision_qa("https://x/s.jpg", "https://x/p.png")
        assert out["pass"] is False and out["severity"] == "medium"

    def test_bad_verdict_raises(self, monkeypatch):
        self._patch_openrouter(monkeypatch, "I cannot answer that")
        with pytest.raises(QaError, match="unparseable"):
            vision_qa("https://x/s.jpg", "https://x/p.png")

    def test_dormant_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        with pytest.raises(QaError, match="dormant"):
            vision_qa("https://x/s.jpg", "https://x/p.png")


# ---------------------------------------------------------------------------
# Pipeline (fake provider, end to end)
# ---------------------------------------------------------------------------


class FakeFal:
    """Implements the FalProvider surface the pipeline touches."""

    name = "fal"

    def __init__(self, fail_generate=False, fail_rig=False, qa_pass=True):
        self.fail_generate = fail_generate
        self.fail_rig = fail_rig
        self.qa_pass = qa_pass
        self.submits: list[str] = []

    def health(self):
        return {"ok": True, "detail": "fake", "gates": {}}

    def capabilities(self):
        return {"kinds": ["prep3d", "to3d", "rig3d"], "models": [], "limits": {}}

    def default_model_for(self, kind):
        return {"to3d": "tripo3d/h3.1/image-to-3d",
                "prep3d": "fal-ai/imageutils/rembg",
                "rig3d": "fal-ai/meshy/rigging"}[kind]

    def estimate(self, kind, model, params):
        return {"usd": 0.40, "verified": False}

    def submit(self, job, urls):
        self.submits.append(job["kind"])
        if job["kind"] == "to3d":
            assert urls == ["https://photo/p.jpg"]
            return {"status_url": "s", "response_url": "r"}, "tripo3d/h3.1/image-to-3d"
        return {"status_url": "s", "response_url": "r"}, "fal-ai/meshy/rigging"


class FakeClient:
    def __init__(self, owner):
        self.owner = owner

    def wait_sync(self, status_url, response_url, timeout=600):
        if self.owner.fail_generate and len(self.owner.submits) == 1:
            return None, "tripo exploded"
        if self.owner.fail_rig and self.owner.submits[-1] == "rig3d":
            raise falmod.FalError("rig down")
        if self.owner.submits[-1] == "to3d":
            return {"model_mesh": {"url": "https://f/m.glb"},
                    "model_urls": {"glb": {"url": "https://f/m.glb"}},
                    "rendered_image": {"url": "https://f/prev.png"}}, None
        return {"rigged_character_glb": {"url": "https://f/rig.glb"}}, None

    def download(self, url, timeout=180):
        return b"GLBDATA", ".glb" if "m.glb" in url or "rig" in url else ".png"


class _FakeAssets:
    def __init__(self, tmp_path):
        self.saved: list[str] = []

    def save(self, data, *, kind, ext=".glb", source_url=None, job_id=None):
        self.saved.append(kind)
        return {"id": f"ast-{len(self.saved)}", "kind": kind, "ext": ext}


class _NoCloud:
    name = "kie"

    def health(self):
        return {"ok": False, "detail": "no key in tests", "gates": {}}

    def capabilities(self):
        return {"kinds": [], "models": [], "limits": {}, "dormant": True}


def make_router(tmp_path, fake_fal):
    router = MediaRouter(job_store=MediaJobStore(tmp_path / "jobs"),
                         asset_store=_FakeAssets(tmp_path),
                         cloud=_NoCloud(), fal=fake_fal)
    router.fal.client = FakeClient(fake_fal)
    return router


class TestThreeDPipeline:
    def _job(self, router):
        return router.jobs.new_job("to3d", "3D character from photo",
                                   params={"name": "Maya",
                                           "source_url": "https://photo/p.jpg"},
                                   requested_provider="fal")

    def test_full_run_succeeds_and_attaches_character(self, tmp_path, monkeypatch):
        fake = FakeFal()
        router = make_router(tmp_path, fake)

        import clawteam.media.characters as chars
        attached: dict = {}

        class FakeCharStore:
            def new(self, **kw):
                return {"id": "chr-1"}

            def attach_canonical(self, cid, asset_id=None, url=None, job_id=None):
                attached["cid"] = cid
                attached["url"] = url

        monkeypatch.setattr(chars, "CharacterStore", lambda: FakeCharStore())
        monkeypatch.setattr("clawteam.media.threed.ThreeDPipeline._qa",
                            lambda self, job, state, out: {"pass": True, "issues": []})

        job = self._job(router)
        ThreeDPipeline(router).run(job)
        done = router.jobs.get(job["id"])
        assert done["state"] == "succeeded"
        assert done["provider"] == "fal"
        assert done["model"] == "tripo3d/h3.1/image-to-3d"
        assert done["output_asset_ids"]          # glb + preview + rigged
        assert "model3d" in router.assets.saved
        assert attached["cid"] == "chr-1"
        assert attached["url"] == "https://f/prev.png"   # movie lane handoff
        assert fake.submits == ["to3d", "rig3d"]

    def test_generate_failure_fails_the_job(self, tmp_path):
        fake = FakeFal(fail_generate=True)
        router = make_router(tmp_path, fake)
        job = self._job(router)
        ThreeDPipeline(router).run(job)
        done = router.jobs.get(job["id"])
        assert done["state"] == "failed"
        assert "generate" in done["error"] and "tripo exploded" in done["error"]

    def test_rig_failure_still_delivers(self, tmp_path, monkeypatch):
        fake = FakeFal(fail_rig=True)
        router = make_router(tmp_path, fake)
        monkeypatch.setattr("clawteam.media.threed.ThreeDPipeline._qa",
                            lambda self, job, state, out: None)
        job = self._job(router)
        ThreeDPipeline(router).run(job)
        done = router.jobs.get(job["id"])
        assert done["state"] == "succeeded"        # rig skipped, delivery continues
        assert "rig skipped" in (done.get("provider_status") or "")

    def test_https_source_is_enforced(self, tmp_path):
        router = make_router(tmp_path, FakeFal())
        job = router.jobs.new_job("to3d", "x",
                                  params={"name": "N", "source_url": "http://nope.jpg"})
        ThreeDPipeline(router).run(job)
        assert router.jobs.get(job["id"])["state"] == "failed"

    def test_kinds_route_to_fal(self, tmp_path):
        assert {"to3d", "prep3d", "rig3d"} <= set(JOB_KINDS)
        assert {"to3d", "prep3d", "rig3d"} <= CLOUD_ONLY_KINDS
        router = make_router(tmp_path, FakeFal())
        plan = router.plan({"kind": "to3d", "params": {}})
        assert plan["provider"] == "fal"
        assert plan["model"] == "tripo3d/h3.1/image-to-3d"