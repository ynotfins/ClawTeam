"""Stuck-task detection (AUTONOMY_POLICY §8) — reassign/respawn, never ask.

A task with no progress for N minutes (default 20) is *stalled*: the leader
reassigns it, respawning the owning agent with context recovery via the
existing keepalive/leader_watcher machinery. This module only *detects* and
names the action — the team watcher executes it.

Report: `<repo>/.clawteam-local/runs/<run>/stuck.json`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from clawteam.autonomy.decide import run_dir

STALLED_AFTER_MINUTES = 20.0      # N minutes without an updated_at bump
ACTIVE_STATUSES = ("pending", "in_progress")   # blocked tasks are their own state


def _report_path(repo_root: Path, run: str) -> Path:
    return run_dir(repo_root, run) / "stuck.json"


def _parse_iso(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def scan_stalled(
    repo_root: Path,
    run: str,
    team: str,
    *,
    task_store=None,
    now: datetime | None = None,
    stalled_after_minutes: float = STALLED_AFTER_MINUTES,
) -> dict:
    """Return the stall report for *team*'s active tasks.

    `task_store` defaults to the real store (`clawteam.team.tasks.TaskStore`)
    and is injectable for tests. Never raises on a bad timestamp — a task with
    an unparseable `updated_at` is reported as stalled (progress unknown).
    """
    now = now or datetime.now(timezone.utc)
    if task_store is None:
        from clawteam.team.tasks import TaskStore
        task_store = TaskStore(team)

    stalled: list[dict] = []
    for t in task_store.list_tasks():
        status = getattr(getattr(t, "status", None), "value", "") or str(getattr(t, "status", ""))
        if status not in ACTIVE_STATUSES:
            continue   # completed/blocked/failed tasks are not "stuck work"
        updated = _parse_iso(getattr(t, "updated_at", "") or "")
        minutes: float | None = None
        if updated is not None:
            minutes = (now - updated).total_seconds() / 60.0
        if minutes is not None and minutes < stalled_after_minutes:
            continue
        stalled.append({
            "task": str(getattr(t, "id", "")),
            "subject": str(getattr(t, "subject", ""))[:80],
            "owner": str(getattr(t, "owner", "")),
            "status": status,
            "minutes_since_update": None if minutes is None else round(minutes, 1),
            "action": "respawn" if status == "in_progress" else "reassign",
        })

    report = {
        "run": run,
        "team": team,
        "checked_at": now.isoformat(),
        "stalled_after_minutes": stalled_after_minutes,
        "stalled": stalled,
        "prompt": {
            "reassign": [s["task"] for s in stalled if s["action"] == "reassign"],
            "respawn": [s["task"] for s in stalled if s["action"] == "respawn"],
        },
    }

    path = _report_path(repo_root, run)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(path))
    return report