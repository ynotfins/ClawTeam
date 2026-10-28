# BUILD_PLAN — Work Packages, Order, and Gap Audit

The agent is ~60 % done. **Audit first, build only what is missing.** Anchors: `ANCHOR_POINTS.md`.

## 1. Known baseline (verified by reading the repo)

| Area | Present | Where |
|---|---|---|
| Board (stdlib HTTP, SSE, 4 views, RGDS 1.1.0, 4 themes) | yes | `clawteam/board/` |
| 6-lane `agentic-se` swarm template | yes | `templates/agentic-se.toml` |
| Other team templates | yes | `clawteam/templates/{software-dev,code-review,harness-default,hedge-fund,research-paper,strategy-room}.toml` |
| Workspace/worktree manager (create, checkpoint, merge, cleanup) | yes | `clawteam/workspace/manager.py` |
| Harness (conductor, orchestrator, roles, strategies, phases, contracts) | yes | `clawteam/harness/` |
| Spawn backends (subprocess default on Windows) | yes | `clawteam/spawn/` |
| Media pipeline (jobs, assets, characters, router, photo host) | yes | `clawteam/media/` |
| KIE adapters: Flux Kontext (image), Runway (video) | yes | `clawteam/media/providers/kie.py` |
| Local ComfyUI provider | yes | `clawteam/media/providers/comfyui_local.py` |
| MCP server + tools | yes | `clawteam/mcp/` |
| Tests | 640 pass / 2 skip | `tests/` |

## 2. Gap audit checklist (agent fills `docs/GAP_REPORT.md`)

Mark each DONE / PARTIAL / MISSING with a file path or test as evidence.

| WP | Check |
|---|---|
| WP1 | `fullstack-commercial` template exists? Appears in `#team-select`? `clawteam ship` command exists? |
| WP2 | One-command fork/A-B worktree creation? Integration branch? Cleanup of stale worktrees? Long-path handling? |
| WP3 | Critic/explorer/judge roles defined? Continuous scan loop? Governors? Stuck detection? |
| WP4 | Benchmark rule enforced in prompts? Blocker-card mechanism? Fork caps? Decision log writer? |
| WP5 | Global KIS toggle + persistence? Simple-mode UI? Parent Gate? |
| WP6 | One-shot media prompt? Preset registry? 40 presets? KIS variants? New KIE adapters (audio/voice, lip-sync, music, upscale, video models)? Movie pipeline? |
| WP7 | OpenHands spike notes in `DECISION_LOG`? `ExecutorEngine` interface? |
| WP8 | Tests for all new code? Hygiene fixes (§6)? `SHIP_REPORT.md`? |
| WP9 | Keys only server-side? Client exe key-free (strings scan)? Admin-only key rotation? Remote client reaches server? |
| WP10 | Stripe $1/month product? Checkout + webhook + license gate? Keys env-only? |
| WP11 | Reproducible exe build script? Clean-profile run (no Python)? Connects + demos pass? Build hash in SHIP_REPORT? |

## 3. Work packages

### WP1 — Team template, dropdown, `clawteam ship`
- Add `clawteam/templates/fullstack-commercial.toml` (roster in `SWARM_TEAM_SPEC.md` §2). Keep `agentic-se` untouched.
- Make the Board team list include template-backed teams that have been created; ensure a "New: Full-Stack Commercial"
  entry or auto-created team appears in `#team-select`.
- `clawteam ship "<prompt>" --mode pro|simple [--budget …] [--no-fork]` in `clawteam/cli/commands.py` (or an additive module imported there).
- Acceptance: AC-1, AC-2.

### WP2 — Stage layer
- New module `clawteam/stage/` (additive) wrapping `clawteam/workspace/`: `stage create --lane|--fork|--ab`, `stage promote`,
  `stage discard`, `stage list`, `stage gc`.
- Branch naming: `ship/<run>/integration`, `ship/<run>/lane/<role>`, `ship/<run>/fork/<decision-id>/<option>`,
  `ship/<run>/ab/<experiment-id>`.
