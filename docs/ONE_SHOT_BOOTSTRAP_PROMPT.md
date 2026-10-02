# ONE_SHOT_BOOTSTRAP_PROMPT — Optimized Build Prompt for the Zcode GLM Agent

> **Run `PRE_BOOTSTRAP_PROMPT.md` first** (cleanup + green baseline); when it prints `PRE-BOOTSTRAP COMPLETE`, come back here.
> Paste the **Full Prompt** into the agent that is currently ~60 % through the build.
> Use the **Compact Prompt** if its context window is tight (it points at the doc pack for detail).
> The pack is installed in the repo (`ANCHOR_POINTS.md` at root, the rest in `docs/`, index in `docs/PACK_INDEX.md`).
> The original authoring copy is in `C:\Users\ynotf\Downloads\ClawTeam`.

## What changed versus the original prompt, and why

| Original issue | Fix |
|---|---|
| Two products blended in one paragraph (swarm runtime vs. media panel) | Split into 8 numbered work packages with acceptance criteria |
| "Add a complete team" — no definition of complete | Roster, loops, and Shipped criteria in `SWARM_TEAM_SPEC.md` |
| "Never ask questions" and "build both ways" had no limits (risk: infinite loops, branch explosion, runaway spend) | Absolute-Blocker definition, fork thresholds and caps, budget governors |
| "Top apps" guidance was vague | Top-Apps Benchmark Rule with a written, auditable output |
| Agent was told *what* but could drift on *foundations* | `ANCHOR_POINTS.md` + explicit latitude list |
| No definition of "shipped" | Gate list in `TESTING_AND_ACCEPTANCE.md` |
| Presets named only by example | 20 + 20 presets with pipelines in `MEDIA_PRESETS_CATALOG.md` |
| OpenHands mentioned as a maybe | Time-boxed spike with objective adopt/reject criteria (`OPENHANDS_EVALUATION.md`) |
| Kids' safety not mentioned | Parent Gate, content policy, spend caps in `KEEP_IT_SIMPLE_SPEC.md` |
| "Keep it Simple" toggle ambiguous about where it lives | Board-wide toggle **and** a toggle on each of the two preset catalogs |

---

## Full Prompt (copy everything inside the block)

