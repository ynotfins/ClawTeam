"""Tier-0 local execution: ComfyUI on the RTX 4070 SUPER (loopback only).

Health-gated: reachable + checkpoint present + single-flight + safe kinds.
Read-only towards the ComfyUI install — auto-boot is the only side effect.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from clawteam.media.providers.base import ProviderResult

COMFYUI_PORT = int(os.environ.get("COMFYUI_PORT", "8188"))
COMFYUI_ROOT = Path(os.environ.get("COMFYUI_ROOT", r"D:\ComfyUI\ComfyUI_windows_portable"))
DEFAULT_CHECKPOINT = "RealVisXL_V5.0_fp16.safetensors"
LOCAL_SAFE_KINDS = {"t2img", "img2img"}

# Local jobs are synchronous-ish: one poll after the workflow completes; the
# poll loop reads ComfyUI history, so the same exponential-backoff worker
# drives local and cloud jobs uniformly.
KIND_TIMEOUT_SECONDS = {"t2img": 300, "img2img": 420, "edit": 300, "upscale": 600,
                        "t2v": 1200, "i2v": 1200}


class ComfyUiLocalProvider:
    name = "comfyui-local"
    _booted_this_session = False

    def capabilities(self) -> dict:
        return {
            "kinds": ["t2img", "img2img"],
            "models": [DEFAULT_CHECKPOINT],
            "limits": {"max_concurrent": 1, "vram_gb": 12},
            "cost": {"local": True, "credits": 0, "usd": 0.0},
        }

    # ---- gates -----------------------------------------------------------
    def _listening(self, timeout: float = 1.5) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", COMFYUI_PORT), timeout=timeout):
                return True
        except OSError:
            return False

    def _checkpoint_present(self) -> bool:
        return (COMFYUI_ROOT / "ComfyUI" / "models" / "checkpoints" / DEFAULT_CHECKPOINT).exists()

    def _ensure_booted(self) -> bool:
        if self._listening():
            return True
        if ComfyUiLocalProvider._booted_this_session:
            # One hidden auto-boot attempt per board session (non-destructive).
            return self._listening()
        ComfyUiLocalProvider._booted_this_session = True
        python = COMFYUI_ROOT / "python_embeded" / "python.exe"
        main = COMFYUI_ROOT / "ComfyUI" / "main.py"
        if not (python.exists() and main.exists()):
            return False
        subprocess.Popen(
            [str(python), "-s", str(main), "--listen", "127.0.0.1", "--port", str(COMFYUI_PORT)],
            cwd=str(COMFYUI_ROOT),
            stdout=open(COMFYUI_ROOT / "comfyui-bridge.log", "ab"),
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        deadline = time.time() + 90
        while time.time() < deadline:
            if self._listening():
                try:
                    self._api("/system_stats", timeout=5)
                    return True
                except Exception:
                    pass
            time.sleep(2)
        return False

    def health(self) -> dict:
        gates = {
            "reachable": self._listening() or self._ensure_booted(),
            "checkpoint": self._checkpoint_present(),
            "kind_safe": True,  # evaluated per-job by the router
        }
        ok = all(gates.values())
        detail = "local GPU ready" if ok else "; ".join(k for k, v in gates.items() if not v)
        return {"ok": ok, "detail": detail, "gates": gates}

    def estimate(self, kind: str, model: str, params: dict) -> dict:
        return {"credits": 0.0, "usd": 0.0, "pricing_table_version": "local/1",
                "verified": True, "note": "local GPU — no credit cost"}

    # ---- HTTP ------------------------------------------------------------
    def _api(self, path: str, payload: dict | None = None, timeout: int = 15):
        url = f"http://127.0.0.1:{COMFYUI_PORT}{path}"
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}

    # ---- workflow graphs (built in code; no workflow files mutated) -------
    def _workflow(self, job: dict) -> dict:
        p = job.get("params", {})
        seed = p.get("seed")
        if seed in (None, -1):
            seed = int.from_bytes(os.urandom(4), "little")
        job["seed"] = seed
        wf: dict = {
            "3": {"class_type": "KSampler", "inputs": {
                "seed": seed, "steps": int(p.get("steps", 25)), "cfg": float(p.get("cfg", 5.5)),
                "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": float(p.get("denoise", 1.0)),
                "model": ["4", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
            "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": p.get("checkpoint", DEFAULT_CHECKPOINT)}},
            "5": {"class_type": "EmptyLatentImage", "inputs": {
                "width": int(p.get("width", 1024)), "height": int(p.get("height", 1024)), "batch_size": 1}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": job.get("prompt", ""), "clip": ["4", 1]}},
            "7": {"class_type": "CLIPTextEncode", "inputs": {"text": job.get("negative", "blurry, low quality, watermark, text"), "clip": ["4", 1]}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
            "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "media", "images": ["8", 0]}},
        }
        return wf

    def submit(self, job: dict, input_asset_paths: list[str]) -> str:
        if job["kind"] not in LOCAL_SAFE_KINDS:
            raise ValueError(f"kind {job['kind']} not in the local-safe set")
        if not self.health()["ok"]:
            raise RuntimeError("ComfyUI local gates failed")
        wf = self._workflow(job)
        client_id = str(uuid.uuid4())
        wf["9"]["inputs"]["filename_prefix"] = f"media/{client_id[:8]}"
        result = self._api("/prompt", {"prompt": wf, "client_id": client_id})
        task_id = result.get("prompt_id")
        if not task_id:
            raise RuntimeError(f"ComfyUI rejected workflow: {result}")
        return task_id

    def poll(self, task_id: str, kind: str) -> ProviderResult:
        history = self._api(f"/history/{task_id}").get(task_id)
        if not history:
            return ProviderResult(state="running", provider_status="queuing")
        status = history.get("status", {})
        if status.get("status_str") == "error":
            return ProviderResult(state="failed", provider_status="error",
                                  error="ComfyUI execution error")
        outputs = history.get("outputs") or {}
        urls = []
        for node_out in outputs.values():
            for img in node_out.get("images", []):
                if img.get("type") == "output":
                    q = urllib.parse.quote
                    urls.append(f"/view?filename={q(img.get('filename',''))}"
                                f"&subfolder={q(img.get('subfolder',''))}&type=output")
        if not urls:
            return ProviderResult(state="running", provider_status="generating")
        return ProviderResult(state="succeeded", provider_status="success", output_urls=urls)

    def download(self, url: str) -> tuple[bytes, str]:
        with urllib.request.urlopen(f"http://127.0.0.1:{COMFYUI_PORT}{url}", timeout=60) as resp:
            return resp.read(), ".png"
