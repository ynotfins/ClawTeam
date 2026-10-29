"""Fal.ai cloud provider — 3D character pipeline (D-016/D-017).

Key from User-scope env FAL_API_KEY only (name, never a value — D1).
Queue API contract (verified 2026-10-28, fal.ai/docs/model-endpoints/queue):
    POST https://queue.fal.run/{model}   Authorization: Key <FAL_KEY>
      -> {request_id, status_url, response_url}
    GET  {status_url}   -> {status: IN_QUEUE|IN_PROGRESS|COMPLETED, ...}
    GET  {response_url}  -> model output JSON

Model schemas (verified 2026-10-28 on fal.ai model pages):
  tripo3d/h3.1/image-to-3d  in {image_url, texture_quality, geometry_quality,
                                pbr, texture} out {model_mesh, model_urls{glb,
                                fbx, base_model, pbr_model}, rendered_image, task_id}
  fal-ai/meshy/rigging      in {model_url, enable_animation, animation_action_id}
                                out {rigged_character_glb, rigged_character_fbx,
                                basic_animations{walking_glb,...}, rig_task_id}
  fal-ai/imageutils/rembg    fal image-io (image_url -> image); schema
                              convention — verified:false until a live task runs (E6).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

QUEUE_BASE = "https://queue.fal.run"

# Estimate-only pricing (fal.ai gallery, 2026-10-28; USD per task). Bump on change.
PRICING_VERSION = "fal-pricing-2026-10-28/1"
PRICING_USD = {
    "tripo3d/h3.1/image-to-3d": {"to3d": 0.40},    # textured tier estimate
    "fal-ai/meshy/rigging": {"rig3d": 0.32},        # $0.20 rig + $0.12 animation
    "fal-ai/imageutils/rembg": {"prep3d": 0.02},
}

FALLBACK_TO3D_MODEL = "fal-ai/hunyuan-3d/v3.1/pro/image-to-3d"


def fal_key() -> str:
    return os.environ.get("FAL_API_KEY", "").strip()


class FalError(Exception):
    """Raised when a Fal queue request fails."""


class FalClient:
    """Thin queue-API wrapper: submit -> poll status -> fetch result."""

    def __init__(self, key: str | None = None):
        self._key = key if key is not None else fal_key()

    @property
    def available(self) -> bool:
        return bool(self._key)

    def _call(self, method: str, url: str, payload: dict | None = None,
              timeout: int = 30) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Key {self._key}",   # fal's prefix (NOT Bearer)
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            raise FalError(f"Fal HTTP {e.code}: {body}") from None
        except urllib.error.URLError as e:
            raise FalError(f"Fal unreachable: {e}") from None

    def submit(self, model: str, payload: dict) -> dict:
        """Enqueue; returns {request_id, status_url, response_url}."""
        out = self._call("POST", f"{QUEUE_BASE}/{model}", payload)
        for field in ("request_id", "status_url", "response_url"):
            if not out.get(field):
                raise FalError(f"submit({model}) missing {field}: {json.dumps(out)[:200]}")
        return out

    def status(self, status_url: str) -> dict:
        """One poll tick. Returns {status, queue_position?, error?}."""
        return self._call("GET", status_url)

    def result(self, response_url: str) -> dict:
        return self._call("GET", response_url)

    def wait_sync(self, status_url: str, response_url: str, timeout: float = 600,
                  fast: float = 2.0, growth: float = 1.5, cap: float = 20.0):
        """Poll to completion in worker context. Returns (output|None, error|None)."""
        import time as _time
        deadline = _time.time() + timeout
        interval = fast
        while _time.time() < deadline:
            try:
                snap = self.status(status_url)
            except FalError:
                snap = {}
            state = str(snap.get("status", "")).upper()
            if state == "COMPLETED":
                try:
                    return self.result(response_url), None
                except FalError as e:
                    return None, str(e)
            if snap.get("error"):
                return None, str(snap.get("error"))
            _time.sleep(interval)
            interval = min(cap, interval * growth)
        return None, "fal queue timeout"

    def download(self, url: str, timeout: int = 180) -> tuple[bytes, str]:
        """Fetch output bytes + extension (models and preview renders)."""
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            data = resp.read()

        def ext_of(u: str) -> str:
            low = u.lower().split("?")[0]
            for e in (".glb", ".fbx", ".png", ".jpg", ".jpeg", ".webp", ".mp4"):
                if low.endswith(e):
                    return e
            return ".bin"

        return data, ext_of(url)


def _file_url(node) -> str:
    """Fal File object -> its url ('' when absent)."""
    if isinstance(node, dict):
        return str(node.get("url", "") or "")
    return str(node or "")


class _FalAdapter:
    """Translate a pipeline step into a fal model payload + result shape."""

    model: str
    kinds: tuple[str, ...]

    def build(self, job: dict, input_urls: list[str]) -> dict:
        raise NotImplementedError

    def parse(self, output: dict) -> dict:
        """Normalize fal output into {urls, previews, task_ids}."""
        raise NotImplementedError


class RembgAdapter(_FalAdapter):
    """fal-ai/imageutils/rembg — background removal (prep3d).

    Input schema follows fal image-io convention (image_url). The exact page
    schema was not fetchable tonight; payload is minimal to stay compatible,
    and estimates stay verified:false until the first live task (E6).
    """

    model = "fal-ai/imageutils/rembg"
    kinds = ("prep3d",)

    def build(self, job: dict, input_urls: list[str]) -> dict:
        return {"image_url": input_urls[0] if input_urls else ""}

    def parse(self, output: dict) -> dict:
        url = _file_url(output.get("image")) or _file_url(output.get("output"))
        return {"urls": [url] if url else [], "previews": [], "task_ids": {}}


class TripoImageTo3DAdapter(_FalAdapter):
    """tripo3d/h3.1/image-to-3d — highest-quality default (D-016 'best model')."""

    model = "tripo3d/h3.1/image-to-3d"
    kinds = ("to3d",)

    def build(self, job: dict, input_urls: list[str]) -> dict:
        p = job.get("params", {})
        payload: dict = {"image_url": input_urls[0] if input_urls else ""}
        # Quality defaults: detailed both (operator: highest quality possible).
        payload["texture_quality"] = p.get("texture_quality", "detailed")
        payload["geometry_quality"] = p.get("geometry_quality", "detailed")
        payload["pbr"] = bool(p.get("pbr", True))
        payload["texture"] = bool(p.get("texture", True))
        return payload

    def parse(self, output: dict) -> dict:
        urls: list[str] = []
        model_urls = output.get("model_urls") or {}
        for key in ("glb", "fbx", "pbr_model", "base_model"):
            u = _file_url(model_urls.get(key)) if isinstance(model_urls, dict) else ""
            if u:
                urls.append(u)
        mesh = _file_url(output.get("model_mesh"))
        if mesh and mesh not in urls:
            urls.insert(0, mesh)
        previews = [u for u in [_file_url(output.get("rendered_image"))] if u]
        return {
            "urls": urls,
            "previews": previews,
            "task_ids": {"tripo": str(output.get("task_id", "") or "")},
        }


class MeshyRiggingAdapter(_FalAdapter):
    """fal-ai/meshy/rigging — humanoid armature + vertex weights (+animations)."""

    model = "fal-ai/meshy/rigging"
    kinds = ("rig3d",)

    def build(self, job: dict, input_urls: list[str]) -> dict:
        p = job.get("params", {})
        return {
            "model_url": input_urls[0] if input_urls else "",  # public GLB url
            "enable_animation": bool(p.get("enable_animation", True)),
            "animation_action_id": int(p.get("animation_action_id", 92)),  # 0..696, 0=Idle
        }

    def parse(self, output: dict) -> dict:
        urls = [u for u in [
            _file_url(output.get("rigged_character_glb")),
            _file_url(output.get("rigged_character_fbx")),
        ] if u]
        anims = output.get("basic_animations") or {}
        previews = [u for u in [
            _file_url(anims.get("walking_glb")),
        ] if u]
        return {
            "urls": urls,
            "previews": previews,
            "task_ids": {"meshy": str(output.get("rig_task_id", "") or "")},
        }


ADAPTERS: dict[str, _FalAdapter] = {a.model: a for a in (
    RembgAdapter(),
    TripoImageTo3DAdapter(),
    MeshyRiggingAdapter(),
)}


class FalProvider:
    """Provider boundary for the Fal queue API (same shape as KieProvider)."""

    name = "fal"

    def __init__(self, client: FalClient | None = None):
        self.client = client or FalClient()

    def capabilities(self) -> dict:
        return {
            "kinds": sorted({k for a in ADAPTERS.values() for k in a.kinds}),
            "models": [{"model": a.model, "kinds": list(a.kinds)} for a in ADAPTERS.values()],
            "limits": {"max_concurrent": 2, "min_submit_spacing_seconds": 2},
            "dormant": not self.client.available,
        }

    def health(self) -> dict:
        if not self.client.available:
            return {"ok": False, "detail": "dormant: FAL_API_KEY not set (User env)",
                    "gates": {"api_key": False}}
        # Key present. A live task is the only full proof; treat present as
        # ready and let the first submit surface auth errors cleanly.
        return {"ok": True, "detail": "ready (FAL_API_KEY present; live task pending)",
                "gates": {"api_key": True}}

    def estimate(self, kind: str, model: str, params: dict) -> dict:
        usd = PRICING_USD.get(model, {}).get(kind)
        if usd is None:
            return {"credits": None, "usd": None, "pricing_table_version": PRICING_VERSION,
                    "verified": False, "note": "no fal pricing entry yet — check dashboard"}
        return {"credits": None, "usd": usd, "pricing_table_version": PRICING_VERSION,
                "verified": False, "note": "USD estimate only — fal bills in dollars, not credits"}

    def default_model_for(self, kind: str) -> str:
        if kind == "prep3d":
            return "fal-ai/imageutils/rembg"
        if kind == "to3d":
            return "tripo3d/h3.1/image-to-3d"
        if kind == "rig3d":
            return "fal-ai/meshy/rigging"
        raise FalError(f"fal has no adapter for kind '{kind}'")

    def submit(self, job: dict, input_urls: list[str]) -> tuple[dict, str]:
        """Enqueue one pipeline step. Returns (queue_ticket, model)."""
        model = job.get("model") or self.default_model_for(job["kind"])
        adapter = ADAPTERS.get(model)
        if adapter is None:
            raise FalError(f"no Fal adapter for model {model}")
        if job["kind"] not in adapter.kinds:
            raise FalError(f"model {model} does not support kind {job['kind']}")
        ticket = self.client.submit(model, adapter.build(job, input_urls))
        return ticket, model

    def poll(self, ticket: dict, kind: str):
        """One poll tick (worker loop). Returns a KIE-shaped ProviderResult."""
        from clawteam.media.providers.base import ProviderResult
        snap = self.client.status(ticket["status_url"])
        state_word = str(snap.get("status", "")).upper()
        mapped = {"IN_QUEUE": "running", "IN_PROGRESS": "running",
                  "COMPLETED": "succeeded"}.get(state_word, "running")
        return ProviderResult(state=mapped, provider_status=state_word or None,
                              error=str(snap.get("error")) if snap.get("error") else None)

    def fetch_output(self, ticket: dict) -> dict:
        """COMPLETED: fetch the model output JSON from the response_url."""
        return self.client.result(ticket["response_url"])