# Changelog

Product-level log for **this deployment** (the Windows-native developer
control-plane on the ClawTeam framework). Framework changes from upstream
HKUDS remain in git history and upstream docs. Dates are 2026.

## [0.3.0-product.4] — 2026-09-26 — Self-hosted photo lane for Characters

### Added
- **Photo upload with temporary public links** (operator decision: option b,
  self-hosted — no third-party upload host): Characters tab → "Upload a
  photo…" → `POST /api/media/uploads` (raw image body, magic-byte sniffed,
  20 MB cap, jpg/png/webp) → token-named file in `~/.clawteam/media/uploads/`
  → served at `https://photos.miaknuckles.com/<token>.<ext>` through a
  dedicated cloudflared tunnel (`clawteam-photos`) to the loopback photo host.
- `clawteam/media/uploads.py` (`UploadStore`: unguessable tokens, 24 h TTL
  config, lazy expiry + 15-min sweep inside the media worker) and
  `clawteam/media/photohost.py` (the ONLY publicly reachable process — serves
  token-named image files exclusively; board + all other services stay
  loopback-only).
- Board routes: `GET/POST /api/media/uploads`, `GET /api/media/uploads/<t>/file`;
  UI upload button + preview + expiry note (RGDS classes only).
- `scripts/windows/Start-PhotoTunnel.ps1` (idempotent; started with the board)
  and machine-local config `~/.clawteam/media/photohost.json` (no secrets).
- 20 new tests (`tests/test_photohost.py`: store, sniff, expiry/sweep,
  traversal guards, photo host 404/410 behavior, board routes, worker sweep).
  Suite: **636 passed / 2 skipped** (was 616 / 2).

### Verified live (2026-09-26)
- Public link fetch is byte-identical through the Cloudflare edge; unknown
  tokens 404 publicly.
- Full E2E: local-GPU portrait (free) → upload → public link → KIE character
  **"Test Maya"** (sculpt + stylize, exactly 10 credits; balance 26 → 16) →
  canonical asset in the library.

### Notes
- The cloudflared CLI on this machine can only write DNS in the miaknuckles.com
  zone (its cert scope), hence `photos.miaknuckles.com` rather than a 4axe.com
  hostname; one unreachable stray DNS record (`photos.4axe.com` inside the
  miaknuckles zone) was left by the probe and can be deleted in the dashboard.

## [0.3.0-product.3] — 2026-09-24 — Characters, docs, push

### Added
- **Characters: reusable-identity workflow** (`clawteam/media/characters.py`
  + Characters tab): photo → *sculpt* (3D animated-film render) → *stylize*
  (big-studio character) canonical; identity-consistent **variants** ("New
  look…"); **Animate** to 5 s scenes — all registered to the character with
  canonical/variants/scenes linked to library assets.
- Character job kinds `character` / `variant` with stage tracking (`_stages`),
  per-stage assets, and summed actual costs.
- **Mid-stage resume**: a board restart mid-pipeline re-polls the in-flight
  provider task — no resubmit, no double charge (proven live).
- **Retry semantics**: user-initiated retry keeps completed pipeline stages
  and strips the failed tail (provider failures auto-refunded upstream).
- 8 new tests (store CRUD, pipeline with fakes, variant registration, adapter
  input-image law, https-only validation). Suite: **616 passed / 2 skipped**.
- Professional doc set: `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md`,
  `docs/MEDIA_STUDIO.md`, `docs/HANDOFF.md`, this changelog; README pointer.
- All work pushed to `ynotfins/ClawTeam` — branch
  `feat/dev-control-plane-multimedia-studio`.

### Fixed
- Pipeline stored KIE's `(task_id, model)` tuple un-unpacked — poller hit an
  invalid URL until timeout; now unpacked at submit.

### Decisions pending
- Personal-photo upload path (community host vs own-domain temp link).

## [0.3.0-product.2] — 2026-09-23 — KIE lanes verified, family experiment reverted

### Added
- **KIE cloud media lane, live-verified end-to-end**: image (flux1-kontext,
  5 credits actual) and video (runway 5 s/720p, 12 credits actual) through
  the full job → adapter → poll → download → asset-library lifecycle.
  Download-before-complete and no-resubmit retry proven live (a real
  download failure recovered without a second charge).
- Provider-reported **actual costs** (`creditsConsumed`) stored per job;
  pricing table corrected from verified actuals (estimates had been 4–6×
  high) — `kie-pricing-2026-09-23/3`.
- recordInfo result extraction hardened (URLs live in `response.resultUrls`
  *and* a JSON-encoded `resultJson`; dedup preserves order).

### Reverted
- Family/mother-daughter assistant experiment (per operator directive):
  services stopped, Windows app uninstalled, routes/UI removed; full archive
  kept at `.clawteam-local/archive/family-20260923/` (inert, recoverable).

### Changed
- **RGDS 1.1.0 vendored** (form-factor release: responsive bands
  mobile/tablet/desktop; `form-factor.css` linked; sha-locked provenance;
  tests assert cross-file version consistency instead of pinning 1.0.1).

## [0.3.0-product.1] — 2026-09-16..22 — Control-plane + Multimedia foundation

### Added
- **Board control-plane app** (stdlib server + RGDS 1.0.1→1.1.0 frontend):
  Tools panel (MCP servers + skills manager across repo/worker/user scopes),
  Models panel (OpenRouter topology, autorouter role table, live rankings,
  model comparison, key & spend, cache lab), Media panel.
- **Multimedia Suite foundation** (`clawteam/media/`): app-owned job
  lifecycle (incl. `provider_succeeded`, `downloading`,
  `succeeded_provider_download_failed`), file-backed job/asset stores,
  exponential-backoff polling, per-kind timeouts, single-flight local lane,
  cloud throttle, provider boundary (`MediaProvider` protocol).
- **Local GPU tier**: ComfyUI bridge (status/ensure-running/list/generate),
  lazy hidden boot, seeded SDXL generation (~16 s at 1024²) — wired into repo,
  worker configs, and the OpenClaw gateway MCP set.
- Media API + UI (Create/Library/Jobs) with cost + route visibility.
- **All-local memory policy** enforced: OpenMemory wiring removed;
  agentcore-gateway facade wired into repo + worker configs; obsidian vault
  MCP removed per operator directive.
- Desktop app: `Open-Board-Desktop.ps1` + shortcut + generated icon.
- Windows-native fixes: `Start-Board.ps1` CIM fallback (Get-NetIPAddress
  broken on this PC), spawn adapter `getuid` guard, AfterWorkerSpawn emit.
- Hardening: redundant portproxy removed; AnyClaw re-verified via serve.
- Full-stack skills library (flutter, react-native, android, ios-handoff,
  web, local-database, api-backend, fullstack-architecture, device-e2e) in
  repo/worker/user scopes.
