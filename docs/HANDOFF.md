# ClawTeam Control-Plane — Engineering Handoff

> State as of **2026-09-26** (photo-upload lane added; baseline doc was
> 2026-09-24). Owner: Tony (ynotfins). This document is the
> single entry point for any engineer or agent taking over this project.

## 1. What this project is

A **Windows-native developer control-plane** built on the ClawTeam framework
(HKUDS upstream): a multi-agent autonomous engineering runtime (6-lane swarm,
git-worktree workers) plus a first-class **Multimedia Studio** (image/video
generation, reusable characters), served by one local web app styled with the
**R3lentless-Grind Design System (RGDS)**. Local ComfyUI on an RTX 4070 SUPER
is the cost-saving execution tier; **KIE.ai** is the cloud provider. Providers
sit behind an app-owned boundary — the UI never talks to them directly.

- Repo: `D:\github\ClawTeam` · Branch: **`feat/dev-control-plane-multimedia-studio`**
  · Remote: `fork` → https://github.com/ynotfins/ClawTeam (upstream `origin` =
  HKUDS, read-only). All work is committed and pushed (commit `9b47fd8` + docs).
- Start here: [`BOOTSTRAP.md`](../BOOTSTRAP.md) (operator manual) ·
  [`ARCHITECTURE.md`](ARCHITECTURE.md) · [`OPERATIONS.md`](OPERATIONS.md) ·
  [`MEDIA_STUDIO.md`](MEDIA_STUDIO.md) · design law:
  [`.rules/design-system.md`](../.rules/design-system.md).

## 2. Verified baseline (everything below was proven live, not assumed)

| Capability | Evidence |
|---|---|
| Board control-plane | HTTP 200 on 8788; all four views render; SSE kanban |
| Swarm runtime | 6-lane template; E2E autonomy proven earlier (agent claimed task → STEP DONE → checkpoint); stale test team cleaned |
| agentcore-gateway | MCP `✔ Connected` (repo, worker config, openclaw gateway) |
| RGDS frontend | 1.1.0 vendored (sha-locked); all 4 themes cycle live; zero color literals (test-enforced) |
| Local GPU lane | ComfyUI auto-boot; 1024² SDXL image ~16 s |
| KIE image lane | Live job → asset library (flux1-kontext, **5 credits actual**) |
| KIE video lane | Live 5 s/720p MP4 (runway, **12 credits actual**) |
| Recovery laws | download-failure state + retry re-polls task (no double charge) — proven live twice |
| Characters | Full E2E: portrait → canonical → variant → animated scene (32 credits); mid-stage resume across a board restart proven live |
| Photo upload (self-hosted) | Characters upload → temporary public https link on own domain (`photos.miaknuckles.com`, cloudflared `clawteam-photos` → 18790) → KIE character "Test Maya" (10 credits, balance 26→16) — proven live 2026-09-26; 24 h auto-expiry + sweep |
| Tests | **640 passed, 2 skipped** (`--basetemp=.clawteam-local/pytest-tmp` on this machine; was 616 / 2 at the 2026-09-24 baseline) |

KIE balance at handoff: **26 credits (~$0.13)**. Balance shows in the Media
cloud badge.

## 3. Where things live

- Code: `clawteam/board/` (app), `clawteam/media/` (studio pipeline),
  `clawteam/team|spawn/` (swarm), `scripts/windows/` (launcher scripts),
  `design/theme.tokens.json` (domain theme layer — no colors).
- Data: `~/.clawteam/` (teams, tasks, media jobs/assets/characters) and
  `<repo>/.clawteam-local/` (logs, worker config — gitignored).
- History note: an abandoned family-assistant experiment is archived at
  `.clawteam-local/archive/family-20260923/` — **inert by design; do not
  delete and do not revive** without the owner's explicit instruction.

## 4. Open decisions & known gaps (owned by Tony)

