# CONTEXTBLOCK.md — What Each Feature Is For, and What It Outputs at Its Best

> **Scope**: the *goal* of every feature this fork added, what it **does when it works
> optimally**, and exactly **what it outputs** — files, states, UI surfaces, artifacts. Section
> numbers are shared with [README.md](README.md) (plain description) and
> [BLUEPRINT.md](BLUEPRINT.md) (build detail). When a feature degrades instead of failing
> (dormant keys, skipped stages, fallbacks), that behavior is stated too — a feature working
> *optimally* includes degrading honestly.
>
> The one-sentence product goal behind everything below: **one prompt in, a complete, tested,
> shippable product out — with a control plane a professional developer trusts and a media
> studio an 11-year-old can use, and no human questions in between except true Absolute
> Blockers.**

---

## 1. Board — the web control plane

**Goal**: give the owner one local window into everything the swarm and studio are doing,
without installing anything.

**Working optimally**: opening `http://127.0.0.1:8788` shows a live dashboard — every team,
every task, every inbox count — updating in real time without refresh; switching teams is
instant (cached snapshots, one collector pass shared across viewers); creating a
fullstack-commercial team from the dropdown produces the full team shell in one click; the
page never leaks a secret, never fetches a non-GitHub URL, and never styles itself outside the
theme.

**Outputs**: a rendered single-page UI (Board/Tools/Models/Media/Extract views); JSON
snapshots at `/api/overview` and `/api/team/<name>`; an SSE stream per team; a
`fullstack-commercial` team + members + 5 seed tasks when created from the UI; served static
assets and binary files from the local asset stores. Degradation: a broken team folder shows a
graceful fallback row, never a crash.

## 2. RGDS frontend & zero-hardcoding design law

**Goal**: one coherent, professional visual system across every surface (board, generated
apps, kid UI), so "simple" means fewer choices — never a different look — and so styling bugs
are impossible to ship.

**Working optimally**: all four themes (two light, two dark) render pixel-consistent from a
single token source; theme choice persists per browser; the animated dark background respects
`prefers-reduced-motion`; every component pulls colors/radii/shadows/spacing from tokens.

**Outputs**: `design/theme.tokens.json` (theme payload via `/api/theme`), the vendored RGDS
package with sha-locked provenance, and a **green literal scan** — the build output that
matters most here is a test result: "0 hardcoded style values found."

## 3. Tools & Models panels

**Goal**: manage agent tooling and LLM routing from the UI instead of hand-editing configs;
make a missing API key a visible, honest state rather than a mystery error.

**Working optimally**: adding an MCP server takes seconds and is immediately live for both the
repo and the worker configs; invalid or non-https entries are refused with a clear reason; the
Models view shows live rankings, key health, spend, and lets the operator flip routing without
touching files.

**Outputs**: updated `.mcp.json` + worker `.claude.json`; skills installed across scopes;
OpenRouter topology/routing state on screen; a **dormant** indicator (never an exception) when
`OPENROUTER_API_KEY`/`LLM_API_KEY` is absent.

## 4. Media pipeline core

**Goal**: spend money on generation safely — every credit accounted, nothing lost, nothing
double-charged, nothing called "done" that isn't on disk.

**Working optimally**: a submitted job always ends in one of the explicit terminal states; a
succeeded job **always has its output files in the local asset store**; polls back off politely;
the cloud is never hit more than once per job or more often than the spacing throttle; a board
crash mid-job costs nothing on restart (the in-flight provider task is re-polled, not
resubmitted).

**Outputs**: per-job JSON records with full cost trail — `cost_estimate_credits/usd`,
`cost_actual_credits/usd` (from provider-reported `creditsConsumed`), `pricing_table_version`,
`provider_task_id`, `seed`; binary assets + sidecars in the library; the special
`succeeded_provider_download_failed` state making a lost download visible and retryable.
Optimal end state of every generation: `succeeded` + local asset + honest actual cost.

## 5. Local GPU tier (ComfyUI)

**Goal**: make routine image generation free and instant by using the local GPU first.

