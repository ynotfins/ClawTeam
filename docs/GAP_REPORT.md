# GAP_REPORT — Audit Against BUILD_PLAN (2026-10-21)

> Audit-first report per `docs/BUILD_PLAN.md` §2. Each row carries file evidence.
> Test baseline this pass: **650 passed / 2 skipped** (all 41 test files, run in 13
> small sequential groups per `docs/HYGIENE_REPORT.md` §0 — Process Lasso kills
> sustained-CPU full-suite runs ~7 s in). Baseline at handoff was 640/2 (`G1`);
> this pass added 10 WP1 tests and lost none.

## Work packages

| WP | Status | Evidence |
|---|---|---|
| WP1 — `fullstack-commercial` template, dropdown, `clawteam ship` | **DONE (this pass, part)** | Template: `clawteam/templates/fullstack-commercial.toml` (19 roles: plan + 18, loads via `clawteam template list`; roster asserts vs `docs/SWARM_TEAM_SPEC.md` §2). `clawteam ship`: `clawteam/cli/commands.py::ship` (run dir `.clawteam-local/runs/<run_id>/run.json`, reuses `launch_team`; AC-2 shape). Dropdown: `POST /api/team/create` in `clawteam/board/server.py` + "New: Full-Stack Commercial (Autonomous)" option in `#team-select` (`clawteam/board/static/index.html`). Tests: `tests/test_templates.py::TestFullstackCommercial` (7), `tests/test_spawn_cli.py::test_ship_cli_creates_team_and_run_record` + invalid-mode rejection, `tests/test_board.py::test_api_team_team_create` variants. NOT yet done: dropdown exercised on a *live* board restart (AC-1 UI tail), `--mode simple` beyond flag validation (WP5 dependency). |
| WP2 — Stage layer (`clawteam/stage/`) | **MISSING** | No `clawteam/stage/` directory. Needed: `stage create --lane\|--fork\|--ab`, `stage promote` (Judge-only), `stage discard`, `stage list`, `stage gc`; short worktree root `D:\w\<run8>\…`; `core.longpaths` (already `true` on this machine). Contract: `docs/STORAGE_AND_DATA_CONTRACT.md` §4. |
| WP3 — Critics, explorers, Judge | **MISSING (roles defined only)** | Roles + charters exist in the WP1 template; no scan loop, no scheduler waking critics on commit/5-min timer, no governors (`tokens/credits/wall-clock/concurrency`), no stuck detection. Spec: `docs/SWARM_TEAM_SPEC.md` §3–5. |
| WP4 — Autonomy engine | **MISSING** | No `decide()` benchmark-table writer, no Blocker Card writer, no fork controller/caps. `docs/AUTONOMY_POLICY.md` and DECISION_LOG format exist; engine code does not. |
| WP5 — Keep It Simple | **MISSING** | No `ui.keep_it_simple` config key, no Board-wide toggle, no Parent Gate, no Simple view. Spec: `docs/KEEP_IT_SIMPLE_SPEC.md`. Note: `clawteam ship --mode simple` (WP1) validates the flag only. |
| WP6 — Media one-shot + presets | **MISSING (pipeline core exists)** | Job/asset/character/photo-host pipeline: DONE (`clawteam/media/`, 52+21 tests green). Missing: `clawteam/media/presets/` registry, `pipelines.py`, 40 presets (2 catalogs), new KIE adapters (audio/voice, lip-sync, music, upscale, newer image/video families), movie pipeline, One-Shot box + Dev/Consumer catalog UI. Upscale lane: operator decision pending (options researched 2026-09-26, `docs/HANDOFF.md` §4.3). |
| WP7 — OpenHands spike | **DONE** | `docs/DECISION_LOG.md` D-003 + D-010 (ADOPT-ENGINE, optional; SDK 1.50.1 smoke 3/3; no Docker hard dep). Notes: `docs/OPENHANDS_AUDIT_2026-10-02.md`. |
| WP8 — Tests, docs, hygiene, ship report | **PARTIAL** | Tests: green (650/2, evidence above). Hygiene §6: fixed earlier — CLAUDE.md OpenMemory refs (gone), `.rules/security-secrets.md` (no `OPENMEMORY_API_KEY`), `desktop.ini` gitignored (line 22), `design-system.md` version text (says 1.1.0 vendored). Remaining: `BLUEPRINT.md` §2 archive charter + §7 still mention OpenMemory (only `plan` may edit — kickoff task `ae2eb942` owns it), `clawteam/board/static/rgds.bak-1.0.1/` backup dir still present (gitignored), `index.html` px fallbacks not re-checked this pass. `SHIP_REPORT.md`: MISSING (correct — nothing shipped through gates yet). |

## Hygiene + repair work done THIS pass (2026-10-21)

| Item | Evidence |
|---|---|
| `templates/agentic-se.toml` ask lane referenced retired `G:\Zcode\docs-store` | Fixed → `F:\\AgentCore\\runtime\\docs-store\\arabold` via agentcore-gateway arabold-docs (line ~119); `tomllib` parse verified |
| Same file, archive kickoff task referenced `oi-openmemory-prod` | Task subject fixed → "Initialize team memory (AgentCore facade via agentcore-gateway)…"; live F: task store subject updated to match (`task update 4c2f94b3`) |
| `~/.clawteam/config.json` `default_team` empty (Board started Disconnected) | Set to `dev-team` (scalar string only; no secrets — verified by reading the file) |
| `docs-lock.json` `tokens_css_sha256` stale (`d33884…` vs actual `425c87fb…`) | Known P0 from 2026-10-01 plan pass — **still open**, recorded here; hash-agreement test + fix queued behind the Governing-Doc unlock (no code consumes the field today) |

## Notable non-gaps (checked, NOT missing)

- Media pipeline, Board, RGDS 1.1.0 four themes, photo host 18790 + tunnel, KIE image/video/characters lanes: **verified working** (52 media + 21 board tests green; `/api/media/*` served live from F: root this pass).
- Data root: `CLAWTEAM_DATA_DIR=F:\AgentCore\runtime\clawteam` complete (28 assets / 2 characters / 10 jobs, sidecar `file` paths rewritten); `~/.clawteam` tree = stale backup (kept, not deleted).

## Recommended next (per BUILD_PLAN §4 order)

1. **WP2 stage layer** (unblocks everything dogfooding).
2. WP4 → WP3 (autonomy engine, then critic/explorer loops on top of stage).
3. WP5 KIS + Parent Gate; WP6 presets/one-shot; then hand WP5–WP7 to `fullstack-commercial` via `clawteam ship` (dogfooding rule §5).
4. Hygiene tail: BLUEPRINT §2/§7 OpenMemory text (plan-lane kickoff), `rgds.bak-1.0.1/` cleanup decision, docs-lock hash test.

## Blockers / operator decisions (per AUTONOMY_POLICY — money)

- **OpenRouter key for the swarm**: `OPENROUTER_API_KEY` (User env) returns **HTTP 401 "User not found"** from `https://openrouter.ai/api/v1/auth/key` — all 6 relaunched dev-team workers died of it on 2026-10-21 ~19:13 (claude transcripts: `API Error: 401 User not found`). Alternatives verified valid this pass (status only, values never read): `OPENROUTER_CODEX_API_KEY` (**$149.25 / $150 limit left**), `OPENHANDS_LLM_API_KEY` / `LLM_API_KEY` (**$63.16 of $50 soft limit — over limit**). Swarm restart is blocked on this choice (spend).
- KIE top-up (balance ~4 credits at last check) — separate decision, media lanes only.
- Upscale lane choice (a/b/c per HANDOFF §4.3) — still pending.