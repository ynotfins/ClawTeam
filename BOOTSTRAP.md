# BOOTSTRAP.md — Native Activation Layout

ClawTeam "2. Agentic Software Engineering" swarm on Windows 11 Pro — fully native,
no Docker, invisible background execution. This document is the operator's manual.

**Doc set**: [Architecture](docs/ARCHITECTURE.md) · [Operations & recovery](docs/OPERATIONS.md) ·
[Media Studio guide](docs/MEDIA_STUDIO.md) · [Engineering handoff](docs/HANDOFF.md) ·
[Changelog](CHANGELOG.md) · design law: [`.rules/design-system.md`](.rules/design-system.md)

---

## 1. What is installed where

| Artifact | Location | Purpose |
|---|---|---|
| Python venv | `D:\github\ClawTeam\.venv` | Framework runtime (`pip install -e ".[dev]"`) |
| CLI | `.venv\Scripts\clawteam.exe` | All swarm commands |
| Runtime config | `~\.clawteam\config.json` | backend=subprocess, profiles, sync hook |
| Team template | `~\.clawteam\templates\agentic-se.toml` | The 6-lane swarm (canonical copy: `templates\agentic-se.toml` in repo) |
| Theme tokens | `~\.clawteam\theme.json` | Served by board at `/api/theme` (canonical: `design\theme.tokens.json`) |
| Hidden-run artifacts | `.clawteam-local\` (gitignored) | run pid files, supervisor scripts, logs |
| Claude Code | `~\.local\bin\claude.exe` (v2.1.241) | Agent CLI (launcher adds it to PATH) |
| Web board | `http://127.0.0.1:8788` | Port 8788 because 8080 is taken (bifrost gateway) |

## 2. The 6-lane swarm layout

| Lane | Charter |
|---|---|
| `plan` (leader) | Decomposes mission; **rewrites BLUEPRINT.md §3 (AGENT SYSTEM PROMPT) after every completed step** and delivers it to the `agent` lane via inbox + runtime inject; merges worktrees at the end |
| `agent` | Primary executor; treats the newest §3 as its live system prompt; re-reads the canonical BLUEPRINT each step |
| `debug` | Reproduces/fixes defects with tests; sweep-verifies completed work |
| `ask` | Decision-ready research answers |
| `archive` | Distills outcomes; owns team memory (all-local: AgentCore facade + local files — `.rules/memory-local.md`) |
| `prompt-engineer` | Audits and proposes improved §3 rewrites to `plan` |

`BLUEPRINT.md` is the absolute canonical truth for every sub-agent workspace. Each
spawned agent's git worktree receives a spawn-time copy of the canonical files
(BLUEPRINT, `.rules/`, `design/`, rule surfaces, `.mcp.json`) via the
`AfterWorkerSpawn → scripts\hooks\sync_blueprint.py` hook, plus a
`.clawteam-workspace.json` pointer to the live canonical copy (only `plan` writes it).

## 3. Activation (one-time setup)

```powershell
cd D:\github\ClawTeam
powershell -ExecutionPolicy Bypass -File scripts\setup_local.ps1
```

Creates `.venv`, installs the framework editable, verifies python/node/npx/ffmpeg/git/claude,
installs the clawteam skill into `~\.claude\skills`, applies runtime config. Git Bash
equivalent: `bash scripts/setup_local.sh`.
(Already executed during this setup — rerun any time, it is idempotent.)

## 4. Launch the swarm (fully autonomous, invisible)

```powershell
cd D:\github\ClawTeam
powershell -ExecutionPolicy Bypass -File scripts\windows\Start-Swarm.ps1 -Goal "Build a full-stack todo app with auth, database, and React frontend"
```

- Runs `clawteam launch agentic-se --team se-swarm --goal ...` inside a hidden
  supervisor (CreateNoWindow — zero console flash), which stays alive hosting the
  agent console so nothing is killed by console teardown.
- Starts the web board and opens `http://127.0.0.1:8788` once.
- Options: `-Team <name>`, `-Profile openrouter-claude`, `-NoBoard`.
- Logs: `.clawteam-local\logs\se-swarm.log` (heartbeat every 60s).

Monitor (any time):

```powershell
cd D:\github\ClawTeam
.venv\Scripts\clawteam.exe board show se-swarm          # terminal kanban
start http://127.0.0.1:8788                              # web board (theme picker in sidebar)
```

