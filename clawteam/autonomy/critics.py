"""Critic loop — continuous scan triggers, findings, Judge triage (§4/§6).

Triggers (SWARM_TEAM_SPEC §4): (a) commits on any lane branch since the last
scan, (b) a timer (default 5 min), (c) phase change. Findings carry evidence
(file:line, failing test, command output) — "looks wrong" is rejected by the
Judge. Dedupe by fingerprint + cooldown keeps critics from noise loops.
State: `<repo>/.clawteam-local/runs/<run>/critic-state.json`.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from clawteam.autonomy.decide import AutonomyError, run_dir
from clawteam.workspace import git

CRITIC_INTERVAL_SECONDS = 300.0   # default timer trigger (5 min)
SEVERITIES = ("low", "medium", "high")
SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3}
TRIAGE_MIN_SEVERITY = "medium"    # findings < medium are dismissed as noise
FINDING_COOLDOWN_SECONDS = 1800.0  # same fingerprint within 30 min merges, not duplicates


def fingerprint_of(lane: str, message: str, evidence: str) -> str:
    """Stable fingerprint for dedupe: same defect re-filed merges into one."""
    h = hashlib.sha256()
    h.update(lane.encode("utf-8"))
    h.update(b"\x00")
    h.update(message.strip().encode("utf-8"))
    h.update(b"\x00")
    h.update(evidence.strip().encode("utf-8"))
    return h.hexdigest()[:16]


def _state_path(repo_root: Path, run: str) -> Path:
    return run_dir(repo_root, run) / "critic-state.json"


def _load_state(repo_root: Path, run: str) -> dict:
    path = _state_path(repo_root, run)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"last_scan": "", "scans": 0, "findings": {}}


def _save_state(repo_root: Path, run: str, state: dict) -> None:
    path = _state_path(repo_root, run)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(path))


def _now() -> datetime:
    return datetime.now(timezone.utc)


class CriticLoop:
    """Scan scheduling + finding registry + Judge triage for one run."""

    def __init__(self, repo_root: Path, run: str):
        self.repo_root = Path(repo_root)
        self.run = run
        self.state = _load_state(repo_root, run)

    # ------------------------------------------------------------------
    # Triggers
    # ------------------------------------------------------------------

    def due_timer(self, now: datetime | None = None) -> bool:
        """True when the timer trigger fires (>= interval since last scan)."""
        now = now or _now()
        last = self.state.get("last_scan")
        if not last:
            return True   # never scanned: due immediately
        try:
            last_dt = datetime.fromisoformat(last)
        except ValueError:
            return True
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return (now - last_dt).total_seconds() >= CRITIC_INTERVAL_SECONDS

    def lane_commits_since_last_scan(self, run: str) -> list[str]:
        """Commits on any `ship/<run>/lane/*` branch since the last scan.

        Empty list when no last-scan timestamp exists (first scan scans
        everything fresh — the commit trigger reports zero new commits).
        """
        last = self.state.get("last_scan")
        if not last:
            return []
        pattern = f"ship/{run}/lane/*"
        args = ["log", f"--since={last}", "--format=%h %s", "--branches=" + pattern]
        result = subprocess.run(["git", *args], cwd=self.repo_root,
                                capture_output=True, text=True)
        if result.returncode != 0:
            return []
        return [l for l in result.stdout.splitlines() if l.strip()]

    def needs_scan(self, run: str, now: datetime | None = None) -> dict:
        """Which triggers fire right now. A scan is due on any of them."""
        commits = self.lane_commits_since_last_scan(run)
        return {
            "timer": self.due_timer(now),
            "commits": len(commits),
            "commit_triggers": commits,
            "due": bool(self.due_timer(now) or commits),
        }

    def mark_scanned(self) -> None:
        self.state["last_scan"] = _now().isoformat()
        self.state["scans"] = int(self.state.get("scans", 0)) + 1
        _save_state(self.repo_root, self.run, self.state)

    # ------------------------------------------------------------------
    # Findings
    # ------------------------------------------------------------------

    def record_finding(
        self,
        lane: str,
        severity: str,
        message: str,
        evidence: str,
        *,
        critic: str = "critic-code",
        now: datetime | None = None,
    ) -> dict:
        """File one finding. Dedupes on fingerprint inside the cooldown.

        Evidence is mandatory — the Judge rejects "looks wrong" (§4).
        Returns the finding dict (new, or the merged duplicate with
        `count` incremented).
        """
        if severity not in SEVERITIES:
            raise AutonomyError(f"severity must be one of {SEVERITIES}")
        if not message.strip() or not evidence.strip():
            raise AutonomyError("a finding needs message + evidence (file:line or command output)")

        now = now or _now()
        fp = fingerprint_of(lane, message, evidence)
        findings = self.state.setdefault("findings", {})
        existing = None
        for f in findings.values():
            if f.get("fingerprint") == fp:
                existing = f
                break

        if existing is not None:
            last = datetime.fromisoformat(existing["ts"]) if existing.get("ts") else None
            if last and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            within = last is not None and (now - last).total_seconds() < FINDING_COOLDOWN_SECONDS
            if within:
                existing["count"] = int(existing.get("count", 1)) + 1
                existing["ts"] = now.isoformat()
                _save_state(self.repo_root, self.run, self.state)
                return existing

        fid = f"CF-{len(findings) + 1:03d}"
        finding = {
            "id": fid, "lane": lane, "severity": severity, "message": message.strip(),
            "evidence": evidence.strip(), "fingerprint": fp, "critic": critic,
            "ts": now.isoformat(), "status": "open", "count": 1,
        }
        findings[fid] = finding
        _save_state(self.repo_root, self.run, self.state)
        return finding

    def findings(self, status: str | None = None) -> list[dict]:
        out = [f for f in self.state.get("findings", {}).values()
               if status is None or f.get("status") == status]
        return sorted(out, key=lambda f: f["id"])

    # ------------------------------------------------------------------
    # Judge triage
    # ------------------------------------------------------------------

    def triage(self, min_severity: str = TRIAGE_MIN_SEVERITY) -> dict:
        """Judge rule: accept >= *min_severity* → route to the `debug` lane;
        lower severity is dismissed as noise (stays recorded, never deleted)."""
        accepted: list[dict] = []
        dismissed: list[dict] = []
        rank = SEVERITY_RANK.get(min_severity, 2)
        for f in self.state.get("findings", {}).values():
            if f.get("status") != "open":
                continue
            if SEVERITY_RANK.get(f.get("severity", "low"), 1) >= rank:
                f["status"] = "triaged"
                f["owner"] = "debug"
                accepted.append(f)
            else:
                f["status"] = "dismissed"
                dismissed.append(f)
        _save_state(self.repo_root, self.run, self.state)
        return {"accepted": accepted, "dismissed": dismissed,
                "route": {f["id"]: "debug" for f in accepted}}