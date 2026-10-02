# ARCHITECTURE_ADDENDUM — Autonomous Ship Runtime + Media Pipelines

Extends the repo's `docs/ARCHITECTURE.md` (do not duplicate it). Anchors: `ANCHOR_POINTS.md`.

## 1. System map (new parts marked ★)

```
┌────────────────────────────── Board 127.0.0.1:8788 (stdlib HTTP) ───────────────────────────┐
│ Header: [Active Swarm ▾] [Keep It Simple ◐]                                                  │
│ Views: Board | Tools | Models | Media | ★Ship                                                │
│ Media: ★One-Shot box · ★Dev catalog (20) · ★Consumer catalog (20) · Library · Jobs · Chars · ★Movies │
└───────┬──────────────────────────────┬───────────────────────────────┬──────────────────────┘
        │ /api/ship/* ★                │ /api/media/*                  │ /api/kis/* ★
┌───────▼────────────────┐   ┌─────────▼───────────────────┐   ┌───────▼────────────┐
│ Ship Orchestrator ★    │   │ Media Pipelines ★           │   │ KIS Service ★      │
│ run state, governors,  │   │ preset registry, intent     │   │ mode, Parent Gate, │
│ decision engine, forks │   │ router, pipeline runner     │   │ content policy     │
└───────┬────────────────┘   └─────────┬───────────────────┘   └────────────────────┘
        │                              │ one job per stage
┌───────▼────────────────┐   ┌─────────▼───────────────────┐
│ Stage Layer ★          │   │ existing media core         │
│ branches + worktrees   │   │ jobs · assets · characters  │
│ over clawteam/workspace│   │ router · providers          │
└───────┬────────────────┘   └─────────┬───────────────────┘
        │                              │
┌───────▼────────────────┐   ┌─────────▼───────────────────┐
│ Executor Engine ★      │   │ Providers                   │
│ native (claude CLI via │   │ KIE adapters (+new) · ComfyUI│
│ subprocess) | OpenHands│   │ FFmpeg (local stitch)       │
│ (optional adapter)     │   └─────────────────────────────┘
└────────────────────────┘
```

## 2. New modules (additive; names are guidance, the agent may rename and must log it)

| Module | Responsibility |
|---|---|
| `clawteam/stage/` | Branch/worktree lifecycle: `create(kind)`, `promote`, `discard`, `gc`, registry JSON per run. Wraps `clawteam/workspace/manager.py`. |
| `clawteam/ship/` | `RunState`, `Governor`, `DecisionEngine`, `ForkController`, `BlockerCards`, report writers, `ship()` entry. |
| `clawteam/ship/roles.py` | Critic, Explorer, Judge, Integrator, etc. as harness `RoleConfig`s. |
| `clawteam/engines/` | `ExecutorEngine` protocol; `NativeEngine`; optional `OpenHandsEngine`. |
| `clawteam/kis/` | Mode store, Parent Gate (hashed PIN), content policy, friendly-message translator. |
| `clawteam/media/presets/` | Declarative preset registry, validator, loader. |
| `clawteam/media/pipelines.py` | Multi-stage runner with resumable records. |
| `clawteam/media/intent.py` | Free-text → preset / custom pipeline. |
| `clawteam/media/providers/kie_*.py` | Additional per-family KIE adapters. |
| `clawteam/board/ship_api.py` | HTTP handlers mounted by `server.py` (keeps the server file small). |

## 3. Run state & storage

```
.clawteam-local/runs/<run-id>/
  run.json              # prompt, mode, status, budgets, ledger, branches
  decisions.jsonl       # one DecisionRecord per line (also rendered to docs/DECISION_LOG.md)
  findings/             # critic findings (fingerprint-named JSON)
  experiments/          # A/B experiment records + judge verdicts
  forks/<id>/           # option A/B records, comparison.md
  blockers/             # Blocker Cards (markdown)
  logs/                 # structured JSON logs
  SHIP_REPORT.md
~/.clawteam/kis.json    # {enabled, parent_pin_hash, caps}  (no plaintext PIN)
~/.clawteam/media/pipelines/<id>.json
```
All writes use the atomic temp+replace helper (`clawteam/fileutil.py`) and file locks where concurrent.