**Working optimally**: the first image request boots ComfyUI invisibly (no window, no manual
step) and generates a seeded 1024² SDXL image in ~16 seconds at zero credit cost; subsequent
requests skip boot; the same `params.seed` reproduces the same image.

**Outputs**: 0-credit jobs (`pricing_table_version "local/1"`, `verified: True`), PNG assets in
the library, `comfyui-bridge.log`. Degradation: if the GPU tier is down, safe image kinds
transparently fall back to the cloud lane (with credits shown), and cloud-only kinds never
touch the local tier at all.

## 6. KIE cloud provider & model adapters

**Goal**: high-quality cloud image/video/upscale generation on the owner's kie.ai account,
with per-model payload correctness and live-corrected pricing.

**Working optimally**: each generation goes to the best default model for its kind
(kontext for images, MiniMax H3 for video, Topaz for upscaling); every completed task reports
its true credit cost, which feeds the estimate table; the balance is visible in health checks.

**Outputs**: provider task ids polled to completion; output URLs downloaded into local
assets; per-job actual costs; a pricing table whose verified rows carry live evidence
(`PRICING_VERSION`). Degradation: no `KIE_API_KEY` ⇒ provider reports **dormant** with an
empty balance slot, the UI disables cloud flows cleanly, and no request is attempted.

## 7. Characters — reusable identity studio

**Goal**: one photo becomes a durable character the family can reuse across looks and scenes
without paying for the identity twice.

**Working optimally**: a photo becomes a polished big-studio character in one pipeline
(sculpt → stylize, chained inputs, ~10 credits with per-stage actuals summed); every new look
keeps the same face and hair; every scene is registered to the character and plays inline on
its card; a mid-pipeline crash resumes without re-paying for finished stages.

**Outputs**: a `chr-…` character record — `canonical_asset_id/url`, `variants[]`,
`scenes[]` (each with `source` labels `variant`/`canonical`) — plus the stage-by-stage cost
trail in the job (`_stages`), and the finished assets in the library. A failed pipeline
retry re-uses completed stages and only re-runs the tail.

## 8. Self-hosted photo lane

**Goal**: let photo-driven cloud generation work without handing family photos to a third-party
upload host — the machine serves its own temporary public links.

**Working optimally**: uploading a photo returns a working public https URL within seconds;
that URL serves byte-identical content through the Cloudflare edge; after 24 h it is gone —
404 for never-existed tokens, **410 Gone** for expired ones (fail-closed), and the file itself
is swept off disk; animate-from-variant always gets a fresh link (provider URLs expire).

**Outputs**: token-named upload files + sidecars (`pho-…`), public URLs under
`photos.miaknuckles.com`, a sweeping media worker, and scene records with `source:"variant"`.
Degradation: with no `public_origin` configured, uploads succeed locally and the UI says so
instead of inventing a URL.

## 9. Easy Studio — one-click tiles

**Goal**: the "Apple product app" experience — the six most-wanted family media operations as
single buttons with zero jargon.

**Working optimally**: a kid clicks *Make My Photo Sharper & Bigger*, adds the photo, and the
tile runs the exact right model at the exact right settings with the cost shown before the
click; every tile in the catalog is guaranteed (by the validator) to match a real, verified
provider capability.

**Outputs**: one job per click with `requested_provider:"kie"` and the pinned model; the
validated 6-tile catalog at `/api/media/presets` (unique ids, mandatory example text); the
finished asset in the library. If a tile ever drifts from a real provider capability, the
**build fails** — that is the feature working.

## 10. Buddy guide

**Goal**: no family user is ever stuck wondering what to do or what is happening.

**Working optimally**: every family panel opens with a checklist that tracks exactly what's
still needed ("One more thing — you can do it!"), shows the photo/video the user actually gave,
shows real examples of the outcome, and then narrates the run live — percentage climbing and
plain-language status every 3 seconds until "All done! Your creation is saved in the library ✓".

**Outputs**: gated Make-It buttons (impossible to click incomplete), uploaded thumbnails, an
examples strip from the real library, live progress bars (including 3D sub-stages), and
kid-language failure copy that points a grown-up at the Jobs tab without scary words.

## 11. 3D Studio — photo to rigged character

