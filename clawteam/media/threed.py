"""3D character pipeline — photo(s) -> rigged, movie-ready character (D-017).

Stage machine over the existing job store (mirrors the character pipeline):
    prep (optional rembg) -> generate (tripo3d/h3.1 image-to-3d, detailed
    quality, PBR) -> rig (fal-ai/meshy/rigging + walking animation) ->
    forensic QA (OpenRouter gemini-2.5-pro: source vs preview; auto-heal =
    one regeneration with the Hunyuan fallback) -> attach.

Family-friendly by design: one photo is enough; progress lives in the Jobs
tab; the finished character appears in Characters with its rig preview as
the canonical image, so "Make a Movie" flows through the existing KIE
image-to-video lane unchanged.
"""

from __future__ import annotations

import time

from clawteam.media.providers.fal import (
    FALLBACK_TO3D_MODEL,
    FalError,
    FalProvider,
    ADAPTERS,
)

QA_MAX_ATTEMPTS = 2  # first generation + one auto-heal regeneration


class ThreeDError(Exception):
    pass


class ThreeDPipeline:
    """Runs inside the media worker tick; synchronous, resumable per stage."""

    def __init__(self, router):
        self.router = router
        self.jobs = router.jobs
        self.assets = router.assets
        self.fal: FalProvider = getattr(router, "fal", None) or FalProvider()

    # ------------------------------------------------------------------
    # Entry
    # ------------------------------------------------------------------

    def run(self, job: dict) -> None:
        state = job.get("_3d") or {}
        params = job.get("params") or {}
        source = state.get("source_url") or params.get("source_url") or ""
        if not source and params.get("source_urls"):
            source = str(params["source_urls"][0])
        if not source.startswith("https://"):
            self.jobs.update(job["id"], state="failed",
                             error="3D creation needs a public https photo link")
            return
        state.setdefault("source_url", source)
        state.setdefault("attempts", 0)
        state.setdefault("character_id", "")

        if not self.fal.health()["ok"]:
            self.jobs.update(job["id"], state="failed",
                             error="3D unavailable: " + str(self.fal.health().get("detail")))
            return

        self.jobs.update(job["id"], state="running", **{"_3d": state})

        try:
            # ---- stage: generate (with auto-heal fallback) ----------------
            outcome = state.get("generate")
            if not outcome:
                outcome = self._generate(job, state)
            if not outcome.get("model_url"):
                return  # _generate recorded the failure
            state["generate"] = outcome

            # ---- stage: rig ------------------------------------------------
            rig = state.get("rig")
            if not rig:
                rig = self._rig(job, state, outcome)
            if rig is None:
                return  # _rig recorded the failure; QA-less delivery still ok
            state["rig"] = rig

            # ---- stage: forensic QA (auto-heal once) ----------------------
            qa = self._qa(job, state, outcome)
            if qa is not None and not qa.get("pass") and int(state.get("attempts", 0)) < QA_MAX_ATTEMPTS - 1:
                state["generate"] = None   # auto-heal: regenerate once
                state["attempts"] = int(state.get("attempts", 0)) + 1
                self.jobs.update(job["id"], **{"_3d": state})
                return self.run(self.jobs.get(job["id"]))
            if qa is not None:
                state["qa"] = qa

            # ---- stage: attach to Characters + finish ---------------------
            self._attach(job, state, outcome, rig)
        except ThreeDError as e:
            self.jobs.update(job["id"], state="failed", error=str(e))
        except FalError as e:
            self.jobs.update(job["id"], state="failed", error=f"fal: {e}")

    # ------------------------------------------------------------------
    # Stages
    # ------------------------------------------------------------------

    def _generate(self, job: dict, state: dict) -> dict:
        """Image-to-3D. Returns {model_url, preview_url, task_ids, ...}."""
        model = (FALLBACK_TO3D_MODEL if state.get("attempts")
                 else (job.get("model") or "tripo3d/h3.1/image-to-3d"))
        step = {"kind": "to3d", "model": model, "params": job.get("params") or {}}
        ticket, used_model = self.fal.submit(step, [state["source_url"]])
        output, error = self.fal.client.wait_sync(ticket["status_url"],
                                                  ticket["response_url"],
                                                  timeout=900)
        if error:
            self.jobs.update(job["id"], state="failed",
                             error=f"generate({used_model}): {error}")
            return {}
        adapter = ADAPTERS[used_model]
        parsed = adapter.parse(output)
        model_url = (parsed["urls"] or [""])[0]
        preview_url = (parsed["previews"] or [""])[0]
        if not model_url:
            self.jobs.update(job["id"], state="failed",
                             error="generate: fal returned no model url")
            return {}

        # Persist the raw generation (GLB + preview) into the local library.
        out: dict = {"model_url": model_url, "preview_url": preview_url,
                     "task_ids": parsed["task_ids"], "model": used_model}
        try:
            data, ext = self.fal.client.download(model_url)
            asset = self.assets.save(data, kind="model3d", ext=ext,
                                     source_url=model_url, job_id=job["id"])
            out["model_asset_id"] = asset["id"]
            if preview_url:
                pdata, pext = self.fal.client.download(preview_url)
                passet = self.assets.save(pdata, kind="image", ext=pext,
                                          source_url=preview_url, job_id=job["id"])
                out["preview_asset_id"] = passet["id"]
        except Exception as e:
            self.jobs.update(job["id"], state="failed",
                             error=f"generate download: {e}")
            return {}
        return out

    def _rig(self, job: dict, state: dict, outcome: dict) -> dict | None:
        """Meshy humanoid rigging (+ walking clip) on the public GLB url."""
        if not outcome.get("model_url"):
            return None
        step = {"kind": "rig3d", "model": "fal-ai/meshy/rigging",
                "params": job.get("params") or {}}
        try:
            ticket, used = self.fal.submit(step, [outcome["model_url"]])
            output, error = self.fal.client.wait_sync(ticket["status_url"],
                                                      ticket["response_url"],
                                                      timeout=900)
        except FalError as e:
            # Rigging failure is not fatal: deliver the unrigged model,
            # record why, keep the family flow moving.
            self.jobs.update(job["id"], provider_status=f"rig skipped: {e}")
            return {"skipped": True, "reason": str(e)}
        if error:
            self.jobs.update(job["id"], provider_status=f"rig skipped: {error}")
            return {"skipped": True, "reason": str(error)}
        parsed = ADAPTERS[used].parse(output)
        rig_url = (parsed["urls"] or [""])[0]
        out: dict = {"rigged_url": rig_url, "task_ids": parsed["task_ids"]}
        if rig_url:
            try:
                data, ext = self.fal.client.download(rig_url)
                asset = self.assets.save(data, kind="model3d", ext=ext,
                                         source_url=rig_url, job_id=job["id"])
                out["rigged_asset_id"] = asset["id"]
            except Exception as e:
                out["download_error"] = str(e)
        return out

    def _qa(self, job: dict, state: dict, outcome: dict) -> dict | None:
        """Forensic vision QA; None when dormant (deliver with a note)."""
        from clawteam.media.providers.openrouter_qa import QaError, qa_available, vision_qa
        source = state.get("source_url", "")
        preview = outcome.get("preview_url", "")
        if not qa_available() or not preview:
            return None
        try:
            verdict = vision_qa(source, preview)
            self.jobs.update(job["id"], provider_status=
                             f"qa: {'pass' if verdict['pass'] else 'fail'} "
                             f"({verdict.get('severity', 'none')})")
            return verdict
        except QaError as e:
            # QA unavailable mid-run never blocks delivery (family-first).
            self.jobs.update(job["id"], provider_status=f"qa skipped: {e}")
            return None

    def _attach(self, job: dict, state: dict, outcome: dict, rig: dict) -> None:
        """Register the character; rig preview = canonical (movie-ready)."""
        from clawteam.media.characters import CharacterStore
        params = job.get("params") or {}
        name = params.get("name") or "character"
        cid = state.get("character_id")
        if not cid:
            rec = CharacterStore().new(name=name, source_url=state["source_url"],
                                       notes="3D digital double",
                                       source_asset_id=params.get("source_asset_id"))
            cid = rec["id"]
        canonical = outcome.get("preview_url") or state["source_url"]
        CharacterStore().attach_canonical(
            cid, asset_id=outcome.get("preview_asset_id") or "",
            url=canonical, job_id=job["id"])
        state["character_id"] = cid

        outputs = [a for a in (
            outcome.get("model_asset_id"),
            outcome.get("preview_asset_id"),
            rig.get("rigged_asset_id"),
        ) if a]
        self.jobs.update(
            job["id"], state="succeeded",
            provider=self.fal.name, model=outcome.get("model", ""),
            output_asset_ids=outputs,
            cost_actual_usd=(self.fal.estimate("to3d", outcome.get("model", ""),
                                               params).get("usd")),
            completed_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            error=None, **{"_3d": state})