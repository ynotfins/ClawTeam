# AUTONOMY_POLICY — Decide, Don't Ask

Governs every swarm agent. Anchor F5/F6/F10 in `ANCHOR_POINTS.md` are the law; this file is the procedure.

## 1. Prime directive

Agents **do not ask the human questions.** They decide, log, and keep going. The human receives finished work, fork
comparisons, and (rarely) a batched Blocker Card.

## 2. Decision ladder (apply top-down, stop at first resolution)

1. **Anchor?** If `ANCHOR_POINTS.md` decides it — done.
2. **Spec?** If the user's prompt or `PRODUCT_SPEC.md` decides it — done.
3. **Repo convention?** Existing code/docs/tests decide — follow them.
4. **Top-Apps Benchmark** (§4) — pick the pattern the leaders converge on.
5. **Reversible & cheap?** Pick the simpler option, log it, move on.
6. **Materially different & benchmark inconclusive?** → **Fork** (§5).
7. **Absolute Blocker?** → park (§3). Never stop other work.

## 3. Absolute Blocker (the only reason to involve the human)

A blocker is **absolute** only if **all** hold:
- (a) Progress on this specific item is **impossible** without information/action only the human can supply
  (e.g., a missing paid credential, a legal/consent decision about a real person's likeness, a physical device action), **and**
- (b) no safe default exists, **and** no mock/stub/dormant mode lets the item proceed, **and**
- (c) the agent has tried: repo search, memory (AgentCore facade), docs (`docs_search`/`fetch_url`), web research, and a benchmark.

Not blockers: ambiguity, taste, naming, stack choice, missing requirements, flaky tests, failing installs (try alternatives),
missing optional keys (go dormant), "I'm not sure" (decide + log).

**Handling**: write a Blocker Card to `.clawteam-local/runs/<run>/blockers/<id>.md`:
```
# BLOCKER <id> — <one line>
Needed from owner: <exact artifact/decision>
Why impossible otherwise: <evidence of (a)(b)(c)>
Work continuing meanwhile: <list>
Default if no reply by SHIP: <what will ship instead, e.g. feature disabled/dormant>
```
Cards are **batched** (one notification per ≥ 15 min), shown in the Board, and **never pause the swarm**. The item ships in its
stated default state.

## 4. Top-Apps Benchmark Rule

Whenever a product/UX/architecture decision arises, the owner of the decision (`architect`, `ask`, or the deciding dev) must:
1. Identify the **category** (e.g., "kid-friendly game maker", "SaaS dashboard", "video editor").
2. Study **3–5 leading apps** (use `ask` lane: web research + docs). Prefer apps with clear public docs/UX.
3. Record a table in the decision record:

| Dimension | App 1 | App 2 | App 3 | Consensus |
|---|---|---|---|---|
| e.g., onboarding | … | … | … | "single prompt + template gallery" |

4. Choose the consensus pattern unless it conflicts with an anchor or the stated audience; if the leaders **split into two camps**
   with materially different outcomes → Fork (§5) with confidence < 0.7.
5. Write `confidence` (0–1) and a one-paragraph rationale. Unverifiable claims are marked `unverified`.

Time-box: ≤ 15 minutes of research per decision; ≤ 5 for trivial ones (skip the table if the choice is reversible and cheap — still log one line).

## 5. Fork-both-ways rule

Fork **only if** all: options produce **visibly different products** (not just internal refactors) · benchmark confidence < 0.7 · rework
cost of choosing wrong is high · the run has fork budget. Otherwise decide.

| Cap | Default |
|---|---|
| Open forks per run | 3 |
| Options per fork | 2 |
| Fork budget share | ≤ 40 % of run budget |
| Nested forks | not allowed (decide inside a fork) |
| Simple mode | Judge auto-picks winner; owner may still review |

Both branches are built to ship-ready on their own worktrees and kept until the owner chooses. Procedure in `SWARM_TEAM_SPEC.md` §7.

## 6. Decision record format (`decisions.jsonl` → rendered into `docs/DECISION_LOG.md`)

```json
{"id":"D-0007","run":"r-20261001-ab12","question":"State management for dashboard","options":[{"name":"Zustand"},{"name":"Redux Toolkit"}],
 "benchmark":[{"app":"Linear","choice":"custom store"},{"app":"Notion","choice":"custom"}],
 "chosen":"Zustand","confidence":0.74,"forked":false,"rationale":"…","ts":"2026-10-01T18:22:00Z"}
```

## 7. Governors (budgets)

| Resource | Default (Pro) | Default (Simple) |
|---|---|---|
| Wall-clock | 6 h | 45 min |
| LLM tokens / spend | owner-set; ledger enforced | tight fixed cap |
| KIE credits | owner-set | small fixed cap (see KIS spec) |
| Concurrent agents | 8 | 5 |
| Open experiments | 4 | 1 |
| Retries per task | 3 then reroute to `debug`/`ask` | 2 |

At 80 % of any budget: stop starting new forks/experiments. At 100 %: **graceful wrap-up** — finish integration of green work, write
`SHIP_REPORT.md` with what remains. Never abort mid-write; never exceed a hard cap; never ask for more budget (Blocker Card only
if the owner must supply a credential).

## 8. Self-recovery

- Failing tests: reproduce → fix → retest (≤ 3 loops) → route to `debug` → route to `ask` for a new approach → try the alternative
  option from the decision record.
- Tool/install failure: try an alternative tool or version, then a native fallback; log it.
- Stuck (no progress N minutes): leader reassigns, respawns the agent with context recovery (`clawteam/harness/context_recovery.py`).
- Merge conflicts: `integrator` resolves with both sides' tests as the oracle; unresolved → `debug`.

## 9. Honesty clauses

Agents must not claim completion without evidence, must not fabricate benchmark data (mark `unverified`), and must record every
deviation from an anchor as an `ANCHOR-CHALLENGE` rather than acting on it.
