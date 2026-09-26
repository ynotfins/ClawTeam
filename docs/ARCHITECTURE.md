# ClawTeam Control-Plane — Architecture

This deployment is a **Windows-native developer control-plane**: a multi-agent
autonomous engineering runtime plus a first-class Multimedia Studio, behind one
local web application. This document is the system map for engineers and agents
joining the project.

> Product/operator guide: [`BOOTSTRAP.md`](../BOOTSTRAP.md) · Media how-to:
> [`MEDIA_STUDIO.md`](MEDIA_STUDIO.md) · Services & recovery:
> [`OPERATIONS.md`](OPERATIONS.md) · Handoff: [`HANDOFF.md`](HANDOFF.md)

## 1. System map

```
┌──────────────────────────────────────────────────────────────┐
│  ClawTeam Board (127.0.0.1:8788)  — the control-plane app    │
│  ┌────────────┬────────────┬────────────┬────────────────┐  │
│  │ Board      │ Tools      │ Models     │ Media          │  │
│  │ live swarm │ MCP+skills │ OpenRouter │ Multimedia     │  │
│  │ kanban/SSE │ manager    │ autorouter │ Studio         │  │
│  └────────────┴────────────┴────────────┴────────────────┘  │
│         clawteam/board/server.py  (stdlib-only HTTP)        │
└──────────────┬───────────────────────────────┬─────────────┘
               │                               │
   ┌───────────▼───────────┐        ┌──────────▼──────────────┐
   │ Swarm runtime          │        │ Media router             │
   │ clawteam/team, spawn   │        │ clawteam/media           │
   │ 6 lanes, git worktrees │        │ jobs/assets/characters   │
   │ subprocess backend     │        │ provider boundary        │
   └───────────┬───────────┘        └──────────┬───────────────┘
               │                               │
               ▼                    ┌───────────▼───────────────┐
   agent CLIs (claude etc.)         │ Execution providers        │
   via OpenRouter GLM-5.3           │ local: ComfyUI (GPU :8188) │
   + agentcore-gateway MCP          │ cloud: KIE.ai adapters     │
   via bifrost (:8080)              └────────────────────────────┘
```

## 2. Layers

| Layer | Component | What it owns |
|---|---|---|
| UI | `clawteam/board/static/` — single-page app, **RGDS 1.1.0** vendored design system (`static/rgds/`, sha-locked `PROVENANCE.md`) | Views: Board (swarm kanban, SSE live), Tools (MCP/skills manager), Models (provider topology), Media (studio). All tokens via `--md-*` RGDS vars; 4 themes (`data-theme`). |
| API | `clawteam/board/server.py` — stdlib `ThreadingHTTPServer` | `/api/overview`, `/api/events/<team>` (SSE), `/api/tools/*`, `/api/openrouter/*`, `/api/media/*`, `/rgds/*` (traversal-guarded static). |
| Swarm runtime | `clawteam/team/`, `clawteam/spawn/` | 6-lane teams (`plan · agent · debug · ask · archive · prompt-engineer`), one git worktree per worker, subprocess backend, inbox/task stores (JSON, atomic writes, file locks), `sync_blueprint.py` hook seeds worktrees. |
| Media pipeline | `clawteam/media/` | `jobs.py` (file-backed job store, app-owned lifecycle), `assets.py` (binary store + registry), `characters.py` (reusable identity records), `router.py` (routing policy + worker thread), `providers/` (boundary). |
| Providers | `providers/comfyui_local.py`, `providers/kie.py` | `MediaProvider` protocol: `capabilities/health/estimate/submit/poll/download`. KIE = `KieClient` + per-model adapters (`FluxKontextAdapter`, `RunwayAdapter`) — **schemas differ per model family; never one universal payload**. |
| Memory/tools plane | agentcore-gateway MCP via bifrost (127.0.0.1:8080) | Governed shared memory/tools; device-assertion policy for project-scoped writes (control-plane owned). |

## 3. Key laws (enforced by tests where possible)

- **Design law** (`.rules/design-system.md`): RGDS tokens only; no color/spacing
  literals anywhere; rainbow = `secondary-dark`, stroke-only.
- **Secrets law** (`.rules/security-secrets.md`): provider keys live in
  User-scope env vars only; never in files, frontend, or client assets. The UI
  references keys by *name* (`${ENV}`), the server expands them.
- **Provider isolation**: UI renders normalized job/asset shapes only; provider
  payloads never cross `providers/`.
- **Job lifecycle** (app-owned states, independent of provider vocabulary):
  `draft → queued → running → provider_succeeded → downloading → succeeded`
  (+ `failed`, `timed_out`, `succeeded_provider_download_failed`).
- **No double-charge**: submit exactly once; polling uses exponential backoff
  (fast window → ×1.5 → 30 s cap) with per-kind timeouts; recovery re-polls the
  existing provider task; retry is user-initiated and strips only failed stages.
- **Download-before-complete**: provider outputs are copied into the local asset
  store before a job is `succeeded` (cloud URLs expire — 14-day storage,
  20-minute temp links).
- **Lane separation (characters)**: stylized 3D-*looking* imagery is Lane A
  (what ships today); true 3D assets are Lane B (future provider slot behind
  the same boundary). The UI never calls Lane A imagery "3D models".

## 4. Data layout

| Path | Contents |
|---|---|
| `~/.clawteam/` | config.json (profiles), theme.json, teams/, tasks/, inboxes/ |
| `~/.clawteam/media/jobs/` | one JSON per job (atomic, survives restarts) |
| `~/.clawteam/media/assets/` | binaries + sidecar JSON registry |
| `~/.clawteam/media/characters/` | `chr-*.json` (canonical + variants + scenes) |
| `<repo>/.clawteam-local/` | runtime logs, worker claude-config, archive/ (gitignored) |
| `D:\ComfyUI\...` | local GPU tier (auto-boots hidden on demand, port 8188) |

## 5. Ports (reserved on this machine)

| Port | Service |
|---|---|
| 8080 | bifrost LLM/MCP gateway (auto) |
| 8188 | ComfyUI local media tier (on-demand) |
| 8787 | openclaw ingest path (via tailscale serve) |
| 8788 | **ClawTeam board** (manual start) |
| 18789 | OpenClaw gateway (scheduled task, auto) |
| 18790 | **photo host** (thread inside the board process — the only process the public photo hostname may reach) |
| 3300 | SwarmRecall (scheduled tasks currently disabled) |
| 55433 / 65432 | AgentCore PG18 / SwarmRecall PG16 (loopback) |

Public surface law: exactly one product hostname is publicly reachable —
`photos.miaknuckles.com` (cloudflared tunnel `clawteam-photos` → loopback
18790), serving only unexpired, token-named image files. Everything else,
including the board API, is loopback-only.

## 6. Test & verification

- `pytest` — 640 passed / 2 skipped (upstream platform skips) at time of writing
  (photo lane + animate-from-variant included). On this machine use
  `--basetemp=.clawteam-local/pytest-tmp` (stale junction breaker). Media
  suite (`tests/test_media.py`, `tests/test_photohost.py`) covers lifecycle,
  gates, adapters (mocked HTTP), backoff, character pipeline, photo upload /
  expiry / traversal guards, and recovery paths.
- Live verification record per capability: see `HANDOFF.md` §2.
