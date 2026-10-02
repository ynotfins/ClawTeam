# STORAGE_AND_DATA_CONTRACT — Where State Lives (Verified Against Code)

Extends `ANCHOR_POINTS.md` B5. Every path below was verified by reading `clawteam/` source
during this pass (tagged `[V]`), not assumed. Anchors: B3, B5, B7, D1, D3.

## 1. ClawTeam runtime data root — `CLAWTEAM_DATA_DIR`

`[V]` `clawteam/team/models.py::get_data_dir()`:

```python
def get_data_dir() -> Path:
    custom = os.environ.get("CLAWTEAM_DATA_DIR")
    if not custom:
        from clawteam.config import load_config
        custom = load_config().data_dir or None
    p = Path(custom) if custom else Path.home() / ".clawteam"
    p.mkdir(parents=True, exist_ok=True)
    return p
```

Priority: `CLAWTEAM_DATA_DIR` env var > `data_dir` key in `~/.clawteam/config.json` > default
`~/.clawteam`. This is the **only** root for: `teams/`, `tasks/`, `costs/`, `sessions/`,
`media/` (jobs, assets, characters — `clawteam/media/jobs.py::media_dir()`), and `inboxes/`
(nested under each team dir, which lives under this root — `clawteam/team/manager.py`).

**This run sets**: `CLAWTEAM_DATA_DIR = F:\AgentCore\runtime\clawteam` (Windows User
environment variable). Expected subtree once the runtime writes to it:

```
F:\AgentCore\runtime\clawteam\
  teams\<team>\...          # team config, members, inboxes
  tasks\<team>\task-*.json  # file-based task store (locked, atomic writes)
  costs\<team>\...
  sessions\<team>\...
  media\
    jobs\ assets\ characters\ pipelines\   # media pipeline state (WP6, not yet built)
  kis.json                                 # ← see §2 caveat: NOT under data_dir today
```

## 2. Fixed root that `CLAWTEAM_DATA_DIR` does **not** move — `~/.clawteam/config.json`

`[V]` `clawteam/config.py::config_path()`:

```python
def config_path() -> Path:
    """Fixed config location: ~/.clawteam/config.json (never affected by data_dir)."""
    return Path.home() / ".clawteam" / "config.json"
```

The scalar/profile config file (`ClawTeamConfig`: profiles, presets, hooks, `default_backend`,
etc.) is **always** `~/.clawteam/config.json` regardless of `CLAWTEAM_DATA_DIR`. This is a
deliberate code fact, not a bug to "fix" in this pass — `scripts/apply_runtime_config.py` and
`setup_local.ps1` write here. `KEEP_IT_SIMPLE_SPEC.md` §6/§11 and `ARCHITECTURE_ADDENDUM.md`
§3 describe `~/.clawteam/kis.json` as a sibling of `config.json` (same fixed-root reasoning);
WP5 must either (a) keep `kis.json` fixed at `~/.clawteam/` alongside `config.json` for
consistency with how the codebase already treats "machine config" vs. "run data", or (b) move
it under `get_data_dir()` if the owner later wants Keep-It-Simple state to follow the data
drive too. **Decision deferred to WP5** (not this hygiene pass); log whichever way it goes in
`DECISION_LOG.md`. Until WP5 exists, this is a documentation note only — no code changes here.

## 3. Repo-local runtime (gitignored) — `.clawteam-local/`

`[V]` `.gitignore` line `.clawteam-local/`. Lives at `<repo>/.clawteam-local/`:
logs, worker spawn config (`.clawteam-local/claude-config/`), the pytest basetemp
(`.clawteam-local/pytest-tmp`), archive (`inert — do not revive`,
`.clawteam-local/archive/family-20260923/`), and — once WP2 exists — `runs/<run-id>/*`
(`run.json`, `decisions.jsonl`, `findings/`, `experiments/`, `forks/`, `blockers/`, `logs/`).
Never under `CLAWTEAM_DATA_DIR`; this is repo-scoped scratch space, not shared runtime state.

## 4. Short ship worktrees (Windows long-path safety)

