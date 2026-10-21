# OPENHANDS_AUDIT — 2026-10-02

Evaluator: Cursor agent (ClawTeam OpenHands spike)  
Anchors consulted: B1, B7, D1, A5–A7, E* (media = KIE), F5, G2  
Protocol: `docs/OPENHANDS_EVALUATION.md`  
Scope: inventory + host configure + code-only smoke. **No WP1–WP6 implementation. No push.**

---

## 0. One-line outcome

**ADOPT-ENGINE** — optional `ExecutorEngine` only. **`NativeEngine` remains the default.** Agent Canvas Docker host stays an **optional operator tool**, never a hard dependency (B1 preserved).

**Media remains kie.ai (`KIE_API_KEY`) + ClawTeam ComfyUI local lane. Do not route image/video through OpenHands, MiniMax, or OpenRouter image models.**

---

## 1. Versions / URLs / license

| Piece | Version / evidence | URL | License |
|---|---|---|---|
| Agent Canvas (Docker host) | image `ghcr.io/openhands/agent-canvas:1.13.0`; build tags in image env `AGENT_CANVAS_BUILD_GIT_REF=refs/tags/v1.13.0`, `OPENHANDS_BUILD_GIT_REF=refs/tags/v1.42.1` | https://docs.openhands.dev/overview · canvas `http://127.0.0.1:8003/canvas/` · ready `http://127.0.0.1:8003/ready` | MIT (OpenHands/OpenHands README: core OSS MIT; `enterprise/` is Polyform — **do not depend on enterprise**) |
| Software Agent SDK | `openhands-sdk==1.50.1` + `openhands-tools==1.50.1` (installed in smoke venv) | https://docs.openhands.dev/sdk/getting-started · https://github.com/OpenHands/software-agent-sdk | MIT (repo; PyPI metadata license field empty, source LICENSE MIT) |
| CLI / headless | Documented `openhands --headless -t "..."` | https://docs.openhands.dev/openhands/usage/cli/headless | Same ecosystem MIT (CLI powered by SDK) |
| Legacy Local Runtime | V0 `RUNTIME=local` / Windows PowerShell | https://docs.openhands.dev/openhands/usage/v0/runtimes/V0_local | Legacy path; prefer SDK |
| Compose template | `D:\github\agentcore-control-plane\scripts\maf_recall\openhands\` | host mirror `I:\LocalApps\OpenHands\` | n/a |

Docs map (official overview): Agent Canvas · Software Agent SDK + Agent Server · CLI · Sandbox Server · Cloud/Enterprise.

---

## 2. Exact OpenRouter model ids (verified, not guessed)

Sources (fetched 2026-10-02):

- https://openrouter.ai/z-ai/glm-5.3 → **`z-ai/glm-5.3`**
- https://openrouter.ai/deepseek/deepseek-v4.1-flash → **`deepseek/deepseek-v4.1-flash`**

| Role | OpenRouter id | OpenHands / LiteLLM form used on this host |
|---|---|---|
| **Primary** (coding/agent) | `z-ai/glm-5.3` | `openrouter/z-ai/glm-5.3` |
| **Secondary** (cheaper critic/explore) | `deepseek/deepseek-v4.1-flash` | `openrouter/deepseek/deepseek-v4.1-flash` |

Provider routing:

- `LLM_BASE_URL=https://openrouter.ai/api/v1`
- `LLM_API_KEY` ← Windows User env **`OPENROUTER_API_KEY`** (name only; value never written to repo)
- Canvas compose supports **one** `LLM_MODEL` → set to GLM-5.3 primary
- Secondary switch: Canvas profile `I:\LocalApps\OpenHands\state\profiles\deepseek-v4.1-flash.json`, or SDK `LLM(model="openrouter/deepseek/deepseek-v4.1-flash", ...)`

**No MiniMax. No OpenRouter image/video models in OpenHands.**

---

## 3. Media boundary (explicit)

| Concern | Owner |
|---|---|
| Image / video / voice clone / movie chain | ClawTeam Media panel → **`KIE_API_KEY`** + adapters + local ComfyUI (`ANCHOR` A5–A6, E*) |
| Code / agent execution | Optional OpenHands engine / Canvas |
| OpenHands config | Must not add media model routes |

`docs/MEDIA_PRESETS_CATALOG.md` architecture **unchanged** by this audit.

---

## 4. STEP A — Inventory (evidence)

### A1. Container

| Check | Result |
|---|---|
| Before audit | `openhands-local-8003` **Exited (0) ~4 weeks**; image `ghcr.io/openhands/agent-canvas:1.13.0`; port bind `127.0.0.1:8003->8000` |
| After Stage B recreate | **Up**; same image; ports `127.0.0.1:8003->8000/tcp` |
| Mounts | `I:/LocalApps/OpenHands/state` → `/home/openhands/.openhands`; `D:/OpenHandsProjects` → `/projects` |
| Forbidden mounts | **No** `F:` AgentCore, **no** `H:` Swarm |

