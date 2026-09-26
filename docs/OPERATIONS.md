# Operations — Services, Start/Stop, Recovery

Everything runs native on Windows; no Docker anywhere. All long-running
services are loopback-bound unless noted.

## Service map

| Service | Port | Starts | Stop |
|---|---|---|---|
| **ClawTeam board** | 8788 | manual (below) | kill PID on 8788 |
| Photo host (temp public photo links) | 18790 | thread inside the board process (auto) | dies with the board |
| Photo tunnel (photos.miaknuckles.com → 18790) | — | `Start-Board.ps1` → `Start-PhotoTunnel.ps1` (idempotent) | kill PID in `.clawteam-local\run\photo-tunnel.pid` |
| OpenClaw Gateway | 18789 | Scheduled Task `OpenClaw Gateway` (auto) | CLI `gateway restart` (NOT Restart-ScheduledTask) |
| bifrost (LLM/MCP) | 8080 | its own autostart | — leave alone |
| ComfyUI (local media tier) | 8188 | auto-booted hidden by the media router on first local job (~30 s) | dies with PC; safe to kill |
| SwarmRecall | 3300 | ⚠ scheduled tasks DISABLED — start manually if needed | `Start-AgentCoreSwarmRecallComponent.ps1` |
| AnyClaw (phone) | — | reconnects via tailscale serve 443 → 18789 automatically | — |

## Daily commands

Start the board (operator PC):
```powershell
cd D:\github\ClawTeam
powershell -ExecutionPolicy Bypass -File scripts\windows\Start-Board.ps1 -NoBrowser
```
The **ClawTeam Board** desktop shortcut does the same and opens the app window
(auto-starts the board if down).

Launch a swarm:
```powershell
cd D:\github\ClawTeam
powershell -ExecutionPolicy Bypass -File scripts\windows\Start-Swarm.ps1 -Goal "<real goal>"
```
Stop a swarm: `scripts\windows\Stop-Swarm.ps1 -Team <team>`.

Run tests:
```powershell
cd D:\github\ClawTeam
.venv\Scripts\python.exe -m pytest tests\ -q --basetemp=.clawteam-local\pytest-tmp
```
(`--basetemp` is required on this machine — the default temp junction goes
stale; fix with `cmd /c rmdir` on `pytest-current` if pytest refuses to start.)

## Recovery playbooks

**Board wedged / port conflict**: two board generations can fight over 8788.
Kill *every* listener PID (`netstat -ano | findstr :8788`), then start once.
Symptoms: page loads but `/api/*` returns empty/`000`.

**Media job stuck in `running`**: check the provider task first (KIE jobs can
legitimately take minutes; polling backs off to 30 s). If the board restarted
mid-job, completed stages resume by re-polling the provider task — no resubmit,
no double charge. `timed_out`/`failed` jobs retry via the Jobs tab (character
retries keep completed stages; provider failures are auto-refunded).

**Cloud lane shows dormant**: `KIE_API_KEY` missing from User env (board
restart needed to pick it up). Health: Media tab cloud badge, or
`curl http://127.0.0.1:8788/api/media/providers`.

**Local lane gates failed**: ComfyUI auto-boot only works if
`D:\ComfyUI\ComfyUI_windows_portable` + checkpoint exist. Health detail names
the failed gate. Check `comfyui-bridge.log` in that folder.

**Photo link expired / unreachable**: uploads live in `~/.clawteam/media/uploads/`
with a 24 h TTL (`~/.clawteam/media/photohost.json`). The photo host rides in
the board process (18790) and the public route is the `clawteam-photos`
cloudflared tunnel (`~/.cloudflared/clawteam-photos.yml`); both come up with
`Start-Board.ps1`. Re-upload the photo if the link expired — expired reads
return 410 and the sweep deletes the files.

**AnyClaw disconnected**: force-stop + relaunch `com.claw.control` on the
phone (`adb shell am force-stop com.claw.control` then monkey-launch). It
reconnects through the tailscale serve path.

## Secrets (unchanged law)

All provider keys are User-scope environment variables only:
`OPENROUTER_API_KEY`, `KIE_API_KEY`, … The board/`docs-lock`/configs reference
them **by name**; nothing stores values. Never paste a key into a file.

## Upgrade paths

- **RGDS**: new release → re-extract tgz into `clawteam/board/static/rgds/`,
  bump version in `PROVENANCE.md` + `design/theme.tokens.json` + `docs-lock.json`
  (tests assert all three agree).
- **ClawTeam framework (upstream)**: this fork tracks `main` from HKUDS; our
  product branch is `feat/dev-control-plane-multimedia-studio` on
  `ynotfins/ClawTeam`. Rebase deliberately; the suite is the gate.
- **KIE models**: add an adapter class + a pricing entry. Pricing table is
  estimates-only; provider-reported `creditsConsumed` is authoritative and is
  stored per job.
