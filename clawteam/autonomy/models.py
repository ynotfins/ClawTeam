"""Data models for the WP4 autonomy engine (decisions, blockers, forks).

Formats follow `docs/AUTONOMY_POLICY.md` §3 (Blocker Card), §5 (fork caps),
§6 (decisions.jsonl record).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DecisionOption(BaseModel):
    """One option under consideration in a decision."""

    name: str
    notes: str = ""


class BenchmarkEntry(BaseModel):
    """One row of a Top-Apps benchmark table (AUTONOMY_POLICY §4)."""

    app: str
    choice: str = ""
    notes: str = ""


class DecisionRecord(BaseModel):
    """One decision, persisted to `<run>/decisions.jsonl` (§6 shape)."""

    id: str                      # e.g. "D-015"
    run: str
    question: str
    options: list[DecisionOption] = Field(default_factory=list)
    benchmark: list[BenchmarkEntry] = Field(default_factory=list)
    chosen: str = ""             # name of the chosen option ("" = undecided/forked)
    confidence: float = 0.0      # 0..1; <0.7 + material difference => fork
    forked: bool = False
    rationale: str = ""
    ts: str                      # ISO-8601 UTC


class BlockerRecord(BaseModel):
    """An Absolute Blocker card (AUTONOMY_POLICY §3). Never pauses the swarm."""

    id: str                      # e.g. "B-001"
    run: str
    title: str
    needed_from_owner: str       # exact artifact/decision requested
    why_impossible: str          # evidence for (a)+(b)+(c)
    work_continuing: str = ""
    ship_default: str = ""       # what ships instead if no reply by SHIP
    notified_at: str = ""        # last batched notification timestamp ("" = pending)
    ts: str


class ForkLedgerEntry(BaseModel):
    """One open or closed fork in `<run>/forks.json` (§5 caps)."""

    decision_id: str
    run: str
    question: str = ""
    options: list[str] = Field(default_factory=list)   # exactly 2 (a/b)
    winner: str = ""                                    # "" while open
    budget_fraction: float = 0.0                       # fork_budget / run budget
    open: bool = True
    created_at: str