### A2. Ready

- Before: connection refused (stopped)
- After: `GET http://127.0.0.1:8003/ready` → **HTTP 200** body `{"status":"ready"}`

### A3. LLM env — compose vs live

| Source | Before | After Stage B |
|---|---|---|
| Compose files (`agentcore` template + `I:\LocalApps\OpenHands`) | `LLM_MODEL=openrouter/deepseek/deepseek-v4-pro` | `LLM_MODEL=openrouter/z-ai/glm-5.3` |
| Live container (stale, before recreate) | `LLM_MODEL=openrouter/openrouter/pareto-code` (diverged from compose) | — |
| Live container (after recreate) | — | `LLM_MODEL=openrouter/z-ai/glm-5.3`, `LLM_BASE_URL=https://openrouter.ai/api/v1`, `ANALYTICS_OPT_OUT=true`, `LLM_API_KEY`/`OPENROUTER_API_KEY` **present (values not logged)** |

### A4. Which piece ClawTeam can wrap as `ExecutorEngine` on Windows 11 **without Docker mandatory**

| Component | Docker mandatory? | Programmatic? | ClawTeam fit |
|---|---|---|---|
| **Software Agent SDK** (`Conversation` + local workspace + `WindowsTerminal`) | **No** | Yes (Python) | **Yes — primary integration target** |
| CLI headless | No (local install) | Yes | Alternate driver |
| Agent Server (`python -m openhands.agent_server --host 127.0.0.1`) | No for local process | REST/WS | Optional; if used, port in **18800–18899** |
| Agent Canvas Docker (`:8003`) | **Yes** (this host) | Browser-first | **Optional operator tool only** — not default engine |
| Docker sandbox | Yes | Yes | Optional adapter only (B1) |

Smoke used SDK locally; logs showed `Auto-detected: Using WindowsTerminal (PowerShell backend)` — local process runtime exists (B1).

### A5. License of component we ship against

MIT for Agent Canvas / SDK OSS paths. Avoid `enterprise/` Polyform code. Redistribution of an **integration wrapper** (our `openhands.py`) is fine; do not vendor enterprise.

### A6. Local/process runtime vs Docker-only

- **Exists**: SDK local workspace + Windows PowerShell terminal; legacy V0 `RUNTIME=local`.
- Therefore ClawTeam may **ADOPT-ENGINE** with Docker **optional**.
- If only Canvas Docker worked, criterion 1 would fail → helper/reject for engine; Canvas could still remain optional UI. **That is not the case here.**

---

## 5. STEP B — Host configure (done)

Changed:

