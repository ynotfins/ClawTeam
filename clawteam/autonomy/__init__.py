"""WP4 autonomy engine — decide, Blocker Cards, fork-both-ways (AUTONOMY_POLICY)."""

from __future__ import annotations

from pathlib import Path

from clawteam.autonomy.blockers import (
    list_blockers,
    mark_notified,
    pending_notification,
    write_blocker,
)
from clawteam.autonomy.decide import (
    AutonomyError,
    decide,
    list_decisions,
    next_decision_id,
)
from clawteam.autonomy.forks import (
    MAX_BUDGET_FRACTION,
    MAX_OPEN_FORKS,
    ForkController,
)
from clawteam.autonomy.models import (
    BenchmarkEntry,
    BlockerRecord,
    DecisionOption,
    DecisionRecord,
    ForkLedgerEntry,
)

__all__ = [
    "AutonomyError",
    "decide",
    "list_decisions",
    "next_decision_id",
    "write_blocker",
    "list_blockers",
    "mark_notified",
    "pending_notification",
    "ForkController",
    "MAX_OPEN_FORKS",
    "MAX_BUDGET_FRACTION",
    "BenchmarkEntry",
    "DecisionOption",
    "DecisionRecord",
    "BlockerRecord",
    "ForkLedgerEntry",
]


def autonomy_dir(repo_root: Path, run: str) -> Path:
    """The per-run autonomy state dir (decisions/blockers/forks live here)."""
    from clawteam.autonomy.decide import run_dir as _run_dir
    return _run_dir(repo_root, run)