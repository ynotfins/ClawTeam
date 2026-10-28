# GOAL_MODE_PROMPT — Ship the ClawTeam Windows App (operator → agent)

Paste this as the **objective** when arming Goal Mode (`/goal <objective>`).
The goal persists until **every requirement below is true and verified** —
there is no deadline, token budget, or turn budget. The operator tests the
result tomorrow (2026-10-28). Work from current repo state; the 2026-10-27
audit lives in `docs/GAP_REPORT.md` (addendum at top).

## Objective (arm this)

Finish the ClawTeam build end-to-end and **ship it as a functional Windows
exe** for 2–3 family members: complete the remaining BUILD_PLAN work packages
(WP4 → WP3 → WP5 → WP6), then commercialization (WP9 key custody, WP10 Stripe
$1/month subscription, WP11 exe packaging), then the ship report — with every
acceptance item below proven by evidence, and the exe build reproducible from
this PC.

## Current state (verified 2026-10-27)

- DONE: board (RGDS 1.1.0, 5 views incl. Extract), stage layer (WP2), media
  pipeline + photo lane + minimax-h3 video defaults, default provider `kie`
  (D-013; OpenRouter keys verified working 2026-10-27), 685 tests collected.
- Remaining: WP4 (autonomy engine), WP3 (critic/explorer/Judge loops +
  governors + stuck detection), WP5 (Keep-It-Simple + Parent Gate), WP6
  (media presets registry + 40 presets + one-shot router + movie pipeline),
  WP9, WP10, WP11, then WP8 tail (`SHIP_REPORT.md` + hygiene).

## Requirements (each needs evidence in SHIP_REPORT.md)

**R1 — WP4 autonomy engine.** `decide()` writes Top-Apps benchmark tables +
decision-log rows (format: `AUTONOMY_POLICY.md` §6). Blocker Card writer →
`.clawteam-local/runs/<run>/blockers/*.md` + Board surface. Fork controller
enforces caps (≤3 open forks/run, 2 options each, ≤40% run budget).

**R2 — WP3 loops + governors.** Critics wake on (a) every lane-branch commit
and (b) a timer (default 5 min). Governors cap tokens/credits/wall-clock/
concurrency. Stuck detection: no task progress N minutes → reassign/respawn
via existing keepalive/leader_watcher. Findings carry evidence (file:line or
command output) or the Judge rejects them.

**R3 — WP5 Keep It Simple.** Global KIS toggle in the board header persisted
to `~/.clawteam/config.json` (`ui.keep_it_simple`). Simple view per
`KEEP_IT_SIMPLE_SPEC.md`. Parent Gate: PIN stored **hashed** in `~/.clawteam/`
(never plaintext). `clawteam ship --mode simple` reuses the same engine with
Simple defaults (Judge auto-picks fork winners).

**R4 — WP6 media presets.** `clawteam/media/presets/` declarative registry
(JSON/TOML) + loader + validator; `clawteam/media/pipelines.py` (each stage =
one job; pipeline references job ids; resumable). 20 Dev + 20 Consumer
presets per `MEDIA_PRESETS_CATALOG.md`, each with a KIS variant. New KIE
adapters (voice/TTS, lip-sync, music, upscale, newer image/video families) —
**verify each schema on docs.kie.ai at build time (E6 law), never from
memory** — each with mocked-HTTP tests. One-Shot box + Dev/Consumer catalog
UI on the Media tab with KIS toggles. Movie pipeline: script → storyboard →
per-shot image/video → voice → music → stitch (local FFmpeg).

**R5 — WP9 key custody.** All provider/API keys live ONLY on this PC's server
(User env / server config). The distributed exe contains **zero key material**
(prove with a strings scan: no `sk-`, no key-like patterns). The client is a
remote: it reaches the server over the network (Tailscale-family address is
acceptable) and inherits board/media/extract/stage functions. Key read/change
routes are **admin-only**; the client has no UI for them and the server
rejects non-admin calls. This PC remains the single control point (keys,
presets, teams).

