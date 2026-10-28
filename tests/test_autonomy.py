"""WP4 — autonomy engine tests: decide(), Blocker Cards, fork controller.

All state is throwaway: each test gets a fresh git repo under pytest
`tmp_path`, `CLAWTEAM_STAGE_ROOT` is sandboxed away from `D:\\w`, and the
decision-log mirror writes inside the temp repo's own `docs/` tree.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clawteam.autonomy import (
    AutonomyError,
    ForkController,
    decide,
    list_blockers,
    list_decisions,
    mark_notified,
    next_decision_id,
    pending_notification,
    write_blocker,
)
from clawteam.cli.commands import app
from clawteam.stage import StageManager
from clawteam.workspace import git

runner = CliRunner()

RUN = "ship-aut01"


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
    # Decision-log mirror target inside the temp repo (never the real docs/).
    (repo / "docs").mkdir()
    (repo / "docs" / "DECISION_LOG.md").write_text(
        "# DECISION_LOG — Append-Only\n\n| # | Date | Decision | Rationale | Anchor impact |\n"
        "|---|---|---|---|---|\n\n## Anchor challenges (`CHAL-xxx`)\n\n_None yet._\n",
        encoding="utf-8",
    )
    return repo


# ---------------------------------------------------------------------------
# decide() — benchmark decision records (§4/§6)
# ---------------------------------------------------------------------------


class TestDecide:
    def test_record_shape_and_jsonl(self, repo: Path):
        rec = decide(
            repo, RUN, "State management for the client dashboard",
            ["Zustand", "Redux Toolkit"],
            benchmark=[("Linear", "custom store"), ("Notion", "custom")],
            chosen="Zustand", confidence=0.74,
            rationale="leaders converge on custom lightweight stores",
        )
        assert rec.id.startswith("D-") and rec.confidence == 0.74
        assert rec.chosen == "Zustand" and rec.forked is False

        path = repo / ".clawteam-local" / "runs" / RUN / "decisions.jsonl"
        lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert lines[-1]["id"] == rec.id
        assert lines[-1]["benchmark"][0]["app"] == "Linear"
        assert [o["name"] for o in lines[-1]["options"]] == ["Zustand", "Redux Toolkit"]
        assert list_decisions(repo, RUN)[0].question.startswith("State management")

    def test_chosen_must_be_an_option(self, repo: Path):
        with pytest.raises(AutonomyError, match="not among options"):
            decide(repo, RUN, "q", ["a", "b"], chosen="c")

    def test_mirror_row_in_decision_log_with_next_id(self, repo: Path):
        seed = next_decision_id(repo)  # "D-001" in the fresh temp log
        rec = decide(repo, RUN, "First question", ["x", "y"], chosen="x", confidence=0.9)
        assert rec.id == seed
        log = (repo / "docs" / "DECISION_LOG.md").read_text(encoding="utf-8")
        assert f"| {rec.id} |" in log and "First question" in log
        # mirrored row lands before the Anchor challenges section
        assert log.find(f"| {rec.id} |") < log.find("## Anchor challenges")

        rec2 = decide(repo, RUN, "Second question", ["p", "q"])
        assert rec2.id != rec.id
        assert next_decision_id(repo) != rec2.id

    def test_missing_log_is_silent(self, tmp_path):
        repo = tmp_path / "nolog"
        repo.mkdir()
        rec = decide(repo, RUN, "q", ["a"], mirror_to_log=True)
        assert not (repo / "docs" / "DECISION_LOG.md").exists()
        assert (repo / ".clawteam-local" / "runs" / RUN / "decisions.jsonl").exists()
        assert rec.chosen == "a"  # ladder rung 5: simple default, logged


# ---------------------------------------------------------------------------
# Blocker Cards (§3)
# ---------------------------------------------------------------------------


class TestBlockers:
    def test_card_written_in_section3_format(self, repo: Path):
        rec = write_blocker(
            repo, RUN, "Stripe key missing",
            needed_from_owner="Stripe test-mode restricted key (STRIPE_API_KEY, User env)",
            why_impossible="checkout cannot be created without a credential only the owner can mint "
                          "(a); no safe default exists (b); tried env, config, docs (c)",
            work_continuing="WP11 packaging lane",
            ship_default="license gate ships dormant with paywall hidden behind a flag",
        )
        assert rec.id == "B-001"
        card = repo / ".clawteam-local" / "runs" / RUN / "blockers" / "B-001.md"
        text = card.read_text(encoding="utf-8")
        assert text.startswith("# BLOCKER B-001 — Stripe key missing")
        assert "Needed from owner:" in text
        assert "Why impossible otherwise:" in text
        assert "Default if no reply by SHIP:" in text

    def test_index_ids_sequence_and_listing(self, repo: Path):
        for n in range(3):
            write_blocker(repo, RUN, f"blocker {n}", needed_from_owner="x", why_impossible="y")
        cards = list_blockers(repo, RUN)
        assert [c.id for c in cards] == ["B-001", "B-002", "B-003"]

    def test_card_requires_evidence_fields(self, repo: Path):
        with pytest.raises(AutonomyError, match="needs title"):
            write_blocker(repo, RUN, "", needed_from_owner="x", why_impossible="y")

    def test_batched_notification_state(self, repo: Path):
        write_blocker(repo, RUN, "b1", needed_from_owner="x", why_impossible="y")
        write_blocker(repo, RUN, "b2", needed_from_owner="x", why_impossible="y")
        assert len(pending_notification(repo, RUN)) == 2

        stamped = mark_notified(repo, RUN)  # batch: stamp never-notified cards
        assert stamped == 2
        assert all(c.notified_at for c in list_blockers(repo, RUN))
        assert pending_notification(repo, RUN) == []  # 15-min batch window


# ---------------------------------------------------------------------------
# Fork controller (§5 caps, paired stages via WP2)
# ---------------------------------------------------------------------------


class TestForkController:
    @pytest.fixture
    def controller(self, repo: Path) -> ForkController:
        return ForkController(StageManager(repo))

    def test_create_pair_makes_both_branches(self, controller: ForkController, repo: Path):
        entry, stages = controller.create_fork_pair(
            RUN, "F-1", "React Native or native Windows?", "react-native", "winui",
        )
        assert entry.options == ["react-native", "winui"]
        assert entry.open and entry.winner == ""
        for option in entry.options:
            branch = f"ship/{RUN}/fork/F-1/{option}"
            assert git.branch_exists(repo, branch)
        assert [s.branch for s in stages] == [
            f"ship/{RUN}/fork/F-1/react-native", f"ship/{RUN}/fork/F-1/winui",
        ]

    def test_two_options_exactly(self, controller: ForkController):
        entry, _ = controller.create_fork_pair(RUN, "F-2", "q", "a", "b")
        assert len(entry.options) == 2  # §5 cap: options per fork = 2

    def test_cap_three_open_forks(self, controller: ForkController):
        for n in (1, 2, 3):
            controller.create_fork_pair(RUN, f"F-{n}", f"q{n}", "a", "b")
        with pytest.raises(AutonomyError, match="cap reached"):
            controller.create_fork_pair(RUN, "F-4", "q4", "a", "b")

    def test_no_nested_forks(self, controller: ForkController):
        controller.create_fork_pair(RUN, "F-5", "q", "a", "b")
        with pytest.raises(AutonomyError, match="nested"):
            controller.create_fork_pair(RUN, "F-5", "q again", "c", "d")

    def test_budget_share_cap(self, controller: ForkController):
        with pytest.raises(AutonomyError, match="cap"):
            controller.create_fork_pair(
                RUN, "F-6", "q", "a", "b", budget_total=10.0, fork_budget=5.0,  # 50% > 40%
            )

    def test_close_records_winner_and_discards_loser(self, controller: ForkController, repo: Path):
        controller.create_fork_pair(RUN, "F-7", "q", "a", "b")
        entry = controller.close_fork(RUN, "F-7", "a")
        assert entry.winner == "a" and entry.open is False
        assert not git.branch_exists(repo, f"ship/{RUN}/fork/F-7/b")  # loser discarded
        assert git.branch_exists(repo, f"ship/{RUN}/fork/F-7/a")     # winner kept
        assert controller.open_forks(RUN) == []
        # closed fork frees a cap slot
        controller.create_fork_pair(RUN, "F-8", "q2", "c", "d")

    def test_close_rejects_unknown_winner(self, controller: ForkController):
        controller.create_fork_pair(RUN, "F-9", "q", "a", "b")
        with pytest.raises(AutonomyError, match="not one of"):
            controller.close_fork(RUN, "F-9", "zzz")


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


class TestAutonomyCli:
    def test_decide_cli_roundtrip(self, repo: Path):
        result = runner.invoke(app, [
            "autonomy", "decide", "Tabs or spaces?", RUN,
            "--option", "tabs", "--option", "spaces",
            "--chosen", "tabs", "--confidence", "0.8",
            "--benchmark", "Google=tabs", "--benchmark", "Meta=tabs",
            "--repo", str(repo),
        ])
        assert result.exit_code == 0, result.output
        assert "tabs" in result.output
        assert list_decisions(repo, RUN)[0].chosen == "tabs"

    def test_blocker_cli_and_list(self, repo: Path):
        result = runner.invoke(app, [
            "autonomy", "blocker", "Need owner photo", RUN,
            "--needed", "a photo of the owner", "--why", "consent decision is owner-only (a)(b)(c)",
            "--repo", str(repo),
        ])
        assert result.exit_code == 0, result.output
        assert "B-001" in result.output

        result = runner.invoke(app, ["autonomy", "blockers", RUN, "--repo", str(repo)])
        assert result.exit_code == 0 and "Need owner photo" in result.output

    def test_forks_cli_create_close_list(self, repo: Path):
        result = runner.invoke(app, [
            "autonomy", "forks", RUN, "--create",
            "--decision-id", "F-CLI", "--question", "Big widgets?",
            "--option-a", "big", "--option-b", "bigger",
            "--repo", str(repo),
        ])
        assert result.exit_code == 0, result.output
        assert "F-CLI" in result.output

        result = runner.invoke(app, [
            "autonomy", "forks", RUN, "--close",
            "--decision-id", "F-CLI", "--winner", "big",
            "--repo", str(repo),
        ])
        assert result.exit_code == 0 and "winner big" in result.output

        result = runner.invoke(app, ["autonomy", "forks", RUN, "--repo", str(repo)])
        assert result.exit_code == 0 and "F-CLI" in result.output

    def test_forks_cap_error_surfaces(self, repo: Path):
        StageManager(repo).integration_stage(RUN)
        args = ["autonomy", "forks", RUN, "--repo", str(repo)]
        for n in (1, 2, 3):
            r = runner.invoke(app, [*args, "--create", "--decision-id", f"FC{n}",
                                    "--question", "q", "--option-a", "a", "--option-b", "b"])
            assert r.exit_code == 0, r.output
        r = runner.invoke(app, [*args, "--create", "--decision-id", "FC4",
                                "--question", "q", "--option-a", "a", "--option-b", "b"])
        assert r.exit_code == 1 and "cap" in r.output