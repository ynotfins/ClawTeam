"""Fork controller — fork-both-ways with §5 caps (AUTONOMY_POLICY / F6).

A fork is opened ONLY when options are materially different and the benchmark
is inconclusive (confidence < 0.7). This controller enforces the caps and
creates the paired option stages through the WP2 stage layer
(`clawteam/stage/`): branches `ship/<run>/fork/<decision-id>/<option>`.
Ledger: `<repo>/.clawteam-local/runs/<run>/forks.json`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from clawteam.autonomy.decide import AutonomyError, run_dir
from clawteam.autonomy.models import ForkLedgerEntry
from clawteam.stage.manager import StageManager

MAX_OPEN_FORKS = 3          # §5 cap: open forks per run
OPTIONS_PER_FORK = 2        # §5 cap: options per fork (exactly two)
MAX_BUDGET_FRACTION = 0.4   # §5 cap: fork budget share of the run budget


def _ledger_path(repo_root: Path, run: str) -> Path:
    return run_dir(repo_root, run) / "forks.json"


def _load_ledger(repo_root: Path, run: str) -> dict[str, dict]:
    path = _ledger_path(repo_root, run)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {}


def _save_ledger(repo_root: Path, run: str, ledger: dict[str, dict]) -> None:
    path = _ledger_path(repo_root, run)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(path))


def _validate_entry(raw: dict) -> ForkLedgerEntry | None:
    try:
        return ForkLedgerEntry.model_validate(raw)
    except Exception:
        return None


class ForkController:
    """Caps + paired stage creation for the fork-both-ways rule."""

    def __init__(self, stage_manager: StageManager):
        self.stages = stage_manager
        self.repo_root = Path(stage_manager.repo_root)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def ledger(self, run: str) -> list[ForkLedgerEntry]:
        raw = _load_ledger(self.repo_root, run)
        out = [e for e in (_validate_entry(v) for v in raw.values()) if e]
        return sorted(out, key=lambda e: e.created_at)

    def open_forks(self, run: str) -> list[ForkLedgerEntry]:
        return [e for e in self.ledger(run) if e.open]

    # ------------------------------------------------------------------
    # Create (paired stages, caps enforced)
    # ------------------------------------------------------------------

    def create_fork_pair(
        self,
        run: str,
        decision_id: str,
        question: str,
        option_a: str,
        option_b: str,
        *,
        budget_total: float | None = None,
        fork_budget: float | None = None,
    ) -> tuple[ForkLedgerEntry, list]:
        """Open one fork: create both option worktrees/branches via the stage layer.

        Caps (§5): at most `MAX_OPEN_FORKS` open forks per run; exactly two
        options; fork budget ≤ `MAX_BUDGET_FRACTION` of the run budget; nested
        forks are rejected (a decision id may not be re-opened while open).
        Returns (ledger entry, [StageInfo(a), StageInfo(b)]).
        """
        if option_a == option_b:
            raise AutonomyError("a fork needs two DIFFERENT options")

        ledger = _load_ledger(self.repo_root, run)
        entries = {k: v for k, v in ledger.items() if _validate_entry(v)}
        existing = entries.get(decision_id)
        if existing and existing.get("open", True):
            raise AutonomyError(
                f"nested forks are not allowed (§5): fork '{decision_id}' is already open — decide inside it"
            )
        open_count = sum(1 for v in entries.values() if v.get("open", True))
        if open_count >= MAX_OPEN_FORKS:
            raise AutonomyError(
                f"cap reached: {MAX_OPEN_FORKS} open forks per run (§5) — close one before forking again"
            )

        budget_fraction = 0.0
        if budget_total is not None and fork_budget is not None:
            if budget_total <= 0:
                raise AutonomyError("budget_total must be > 0 to measure the fork share")
            budget_fraction = fork_budget / budget_total
            if budget_fraction > MAX_BUDGET_FRACTION:
                raise AutonomyError(
                    f"fork budget share {budget_fraction:.0%} exceeds the {MAX_BUDGET_FRACTION:.0%} cap (§5)"
                )

        stage_a = self.stages.create_fork(run, decision_id, option_a)
        stage_b = self.stages.create_fork(run, decision_id, option_b)

        entry = ForkLedgerEntry(
            decision_id=decision_id,
            run=run,
            question=question,
            options=[option_a, option_b],
            budget_fraction=round(budget_fraction, 4),
            open=True,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        ledger[decision_id] = json.loads(entry.model_dump_json())
        _save_ledger(self.repo_root, run, ledger)
        return entry, [stage_a, stage_b]

    # ------------------------------------------------------------------
    # Close (Judge/owner picked a winner)
    # ------------------------------------------------------------------

    def close_fork(self, run: str, decision_id: str, winner: str) -> ForkLedgerEntry:
        """Record the winning option and remove the loser's stage.

        The loser branch is archived, not deleted: its commit stays reachable
        on the repo until the Judge's verdict is mirrored into the decision log
        by the caller, and `git branch` history retains it while the stage
        worktree is released. The ledger verdict is the source of truth.
        """
        ledger = _load_ledger(self.repo_root, run)
        raw = ledger.get(decision_id)
        entry = _validate_entry(raw) if raw else None
        if entry is None or not entry.open:
            raise AutonomyError(f"no open fork '{decision_id}' in run '{run}'")
        if winner not in entry.options:
            raise AutonomyError(f"winner '{winner}' is not one of {entry.options}")

        loser = next(o for o in entry.options if o != winner)
        loser_branch = f"ship/{run}/fork/{decision_id}/{loser}"
        try:
            self.stages.discard(run, loser_branch)
        except Exception:
            pass  # loser worktree release is best-effort; the ledger verdict is the truth

        entry.winner = winner
        entry.open = False
        ledger[decision_id] = json.loads(entry.model_dump_json())
        _save_ledger(self.repo_root, run, ledger)
        return entry