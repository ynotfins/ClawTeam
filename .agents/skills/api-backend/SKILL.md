---
name: api-backend
description: Local API backends (FastAPI/Python, Node) on Windows with auth, validation, and loopback-only serving
---

# API Backend Development (local, Windows-native)

## Defaults
- Python: FastAPI + uvicorn + pydantic v2 (+ SQLAlchemy 2 if relational). Venv per project.
- Node: Hono or Express + zod + better-sqlite3 (see local-database skill).
- Both: OpenAPI auto-docs must work (`/docs` for FastAPI).

## Serve law
- Bind 127.0.0.1 ONLY unless the task explicitly needs LAN (then bind the specific interface + firewall rule and say so).
- Reserved ports (never use): 8080, 8788, 18789, 3300, 55433. Pick 5xxx/8xxx free ports; check with a TCP probe first.
- Long-running hosting = Windows Scheduled Task or hidden background process, not a console window left open.

## Auth (local implementations only)
- JWT (HS256) with refresh, or session cookies; Argon2/bcrypt for passwords.
- Secrets from User-scope env (`os.environ` / `process.env`) - never in files, never logged.

## Validation and errors
- Validate every input at the boundary (pydantic/zod). Uniform error envelope: error.code + error.message.
- Timeouts on all outbound calls; graceful shutdown handlers so tasks don't leak.

## Loop
```
# Python
.venv/Scripts/activate && pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port <port>
pytest -q                            # must pass
# Node
pnpm install && pnpm test && node src/index.js
```

## Done criteria
Endpoints return correct status codes (test with real requests - curl or Playwright MCP), auth blocks unauthenticated access, validation rejects bad input, server runs hidden + survives restart.
