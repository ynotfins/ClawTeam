"""KIE.ai cloud provider: KieClient + per-model adapters (never one universal schema).

Key from User-scope env KIE_API_KEY only; dormant (no key) is a first-class state.
Polling endpoint is universal (GET /api/v1/jobs/recordInfo) but CREATE payloads
are model-family specific — each adapter owns its request shape.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE = "https://api.kie.ai"
CREDIT_TO_USD = 0.005

# Estimate-only pricing table (NOT verified billing — dashboard caveat in UI).
# Sources: kie.ai public model pages, 2026-09-17. Bump version on any change.
PRICING_VERSION = "kie-pricing-2026-09-23/3"
PRICING = {
    # model: {kind: credits} — estimates pending per-task actuals from provider
    "flux1-kontext": {"t2img": 5.0, "edit": 5.0, "img2img": 5.0},  # verified live: creditsConsumed=5.0
    "runway": {"t2v": 12.0, "i2v": 12.0},  # verified live 2026-09-23: 5s/720p creditsConsumed=12.0
}


def kie_key() -> str:
    return os.environ.get("KIE_API_KEY", "").strip()


class KieClient:
    """Thin HTTP wrapper — auth, retries on 5xx/429 with backoff, no domain logic."""

    def __init__(self, key: str | None = None):
        self._key = key if key is not None else kie_key()

    @property
    def available(self) -> bool:
        return bool(self._key)

    def _call(self, method: str, path: str, payload: dict | None = None, timeout: int = 20) -> dict:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(BASE + path, data=data, method=method, headers={
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        })
        last_error = None
        for attempt in range(3):  # safe retry: GET only; POST retries are caller-controlled
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")[:300]
                if e.code in (429, 500, 503) and method == "GET" and attempt < 2:
                    continue
                raise RuntimeError(f"KIE HTTP {e.code}: {body}") from None
            except urllib.error.URLError as e:
                last_error = e
                if method == "GET" and attempt < 2:
                    continue
                raise RuntimeError(f"KIE unreachable: {e}") from None
        raise RuntimeError(f"KIE retries exhausted: {last_error}")

    def credits(self) -> float | None:
        if not self.available:
            return None
        try:
            d = self._call("GET", "/api/v1/chat/credit")
            return float(d.get("data", 0)) if isinstance(d.get("data"), (int, float)) else None
        except (RuntimeError, ValueError):
            return None

    def create_task(self, payload: dict) -> str:
        d = self._call("POST", "/api/v1/jobs/createTask", payload)
        task_id = (d.get("data") or {}).get("taskId")
        if not task_id:
            raise RuntimeError(f"createTask returned no taskId: {json.dumps(d)[:200]}")
        return task_id

    def record_info(self, task_id: str) -> dict:
        return self._call("GET", f"/api/v1/jobs/recordInfo?taskId={urllib.request.quote(task_id)}")

    def download(self, url: str, timeout: int = 120) -> tuple[bytes, str]:
        # KIE file URLs may need the download-url conversion for temp links;
        # try direct fetch first, convert on failure.
        def ext_of(u: str) -> str:
            low = u.lower().split("?")[0]
            for e in (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".webm"):
                if low.endswith(e):
                    return e
            return ".bin"

        def fetch(u: str) -> bytes:
            with urllib.request.urlopen(u, timeout=timeout) as resp:
                return resp.read()

        try:
            return fetch(url), ext_of(url)
        except urllib.error.HTTPError:
            d = self._call("POST", "/api/v1/common/download-url", {"url": url})
            temp = d.get("data")
            if isinstance(temp, str) and temp:
                return fetch(temp), ext_of(temp)
            raise


class _Adapter:
    """Base: translate a normalized job into this model family's createTask shape."""

    model: str
    kinds: tuple[str, ...]

    def build(self, job: dict, input_asset_urls: list[str]) -> dict:
        raise NotImplementedError


class FluxKontextAdapter(_Adapter):
    """docs.kie.ai/flux-kontext-api — image gen + edit (input_image)."""

    model = "flux1-kontext"
    kinds = ("t2img", "img2img", "edit", "character", "variant")

    def build(self, job: dict, input_asset_urls: list[str]) -> dict:
        p = job.get("params", {})
        inp: dict = {
            "prompt": job.get("prompt", ""),
            "aspect_ratio": p.get("aspect_ratio", "16:9"),
            "output_format": p.get("output_format", "png"),
            "safety_tolerance": 2,
        }
        if job["kind"] in ("img2img", "edit", "variant") and input_asset_urls:
            inp["input_image"] = input_asset_urls[0]
        return {"model": self.model, "input": inp}


class RunwayAdapter(_Adapter):
    """docs.kie.ai/runway-api — video (duration/quality; image_url for i2v)."""

    model = "runway"
    kinds = ("t2v", "i2v")

    def build(self, job: dict, input_asset_urls: list[str]) -> dict:
        p = job.get("params", {})
        inp: dict = {
            "prompt": job.get("prompt", "")[:1800],
            "duration": str(p.get("duration", 5)),
            "quality": p.get("quality", "720p"),
        }
        if job["kind"] == "i2v" and input_asset_urls:
            inp["image_url"] = input_asset_urls[0]
        else:
            inp["aspect_ratio"] = p.get("aspect_ratio", "16:9")
        return {"model": self.model, "input": inp}


ADAPTERS: dict[str, _Adapter] = {a.model: a for a in (FluxKontextAdapter(), RunwayAdapter())}

