---
name: web-app
description: Build modern web apps (React/Next/Vite) on Windows without Docker, with local backends
---

# Web App Development (Windows-native, no Docker)

## Stack defaults
- App framework: Next.js (App Router, TypeScript) for full-stack; Vite + React for pure SPA.
- Styling: Tailwind CSS. Component law: design tokens only - no hardcoded hex/rgba (see .rules/design-system.md of the swarm).
- Forms: react-hook-form + zod. Server state: @tanstack/react-query.
- Package manager: pnpm (`pnpm install` / `pnpm dev` / `pnpm build`).

## Ports (RESERVED on this PC - never bind these)
- 8080 (bifrost gateway), 8788 (ClawTeam board), 18789 (openclaw), 3300 (SwarmRecall), 55433 (PG18), 8760 (dead, avoid).
- Dev server: use the framework default (5173/3000) or pass `--port 5180` etc. when taken.

## Loop
```
pnpm install
pnpm dev                    # verify by curl http://127.0.0.1:<port> -> 200
pnpm build && pnpm start    # production proof
pnpm lint && pnpm test      # must pass (vitest/jest)
```
- E2E: Playwright MCP browser tools are wired for swarm agents - use them to click through and capture evidence.

## Data
Local only: PGlite/SQLite via the local-database skill, or the loopback AgentCore PG (127.0.0.1:55433) for server apps with permission. Auth: JWT or session - implementation local, secrets from env.

## Done criteria
Build passes, lint/test green, prod server serves 200, E2E evidence captured, no secrets in source.