```
ROLE
You are the lead build agent for ClawTeam (D:\github\ClawTeam), ~60% complete, running as a
Cursor Full Agent. You may change, extend, or restructure the app however is best, subject
only to ANCHOR_POINTS.md. You are finishing this build in ONE autonomous run. Do not ask me
questions except an Absolute Blocker (docs/AUTONOMY_POLICY.md §3) — everything else is
decided via the Top-Apps Benchmark Rule, logged, and built. Report progress; do not wait for
replies.

MISSION (two products, one runtime)
(1) SWARM RUNTIME — a "single-bootstrap-prompt-to-ship" autonomous developer team, selectable
    in the Board's Active Swarm dropdown, with its own frictionless git-worktree staging layer,
    continuous critic agents, A/B explorer agents, a Judge, and a fork-both-ways rule.
(2) MEDIA PANEL — the image/video panel in the Board has a built-in one-shot prompt that runs
    on my kie.ai key (KIE_API_KEY env var), with Top-20 Developer and Top-20 Consumer preset
    catalogs. Consumer flagship: Pixar-style 3D-style character clones from photos, voice
    clones, and full movies built from those clones.
The Board AND BOTH preset catalogs carry a "Keep It Simple" toggle for my 11- and 14-year-old
kids (no code knowledge). Everything they build uses RGDS as its front end.

STEP 0 — READ THE DOC PACK (already installed in the repo; index: docs/PACK_INDEX.md)
a. Read in this exact order: ANCHOR_POINTS.md (repo root) → docs/ORIGINAL_PRODUCT_PROMPT.md
   (owner's verbatim product intent — wins over every paraphrase below it, including this
   prompt) → docs/STORAGE_AND_DATA_CONTRACT.md (CLAWTEAM_DATA_DIR, the always-fixed
   ~/.clawteam/config.json, PG assignment, memory wiring — verified against code) →
   BLUEPRINT.md → AGENTS.md → .rules/* → docs/PRODUCT_SPEC.md → docs/BUILD_PLAN.md →
   docs/AUTONOMY_POLICY.md → then the spec for the work package you are on. Existing docs
   (ARCHITECTURE/OPERATIONS/MEDIA_STUDIO/HANDOFF) stay; the *_ADDENDUM files extend them.
   docs/HYGIENE_REPORT.md records the pre-bootstrap baseline and known environment caveats —
   read it before trusting a `pytest` run on this machine.
b. Work on a new branch from the current one (e.g. ship/bootstrap) in a worktree; never push to `origin`.
c. Audit the repo against docs/BUILD_PLAN.md and write docs/GAP_REPORT.md: for each work
   package mark DONE / PARTIAL / MISSING with file evidence. Do NOT redo finished work.

WORK PACKAGES (acceptance criteria: docs/TESTING_AND_ACCEPTANCE.md)
WP1  `fullstack-commercial` team template + Active Swarm dropdown entry + `clawteam ship`.
WP2  Stage layer: one-command branch+worktree creation for lanes, forks, A/B experiments;
     integration branch; safe cleanup; Windows long-path safe.
WP3  Continuous critics + A/B explorers + Judge, with budget governors and stuck-detection.
WP4  Autonomy engine: Top-Apps Benchmark Rule, Absolute-Blocker parking (never halt),
     fork-both-ways with caps, decision log.
WP5  Keep It Simple mode (Board-wide, persisted) = one-prompt build mode; Parent Gate.
WP6  Media one-shot panel + capability registry + 20 Dev + 20 Consumer presets, each with a
     Keep-It-Simple variant; KIE adapters verified against docs.kie.ai at build time.
WP7  OpenHands: run the time-boxed spike in docs/OPENHANDS_EVALUATION.md. Adopt it as an
     optional executor engine if (and only if) it meets the adopt criteria; otherwise record
     why not and proceed natively. Either outcome is acceptable; an unrecorded one is not.
WP8  Tests, docs, hygiene fixes (docs/BUILD_PLAN.md §6), final ship report.

LATITUDE (you decide; log in docs/DECISION_LOG.md)
Module layout, new internal tools/languages (optional, never required to run the Board),
whether OpenHands is used, order of work packages, what to refactor, UI layout inside RGDS.
You may modify any non-anchor code, including the 60% already built, if it serves the goal.

HOW TO DECIDE (no questions)
1. Check ANCHOR_POINTS.md.
2. Apply the Top-Apps Benchmark Rule (AUTONOMY_POLICY.md §4): study 3-5 leading apps in the
   field, tabulate, pick.
3. If outcomes are materially different AND the benchmark is inconclusive, FORK: build both
   on separate branches to ship-ready (caps in AUTONOMY_POLICY.md §5); the Judge writes the
   comparison for me.
4. Otherwise choose, log, move on. A true Absolute Blocker (AUTONOMY_POLICY.md §3) is parked
   in one batched Blocker Card while all other work continues.

OPERATING RULES
- Work in git worktrees via the Stage layer; never edit the main checkout directly.
- Windows 11 native, subprocess backend, loopback only, no Docker dependency.
- Secrets only as env vars; never print/write values. Tokens only, no style literals.
- Evidence or it didn't happen: every completed WP cites test output or artifact paths.
- Commit small, checkpoint often. Push only to `fork`; never to `origin`.
- Respect budget governors; on a cap, wrap up gracefully and report.

DEFINITION OF DONE
All gates in docs/TESTING_AND_ACCEPTANCE.md §2 pass, including the two E2E demos:
 (a) KIS demo: the single sentence "make me a space shooter game" -> playable RGDS game in the
     preview, zero questions.
 (b) Pro demo: a one-paragraph SaaS brief -> tested full-stack app on an integration branch
     with critic/judge reports.
Final output: docs/SHIP_REPORT.md (what shipped, evidence, open forks awaiting my pick,
blocker cards, known gaps, cost summary). Then idle; do not loop forever.
```

---

## Compact Prompt

```
You are finishing ClawTeam (D:\github\ClawTeam, ~60% built) as a Cursor Full Agent in one
autonomous run — no questions except an Absolute Blocker (docs/AUTONOMY_POLICY.md §3).
1) The doc pack is already in the repo (index: docs/PACK_INDEX.md). Read ANCHOR_POINTS.md first — it is
   immutable unless I say so — then docs/ORIGINAL_PRODUCT_PROMPT.md (verbatim intent, wins over
   paraphrases) and docs/STORAGE_AND_DATA_CONTRACT.md (verified data/PG/memory wiring). Then
   docs/BUILD_PLAN.md; write docs/GAP_REPORT.md; skip what is done.
2) Build WP1-WP8 from docs/BUILD_PLAN.md: fullstack-commercial swarm in the Active Swarm dropdown +
   `clawteam ship`; worktree Stage layer; continuous critics + A/B explorers + Judge; autonomy engine
   (Top-Apps Benchmark, Absolute Blockers only, fork-both-ways with caps); Keep It Simple mode +
   Parent Gate; Media one-shot panel on KIE_API_KEY with 20 Dev + 20 Consumer presets (each with a
   KIS toggle); OpenHands time-boxed spike (adopt only if criteria met; log either way);
   tests/docs/ship report.
3) You may change anything not in ANCHOR_POINTS.md. Log decisions in docs/DECISION_LOG.md.
4) Done = docs/TESTING_AND_ACCEPTANCE.md §2 gates green + both E2E demos + docs/SHIP_REPORT.md. Then idle.
```