# Normalized mapping from recordInfo states (waiting/queuing/generating/
# success/fail per docs) — defensive: unknown strings stay "running" until timeout.
_STATUS_MAP = {"waiting": "running", "queuing": "running", "generating": "running",
               "success": "succeeded", "fail": "failed"}


class KieProvider:
    name = "kie"

    def __init__(self, client: KieClient | None = None):
        self.client = client or KieClient()

    def _adapter_for(self, model: str) -> _Adapter:
        adapter = ADAPTERS.get(model)
        if adapter is None:
            raise ValueError(f"no KIE adapter for model {model} (add one — schemas differ per family)")
        return adapter

    def capabilities(self) -> dict:
        return {
            "kinds": sorted({k for a in ADAPTERS.values() for k in a.kinds}),
            "models": [
                {"model": a.model, "kinds": list(a.kinds)} for a in ADAPTERS.values()
            ],
            "limits": {"max_concurrent": 1, "min_submit_spacing_seconds": 5},
            "dormant": not self.client.available,
        }

    def health(self) -> dict:
        if not self.client.available:
            return {"ok": False, "detail": "dormant: KIE_API_KEY not set (User env)",
                    "gates": {"api_key": False}}
        credits = self.client.credits()
        if credits is None:
            return {"ok": False, "detail": "key present but credits probe failed",
                    "gates": {"api_key": True, "credits_probe": False}}
        return {"ok": True, "detail": f"live · {credits:.0f} credits (~${credits * CREDIT_TO_USD:.2f})",
                "gates": {"api_key": True, "credits_probe": True}, "credits": credits}

    def estimate(self, kind: str, model: str, params: dict) -> dict:
        if kind == "character":
            # pipeline: sculpt edit + stylize edit (verified 5 credits each)
            credits = PRICING["flux1-kontext"]["edit"] * 2
            return {"credits": credits, "usd": round(credits * CREDIT_TO_USD, 4),
                    "pricing_table_version": PRICING_VERSION, "verified": False,
                    "note": "estimate only - two stylization edits"}
        if kind == "variant":
            credits = PRICING["flux1-kontext"]["edit"]
            return {"credits": credits, "usd": round(credits * CREDIT_TO_USD, 4),
                    "pricing_table_version": PRICING_VERSION, "verified": False,
                    "note": "estimate only - one identity-consistent edit"}
        credits = PRICING.get(model, {}).get(kind)
        if credits is None:
            return {"credits": None, "usd": None, "pricing_table_version": PRICING_VERSION,
                    "verified": False, "note": "no estimate entry — check dashboard before submitting"}
        return {"credits": credits, "usd": round(credits * CREDIT_TO_USD, 4),
                "pricing_table_version": PRICING_VERSION, "verified": False,
                "note": "estimate only — verify against KIE dashboard"}

    def default_model_for(self, kind: str) -> str:
        return "runway" if kind in ("t2v", "i2v") else "flux1-kontext"

    def submit(self, job: dict, input_asset_urls: list[str]) -> tuple[str, str]:
        model = job.get("model") or self.default_model_for(job["kind"])
        adapter = self._adapter_for(model)
        if job["kind"] not in adapter.kinds:
            raise ValueError(f"model {model} does not support kind {job['kind']}")
        task_id = self.client.create_task(adapter.build(job, input_asset_urls))
        return task_id, model

    def poll(self, task_id: str, kind: str) -> "ProviderResult":
        from clawteam.media.providers.base import ProviderResult
        d = self.client.record_info(task_id)
        data = d.get("data") or {}
        state_word = str(data.get("state") or data.get("status") or "").lower()
        state = _STATUS_MAP.get(state_word, "running")
        result = ProviderResult(state=state, provider_status=state_word or None)
        # Provider-reported actual cost (authoritative when present).
        credits = data.get("creditsConsumed")
        if credits is not None:
            try:
                result.actual_credits = float(credits)
                result.actual_usd = round(result.actual_credits * CREDIT_TO_USD, 6)
            except (TypeError, ValueError):
                pass
        if state == "failed":
            result.error = str(data.get("failMsg") or data.get("fail_code") or "provider reported failure")[:300]
        elif state == "succeeded":
            # Observed recordInfo shapes (verified live 2026-09-23): the URL list
            # appears in data.response.resultUrls, and/or in data.resultJson as a
            # JSON-encoded string. Collect every http(s) URL from all of them.
            urls: list[str] = []

            def walk(node):
                if isinstance(node, str) and node.startswith("http") and not node.endswith(".json"):
                    urls.append(node)
                elif isinstance(node, dict):
                    for v in node.values():
                        walk(v)
                elif isinstance(node, list):
                    for v in node:
                        walk(v)

            for source in (data.get("response"), data.get("resultUrls"), data.get("result_url"),
                           data.get("info")):
                if source:
                    walk(source)
            rj = data.get("resultJson")
            if isinstance(rj, str) and rj.strip().startswith("{"):
                try:
                    walk(json.loads(rj))
                except ValueError:
                    pass
            elif isinstance(rj, list) or isinstance(rj, dict):
                walk(rj)
            for v in (k for k in data if "url" in k.lower()):
                walk(data[v])
            seen = set()
            result.output_urls = [u for u in urls if not (u in seen or seen.add(u))]
        return result

    def download(self, url: str) -> tuple[bytes, str]:
        return self.client.download(url)
