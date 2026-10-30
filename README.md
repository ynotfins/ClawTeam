# ClawTeam — Control-Plane Deployment: Every Feature We Added

This is the **production deployment fork** of [HKUDS ClawTeam](https://github.com/HKUDS) (upstream
framework: config management, multi-user workflows, P2P transport, team templates — unchanged and
credited). On top of that base, this fork is a **Windows-native, fully autonomous software-building
runtime** with a local web control-plane (**the Board**) and a **Multimedia Studio**, serving two
audiences at once: **Pro** (commercial developers) and **Keep It Simple** (kids and non-technical
family), with neither degrading the other.

* The upstream ClawTeam product README is preserved in git history: `git show HEAD:README.md`.
* The swarm's canonical team-truth file now lives at `docs/SWARM_BLUEPRINT.md` (decision D-019).
* Companion documents: **[BLUEPRINT.md](BLUEPRINT.md)** (how every feature is built, wired, and
  tested) · **[CONTEXTBLOCK.md](CONTEXTBLOCK.md)** (what every feature does and outputs at its best).

**Open the app**: `scripts/windows/Start-Board.ps1` → Board at `http://127.0.0.1:8788`
(loopback-only; the desktop shortcut does the same). **Ship software**: `clawteam ship "<prompt>"
--mode pro|simple` — one prompt in, a spawned autonomous team out.

Test baseline: **685 collected (2026-10-27 audit), ~744 test functions at HEAD** — run with
`pytest --basetemp=.clawteam-local/pytest-tmp`.

---

## The features we added

### 1. Board — the web control plane

