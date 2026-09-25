"""File-backed media job store (app-owned lifecycle).

One JSON file per job under {data_dir}/media/jobs/, atomic writes, cross-platform
advisory lock — mirrors clawteam/store/file.py conventions.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path

from clawteam.team.models import get_data_dir

# App-owned lifecycle states, independent of provider status vocabularies.
JOB_STATES = (
    "draft", "queued", "running", "provider_succeeded", "downloading",
    "succeeded", "failed", "timed_out", "succeeded_provider_download_failed",
)
TERMINAL_STATES = {"succeeded", "failed", "timed_out", "succeeded_provider_download_failed"}
ACTIVE_STATES = {"queued", "running", "provider_succeeded", "downloading"}

JOB_KINDS = ("t2img", "img2img", "edit", "t2v", "i2v", "upscale",
             "character", "variant")


def media_dir() -> Path:
    d = Path(get_data_dir()) / "media"
    d.mkdir(parents=True, exist_ok=True)
    return d


class _DirLock:
    def __init__(self, path: Path):
        self._path = path
        self._handle = None

    def __enter__(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self._path, "a+")
        try:
            import msvcrt
            while True:
                try:
                    msvcrt.locking(self._handle.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        except ImportError:
            import fcntl
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        try:
            import msvcrt
            msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
        except ImportError:
            import fcntl
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        self._handle.close()
        return False


def _atomic_write_json(path: Path, data: dict) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class MediaJobStore:
    def __init__(self, root: Path | None = None):
        self._root = Path(root) if root else media_dir()
        self._jobs = self._root / "jobs"
        self._jobs.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def new_job(self, kind: str, prompt: str, *, negative: str = "", params: dict | None = None,
                input_asset_ids: list[str] | None = None, route: str = "auto",
                requested_provider: str | None = None) -> dict:
        if kind not in JOB_KINDS:
            raise ValueError(f"unknown job kind: {kind}")
        job = {
            "id": f"job-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            "kind": kind,
            "prompt": prompt,
            "negative": negative,
            "params": params or {},
            "input_asset_ids": input_asset_ids or [],
            "output_asset_ids": [],
            "provider": None,
            "model": None,
            "route": route,
            "requested_provider": requested_provider,
            "state": "draft",
            "provider_task_id": None,
            "provider_status": None,
            "error": None,
            "cost_estimate_credits": None,
            "cost_estimate_usd": None,
            "cost_actual_credits": None,
            "cost_actual_usd": None,
            "pricing_table_version": None,
            "seed": None,
            "submitted_at": None,
            "completed_at": None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self.save(job)
        return job

    def _path(self, job_id: str) -> Path:
        if "/" in job_id or "\\" in job_id or ".." in job_id:
            raise ValueError("invalid job id")
        return self._jobs / f"{job_id}.json"

    def save(self, job: dict) -> None:
        job["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._lock:
            _atomic_write_json(self._path(job["id"]), job)

    def get(self, job_id: str) -> dict | None:
        try:
            return json.loads(self._path(job_id).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def update(self, job_id: str, **fields) -> dict | None:
        with self._lock:
            job = self.get(job_id)
            if job is None:
                return None
            job.update(fields)
            job["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            _atomic_write_json(self._path(job_id), job)
            return job

    def list(self, limit: int = 100) -> list[dict]:
        out = []
        for p in sorted(self._jobs.glob("job-*.json"), reverse=True)[:limit]:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        out.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return out

    def queue(self, job: dict) -> dict:
        return self.update(job["id"], state="queued")

    def lock_file(self) -> Path:
        return self._jobs / ".jobs.lock"
