"""Route policy + background worker driving the app-owned job lifecycle.

Amendment guarantees:
- exponential backoff polling (fast window -> x1.5 growth -> 30s cap), per-kind timeout
- no duplicate credit-consuming submits (submit exactly once; retry is user-initiated)
- cloud throttle: 1 concurrent submit, >=5s spacing
- download outputs into local assets BEFORE marking succeeded
  (failure -> succeeded_provider_download_failed, never silently lost)
"""

from __future__ import annotations

import threading
import time
import traceback

from clawteam.media.assets import AssetStore
from clawteam.media.jobs import MediaJobStore, ACTIVE_STATES, TERMINAL_STATES
from clawteam.media.providers.base import ProviderResult
from clawteam.media.providers.comfyui_local import ComfyUiLocalProvider, KIND_TIMEOUT_SECONDS
from clawteam.media.providers.kie import KieProvider

# Default routing policy: local-first for safe image kinds; cloud for the rest.
LOCAL_SAFE_KINDS = {"t2img", "img2img"}
CLOUD_ONLY_KINDS = {"t2v", "i2v", "edit", "upscale", "character", "variant"}

POLL_FAST_INTERVAL = 2.0
POLL_FAST_TICKS = 10
POLL_GROWTH = 1.5
POLL_MAX_INTERVAL = 30.0
CLOUD_MIN_SUBMIT_SPACING = 5.0
UPLOAD_SWEEP_INTERVAL = 900.0  # expired photo links: sweep every 15 min