1. **Photo upload for Characters** — **RESOLVED 2026-09-26: option (b),
   self-hosted**. Implemented + verified live (see §2). Photos get a
   temporary public https link on the operator's own domain
   (`photos.miaknuckles.com` → cloudflared tunnel `clawteam-photos` →
   loopback photo host 18790); 24 h auto-expiry; the photo host is the only
   publicly reachable process. Machine-local artifacts (not in the repo):
   `~/.clawteam/media/photohost.json`, `~/.cloudflared/clawteam-photos.yml`
   + tunnel credentials, DNS record `photos.miaknuckles.com`.
   *Cleanup note:* one stray DNS record was created while probing the CLI's
   zone handling — `photos.4axe.com` inside the miaknuckles.com Cloudflare
   zone (unreachable: no TLS cert at that depth; harmless). cloudflared has
   no record-delete command; delete it once in the Cloudflare dashboard if
   you want the zone tidy.
2. **True 3D assets (Lane B)**: no provider wired; the boundary already
   supports adding one (adapter + kind + pricing entry) without UI changes.
3. **Enhance/upscale lane**: UI present; needs a provider choice (researched
   2026-09-26, not implemented — operator picks):
   **(a) Local ComfyUI** — `RealESRGAN_x2plus.pth` + `RealESRGAN_x4plus.pth`
   are **already installed** in
   `D:\ComfyUI\ComfyUI_windows_portable\ComfyUI\models\upscale_models\` (the
   old "empty" note is stale). $0/image, private, seconds on the 4070 SUPER;
   work = an `upscale` workflow in `comfyui_local.py` (repo code only — no
   ComfyUI-side change, no model download). Classic ESRGAN quality.
   **(b) KIE cloud `recraft/crisp-upscale`** — same jobs API as the existing
   adapters (`POST createTask`, model id `recraft/crisp-upscale`, input
   `{image: <public URL>}` — the photo lane covers input hosting); spec's
   illustrative cost ~1 credit (~$0.005)/image.
   **(c) KIE cloud `topaz/image-upscale`** — model id `topaz/image-upscale`,
   input `{image_url, upscale_factor: '1'|'2'|'4'}`; spec's illustrative cost
   ~10 credits (~$0.05)/image (premium quality). Cloud prices are
   estimates-only until a live task reports `creditsConsumed`.
   Decision owned by Tony; do not implement before the choice.
4. **Device-identity assertions** for headless agent DB writes — gateway-side
   policy; proposals only (control-plane governance).
5. SwarmRecall scheduled tasks remain disabled (start manually when needed).
   Proposal (2026-09-26, no action taken): **stay documented-manual** — the
   deliberate shutdown-time disable should hold until the pending WS3.3 work
   lands (it may change how the service starts, and nothing in the
   control-plane product depends on port 3300 being up). Re-enable as part of
   WS3.3, or earlier if recall is wanted ad hoc (one-time
   `Enable-ScheduledTask` on SwarmRecallApi + SwarmRecallMeilisearch —
   loopback-only, no cloud spend).

## 5. Environment & secrets

Windows 11 native. Python venv at `.venv/` (framework) — media pipeline is
stdlib-only. Provider keys are **User-scope env vars only**:
`OPENROUTER_API_KEY` (swarm + models), `KIE_API_KEY` (cloud media). Configs
reference keys by name; nothing stores values. Ports and services:
`OPERATIONS.md`.

## 6. How to pick up work

1. Read `BOOTSTRAP.md` top-to-bottom (§6b–6f cover this product's additions).
2. Start the board (`OPERATIONS.md` daily commands) and click through every
   view — ten minutes makes the rest of the docs concrete.
3. Run the suite; 636 green is the baseline. Anything red is a regression you
   introduced or a discovery worth writing down.
4. Branch from `feat/dev-control-plane-multimedia-studio`; the suite + the
   design law are the gates. Push to `fork`.
5. For the open items in §4, propose before building where they touch scope,
   trust, or third-party spend.

## 7. Recent history

See [`CHANGELOG.md`](../CHANGELOG.md) — the product-level log of this
deployment (framework upstream history remains in git log / upstream docs).