A stdlib-only Python server (`clawteam/board/`, `ThreadingHTTPServer`, no build tooling required)
serving a single-page app on `127.0.0.1:8788` with five views — **Board** (live kanban of every
team's tasks, streaming per-team updates over SSE with a shared TTL snapshot cache), **Tools**
(MCP servers + skills manager), **Models** (OpenRouter explorer), **Media** (the studio),
**Extract** (local OCR). The team selector can create a full `fullstack-commercial` team shell
from the Board itself (`POST /api/team/create`). A GitHub-only egress proxy lets the UI fetch
allow-listed upstream content while blocking loopback/private/metadata targets and redirects.

### 2. RGDS frontend & the zero-hardcoding design law

The entire UI runs on the vendored **R3lentless-Grind Design System 1.1.0**
(`clawteam/board/static/rgds/`, sha-locked). `design/theme.tokens.json` defines exactly four theme
modes (two light, two dark) served at `/api/theme`; **no color, gradient, shadow, radius, spacing,
or font literal may be hardcoded anywhere** — only design tokens. This is enforced by tests that
scan the UI for literals and fail the build if one appears (a real regression in board CSS was
found and fixed this way: one unclosed rule had silently unstyled half the app).

### 3. Tools & Models panels

**Tools** manages MCP servers and skills across repo/worker/user scopes — adding an MCP server is
validated (name pattern, https-or-loopback-only URLs) and written to both the repo and worker
configs at once. **Models** shows the OpenRouter topology: live model rankings, an autorouter
role table, model comparison, API-key health and spend, and a routing editor (`/api/openrouter/*`).
Missing keys are a first-class **dormant** state — the UI shows "not configured," never crashes.

### 4. Media pipeline core

The app-owned job engine behind every image/video/3D generation (`clawteam/media/`): jobs move
through fixed states (`draft → queued → running → provider_succeeded → downloading → succeeded`,
plus explicit `failed` / `timed_out` / `succeeded_provider_download_failed`), stored as atomic
per-job JSON with file locking. Every submission is **estimated first** (route + credits shown
before you spend); submits happen **exactly once** (cloud throttle, 5 s spacing — no double
charge); polling backs off exponentially; **outputs are downloaded into the local asset store
before a job is called `succeeded`**; a failed download never silently loses the result. Retry is
user-initiated and keeps completed pipeline stages; a board restart mid-job re-polls the in-flight
provider task instead of resubmitting. The provider boundary (`MediaProvider` protocol) keeps
every provider's payload format inside its own adapter.

### 5. Local GPU tier (ComfyUI bridge)

A ComfyUI provider (`clawteam/media/providers/comfyui_local.py`) that lazily boots ComfyUI
(hidden window, loopback :8188) on first use, runs a seeded SDXL workflow (1024², ~16 s), and is
the default (free) route for safe image kinds, falling back to cloud only if the GPU tier is down.

### 6. KIE cloud provider & model adapters

Cloud generation runs on the user's **kie.ai** key (`KIE_API_KEY`, name-only in configs): image
kinds on **flux1-kontext** (5 credits, live-verified), video on **MiniMax H3** (per-second
pricing, 4–15 s), upscaling on **Topaz** image/video models, plus a runway adapter. Each model
family gets its own pinned payload adapter built from verified docs (never one universal
schema). The provider records **actual** credits from each completed task (`creditsConsumed`)
and corrects the estimate table from live results. A dormant key = clean "not configured" health,
never a crash. Default swarm LLM routing (D-013) also runs through KIE for Claude-family chat,
with GLM-5.3 kept on the separate `openrouter-llm` profile.

### 7. Characters — reusable identity studio

The Characters tab turns one photo into a reusable character (`clawteam/media/characters.py`):
photo → **sculpt** (3D animated-film render) → **stylize** (big-studio character) as the canonical
identity; then **new looks** (identity-consistent variants, prompt auto-wrapped to keep the same
face/hair) and **5-second scenes** (animate from the canonical or any variant, playing inline as
thumbnails on the character card). Every asset is registered to the character with per-stage cost
summed from provider actuals (~10 credits to create, ~5 per look, ~12 per scene).

### 8. Self-hosted photo lane

Uploads for character work are **self-hosted** (no third-party host): the Characters tab uploads
a photo (magic-byte sniffed, 10 MB cap, jpg/png/webp) to a token-named local store with a 24 h
TTL (`clawteam/media/uploads.py`), served through the **only publicly reachable process** in the
system — a dedicated loopback photo host (:18790) behind a cloudflared tunnel
(`photos.miaknuckles.com`). Unknown tokens 404, expired tokens 410 (fail-closed), expired files
are swept by the media worker. **Animate-from-variant** re-hosts an existing look through this
lane server-side (provider URLs expire) so any variant can be animated fresh.

### 9. Easy Studio — one-click tiles (WP6)

Six plain-English tiles that hide the entire pipeline behind one click
(`clawteam/media/presets.py`): *Make a Picture*, *Change My Photo*, *Make My Photo Sharper &
Bigger* (Topaz image upscale), *Make a Video*, *Make My Video Sharper* (Topaz video upscale),
*Make My Photo Move*. Each tile pins the best model for the job, shows the credit cost up front,
validates its inputs, and is checked by a catalog validator (unique ids, verified models, kind
consistency, mandatory example text) — a tile that drifts from a real provider capability fails
the build, not the user.

### 10. Buddy guide (D-018)

Every family panel holds the user's hand: a **"What we need from you" checklist** with live ✓
marks that keeps the Make-It button disabled until every needed input exists; **"What you gave
us"** thumbnails of the exact photo/video uploaded; **"Here is what it can look like"** examples
drawn from the real asset library; and a **live progress bar with % and plain-language status**
("Sculpting your 3D character from the photo…", "Saving it to your library…") polled from the job
state every 3 seconds until done. Copy is grade-school plain; failures speak kid ("The photo did
not go through — let's try that again.").

### 11. 3D Studio — photo to rigged character (WP7/D-017)

A first-class Media tab that turns one photo into a **true 3D mesh asset** (Lane B — the UI never
presents stylized imagery as 3D): **Fal.ai** `tripo3d/h3.1/image-to-3d` generates a rigged-ready
GLB + preview, `fal-ai/meshy/rigging` adds a humanoid skeleton with a walking clip (rig failure
is non-fatal — the unrigged model still ships), and a **forensic vision QA**
(`google/gemini-2.5-pro` via OpenRouter) compares source photo vs preview and returns a strict
JSON verdict; a failed verdict triggers **one automatic regeneration** on a fallback model
(Hunyuan) before giving up. The rig preview becomes the character's canonical image, so the
existing "Make My Photo Move" lane immediately puts the 3D character in a movie.

### 12. Extract panel — local OCR/PDF

A fifth Board view wiring the six **local** IureOCR MCP tools (`ocr_file`, `extract_text`,
`pdf_info`, `render_page`, `edit_pdf_pages`, `ocr_languages`) through a stdio JSON-RPC bridge
(`clawteam/board/ocr_tools.py`) and `/api/ocr/*` routes — OCR text extraction, page rendering,
and PDF page editing (rotate/delete/keep/reorder) fully on-device: no network, no key, serialized
so the CPU-bound Tesseract is never run concurrently.

### 13. Stage layer (WP2)

Per-run git staging that makes parallel swarm work safe (`clawteam/stage/`): every ship run gets
`ship/<run>/integration` plus `lane/<role>`, `fork/<decision>/<option>`, and `ab/<experiment>`
branches, each in its own worktree under a short root (`D:\w\<run8>`, override
`CLAWTEAM_STAGE_ROOT`) with `core.longpaths` enabled. **Nothing reaches the integration branch
except a `stage promote --approved-by judge`** (impostors are rejected and integration is left
untouched); every promotion is audit-logged; discard and gc keep the tree clean. `clawteam ship`
creates the run's integration stage automatically.

### 14. Autonomy engine (WP4)

The no-questions law, as code (`clawteam/autonomy/`): **`decide()`** turns every non-blocker
decision into a `D-nnn` record (question, options, benchmark table, chosen, confidence,
rationale) appended to `decisions.jsonl` and mirrored into `docs/DECISION_LOG.md`; **Blocker
Cards** capture the only legitimate reason to interrupt the owner (impossible without
owner-only action, no safe default, all self-recovery tried) as `B-nnn` cards with batched
15-minute notifications — the swarm **never pauses**; the **Fork Controller** builds *both*
materially-different options as real stage branches when the Top-Apps Benchmark can't pick a
winner (max 3 open forks, 2 options each, ≤40 % of budget, no nesting), then records the winner
and discards the loser.

### 15. Critic loop, budget governors, stuck detection (WP3)

**Critic loop**: continuous defect scanning triggered every 5 minutes or by lane commits;
findings require evidence, dedupe by fingerprint within a 30-minute cooldown, and the Judge
triages ≥medium to the debug lane (lower severities are kept, never deleted). **Budget
governors**: every run has caps (wall-clock, tokens, credits, concurrency, open experiments;
separate Pro and Simple defaults) — 80 % stops new forks, 100 % triggers graceful wrap-up,
never a silent runaway. **Stuck detection**: tasks active but untouched for 20 minutes are
reported with the right fix — in_progress → respawn, pending → reassign — for the leader
watcher to execute.

### 16. Keep It Simple mode & Parent Gate (WP5)

A backend + Board routes for the kids' experience (`clawteam/kis/`, `~/.clawteam/kis.json`):
turning KIS **on** is free; turning it **off** requires the **Parent Gate** — a scrypt-hashed
PIN (never stored or logged in plaintext, 5 wrong attempts = 5-minute lockout). The same gate
approves the sensitive actions: disabling KIS, changing caps, publishing externally, approving
a person's photo or a voice clone, raising credit caps, deleting a project. Kid sessions run
under default caps (40 credits/run, 150/day, 45 min/run, 2 concurrent jobs) and stay local-only
by default. The policy snapshot served to the UI contains zero PIN material.

### 17. One-shot ship & the fullstack-commercial team (WP1/D-014)

`clawteam ship "<prompt>" --mode pro|simple` is the single entry point: it mints a run id,
creates the run's stage integration branch, records `run.json`, and launches the
**fullstack-commercial** team — a 19-role swarm (leader `plan`, architect, front/back-end devs,
QA, debug, security, devops, three critics, two A/B explorers, a Judge, an integrator, archive,
prompt-engineer) that works in parallel lanes under INTAKE → RESEARCH → PLAN → BUILD → HARDEN →
SHIP → IDLE phases, proves every step with evidence, and only promotes through the Judge. The
team is also creatable from the Board dropdown. The 6-lane `agentic-se` base template is
untouched.

### 18. Windows operations scripts

`scripts/windows/` runs the whole deployment natively: **Start-Board.ps1** (hidden board on
8788 + browser), **Start-PhotoTunnel.ps1** (idempotent cloudflared tunnel for the photo host),
**Start-Swarm.ps1 / Stop-Swarm.ps1** (fully hidden swarm supervisor with graceful stop),
**Open-Board-Desktop.ps1** (app-mode browser window with its own taskbar entry),
**Invoke-Hidden.ps1** (no console-flash process helper).

### 19. Commercialization contracts (WP9–11 — designed, not yet built)

The locked plan for shipping (D-014): **WP9** all keys stay on the owner's PC; the shipped exe
carries zero key material (provable by strings scan) and is a remote client of the local server
through an authenticated tunnel; **WP10** Stripe **$1/month** subscription gating
(checkout + webhook license states, paywall when unlicensed); **WP11** Windows exe packaging
(PyInstaller onedir, clean-profile run, build hash in the ship report). Contract-only today —
no code exists yet; the contracts live in `docs/BUILD_PLAN.md` §3b and anchors A8/A9/B7a/D7/D8.

---

## Where everything lives

| Surface | Location |
|---|---|
| Board server + UI | `clawteam/board/` (server.py, static/index.html, static/rgds/) |
| Media pipeline + providers | `clawteam/media/` (jobs, assets, router, characters, presets, threed, providers/) |
| OCR bridge | `clawteam/board/ocr_tools.py` + `/api/ocr/*` |
| Stage layer | `clawteam/stage/` + `clawteam stage` CLI |
| Autonomy engine (decide/blockers/forks/critics/governors/stuck) | `clawteam/autonomy/` + `clawteam autonomy` CLI |
| Keep It Simple + Parent Gate | `clawteam/kis/` + `/api/kis/*` |
| One-shot ship + team template | `clawteam/cli/commands.py` (`ship`, `launch`), `clawteam/templates/fullstack-commercial.toml` |
| Tests | `tests/` (board, media, photohost, stage, autonomy, wp3, wp5, wp6, wp7, board_ocr, templates, …) |
| Decision log / anchors | `docs/DECISION_LOG.md` (D-001…D-019) · `ANCHOR_POINTS.md` |
| Deep docs | `docs/ARCHITECTURE.md` · `docs/MEDIA_STUDIO.md` · `docs/AUTONOMY_POLICY.md` · `docs/KEEP_IT_SIMPLE_SPEC.md` · `docs/SWARM_TEAM_SPEC.md` · `docs/BUILD_PLAN.md` |

**Never**: push to upstream `origin`, write a secret value anywhere, hardcode a style value,
bind `0.0.0.0`, double-submit to a paid provider, or ask the human anything that isn't an
Absolute Blocker. Full law: `ANCHOR_POINTS.md`.
