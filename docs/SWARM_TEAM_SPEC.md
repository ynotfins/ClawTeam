# SWARM_TEAM_SPEC — `fullstack-commercial` Autonomous Developer Team

Template file to create: `clawteam/templates/fullstack-commercial.toml`. Existing `agentic-se` stays as-is (anchor F1).
Backend: `subprocess`, headless. Each role works in its own worktree via the Stage layer. Dropdown label: **Full-Stack Commercial (Autonomous)**.

## 1. Principles

1. One prompt in, shipped product out. 2. No human questions (see `AUTONOMY_POLICY.md`). 3. Everything is a task on the
existing board — visible, auditable. 4. Nothing reaches `ship/<run>/integration` without Judge approval + green gates.
5. Roles are additive to the 6 base lanes; the base lanes keep their meaning.

## 2. Roster

| Role (agent name) | Type | Count | Worktree | Charter |
|---|---|---|---|---|
| `plan` | leader/planner | 1 | main-adjacent (read/write BLUEPRINT only) | Turns the prompt into a PRD-lite + task DAG; rewrites BLUEPRINT §1/§3 each step; owns phase transitions; merges via Integrator |
| `architect` | planner | 1 | lane | Stack/architecture decisions using the Benchmark Rule; writes ADRs; decides fork points |
| `agent` | executor | 1 | lane | Primary implementation lane (kept for compatibility with BLUEPRINT §3) |
| `be-dev` | executor | 1–2 | lane | Back-end / data / API |
| `fe-dev` | executor | 1–2 | lane | Front end — **RGDS only** |
| `qa` | evaluator | 1 | lane | Writes/maintains tests, E2E (Playwright/device-e2e skills), runs gates |
| `debug` | debugger | 1 | lane | Reproduce→root-cause→fix; owns critic findings of severity ≥ medium |
| `ask` | researcher | 1 | lane | Top-Apps Benchmark research; library/API verification |
| `security` | evaluator | 1 | lane | Secret scan, dependency audit, authz/injection review of the diff |
| `devops` | executor | 1 | lane | Build scripts, packaging, local run scripts, CI config |
| `archive` | archivist | 1 | lane | Docs, changelog, memory via AgentCore facade (local only) |
| `prompt-engineer` | prompt optimizer | 1 | lane | Tunes role prompts from observed failures |
| `critic-code` | evaluator | 1+ | read-only worktree | Continuous: correctness, complexity, dead code, error handling, race conditions |
| `critic-design` | evaluator | 1 | read-only | Continuous: RGDS literal violations, a11y, responsive behavior, Keep-It-Simple readability |
| `critic-product` | evaluator | 1 | read-only | Continuous: compares against Top-Apps benchmark; flags missing table-stakes features |
| `explorer-a`, `explorer-b` | explorer | 2 | per-experiment worktrees | A/B agents: propose and trial better strategy/logic on **new branches** |
| `judge` | judge | 1 | read-only + integration promote | Arbitrates critic triage, A/B experiments, forks (Simple mode), and merges |
| `integrator` | executor | 1 | integration worktree | Performs Judge-approved promotions, resolves conflicts, runs gates |

Scale rule: default total concurrent live agents ≤ 8 (governor). Roles sleep when idle; critics/explorers are timer- and event-driven
so idle roles cost nothing.

## 3. Phases

`INTAKE → RESEARCH → PLAN → BUILD ⇄ CRITIQUE/EXPLORE → HARDEN → SHIP → (IDLE)`

| Phase | Exit condition |
|---|---|
| INTAKE | Prompt normalized; mode (pro/simple) set; budget set; run dir created |
| RESEARCH | Benchmark table for the product category exists (3–5 leading apps); table-stakes feature list written |
| PLAN | PRD-lite, architecture ADR, task DAG, fork points identified (if any), test strategy |
| BUILD | All MVP tasks complete on lanes; integration branch builds and unit tests pass |
| HARDEN | No open critic finding ≥ medium; E2E passes; security scan clean; RGDS scan clean |
| SHIP | Gates green; `SHIP_REPORT.md` written; (forks) comparison ready |

BUILD runs concurrently with CRITIQUE/EXPLORE — they never wait for BUILD to "finish".

## 4. Critic loop (continuous)

