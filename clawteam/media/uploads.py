"""Self-hosted temporary photo links for the Characters workflow.

Operator decision 2026-09-26 (option b): personal photos get into the
character pipeline through a temporary public https link on the operator's
own domain (cloudflared tunnel -> photohost), never a third-party host.

Storage: one binary + one JSON sidecar per upload under
{data_dir}/media/uploads/. File names carry an unguessable token
(pho-<epoch>-<uuid8>.<ext>) so the public link is capability-style.
Links auto-expire (configurable TTL, default 24h): reads past the
expiry fail closed and a background sweep deletes expired files.

Machine-local config (no secrets): {data_dir}/media/photohost.json
{"public_origin": "https://photos.example.com", "port": 18790, "ttl_hours": 24}
Override the file location with CLAWTEAM_PHOTOHOST_FILE (tests).
"""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path

from clawteam.media.jobs import media_dir

# What the public lane may ever serve: still images only.
ALLOWED_EXT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".png": "image/png", ".webp": "image/webp"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # matches the board-side cap
DEFAULT_TTL_HOURS = 24.0
DEFAULT_PORT = 18790

# pho-<epoch-seconds>-<8+ hex>.<ext> — the photohost serves exactly this shape.
TOKEN_RE = re.compile(r"^pho-\d{10,}-[0-9a-f]{8,}$")

# Magic bytes per allowed type — an upload must actually be the image it claims.
_MAGIC = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG",),
    ".webp": (b"RIFF",),  # + WEBP at offset 8, checked in _sniffs_as
}


def _sniffs_as(data: bytes, ext: str) -> bool:
    for magic in _MAGIC.get(ext, ()):
        if data.startswith(magic):
            if ext == ".webp" and data[8:12] != b"WEBP":
                return False
            return True
    return False


def photohost_config() -> dict:
    """Load machine-local photohost config (public origin / port / TTL)."""
    import os
    path = Path(os.environ.get("CLAWTEAM_PHOTOHOST_FILE", "")) \
        if os.environ.get("CLAWTEAM_PHOTOHOST_FILE") else media_dir() / "photohost.json"
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    return {
        "public_origin": str(cfg.get("public_origin", "")).rstrip("/"),
        "port": int(cfg.get("port", DEFAULT_PORT)),
        "ttl_hours": float(cfg.get("ttl_hours", DEFAULT_TTL_HOURS)),
    }


def uploads_dir() -> Path:
    d = media_dir() / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


class UploadStore:
    """Token-named photo files with expiry; the public link is the token."""

    def __init__(self, ttl_hours: float | None = None):
        cfg = photohost_config()
        self.ttl_hours = DEFAULT_TTL_HOURS if ttl_hours is None else float(ttl_hours)
        self.public_origin = cfg["public_origin"]

    # ---- save -------------------------------------------------------------
    def save(self, data: bytes, *, ext: str, original_name: str = "") -> dict:
        if not data:
            raise ValueError("empty upload")
        if len(data) > MAX_UPLOAD_BYTES:
            raise ValueError(f"upload exceeds {MAX_UPLOAD_BYTES // (1024 * 1024)} MB cap")
        ext = ext if ext.startswith(".") else "." + ext
        ext = ext.lower()
        if ext not in ALLOWED_EXT:
            raise ValueError(f"unsupported image type {ext} (allowed: {', '.join(sorted(ALLOWED_EXT))})")
        if not _sniffs_as(data, ext):
            raise ValueError("file content does not match a supported image format")
        token = f"pho-{int(time.time())}-{uuid.uuid4().hex[:12]}"
        binary = uploads_dir() / f"{token}{ext}"
        tmp = binary.with_suffix(".tmp")
        tmp.write_bytes(data)
        import os
        os.replace(tmp, binary)
        created = time.time()
        record = {
            "token": token,
            "ext": ext,
            "mime": ALLOWED_EXT[ext],
            "bytes": len(data),
            "original_name": (original_name or "")[:120],
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(created)),
            "expires_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(created + self.ttl_hours * 3600)),
            "_expires_epoch": created + self.ttl_hours * 3600,
        }
        sidecar = uploads_dir() / f"{token}.json"
        tmp = sidecar.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, sidecar)
        return self.public_view(record)

    # ---- read -------------------------------------------------------------
    def _record(self, token: str) -> dict | None:
        if not TOKEN_RE.fullmatch(token or ""):
            return None
        try:
            rec = json.loads((uploads_dir() / f"{token}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        return rec

    def get(self, token: str) -> dict | None:
        """Live (unexpired) record, or None. Expired reads fail closed."""
        rec = self._record(token)
        if rec is None:
            return None
        if float(rec.get("_expires_epoch", 0)) <= time.time():
            return None
        return rec

    def read_bytes(self, token: str) -> tuple[dict, bytes] | None:
        rec = self.get(token)
        if rec is None:
            return None
        try:
            return rec, (uploads_dir() / f"{rec['token']}{rec['ext']}").read_bytes()
        except OSError:
            return None

    def expired(self, token: str) -> bool:
        """True when the record exists but its TTL has passed."""
        rec = self._record(token)
        return rec is not None and float(rec.get("_expires_epoch", 0)) <= time.time()

    def file_path(self, token: str) -> Path | None:
        rec = self.get(token)
        if rec is None:
            return None
        p = uploads_dir() / f"{rec['token']}{rec['ext']}"
        # Containment guard: the resolved path must stay inside uploads_dir.
        try:
            p.resolve().relative_to(uploads_dir().resolve())
        except ValueError:
            return None
        return p if p.is_file() else None

    # ---- expiry sweep -----------------------------------------------------
    def sweep(self) -> int:
        """Delete every expired upload (binary + sidecar). Returns count."""
        import os
        removed = 0
        now = time.time()
        for sidecar in uploads_dir().glob("pho-*.json"):
            try:
                rec = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if float(rec.get("_expires_epoch", 0)) <= now:
                binary = uploads_dir() / f"{rec.get('token', '')}{rec.get('ext', '')}"
                for p in (sidecar, binary):
                    try:
                        if p.is_file():
                            os.unlink(p)
                    except OSError:
                        pass
                removed += 1
        return removed

    # ---- list / delete ----------------------------------------------------
    def list(self, limit: int = 50) -> list[dict]:
        out = []
        for sidecar in sorted(uploads_dir().glob("pho-*.json"), reverse=True)[:limit]:
            try:
                rec = json.loads(sidecar.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if float(rec.get("_expires_epoch", 0)) <= time.time():
                continue
            out.append(self.public_view(rec))
        out.sort(key=lambda u: u.get("created_at", ""), reverse=True)
        return out

    def delete(self, token: str) -> bool:
        import os
        rec = self._record(token)
        if rec is None:
            return False
        removed = False
        for p in (uploads_dir() / f"{token}.json",
                  uploads_dir() / f"{token}{rec.get('ext', '')}"):
            try:
                if p.is_file():
                    os.unlink(p)
                    removed = True
            except OSError:
                pass
        return removed

    # ---- URL shapes -------------------------------------------------------
    def public_url(self, record: dict) -> str | None:
        """https link the provider fetches, or None when no origin is configured."""
        if not self.public_origin:
            return None
        return f"{self.public_origin}/{record['token']}{record['ext']}"

    def public_view(self, record: dict) -> dict:
        """API shape: record + derived URLs, without internal epoch fields."""
        view = {k: v for k, v in record.items() if not k.startswith("_")}
        view["url"] = self.public_url(record)
        view["local_url"] = f"/api/media/uploads/{record['token']}/file"
        return view
