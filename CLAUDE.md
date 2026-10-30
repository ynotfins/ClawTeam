# ClawTeam Workspace — Claude Code Agent Contract

Read `AGENTS.md` in this directory first — it is the full operating contract for every
agent (any CLI) in this swarm. `ANCHOR_POINTS.md` (immutable foundations) is the first thing
`AGENTS.md` tells you to read — read it before anything else.

Quick reference:

- `docs/SWARM_BLUEPRINT.md` = swarm canonical truth; §3 is your live system prompt (rewritten by `plan` every step; your worktree's `BLUEPRINT.md` is its spawn-time snapshot). Root `BLUEPRINT.md` = fork feature documentation (humans, not runtime).
- Worker loop + done criteria: `.rules/swarm-operations.md`
- Styling (tokens only): `.rules/design-system.md`
- Secrets (env vars only): `.rules/security-secrets.md`
- Memory (all-local, AgentCore facade): `.rules/memory-local.md`
- Team memory MCP server `agentcore-gateway` is registered via `.mcp.json`.

You run headless in a git worktree on Windows (subprocess backend). Never exit after one
task — poll tasks and inbox, report to `plan`, checkpoint your worktree.
