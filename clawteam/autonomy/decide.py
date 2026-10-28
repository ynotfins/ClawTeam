"""decide() — the WP4 benchmark-decision writer (AUTONOMY_POLICY §4/§6).

Every non-obvious product/UX/architecture decision gets a record: the question,
the options studied, the Top-Apps benchmark table, the chosen pattern with a
confidence, and a one-paragraph rationale. Records append to
`<repo>/.clawteam-local/runs/<run>/decisions.jsonl` and mirror into
`docs/DECISION_LOG.md` (next `D-xxx` row) when that file exists.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from clawteam.autonomy.models import BenchmarkEntry, DecisionOption, DecisionRecord
from clawteam.paths import validate_identifier


class AutonomyError(Exception):
    """Raised when an autonomy-engine invariant is violated."""


def run_dir(repo_root: Path, run: str) -> Path:
    """Return (and create) `<repo>/.clawteam-local/runs/<run>`."""
    rd = repo_root / ".clawteam-local" / "runs" / validate_identifier(run, "run id")
    rd.mkdir(parents=True, exist_ok=True)
    return rd


def decisions_path(repo_root: Path, run: str) -> Path:
    return run_dir(repo_root, run) / "decisions.jsonl"


def decision_log_path(repo_root: Path) -> Path:
    return repo_root / "docs" / "DECISION_LOG.md"


def next_decision_id(repo_root: Path) -> str:
    """Next `D-nnn` from the highest existing id in docs/DECISION_LOG.md."""
    log = decision_log_path(repo_root)
    highest = 0
    if log.exists():
        for m in re.finditer(r"\|\s*D-(\d+)\s*\|", log.read_text(encoding="utf-8")):
            highest = max(highest, int(m.group(1)))
    return f"D-{highest + 1:03d}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _as_benchmark(b: str | tuple | BenchmarkEntry) -> BenchmarkEntry:
    if isinstance(b, BenchmarkEntry):
        return b
    if isinstance(b, str):
        app_name, _, choice = b.partition("=")
        return BenchmarkEntry(app=app_name.strip(), choice=choice.strip())
    if isinstance(b, tuple) and len(b) >= 1:
        app_name = str(b[0])
        choice = str(b[1]) if len(b) > 1 else ""
        notes = str(b[2]) if len(b) > 2 else ""
        return BenchmarkEntry(app=app_name, choice=choice, notes=notes)
    raise AutonomyError(f"benchmark entry must be str 'App=choice', tuple, or BenchmarkEntry — got {b!r}")


def decide(
    repo_root: Path,
    run: str,
    question: str,
    options: list[str | DecisionOption],
    *,
    benchmark: list[str | tuple | BenchmarkEntry] | None = None,
    chosen: str | None = None,
    confidence: float = 0.0,
    rationale: str = "",
    forked: bool = False,
    mirror_to_log: bool = True,
) -> DecisionRecord:
    """Record one decision (AUTONOMY_POLICY §2/§4/§6).

    `chosen` defaults to the first option — the decision ladder's "reversible &
    cheap → pick the simpler option, log it, move on" rung. `forked=True`
    records that no single option was chosen and both are being built (§5).
    """
    opts = [o if isinstance(o, DecisionOption) else DecisionOption(name=str(o)) for o in options]
    if not opts:
        raise AutonomyError("decide() needs at least one option")
    names = [o.name for o in opts]
    if chosen is None:
        chosen = names[0]
    if chosen and chosen not in names:
        raise AutonomyError(f"chosen '{chosen}' is not among options {names}")

    record = DecisionRecord(
        id=next_decision_id(repo_root),
        run=validate_identifier(run, "run id"),
        question=question,
        options=opts,
        benchmark=[_as_benchmark(b) for b in (benchmark or [])],
        chosen=chosen or "",
        confidence=max(0.0, min(1.0, float(confidence))),
        forked=forked,
        rationale=rationale,
        ts=_now_iso(),
    )

    path = decisions_path(repo_root, run)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(json.loads(record.model_dump_json()), ensure_ascii=False) + "\n")

    if mirror_to_log:
        _mirror_decision_row(repo_root, record)
    return record


def _mirror_decision_row(repo_root: Path, record: DecisionRecord) -> None:
    """Append the decision as a `D-xxx` row in docs/DECISION_LOG.md (if present)."""
    log = decision_log_path(repo_root)
    if not log.exists():
        return
    date = record.ts.split("T")[0]
    options_txt = " / ".join(o.name for o in record.options)
    bench_txt = "; ".join(f"{b.app}={b.choice}" for b in record.benchmark if b.choice) or "none"
    row = (
        f"| {record.id} | {date} | {record.question} — options [{options_txt}]"
        f" → **{record.chosen or 'FORKED (both)'}**"
        f" (confidence {record.confidence:.2f}; benchmark: {bench_txt}) |"
        f" {record.rationale} | none |\n"
    )
    text = log.read_text(encoding="utf-8")
    anchor = "## Anchor challenges"
    idx = text.find(anchor)
    if idx == -1:
        text = text.rstrip() + "\n\n" + row
    else:
        text = text[:idx] + row + text[idx:]
    log.write_text(text, encoding="utf-8")


def list_decisions(repo_root: Path, run: str) -> list[DecisionRecord]:
    """All decisions recorded for a run (oldest first)."""
    path = decisions_path(repo_root, run)
    if not path.exists():
        return []
    out: list[DecisionRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(DecisionRecord.model_validate(json.loads(line)))
        except Exception:
            continue  # a malformed line never breaks the Board surface
    return out