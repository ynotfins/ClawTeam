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
| D-010 | 2026-10-02 | OpenHands spike → **ADOPT-ENGINE** (optional). NativeEngine remains default. Canvas Docker at `127.0.0.1:8003` is optional operator UI only. Primary LLM `z-ai/glm-5.3` / LiteLLM `openrouter/z-ai/glm-5.3`; secondary `deepseek/deepseek-v4.1-flash`. Media stays `KIE_API_KEY` (not OpenHands). | Evidence: `docs/OPENHANDS_AUDIT_2026-10-02.md`; SDK 1.50.1 local WindowsTerminal smoke 3/3 corrected; `/ready` 200; MIT OSS path; B1 preserved (no Docker hard-dep) | none (B1 upheld) |
| D-011 | 2026-10-21 | Kickoff task `57d084fa` ("Scaffold the project skeleton per BLUEPRINT.md section 1") executed as **scaffold verification with evidence**, not new scaffolding: BLUEPRINT §1 was still MISSION PENDING at execution time (only `plan` may write it — blueprint discipline), and the project skeleton pre-exists and matches `docs/BUILD_PLAN.md` §1 + `ANCHOR_POINTS.md` (verified: package tree, core imports, 7 templates load, pytest smoke 60 passed `tests/test_templates.py + test_config.py + test_fileutil.py + test_timefmt.py`). No new code — WP2 `clawteam/stage/` etc. stay MISSING until `plan` steers via §3 v2; scope-drift rule held. | Autonomy ladder §2 (repo convention + decide/log); ambiguity is not a blocker. Full-suite baseline 650/2 re-verification belongs to `debug` task `48278107`; agent lane ran smoke only (Process Lasso kills sustained full-suite runs, `docs/HYGIENE_REPORT.md` §0) | none |
| D-012 | 2026-10-21 | Swarm LLM profile switched to new **`openrouter-llm`** profile reading env-name `LLM_API_KEY` (was `openrouter-claude` reading `OPENROUTER_API_KEY`); `default_profile` updated. Same model family as before (`z-ai/glm-5.3` + `glm-5.3-flash` small-fast). Operator was asked (spend decision) with no answer; A6/A7 restart order + Top-Apps fallback applied. Reversible: original profiles untouched. | `OPENROUTER_API_KEY` is **dead** — OpenRouter `auth/key` returns 401 "User not found"; all 6 dev-team workers died of it 2026-10-21 ~19:13 (claude transcripts `API Error: 401 User not found`). Alternatives live-probed: `OPENROUTER_CODEX_API_KEY` valid but its workspace guardrails 404 `z-ai/glm-5.3` (all 48 endpoints blocked); `LLM_API_KEY`/`OPENHANDS_LLM_API_KEY` run `glm-5.3`+`glm-5.3-flash` HTTP 200. `LLM_API_KEY` picked (generic name). End-to-end proof: `claude -p` probe via the profile env → "ok"; after restart: task `57d084fa` completed, plan inbox 2, SSE live. Key NAMES only ever referenced, never values (D1). | none (D1 upheld) |

## Anchor challenges (`CHAL-xxx`)

_None yet._ Format: `CHAL-001 | date | anchor id | why it blocks the goal | what was done instead | owner response`.

## Open owner choices (forks awaiting decision)

_None yet._ Each fork lists: id · question · branch A · branch B · comparison path · Judge recommendation.

## Template for new rows

```
| D-0xx | YYYY-MM-DD | <decision> | <benchmark apps, evidence, confidence> | <anchors touched or none> |
```
