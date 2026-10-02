# OPENHANDS_EVALUATION — Time-Boxed Spike and Adoption Criteria

Anchors: B1 (no hard Docker), B7 (loopback), D1 (secrets), A7 (agent latitude), G2 (dependency justification).

## 1. Intent

The owner said: *if incorporating OpenHands is the best option, do it.* The agent has full latitude. This document makes that
decision **objective and recorded** so it neither gets skipped nor adopted on hype.

> Facts about OpenHands (current CLI/SDK/server packaging, license terms, Windows support, runtime requirements) were **not
> verified** during this documentation pass (web search was unavailable). Treat everything in §3 as a hypothesis checklist.
> Verify from the official repository/docs at spike time (`ask` lane + `docs_search`/`fetch_url`).

## 2. Spike protocol (≤ 4 agent-hours; run in an `ab` worktree; parallel to other WPs)

1. **Discover**: find the current official install path (SDK/CLI/server), license, supported platforms, headless mode, and how a
   runtime/sandbox is chosen (Docker vs. local/process). Record versions and URLs in the decision record.
2. **Install in isolation**: in a throwaway venv/worktree. If it requires Docker/WSL for its default runtime, test whether a
   **local (non-Docker) runtime** is supported on Windows 11.
3. **Smoke task**: have it complete the same three tasks that the native engine completes, in a scratch repo:
   (a) fix a failing unit test, (b) add a small endpoint with tests, (c) refactor a function without behavior change.
4. **Measure** vs. the native engine (`claude` CLI via OpenRouter profile): pass rate, wall-clock, tokens/cost, diff quality, crash
   count, resumability, ability to be driven by `ExecutorEngine` (start/inject/poll/stop), log structure.
5. **Integration probe**: can it (i) run bound to `127.0.0.1` only, (ii) read the model key from env var names only, (iii) work inside a
   given git worktree path, (iv) accept an injected message mid-run, (v) report usage?
6. **Decide** using §4 and write the decision.

## 3. Hypothesis checklist (verify, do not assume)

| Question | Why it matters |
|---|---|
| License permits our use and redistribution of an integration? | Legal safety for a commercial product |
| Has a headless/programmatic interface (SDK or server API) suitable for `ExecutorEngine`? | Needed to drive it from the swarm |
| Runs natively on Windows 11 without Docker? | Anchor B1 |
| Supports OpenRouter or arbitrary OpenAI-compatible endpoints via env-var key? | Anchor D1 + existing model routing |
| Per-task isolation to a given directory (our worktree)? | Anchor B3 |
| Event/usage stream for governors? | Budget caps (F10) |
| Maintained and stable (recent releases)? | Long-term risk |

## 4. Adopt / reject criteria

**Adopt as an optional executor engine** only if **all** hold:
1. Works headless on Windows 11 **without** making Docker/WSL mandatory (B1).
2. Binds loopback-only and uses env-var keys (B7, D1).
3. Passes ≥ 2 of 3 smoke tasks and is within 25 % of native on cost, **or** is clearly better on pass rate.
4. Can be wrapped behind `ExecutorEngine` in ≤ ~300 lines without patching OpenHands.
5. License is compatible.

**Adopt as a critic/explorer helper only** (partial) if 1, 2, 4, 5 hold but 3 fails — use where its strengths show.

**Reject** otherwise. Record the specific failing criterion.

## 5. Integration design if adopted

- `clawteam/engines/openhands.py` implements `ExecutorEngine`; `available()` returns `{ok:false, detail:"not installed"}` when absent so the
  rest of the app is unaffected.
- Template roles gain an optional `engine = "native" | "openhands"` field; default `native`.
- Per-run override: `clawteam ship … --engine openhands`.
- Optional dependency: installed into a dedicated venv under `.clawteam-local/engines/openhands/`, not into the Board's environment
  (keeps the Board stdlib-only; G2).
- Service port (if a server is needed): next free in 18800–18899, `127.0.0.1` only, registered in `OPERATIONS_ADDENDUM.md`.
- Session logs mapped into the standard run log format for the Board.
- Tests: contract tests against a fake `ExecutorEngine`; an opt-in integration test skipped when OpenHands is not installed.

## 6. If rejected

Still keep the `ExecutorEngine` protocol — it is the clean seam for any future engine — and implement `NativeEngine` as the only
registered engine. Log: version evaluated, date, criteria results, and revisit trigger (e.g., "native Windows runtime GA").

## 7. Decision record template

```
D-xxxx OpenHands decision
Date / evaluator / OpenHands version / sources (URLs)
Criteria 1..5: pass/fail + evidence
Measurements table (native vs openhands)
Outcome: ADOPT-ENGINE | ADOPT-HELPER | REJECT
Follow-ups / revisit trigger
```
