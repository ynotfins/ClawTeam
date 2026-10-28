"""Keep It Simple — one-prompt mode + Parent Gate (KEEP_IT_SIMPLE_SPEC)."""

from __future__ import annotations

from clawteam.kis.state import (
    DEFAULT_CAPS,
    GATED_ACTIONS,
    KisState,
    ParentGateError,
    kis_path,
)

__all__ = [
    "DEFAULT_CAPS",
    "GATED_ACTIONS",
    "KisState",
    "ParentGateError",
    "kis_path",
]