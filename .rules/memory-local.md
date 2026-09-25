# Memory — All-Local Policy (Canonical)

**Operator directive (2026-09-16):** ALL memory, storage, and databases are LOCAL on
this PC. No OpenMemory/mem0, no Obsidian vault, no cloud memory services. The previous
OpenMemory wiring (`oi-openmemory-prod`, port 8760) is REMOVED.

## 1. What agents use now

| Layer | What | Where |
|---|---|---|
| Team memory | AgentCore memory facade (MCP `agentcore-gateway`) | `http://127.0.0.1:8080/mcp` via bifrost, Bearer `$BIFROST_MCP_VIRTUAL_KEY` (User-scope env) |
| Workspace state | Plain local files (tasks, inbox, BLUEPRINT, worktrees) | `~\.clawteam\` + `D:\github\ClawTeam\.clawteam-local\` |
| Canonical DB | AgentCore PostgreSQL (loopback only) | `127.0.0.1:55433` (governed — no raw SQL; facade tools only) |
| Neutral semantic plane | SwarmRecall (loopback only) | `127.0.0.1:3300` / PG16 `65432`, server-side adapter only |

## 2. MCP wiring

- Repo `.mcp.json` and the spawned-worker config
  (`.clawteam-local\claude-config\.claude.json`) both define exactly one MCP server:
  `agentcore-gateway` (HTTP → bifrost). Verify with `claude mcp list`.
- Project-scoped memory tools (session_open, append_event, docs_search, …) additionally
  require a signed **device assertion** from the AgentCore device-identity layer.
  Headless swarm agents do not hold device identities yet — that is a known blocker
  owned by the operator/control-plane (see `BOOTSTRAP.md` § Known limitations).
  Non-assertion tools (e.g. `memory_status`) work for wired agents today.

## 3. Rules

- Never persist secrets in files; secrets live in User-scope env vars only.
- Never write memory to network services. If a tool needs one, stop and report.
- Do not re-introduce OpenMemory/mem0/Obsidian wiring — superseded by this policy.
- Performance expectations: local-file state and loopback PG beat any HTTP memory
  service; see `BOOTSTRAP.md` § Memory for the measured numbers.