**Goal**: the "photo becomes a real 3D character" promise, delivered as a true mesh asset
(Lane B) with the system checking its own work.

**Working optimally**: one photo → a rigged, walking-ready GLB character in the library in one
run; the forensic vision QA compares the result to the source photo and passes it; if it
doesn't, the pipeline silently regenerates once on the fallback model before reporting;
rigging failure still delivers the unrigged model (marked honestly); the character's canonical
image becomes the rig preview, so the very next click ("Make My Photo Move") puts the 3D
character into a movie.

**Outputs**: job kind `to3d` with the `_3d` state trail (generate/rig/qa), a character record,
three assets (mesh GLB `kind:"model3d"`, preview image, rigged GLB), `cost_actual_usd`, and a
QA verdict record. Degradation: QA key absent ⇒ QA skipped (`qa: null`), delivery proceeds;
generate failure ⇒ job `failed` with a retry available.

## 12. Extract panel — local OCR/PDF

**Goal**: paper and PDFs become text and images for the agents and the family, entirely
on-device.

**Working optimally**: any of the six OCR/PDF operations (OCR a file, extract text, page info,
render a page, edit pages, list languages) runs against the local IureOCR engine with a clean
typed form, serialized so the CPU is never oversubscribed, and returns both extracted text and
rendered page images.

**Outputs**: `POST /api/ocr/call` results normalized to `{text, images[]}`, a tool catalog +
server status at `GET /api/ocr/tools`. Degradation: IureOCR binary missing ⇒ a clean
"unavailable" status and a precise bridge error — never a hang, never a crash.

## 13. Stage layer

**Goal**: make parallel swarm development safe — nobody steps on anybody, and only
Judge-approved work reaches the integration branch.

**Working optimally**: every ship run gets an integration branch and as many lane/fork/A-B
worktrees as needed, on short Windows-safe paths; promotion happens only through
`--approved-by judge` (any impostor attempt is rejected and integration is untouched); every
promotion (success or conflict) is audit-logged; dead stages are gc'd.

**Outputs**: `ship/<run>/…` branches, worktrees under `D:\w\<run8>`, the stage registry
`runs/<run>/stages.json` with promotion audit rows, `run.json["stage"]`, and an integration
branch that contains **only** Judge-approved, gate-green merges.

## 14. Autonomy engine

**Goal**: implement the no-questions law as auditable machinery — every decision logged, every
interruption justified, every fork deliberate.

**Working optimally**: an agent facing a decision records a `D-nnn` row (question, options,
benchmark, choice, confidence) that appears in `docs/DECISION_LOG.md` automatically; a true
Absolute Blocker becomes a `B-nnn` card with exactly what the owner must provide and what ships
by default if there's no answer — while every other lane keeps working; a genuinely contested
decision becomes **both** options built as real branches, then a recorded winner and a
discarded loser.

**Outputs**: `decisions.jsonl` + mirrored decision-log rows; `blockers/index.json` +
`B-nnn.md` cards with batched notification state; `forks.json` ledger with winners. Optimal
behavior on any question: the swarm decides, logs, and continues — silence is a valid owner
answer (the stated ship-default is used).

## 15. Critic loop, budget governors, stuck detection

**Goal**: the swarm polices its own quality, its own budget, and its own liveness — no silent
runaways, no zombie tasks, no unnoticed defects.

**Working optimally**: critics scan every 5 minutes and on every lane commit; findings carry
evidence and dedupe instead of spamming; the Judge routes everything ≥ medium to the debug
lane and keeps (never deletes) the rest; at 80 % of any budget cap new forks stop; at 100 %
the run wraps up gracefully and writes its report; a task silent for 20 minutes gets exactly
the right intervention (respawn if it was in progress, reassign if it never started).

**Outputs**: `critic-state.json` findings (`CF-nnn` with fingerprints, triage state),
`governor.json` budget/used with soft-stop and wrap-up verdicts, `stuck.json` reports with a
reassign/respawn prompt map. Optimal end state: every run ends by **choice** (mission complete
or budget respected), never by exhaustion.

## 16. Keep It Simple mode & Parent Gate

