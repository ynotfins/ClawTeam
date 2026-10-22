"""WP2 — stage layer tests on a temp git repo.

Exercises `clawteam.stage.StageManager` and the `clawteam stage` / `clawteam ship`
CLI wiring. All git state is throwaway: every test gets a fresh repo under pytest
`tmp_path`, and `CLAWTEAM_STAGE_ROOT` is pointed at the sandbox so the default
``D:\\w`` root is never touched. `launch_team` is monkeypatched in the ship test
so no agents are spawned (the swarm stays down).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app
from clawteam.stage import StageError, StageManager, stage_root_for
from clawteam.workspace import git

runner = CliRunner()

RUN = "ship-aa11bb22"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True,
    )
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
    # Keep every stage worktree inside the test sandbox, never D:\w.
    monkeypatch.setenv("CLAWTEAM_STAGE_ROOT", str(tmp_path / "w"))
    return repo


@pytest.fixture
def mgr(repo: Path) -> StageManager:
    return StageManager(repo)


# ---------------------------------------------------------------------------
# Roots and naming law
# ---------------------------------------------------------------------------


def test_stage_root_defaults_to_short_drive_and_run8(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAWTEAM_STAGE_ROOT", raising=False)
    root = stage_root_for(RUN)
    assert str(root) == str(Path("D:\\w") / RUN[:8])

    monkeypatch.setenv("CLAWTEAM_STAGE_ROOT", str(tmp_path / "custom"))
    assert stage_root_for(RUN) == tmp_path / "custom" / RUN[:8]


def test_integration_stage_creates_branch_worktree_and_longpaths(mgr: StageManager, repo: Path, tmp_path: Path):
    info = mgr.integration_stage(RUN)

    assert info.kind == "integration"
    assert info.branch == f"ship/{RUN}/integration"
    assert git.branch_exists(repo, info.branch)
    wt = Path(info.worktree_path)
    assert wt.is_dir()
    assert wt.is_relative_to(tmp_path / "w" / RUN[:8])
    assert (wt / "README.md").exists()  # content inherited from the base branch

    # longpaths is enabled on the repo (idempotent on second call)
    assert git.config_get(repo, "core.longpaths") == "true"
    assert git.ensure_longpaths(repo) is False  # already on — no rewrite

    # registry persisted inside the run dir
    registry = json.loads(
        (repo / ".clawteam-local" / "runs" / RUN / "stages.json").read_text(encoding="utf-8")
    )
    assert registry["integration_branch"] == f"ship/{RUN}/integration"
    assert any(s["branch"] == info.branch for s in registry["stages"])


def test_lane_fork_ab_branch_naming(mgr: StageManager, repo: Path):
    lane = mgr.create_lane(RUN, "be-dev")
    fork = mgr.create_fork(RUN, "D1", "a")
    ab = mgr.create_ab(RUN, "exp1")

    assert lane.branch == f"ship/{RUN}/lane/be-dev"
    assert fork.branch == f"ship/{RUN}/fork/D1/a"
    assert ab.branch == f"ship/{RUN}/ab/exp1"
    for info in (lane, fork, ab):
        assert git.branch_exists(repo, info.branch)
        assert Path(info.worktree_path).is_dir()

    kinds = {s["kind"]: s["branch"] for s in
             (json.loads((repo / ".clawteam-local" / "runs" / RUN / "stages.json")
                         .read_text(encoding="utf-8"))["stages"])}
    assert set(kinds) == {"integration", "lane", "fork", "ab"}


# ---------------------------------------------------------------------------
# Promote — Judge-approved only
# ---------------------------------------------------------------------------


def _commit_in(worktree: Path, name: str, content: str) -> None:
    (worktree / name).write_text(content, encoding="utf-8")
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", f"add {name}")


def test_promote_rejects_non_judge_and_leaves_integration_untouched(mgr: StageManager, repo: Path):
    integration = mgr.integration_stage(RUN)
    lane = mgr.create_lane(RUN, "qa")
    _commit_in(Path(lane.worktree_path), "gate.txt", "qa work\n")

    before = _git(repo, "rev-parse", integration.branch)
    for impostor in ("owner", "agent", "plan"):
        with pytest.raises(StageError, match="[Jj]udge"):
            mgr.promote(RUN, lane.branch, approved_by=impostor)
    assert _git(repo, "rev-parse", integration.branch) == before


def test_promote_merges_judge_approved_lane_into_integration(mgr: StageManager, repo: Path):
    integration = mgr.integration_stage(RUN)
    lane = mgr.create_lane(RUN, "qa")
    _commit_in(Path(lane.worktree_path), "gate.txt", "qa work\n")

    record = mgr.promote(RUN, lane.branch, approved_by="judge", note="gates green, metric +12%")
    assert record.merged is True
    assert record.approved_by == "judge"
    assert record.note.startswith("gates green")

    integration_wt = Path(integration.worktree_path)
    assert (integration_wt / "gate.txt").exists()
    assert _git(repo, "rev-parse", integration.branch) != _git(
        repo, "rev-parse", f"{integration.branch}~1"
    )


def test_promote_unknown_branch_fails(mgr: StageManager):
    mgr.integration_stage(RUN)
    with pytest.raises(StageError, match="No stage found"):
        mgr.promote(RUN, f"ship/{RUN}/lane/ghost", approved_by="judge")


# ---------------------------------------------------------------------------
# Discard / GC
# ---------------------------------------------------------------------------


def test_discard_removes_worktree_and_branch(mgr: StageManager, repo: Path):
    lane = mgr.create_lane(RUN, "temp-lane")
    assert mgr.discard(RUN, lane.branch) is True

    assert not git.branch_exists(repo, lane.branch)
    assert not Path(lane.worktree_path).exists()
    assert lane.branch not in [s.branch for s in mgr.list_stages(RUN)]


def test_discard_refuses_integration(mgr: StageManager):
    integration = mgr.integration_stage(RUN)
    with pytest.raises(StageError, match="integration"):
        mgr.discard(RUN, integration.branch)


def test_gc_drops_dead_entries_and_keeps_live(mgr: StageManager, repo: Path):
    integration = mgr.integration_stage(RUN)
    lane = mgr.create_lane(RUN, "gone-lane")

    # Kill the lane stage out-of-band (worktree + branch).
    _git(repo, "worktree", "remove", "--force", lane.worktree_path)
    _git(repo, "branch", "-D", lane.branch)

    report = mgr.gc(RUN)
    assert lane.branch in report.removed
    assert integration.branch in report.kept
    assert [s.branch for s in mgr.list_stages(RUN)] == [integration.branch]


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


def test_cli_create_requires_exactly_one_kind(repo: Path):
    result = runner.invoke(app, ["stage", "create", RUN, "--repo", str(repo)])
    assert result.exit_code == 1
    assert "exactly one" in result.output

    result = runner.invoke(
        app, ["stage", "create", RUN, "--lane", "--ab", "--experiment-id", "e1",
              "--repo", str(repo)]
    )
    assert result.exit_code == 1


def test_cli_create_lane_list_discard_gc_roundtrip(repo: Path):
    result = runner.invoke(
        app, ["stage", "create", RUN, "--lane", "--role", "fe-dev", "--repo", str(repo)]
    )
    assert result.exit_code == 0, result.output
    assert f"ship/{RUN}/lane/fe-dev" in result.output

    result = runner.invoke(app, ["stage", "list", RUN, "--repo", str(repo)])
    assert result.exit_code == 0, result.output
    assert "fe-dev" in result.output

    result = runner.invoke(
        app, ["stage", "discard", RUN, f"ship/{RUN}/lane/fe-dev", "--repo", str(repo)]
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        app, ["stage", "gc", RUN, "--repo", str(repo)]
    )
    assert result.exit_code == 0, result.output
    assert f"ship/{RUN}/integration" in result.output  # the live integration is kept


def test_cli_promote_gates_non_judge(repo: Path):
    mgr = StageManager(repo)
    lane = mgr.create_lane(RUN, "be-dev")

    result = runner.invoke(
        app, ["stage", "promote", RUN, lane.branch, "--approved-by", "owner",
              "--repo", str(repo)]
    )
    assert result.exit_code == 1
    assert "Judge" in result.output

    _commit_in(Path(lane.worktree_path), "api.txt", "endpoint\n")
    result = runner.invoke(
        app, ["stage", "promote", RUN, lane.branch, "--note", "verdict: metric +1",
              "--repo", str(repo)]
    )
    assert result.exit_code == 0, result.output
    assert "integration" in result.output


def test_ship_creates_integration_stage_in_run_json(repo: Path, monkeypatch):
    """WP2/AC-3: `clawteam ship` wires the integration stage into run.json."""
    # Keep the swarm down: never actually launch the template team.
    monkeypatch.setattr(
        "clawteam.cli.commands.launch_team", lambda **kwargs: None
    )

    result = runner.invoke(app, ["ship", "a tiny product", "--repo", str(repo)])
    assert result.exit_code == 0, result.output

    runs_dir = repo / ".clawteam-local" / "runs"
    run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]

    record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert record["template"] == "fullstack-commercial"
    run_id = record["run_id"]

    stage = record["stage"]
    assert stage["kind"] == "integration"
    assert stage["branch"] == f"ship/{run_id}/integration"
    assert Path(stage["worktree_path"]).is_dir()
    assert (run_dir / "stages.json").exists()

    stages = json.loads((run_dir / "stages.json").read_text(encoding="utf-8"))
    assert stages["integration_branch"] == f"ship/{run_id}/integration"