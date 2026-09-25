"""Reusable character records for the Multimedia Studio.

A character is a persistent identity built from a source photo:
- canonical stylized image (3D-look animated-film style, identity-preserving)
- variant images (poses / clothing / expressions / environments / angles)
- scene videos (animated shots of the canonical image or a variant)

This is Lane A (stylized 3D-looking imagery). It is NOT a true 3D mesh/asset —
true-3D providers attach later through the same provider boundary.

Storage: one JSON file per character under {data_dir}/media/characters/.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path

from clawteam.media.jobs import media_dir


def _characters_dir() -> Path:
    d = media_dir() / "characters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _atomic_write(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


class CharacterStore:
    def new(self, *, name: str, source_url: str, notes: str = "",
            source_asset_id: str | None = None) -> dict:
        if not re.fullmatch(r"[\w \-]{1,60}", name or ""):
            raise ValueError("invalid character name (letters, digits, space, dash)")
        if not source_url.startswith("https://"):
            raise ValueError("source_url must be a public https URL the provider can fetch")
        rec = {
            "id": f"chr-{int(time.time())}-{uuid.uuid4().hex[:8]}",
            "name": name,
            "notes": notes,
            "source_url": source_url,
            "source_asset_id": source_asset_id,
            "canonical_asset_id": None,
            "canonical_url": None,        # provider URL (expires; canonical asset is the durable copy)
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "job_id": None,               # creating pipeline job
            "variants": [],               # [{asset_id, url, prompt, created_at}]
            "scenes": [],                 # [{asset_id, prompt, source, created_at}]
        }
        self.save(rec)
        return rec

    def _path(self, cid: str) -> Path:
        if "/" in cid or "\\" in cid or ".." in cid:
            raise ValueError("invalid character id")
        return _characters_dir() / f"{cid}.json"

    def save(self, rec: dict) -> None:
        _atomic_write(self._path(rec["id"]), rec)

    def get(self, cid: str) -> dict | None:
        try:
            return json.loads(self._path(cid).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def list(self, limit: int = 100) -> list[dict]:
        out = []
        for p in sorted(_characters_dir().glob("chr-*.json"), reverse=True)[:limit]:
            try:
                out.append(json.loads(p.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        out.sort(key=lambda c: c.get("created_at", ""), reverse=True)
        return out

    def update(self, cid: str, **fields) -> dict | None:
        rec = self.get(cid)
        if rec is None:
            return None
        rec.update(fields)
        self.save(rec)
        return rec

    def add_variant(self, cid: str, *, asset_id: str, url: str, prompt: str) -> dict | None:
        rec = self.get(cid)
        if rec is None:
            return None
        rec.setdefault("variants", []).append({
            "asset_id": asset_id, "url": url, "prompt": prompt,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        self.save(rec)
        return rec

    def add_scene(self, cid: str, *, asset_id: str, prompt: str, source: str) -> dict | None:
        rec = self.get(cid)
        if rec is None:
            return None
        rec.setdefault("scenes", []).append({
            "asset_id": asset_id, "prompt": prompt, "source": source,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
        self.save(rec)
        return rec

    def attach_canonical(self, cid: str, *, asset_id: str, url: str, job_id: str | None = None) -> dict | None:
        rec = self.get(cid)
        if rec is None:
            return None
        rec["canonical_asset_id"] = asset_id
        rec["canonical_url"] = url
        if job_id:
            rec["job_id"] = job_id
        self.save(rec)
        return rec