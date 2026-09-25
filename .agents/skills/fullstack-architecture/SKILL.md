---
name: fullstack-architecture
description: Structure complex full-stack app projects - monorepo layout, offline-first, env law, ports, done gates
---

# Full-Stack Architecture (project structure law)

## Monorepo layout (pnpm workspaces when JS-heavy)
```
<project>/
  apps/
    web/          # Next.js or Vite (web-app skill)
    mobile/       # flutter | react-native | android (their skills)
    api/          # FastAPI or Node (api-backend skill)
  packages/
    shared/       # types, zod schemas, domain models shared web+mobile+api
  db/
    migrations/   # one migration system per store (local-database skill)
  docs/
    ARCHITECTURE.md   # decisions, ports, data flow
    IOS_BUILD_NOTES.md  # if iOS target exists
  .env.example    # NAMES only, never values
```

## Cross-cutting law
1. Ports: 8080/8788/18789/3300/55433 reserved; each app documents its ports in ARCHITECTURE.md and probes before bind.
2. Secrets: User-scope env only; .env.example lists NAMES; code reads env at runtime.
3. Offline-first mobile: local DB is source of truth; sync is an additive feature, never a hard dependency. Every screen renders with zero network.
4. Shared contracts: one schema package (zod/pydantic mirrored) - API and clients never re-declare types by hand.
5. Data gravity: keep storage local (local-database skill); the API owns its DB; mobile never talks to another app's DB directly.
6. No Docker - everything runs native Windows processes.
7. Theme/design: tokens only, no hardcoded colors (swarm design law).

## ARCHITECTURE.md must answer
- What runs where (process map: app, port, how it starts, how it is hosted long-term).
- Data flow diagram (text ok): client -> API -> DB, sync paths.
- Failure modes: what happens offline, when API is down, on bad migrations.

## Done gates for the whole project
- Every app: its own skill's done criteria met.
- Fresh-clone boot: pnpm install + documented start commands bring the whole stack up.
- E2E proof: one scripted user journey across web OR mobile -> API -> DB with evidence (screenshots/logs).