`[V]` `ARCHITECTURE_ADDENDUM.md` §3, `OPERATIONS_ADDENDUM.md` §4, `BUILD_PLAN.md` WP2:
worktree root default `D:\w\<run8>\...` (short path; `<run8>` = first 8 chars of the run id).
Not present in the codebase yet (WP2 is unbuilt) — this is the target contract the stage
layer must honor when built. `git config core.longpaths true` is required on this repo (see
`STEP 3` of this pass — confirmed `true` at both `--local` and `--global` scope on this
machine).

## 5. PostgreSQL

`[V]` `.rules/memory-local.md` §1: the existing loopback Postgres at `127.0.0.1:55433` is
**AgentCore's** canonical DB (PG, exact major version not re-verified this pass — treat the
version number in any older note as `[U]` until an agent runs `SELECT version();` against
it) — it belongs to **AgentCore control-plane, which this run must not touch.**

**Contract for ClawTeam**: when ClawTeam needs durable SQL storage (none of the verified
code today uses SQL — `task_store = "file"` is the only implemented backend per
`clawteam/config.py`), it gets a **dedicated database named `clawteam`** inside that same
`127.0.0.1:55433` instance (one Postgres server, multiple databases — this does **not**
require a new port or a new anchor; `ANCHOR_POINTS.md` B6 already reserves `55433` for
"loopback PG" generically, not exclusively for AgentCore). If database creation is blocked
(insufficient privilege, or the control-plane owner reserves database-create rights), the
fallback is a dedicated **schema** (`clawteam.*`) inside AgentCore's existing database
instead of a new database. **ClawTeam's own server process is the only writer** — no IDE SQL
client, no ad-hoc psql session from an agent, ever touches this DB directly; all access goes
through ClawTeam's own code path once WP6/WP2 need it.

This pass does **not** create the database or schema — that is a WP2/WP6-time action, and
creating/altering anything inside the shared AgentCore Postgres instance is explicitly outside
this run's "do not touch AgentCore control-plane" boundary. This section is contract-only.

## 6. Memory

`[V]` `.rules/memory-local.md`, `.mcp.json`: team memory is the AgentCore memory facade via
MCP `agentcore-gateway` (`http://127.0.0.1:8080/mcp`, Bearer `${BIFROST_MCP_VIRTUAL_KEY}` —
name only, never the value). **No OpenMemory/mem0, no Obsidian.** `.mcp.json` registers
exactly one MCP server for this purpose plus two unrelated dev-tool servers (`playwright`,
`comfyui`) — confirmed by reading the file this pass.

## 7. Migration note — `~/.clawteam` → `F:` drive

If any prior run already wrote state under the default `~/.clawteam` (the home-relative
fallback, since `CLAWTEAM_DATA_DIR` was unset before this pass — confirmed via
`[Environment]::GetEnvironmentVariable('CLAWTEAM_DATA_DIR','User')` returning empty), a future
agent that turns on `CLAWTEAM_DATA_DIR` should treat `~/.clawteam/teams`, `~/.clawteam/tasks`,
`~/.clawteam/costs`, `~/.clawteam/sessions`, and `~/.clawteam/media` as **candidates to copy**
(not move blindly — check for in-flight tasks/locks first) into the new
`F:\AgentCore\runtime\clawteam\` root before relying on the new location, so no team/task/media
history is silently orphaned. `~/.clawteam/config.json` and `~/.clawteam/kis.json` (if/when it
exists) stay at `~/.clawteam/` regardless (§2). This pass does not perform that copy — it only
sets the env var and creates the empty target directory so the next run picks it up cleanly
(no existing `~/.clawteam/teams|tasks|costs|sessions|media` were found on this machine during
this pass, so there is nothing to migrate yet).

## 8. Known worktree/enrollment friction (documented, not fixed this pass)

`scripts/hooks/sync_blueprint.py` copies `.mcp.json` into new worktrees at creation time.
Worktrees created **before** an `.mcp.json` change (e.g., before this pass, if `.mcp.json` is
ever edited) will carry a stale snapshot until re-synced. There is currently no "re-enroll an
existing worktree" command — only `clawteam workspace manager.py` worktree *creation* wires
it. Future stage-layer work (WP2) should add a `stage resync <run>` (or similar) step that
re-copies `.mcp.json` (and any other spawn-time config snapshot) into already-existing lane
worktrees, not just new ones, so a mid-run `.mcp.json`/env change doesn't leave stale workers
behind. Logged here and in `docs/HYGIENE_REPORT.md`; no code changes in this pass.