1. `docker-compose.yml` in both `agentcore-control-plane\scripts\maf_recall\openhands\` and `I:\LocalApps\OpenHands\` → GLM-5.3 primary, OpenRouter base URL, `OPENROUTER_API_KEY` → `LLM_API_KEY`, `ANALYTICS_OPT_OUT=true`.
2. Recreated container (`docker rm -f` + `compose up -d`) after name conflict on `--force-recreate`.
3. Canvas state: `settings.json` primary model → `openrouter/z-ai/glm-5.3`; `active_profile` → `glm-5.3`; analytics consent → false.
4. Profiles: `profiles/glm-5.3.json`, `profiles/deepseek-v4.1-flash.json` (`api_key: null`; rely on env).
5. `START_OPENHANDS.md` updated (both trees) with model ids + media boundary.
6. **No** `.env` with secrets. **No** F:/H: mounts. Bind remains `127.0.0.1:8003`.

D1 note: pre-existing Canvas state still contains **encrypted** `api_key` blobs under `state/settings.json` / old profiles (Fernet ciphertext). Prefer env-only going forward; do not expand or log those values. New profiles intentionally set `api_key: null`.

---

## 6. STEP C — Smoke (code only)

Scratch repo: `D:\OpenHandsProjects\clawteam-oh-smoke` (not ClawTeam main).  
Driver: **programmatic SDK** (`openhands-sdk` 1.50.1), model `openrouter/z-ai/glm-5.3`, key from `OPENROUTER_API_KEY`.  
Evidence: `smoke_results.jsonl`, `smoke_summary.json`, `run_smoke.py`.

| Task | Agent edited? | Corrected verify (venv pytest) | Wall time | Crash? | Notes |
|---|---|---|---|---|---|
| (a) fix failing unit test | Yes (`math_utils` → `a+b`) | **PASS** | 37.3 s | No | First harness used Store `python` without pytest → false FAIL |
| (b) add small endpoint + tests | Yes (`app.py` + `test_app.py`) | **PASS** | 49.8 s | No | Agent set sample `HOST="0.0.0.0"` — **discipline miss** vs B7; unit test only checked `health_body()` |
| (c) refactor no behavior change | Yes (f-string) | **PASS** (attempt 2) | 18.4 s | Attempt 1: OpenRouter **403 PII** `redaction_context_lost` | Attempt 2 succeeded |

**Smoke score (corrected): 3/3 pass.** Programmatic API criterion: **PASS** (not Canvas-only).  
ExecutorEngine wrap feasibility: SDK `start`-like = create Conversation; `inject` ≈ `send_message`; `poll`/`stop` via conversation lifecycle — estimated ≤ ~300 lines.

Operational risks to budget for:

- OpenRouter PII redaction can abort runs mid-conversation.
- Agent may ignore loopback instructions in *generated* sample servers — governors/prompts must enforce `127.0.0.1`.
- PATH/`python` ambiguity on Windows — engine wrapper must pin worktree venv interpreter.

Native engine cost comparison: **not measured this spike** (no parallel native run). Pass-rate bar (≥2/3) met; revisit cost within 25% when NativeEngine exists.

---

## 7. Criteria vs `OPENHANDS_EVALUATION.md` §4

| # | Criterion | Result |
|---|---|---|
| 1 | Headless Windows **without** Docker mandatory (B1) | **PASS** (SDK local) |
| 2 | Loopback + env-var keys (B7, D1) | **PASS** for host bind + env injection; watch encrypted Canvas state leftovers + generated-app bind discipline |
| 3 | ≥2/3 smoke (or clearly better pass rate) | **PASS** (3/3 corrected) |
| 4 | Wrap `ExecutorEngine` ≤ ~300 lines | **PASS** (SDK surface adequate; not implemented this spike) |
| 5 | License compatible | **PASS** (MIT OSS path) |

→ **ADOPT-ENGINE** (optional). Not REJECT. Not merely HELPER — smoke + local SDK cleared engine bar. Canvas Docker remains helper/UI.

---

## 8. How ZCode / ClawTeam should wire it (design only — not built today)

1. Keep / add `ExecutorEngine` protocol (`docs/ARCHITECTURE_ADDENDUM.md`).
2. Implement `clawteam/engines/openhands.py`:
   - `available()` → `{ok:false, detail:"not installed"}` unless `.clawteam-local/engines/openhands/` venv has `openhands-sdk`+`openhands-tools`.
   - Drive **SDK** (not Canvas) with worktree-bound `workspace=Path`.
   - `LLM_MODEL` primary `openrouter/z-ai/glm-5.3`; allow override to `openrouter/deepseek/deepseek-v4.1-flash` for critic/explore roles.
   - Read **`OPENROUTER_API_KEY`** / `LLM_BASE_URL` from environment only.
3. Install optional deps into **`.clawteam-local/engines/openhands/`** (never Board stdlib env) — G2.
4. If a long-lived Agent Server is needed: bind **`127.0.0.1`**, pick free port in **18800–18899**, register in `OPERATIONS_ADDENDUM.md`. Do **not** require `:8003` Canvas for autonomy.
5. Template field `engine = "native" | "openhands"`; default **`native`**. CLI: `clawteam ship … --engine openhands`.
6. Autonomy settings: headless always-approve; worktree cwd; no human ask except Absolute Blocker (F5); map usage events from SDK token/cost counters into `Governor` when available.
7. **NativeEngine always default and always available.**

---

## 9. Recommended autonomy settings (operator)

| Setting | Value |
|---|---|
| Default engine | `native` |
| Optional engine | `openhands` via SDK venv |
| Primary LLM | `openrouter/z-ai/glm-5.3` |
| Secondary LLM | `openrouter/deepseek/deepseek-v4.1-flash` |
| Provider | OpenRouter only for OH LLM |
| Media | `KIE_API_KEY` only (unchanged) |
| Canvas | `http://127.0.0.1:8003/canvas/` optional; `ANALYTICS_OPT_OUT=true` |
| Human asks | Absolute Blocker only |
| Budget | Wrap on token/credit/wall-clock caps (F10) |

---

## 10. Revisit triggers

- OpenRouter PII blocks become frequent on Windows path-heavy contexts.
- SDK drops WindowsTerminal / requires Docker for default workspace.
- License or packaging moves critical pieces under Polyform/enterprise-only.
- Cost >125% of native at equal pass rate with no quality gain.

---

## 11. Decision record (also in DECISION_LOG)

```
D-010 OpenHands decision
Date: 2026-10-02
Evaluator: Cursor agent spike
OpenHands: agent-canvas 1.13.0; SDK 1.50.1
Sources: docs.openhands.dev/overview; openrouter.ai/z-ai/glm-5.3; openrouter.ai/deepseek/deepseek-v4.1-flash; OPENHANDS_EVALUATION.md
Criteria 1..5: PASS / PASS / PASS / PASS / PASS
Outcome: ADOPT-ENGINE (optional; NativeEngine default)
Media: KIE unchanged
B1: not weakened — Docker Canvas optional only
```
