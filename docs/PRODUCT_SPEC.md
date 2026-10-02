# PRODUCT_SPEC — ClawTeam Autonomous Runtime + Media Studio

Status: target spec for completing the build. Read `ANCHOR_POINTS.md` first; anchors override this file.

## 1. Vision

A Windows-native, fully autonomous software-building runtime. A person types **one prompt**; a coordinated
team of agents plans, builds, critiques, tests, explores alternatives, and ships — working in isolated git
worktrees, deciding for itself, and surfacing only finished results and fork comparisons. A built-in media
studio turns a single kie.ai API key into image, video, character, and movie production through one-shot
presets.

## 2. Personas

| Persona | Needs | Mode |
|---|---|---|
| **Pro developer** (owner; serious commercial apps) | Full control: branches, diffs, cost, agent logs, model routing, test gates, fork comparisons | Pro (default) |
| **Daughter, 11** | Says "make me a game / a website"; sees it appear; no jargon | Keep It Simple |
| **Son, 14** | Believes he knows code; wants to tweak; must not break things | Keep It Simple (guard-railed, "peek under the hood" is read-only) |
| **Parent/owner as guardian** | Spend caps, content safety, approve photo/voice use | Parent Gate |

## 3. Product surfaces

1. **Board** (`127.0.0.1:8788`) — views: Board, Tools, Models, Media, plus new **Ship** (one-shot launcher + run
   monitor + fork comparison). Header carries the global **Keep It Simple** toggle and Active Swarm dropdown.
2. **Swarm runtime** — `fullstack-commercial` team and the `clawteam ship` CLI.
3. **Media panel** — one-shot prompt box, Dev catalog, Consumer catalog, Library, Jobs, Characters, Movies.
4. **Generated products** — apps/games/sites the swarm builds; RGDS front end; preview on loopback.

## 4. Functional requirements

### FR-SWARM — autonomous team
- FR-S1 `fullstack-commercial` appears in Active Swarm; selecting it shows its lanes live.
- FR-S2 `clawteam ship "<prompt>" [--mode pro|simple]` creates the team, stage layer, plan, and runs to Shipped.
- FR-S3 Stage layer creates/cleans branches + worktrees with one command; supports lane, fork, and A/B kinds.
- FR-S4 Critics run continuously (see `SWARM_TEAM_SPEC.md`); defects appear as tasks within one scan cycle.
- FR-S5 A/B explorers propose and trial alternatives on their own branches; the Judge decides promotions.
- FR-S6 Autonomy: no questions except Absolute Blockers; benchmark-driven decisions; fork-both-ways with caps.
- FR-S7 Governors: token/credit/wall-clock/concurrency budgets with graceful wrap-up.
- FR-S8 Every run emits `SHIP_REPORT.md`, `DECISION_LOG` entries, and (if forked) a comparison dashboard.

### FR-KIS — Keep It Simple
- FR-K1 A global persisted toggle (per Board profile) switches Pro ↔ Simple UI and run mode.
- FR-K2 Simple mode = one big prompt box, one "Make it" button, a live progress story, a result card.
- FR-K3 Simple mode never shows branches, diffs, model names, token counts, or stack traces; shows friendly equivalents.
- FR-K4 Simple runs inherit hard spend/time caps and the content policy (`KEEP_IT_SIMPLE_SPEC.md`).
- FR-K5 Both media catalogs expose the toggle; Simple variants hide knobs, choose safe defaults, and cap cost.

### FR-MEDIA — media studio
- FR-M1 One-shot prompt box: free text → intent classification → matching preset(s) or custom pipeline → estimate → run.
- FR-M2 40 presets (20 Dev, 20 Consumer) defined declaratively (`MEDIA_PRESETS_CATALOG.md`), each with a
  Simple variant and a cost cap.
- FR-M3 Capability registry maps preset stages to KIE model adapters and local ComfyUI where cheaper/safe.
- FR-M4 Character Studio extends the existing flow: photo → 3D-style canonical → variants → scenes → **movie**
  (storyboard → shots → stitched edit) with optional **voice clone** narration/dialogue.
- FR-M5 Lane honesty and likeness/voice consent (anchors E5, D5).
- FR-M6 All laws of E1–E4 hold for multi-stage presets (single submit per stage, resumable pipelines).

### FR-OH — OpenHands (optional engine)
- FR-O1 Evaluated by a time-boxed spike; adopted only if criteria in `OPENHANDS_EVALUATION.md` pass.
- FR-O2 If adopted it sits behind an `ExecutorEngine` interface; the native engine remains available.

## 5. Non-functional requirements

| Area | Requirement |
|---|---|
| Platform | Windows 11 native, no Docker dependency, Windows long-path safe worktrees |
| Security | Loopback only; secrets env-only; generated code sandboxed to its worktree; secret scan in CI |
| Reliability | All pipelines resumable after Board restart; atomic writes; no double-charge |
| Performance | Board p95 API < 200 ms (non-media); SSE latency < 2 s; up to 8 concurrent worktrees by default |
| Accessibility | Keyboard-first, focus rings via RGDS tokens, `prefers-reduced-motion`, min touch target for Simple mode |
| Observability | Structured JSON logs under `.clawteam-local/logs/`, per-run cost ledger, decision log |
| Maintainability | Additive modules; tests for every new module; docs updated with code |

## 6. Success metrics

- KIS demo and Pro demo (see `TESTING_AND_ACCEPTANCE.md`) pass unattended.
- Zero questions asked in either demo.
- ≥ 1 critic-found defect fixed autonomously per demo run (proves the loop is live).
- Test suite ≥ baseline + new tests; RGDS and secret scans green.
- A fork run produces two ship-ready branches and a Judge comparison.

## 7. Out of scope (this release)

True 3D mesh generation (Lane B provider slot only), public hosting of generated apps, multi-user auth,
non-Windows runtimes, cloud memory services.

## 8. Glossary

**Anchor** immutable foundation · **Board** local web control-plane · **Fork** two-branch build of a
materially different decision · **Judge** arbiter agent · **KIS** Keep It Simple · **Lane A/B** stylized vs true 3D ·
**Parent Gate** guardian approval step · **RGDS** R3lentless-Grind Design System · **Stage layer** branch+worktree
staging/execution layer · **WP** work package.
