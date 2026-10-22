"""StageManager — per-run ship stages (integration / lane / fork / ab) on git worktrees.

Wraps the existing ``clawteam.workspace`` layer: branch and worktree plumbing goes
through :mod:`clawteam.workspace.git`, the worktree-per-agent idea is the same as
``WorkspaceManager`` but keyed by *run* + *stage kind* instead of team + agent.

Layout for a run ``ship-ab12cd34``:

- branches      ``ship/ship-ab12cd34/integration``, ``ship/ship-ab12cd34/lane/<role>``,
                ``ship/ship-ab12cd34/fork/<decision-id>/<option>``, ``ship/ship-ab12cd34/ab/<experiment-id>``
- worktrees      ``<stage_root>/<run8>/…`` where ``<run8>`` is the first 8 chars of the
                run id; ``<stage_root>`` defaults to ``D:\\w`` and is overridden by
                ``CLAWTEAM_STAGE_ROOT`` (short paths dodge the Windows MAX_PATH limit;
                ``core.longpaths`` is also enabled on the repo).
- registry      ``<repo>/.clawteam-local/runs/<run>/stages.json``

Nothing reaches the integration branch except :meth:`StageManager.promote`, which
accepts Judge-approved promotions only.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.stage.models import StageGCReport, StageInfo, StagePromotion, StageRegistry
from clawteam.workspace import git

logger = logging.getLogger(__name__)

_DEFAULT_STAGE_ROOT = "D:\\w"
_RUN8_LEN = 8


class StageError(Exception):
    """Raised when a stage operation is invalid or unsafe."""


def stage_root_for(run: str) -> Path:
    """Return the stage root for *run* (``CLAWTEAM_STAGE_ROOT`` overrides ``D:\\w``)."""
    base = os.environ.get("CLAWTEAM_STAGE_ROOT") or _DEFAULT_STAGE_ROOT
    return Path(base) / validate_identifier(run, "run id")[:_RUN8_LEN]


class StageManager:
    """Manages the stage layer for ship runs inside one git repository."""

    def __init__(self, repo_path: Path | None = None):
        cwd = repo_path or Path.cwd()
        self.repo_root = git.repo_root(cwd)
        self.base_branch = git.current_branch(self.repo_root)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def try_create(repo_path: Path | None = None) -> StageManager | None:
        """Return a StageManager if inside a git repo, else None."""
        try:
            return StageManager(repo_path)
        except git.GitError:
            return None

    # ------------------------------------------------------------------
    # Registry
    # ------------------------------------------------------------------

    def _run_dir(self, run: str) -> Path:
        return self.repo_root / ".clawteam-local" / "runs" / validate_identifier(run, "run id")

    def _registry_path(self, run: str) -> Path:
        return self._run_dir(run) / "stages.json"

    def _load_registry(self, run: str, team: str | None = None) -> StageRegistry:
        path = self._registry_path(run)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return StageRegistry.model_validate(data)
            except Exception:
                pass
        return StageRegistry(
            run=run,
            team=team or run,
            repo_root=str(self.repo_root),
            stage_root=str(stage_root_for(run)),
        )

    def _save_registry(self, registry: StageRegistry) -> None:
        path = self._registry_path(registry.run)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(registry.model_dump_json(indent=2), encoding="utf-8")
        os.replace(str(tmp), str(path))

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def integration_stage(self, run: str, team: str | None = None) -> StageInfo:
        """Create (idempotently) the run's integration stage.

        The integration branch is the run's mainline: only Judge-approved
        promotions land on it (see :meth:`promote`).
        """
        branch = f"ship/{run}/integration"
        info = self._create_stage(
            run=run, team=team or run, kind="integration", name="integration",
            branch=branch, worktree_parts=("integration",), base_ref=self.base_branch,
        )
        registry = self._load_registry(run, team)
        registry.integration_branch = branch
        if team:
            registry.team = team
        self._save_registry(registry)
        return info

    def create_lane(self, run: str, role: str, team: str | None = None) -> StageInfo:
        """Create a lane worktree for *role* (based off the integration branch)."""
        validate_identifier(role, "lane role")
        branch = f"ship/{run}/lane/{role}"
        return self._create_stage(
            run=run, team=team or run, kind="lane", name=role,
            branch=branch, worktree_parts=("lane", role),
            base_ref=self._require_integration(run, team).branch,
        )

    def create_fork(
        self, run: str, decision_id: str, option: str, team: str | None = None,
    ) -> StageInfo:
        """Create one fork-option worktree (``ship/<run>/fork/<decision-id>/<option>``)."""
        validate_identifier(decision_id, "fork decision id")
        validate_identifier(option, "fork option")
        branch = f"ship/{run}/fork/{decision_id}/{option}"
        return self._create_stage(
            run=run, team=team or run, kind="fork", name=f"{decision_id}/{option}",
            branch=branch, worktree_parts=("fork", decision_id, option),
            base_ref=self._require_integration(run, team).branch,
        )

    def create_ab(self, run: str, experiment_id: str, team: str | None = None) -> StageInfo:
        """Create an A/B experiment worktree (``ship/<run>/ab/<experiment-id>``)."""
        validate_identifier(experiment_id, "experiment id")
        branch = f"ship/{run}/ab/{experiment_id}"
        return self._create_stage(
            run=run, team=team or run, kind="ab", name=experiment_id,
            branch=branch, worktree_parts=("ab", experiment_id),
            base_ref=self._require_integration(run, team).branch,
        )

    def _require_integration(self, run: str, team: str | None) -> StageInfo:
        """Return the run's integration stage, creating it when missing."""
        registry = self._load_registry(run, team)
        if registry.integration_branch and git.branch_exists(
            self.repo_root, registry.integration_branch,
        ):
            return StageInfo(
                kind="integration", run=run, team=registry.team or run,
                name="integration", branch=registry.integration_branch,
                worktree_path=str(self._stage_worktree(registry.integration_branch)),
                repo_root=str(self.repo_root), created_at="",
            )
        return self.integration_stage(run, team)

    def _create_stage(
        self,
        *,
        run: str,
        team: str,
        kind: str,
        name: str,
        branch: str,
        worktree_parts: tuple[str, ...],
        base_ref: str,
    ) -> StageInfo:
        validate_identifier(run, "run id")
        git.ensure_longpaths(self.repo_root)
        wt_path = ensure_within_root(stage_root_for(run), *worktree_parts)

        # Crash recovery: stale branch metadata can survive after the physical
        # worktree directory is deleted, so clear both path and branch state.
        if wt_path.exists():
            try:
                git.remove_worktree(self.repo_root, wt_path)
            except git.GitError:
                pass
        try:
            git.delete_branch(self.repo_root, branch)
        except git.GitError:
            pass

        git.create_worktree(self.repo_root, wt_path, branch, base_ref=base_ref)

        info = StageInfo(
            kind=kind, run=run, team=team, name=name, branch=branch,
            worktree_path=str(wt_path), repo_root=str(self.repo_root),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        registry = self._load_registry(run, team)
        if team:
            registry.team = team
        # Replace any stale entry for the same stage branch.
        registry.stages = [s for s in registry.stages if s.branch != branch]
        registry.stages.append(info)
        self._save_registry(registry)
        return info

    # ------------------------------------------------------------------
    # Promote (Judge-approved only) / Discard
    # ------------------------------------------------------------------

    def promote(
        self,
        run: str,
        branch: str,
        *,
        approved_by: str = "judge",
        note: str = "",
        team: str | None = None,
    ) -> StagePromotion:
        """Merge *branch* into the integration branch.

        Judge-approved only: *approved_by* must be ``judge``. Anything else is
        rejected with :class:`StageError` and the integration branch is untouched.
        """
        if str(approved_by).strip().lower() != "judge":
            raise StageError(
                "promote is Judge-approved only — pass --approved-by judge "
                f"(got '{approved_by}'); the Judge never auto-approves"
            )
        integration = self._require_integration(run, team)
        stage = self._find_stage(run, branch)
        if stage is None:
            raise StageError(f"No stage found for branch '{branch}' in run '{run}'")

        # Checkpoint the source worktree so nothing in-flight is lost.
        try:
            git.commit_all(Path(stage.worktree_path), f"[stage] pre-promote checkpoint: {branch}")
        except git.GitError as exc:
            logger.warning("pre-promote checkpoint failed for %s: %s", branch, exc)

        merged, output = git.merge_in_worktree(
            Path(integration.worktree_path), branch,
        )
        if not merged:
            registry = self._load_registry(run, team)
            registry.promotions.append(StagePromotion(
                run=run, branch=branch, approved_by="judge", note=note or "",
                merged=False, output=output,
                promoted_at=datetime.now(timezone.utc).isoformat(),
            ))
            self._save_registry(registry)
            raise StageError(
                f"Judge-approved promotion of '{branch}' failed (integration untouched):\n{output}"
            )
        record = StagePromotion(
            run=run, branch=branch, approved_by="judge", note=note or "",
            merged=True, output=output,
            promoted_at=datetime.now(timezone.utc).isoformat(),
        )
        registry = self._load_registry(run, team)
        registry.promotions.append(record)
        self._save_registry(registry)
        return record

    def discard(self, run: str, branch: str, team: str | None = None) -> bool:
        """Remove a stage's worktree and branch and drop it from the registry.

        The integration stage cannot be discarded — it is the run's mainline.
        """
        stage = self._find_stage(run, branch)
        if stage is None:
            return False
        if stage.kind == "integration":
            raise StageError(
                "the integration stage cannot be discarded — it is the run's mainline"
            )
        try:
            git.remove_worktree(self.repo_root, Path(stage.worktree_path))
        except git.GitError as exc:
            logger.warning("worktree remove failed: %s", exc)
        try:
            git.delete_branch(self.repo_root, stage.branch)
        except git.GitError as exc:
            logger.warning("branch delete failed: %s", exc)
        registry = self._load_registry(run, team)
        registry.stages = [s for s in registry.stages if s.branch != branch]
        self._save_registry(registry)
        return True

    # ------------------------------------------------------------------
    # Query / GC
    # ------------------------------------------------------------------

    def list_stages(self, run: str, team: str | None = None) -> list[StageInfo]:
        return self._load_registry(run, team).stages

    def gc(self, run: str, team: str | None = None) -> StageGCReport:
        """Drop registry entries whose branch and worktree are both gone.

        Live stages (branch exists, worktree registered) are verified and kept.
        """
        registry = self._load_registry(run, team)
        removed: list[str] = []
        kept: list[str] = []
        for stage in list(registry.stages):
            alive = (
                git.branch_exists(self.repo_root, stage.branch)
                and git.worktree_path_exists(self.repo_root, Path(stage.worktree_path))
            )
            if alive:
                kept.append(stage.branch)
            else:
                removed.append(stage.branch)
        if removed:
            registry.stages = [
                s for s in registry.stages if s.branch not in set(removed)
            ]
            self._save_registry(registry)
        return StageGCReport(run=run, removed=removed, kept=kept)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _stage_worktree(self, branch: str) -> Path:
        """Best-effort worktree path for *branch* from ``git worktree list``."""
        for wt in git.list_worktrees(self.repo_root):
            if wt.get("branch") == branch.removeprefix("refs/heads/"):
                return Path(wt["path"])
        raise StageError(f"No worktree found for branch '{branch}'")

    def _find_stage(self, run: str, branch: str) -> StageInfo | None:
        for stage in self._load_registry(run).stages:
            if stage.branch == branch:
                return stage
        return None