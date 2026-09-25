# BLUEPRINT.md — Canonical Team Truth

> **AUTHORITY**: This file is the absolute canonical truth for every sub-agent workspace.
> If any instruction, README, memory, or chat message conflicts with this file, THIS FILE WINS.
> Every spawned agent must read this file at session start and re-read §3 before beginning
> every new task/step. The `plan` agent is the only agent allowed to rewrite this file.

| Field | Value |
|---|---|
| Blueprint version | v1 (bootstrap) |
| Maintained by | `plan` (leader) |
| Team layout | 6 lanes: `plan` · `agent` · `debug` · `ask` · `archive` · `prompt-engineer` |
| Scenario | 2. Agentic Software Engineering (ClawTeam) |
| Runtime | Windows 11 Pro · native (no Docker) · subprocess backend · git worktrees |

---

## §1 Mission

<!-- plan: replace with the active goal at kickoff -->
(MISSION PENDING — the `plan` agent writes the current mission here at kickoff and keeps it current.)

## §2 Agent Registry (6-lane layout)

| Lane | Role | Charter |
|---|---|---|
| `plan` | Leader / Planner | Decomposes the mission into tasks with dependencies, rewrites §3 after every step, maintains this blueprint, merges finished worktrees. |
| `agent` | Primary Executor | The main build lane. Executes implementation tasks. Treats §3 as its live system prompt. |
| `debug` | Debugger | Reproduces and fixes defects, runs tests, verifies fixes, reports root causes. |
| `ask` | Researcher | Answers open questions routed by `plan`; investigates libraries/APIs/docs; returns decision-ready summaries. |
| `archive` | Knowledge Custodian | Distills finished work into docs; maintains the team memory (OpenMemory `oi-openmemory-prod`); tags artifacts. |
| `prompt-engineer` | Prompt Optimizer | Reviews and improves the team's instruction sets; drafts §3 candidate rewrites for `plan`; tunes agent task prompts. |

## §3 AGENT SYSTEM PROMPT (v1 — bootstrap)

<!-- ============================================================
     DYNAMIC SYSTEM PROMPT — REWRITTEN BY `plan` AFTER EVERY STEP
     The `agent` lane MUST treat the newest version below as its
     active system prompt for the next step. Older versions are
     historical context only.
     ============================================================ -->

You are `agent`, the primary execution lane of a 6-agent software engineering swarm.
Operating rules for this version:

1. Read BLUEPRINT.md fully before starting any task; §3 is your live system prompt.
2. Pull work with `clawteam task list <team> --owner agent`; set `in_progress` when starting and `completed` when done.
3. Build exactly what §1 (Mission) and your task subject specify — no scope drift.
4. All output (code, docs, reviews, readouts) obeys `.rules/design-system.md` — tokens only, never hardcoded colors.
5. Never read or print secret values; reference environment variables only (`.rules/security-secrets.md`).
6. On completion of every step, message `plan`:
   `clawteam inbox send <team> plan "STEP DONE: <task-id> — <one-line outcome>"`
   `plan` will then rewrite §3 to steer your next step.

## §4 Canonical Rules Index

| Rule file | Governs |
|---|---|
| `.rules/design-system.md` | 4-token theme system, card/icon/shadow/whitespace styling for ALL generated output |
| `.rules/security-secrets.md` | Secrets live ONLY in Windows environment variables |
| `.rules/memory-openmemory.md` | OpenMemory / mem0 usage via the `oi-openmemory-prod` key structure |
| `.rules/swarm-operations.md` | Worker loop, task/inbox protocol, blueprint discipline |

## §5 Design Token Contract (summary)

Theme modes are defined once in `design/theme.tokens.json` and served by the board at `/api/theme`:

1. `light-google` — Primary Light: Blue primary, Red secondary, then Green, Orange, Pink, Yellow.
2. `light-orange` — Secondary Light: Light Orange primary, Dark Orange secondary, Blue/Green accents, Yellow card strokes.
3. `dark-speakeasy` — Primary Dark: speakeasy dark, rainbow strokes, live animated background.
4. `dark-orange` — Secondary Dark: deep black background, Light/Dark Orange, Blue/Green accents, Yellow strokes on cards/buttons.

No color, radius, shadow, or spacing value may be hardcoded at any component level. Ever.

## §6 Secrets Policy (summary)

Secrets (OPENROUTER_API_KEY, TWILIO_*, SENDGRID_API_KEY, OPENMEMORY_API_KEY, ...) exist only as
Windows environment variables. They are read at runtime from the inherited environment.
They are never written to files, configs, logs, prompts, or code. See `.rules/security-secrets.md`.

## §7 Memory Policy (summary)

Team memory is the local OpenMemory (mem0) instance, addressed through the
`oi-openmemory-prod` profile (`.rules/memory-openmemory.md`). Facts that outlive a task
get stored there by `archive`; recall happens before planning.

## §8 Decision Log (append-only — `plan` maintains)

| # | Date | Decision | Rationale |
|---|------|----------|-----------|
| 1 | 2026-09-15 | Bootstrap blueprint; 6-lane layout; subprocess backend on Windows | Operator requirement: native, no Docker, hidden windows |

## §9 Definition of Done

A step is done when: task status is `completed`, tests/evidence attached or referenced,
`archive` has distilled the outcome, and `plan` has rewritten §3 for the next step.
A mission is done when §8 records final merge and all lanes report idle.
