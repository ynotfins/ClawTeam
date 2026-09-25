"""Multimedia Suite tests: store, router gates/throttle, KIE adapters, lifecycle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clawteam.media.assets import AssetStore
from clawteam.media.jobs import MediaJobStore, JOB_STATES, TERMINAL_STATES
from clawteam.media.providers.base import ProviderResult
from clawteam.media.providers import kie
from clawteam.media.router import MediaRouter


@pytest.fixture()
def stores(tmp_path):
    return MediaJobStore(tmp_path), AssetStore(tmp_path)


class FakeLocal:
    name = "comfyui-local"

    def __init__(self, healthy=True):
        self.healthy_ok = healthy
        self.submitted = []

    def capabilities(self):
        return {"kinds": ["t2img", "img2img"], "models": [], "limits": {}}

    def health(self):
        return {"ok": self.healthy_ok, "detail": "ok" if self.healthy_ok else "down", "gates": {}}

    def estimate(self, kind, model, params):
        return {"credits": 0.0, "usd": 0.0, "pricing_table_version": "local/1", "verified": True}

    def submit(self, job, input_urls):
        self.submitted.append(job["id"])
        return f"local-task-{len(self.submitted)}"

    def poll(self, task_id, kind):
        return ProviderResult(state="succeeded", provider_status="success",
                              output_urls=["/view?filename=x.png"])

    def download(self, url):
        return b"PNGDATA", ".png"


class FakeCloud:
    name = "kie"

    def __init__(self, available=True):
        from clawteam.media.providers.base import ProviderResult as R
        self._R = R
        self.available = available
        self.submits = 0

    def capabilities(self):
        return {"kinds": ["t2img", "edit", "t2v", "i2v"],
                "models": [{"model": "flux1-kontext", "kinds": ["t2img", "edit"]},
                           {"model": "runway", "kinds": ["t2v", "i2v"]}],
                "limits": {}, "dormant": not self.available}

    def health(self):
        if not self.available:
            return {"ok": False, "detail": "dormant: KIE_API_KEY not set", "gates": {"api_key": False}}
        return {"ok": True, "detail": "live", "gates": {}}

    def estimate(self, kind, model, params):
        return {"credits": 20.0, "usd": 0.10, "pricing_table_version": kie.PRICING_VERSION, "verified": False}

    def default_model_for(self, kind):
        return "runway" if kind in ("t2v", "i2v") else "flux1-kontext"

    def submit(self, job, input_urls):
        self.submits += 1
        return f"kie-task-{self.submits}"

    def poll(self, task_id, kind):
        return self._R(state="succeeded", provider_status="success", output_urls=["https://file/k/x.mp4"])

    def download(self, url):
        return b"MP4DATA", ".mp4"


def make_router(tmp_path, local=None, cloud=None):
    return MediaRouter(
        job_store=MediaJobStore(tmp_path), asset_store=AssetStore(tmp_path),
        local=local or FakeLocal(), cloud=cloud or FakeCloud())


class TestJobStore:
    def test_lifecycle_states_defined(self):
        assert "succeeded_provider_download_failed" in JOB_STATES
        assert "downloading" in JOB_STATES
        assert TERMINAL_STATES == {"succeeded", "failed", "timed_out", "succeeded_provider_download_failed"}

    def test_create_and_persist(self, stores):
        jobs, _ = stores
        job = jobs.new_job("t2img", "a cat", params={"steps": 20})
        assert job["state"] == "draft"
        assert jobs.get(job["id"])["prompt"] == "a cat"
        jobs.queue(job)
        assert jobs.get(job["id"])["state"] == "queued"

    def test_bad_kind_rejected(self, stores):
        jobs, _ = stores
        with pytest.raises(ValueError):
            jobs.new_job("nope", "x")

    def test_list_roundtrip(self, stores):
        jobs, _ = stores
        jobs.new_job("t2img", "one")
        jobs.new_job("t2img", "two")
        assert len(jobs.list()) == 2


class TestRouter:
    def test_local_first_for_safe_kind(self, tmp_path):
        r = make_router(tmp_path)
        job = r.jobs.new_job("t2img", "cat")
        plan = r.plan(job)
        assert plan["provider"] == "comfyui-local"
        assert plan["estimate"]["credits"] == 0.0

    def test_cloud_only_kind_routes_to_kie(self, tmp_path):
        r = make_router(tmp_path)
        job = r.jobs.new_job("t2v", "cat dancing")
        assert r.plan(job)["provider"] == "kie"

    def test_local_down_falls_back_to_cloud_for_t2img(self, tmp_path):
        r = make_router(tmp_path, local=FakeLocal(healthy=False))
        assert r.plan(r.jobs.new_job("t2img", "x"))["provider"] == "kie"

    def test_all_down_reports_error(self, tmp_path):
        r = make_router(tmp_path, local=FakeLocal(healthy=False), cloud=FakeCloud(available=False))
        plan = r.plan(r.jobs.new_job("t2v", "x"))
        assert plan.get("error")

    def test_full_success_lifecycle_downloads_before_complete(self, tmp_path):
        r = make_router(tmp_path)
        job = r.jobs.new_job("t2img", "cat")
        r.jobs.queue(job)
        r._tick()
        assert r.jobs.get(job["id"])["state"] == "running"
        r._tick()  # poll -> provider_succeeded -> download
        final = r.jobs.get(job["id"])
        assert final["state"] == "succeeded"
        assert len(final["output_asset_ids"]) == 1
        asset = r.assets.get(final["output_asset_ids"][0])
        assert asset["bytes"] == 7  # b"PNGDATA"

    def test_download_failure_marks_special_state(self, tmp_path):
        class DLFail(FakeLocal):
            def download(self, url):
                raise RuntimeError("link expired")
        r = make_router(tmp_path, local=DLFail())
        job = r.jobs.new_job("t2img", "cat")
        r.jobs.queue(job)
        r._tick(); r._tick(); r._tick()
        final = r.jobs.get(job["id"])
        assert final["state"] == "succeeded_provider_download_failed"
        assert "download failed" in (final["error"] or "")

    def test_no_duplicate_submit_after_failure(self, tmp_path):
        class FailSubmit(FakeLocal):
            def submit(self, job, input_urls):
                raise RuntimeError("boom")
        local = FailSubmit()
        r = make_router(tmp_path, local=local)
        job = r.jobs.new_job("t2img", "cat")
        r.jobs.queue(job)
        r._tick()
        assert r.jobs.get(job["id"])["state"] == "failed"
        r._tick()  # failed jobs are terminal; worker must not resubmit
        assert local.submitted == []
        assert r.jobs.get(job["id"])["state"] == "failed"

    def test_backoff_schedule_is_not_fixed(self):
        from clawteam.media.router import POLL_FAST_INTERVAL, POLL_FAST_TICKS, POLL_GROWTH, POLL_MAX_INTERVAL
        intervals = []
        for n in range(25):
            i = POLL_FAST_INTERVAL if n < POLL_FAST_TICKS else min(
                POLL_MAX_INTERVAL, POLL_FAST_INTERVAL * (POLL_GROWTH ** (n - POLL_FAST_TICKS + 1)))
            intervals.append(i)
        assert intervals[0] == 2.0
        assert intervals[10] > intervals[9]
        assert max(intervals) <= 30.0


class TestKieAdapters:
    def test_kontext_t2img_payload(self):
        a = kie.FluxKontextAdapter()
        payload = a.build({"kind": "t2img", "prompt": "p", "params": {"aspect_ratio": "1:1"}}, [])
        assert payload["model"] == "flux1-kontext"
        assert payload["input"]["prompt"] == "p"
        assert payload["input"]["aspect_ratio"] == "1:1"
        assert "input_image" not in payload["input"]

    def test_kontext_edit_uses_input_image(self):
        a = kie.FluxKontextAdapter()
        payload = a.build({"kind": "edit", "prompt": "p", "params": {}}, ["https://x/img.png"])
        assert payload["input"]["input_image"] == "https://x/img.png"

    def test_runway_t2v_needs_aspect(self):
        a = kie.RunwayAdapter()
        payload = a.build({"kind": "t2v", "prompt": "p", "params": {"aspect_ratio": "9:16"}}, [])
        assert payload["model"] == "runway"
        assert payload["input"]["aspect_ratio"] == "9:16"
        assert "image_url" not in payload["input"]

    def test_runway_i2v_uses_image_url(self):
        a = kie.RunwayAdapter()
        payload = a.build({"kind": "i2v", "prompt": "p", "params": {}}, ["https://x/img.png"])
        assert payload["input"]["image_url"] == "https://x/img.png"
        assert "aspect_ratio" not in payload["input"]

    def test_unknown_model_rejected(self):
        p = kie.KieProvider.__new__(kie.KieProvider)
        with pytest.raises(ValueError):
            p._adapter_for("unknown-model")

    def test_status_normalization(self):
        p = kie.KieProvider(client=kie.KieClient(key="k"))
        p.client.record_info = lambda tid: {"data": {"state": "generating"}}
        assert p.poll("t", "t2img").state == "running"
        p.client.record_info = lambda tid: {"data": {"state": "fail", "failMsg": "boom"}}
        result = p.poll("t", "t2img")
        assert result.state == "failed" and "boom" in result.error
        p.client.record_info = lambda tid: {"data": {"state": "success",
            "resultUrls": ["https://a/1.png", "https://a/2.png"]}}
        assert p.poll("t", "t2img").output_urls == ["https://a/1.png", "https://a/2.png"]

    def test_estimate_is_labeled_unverified(self):
        p = kie.KieProvider(client=kie.KieClient(key="k"))
        est = p.estimate("t2img", "flux1-kontext", {})
        assert est["verified"] is False
        assert est["credits"] == kie.PRICING["flux1-kontext"]["t2img"]

    def test_dormant_health(self):
        p = kie.KieProvider(client=kie.KieClient(key=""))
        h = p.health()
        assert h["ok"] is False and "KIE_API_KEY" in h["detail"]


class TestCharacters:
    @pytest.fixture()
    def char_store(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
        from clawteam.media.characters import CharacterStore
        return CharacterStore()

    def test_character_crud(self, char_store):
        rec = char_store.new(name="Maya", source_url="https://x/photo.jpg")
        assert rec["canonical_asset_id"] is None
        assert char_store.get(rec["id"])["name"] == "Maya"
        assert len(char_store.list()) == 1
        char_store.attach_canonical(rec["id"], asset_id="ast-1", url="https://x/1.png", job_id="job-1")
        assert char_store.get(rec["id"])["canonical_url"] == "https://x/1.png"
        char_store.add_variant(rec["id"], asset_id="ast-2", url="https://x/2.png", prompt="waving")
        char_store.add_scene(rec["id"], asset_id="ast-3", prompt="waves", source="canonical")
        got = char_store.get(rec["id"])
        assert len(got["variants"]) == 1 and len(got["scenes"]) == 1

    def test_character_name_validated(self, char_store):
        with pytest.raises(ValueError):
            char_store.new(name="bad/name", source_url="https://x/p.jpg")
        with pytest.raises(ValueError):
            char_store.new(name="ok", source_url="http://not-https.jpg")

    def test_kinds_include_character_variant(self):
        from clawteam.media.jobs import JOB_KINDS
        assert "character" in JOB_KINDS and "variant" in JOB_KINDS

    def test_character_estimates(self):
        from clawteam.media.providers.kie import KieProvider, KieClient
        p = KieProvider(client=KieClient(key="k"))
        est = p.estimate("character", "flux1-kontext", {})
        assert est["credits"] == 10.0 and est["verified"] is False
        est2 = p.estimate("variant", "flux1-kontext", {})
        assert est2["credits"] == 5.0

    def test_variant_adapter_uses_input_image(self):
        a = kie.FluxKontextAdapter()
        payload = a.build({"kind": "variant", "prompt": "same character, new pose", "params": {}},
                          ["https://x/canon.png"])
        assert payload["input"]["input_image"] == "https://x/canon.png"

    def test_character_pipeline_success(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
        from clawteam.media.characters import CharacterStore

        class FakeCloudChars(FakeCloud):
            def __init__(self):
                super().__init__()
                self.submits = 0

            def estimate(self, kind, model, params):
                return {"credits": 10.0 if kind == "character" else 5.0,
                        "usd": 0.05, "pricing_table_version": "t/1", "verified": False}

            def submit(self, job, input_urls):
                self.submits += 1
                return f"task-{self.submits}", "flux1-kontext"

            def poll(self, task_id, kind):
                from clawteam.media.providers.base import ProviderResult as R
                return R(state="succeeded", provider_status="success",
                         output_urls=[f"https://x/out-{task_id}.png"],
                         actual_credits=5.0, actual_usd=0.025)

            def download(self, url):
                return b"IMGDATA", ".png"

        r = MediaRouter(job_store=MediaJobStore(tmp_path), asset_store=AssetStore(tmp_path),
                        local=FakeLocal(), cloud=FakeCloudChars())
        job = r.jobs.new_job("character", "create character",
                             params={"source_url": "https://x/photo.jpg", "name": "Maya"})
        r.jobs.queue(job)
        r._tick()
        final = r.jobs.get(job["id"])
        assert final["state"] == "succeeded"
        assert len(final["output_asset_ids"]) == 2          # sculpt + stylize assets
        assert final["cost_actual_credits"] == 10.0         # 5 + 5 summed
        chars = CharacterStore().list()
        assert len(chars) == 1 and chars[0]["name"] == "Maya"
        assert chars[0]["canonical_asset_id"] == final["output_asset_ids"][-1]

    def test_character_requires_https(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
        r = make_router(tmp_path)
        job = r.jobs.new_job("character", "x", params={"source_url": "http://x/p.jpg", "name": "M"})
        r.jobs.queue(job)
        r._tick()
        assert r.jobs.get(job["id"])["state"] == "failed"

    def test_variant_job_registers_to_character(self, tmp_path, monkeypatch):
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
        from clawteam.media.characters import CharacterStore
        cs = CharacterStore()
        rec = cs.new(name="Maya", source_url="https://x/p.jpg")
        cs.attach_canonical(rec["id"], asset_id="ast-c", url="https://x/canon.png")

        class FakeCloudVariant(FakeCloud):
            def estimate(self, kind, model, params):
                return {"credits": 5.0, "usd": 0.025, "pricing_table_version": "t/1", "verified": False}
            def submit(self, job, input_urls):
                assert input_urls == ["https://x/canon.png"]  # canonical feeds the edit
                return "task-v", "flux1-kontext"
            def poll(self, task_id, kind):
                from clawteam.media.providers.base import ProviderResult as R
                return R(state="succeeded", provider_status="success",
                         output_urls=["https://x/variant.png"], actual_credits=5.0)
            def download(self, url):
                return b"VAR", ".png"

        r = MediaRouter(job_store=MediaJobStore(tmp_path), asset_store=AssetStore(tmp_path),
                        local=FakeLocal(), cloud=FakeCloudVariant())
        job = r.jobs.new_job("variant", "same character - now waving",
                             params={"character_id": rec["id"]})
        r.jobs.queue(job)
        r._tick(); r._tick(); r._tick()
        assert r.jobs.get(job["id"])["state"] == "succeeded"
        got = cs.get(rec["id"])
        assert len(got["variants"]) == 1
        assert got["variants"][0]["asset_id"] == r.jobs.get(job["id"])["output_asset_ids"][0]
