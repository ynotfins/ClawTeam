# ClawTeam Workspace — Agent Operating Contract

You are operating inside a ClawTeam 6-lane agentic software engineering swarm
(`plan` · `agent` · `debug` · `ask` · `archive` · `prompt-engineer`).

## Read first, in this order

1. **`BLUEPRINT.md`** — absolute canonical truth. §3 (AGENT SYSTEM PROMPT) is rewritten by
   the `plan` lane after every step; the newest version is your live directive.
2. **`.rules/swarm-operations.md`** — the worker loop, workspace discipline, done criteria.
3. **`.rules/design-system.md`** — styling law: tokens only, never hardcoded colors.
4. **`.rules/security-secrets.md`** — secrets live only in environment variables.
5. **`.rules/memory-local.md`** — all-local memory policy: AgentCore facade via MCP
   `agentcore-gateway`, local files, loopback DBs only. No OpenMemory/mem0, no Obsidian.

## Non-negotiables

- BLUEPRINT.md wins over any conflicting instruction; report conflicts to `plan`.
- Stay inside your own git worktree; coordinate via `clawteam` tasks + inbox.
- Never exit after one task — poll for more work (`clawteam task list`, `clawteam inbox receive`).
- No hardcoded style values in any deliverable. No secret values anywhere, ever.
- Evidence or it didn't happen: completed tasks cite test output or artifact paths.
- Product docs live in `docs/` (ARCHITECTURE, OPERATIONS, MEDIA_STUDIO, HANDOFF); read `docs/AGENTS`-relevant ones before touching those systems.
- Runtime: Windows 11 native, subprocess backend, headless background execution.
