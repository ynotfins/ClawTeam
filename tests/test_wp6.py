"""WP6 pass 1 — Easy Studio: Topaz adapters, vupscale kind, one-click presets.

New-surface tests for the D-016 family-first media center. Adapter payload
shapes are pinned to the docs.kie.ai schemas fetched 2026-10-28 (E6);
presets are validated against the live adapter registry at load time.
"""

from __future__ import annotations

import json

import pytest

from clawteam.media.providers import kie
from clawteam.media.presets import (
    BUILTIN_PRESETS,
    PresetError,
    load_presets,
    preset_job_spec,
    validate_presets,
)
from clawteam.media.jobs import JOB_KINDS
from clawteam.media.router import CLOUD_ONLY_KINDS


# ---------------------------------------------------------------------------
# Topaz adapters (E6-verified schemas)
# ---------------------------------------------------------------------------


class TestTopazAdapters:
    def test_image_upscale_payload(self):
        a = kie.TopazImageUpscaleAdapter()
        payload = a.build({"kind": "upscale", "prompt": "", "params": {}},
                          ["https://x/photo.jpg"])
        assert payload["model"] == "topaz/image-upscale"
        assert payload["input"]["image_url"] == "https://x/photo.jpg"
        assert payload["input"]["upscale_factor"] == "2"       # string enum per schema
        assert set(payload["input"].keys()) == {"image_url", "upscale_factor"}

    def test_image_upscale_factor_4(self):
        a = kie.TopazImageUpscaleAdapter()
        payload = a.build({"kind": "upscale", "prompt": "", "params": {"upscale_factor": "4"}}, [])
        assert payload["input"]["upscale_factor"] == "4"

    def test_video_upscale_payload(self):
        a = kie.TopazVideoUpscaleAdapter()
        payload = a.build({"kind": "vupscale", "prompt": "", "params": {}},
                          ["https://x/clip.mp4"])
        assert payload["model"] == "topaz/video-upscale"
        assert payload["input"]["video_url"] == "https://x/clip.mp4"
        assert payload["input"]["upscale_factor"] == "2"

    def test_registered_and_defaulted(self):
        assert "topaz/image-upscale" in kie.ADAPTERS
        assert "topaz/video-upscale" in kie.ADAPTERS
        p = kie.KieProvider(client=kie.KieClient(key="k"))
        assert p.default_model_for("upscale") == "topaz/image-upscale"
        assert p.default_model_for("vupscale") == "topaz/video-upscale"

    def test_vupscale_is_a_job_kind_and_cloud_only(self):
        assert "vupscale" in JOB_KINDS
        assert "vupscale" in CLOUD_ONLY_KINDS

    def test_topaz_estimate_uses_pricing(self):
        p = kie.KieProvider(client=kie.KieClient(key="k"))
        est = p.estimate("upscale", "topaz/image-upscale", {})
        assert est["credits"] == kie.PRICING["topaz/image-upscale"]["upscale"]
        assert est["verified"] is False        # E6: verified only after live creditsConsumed


# ---------------------------------------------------------------------------
# One-click presets (D-016 Easy Studio)
# ---------------------------------------------------------------------------


class TestPresets:
    def test_builtin_catalog_validates(self):
        presets = load_presets()
        assert any(p["id"] == "sharper-photo" for p in presets)
        assert all(p["one_click"] for p in presets)
        assert len(presets) >= 6

    def test_upscale_tiles_are_topaz(self):
        presets = {p["id"]: p for p in load_presets()}
        assert presets["sharper-photo"]["model"] == "topaz/image-upscale"
        assert presets["sharper-video"]["model"] == "topaz/video-upscale"

    def test_e6_rejects_unverified_model(self):
        with pytest.raises(PresetError, match="no verified KIE adapter"):
            validate_presets([{"id": "x", "title": "t", "blurb": "b",
                               "kind": "t2img", "model": "not-a-model",
                               "needs": "none"}])

    def test_e6_rejects_kind_drift(self):
        with pytest.raises(PresetError, match="does not support kind"):
            validate_presets([{"id": "x", "title": "t", "blurb": "b",
                               "kind": "t2v", "model": "topaz/image-upscale",
                               "needs": "none"}])

    def test_rejects_duplicate_ids_and_missing_titles(self):
        base = {"title": "t", "blurb": "b", "kind": "upscale",
                "model": "topaz/image-upscale", "needs": "image"}
        with pytest.raises(PresetError, match="duplicated"):
            validate_presets([{**base, "id": "x"}, {**base, "id": "x"}])
        with pytest.raises(PresetError, match="title and blurb"):
            validate_presets([{"id": "x", "blurb": "b", "kind": "upscale",
                               "model": "topaz/image-upscale", "needs": "image"}])

    def test_job_spec_shape(self):
        preset = next(p for p in BUILTIN_PRESETS if p["id"] == "sharper-photo")
        spec = preset_job_spec(preset, source_url="https://x/p.jpg")
        assert spec["kind"] == "upscale"
        assert spec["model"] == "topaz/image-upscale"
        assert spec["params"]["upscale_factor"] == "2"
        assert spec["params"]["source_url"] == "https://x/p.jpg"
        assert spec["requested_provider"] == "kie"


# ---------------------------------------------------------------------------
# Board route
# ---------------------------------------------------------------------------


class TestPresetsRoute:
    @staticmethod
    def _get(path: str) -> dict:
        import io
        from clawteam.board.server import BoardHandler
        handler = object.__new__(BoardHandler)
        handler.path = path
        handler.command = "GET"
        handler.headers = {}
        handler.rfile = io.BytesIO(b"")
        handler.wfile = io.BytesIO()
        handler.log_message = lambda *a, **kw: None
        handler.send_response = lambda *a, **kw: None
        handler.send_header = lambda *a, **kw: None
        handler.end_headers = lambda: None
        served: dict = {}
        handler._serve_json = lambda data: served.setdefault("data", data)
        handler.do_GET()
        return served["data"]

    def test_presets_route_serves_validated_catalog(self):
        data = self._get("/api/media/presets")
        ids = {p["id"] for p in data["presets"]}
        assert {"sharper-photo", "sharper-video", "make-picture"} <= ids
        # every preset on the wire is E6-validated
        validate_presets(data["presets"])