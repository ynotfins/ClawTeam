"""Data models for the stage layer (git worktrees per ship run)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

StageKind = Literal["integration", "lane", "fork", "ab"]


class StageInfo(BaseModel):
    """One stage = one branch + one worktree under the run's stage root."""

    kind: StageKind
    run: str                       # full run id, e.g. "ship-ab12cd34"
    team: str                       # board team the run belongs to
    name: str                       # segment after the kind: role / "<id>/<option>" / experiment id
    branch: str                     # ship/<run>/integration | lane/<role> | fork/<id>/<option> | ab/<id>
    worktree_path: str              # D:\w\<run8>\<...> (or CLAWTEAM_STAGE_ROOT override)
    repo_root: str
    created_at: str


class StagePromotion(BaseModel):
    """Audit record for a Judge-approved promotion into the integration branch."""

    run: str
    branch: str                     # source branch promoted
    approved_by: str = "judge"
    note: str = ""
    merged: bool
    output: str = ""
    promoted_at: str


class StageRegistry(BaseModel):
    """Per-run stage registry, persisted as stages.json inside the run dir."""

    run: str
    team: str
    repo_root: str
    stage_root: str
    integration_branch: str = ""   # set on first create; ship/<run>/integration
    stages: list[StageInfo] = []
    promotions: list[StagePromotion] = []


class StageGCReport(BaseModel):
    """Result of `stage gc` for one run."""

    run: str
    removed: list[str] = []         # stage names removed
    kept: list[str] = []             # stage names verified alive and kept