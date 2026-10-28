"""WP3 — critic loop, governors, stuck detection.

Throwaway state: fresh git repo per test under pytest `tmp_path`,
`CLAWTEAM_STAGE_ROOT` sandboxed, fake task store injected for stuck scans.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clawteam.autonomy import (
    ACTIVE_STATUSES,
    CRITIC_INTERVAL_SECONDS,
    AutonomyError,
    CriticLoop,
    FINDING_COOLDOWN_SECONDS,
    Governor,
    ForkController,
    fingerprint_of,
    scan_stalled,
)
from clawteam.cli.commands import app
from clawteam.stage import StageManager

runner = CliRunner()

RUN = "ship-wp301"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, f"git {args}: {result.stderr}"
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "clawteam-test")
    (repo / "README.md").write_text("temp repo\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "init")
    monkeypatch.setenv("CLAWTEAM_STAGE_ROOT", str(tmp_path / "w"))
    return repo


# ---------------------------------------------------------------------------
# Governor (§7)
# ---------------------------------------------------------------------------


class TestGovernor:
    def test_pro_and_simple_defaults(self, repo: Path):
        pro = Governor(repo, RUN, mode="pro")
        simple = Governor(repo, RUN + "s", mode="simple")
        assert pro.state["budgets"]["wall_clock_hours"] == 6.0
        assert simple.state["budgets"]["wall_clock_hours"] == 45 / 60
        assert pro.state["budgets"]["concurrent_agents"] == 8
        assert simple.state["budgets"]["concurrent_agents"] == 5

    def test_record_and_soft_stop_then_wrap_up(self, repo: Path):
        gov = Governor(repo, RUN, mode="pro")
        gov.set_budget("kie_credits", 100)
        assert gov.should_soft_stop() is False
        gov.record("kie_credits", 80)               # 80 % → soft-stop edge
        assert gov.should_soft_stop() is True       # >= 80 %
        assert gov.should_wrap_up() is False
        with pytest.raises(AutonomyError, match="no new forks"):
            gov.check_fork()
        gov.record("kie_credits", 21)               # 100 %
        assert gov.should_wrap_up() is True
        with pytest.raises(AutonomyError, match="wrap-up"):
            gov.check_fork()

    def test_uncapped_kinds_never_trip(self, repo: Path):
        gov = Governor(repo, RUN, mode="pro")
        assert gov.usage("llm_tokens") is None      # owner-set only
        gov.record("llm_tokens", 10_000_000)
        assert gov.should_soft_stop() is False

    def test_gauge_kinds_are_set_not_summed(self, repo: Path):
        gov = Governor(repo, RUN, mode="simple")
        gov.set_budget("open_experiments", 1)
        gov.set_used("open_experiments", 1)
        assert gov.should_wrap_up() is True         # 1/1 = 100 %
        gov.set_used("open_experiments", 0)
        assert gov.should_wrap_up() is False

    def test_governor_gates_fork_controller(self, repo: Path):
        mgr = StageManager(repo)
        gov = Governor(repo, RUN, mode="pro")
        gov.set_budget("kie_credits", 10)
        gov.record("kie_credits", 9)                # 90 % → soft-stop
        controller = ForkController(mgr, governor=gov)
        with pytest.raises(AutonomyError, match="governor"):
            controller.create_fork_pair(RUN, "F-G", "q", "a", "b")
        # without a governor the same fork opens fine
        ForkController(mgr).create_fork_pair(RUN, "F-G2", "q", "a", "b")


# ---------------------------------------------------------------------------
# Critic loop (§4)
# ---------------------------------------------------------------------------


class TestCriticLoop:
    def test_timer_trigger_default_5min(self, repo: Path):
        loop = CriticLoop(repo, RUN)
        assert loop.due_timer() is True             # never scanned
        past = datetime.now(timezone.utc) - timedelta(seconds=CRITIC_INTERVAL_SECONDS + 1)
        loop.state["last_scan"] = past.isoformat()
        assert loop.due_timer() is True
        recent = datetime.now(timezone.utc)
        loop.state["last_scan"] = recent.isoformat()
        assert loop.due_timer() is False

    def test_commit_trigger_sees_lane_commits(self, repo: Path):
        mgr = StageManager(repo)
        mgr.create_lane(RUN, "qa")
        wt = Path(mgr.list_stages(RUN)[-1].worktree_path)
        (wt / "change.txt").write_text("x", encoding="utf-8")
        _git(wt, "add", "-A")
        _git(wt, "commit", "-m", "qa work")

        loop = CriticLoop(repo, RUN)
        loop.mark_scanned()
        # a brand-new lane commit after the scan shows up as a trigger
        (wt / "change2.txt").write_text("y", encoding="utf-8")
        _git(wt, "add", "-A")
        _git(wt, "commit", "-m", "qa work 2")
        needs = loop.needs_scan(RUN)
        assert needs["commits"] >= 1
        assert needs["due"] is True

    def test_finding_requires_evidence(self, repo: Path):
        loop = CriticLoop(repo, RUN)
        with pytest.raises(AutonomyError, match="message \\+ evidence"):
            loop.record_finding("qa", "high", "looks wrong", "  ")

    def test_fingerprint_dedupe_within_cooldown(self, repo: Path):
        loop = CriticLoop(repo, RUN)
        now = datetime.now(timezone.utc)
        f1 = loop.record_finding("qa", "high", "race in writer", "file.py:42 TSAN", now=now)
        f2 = loop.record_finding("qa", "high", "race in writer", "file.py:42 TSAN",
                                 now=now + timedelta(seconds=60))
        assert f1["id"] == f2["id"] and f2["count"] == 2
        # outside the cooldown (ts refreshed by the merge) it files as new
        f3 = loop.record_finding("qa", "high", "race in writer", "file.py:42 TSAN",
                                  now=now + timedelta(seconds=2 * FINDING_COOLDOWN_SECONDS))
        assert f3["id"] != f1["id"]

    def test_judge_triage_routes_medium_plus_to_debug(self, repo: Path):
        loop = CriticLoop(repo, RUN)
        loop.record_finding("qa", "low", "naming", "file.py:1")
        loop.record_finding("qa", "medium", "swallowed error", "file.py:7 except: pass")
        loop.record_finding("fe-dev", "high", " XSS", "index.html:9")
        verdict = loop.triage()
        assert len(verdict["accepted"]) == 2        # medium + high
        assert all(f["owner"] == "debug" for f in verdict["accepted"])
        assert len(verdict["dismissed"]) == 1       # low
        assert verdict["route"]["CF-002"] == "debug"

    def test_fingerprint_is_stable(self):
        assert fingerprint_of("qa", "m", "e") == fingerprint_of("qa", " m ", " e ")
        assert fingerprint_of("qa", "m", "e") != fingerprint_of("qa", "m", "e2")


# ---------------------------------------------------------------------------
# Stuck detection (§8)
# ---------------------------------------------------------------------------


@dataclass
class FakeTask:
    id: str = "t-1"
    subject: str = "do the thing"
    owner: str = "qa"
    status: str = "in_progress"
    updated_at: str = ""


@dataclass
class FakeStore:
    tasks: list = field(default_factory=list)

    def list_tasks(self):
        return self.tasks


class TestStuck:
    def test_stalled_in_progress_prompts_respawn(self, repo: Path):
        old = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
        store = FakeStore([FakeTask(updated_at=old)])
        report = scan_stalled(repo, RUN, "team-x", task_store=store)
        assert len(report["stalled"]) == 1
        assert report["stalled"][0]["action"] == "respawn"
        assert report["prompt"]["respawn"] == ["t-1"]
        assert (repo / ".clawteam-local" / "runs" / RUN / "stuck.json").exists()

    def test_fresh_pending_is_not_stalled_old_pending_reassigns(self, repo: Path):
        now = datetime.now(timezone.utc)
        store = FakeStore([
            FakeTask(id="t-new", status="pending",
                     updated_at=(now - timedelta(minutes=1)).isoformat()),
            FakeTask(id="t-old", status="pending",
                     updated_at=(now - timedelta(minutes=30)).isoformat()),
        ])
        report = scan_stalled(repo, RUN, "team-x", task_store=store)
        assert [s["task"] for s in report["stalled"]] == ["t-old"]
        assert report["prompt"]["reassign"] == ["t-old"]

    def test_completed_and_blocked_are_never_stuck(self, repo: Path):
        store = FakeStore([
            FakeTask(id="t-done", status="completed", updated_at=""),
            FakeTask(id="t-blocked", status="blocked", updated_at=""),
        ])
        report = scan_stalled(repo, RUN, "team-x", task_store=store)
        assert report["stalled"] == []
        assert set(ACTIVE_STATUSES) == {"pending", "in_progress"}


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


class TestWp3Cli:
    def test_governor_cli_record_and_verdicts(self, repo: Path):
        r = runner.invoke(app, ["autonomy", "governor", RUN, "--repo", str(repo),
                                 "--set-budget", "kie_credits=50", "--record", "kie_credits=40"])
        assert r.exit_code == 0, r.output
        assert "soft_stop=True" in r.output          # 40/50 = 80 %

    def test_findings_cli_file_and_triage(self, repo: Path):
        r = runner.invoke(app, ["autonomy", "findings", RUN, "--repo", str(repo),
                                "--file", "qa:medium:swallowed error|file.py:7 except: pass"])
        assert r.exit_code == 0, r.output
        r = runner.invoke(app, ["autonomy", "findings", RUN, "--triage", "--repo", str(repo)])
        assert r.exit_code == 0 and "1 accepted" in r.output
        r = runner.invoke(app, ["autonomy", "findings", RUN, "--status", "triaged", "--repo", str(repo)])
        assert r.exit_code == 0 and "CF-001" in r.output

    def test_stuck_cli(self, repo: Path, monkeypatch):
        # the CLI resolves scan_stalled from the package namespace at call time
        monkeypatch.setattr(
            "clawteam.autonomy.scan_stalled",
            lambda root, run, team, **kw: {
                "run": run, "team": team,
                "stalled": [{"task": "t-1", "action": "respawn"}],
                "prompt": {"respawn": ["t-1"], "reassign": []},
            },
        )
        r = runner.invoke(app, ["autonomy", "stuck", RUN, "--repo", str(repo)])
        assert r.exit_code == 0 and "1 stalled" in r.output