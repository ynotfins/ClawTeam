# OPERATIONS_ADDENDUM — Running the Autonomous Ship Runtime

Extends the repo's `docs/OPERATIONS.md` (daily commands, recovery). Anchors: B1–B7, D1, F10.
Full data-root/PG/memory contract (verified against code): `docs/STORAGE_AND_DATA_CONTRACT.md`.

## 1. Environment variables (names only; values never stored)

| Variable | Used for | If missing |
|---|---|---|
| `CLAWTEAM_DATA_DIR` | ClawTeam data root (teams/tasks/costs/sessions/media) — this machine: `F:\AgentCore\runtime\clawteam` | falls back to `config.data_dir`, then `~/.clawteam` |
| `KIE_API_KEY` | all cloud media | media cloud lane **dormant**; local lane + non-media features work |
| `OPENROUTER_API_KEY` | swarm model routing, intent router fallback | swarm cannot spawn LLM agents; stub engine still runs tests |
| `BIFROST_MCP_VIRTUAL_KEY` | agentcore-gateway MCP | memory tools unavailable; local files still work |
| (OpenHands model key, if adopted) | engine | engine reports `available:false` |

Set with `[Environment]::SetEnvironmentVariable('NAME','value','User')`, then restart terminals. Verify presence with
`scripts/setup_local.ps1` (prints SET/MISSING only).

## 2. Ports (new services only; reserved ones are in `ARCHITECTURE.md` §5)

| Port | Service | Bind | Notes |
|---|---|---|---|
| 18800 | Ship preview server (serves a built product from its worktree for demos) | 127.0.0.1 | one per active preview, next free up to 18899 |
| 18801–18899 | Optional engine servers (e.g., OpenHands), preview servers | 127.0.0.1 | register each in this table when added |

## 3. Daily commands (additions)

```bash
# start the board (unchanged)
python -m clawteam board serve --port 8788

# one-shot builds
clawteam ship "make me a space shooter game" --mode simple
clawteam ship "B2B invoicing SaaS ..." --mode pro --budget-hours 6

# observe
clawteam ship list
clawteam ship show <run>
clawteam ship forks <run>                 # list forks + comparison paths
clawteam ship choose <run> <fork> <a|b>   # owner decision (Pro)
clawteam ship stop <run>                  # graceful wrap-up

# stage layer
clawteam stage list <run>
clawteam stage gc <run>
```
(Command names are the target interface; the agent may adjust spellings but must document the final ones here.)

## 4. Disk & worktrees (Windows)

- Worktree root default `D:\w\<run8>\...` (short). Set `git config core.longpaths true`.
- Cap: 8 concurrent worktrees (Pro) / 5 (Simple). `stage gc` runs automatically at phase change and after Shipped.
- Fork losers are archived under `.clawteam-local/runs/<run>/forks/<id>/archive/`, not deleted.
- Retention: runs older than 30 days are compressed by `stage gc --archive`.

## 5. Monitoring

- Board → Ship view: phase, agents, findings, experiments, forks, ledger (tokens/credits/time), blocker cards.
- Logs: `.clawteam-local/logs/` and `.clawteam-local/runs/<run>/logs/` (JSON lines). No secrets are ever logged; a log-scrubber test enforces this.
- Alerts: governor at 80 % and 100 %; stuck agents; blocker cards (batched).

## 6. Recovery

| Symptom | Action |
|---|---|
| Board restarted mid-run | Runs and pipelines resume from their JSON records; no resubmission (E2) |
| Agent stuck | Leader respawns with context recovery; check `exit_journal` |
| Orphan worktree | `clawteam stage gc <run>`; if locked, close handles and retry (Windows) |
| Budget hit | Read `SHIP_REPORT.md` "Remaining work"; start a continuation run with a new budget |
| KIE job failed | Retry from Jobs tab (strips only failed stage); refunds are provider-side |
| Merge conflict | `integrator` handles; else task to `debug` |
| Parent PIN forgotten | Owner deletes `pin_hash`/`pin_salt` from `~/.clawteam/kis.json` (requires local admin access; documented deliberately — no remote reset exists) |

## 7. Backups

`~/.clawteam/` and `.clawteam-local/runs/` are the state. Back them up before upgrades. Media assets are in `~/.clawteam/media/assets/`.

## 8. Upgrade procedure

1. Stop runs (`clawteam ship stop`). 2. Back up state. 3. Pull/merge on a branch. 4. Run the full suite + gates. 5. Re-vendor RGDS only via
`.rules/design-system.md` §5. 6. Restart Board.