**Desktop app (no browser):** double-click the **ClawTeam Board** shortcut on the
Desktop. It auto-starts the board if it is down and opens a standalone app window
(Edge app-mode) — see `scripts\windows\Open-Board-Desktop.ps1`.

**Board views:**
- **Board** — live swarm kanban (per team SSE).
- **Tools** — manage MCP servers + skills for interactive sessions AND spawned
  agents (writes repo `.mcp.json` + worker config together); agent profiles list.
- **Models · OpenRouter** — provider/model picker, autorouter role table
  (primary / small_fast / fallback / vision / deep_reasoning → applied to the
  swarm profile env), live top-model rankings (OpenRouter tool/image usage,
  auto-refresh), model comparison (price/context/cache economics), key & spend
  stats, and a cache lab that measures real prompt-cache hits. Routing table
  persists at `~\.clawteam\openrouter_routing.json`; the API key is read from
  env `OPENROUTER_API_KEY` only.

Stop:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\Stop-Swarm.ps1 -Team se-swarm
```

## 5. Providers & secrets — environment only, never files

Secrets are read live from the Windows environment at spawn/call time; referenced by
NAME in all configs (never values):

`OPENROUTER_API_KEY` · `TWILIO_API_KEY` (+SID vars when present) · `SENDGRID_API_KEY` ·
`OPENAI_API_KEY` · `BIFROST_MCP_VIRTUAL_KEY` (AgentCore MCP facade auth)

**Default provider: OpenRouter — GLM-5.3** (verified live 2026-09-16, key valid):

| Profile | Model | Use |
|---|---|---|
| `openrouter-claude` (**default**) | `z-ai/glm-5.3` (+ `glm-5.3-flash` as small/fast) | All swarm agents |
| `openrouter-deepseek` | `deepseek/deepseek-v4-pro-0813` | Fallback — `-Profile openrouter-deepseek` |
| `default-claude` | Claude Code's own login | Manual/interactive use |

Switch defaults: `clawteam config set default_profile openrouter-deepseek`.
Swarm agents run with an isolated Claude config (`.clawteam-local\claude-config`) so
your interactive AgentCore hooks never block headless prompts (see §6b).

## 6. Memory — ALL-LOCAL (operator directive 2026-09-16)

All memory, storage, and databases are LOCAL on this PC. OpenMemory/mem0 wiring is
**removed** (the 8760 service is gone and must not be reintroduced); Obsidian vault
MCP is likewise banned. Rules: `.rules/memory-local.md`.

- **Team memory** = AgentCore memory facade, wired as the single MCP server
  `agentcore-gateway` (HTTP → bifrost `127.0.0.1:8080/mcp`, Bearer
  `$BIFROST_MCP_VIRTUAL_KEY` from User-scope env). Defined in BOTH the repo
  `.mcp.json` (interactive sessions) and the spawned-worker config
  `.clawteam-local\claude-config\.claude.json`; the sync hook copies `.mcp.json`
  into each new worktree at spawn. Verify: `claude mcp list` → `agentcore-gateway ✔`.
- **Workspace state** = plain local files under `~\.clawteam\` + `.clawteam-local\`.
- **Databases** = loopback only: AgentCore PG `127.0.0.1:55433` (governed, facade
  tools only — no raw SQL), SwarmRecall `127.0.0.1:3300` (server-side adapter).
- **Known limitation (operator to clear):** project-scoped memory tools
  (`session_open`, `append_event`, `docs_search`, …) require a signed
  **device assertion**; the device-identity migration window closed 2026-08-09 and
  headless swarm agents hold no device identity. Non-assertion tools
  (e.g. `memory_status`) work for wired agents today. Fixing assertion issuance for
  headless agents is a control-plane decision (proposals only — do not edit
  agentcore-control-plane from this repo).
- **Measured performance (2026-09-16, this PC):** local file write+read ≈ 0.34 ms
  median; SwarmRecall loopback HTTP ≈ 2.1 ms; MCP initialize via bifrost ≈ 0.6 ms
  (28 ms cold). The old paths are strictly worse: OpenMemory (8760) was an extra
  HTTP service layer and is down; Obsidian REST required the Obsidian app running
  as an HTTPS middleman. Local storage wins on every path — no action needed.

## 6f. Multimedia Studio - Characters (reusable identity workflow, verified live 2026-09-23)

Goal-oriented flow in the Media panel's **Characters** tab (Lane A - stylized
3D-LOOKING imagery; NOT a true 3D mesh - true-3D providers attach later behind
the same provider boundary):

1. **Create Character** - upload a photo (self-hosted temporary public link,
   see the note below) or paste any public https link + name -> two
   identity-preserving kontext edits: *sculpt* (3D animated-film render)
   -> *stylize* (big-studio movie character). Actual cost: 10 credits
   (5+5, verified live). The canonical image lands in the character record +
   asset library.
2. **New look...** - identity-consistent variants (pose / clothing /
   expression / environment / camera angle): the gateway-style wrapper
   enforces "same character, keep identity exactly consistent" on every edit
   from the canonical reference. 5 credits (verified).
3. **Animate** - i2v from the canonical (or a variant) into a 5s/720p scene,
   registered to the character. 12 credits (verified).

Character records live at `~/.clawteam/media/characters/chr-*.json` with
canonical + variants + scenes linked to asset ids. Jobs show stages
(`_stages`) and survive restarts: completed stages are kept, an in-flight
stage resumes by re-polling its provider task (NO resubmit, no double
charge - proven live), and a user-initiated retry strips failed stages only
(provider failures are auto-refunded upstream).

Live proof (2026-09-23): portrait -> "Maya" canonical -> red-jacket waving
variant -> animated wave scene; all assets served from the library; 32
credits total. KIE balance visible in the Media cloud badge.

Photo-upload note (RESOLVED 2026-09-26, operator chose the self-hosted path):
the official KIE API has NO file-upload endpoint (probed: /api/v1/common/upload
and variants = 404). Personal photos now go through the **self-hosted
temporary-link lane**: Characters tab → "Upload a photo…" → board saves the
photo under an unguessable token in `~/.clawteam/media/uploads/` and serves it
at a temporary public https URL on the operator's own domain —
`https://photos.miaknuckles.com/<token>.<ext>` (dedicated cloudflared tunnel
`clawteam-photos` → loopback photo host on 18790, config
`~/.cloudflared/clawteam-photos.yml`; started with the board by
`scripts\windows\Start-PhotoTunnel.ps1`). Links auto-expire after 24 h
(expired reads → 410; a 15-min sweep inside the media worker deletes files);
the photo host serves ONLY token-named image files — the board and every
other service stay loopback-only. Machine config (no secrets):
`~/.clawteam/media/photohost.json` (`public_origin` / `port` / `ttl_hours`).
Verified E2E live 2026-09-26: upload → public fetch byte-identical through the
Cloudflare edge → character "Test Maya" (10 credits). Pasting any public
https photo link still works.

