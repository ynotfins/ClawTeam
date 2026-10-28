"""Budget governors (AUTONOMY_POLICY §7) — caps enforce themselves, no asking.

At 80 % of any budget the run stops starting new forks/experiments; at 100 %
it wraps up gracefully: finish integrating green work, write SHIP_REPORT with
what remains. Never abort mid-write, never exceed a hard cap, never ask for
more budget (a Blocker Card only if the owner must supply a credential).

State: `<repo>/.clawteam-local/runs/<run>/governor.json`
`{"budgets": {kind: cap}, "used": {kind: amount}}`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from clawteam.autonomy.decide import AutonomyError, run_dir

# §7 defaults. `None` = owner-set at run start (unlimited until set).
PRO_DEFAULTS: dict[str, float | None] = {
    "wall_clock_hours": 6.0,
    "llm_tokens": None,
    "kie_credits": None,
    "concurrent_agents": 8,
    "open_experiments": 4,
}
SIMPLE_DEFAULTS: dict[str, float | None] = {
    "wall_clock_hours": 45 / 60,   # 45 min
    "llm_tokens": None,
    "kie_credits": None,
    "concurrent_agents": 5,
    "open_experiments": 1,
}

SOFT_STOP_FRACTION = 0.8   # stop starting new forks/experiments
KINDS = ("wall_clock_hours", "llm_tokens", "kie_credits",
         "concurrent_agents", "open_experiments")


def _governor_path(repo_root: Path, run: str) -> Path:
    return run_dir(repo_root, run) / "governor.json"


def _load(repo_root: Path, run: str) -> dict:
    path = _governor_path(repo_root, run)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return {"budgets": {}, "used": {}, "started_at": None}


def _save(repo_root: Path, run: str, data: dict) -> None:
    path = _governor_path(repo_root, run)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(path))


class Governor:
    """One run's budget ledger. Pure bookkeeping — callers act on its verdicts."""

    def __init__(self, repo_root: Path, run: str, mode: str = "pro"):
        if mode not in ("pro", "simple"):
            raise AutonomyError("governor mode must be pro|simple")
        self.repo_root = Path(repo_root)
        self.run = run
        self.mode = mode
        self.state = _load(repo_root, run)
        defaults = PRO_DEFAULTS if mode == "pro" else SIMPLE_DEFAULTS
        budgets = dict(self.state.get("budgets") or {})
        for kind, cap in defaults.items():
            budgets.setdefault(kind, cap)
        self.state["budgets"] = budgets
        self.state.setdefault("used", {})
        if not self.state.get("started_at"):
            self.state["started_at"] = datetime.now(timezone.utc).isoformat()
        _save(repo_root, run, self.state)

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def set_budget(self, kind: str, cap: float) -> None:
        if kind not in KINDS:
            raise AutonomyError(f"unknown budget kind '{kind}' (one of {KINDS})")
        self.state["budgets"][kind] = cap
        _save(self.repo_root, self.run, self.state)

    def record(self, kind: str, amount: float) -> dict:
        """Accumulate *amount* into *kind* (tokens/credits/etc.). Returns usage."""
        if kind not in KINDS:
            raise AutonomyError(f"unknown budget kind '{kind}' (one of {KINDS})")
        used = self.state["used"]
        used[kind] = float(used.get(kind, 0.0)) + float(amount)
        _save(self.repo_root, self.run, self.state)
        return self.usage(kind)

    def set_used(self, kind: str, value: float) -> dict:
        """Gauge kinds (concurrency, open experiments) are set, not summed."""
        if kind not in KINDS:
            raise AutonomyError(f"unknown budget kind '{kind}' (one of {KINDS})")
        self.state["used"][kind] = float(value)
        _save(self.repo_root, self.run, self.state)
        return self.usage(kind)

    # ------------------------------------------------------------------
    # Verdicts
    # ------------------------------------------------------------------

    def usage(self, kind: str) -> float | None:
        """Fraction of *kind*'s budget used (0..1), None when uncapped."""
        cap = self.state["budgets"].get(kind)
        if cap is None:
            return None
        used = float(self.state["used"].get(kind, 0.0))
        return used / cap if cap else 0.0

    def status(self) -> dict:
        out: dict = {"run": self.run, "mode": self.mode, "started_at": self.state["started_at"],
                     "soft_stop": self.should_soft_stop(), "wrap_up": self.should_wrap_up(),
                     "budgets": {}}
        for kind in KINDS:
            out["budgets"][kind] = {
                "cap": self.state["budgets"].get(kind),
                "used": self.state["used"].get(kind, 0.0),
                "usage": self.usage(kind),
            }
        return out

    def _capped_usages(self) -> list[float]:
        return [u for k in KINDS if (u := self.usage(k)) is not None]

    def should_soft_stop(self) -> bool:
        """True at >=80 % of any budget: stop starting new forks/experiments."""
        return any(u >= SOFT_STOP_FRACTION for u in self._capped_usages())

    def should_wrap_up(self) -> bool:
        """True at >=100 % of any budget: graceful wrap-up (never mid-write)."""
        return any(u >= 1.0 for u in self._capped_usages())

    def can_start_fork(self) -> bool:
        return not self.should_soft_stop()

    def check_fork(self) -> None:
        """Gate for the fork controller: soft-stop blocks new forks (§7)."""
        if self.should_wrap_up():
            raise AutonomyError(
                "governor: budget exhausted — graceful wrap-up in progress, no new forks"
            )
        if self.should_soft_stop():
            raise AutonomyError(
                f"governor: >= {SOFT_STOP_FRACTION:.0%} of a budget consumed — "
                "no new forks/experiments this run (§7)"
            )