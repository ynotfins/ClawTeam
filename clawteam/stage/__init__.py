"""Ship-run stage layer: integration / lane / fork / A-B worktrees per run."""

from __future__ import annotations

from pathlib import Path

from clawteam.stage.manager import (
    StageError,
    StageManager,
    stage_root_for,
)
from clawteam.stage.models import (
    StageGCReport,
    StageInfo,
    StageKind,
    StagePromotion,
    StageRegistry,
)

__all__ = [
    "StageError",
    "StageManager",
    "stage_root_for",
    "StageGCReport",
    "StageInfo",
    "StageKind",
    "StagePromotion",
    "StageRegistry",
    "get_stage_manager",
]


def get_stage_manager(repo_path: str | None = None) -> StageManager | None:
    """Return a StageManager if inside a git repo, else None."""
    path = Path(repo_path) if repo_path else None
    return StageManager.try_create(path)