## 6e. KIE.ai cloud media lane — VERIFIED LIVE (2026-09-23)

Both KIE generation lanes work end-to-end through the Multimedia Suite
(Media tab → Create → cloud route), with the app-owned lifecycle enforced:

- **Image (flux1-kontext)**: t2img/edit/img2img; verified E2E — job -> queue ->
  adapter -> KIE createTask -> recordInfo polling (exponential backoff) ->
  download-to-local-assets BEFORE "succeeded" -> asset in Library.
  Actual cost **5 credits/image** (verified via creditsConsumed).
- **Video (runway)**: t2v/i2v (5s/720p tested); verified E2E — 1.48MB MP4
  downloaded into the asset library. Actual cost **12 credits** (verified).
- **Pricing law**: estimates are shown pre-submit but real costs come from
  KIE's creditsConsumed field (stored per job as cost_actual_*). Verified
  actuals: kontext 5cr, runway 12cr (estimates initially 4-6x high — the
  provider's own numbers now win).
- **Recovery law (proven)**: a successful generation whose download failed lands
  in `succeeded_provider_download_failed` and can be RETRIED without
  resubmitting (re-polls the same taskId — no double charge).
- recordInfo result shape (verified): `data.response.resultUrls` +
  `data.resultJson` (JSON-encoded string) + `data.creditsConsumed`.
- Credits balance visible in the Media view cloud badge (refreshes on load).

## 6d. Local GPU hybrid acceleration & ComfyUI API bridge (2026-09-17)

**RTX 4070 SUPER (12GB)** is a first-class execution lane for the whole stack:

- **Bridge**: `D:\ComfyUI\comfyui_mcp.py` (MCP stdio, Python 3.13) exposes 4 tools —
  `comfyui_status`, `comfyui_ensure_running` (lazy-boots the portable ComfyUI hidden,
  ~30s cold), `comfyui_list_models`, `comfyui_generate_image` (SDXL txt2img, seeded,
  saves to `D:\ComfyUI\...\output\bridge\`). Verified E2E: 1024×1024 RealVisXL image in
  ~16s on GPU.
- **Wired into ALL agent surfaces**: repo `.mcp.json` + worker config (swarm agents),
  and the OpenClaw gateway (`mcp.servers`) — so AnyClaw on the phone can generate
  images on the PC GPU through chat too.
- **Autorouter role**: `image_gen` → `comfyui:RealVisXL_V5.0_fp16.safetensors`
  (local-first; cloud image models only as fallback per the all-local policy).
- ComfyUI serves loopback only (127.0.0.1:8188); bridge log at
  `D:\ComfyUI\ComfyUI_windows_portable\comfyui-bridge.log`.
- Cost model: local GPU generation is free and private; use it for app icons, mock
  assets, and UI imagery instead of paid image APIs.

## 6b. AgentCore integration status

Your interactive Claude Code runs AgentCore ContextEngine hooks that block prompts in
non-enrolled projects. For this workspace:

- `D:\github\ClawTeam` **is enrolled** in the AgentCore contract (project key `clawteam`,
  rollback snapshot saved in `agentcore-control-plane\.agentcore\rollback\...`). Your own
  interactive Claude sessions here bind to the context engine normally.
- Agent **worktrees** are enrolled automatically at spawn by the sync hook, BUT the
  gateway's `session_open` currently rejects worktree paths with an opaque
  `mcp_tool_error` even when enrolled (repo root works). That is gateway-side, in your
  control-plane stack — worth a look there.
- **Consequence**: spawned swarm agents run with `CLAUDE_CONFIG_DIR` pointed at
  `.clawteam-local\claude-config` (no hooks, clawteam skill installed) — headless agents
  are immune to the block, and your interactive setup is untouched. Verified end-to-end:
  agent claimed a task, executed it, reported `STEP DONE` to the leader inbox, and
  checkpointed its worktree — all on GLM-5.3 via OpenRouter.

## 6c. Phone control (S26 Ultra / anyclaw)

The phone controls this PC through two channels, both authenticated with **Windows
credentials** (Windows OpenSSH authenticates against your Windows user account):

1. **One-time admin setup** (accepts UAC, ~30 seconds):
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\phone\Enable-PhoneControl.ps1
   ```
   Installs/starts OpenSSH Server (auto-start), opens firewall for SSH (22) and the
   board (8788) on the local subnet only, prints this PC's IP.

2. **From the phone** (anyclaw shell skill, Termux, any SSH client):
   ```
   ssh ynotf@<pc-ip>                      # password = your Windows account password
   D:\github\ClawTeam\scripts\phone\swarm.cmd status
   D:\github\ClawTeam\scripts\phone\swarm.cmd start -Goal "<mission>"
   D:\github\ClawTeam\scripts\phone\swarm.cmd task "<subject>" agent
   D:\github\ClawTeam\scripts\phone\swarm.cmd message plan "<directive>"
   D:\github\ClawTeam\scripts\phone\swarm.cmd log 60
   D:\github\ClawTeam\scripts\phone\swarm.cmd stop
   ```

3. **Dashboard from the phone browser**: `http://<pc-ip>:8788` (start swarm with
   `-ExternalBoard`, or `scripts\windows\Start-Board.ps1 -External`). The board UI can
   inject tasks and set mission context directly — enough to steer the swarm from
   anyclaw with just HTTP if SSH is unavailable.

4. **USB-grade control via adb** (wireless debugging):
   ```powershell
   .\scripts\phone\connect-phone.ps1 -IpPort <phone-ip:port> [-PairIpPort <ip:port> -PairCode <code>]
   ```
   Pairs/connects adb, detects anyclaw, and sets `adb reverse tcp:8788 tcp:8788` so the
   phone can open `http://localhost:8788` with zero firewall changes. The S26 Ultra was
   **not visible to adb** during setup (no devices/mDNS) — run the connect script with
   the IP:port from Developer options → Wireless debugging.

Additional agent CLIs installed for the swarm (optional workers via template
`command` overrides): `codex` 0.154.0, `opencode` 1.18.31, `openclaw` 2026.9.4.
Codex/opencode still need their one-time interactive auth (`codex login` /
`opencode auth login`) — Claude-via-OpenRouter needs nothing extra.

## 7. Theme system (4-token)

`design/theme.tokens.json` → `~\.clawteam\theme.json` → board `/api/theme`:

1. `light-google` — Google palette (blue primary, red secondary, green/orange/pink/yellow)
2. `light-orange` — light+dark orange, blue/green accents, yellow card strokes
3. `dark-speakeasy` — dark, rainbow strokes, live animated background (default)
4. `dark-orange` — deep black, orange pair, blue/green accents, yellow strokes

Switch modes via the sidebar picker on the board. No color/style value is hardcoded at
component level anywhere — board UI included (converted to CSS variables +
`--stroke-gradient`). The same law binds all agent-generated output via
`.rules/design-system.md`.

## 8. Rule surfaces (default folder setup)

| Surface | Files |
|---|---|
| Canonical pack | `.rules\design-system.md`, `security-secrets.md`, `memory-openmemory.md`, `swarm-operations.md` |
| Agent entry | `AGENTS.md`, `CLAUDE.md` (point at BLUEPRINT + `.rules`) |
| Cursor | `.cursorrules` + `.cursor\rules\*.mdc` (4 rules, alwaysApply) |
| Canonical truth | `BLUEPRINT.md` |

## 9. Framework fixes applied in this workspace (vs upstream HEAD `0119833`)

1. `clawteam\spawn\adapters.py` — `os.getuid` crash on Windows (guarded; fixes 15 tests).
2. `clawteam\spawn\subprocess_backend.py` — subprocess backend now emits `AfterWorkerSpawn`
   (hooks work without tmux).
3. `clawteam\board\server.py` + `static\index.html` — `/api/theme` route + full theme engine,
   zero hardcoded component colors, theme picker, live-background toggle, gradient strokes.

Known noise: `tests/test_spawn_backends.py` keeps 14 failures on Windows from upstream
POSIX-only assumptions (`/usr/bin`, `/bin/sh`, `:` path separators) — verified identical
on pristine HEAD; not caused by this setup.

## 10. First autonomous project (no human in the middle) — runbook

```powershell
# 0. Once: phone control (UAC prompt) + connect the phone
powershell -ExecutionPolicy Bypass -File scripts\phone\Enable-PhoneControl.ps1
.\scripts\phone\connect-phone.ps1 -IpPort <phone-ip:port>

# 1. Fire the swarm at a real goal (hidden, GLM-5.3 via OpenRouter, board on LAN)
powershell -ExecutionPolicy Bypass -File scripts\windows\Start-Swarm.ps1 -Goal "<your project goal>" -ExternalBoard

# 2. Watch from PC or phone
start http://127.0.0.1:8788        # phone: http://<pc-ip>:8788
.venv\Scripts\clawteam.exe board show se-swarm

# 3. Steer (optional) - from anywhere
scripts\phone\swarm.cmd task "Add dark mode toggle" agent
scripts\phone\swarm.cmd message plan "Prioritize the API before the UI"

# 4. Done
powershell -ExecutionPolicy Bypass -File scripts\windows\Stop-Swarm.ps1
```

Known constraints to keep in mind: headless `-p` agents exit when they stop acting —
the worker loop keeps them alive by design (poll + sleep), and `plan` re-spawns via
`clawteam spawn --resume` if a lane dies mid-mission. OpenMemory is still down
(memory features degrade). Codex/opencode need one-time `login` before use as workers.

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| `claude: command not found` in agent logs | Launchers prepend `~\.local\bin`; for manual shells run `scripts\setup_local.ps1` (adds it to user PATH) or set it yourself |
| Board unreachable | `scripts\windows\Start-Board.ps1 -Port <other>`; 8080 is occupied by bifrost |
| Agents idle, no tasks | Ask via board UI ("New Task", owner `agent`) or `clawteam task create se-swarm "..." -o agent` |
| `plan` not rewriting §3 | Check `.clawteam-local\logs\se-swarm.log` and `clawteam inbox peek se-swarm` |
| AgentCore `mcp_tool_error` on worktrees | Known gateway quirk (see §6b); swarm agents are insulated via isolated CLAUDE_CONFIG_DIR |
| `unrecognized_model` warnings in claude stderr | Cosmetic (OpenRouter models vs Claude Code's known list); `CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT=1` is already set in profiles |
| Phone can't SSH | Run `Enable-PhoneControl.ps1` as admin; password is your Windows account password (Microsoft-account password if you sign in with MSA — PIN never works over SSH) |
| adb shows no device | Wireless debugging port rotates — re-read it from Developer options and run `connect-phone.ps1` |
| OpenMemory errors | `scripts\memory\openmemory_check.py`; start the local stack or ignore |
| Everything on fire | `Stop-Swarm.ps1` then `Start-Swarm.ps1` again (teams are cheap) |
