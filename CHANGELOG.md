# Changelog

Product-level log for **this deployment** (the Windows-native developer
control-plane on the ClawTeam framework). Framework changes from upstream
HKUDS remain in git history and upstream docs. Dates are 2026.

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
