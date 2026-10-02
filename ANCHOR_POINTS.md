# ANCHOR_POINTS.md — Immutable Foundations

> **Purpose**: stop drift. Everything here is a fixed fact or fixed law of this project.
> The build agent may add, refactor, replace, or delete anything **not** listed here.
> It may **not** change, weaken, bypass, or "reinterpret" anything listed here.
>
> **Change protocol**: an anchor changes only by an explicit written instruction from the
> owner (Tony / `ynotfins`), recorded as a row in `docs/DECISION_LOG.md` naming the anchor ID
> it supersedes. An agent that believes an anchor is wrong must (1) finish the work in a way
> that respects it and (2) log an `ANCHOR-CHALLENGE` entry in `docs/DECISION_LOG.md`.
> It does **not** unilaterally deviate.
>
> **Precedence**: owner's live instruction > this file > `BLUEPRINT.md` §3 > everything else.
> (`BLUEPRINT.md` stays canonical for swarm mechanics. On conflict, follow this file and log
> an `ANCHOR-CHALLENGE`.)
>
> **Tags**: `[V]` verified by reading the repo during this documentation pass ·
> `[O]` owner directive from the build request · `[U]` unverified — confirm before relying on it.

---

## A. Identity & scope

| ID | Anchor |
|---|---|
| A1 | The product is **ClawTeam**: a Windows-native, fully autonomous software-building runtime with a local web control-plane (the **Board**). `[V]` |
| A2 | Repo `D:\github\ClawTeam`. Work branch lineage `feat/dev-control-plane-multimedia-studio`. Push remote is `fork` (`ynotfins/ClawTeam`); `origin` (HKUDS upstream) is **read-only — never push to it**. `[V]` |
| A3 | Two audiences, one runtime: **Pro** (serious commercial developers) and **Keep It Simple** (the owner's 11- and 14-year-old children, no code knowledge). Neither experience may be degraded to serve the other. `[O]` |
| A4 | The runtime is **one-shot capable**: one prompt in → a complete, tested, shippable product out, with the agents resolving their own problems. `[O]` |
| A5 | The image/video **Media panel** is a first-class surface of the Board with a built-in one-shot prompt flow, powered by the user's **kie.ai API key** (`KIE_API_KEY`). `[O]` |
| A6 | The Media panel ships **two preset catalogs** — Top 20 Developer and Top 20 Consumer — and **both catalogs carry the "Keep It Simple" toggle**. `[O]` |
| A7 | The agent keeps **latitude** over *how* to build (language of new modules, internal structure, whether to adopt OpenHands, which refactors to do) as long as every anchor holds. `[O]` |

## B. Platform & runtime

| ID | Anchor |
|---|---|
| B1 | **Windows 11 native. Docker is never a hard dependency.** Anything needing Docker/WSL is an optional adapter that degrades to a native path. `[V]` |
| B2 | Spawn backend is **`subprocess`**, headless, hidden windows. `[V]` |
| B3 | Parallel work happens in **git worktrees** created/cleaned by `clawteam/workspace/`. Agents never edit the main checkout directly. `[V]` |
| B4 | The Board server is **stdlib-only Python** (`ThreadingHTTPServer`) on **`127.0.0.1:8788`**. Optional build tooling must not become required to *run* the Board. Replacing the server needs an `ANCHOR-CHALLENGE`. `[V]` |
| B5 | State roots are stable and env-overridable: the ClawTeam **data root** (teams, tasks, costs, sessions, inboxes, media jobs/assets/characters) resolves via `clawteam/team/models.py::get_data_dir()` — `CLAWTEAM_DATA_DIR` env var, else `config.data_dir`, else `~/.clawteam` (default). This machine sets `CLAWTEAM_DATA_DIR = F:\AgentCore\runtime\clawteam`. The **scalar config file** `~/.clawteam/config.json` (`clawteam/config.py::config_path()`) is a *separate, fixed* path — never affected by `CLAWTEAM_DATA_DIR` — and stays at `~/.clawteam/` regardless of the data-root setting; `~/.clawteam/kis.json` (WP5, not yet built) follows the same fixed-root pattern. `<repo>/.clawteam-local/` (logs, worker config, pytest basetemp, archive; gitignored) is unaffected by either and stays repo-local. Full contract: `docs/STORAGE_AND_DATA_CONTRACT.md`. `[V]` |
| B6 | Reserved ports are never reassigned: 8080 bifrost · 8188 ComfyUI · 8787 openclaw ingest · **8788 Board** · 18789 OpenClaw gateway · **18790 photo host** · 3300 SwarmRecall · 55433/65432 loopback PG. New services use **18800–18899** and are registered in `docs/OPERATIONS_ADDENDUM.md`. `[V]` |
| B6a | PG assignment: `127.0.0.1:55433` is one shared Postgres instance; AgentCore control-plane owns it and keeps its own canonical DB there (`.rules/memory-local.md`). ClawTeam gets its **own dedicated database named `clawteam`** inside that *same* instance — not a new port, not a new anchor-breaking service — or, if DB-create is blocked, a dedicated **schema** (`clawteam.*`) in AgentCore's existing DB. Only ClawTeam's own server process writes to it; no IDE SQL client, no ad-hoc psql from any agent. Creating the DB/schema is a WP2/WP6-time action by the product build, not this hygiene pass — this row is contract-only and must not be read as permission to modify the shared AgentCore Postgres instance today. `[O]` |
| B7 | **Loopback-only.** The only publicly reachable process is the photo host (18790 via cloudflared). Board API, orchestration APIs, previews of generated apps, and any OpenHands server bind `127.0.0.1`. `[V]` |
| B8 | Existing primitives are extended, never replaced: `clawteam task / inbox / workspace / lifecycle / runtime inject`, templates in `clawteam/templates/*.toml` and `templates/agentic-se.toml`. `[V]` |

## C. Design law (RGDS)

| ID | Anchor |
|---|---|
| C1 | Front end = **R3lentless-Grind Design System (RGDS)**, vendored at `clawteam/board/static/rgds/` (1.1.0, sha-locked in `PROVENANCE.md`). Never hand-edit vendored files; upgrade only by re-vendoring. `[V]` |
| C2 | **Zero hardcoding**: no color, gradient, shadow, radius, spacing, or font literal anywhere (CSS, inline `style`, SVG, charts, generated apps' markup). Only `var(--md-*)` tokens or board aliases. `tests/test_board.py` enforces this and stays green. `[V]` |
| C3 | Four theme modes only: `primary-light`, `secondary-light`, `primary-dark`, `secondary-dark` (legacy ids map via `legacyModeMap` in `design/theme.tokens.json`). No new theme names, no competing token system. `[V]` |
| C4 | **Rainbow is stroke-only**, never a fill; rainbow strokes sit under an *opaque* padding-box fill; motion respects `prefers-reduced-motion`. `[V]` |
| C5 | Every UI product the swarm builds for Keep-It-Simple users **uses RGDS** as its front end (token theme system). `[O]` |
| C6 | The Board's own Keep-It-Simple UI is 100 % RGDS. "Simple" means fewer choices and larger targets, not a different visual system. `[O]` |

## D. Security, secrets, safety

| ID | Anchor |
|---|---|
| D1 | Secrets exist **only** as Windows User-scope environment variables (`KIE_API_KEY`, `OPENROUTER_API_KEY`, …). Never in files, logs, prompts, memory, fixtures, frontend assets, or generated apps. Config references the variable **name** (`${ENV}`). `[V]` |
| D2 | The UI never receives a key value; the server expands env references. A missing key is a first-class **dormant** state, never a crash and never worked around. `[V]` |
| D3 | All memory/storage/DB is **local** (AgentCore facade via MCP `agentcore-gateway`, local files, loopback DBs). No OpenMemory/mem0, no Obsidian, no cloud memory. `.rules/memory-local.md` and `AGENTS.md` win over stale mentions in `CLAUDE.md`/`BLUEPRINT.md` §4/§7. `[V]` |
| D4 | Provider payloads never cross `clawteam/media/providers/`. UI sees normalized job/asset shapes. Adapters are per model family — **never one universal payload**. `[V]` |
| D5 | **Likeness & voice safety**: uploading a person's photo or cloning a voice requires an explicit on-screen consent attestation. In Keep-It-Simple mode these actions are **local-only by default** and gated by the **Parent Gate** (see `docs/KEEP_IT_SIMPLE_SPEC.md`); nothing of a child user is published via the public photo host without Parent Gate approval. `[O]` + safety default |
| D6 | Generated code from any agent is untrusted until it passes the gates in `docs/TESTING_AND_ACCEPTANCE.md`. Agents never run destructive commands outside their own worktree. |

## E. Media pipeline laws (implemented — preserve)

| ID | Anchor |
|---|---|
| E1 | Job states are app-owned: `draft → queued → running → provider_succeeded → downloading → succeeded` (+ `failed`, `timed_out`, `succeeded_provider_download_failed`). Presets compose jobs; they never invent states. `[V]` |
| E2 | **No double-charge**: submit exactly once; poll with backoff (fast window → ×1.5 → 30 s cap); recovery re-polls the existing provider task; retry is user-initiated. `[V]` |
| E3 | **Download-before-complete**: outputs are copied into the local asset store before a job is `succeeded`. `[V]` |
| E4 | **Estimate before submit**: every generation and every preset shows route + credit estimate first; actuals come from the provider. A multi-stage preset shows a *total* estimate and enforces a **hard cap**. `[V]` + `[O]` |
| E5 | **Lane honesty**: stylized 3D-*looking* imagery is Lane A; true 3D mesh assets are Lane B. UI copy says "3D-style" unless a Lane B provider produced the asset. `[V]` |
| E6 | Every new KIE model gets its own adapter after its schema is verified in `docs.kie.ai` **at build time**; pricing stays `verified: false` until a live task reports `creditsConsumed`. `[V]` |

## F. Swarm & autonomy laws

| ID | Anchor |
|---|---|
| F1 | Lanes `plan · agent · debug · ask · archive · prompt-engineer` remain valid. New roles/teams are **additive**; `agentic-se` keeps working. `[V]` |
| F2 | `BLUEPRINT.md` stays canonical for swarm mechanics; only `plan` rewrites it; §3 is the live agent prompt. `[V]` |
| F3 | Worker loops poll tasks + inbox, report `STEP DONE`, and checkpoint their worktree. A *mission* ends when the Shipped criteria are met (`docs/SWARM_TEAM_SPEC.md` §9); workers then idle, not spin. `[V]` + `[O]` |
| F4 | "Done" requires **evidence** (test output or artifact path). `[V]` |
| F5 | **No questions.** Swarm agents never ask the human anything except an **Absolute Blocker** (`docs/AUTONOMY_POLICY.md` §3). All other decisions follow the **Top-Apps Benchmark Rule**. `[O]` |
| F6 | **Fork law**: when two or more options yield *materially different* products and the Top-Apps Benchmark cannot pick a clear winner, build **both** on separate branches/worktrees through to ship-ready; a Judge produces a side-by-side for the owner's final decision. `[O]` |
| F7 | **Continuous critique + continuous exploration + Judge**: critic agents scan the codebase continuously and file defects in real time; A/B agents continuously seek better strategies/logic on their own branches/worktrees; one Judge arbitrates. Nothing reaches the integration branch without Judge approval **and** green gates. `[O]` |
| F8 | The full-stack commercial developer team (`fullstack-commercial`) is selectable in the Board's **Active Swarm dropdown** (`#team-select`). `[O]` |
| F9 | A single entry point — `clawteam ship "<prompt>" --mode pro\|simple` and the Board's equivalent — bootstraps the entire team from one prompt. `[O]` |
| F10 | Every autonomous run has **budget governors** (tokens/credits/wall-clock/concurrency). Hitting a cap triggers graceful wrap-up, never a silent runaway and never a question. |

## G. Engineering baseline

| ID | Anchor |
|---|---|
| G1 | Test baseline **640 passed / 2 skipped** at handoff; it may only grow. On this machine use `--basetemp=.clawteam-local/pytest-tmp`. A previously green test gone red is the agent's regression. `[V]` |
| G2 | The media pipeline stays stdlib-only. Any new third-party dependency needs a one-line justification in `docs/DECISION_LOG.md`. `[V]` |
| G3 | Upstream (HKUDS) framework code is modified minimally; prefer additive modules to keep upstream merges feasible. |
| G4 | Nothing is "shipped" while `pytest`, the RGDS literal scan, or the secret scan is red. |

## H. Never

1. Push to `origin`, or force-push any shared branch.
2. Write a secret value anywhere.
3. Hardcode a style value.
4. Revive `.clawteam-local/archive/family-20260923/` (inert by design).
5. Bind any service to `0.0.0.0`.
6. Silently double-submit to a paid provider.
7. Block on a human question that is not an Absolute Blocker.
8. Rewrite history on a branch another worktree depends on.
9. Present a Lane A image as a true 3D asset.
10. Remove the Keep-It-Simple toggle from either media catalog or from the Board.

---

## Pre-merge anchor self-check (every agent, every merge)

- [ ] No edits under `clawteam/board/static/rgds/` (unless re-vendoring with updated provenance)
- [ ] RGDS literal scan green
- [ ] Secret scan green; no secret values in diff
- [ ] Every new listener binds `127.0.0.1` and is registered in `OPERATIONS_ADDENDUM.md`
- [ ] Test count ≥ baseline and all green
- [ ] Active Swarm dropdown entry, Keep-It-Simple toggles (Board + both catalogs), both preset catalogs still present
- [ ] Non-obvious decisions logged in `docs/DECISION_LOG.md`
