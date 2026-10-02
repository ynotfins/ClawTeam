# DECISION_LOG — Append-Only

Every non-obvious decision by any agent goes here (also mirrored from `.clawteam-local/runs/<run>/decisions.jsonl`).
Format and rules: `AUTONOMY_POLICY.md` §6. Anchor challenges use the id prefix **`CHAL-`** (not `AC-`, which is reserved for acceptance criteria).

| # | Date | Decision | Rationale / Evidence | Anchor impact |
|---|---|---|---|---|
| D-001 | 2026-10-01 | Doc pack authored outside the repo in `C:\Users\ynotf\Downloads\ClawTeam` | Owner instruction: repo folder must not be written during doc authoring | none |
| D-002 | 2026-10-01 | Anchors tagged `[V]/[O]/[U]` | Separates verified repo facts from owner directives and unknowns | none |
| D-003 | 2026-10-01 | OpenHands treated as a time-boxed spike, not a presumed dependency | Facts unverified at authoring time (search unavailable); see `OPENHANDS_EVALUATION.md` | none |
| D-004 | 2026-10-01 | New service ports reserved 18800–18899 | Avoids the reserved list in ARCHITECTURE §5 | adds B6 |
| D-005 | 2026-10-01 | Parent Gate approvals are not "agent questions" | Cap/consent approvals go to the guardian via UI, not as agent-to-human questions; F5 stands | clarifies F5 |
| D-006 | 2026-10-01 | Preset "top 20" lists are editorial, to be re-validated with the Benchmark Rule | No usage data was available | none |
| D-007 | 2026-10-01 | `fullstack-commercial` is additive; `agentic-se` unchanged | Anchor F1 | none |
| D-008 | 2026-10-01 | Push only to `fork`; never `origin` | Anchor A2 | none |
| D-009 | 2026-10-02 | `CLAWTEAM_DATA_DIR` set to `F:\AgentCore\runtime\clawteam`; `~/.clawteam/config.json` confirmed to stay fixed (code fact, `clawteam/config.py::config_path()`); PG assignment is a dedicated `clawteam` DB (or schema) inside the existing shared `127.0.0.1:55433` instance, not a new port | Verified by reading `clawteam/team/models.py::get_data_dir()` and `clawteam/config.py::config_path()`; see `docs/STORAGE_AND_DATA_CONTRACT.md` | updates B5, adds B6a |

## Anchor challenges (`CHAL-xxx`)

_None yet._ Format: `CHAL-001 | date | anchor id | why it blocks the goal | what was done instead | owner response`.

## Open owner choices (forks awaiting decision)

_None yet._ Each fork lists: id · question · branch A · branch B · comparison path · Judge recommendation.

## Template for new rows

```
| D-0xx | YYYY-MM-DD | <decision> | <benchmark apps, evidence, confidence> | <anchors touched or none> |
```
