"""Local asset registry + binary storage for generated media."""

from __future__ import annotations

import json
import mimetypes
import os
import tempfile
import time
import uuid
from pathlib import Path

from clawteam.media.jobs import media_dir

_MIME_BY_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp", ".mp4": "video/mp4", ".webm": "video/webm"}


class AssetStore:
    def __init__(self, root: Path | None = None):
        self._root = Path(root) if root else media_dir()
        self._assets = self._root / "assets"
        self._assets.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, *, kind: str, mime: str | None = None,
             source_url: str | None = None, job_id: str | None = None,
             ext: str = ".png") -> dict:
        asset_id = f"ast-{int(time.time())}-{uuid.uuid4().hex[:8]}"
        ext = ext if ext.startswith(".") else "." + ext
        if mime is None:
            mime = _MIME_BY_EXT.get(ext) or mimetypes.guess_type("x" + ext)[0] or "application/octet-stream"
        binary = self._assets / f"{asset_id}{ext}"
        fd, tmp = tempfile.mkstemp(dir=str(self._assets), suffix=".tmp")
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        os.replace(tmp, binary)
        record = {
            "id": asset_id,
            "kind": kind,
            "mime": mime,
            "bytes": len(data),
            "ext": ext,
            "file": str(binary),
            "source_url": source_url,
            "job_id": job_id,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        sidecar = self._assets / f"{asset_id}.json"
        tmp = sidecar.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2), encoding="utf-8")
        os.replace(tmp, sidecar)
        return record

    def get(self, asset_id: str) -> dict | None:
        if "/" in asset_id or "\\" in asset_id or ".." in asset_id:
            return None
        for p in self._assets.glob(f"{asset_id}.json"):
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return None
        return None

    def read_bytes(self, asset_id: str) -> bytes | None:
        record = self.get(asset_id)
        if record is None:
            return None
        try:
            return Path(record["file"]).read_bytes()
        except OSError:
            return None

    def list(self, limit: int = 200) -> list[dict]:
        out = []
        for p in sorted(self._assets.glob("ast-*.json"), reverse=True)[:limit]:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        out.sort(key=lambda a: a.get("created_at", ""), reverse=True)
        return out