```
trigger: on commit to any lane branch  OR  every CRITIC_INTERVAL (default 5 min)  OR  phase change
scan(scope = diff since last scan + whole-repo rotating slice):
    run linters/type-checks/tests relevant to the slice
    review with role-specific checklist
    for each issue:
        fingerprint = hash(file, rule, normalized snippet)
        if fingerprint seen and not regressed: skip
        file Finding{severity, evidence, repro?, suggested_fix}
        severity >= medium  -> create task owned by `debug` (or the owning dev lane)
        severity == low     -> batch into a weekly-style "polish" task
        severity == blocker -> interrupt: inbox to owning lane + `clawteam runtime inject`
cooldown: a role cannot file more than N findings per scan (default 10); excess is batched
```
Severity: `blocker` (build/test broken, secret leak, data loss) · `high` (functional bug) · `medium` (likely bug, perf, a11y) · `low` (style, refactor).
A critic must include **evidence** (command output, failing test, or file:line) — "looks wrong" is rejected by the Judge.

## 5. A/B explorer loop (continuous)

```
every EXPLORE_INTERVAL (default 15 min) or when a critic reports repeated friction:
    pick a target (algorithm, module design, prompt, UX flow, performance hot-spot)
    hypothesis: "<change> will improve <metric> by <amount>"
    create ab worktree/branch via Stage layer from integration HEAD
    implement the alternative; write/extend a benchmark or test that measures the metric
    submit Experiment{hypothesis, metric, baseline, result, diff stats} to judge
```
- Two explorers deliberately take **different** approaches (A = conservative refactor, B = bolder redesign) on the same target when
  the Judge flags a hot-spot, so results are comparable.
- Max open experiments: 4 (governor). Experiments older than 2 h without a result are discarded.
- Explorers never merge; only the Judge promotes.

## 6. Judge

Inputs: critic findings, experiment results, fork comparisons, gate results.
Decisions: (1) triage findings (accept/reject/merge duplicates, assign owner), (2) promote/discard experiments, (3) approve
integration merges, (4) in Simple mode, auto-select fork winners; in Pro mode, produce the side-by-side for the owner.
Promotion rule: improvement ≥ threshold on the declared metric **and** no regression in gates **and** diff risk acceptable.
Every verdict is written to `experiments/` with the metric table and logged in the decision log. The Judge never edits product code.

## 7. Fork protocol (fork-both-ways)

Trigger: a `DecisionRecord` with ≥ 2 options that are **materially different** (different user-visible product, stack, or UX
paradigm) and Benchmark confidence < 0.7. Procedure:
1. `architect` writes `forks/<id>/spec.md` stating the question and both options.
2. Stage layer creates `ship/<run>/fork/<id>/a` and `/b` from the same commit, each with its own lane worktrees as needed.
3. Both are built **to ship-ready** (tests, docs, RGDS). Shared work done before the fork stays shared.
4. `judge` writes `comparison.md`: feature matrix, test/gate results, cost, complexity, benchmark alignment, recommendation.
5. Owner picks in the Board's Ship view (Pro) — or Judge auto-selects (Simple). The loser branch is archived, not deleted.
Caps: ≤ 3 open forks per run, 2 options each, total fork budget ≤ 40 % of run budget (see `AUTONOMY_POLICY.md` §5).

## 8. Messaging protocol

Reuse `clawteam inbox`. Message prefixes: `STEP DONE:`, `FIXED:`, `FINDING:`, `EXPERIMENT:`, `VERDICT:`, `FORK:`, `BLOCKER:`, `ANSWER:`,
`ARCHIVED:`, `PHASE:`. Critics/explorers message `judge`, not `plan`, to avoid flooding the leader.

## 9. Shipped criteria

A run is **Shipped** when all are true: gates in `TESTING_AND_ACCEPTANCE.md` §2 green on the integration branch; no open
finding ≥ medium; `SHIP_REPORT.md` written; forks (if any) have `comparison.md`; governor ledger closed. After Shipped, workers go
idle (`clawteam lifecycle idle`) and critics/explorers pause (anchor F3). A new prompt or owner message resumes them.

## 10. Template skeleton (illustrative — match the real schema in `templates/agentic-se.toml`)

```toml
[template]
name = "fullstack-commercial"
description = "Autonomous full-stack commercial developer team: builders + continuous critics + A/B explorers + judge"
command = ["claude"]
backend = "subprocess"

[template.leader]
name = "plan"
type = "planner"
task = """...phase machine, benchmark rule, fork protocol, governors... (compose from AUTONOMY_POLICY.md)"""

[[template.agents]]
name = "critic-code"
type = "evaluator"
task = """...continuous loop from §4; never exit; evidence required..."""
# ...one [[template.agents]] block per role in §2
```
Use `{team_name}` and `{goal}` placeholders exactly as the existing template does. Secrets rule and RGDS rule go in every role prompt.
