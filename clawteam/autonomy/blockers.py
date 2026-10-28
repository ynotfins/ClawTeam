"""Blocker Card writer + Board listing (AUTONOMY_POLICY §3).

An Absolute Blocker never pauses the swarm: the card is written, the owner is
batched a notification, and the item ships in its stated default state.
Cards live at `<repo>/.clawteam-local/runs/<run>/blockers/<B-nnn>.md` with a
machine-readable `index.json` beside them.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from clawteam.autonomy.decide import AutonomyError, run_dir
from clawteam.autonomy.models import BlockerRecord
from clawteam.paths import validate_identifier

_CARD_TEMPLATE = """# BLOCKER {id} — {title}

Needed from owner: {needed_from_owner}
Why impossible otherwise: {why_impossible}
Work continuing meanwhile: {work_continuing}
Default if no reply by SHIP: {ship_default}
"""


def blockers_dir(repo_root: Path, run: str) -> Path:
    return run_dir(repo_root, run) / "blockers"


def index_path(repo_root: Path, run: str) -> Path:
    return blockers_dir(repo_root, run) / "index.json"


def _load_index(repo_root: Path, run: str) -> dict:
    path = index_path(repo_root, run)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"next": 1, "cards": {}}


def _save_index(repo_root: Path, run: str, data: dict) -> None:
    path = index_path(repo_root, run)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(path))


def write_blocker(
    repo_root: Path,
    run: str,
    title: str,
    needed_from_owner: str,
    why_impossible: str,
    work_continuing: str = "",
    ship_default: str = "",
) -> BlockerRecord:
    """Write one Blocker Card (§3) and register it in the index.

    `why_impossible` must carry the evidence for (a)+(b)+(c); the caller
    (an agent that already tried repo search, memory, docs, and the benchmark)
    supplies it — this writer never blocks on a human.
    """
    if not title or not needed_from_owner or not why_impossible:
        raise AutonomyError("a Blocker Card needs title + needed_from_owner + why_impossible")

    index = _load_index(repo_root, run)
    n = int(index.get("next", 1))
    bid = f"B-{n:03d}"

    record = BlockerRecord(
        id=bid,
        run=validate_identifier(run, "run id"),
        title=title,
        needed_from_owner=needed_from_owner,
        why_impossible=why_impossible,
        work_continuing=work_continuing,
        ship_default=ship_default,
        ts=datetime.now(timezone.utc).isoformat(),
    )

    card = blockers_dir(repo_root, run) / f"{bid}.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(
        _CARD_TEMPLATE.format(
            id=bid,
            title=title,
            needed_from_owner=needed_from_owner,
            why_impossible=why_impossible,
            work_continuing=work_continuing or "all other lanes (swarm never pauses)",
            ship_default=ship_default or "feature ships disabled/dormant",
        ),
        encoding="utf-8",
    )

    index["next"] = n + 1
    cards = index.get("cards", {})
    cards[bid] = json.loads(record.model_dump_json())
    index["cards"] = cards
    _save_index(repo_root, run, index)
    return record


def list_blockers(repo_root: Path, run: str) -> list[BlockerRecord]:
    """All blocker cards for a run (id order). Never raises on bad state."""
    index = _load_index(repo_root, run)
    out: list[BlockerRecord] = []
    for bid in sorted(index.get("cards", {})):
        try:
            out.append(BlockerRecord.model_validate(index["cards"][bid]))
        except Exception:
            continue
    return out


def mark_notified(repo_root: Path, run: str, ids: list[str] | None = None) -> int:
    """Stamp `notified_at` on cards (batched notification ≥15 min apart).

    With `ids=None`, stamps every card that has never been notified.
    Returns the number of cards stamped (0 = nothing was due).
    """
    index = _load_index(repo_root, run)
    cards = index.get("cards", {})
    now = datetime.now(timezone.utc).isoformat()
    stamped = 0
    for bid, data in cards.items():
        if ids is not None and bid not in ids:
            continue
        if ids is None and data.get("notified_at"):
            continue  # batch rule: only never-notified cards stamp by default
        data["notified_at"] = now
        stamped += 1
    if stamped:
        _save_index(repo_root, run, index)
    return stamped


def pending_notification(repo_root: Path, run: str, min_age_minutes: float = 15.0) -> list[BlockerRecord]:
    """Cards whose last notification is older than the batch window (or never sent)."""
    now = datetime.now(timezone.utc)
    out: list[BlockerRecord] = []
    for card in list_blockers(repo_root, run):
        if not card.notified_at:
            out.append(card)
            continue
        try:
            sent = datetime.fromisoformat(card.notified_at)
            age = (now - sent).total_seconds() / 60.0
            if age >= min_age_minutes:
                out.append(card)
        except ValueError:
            out.append(card)
    return out