**R6 — WP10 Stripe $1/month.** Create the $1/month price on this PC
(`STRIPE_API_KEY` env-only, never in files/git). Checkout → success →
license grant; webhook handles `checkout.session.completed`,
`customer.subscription.updated/deleted`; monthly expiry enforced. License
gate: client checks license on start + periodically; unlicensed ⇒ paywall
(Subscribe → Stripe Checkout); server honors `active`/`past_due`/`canceled`.
E2E in **Stripe test mode** (test card 4242…): subscribe → license active →
app usable; cancel → grace → blocked. Mocked webhook tests in the suite.

**R7 — WP11 exe packaging.** `scripts/windows/build-exe.ps1` builds the
client (`clawteam-client` entry point) with PyInstaller onedir (or
equivalent), bundling RGDS assets + templates; deterministic steps; SHA-256
of the build recorded in `SHIP_REPORT.md`. The exe runs on a **clean Windows
profile with no Python installed**. Ship demo: exe launches → connects to the
server → all 5 board views render → one demo each of media job, OCR extract,
stage list → unlicensed install shows the paywall.

**R8 — WP8 ship report.** `docs/SHIP_REPORT.md` written: per-WP status,
evidence (test output paths, live probe transcripts, build hash), known
limitations, operator test checklist for tomorrow.

**R9 — Laws hold.** `BLUEPRINT.md`/anchors untouched except by `plan` lane;
RGDS tokens only (no hardcoded colors — the design-law tests stay green);
secrets env-only (CI/repo grep clean of key values); push **only to `fork`**
(never HKUDS `origin`); additive modules; `docs-lock.json` updated for any new
dependency (Stripe SDK etc.) and `docs-version-guardian`-checked.

**R10 — Suite green.** Full `pytest --basetemp=.clawteam-local/pytest-tmp`
green (685+ collected; run in small sequential groups per
`docs/HYGIENE_REPORT.md` §0 — Process Lasso kills sustained full-suite runs).

**R11 — Dogfooding rule** (`BUILD_PLAN.md` §5): once WP4 works, remaining WPs
are built **by the swarm via `clawteam ship`** where practical; each run's
report links from `SHIP_REPORT.md`. If dogfooding fails, log the defect in
the runtime and fix it — that is the test.

**R12 — Docs lock-in.** `docs/GAP_REPORT.md` addendum updated as milestones
land; `CHANGELOG.md` entry per shipped work package; `DECISION_LOG.md` rows
for every non-obvious choice; `docs/PACK_INDEX.md`/`README` refreshed.

## Non-negotiables

- No questions to the operator except Absolute Blockers
  (`AUTONOMY_POLICY.md` §3) — decide via Top-Apps Benchmark and log it.
- Never guess version-sensitive APIs (E6): Stripe + KIE schemas verified
  against live docs before implementation.
- No secrets in the repo, config files, or the exe's bundled sources —
  env-var names only.
- The exe must never read provider keys from its own environment; it only
  talks to the server.

## Completion audit (before claiming the goal)

For every R1–R12: name the authoritative evidence (test output, live probe
transcript, strings-scan result, clean-profile run log) and verify it in the
**current** tree — not from memory. If any item's evidence is missing, weak,
or indirect, keep working; do not narrow the objective to what is already
done. Mark the goal complete only when every requirement is proven.

## Operator test (tomorrow)

1. Clean-profile VM (or a family machine): run the exe → paywall shows →
   subscribe (test card) → all 5 views work against this PC's server.
2. Try to find/change an API key in the client → nothing to find; admin
   routes rejected.
3. Rotate a key on this PC → client keeps working with zero reinstall.
4. Board demo: ship a tiny prompt through `clawteam ship`; watch stage
   branches appear; Judge-promote one lane.