- Worktree root must be short (Windows path limit): default `D:\w\<run8>\…`; configurable; enable
  `core.longpaths` on the repo.
- Integration branch merges only via Judge-approved promotion. Conflicts route to `debug` lane.
- Acceptance: AC-3.

### WP3 — Critics, explorers, Judge
- Roles and loops per `SWARM_TEAM_SPEC.md`. Implement as harness roles + a scheduler that wakes critics on
  (a) every commit on a lane branch and (b) a timer (default 5 min).
- Governors in `clawteam/team/` or `clawteam/stage/governor.py`: tokens, credits, wall-clock, concurrency, max forks.
- Stuck detection: no task progress for N minutes → reassign or respawn via existing keepalive/leader_watcher.
- Acceptance: AC-4, AC-5.

### WP4 — Autonomy engine
- Prompt fragments + a `decide()` helper that writes benchmark tables and decision-log rows
  (format in `AUTONOMY_POLICY.md`).
- Blocker Card writer (`.clawteam-local/runs/<run>/blockers/*.md`) + Board surface; work continues around blockers.
- Fork controller enforcing caps and triggering paired stage creation.
- Acceptance: AC-6, AC-7.

### WP5 — Keep It Simple
- Board-wide toggle in the header; persisted in `~/.clawteam/config.json` (profile key `ui.keep_it_simple`).
- Simple view per `KEEP_IT_SIMPLE_SPEC.md`; Parent Gate (PIN stored hashed in `~/.clawteam/`, never plaintext).
- `--mode simple` reuses the same engine with Simple defaults (no forks surfaced unless owner opts in; auto-pick winner by Judge).
- Acceptance: AC-8, AC-9.

### WP6 — Media one-shot panel and presets
- `clawteam/media/presets/` declarative registry (JSON/TOML) + loader + validator; `clawteam/media/pipelines.py`
  for multi-stage orchestration on top of existing job store (each stage = one job; pipeline record references job ids; resumable).
- New KIE adapters (verify schemas on docs.kie.ai at build time; per-family): text-to-speech/voice clone, lip-sync/avatar,
  music, upscale, newer image/video families. Each adapter ships with mocked-HTTP tests.
- Intent router for free-text one-shot prompt (rules first, LLM via OpenRouter profile second; env-only keys).
- Movie pipeline: script → storyboard → per-shot image/video → voice → music → stitch with local FFmpeg (on PATH).
- UI: Media tab gets **One-Shot** box, **Dev** and **Consumer** catalogs, each with the KIS toggle.
- Acceptance: AC-10 … AC-13.

### WP7 — OpenHands spike
- Follow `OPENHANDS_EVALUATION.md`. Max 4 hours of agent time. Outcome logged as a decision either way.
- Acceptance: AC-14.

### WP8 — Tests, docs, hygiene, ship report
- See §6 and `TESTING_AND_ACCEPTANCE.md`.

### WP9 — Key custody: server-held, remote-controlled (operator directive 2026-10-27, D-014)
- **Keys never ship**: `KIE_API_KEY`/provider keys live ONLY on this PC's server side (User env / server
  config). The distributed client carries no key material — verify with a strings scan of the built exe.
- **Client = remote**: the exe is a client of the local server (HTTPS/Tailscale-family address), inheriting
  board/media/extract/stage functions over the existing routes; key-material routes are admin-auth-only.
- **Admin control stays here**: key rotation, presets, team control happen on this PC only; the client blocks
  any attempt to read/change keys (no UI surface, server rejects non-admin calls).
- Acceptance: strings scan of exe shows no `sk-`/key patterns; client works against server with zero keys in
  its environment; admin routes reject non-admin.

### WP10 — Commercialization: Stripe $1/month subscription (operator directive 2026-10-27, D-014)
- Stripe product **$1/month** (price created on this PC; `STRIPE_API_KEY` env-only, never committed).
- Checkout → success → **license grant**; webhook (`checkout.session.completed`,
  `customer.subscription.updated/deleted`) → license state; monthly expiry enforcement.
