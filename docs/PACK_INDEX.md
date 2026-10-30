# Autonomous Ship Runtime + Media Studio — Doc Pack Index

This pack tells a build agent exactly what to finish, what must never change, and how to prove it is done. It **extends** the
existing docs (`docs/SWARM_BLUEPRINT.md`, `BOOTSTRAP.md`, `ARCHITECTURE.md`, `OPERATIONS.md`, `MEDIA_STUDIO.md`, `HANDOFF.md`, `.rules/*`);
it does not replace them. It is installed in the repo; the original authoring copy is in `C:\Users\ynotf\Downloads\ClawTeam`.

## Start here

1. **[../ANCHOR_POINTS.md](../ANCHOR_POINTS.md)** — immutable foundations. Read first, re-read before every merge.
2. **[ORIGINAL_PRODUCT_PROMPT.md](ORIGINAL_PRODUCT_PROMPT.md)** — the owner's verbatim product intent. Wins over every paraphrase in this pack.
3. **[STORAGE_AND_DATA_CONTRACT.md](STORAGE_AND_DATA_CONTRACT.md)** — where state actually lives, verified against code (`CLAWTEAM_DATA_DIR`, PG, memory).
4. **[PRE_BOOTSTRAP_PROMPT.md](PRE_BOOTSTRAP_PROMPT.md)** — paste into the agent **first**: one-time cleanup edits + green baseline.
5. **[ONE_SHOT_BOOTSTRAP_PROMPT.md](ONE_SHOT_BOOTSTRAP_PROMPT.md)** — paste **second**: the optimized build prompt (full + compact).
6. **[GOAL_MODE_PROMPT.md](GOAL_MODE_PROMPT.md)** — paste **third** (2026-10-27): Goal Mode objective — finish WP4/WP3/WP5/WP6 + WP9/WP10/WP11 and ship the Windows exe; operator tests 2026-10-28.

## Index

| Doc | Audience | Purpose |
|---|---|---|
| [../ANCHOR_POINTS.md](../ANCHOR_POINTS.md) | everyone | Facts and laws that never change without the owner's written instruction |
| [ORIGINAL_PRODUCT_PROMPT.md](ORIGINAL_PRODUCT_PROMPT.md) | everyone | Owner's verbatim product intent (SSOT) — wins over every derived doc |
| [STORAGE_AND_DATA_CONTRACT.md](STORAGE_AND_DATA_CONTRACT.md) | engineers, ops | Data roots, `CLAWTEAM_DATA_DIR`, PG assignment, memory wiring — verified against code |
| [PRE_BOOTSTRAP_PROMPT.md](PRE_BOOTSTRAP_PROMPT.md) | owner → agent | Run first: hygiene edits (memory policy text, secrets table, .gitignore, BLUEPRINT), baseline tests, local commit |
| [ONE_SHOT_BOOTSTRAP_PROMPT.md](ONE_SHOT_BOOTSTRAP_PROMPT.md) | owner → agent | Run second: optimized build prompt + what changed from the original |
| [PRODUCT_SPEC.md](PRODUCT_SPEC.md) | PM, agents | Vision, personas, functional/non-functional requirements |
| [BUILD_PLAN.md](BUILD_PLAN.md) | lead agent | Baseline, gap-audit checklist, WP1–WP8 + §3b WP9–WP11 (key custody, Stripe $1/mo, exe), order, hygiene fixes, risks |
| [GOAL_MODE_PROMPT.md](GOAL_MODE_PROMPT.md) | owner → agent | Goal Mode objective + R1–R12 ship requirements + completion audit; arms `/goal` until the exe ships |
| [ARCHITECTURE_ADDENDUM.md](ARCHITECTURE_ADDENDUM.md) | engineers | New modules, interfaces, storage, APIs |
| [SWARM_TEAM_SPEC.md](SWARM_TEAM_SPEC.md) | engineers, `plan` | `fullstack-commercial` roster, phases, critic/explorer/judge loops, fork protocol |
| [AUTONOMY_POLICY.md](AUTONOMY_POLICY.md) | all agents | No-questions policy, Top-Apps Benchmark, Absolute Blockers, fork rule, governors |
| [KEEP_IT_SIMPLE_SPEC.md](KEEP_IT_SIMPLE_SPEC.md) | engineers, guardian | Simple mode, Parent Gate, safety policy, caps |
| [MEDIA_PRESETS_CATALOG.md](MEDIA_PRESETS_CATALOG.md) | engineers, designers | 20 Dev + 20 Consumer presets, schema, capability registry |
| [OPENHANDS_EVALUATION.md](OPENHANDS_EVALUATION.md) | lead agent | Objective spike + adopt/reject criteria |
| [TESTING_AND_ACCEPTANCE.md](TESTING_AND_ACCEPTANCE.md) | QA, agents | Ship gates, AC-1…AC-17, demos K/P/M, stub executor |
| [OPERATIONS_ADDENDUM.md](OPERATIONS_ADDENDUM.md) | operators | Env vars, ports, commands, disk, recovery |
| [DECISION_LOG.md](DECISION_LOG.md) | all | Append-only decisions, anchor challenges, open forks |

Files the **agent creates** during the build (not in this pack): `docs/GAP_REPORT.md`, `docs/SHIP_REPORT.md`,
`.clawteam-local/runs/<run>/…`.

## Reading order by role

- **Owner**: ONE_SHOT_BOOTSTRAP_PROMPT → ANCHOR_POINTS → DECISION_LOG (open forks) → SHIP_REPORT.
- **Lead agent**: ANCHOR_POINTS → ORIGINAL_PRODUCT_PROMPT → STORAGE_AND_DATA_CONTRACT → BLUEPRINT → PRODUCT_SPEC → BUILD_PLAN → the spec for the active WP → TESTING_AND_ACCEPTANCE.
- **Any swarm role**: ANCHOR_POINTS → AUTONOMY_POLICY → SWARM_TEAM_SPEC (own role) → `.rules/*`.
- **Guardian (parent)**: KEEP_IT_SIMPLE_SPEC → OPERATIONS_ADDENDUM §6.

## Known caveats of this pack

- Authored by reading the repo only; nothing was executed. Items tagged `[U]` or described as "verify" must be checked by the agent.
- OpenHands specifics and kie.ai model/endpoint availability (voice, lip-sync, music, upscale) were **not** verified; docs instruct build-time verification.
- Preset "top 20" rankings are editorial; credit costs are placeholders until live `creditsConsumed` is recorded.
- Command and module names are target interfaces; the agent may adjust them if it updates the docs and logs the change.
