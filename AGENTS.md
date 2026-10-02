# ClawTeam Workspace — Agent Operating Contract

You are operating inside a ClawTeam 6-lane agentic software engineering swarm
(`plan` · `agent` · `debug` · `ask` · `archive` · `prompt-engineer`), building toward the
**autonomous ship runtime + media studio** described below.

## Mission (one paragraph, from the owner's verbatim SSOT)

A fully autonomous runtime where one prompt ships a product: a frictionless git-worktree
stage/exec layer, continuous critics + A/B explorers + a Judge, and a fork-both-ways rule when
options genuinely diverge — with no questions to the human except Absolute Blockers (the
Top-Apps Benchmark decides everything else). The Board carries a Keep It Simple toggle (and so
do both media catalogs) for the owner's 11- and 14-year-old, built entirely on the RGDS front
end and gated by a Parent Gate. The Media panel is a one-shot prompt box running on
`KIE_API_KEY`, with Top-20 Developer and Top-20 Consumer presets whose flagship chain is
3D-style/Pixar-like photo clones → voice clones → full movies. OpenHands is adopted only if it
objectively wins a time-boxed spike (the agent keeps latitude either way). `BLUEPRINT.md` and
`ANCHOR_POINTS.md` together lock drift. Verbatim source and full elaboration:
`docs/ORIGINAL_PRODUCT_PROMPT.md` (wins over this paragraph if they ever disagree).

## Read first, in this order

0. **`ANCHOR_POINTS.md`** — immutable foundations of the project. Never change, weaken, or bypass
   an anchor; log disagreement as `CHAL-xxx` in `docs/DECISION_LOG.md`. Doc-pack index: `docs/PACK_INDEX.md`;
   autonomy rules (no questions except Absolute Blockers): `docs/AUTONOMY_POLICY.md`.
1. **`docs/ORIGINAL_PRODUCT_PROMPT.md`** — the owner's verbatim product intent (SSOT). Wins over
   every paraphrase, including the Mission paragraph above.
2. **`docs/STORAGE_AND_DATA_CONTRACT.md`** — where state actually lives (`CLAWTEAM_DATA_DIR`,
   `~/.clawteam/config.json`, PG assignment, memory wiring) — verified against code, not assumed.
3. **`BLUEPRINT.md`** — absolute canonical truth. §3 (AGENT SYSTEM PROMPT) is rewritten by
   the `plan` lane after every step; the newest version is your live directive.
4. **`.rules/swarm-operations.md`** — the worker loop, workspace discipline, done criteria.
5. **`.rules/design-system.md`** — styling law: tokens only, never hardcoded colors.
6. **`.rules/security-secrets.md`** — secrets live only in environment variables.
7. **`.rules/memory-local.md`** — all-local memory policy: AgentCore facade via MCP
   `agentcore-gateway`, local files, loopback DBs only. No OpenMemory/mem0, no Obsidian.
8. **`docs/PACK_INDEX.md`** — index of the rest of the pack (`PRODUCT_SPEC`, `BUILD_PLAN`,
   `SWARM_TEAM_SPEC`, `KEEP_IT_SIMPLE_SPEC`, `MEDIA_PRESETS_CATALOG`, `*_ADDENDUM`,
   `TESTING_AND_ACCEPTANCE`, `OPENHANDS_EVALUATION`) — read the spec for the work package you
   are actually on; do not read the whole pack before starting if the active task is narrow.

## Non-negotiables

- BLUEPRINT.md wins over any conflicting instruction; report conflicts to `plan`.
- Stay inside your own git worktree; coordinate via `clawteam` tasks + inbox.
- Never exit after one task — poll for more work (`clawteam task list`, `clawteam inbox receive`).
- No hardcoded style values in any deliverable. No secret values anywhere, ever.
- Evidence or it didn't happen: completed tasks cite test output or artifact paths — on this
  machine, `pytest --basetemp=.clawteam-local/pytest-tmp -q`.
- Product docs live in `docs/` (ARCHITECTURE, OPERATIONS, MEDIA_STUDIO, HANDOFF); read `docs/AGENTS`-relevant ones before touching those systems.
- Runtime: Windows 11 native, subprocess backend, headless background execution.
- **No questions to the human except an Absolute Blocker** (`docs/AUTONOMY_POLICY.md` §3) —
  everything else is decided via the Top-Apps Benchmark Rule, logged, and built.