## 4. Key interfaces

```python
class ExecutorEngine(Protocol):
    name: str
    def available(self) -> dict: ...                       # {ok, detail}
    def start(self, task: "WorkItem", worktree: Path, budget: "Budget") -> "SessionId": ...
    def inject(self, session: "SessionId", message: str) -> None: ...
    def poll(self, session: "SessionId") -> "EngineStatus": ...   # running|done|failed|stuck + usage
    def stop(self, session: "SessionId") -> None: ...

class Governor:
    def charge(self, kind: Literal["tokens","credits","seconds"], amount: float) -> None
    def allow(self, action: str) -> bool            # False => graceful wrap-up
    def snapshot(self) -> dict

class DecisionRecord(TypedDict):
    id: str; run: str; question: str; options: list[dict]; benchmark: list[dict]
    chosen: str | None; confidence: float; forked: bool; rationale: str; ts: str
```

## 5. Stage layer semantics

- **Lane worktree**: persistent per role for the whole run.
- **Fork worktrees**: created in pairs (A/B) from the same base commit; each builds the *entire* affected scope to ship-ready,
  including tests and docs; both are kept until the owner decides (or Judge auto-picks in Simple mode).
- **A/B experiment worktrees**: short-lived; branch from integration HEAD; merge back only through the Judge.
- **Integration branch**: the only branch that ships. Fast-forward-only promotions after gate pass.
- GC removes worktrees whose branches are merged/discarded and worktrees idle > N hours; never deletes unmerged fork branches.

## 6. Critic / explorer scheduling

Event sources: commit hooks (`scripts/hooks/`), timer, and run-phase changes. A scheduler enqueues critic scans as tasks
owned by critic roles (so everything remains visible in the existing task board). Findings dedupe on a content fingerprint.

## 7. Media pipeline model

```
Preset (declarative)  ──►  Pipeline instance (record)  ──►  Stage jobs (existing job store)
 inputs, stages[], caps       state per stage, refs to job ids      lifecycle E1 (unchanged)
```
- A stage declares: `kind`, `provider_pref` (local|kie), `model_family`, `params_template`, `needs` (prior stage outputs), `est_credits`.
- Runner guarantees: single submit per stage; resume re-polls; failed stage retry strips only that stage; total estimate
  + hard cap evaluated before stage 1; cap breach pauses the pipeline (never silently continues).
- Local FFmpeg handles stitch/mux/trim/loudness; no provider needed.

## 8. Board API additions (all loopback, JSON)

| Route | Purpose |
|---|---|
| `POST /api/ship/runs` | Start a run `{prompt, mode, budget?}` |
| `GET /api/ship/runs`, `GET /api/ship/runs/<id>` | List / detail |
| `GET /api/ship/runs/<id>/events` | SSE feed |
| `GET /api/ship/runs/<id>/forks` / `POST …/forks/<fid>/choose` | Fork comparison and owner choice |
| `GET/POST /api/kis/mode`, `POST /api/kis/parent-gate/verify` | Mode + Parent Gate |
| `GET /api/media/presets?catalog=dev\|consumer&simple=0\|1` | Preset catalog |
| `POST /api/media/oneshot` | Free-text prompt → plan + estimate |
| `POST /api/media/pipelines` / `GET …/<id>` | Run / inspect pipeline |

Handlers validate input, never echo secrets, and reuse the traversal-guard patterns already in `server.py`.

## 9. Backwards compatibility

Existing CLI, templates, routes, job states, and 640 tests must keep working. New behavior is additive and feature-flagged
by the presence of new templates/routes, not by changing old defaults.
