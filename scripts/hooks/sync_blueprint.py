#!/usr/bin/env python3
"""AfterWorkerSpawn hook: push canonical swarm files into the new agent's worktree.

ClawTeam creates each agent's git worktree from the committed HEAD, so untracked
canon files (BLUEPRINT.md, .rules/, design tokens, rule surfaces, MCP config) are
missing there. This hook copies them in at spawn time and writes a
.clawteam-workspace.json pointer so agents can find the canonical BLUEPRINT.md
(which only the `plan` lane rewrites) in the main checkout.

Runs with the workspace .venv python; registered in ~/.clawteam/config.json via
`clawteam hook add` (or scripts/apply_runtime_config.py). Stdlib only.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

CANONICAL_FILES = [
    "BLUEPRINT.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".cursorrules",
    ".mcp.json",
]
CANONICAL_DIRS = [
    ".rules",
    "design",
    ".agentcore",  # project_key marker so AgentCore hooks bind in worktree git roots
    os.path.join(".cursor", "rules"),
]


def _data_dir() -> Path:
    env = os.environ.get("CLAWTEAM_DATA_DIR", "").strip()
    return Path(env) if env else Path.home() / ".clawteam"


# 2026-09-16: worktree auto-enrollment into the AgentCore contract REMOVED per the
# operator's AgentCore client contract ("do not auto-enroll or weaken gates"; the
# control plane is no-touch). Spawned swarm agents run with an isolated
# CLAUDE_CONFIG_DIR (no AgentCore hooks), so they need no worktree enrollment.
# The .agentcore/project_key marker is still synced for interactive use.


def _find_worktree(team: str, agent: str) -> tuple[str, str]:
    """Return (worktree_path, repo_root) for a team/agent from the workspace registry."""
    registry = _data_dir() / "workspaces" / team / "workspace-registry.json"
    if not registry.is_file():
        return "", ""
    try:
        data = json.loads(registry.read_text(encoding="utf-8"))
    except Exception:
        return "", ""
    repo_root = str(data.get("repo_root", ""))
    for entry in data.get("workspaces", []):
        if entry.get("agent_name") == agent:
            return str(entry.get("worktree_path", "")), repo_root
    return "", repo_root


def _append_log(repo_root: Path, line: str) -> None:
    try:
        log_dir = repo_root / ".clawteam-local" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "sync_blueprint.log").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


def main() -> int:
    if os.environ.get("CLAWTEAM_EVENT_TYPE") != "AfterWorkerSpawn":
        return 0
    team = os.environ.get("CLAWTEAM_TEAM_NAME", "")
    agent = os.environ.get("CLAWTEAM_AGENT_NAME", "")
    if not team or not agent:
        return 0

    worktree, repo_root = _find_worktree(team, agent)
    if not worktree or not repo_root:
        _append_log(
            Path(repo_root) if repo_root else Path.home(),
            f"skip: no worktree/registry for {team}/{agent}",
        )
        return 0

    src = Path(repo_root)
    dst = Path(worktree)
    try:
        if src.resolve() == dst.resolve():
            return 0
    except Exception:
        return 0

    copied: list[str] = []
    for name in CANONICAL_FILES:
        s = src / name
        if s.is_file():
            try:
                shutil.copy2(s, dst / name)
                copied.append(name)
            except Exception:
                pass
    for rel in CANONICAL_DIRS:
        s = src / rel
        if s.is_dir():
            try:
                shutil.copytree(s, dst / rel, dirs_exist_ok=True)
                copied.append(rel)
            except Exception:
                pass

    try:
        (dst / ".clawteam-workspace.json").write_text(
            json.dumps(
                {
                    "repo_root": str(src),
                    "blueprint_canonical": str(src / "BLUEPRINT.md"),
                    "note": "BLUEPRINT.md here is a spawn-time snapshot; the canonical "
                    "live copy is blueprint_canonical (maintained by the plan lane).",
                    "team": team,
                    "agent": agent,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass

    _append_log(src, f"{team}/{agent}: synced {', '.join(copied) if copied else 'nothing'}")
    print(f"[sync_blueprint] {team}/{agent}: {', '.join(copied) if copied else 'nothing to copy'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