- **License gate**: client checks license with server on start and periodically; unlicensed ⇒ paywall screen
  (Subscribe button → Stripe Checkout); server honors `active`/`past_due`/`canceled`.
- Acceptance: E2E (test-mode) subscribe → license active → app usable; cancel → grace → blocked; mocked
  webhook tests; no keys in repo (CI grep).

### WP11 — Packaging: ship as a Windows exe (operator directive 2026-10-27, D-014)
- `scripts/windows/build-exe.ps1`: PyInstaller onedir (or equivalent) with RGDS assets, templates, and the
  client entry point `clawteam-client`; deterministic steps; build hash recorded in `SHIP_REPORT.md`.
- Client needs NO Python on the target machine; runs on a clean Windows profile (family recipients).
- **Ship criteria** (`TESTING_AND_ACCEPTANCE.md` §2-style): exe launches → connects to server → all 5 board
  views render (Board/Tools/Models/Media/Extract) → one demo of each: media job, OCR extract, stage list →
  license paywall shows for unlicensed install. Signed installer optional; antivirus false-positive notes
  recorded.

## 4. Suggested order (agent may reorder; log it)

`GAP_REPORT → WP2 → WP1 → WP4 → WP3 → WP5 → WP6 (registry+one-shot → dev presets → consumer presets → movie) → WP9 → WP10 → WP11 → WP7 (parallel, time-boxed) → WP8 (SHIP_REPORT)`

Rationale: Stage layer and team template are prerequisites for the swarm to build the rest of the product itself
(dogfooding). Once WP1–WP4 work, **hand WP5–WP7 to the `fullstack-commercial` team** and supervise.

## 5. Dogfooding rule

From the moment `clawteam ship` works, remaining WPs are built **by the swarm via `clawteam ship`**, not by the
lead agent typing code. Each such run's report is linked from `SHIP_REPORT.md`. If dogfooding fails, log the failure
as a defect in the runtime (that is the best test there is) and fix it.

## 6. Hygiene fixes to include (found during doc audit)

| Item | Fix |
|---|---|
| `CLAUDE.md` still references OpenMemory (`.rules/memory-openmemory.md`, MCP `openmemory`) | Align with `.rules/memory-local.md` |
| `BLUEPRINT.md` §4/§7 still reference OpenMemory; §1 Mission is "PENDING" | `plan` lane updates (only `plan` may edit BLUEPRINT) |
| `templates/agentic-se.toml` `archive` lane references OpenMemory | Switch to AgentCore facade per `.rules/memory-local.md` |
| `.rules/security-secrets.md` lists `OPENMEMORY_API_KEY` | Remove; add `KIE_API_KEY` |
| `.rules/design-system.md` says npm `@r3lentless/rgds-web` 1.0.1 while vendored is 1.1.0 | Reconcile text |
| HANDOFF says "636 green" in §6 vs 640 in §2 | Reconcile to actual count |
| `clawteam/board/static/rgds.bak-1.0.1/` backup dir inside static | Confirm excluded from literal scan; remove if unused |
| `desktop.ini` untracked at repo root | Add to `.gitignore` |
| `index.html` uses `--nfa-typography-*` fallbacks with px literals (e.g. `16px`) | Replace with RGDS typescale tokens if the literal scan allows; else document the exemption |

## 7. Risk register

| Risk | Mitigation |
|---|---|
| Agent runaway spend | Governors (F10), cost ledger, hard caps in every preset |
| Worktree explosion / disk | Max concurrent worktrees, `stage gc`, short root path |
| Critics create noise loops | Severity threshold, dedupe by fingerprint, cooldown, Judge triage |
| Fork explosion | Max 3 open forks per run, 2 options each |
| KIE schema drift | Verify at build time; mocked tests; `verified:false` pricing until live |
| Child safety | Parent Gate, content policy, local-only likeness/voice, consent attestation |
| Windows path/lock issues | Short worktree root, `core.longpaths`, retry-on-lock helpers (see `fileutil.py`) |
| Upstream merge pain | Additive modules (G3) |