**Goal**: the kids get a bounded, local-first experience that a parent controls with a PIN —
and nothing about a child is published or unlocked without that parent.

**Working optimally**: KIS turns on freely and turns off only behind the gate; a scrypt-hashed
PIN that is never stored or logged in plaintext; five wrong PINs lock the gate for five
minutes; sensitive actions (publishing, person-photo approval, voice-clone approval, cap
changes, project deletion) are each individually gated; kid sessions run under explicit caps.

**Outputs**: `~/.clawteam/kis.json` (enabled, caps, hashed PIN material, lockout state), a
clean policy snapshot for the UI with zero PIN material, and gate approvals as the durable
consent record for likeness/voice actions. Optimal behavior: the worst a child can do is spend
bounded credits locally; the gate answers "no" for them everywhere it matters.

## 17. One-shot ship & the fullstack-commercial team

**Goal**: the operator types a product prompt once; a 19-role autonomous team assembles, plans,
builds, critiques, judges, and ships it — with evidence at every step.

**Working optimally**: `clawteam ship "<prompt>" --mode pro|simple` produces, in seconds: a run
directory, an integration stage, a spawned team working in parallel lanes under
INTAKE→RESEARCH→PLAN→BUILD→HARDEN→SHIP→IDLE; critics and explorers work continuously during
BUILD; only Judge-approved, gate-green work merges; the mission ends when the ship criteria are
met and the workers idle — the product is complete and the operator was asked nothing.

**Outputs**: `runs/<run>/run.json` (prompt, mode, team, stage), the spawned team + tasks +
inboxes, stage branches per role, and (when the mission completes) a shippable result on the
integration branch plus a ship report. The base 6-lane template remains available and untouched.

## 18. Windows operations scripts

**Goal**: the whole deployment runs like a native Windows appliance — no consoles, no Docker,
no manual steps.

**Working optimally**: one shortcut opens the Board as an app window; the board, photo tunnel,
and swarm all start hidden and idempotently (re-running a script is always safe); stopping the
swarm is graceful (stop file, PID cleanup, optional data retention); a machine reboot needs
nothing more than launching the same scripts.

**Outputs**: hidden processes with logs under `.clawteam-local/logs/`, pid files, generated
runners under `.clawteam-local/runs/`, and a browser/app window on `127.0.0.1:8788`.

## 19. Commercialization contracts (WP9–11)

**Goal**: ship this product to 2–3 family members (then customers) as a $1/month subscription
**without ever letting a key leave this PC**.

**Working optimally (once built)**: the recipient's exe is a thin remote client; every key and
every rotation stays on the owner's PC, provably (strings scan of the build shows zero key
material); the client checks its license on start and periodically; unlicensed users see a
Subscribe button that opens Stripe Checkout; webhooks keep `active/past_due/canceled` truth on
the server.

**Outputs (planned)**: a PyInstaller onedir exe with a recorded build hash, Stripe
checkout/webhook integration with license state, and a SHIP_REPORT documenting the build. Until
built, the honest output is what exists today: the contract text in `docs/BUILD_PLAN.md` §3b
and anchors A8/A9/B7a/D7/D8 — no code claims, no fake gates.

---

## The whole, working end-to-end (the optimal story)

1. The owner (or a kid, via KIS) opens the Board — it's up, themed, and live.
2. A family member clicks an Easy Studio tile, uploads a photo, follows the buddy checklist,
   watches the progress bar, and gets a finished asset in the library — bounded by KIS caps,
   protected by the Parent Gate, never asked a technical question.
3. A developer types `clawteam ship "…" --mode pro` — a 19-role team forms on stage branches;
   decisions get logged, forks get built both ways, critics file evidence-backed findings, the
   Judge gates every merge, budgets wrap the run up gracefully, and the integration branch ends
   up containing a tested, shippable product.
4. If something is truly impossible without the owner, a Blocker Card says exactly what's
   needed and what ships by default — and everything else kept working the whole time.
5. Every credit spent is estimated first, charged once, reported honestly, and downloaded
   before anything is called done.

That is this fork, working optimally: **two audiences, one runtime, zero unanswered
questions.**