class MediaRouter:
    def __init__(self, job_store: MediaJobStore | None = None,
                 asset_store: AssetStore | None = None,
                 local: ComfyUiLocalProvider | None = None,
                 cloud: KieProvider | None = None):
        self.jobs = job_store or MediaJobStore()
        self.assets = asset_store or AssetStore()
        self.local = local or ComfyUiLocalProvider()
        self.cloud = cloud or KieProvider()
        self._worker: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_cloud_submit = 0.0
        self._cloud_lock = threading.Lock()

    # ---- routing ---------------------------------------------------------
    def providers_status(self) -> dict:
        return {
            "local": {"name": self.local.name, **self.local.capabilities(), "health": self.local.health()},
            "cloud": {"name": self.cloud.name, **self.cloud.capabilities(), "health": self.cloud.health()},
        }

    def plan(self, job: dict) -> dict:
        """Pick provider+model and attach the pre-submit estimate."""
        kind = job["kind"]
        requested = job.get("requested_provider")
        local_ok = self.local.health()["ok"] and kind in LOCAL_SAFE_KINDS
        cloud_ok = self.cloud.health()["ok"]

        if requested == "comfyui-local":
            if kind not in LOCAL_SAFE_KINDS:
                return {"error": f"kind {kind} is not in the local-safe set"}
            if not self.local.health()["ok"]:
                return {"error": "local gates failed: " + self.local.health()["detail"]}
            provider, model = self.local, None
        elif requested == "kie":
            if not self.cloud.health()["ok"]:
                return {"error": "KIE unavailable: " + self.cloud.health()["detail"]}
            if kind not in {k for a in (self.cloud.capabilities()["models"]) for k in a["kinds"]}:
                return {"error": f"KIE has no adapter covering {kind} yet"}
            provider, model = self.cloud, job.get("model") or self.cloud.default_model_for(kind)
        elif local_ok:
            provider, model = self.local, None
        elif cloud_ok and kind != "img2img":
            provider, model = self.cloud, job.get("model") or self.cloud.default_model_for(kind)
        else:
            reason = "local gates failed" if kind in LOCAL_SAFE_KINDS else f"kind {kind} requires cloud"
            if not cloud_ok:
                reason += " and KIE is unavailable/dormant"
            return {"error": reason}

        estimate = provider.estimate(kind, model or "", job.get("params", {}))
        return {"provider": provider.name, "model": model, "estimate": estimate}

    # ---- input URLs (cloud needs public URLs; local reads files) ---------
    def _input_urls(self, job: dict) -> list[str]:
        from clawteam.media.characters import CharacterStore
        params = job.get("params") or {}
        if job.get("kind") == "variant":
            cid = params.get("character_id") or job.get("_character_id")
            rec = CharacterStore().get(cid) if cid else None
            if rec is None or not rec.get("canonical_url"):
                raise ValueError("variant needs a character with a canonical image")
            return [rec["canonical_url"]]
        if job.get("kind") == "i2v" and params.get("character_id") and not params.get("source_url"):
            rec = CharacterStore().get(params["character_id"])
            if rec is None or not rec.get("canonical_url"):
                raise ValueError("character not found for animation")
            return [rec["canonical_url"]]
        urls = []
        source = params.get("source_url")
        if source:
            urls.append(source)
        return urls

    # ---- worker ----------------------------------------------------------
    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._stop.clear()
        self._worker = threading.Thread(target=self._run, name="media-router", daemon=True)
        self._worker.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        next_sweep = 0.0
        while not self._stop.is_set():
            try:
                self._tick()
                if time.monotonic() >= next_sweep:
                    from clawteam.media.uploads import UploadStore
                    UploadStore().sweep()
                    next_sweep = time.monotonic() + UPLOAD_SWEEP_INTERVAL
            except Exception:
                traceback.print_exc()
            self._stop.wait(1.0)

    def _tick(self) -> None:
        for job in self.jobs.list(limit=50):
            state = job.get("state")
            if state == "queued":
                if job.get("kind") == "character":
                    self._run_character_pipeline(job)
                    continue
                self._submit(job)
            elif state == "running":
                self._advance(job, poll=True)
            elif state in ("provider_succeeded", "downloading"):
                self._download_outputs(job)

    # ---- character pipeline (photo -> 3D-look stylized canonical) ----------
    # Lane A: stylized 3D-LOOKING imagery via kontext identity-preserving edits.
    # Not a true 3D asset; true-3D providers attach later behind the same boundary.
    CHARACTER_STAGES = (
        ("sculpt", "Transform this photo into a polished 3D animated-film character "
                   "render: sculpted stylized proportions, smooth high-quality 3D "
                   "shading, soft studio lighting, clean neutral background. Keep this "
                   "person clearly recognizable - same face structure, hair, skin tone, "
                   "and distinguishing features."),
        ("stylize", "Restyle this 3D character render into a heartwarming big-studio "
                    "animated movie character: expressive friendly eyes, refined "
                    "stylized proportions, soft cinematic lighting, rich colors. "
                    "Preserve the same recognizable person - same face structure, "
                    "hair, and features."),
    )

    def _poll_sync(self, provider, task_id, kind, timeout=300,
                   fast=2.0, growth=1.5, cap=15.0):
        """Synchronous exponential-backoff poll for pipeline stages (worker context)."""
        deadline = time.time() + timeout
        interval = fast
        while time.time() < deadline:
            try:
                result = provider.poll(task_id, kind)
            except Exception:
                result = None
            if result is not None:
                if result.state == "succeeded":
                    return result, None
                if result.state == "failed":
                    return None, result.error or "provider reported failure"
            time.sleep(interval)
            interval = min(cap, interval * growth)
        return None, "stage timeout"

    def _run_character_pipeline(self, job):
        from clawteam.media.characters import CharacterStore
        params = job.get("params") or {}
        source_url = params.get("source_url") or ""
        name = params.get("name") or "character"
        if not source_url.startswith("https://"):
            self.jobs.update(job["id"], state="failed",
                             error="character creation needs a public https photo URL")
            return
        stages = job.get("_stages") or []
        current = len([s for s in stages if s.get("status") == "done"])

        cid = job.get("_character_id")
        if not cid:
            try:
                rec = CharacterStore().new(name=name, source_url=source_url,
                                           notes=params.get("notes", ""),
                                           source_asset_id=params.get("source_asset_id"))
                cid = rec["id"]
            except ValueError as e:
                self.jobs.update(job["id"], state="failed", error=str(e))
                return

        self.jobs.update(job["id"], state="running", _character_id=cid)
        provider = self.cloud
        if not provider.health()["ok"]:
            self.jobs.update(job["id"], state="failed",
                             error="cloud unavailable: " + str(provider.health().get("detail")))
            return

        # Resume an in-flight stage by re-polling its provider task (no resubmit,
        # no double charge) — mirrors the download-recovery law.
        if stages and stages[-1].get("status") == "running" and stages[-1].get("task_id"):
            inflight = stages[-1]
            result, error = self._poll_sync(provider, inflight["task_id"], "edit")
            if error:
                self.jobs.update(job["id"], state="failed",
                                 error="stage " + inflight["name"] + ": " + str(error))
                return
            output_url = (result.output_urls or [None])[0]
            if not output_url:
                self.jobs.update(job["id"], state="failed",
                                 error="stage " + inflight["name"] + ": no output URL")
                return
            try:
                data, ext = provider.download(output_url)
                asset = self.assets.save(data, kind="image", source_url=output_url,
                                         job_id=job["id"], ext=ext)
            except Exception as e:
                self.jobs.update(job["id"], state="failed",
                                 error="stage " + inflight["name"] + " download: " + str(e))
                return
            stages = stages[:-1] + [{"name": inflight["name"], "status": "done",
                                    "task_id": inflight["task_id"], "output_url": output_url,
                                    "asset_id": asset["id"],
                                    "credits": result.actual_credits or 0.0}]
            self.jobs.update(job["id"], _stages=stages)
            current = len([s for s in stages if s.get("status") == "done"])

        input_url = source_url
        total_credits = 0.0
        for idx, (stage_name, prompt) in enumerate(self.CHARACTER_STAGES):
            if idx < current:
                s = stages[idx]
                input_url = s.get("output_url") or source_url
                total_credits += s.get("credits") or 0.0
                continue
            stage_job = {"kind": "edit", "prompt": prompt, "negative": "",
                         "params": {}, "model": "flux1-kontext"}
            try:
                with self._cloud_lock:
                    wait = CLOUD_MIN_SUBMIT_SPACING - (time.time() - self._last_cloud_submit)
                    if wait > 0:
                        time.sleep(wait)
                    task_id, _stage_model = provider.submit(stage_job, [input_url])
                    self._last_cloud_submit = time.time()
            except Exception as e:
                self.jobs.update(job["id"], state="failed", error="stage " + stage_name + " submit: " + str(e))
                return
            self.jobs.update(job["id"], _stages=stages + [{"name": stage_name, "status": "running", "task_id": task_id}])
            result, error = self._poll_sync(provider, task_id, "edit")
            if error:
                self.jobs.update(job["id"], state="failed", error="stage " + stage_name + ": " + str(error))
                return
            output_url = (result.output_urls or [None])[0]
            if not output_url:
                self.jobs.update(job["id"], state="failed", error="stage " + stage_name + ": no output URL")
                return
            try:
                data, ext = provider.download(output_url)
                asset = self.assets.save(data, kind="image", source_url=output_url,
                                         job_id=job["id"], ext=ext)
            except Exception as e:
                self.jobs.update(job["id"], state="failed", error="stage " + stage_name + " download: " + str(e))
                return
            stages = stages + [{"name": stage_name, "status": "done", "task_id": task_id,
                                "output_url": output_url, "asset_id": asset["id"],
                                "credits": result.actual_credits or 0.0}]
            total_credits += result.actual_credits or 0.0
            input_url = output_url
            self.jobs.update(job["id"], _stages=stages)

        CharacterStore().attach_canonical(cid, asset_id=stages[-1]["asset_id"],
                                          url=stages[-1]["output_url"], job_id=job["id"])
        self.jobs.update(job["id"], state="succeeded",
                         provider=self.cloud.name, model="flux1-kontext",
                         output_asset_ids=[s["asset_id"] for s in stages],
                         cost_actual_credits=round(total_credits, 4),
                         cost_actual_usd=round(total_credits * 0.005, 6),
                         cost_estimate_credits=10.0, cost_estimate_usd=0.05,
                         pricing_table_version=getattr(self.cloud, "PRICING_VERSION", ""),
                         completed_at=time.strftime("%Y-%m-%dT%H:%M:%S"))

    def _submit(self, job: dict) -> None:
        plan = self.plan(job)
        if plan.get("error"):
            self.jobs.update(job["id"], state="failed", error="routing: " + plan["error"])
            return
        provider = self.local if plan["provider"] == self.local.name else self.cloud
        try:
            if provider is self.cloud:
                with self._cloud_lock:
                    wait = CLOUD_MIN_SUBMIT_SPACING - (time.time() - self._last_cloud_submit)
                    if wait > 0:
                        time.sleep(wait)
                    if provider is self.cloud:
                        task_id, model = provider.submit(job, self._input_urls(job))
                        self._last_cloud_submit = time.time()
            else:
                task_id = provider.submit(job, [])
                model = plan.get("model")
            est = plan.get("estimate") or {}
            self.jobs.update(
                job["id"], state="running", provider=provider.name, model=model,
                provider_task_id=task_id, submitted_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                cost_estimate_credits=est.get("credits"), cost_estimate_usd=est.get("usd"),
                pricing_table_version=est.get("pricing_table_version"),
                seed=job.get("seed"),
            )
        except Exception as e:
            self.jobs.update(job["id"], state="failed", error=f"submit: {e}")

    def _advance(self, job: dict, poll: bool) -> None:
        provider = self.local if job.get("provider") == self.local.name else self.cloud
        timeout = KIND_TIMEOUT_SECONDS.get(job["kind"], 600)
        submitted = job.get("submitted_at")
        if submitted and time.mktime(time.strptime(submitted, "%Y-%m-%dT%H:%M:%S")) + timeout < time.time():
            self.jobs.update(job["id"], state="timed_out",
                             error=f"exceeded {timeout}s budget for {job['kind']}")
            return
        if not poll:
            return
        # Exponential backoff: fast window (2s x N ticks), then x1.5 growth to a 30s cap.
        now = time.time()
        if now < float(job.get("_next_poll_at") or 0):
            return
        poll_count = int(job.get("_poll_count") or 0)
        interval = POLL_FAST_INTERVAL if poll_count < POLL_FAST_TICKS else min(
            POLL_MAX_INTERVAL, POLL_FAST_INTERVAL * (POLL_GROWTH ** (poll_count - POLL_FAST_TICKS + 1)))
        try:
            result: ProviderResult = provider.poll(job["provider_task_id"], job["kind"])
        except Exception as e:
            self.jobs.update(job["id"], provider_status=f"poll-error: {e}",
                             _poll_count=poll_count + 1,
                             _next_poll_at=now + interval)
            return  # transient poll failures leave the job running; timeout guards
        fields = {"provider_status": result.provider_status,
                  "_poll_count": poll_count + 1, "_next_poll_at": now + interval}
        if result.state == "succeeded":
            fields["state"] = "provider_succeeded"
            fields["_output_urls"] = result.output_urls
            if result.actual_credits is not None:
                fields["cost_actual_credits"] = result.actual_credits
                fields["cost_actual_usd"] = result.actual_usd
            self.jobs.update(job["id"], **fields)
            job.update(fields)
            self._download_outputs(job)
            return
        if result.state == "failed":
            fields.update(state="failed", error=result.error or "provider reported failure")
        self.jobs.update(job["id"], **fields)

    def _download_outputs(self, job: dict) -> None:
        provider = self.local if job.get("provider") == self.local.name else self.cloud
        urls = job.get("_output_urls")
        if urls is None:
            # Reconstructed after restart: re-poll once to recover the urls.
            try:
                result = provider.poll(job["provider_task_id"], job["kind"])
                urls = result.output_urls if result.state == "succeeded" else []
                if not urls:
                    return  # still running or lost; timeout gate will catch it
            except Exception:
                return
        self.jobs.update(job["id"], state="downloading")
        saved, errors = [], []
        for url in urls[:4]:
            try:
                data, ext = provider.download(url)
                record = self.assets.save(
                    data, kind="video" if job["kind"] in ("t2v", "i2v") else "image",
                    source_url=None if provider is self.local else url,
                    job_id=job["id"], ext=ext)
                saved.append(record["id"])
            except Exception as e:
                errors.append(str(e))
        if saved:
            from clawteam.media.characters import CharacterStore
            if job.get("kind") == "variant":
                cid = (job.get("params") or {}).get("character_id") or job.get("_character_id")
                if cid:
                    CharacterStore().add_variant(cid, asset_id=saved[0],
                                                 url=urls[0] if urls else "",
                                                 prompt=job.get("prompt", ""))
            if job.get("kind") == "i2v" and (job.get("params") or {}).get("character_id"):
                cid = job["params"]["character_id"]
                params = job.get("params") or {}
                CharacterStore().add_scene(cid, asset_id=saved[0],
                                           prompt=job.get("prompt", ""),
                                           source=params.get("source") or params.get("source_url") or "canonical")
            self.jobs.update(job["id"], state="succeeded",
                             output_asset_ids=saved, completed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                             error=("partial download: " + "; ".join(errors)) if errors else None)
        else:
            # Provider finished but we hold nothing — never silently lose this.
            self.jobs.update(job["id"], state="succeeded_provider_download_failed",
                             error="download failed: " + "; ".join(errors)[:300],
                             completed_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
