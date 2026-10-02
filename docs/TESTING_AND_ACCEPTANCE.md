# TESTING_AND_ACCEPTANCE — Gates, Acceptance Criteria, and Demos

Anchors: F4, G1, G4, C2, D1, D6.

## 1. Test strategy

| Layer | Tooling | Scope |
|---|---|---|
| Unit | `pytest` (existing suite, 640 pass / 2 skip baseline) | stage layer, governor, decision engine, KIS, presets, pipelines, adapters (mocked HTTP) |
| Contract | `pytest` | `ExecutorEngine` fake; `MediaProvider` protocol; preset schema |
| Integration | `pytest` + temp git repos | Stage layer against a real temp repo; fork creation; promotion; gc |
| UI | `tests/test_board.py` patterns + Playwright MCP (web) | toggle persistence, catalogs render, no color literals, Simple view hides forbidden elements |
| E2E demos | scripted run with a **stub executor** (CI-safe) + one **live** run (owner machine) | §4 |
| Security | secret scan, loopback-bind assertion, path-traversal tests | §2 |

Run on this machine: `pytest --basetemp=.clawteam-local/pytest-tmp`.

## 2. Ship gates (all must be green on the integration branch)

| Gate | Command / check | Pass |
|---|---|---|
| G-TEST | `pytest --basetemp=.clawteam-local/pytest-tmp` | all pass; count ≥ 640 + new; skips ≤ 2 unexplained |
| G-RGDS | RGDS literal scan (test in `tests/test_board.py`; extend to generated apps and new Board code) | 0 literals |
| G-SECRET | scan diff + tree for key-like strings and known env var *values*; assert none | 0 findings |
| G-BIND | assertion test: every listener in code binds `127.0.0.1` | pass |
| G-ANCHOR | pre-merge anchor checklist (`ANCHOR_POINTS.md`) ticked in the PR/decision log | complete |
| G-DEP | new third-party deps each justified in `DECISION_LOG.md` | complete |
| G-DOCS | docs updated; links resolve; no stale OpenMemory references added | pass |
| G-CRITIC | no open Finding ≥ medium | 0 |
| G-E2E | demos AC-8 and AC-3/4 (§4) pass | pass |

## 3. Acceptance criteria

| ID | Criterion | Evidence |
|---|---|---|
| AC-1 | `fullstack-commercial` template validates and loads (`clawteam template list/show`), and **appears in the Active Swarm dropdown** after team creation | template test + UI screenshot/DOM assertion |
| AC-2 | `clawteam ship "<prompt>" --mode pro\|simple` creates team, run dir, stage layer, plan; exits 0 quickly and run proceeds in background | CLI test + run.json |
| AC-3 | Stage layer: create lane/fork/ab worktrees+branches with one command; promote only via Judge-approved path; `gc` removes merged/discarded; works with long paths | integration tests on temp repo |
| AC-4 | Critic loop: injecting a deliberate bug (e.g., failing test / color literal) into a lane branch yields a Finding **and** a `debug` task within one scan interval | scripted test w/ stub executor + timer override |
| AC-5 | Explorer/Judge loop: an experiment is created on its own branch, scored on a metric, and promoted or discarded with a recorded verdict | experiment record + branch evidence |
| AC-6 | Zero questions: static check that role prompts contain the no-questions clause, and runtime test that a mocked ambiguous task results in a logged decision, not an inbox question to the human | prompt lint + test |
| AC-7 | Fork: a mocked inconclusive decision creates two branches built to a stub "ship-ready" state, produces `comparison.md`, respects caps (3 forks/2 options/40 % budget); Simple mode auto-picks | integration test |
| AC-8 | Keep It Simple toggle: persists across restart; present in Board header **and** both catalogs; shares one state; turning off requires Parent Gate once a PIN exists; Simple view hides branch/diff/model/token UI | UI + API tests |
| AC-9 | KIS demo: "make me a space shooter game" → playable RGDS game within caps, zero questions, friendly progress, Result card | live run log + screenshot; stub-executor variant in CI |
| AC-10 | Preset registry: 40 presets validate; each has a Simple block; ranks unique per catalog | schema tests |
| AC-11 | Pipelines: mocked-provider run of one Dev and one Consumer preset end-to-end; total estimate shown; cap breach pauses; restart resumes without duplicate submit | tests |
| AC-12 | New KIE adapters (those verified to exist) have per-family payload tests with mocked HTTP; unverified slots render "Coming soon" and are covered by a test | tests |
| AC-13 | One-shot box: free-text routes to a preset or composed pipeline with estimate; Lane A copy never says "3D model" | tests + copy lint |
| AC-14 | OpenHands decision recorded with criteria results (adopt/helper/reject) and `ExecutorEngine` seam exists with `NativeEngine` | decision record + tests |
| AC-15 | Pro demo: one-paragraph SaaS brief → tested full-stack app on the integration branch with critic and judge reports, no questions | live run + SHIP_REPORT |
| AC-16 | Hygiene fixes in `BUILD_PLAN.md` §6 applied (or explicitly deferred with reason) | diff + log |
| AC-17 | Docs: every doc in this pack either installed in `docs/` or merged; `SHIP_REPORT.md` exists | file check |

## 4. End-to-end demos

### Demo K (Keep It Simple)
1. Fresh Board, set Parent Gate PIN, turn Keep It Simple ON.
2. Type: **"make me a space shooter game"** → press **Make it**.
3. Expect: friendly progress stages; no terminal/branch/model text; completes ≤ 45 min (live) or ≤ 2 min (stub); a **Play** button opens the game
   on loopback; game uses RGDS tokens (scan green); zero questions in inbox/UI; at least one self-fixed issue noted in the under-the-hood report.
4. Type "make the ship faster and add a boss" → incremental change on the same run; **Go back** reverts it.

### Demo P (Pro)
1. Pro mode. Prompt: *"B2B invoicing SaaS: auth, customers, invoices with PDF export, Stripe-style payment links (sandbox), dashboard, tests, CI."*
2. Expect: research benchmark table; PRD-lite + ADRs; lanes build in worktrees; critics file ≥ 1 finding that is fixed; at least one A/B experiment
   judged; optionally one fork (e.g., server-rendered vs SPA) with `comparison.md`; integration branch passes all gates; `SHIP_REPORT.md`.

### Demo M (Media — owner's flagship chain, live, small)
`consumer.pixar-clone` → `consumer.voice-clone` (consented, owner's own voice) → `consumer.talking-clone` → a **30-second** `consumer.movie-from-clone`.
Record actual credits consumed per stage into the pricing table (`verified: true`). Spend ≤ the owner's stated cap.

## 5. Stub executor for CI

Provide a deterministic `StubEngine` (implements `ExecutorEngine`) that applies pre-scripted file edits per task id, simulates failures (e.g., a failing
test on first attempt), and emits usage numbers. This lets CI exercise phases, critics, forks, governors, and Simple mode without any LLM or spend.

## 6. Regression guard

A single `tests/test_anchors.py` encodes machine-checkable anchors: loopback binding, no `0.0.0.0`, no secrets, RGDS scan, presence of
the dropdown template, both catalogs, the KIS toggle element ids, `origin` never used as a push target in scripts, port registry (18800–18899 for new services).

## 7. Evidence format (completion messages)

```
STEP DONE: WP4 — decision engine + blocker cards
Evidence: pytest -q → 712 passed, 2 skipped (was 640/2); new tests: tests/test_ship_decisions.py (24)
Artifacts: clawteam/ship/decision.py, .clawteam-local/runs/r-…/decisions.jsonl
Anchors: self-check ticked (see DECISION_LOG D-0031)
```
