# BLUEPRINT.md — How Every Feature Is Built, Wired, and Proven

> **Scope**: every feature this deployment fork added on top of the HKUDS ClawTeam framework,
> described at engineering depth: implementing modules, surfaces (CLI/routes), the logic and
> guards inside, and the tests that prove each one works. Section numbers are shared with
> [README.md](README.md) (what each feature does) and [CONTEXTBLOCK.md](CONTEXTBLOCK.md)
> (what each feature is for and outputs at its best).
>
> **Note (D-019)**: the swarm's canonical team-truth blueprint — the file `plan` rewrites each
> step — lives at **`docs/SWARM_BLUEPRINT.md`**. This file is owner-directed documentation.
>
> Conventions: state roots per `docs/STORAGE_AND_DATA_CONTRACT.md` — `CLAWTEAM_DATA_DIR`
> (else `~/.clawteam`) for data, repo-local `.clawteam-local/` for run state, atomic
> `.tmp` + `os.replace` writes everywhere. Tests run with
> `pytest --basetemp=.clawteam-local/pytest-tmp`.

---

## 1. Board — the web control plane

**Built**: `clawteam/board/server.py` (stdlib `ThreadingHTTPServer`; `serve()` at L1145 binds
`127.0.0.1`, default port 8080 — the operator default **8788** is set by `Start-Board.ps1`
`-Port 8788`), `clawteam/board/collector.py` (`BoardCollector.collect_overview/collect_team`),
`clawteam/board/renderer.py` (Rich CLI for `clawteam board show|live|overview|attach|gource`),
UI: `clawteam/board/static/index.html` (single-page, no framework).

**Wiring**: `serve()` builds the collector, wires class attrs onto `BoardHandler`, starts
`TeamSnapshotCache(ttl_seconds=interval)` (L147–168 — load-outside-lock TTL cache), starts the
`MediaRouter()` worker thread, and starts the photo host ("board up = photo lane up"), then
serves forever. GET routes: `/api/overview`, `/api/theme` (mtime-cached read of
`~/.clawteam/theme.json`), `/api/tools/mcp|skills|profiles`, `/api/ocr/tools`, `/api/kis/policy|mode`,
`/api/openrouter/models|rankings|key|routing`, `/api/media/presets|providers|jobs|assets|characters|uploads`,
binary asset/upload files, `/api/team/<name>`, SSE `/api/events/<team>` (`_serve_sse` L1115 —
infinite loop pushing `collect_team` snapshots every `interval`, sharing the snapshot cache),
and `/api/proxy?url=` (GitHub-only egress). POST routes: tools add/remove/test, `/api/ocr/call`,
`/api/kis/*`, `/api/media/uploads|jobs|estimate|jobs/<id>/retry`, `/api/openrouter/routing|set-model|cache-lab`,
`/api/team/create`, `/api/team/<name>/task`.

**Logic**: the SPA's `init()` fetches `/api/overview`, populates `#team-select` (Active Swarm);
picking a team opens an `EventSource` and re-renders a 4-column kanban. Team creation from the
Board (`_api_team_create` L991) loads the `fullstack-commercial` template and creates team +
members + 5 seed tasks (no agent spawn). The egress proxy normalizes targets, **blocks
loopback/private/link-local/metadata hostnames**, uses a no-redirect handler (redirect to a
disallowed host = rejected), and only fetches github.com hosts. UI text is escaped
(`test_board_ui_escapes_attacker_controlled_fields`).

**Tests** (`tests/test_board.py`, 22): cache TTL (`test_team_snapshot_cache_reuses_value_within_ttl`,
`test_team_snapshot_cache_expires_after_ttl`, `test_serve_sse_uses_shared_team_snapshot_cache`,
`test_serve_team_reads_fresh_snapshot_without_cache`), proxy SSRF suite
(`test_proxy_rejects_non_github_targets`, `test_proxy_rejects_localhost_targets`,
`test_proxy_rejects_non_https_targets`, `test_proxy_rejects_metadata_targets`,
`test_proxy_rejects_redirect_to_disallowed_host`, `test_proxy_fetches_allowed_github_content`),
`test_api_team_create_builds_fullstack_commercial_shell`, collector-shape tests, plus the
design-law suite (see §2).

## 2. RGDS frontend & zero-hardcoding law

**Built**: vendored RGDS 1.1.0 at `clawteam/board/static/rgds/` (`tokens.css`,
`components.css`, `animations.css`, `interaction.css`, `form-factor.css`, `rgds-web.js`; sha-256
locked in `static/rgds/PROVENANCE.md` — hand-editing forbidden). Theme layer:
`design/theme.tokens.json` + `/api/theme`.

**Wiring**: `theme.tokens.json` carries **zero color values** — only RGDS provenance, the four
modes (`primary-light`, `secondary-light`, `primary-dark`, `secondary-dark`; legacy names map via
`legacyModeMap`), a `domain` block of board-specific sizes, and `strokeGradient` as a
`var(--md-*)` alias. The UI engine IIFE (index.html L830–941) fetches `/api/theme`, sets
`document.documentElement.dataset.theme/mode` (which drives `tokens.css`
`:root[data-theme=…]`), expands mode tokens + domain into CSS custom properties, persists to
`localStorage` (`rgds-theme` + legacy key), and falls back to `secondary-dark` with no server.
Rainbow is stroke-only over an opaque padding-box fill; a rAF pointer loop feeds the dynamic
stroke; `prefers-reduced-motion` is respected.

**Logic behind it**: the CSS-repair incident proved the law's value — a duplicated `.task-id {`
selector left a rule unclosed and CSS nesting swallowed every rule after it (kanban, tools,
modals, nav lost all styling); fixed by re-balancing braces (205/205) and tokenizing 22 spacing
declarations. The literal scan turns that class of bug into a test failure.

**Tests**: `test_board_ui_has_no_color_literals`, `test_board_ui_rainbow_is_stroke_only`,
`test_theme_tokens_json_is_rgds_domain_layer`, `test_rgds_assets_are_vendored_and_linked`,
`test_board_ui_escapes_attacker_controlled_fields`.

## 3. Tools & Models panels

**Built**: Board server routes + UI sections. Tools: `_mcp_add/_mcp_save/_expand_env`
(server.py L171–225); Models: OpenRouter client code L350–551 + `/api/openrouter/*`.

**Wiring/logic**: MCP entries are validated (name regex `[a-z0-9][a-z0-9-]{0,39}`; http-type
must be **https or loopback**), secrets referenced by env-var *name* and expanded at runtime
(`${VAR}`) — the UI never sees a value. Saves write **both** repo `.mcp.json` and worker
`.clawteam-local/claude-config/.claude.json`. Skills manager covers repo/worker/user scopes.
Models view: rankings (`/api/openrouter/rankings`), key health + spend, cache lab, and a routing
editor (`/api/openrouter/routing` apply — default model `z-ai/glm-5.3` on the
`openrouter-llm`/`LLM_API_KEY` profile, per D-012/D-013). Missing key ⇒ **dormant** state, a
first-class UI state rather than an error (D2 law).

**Tests**: exercised through the board route tests + `tests/test_presets.py`/`test_profiles.py`
(profile machinery) — no live OpenRouter calls in tests.

## 4. Media pipeline core

**Built**: `clawteam/media/jobs.py` (`MediaJobStore`), `assets.py` (`AssetStore`),
`router.py` (`MediaRouter`), `providers/base.py` (`MediaProvider` Protocol + `ProviderResult`).

**Wiring**: `serve()` starts `MediaRouter().start()` — a daemon worker (`_tick`, 1 s) that
dispatches by job state: `queued` → submit (or character/3D pipelines), `running` → poll,
`provider_succeeded|downloading` → download. Routing (`plan()` L61–100): local-first for
`LOCAL_SAFE_KINDS {t2img, img2img}` when ComfyUI is healthy; cloud for the rest; fal kinds
(`to3d|prep3d|rig3d`) go to fal; explicit `requested_provider` is honored only when the kind is
safe/covered. Storage: one JSON per job (`job-<epoch>-<uuid8>`) under `{data_dir}/media/jobs/`,
binary assets (`ast-<epoch>-<uuid8>`) + sidecars under `{data_dir}/media/assets/`; `_DirLock`
uses `msvcrt.locking`/`fcntl.flock`; all writes atomic.

**Logic (the laws)**:
- *Job states* (jobs.py L20–28): `draft → queued → running → provider_succeeded → downloading
  → succeeded`; terminal `failed | timed_out | succeeded_provider_download_failed`; kinds:
  `t2img img2img edit t2v i2v upscale vupscale character variant to3d prep3d rig3d`.
- *No double charge (E2)*: submit happens only on the `queued→running` transition, under
  `_cloud_lock` with `CLOUD_MIN_SUBMIT_SPACING = 5.0 s`; POSTs are never retried at the KIE
  client level; recovery re-polls the stored `provider_task_id`.
- *Backoff*: `POLL_FAST_INTERVAL=2.0` for 10 ticks, then ×1.5 growth capped at 30 s
  (`_advance` L341–379; schedule persisted in `_poll_count`/`_next_poll_at`).
- *Per-kind timeouts* (`KIND_TIMEOUT_SECONDS`, comfyui_local.py L29–30): checked against
  `submitted_at` → `timed_out`.
- *Download-before-complete (E3)*: on `provider_succeeded` → `downloading` → save assets →
  `succeeded`; zero downloads ⇒ `succeeded_provider_download_failed` (visible, never silent);
  partial downloads still `succeeded` with `error="partial download: …"`. After a restart with
  missing `_output_urls`, one re-poll recovers the URLs.
- *Retry* (`/api/media/jobs/<id>/retry`): only from `failed|timed_out|succeeded_provider_download_failed`;
  resets poll state; for `character` jobs keeps `status=="done"` stages and strips the failed
  tail (`_stages = done`).
- *Side-effect registration*: on download, `variant` jobs call `CharacterStore.add_variant`;
  `i2v` with `character_id` calls `add_scene` with a `source` label.
- The worker also sweeps expired uploads every `UPLOAD_SWEEP_INTERVAL = 900 s`.
- *Estimate-first (E4)*: `plan()` attaches `estimate()` to every job (`cost_estimate_credits/usd`,
  `pricing_table_version`); multi-stage presets show a summed estimate with a hard cap.

**Tests** (`tests/test_media.py` TestJobStore/TestRouter with `FakeLocal`/`FakeCloud` fakes):
`test_full_success_lifecycle_downloads_before_complete`, `test_no_duplicate_submit_after_failure`,
`test_download_failure_marks_special_state`, `test_backoff_schedule_is_not_fixed`,
`test_local_first_for_safe_kind`, `test_local_down_falls_back_to_cloud_for_t2img`,
`test_cloud_only_kind_routes_to_kie`, `test_all_down_reports_error`, `test_lifecycle_states_defined`,
`test_bad_kind_rejected`, `test_create_and_persist`, `test_list_roundtrip`.

## 5. Local GPU tier (ComfyUI bridge)

**Built**: `clawteam/media/providers/comfyui_local.py` (`ComfyUiLocalProvider`, name
`comfyui-local`). No dedicated routes — reached via routing (§4) and `/api/media/providers`.

**Wiring/logic**: health = reachable (socket probe `_listening()` or auto-boot) + checkpoint
present + kind-safe. `_ensure_booted()` (L56–83) runs **once per board session**: launches
`python_embeded\python.exe -s ComfyUI\main.py --listen 127.0.0.1 --port 8188` with
`CREATE_NO_WINDOW`, logs to `comfyui-bridge.log`, polls `/system_stats` up to 90 s. The workflow
(`_workflow` L110–129) is a code-built graph: `CheckpointLoaderSimple` (default
`RealVisXL_V5.0_fp16.safetensors`) → `EmptyLatentImage` (1024²) → `CLIPTextEncode` ×2 (prompt /
fixed negative) → `KSampler` (seed = `params.seed` or `os.urandom(4)`, 25 steps, cfg 5.5,
dpmpp_2m/karras) → `VAEDecode` → `SaveImage`. `submit` POSTs `/prompt`; `poll` reads
`/history/<id>` and collects output images as `/view?...` URLs; `download` fetches them (.png).
Costs: 0 credits, `pricing_table_version "local/1"`, `verified: True`. Local concurrency is
capped by `capabilities().limits.max_concurrent = 1` (single-flight).

**Tests**: router-level with `FakeLocal` (§4 routing tests). Live evidence: `docs/HANDOFF.md`
§2 — auto-boot, 1024² SDXL in ~16 s.

## 6. KIE cloud provider & model adapters

**Built**: `clawteam/media/providers/kie.py` (385 lines): `KieClient` (L42–115), pricing table
(L16–35), per-family adapters (L128–243), `KieProvider` (L251–385). Swarm-side default profile
`kie` in `clawteam/spawn/presets.py` (D-013).

**Wiring/logic**:
- Key from env *name* `KIE_API_KEY`; `credits()` = `GET /api/v1/chat/credit`;
  `create_task` = `POST /api/v1/jobs/createTask` → `data.taskId`; `record_info` =
  `GET /api/v1/jobs/recordInfo?taskId=`; download tries direct fetch, falls back to
  `POST /api/v1/common/download-url`. **GETs retry on 429/5xx (3 attempts); POSTs never retry**
  (credit safety).
- Pricing: `CREDIT_TO_USD = 0.005`; `PRICING_VERSION "kie-pricing-2026-10-25/4"`; verified
  actuals — flux1-kontext 5 cr, runway 12 cr (5 s/720p, 2026-09-23); Topaz image 10 cr,
  video 8 cr/s (estimates); MiniMax H3 per-second: 768P 8/s, 2K 13/s, default 6 s, prompt cap
  7000 chars.
- Adapters (E6 law — per-family schemas pinned from docs.kie.ai, never one universal payload):
  `FluxKontextAdapter` (t2img/img2img/edit/character/variant; sets `input_image` where needed),
  `RunwayAdapter` (t2v/i2v), `MiniMaxH3TextToVideoAdapter` (required `aspect_ratio`, `duration`
  4–15 s, `resolution`), `MiniMaxH3ImageToVideoAdapter` (`first_frame_url`),
  `TopazImageUpscaleAdapter` (`upscale_factor` "1"|"2"|"4" as string),
  `TopazVideoUpscaleAdapter` (`video_url`). Registry `ADAPTERS` + `default_model_for()`:
  t2v→`minimax-h3/text-to-video`, i2v→`minimax-h3/image-to-video`, upscale→`topaz/image-upscale`,
  vupscale→`topaz/video-upscale`, else `flux1-kontext`.
- `poll()` normalizes provider status (`waiting/queuing/generating→running`, `success→succeeded`,
  `fail→failed`; unknown stays running until timeout), reads **`creditsConsumed`** into
  `actual_credits/actual_usd`, and extracts output URLs from `response.resultUrls` **and**
  JSON-encoded `resultJson` (dedup, order-preserving — fixed a real poller bug).
- `health()` gates on key presence then a live credit probe (balance in the detail string);
  `estimate()` always returns `"verified": False` until a live task reports actuals (E6);
  `capabilities().limits = {max_concurrent: 1, min_submit_spacing_seconds: 5}`.

**Tests** (`tests/test_media.py` TestKieAdapters): `test_kontext_t2img_payload`,
`test_kontext_edit_uses_input_image`, `test_runway_t2v_needs_aspect`,
`test_runway_i2v_uses_image_url`, `test_minimax_h3_t2v_payload`,
`test_minimax_h3_i2v_uses_first_frame`, `test_minimax_h3_prompt_is_capped`,
`test_default_video_models_are_minimax_h3`, `test_minimax_h3_estimate_is_per_second`,
`test_unknown_model_rejected`, `test_status_normalization`,
`test_estimate_is_labeled_unverified`, `test_dormant_health`.

## 7. Characters — reusable identity studio

**Built**: `clawteam/media/characters.py` (`CharacterStore`; one JSON per
`chr-<epoch>-<uuid8>` under `{data_dir}/media/characters/`) + the canonical pipeline
`MediaRouter._run_character_pipeline` (router.py L199–310) + board routes.

**Wiring/logic**:
- Store: `new()` validates name (`[\w \-]{1,60}`) and `source_url` (must be `https://`);
  fields `canonical_asset_id`, `canonical_url`, `variants[] {asset_id,url,prompt,created_at}`,
  `scenes[] {asset_id,prompt,source,created_at}`; `add_variant`, `add_scene`, `attach_canonical`.
- Pipeline: guard https → create the character record once (`_character_id`) → state `running`
  → **mid-stage resume**: if the last `_stages` entry is `running` with a `task_id`, re-poll that
  provider task synchronously (no resubmit — mirrors the download-recovery law) → loop
  `CHARACTER_STAGES` = **sculpt** then **stylize**: each stage is a synthetic
  `kind:"edit", model:"flux1-kontext"` job (submitted under the cloud lock/spacing), tracked in
  `_stages` as `{name, status running|done, task_id, output_url, asset_id, credits}`; stage 2's
  input is stage 1's `output_url` (chained). Finalization: `attach_canonical(...)`, job
  `succeeded` with all stage assets in `output_asset_ids` and
  **`cost_actual_credits` = Σ per-stage actuals**.
- Variants: kind `variant`; the board route requires a character with a finished canonical and
  wraps the prompt ("Same character - keep the face, hair, and identity exactly consistent…
  Now: <user prompt>"); router feeds `canonical_url` as input; download registers via
  `add_variant`.
- Scenes: kind `i2v` with `params.character_id` (input falls back to canonical) or
  `params.variant_asset_id` (see §8); download registers via `add_scene` with
  `source: "variant" | "canonical"`.

**Tests**: `test_character_crud`, `test_character_name_validated`,
`test_kinds_include_character_variant`, `test_character_estimates`,
`test_variant_adapter_uses_input_image` (the adapter input-image law),
`test_character_pipeline_success` (2 stage assets, summed actuals = 10.0, canonical attached),
`test_character_requires_https`, `test_variant_job_registers_to_character`.

## 8. Self-hosted photo lane

**Built**: `clawteam/media/uploads.py` (`UploadStore`, 233 lines),
`clawteam/media/photohost.py` (`PhotoHost` + `python -m clawteam.media.photohost` CLI),
board routes, `scripts/windows/Start-PhotoTunnel.ps1`; config
`~/.clawteam/media/photohost.json` (`{public_origin, port, ttl_hours}`).

**Wiring/logic**:
- `UploadStore`: tokens `pho-<epoch>-<uuid4hex>` (`TOKEN_RE`); extension whitelist
  {.jpg,.jpeg,.png,.webp}; `MAX_UPLOAD_BYTES = 10 MB`; **magic-byte sniffing** (PNG `\x89PNG`,
  JPEG `\xff\xd8\xff`, WEBP `RIFF…WEBP`) so mislabeled content is rejected;
  `DEFAULT_TTL_HOURS = 24`; `get()` **fails closed on expiry**; `expired()` drives 410;
  `file_path` containment guard blocks traversal; `sweep()` deletes expired binary+sidecar
  (called by the media worker every 900 s); `public_url()` = `{public_origin}/{token}{ext}`
  (None when unconfigured — surfaced as an error, never a fake URL).
- `PhotoHost` (the **only publicly reachable process**, loopback :18790 behind the cloudflared
  `clawteam-photos` tunnel → `photos.miaknuckles.com`): GET/HEAD only, single path segment,
  ext whitelist, live token → 200 `Cache-Control: no-store` + `nosniff`; unknown → 404;
  expired → **410**. `serve()` starts it with the board.
- Board upload route: `POST /api/media/uploads?filename=` (raw body, cap/whitelist/sniff);
  `GET /api/media/uploads` list; `GET /api/media/uploads/<t>/file` local preview.
- **Animate-from-variant** (server.py L864–894): `i2v` with `params.variant_asset_id` → looks
  the variant up, reads the asset bytes, **re-hosts via `UploadStore().save(...,
  original_name="variant")`** for a fresh temp public URL (provider URLs expire), then sets
  `source_url` + `source:"variant"`. Scene thumbnails play inline on the character card from
  `/api/media/assets/<id>/file`.

**Tests** (`tests/test_photohost.py`, 24): `test_save_and_read_roundtrip`,
`test_content_must_match_extension`, `test_bad_extension_rejected`, `test_size_cap`,
`test_expired_link_fails_closed_and_sweeps`, `test_no_origin_configured_gives_no_public_url`,
`test_token_validation_blocks_traversal`, `test_serves_live_upload`,
`test_serves_webp_with_correct_mime`, `test_unknown_token_is_404`,
`test_expired_token_is_410`, `test_traversal_and_nested_paths_rejected`,
`test_non_image_extension_404`, `test_post_upload_saves_and_returns_public_url`,
`test_post_upload_rejects_non_image_name`, `test_post_upload_rejects_mislabeled_content`,
`test_post_upload_without_origin_reports_error`, `test_get_lists_live_uploads`,
`test_get_local_file_serves_bytes`, `test_post_i2v_variant_rehosts_through_photo_lane`,
`test_post_i2v_unknown_variant_rejected`, `test_i2v_scene_source_label_variant`,
`test_i2v_scene_source_label_canonical_default`, `test_worker_sweep_removes_expired`.

## 9. Easy Studio — one-click tiles (WP6/D-016)

**Built**: `clawteam/media/presets.py` — `BUILTIN_PRESETS` (6 tiles), `validate_presets()`
(`PresetError`), `load_presets()`, `preset_job_spec()`; route `GET /api/media/presets`;
UI `loadEasyStudio/renderEasyTiles/easyOpen/easyRun` (index.html).

**Wiring/logic**: each tile is declarative — `{id,title,blurb,example,kind,model,needs,defaults,
est_credits,one_click}`: `sharper-photo` (upscale, `topaz/image-upscale`, factor 2, 10 cr),
`sharper-video` (vupscale, `topaz/video-upscale`, 48 cr = 8/s × 6 s), `make-picture`
(t2img, flux1-kontext, 5 cr), `change-photo` (edit, 5 cr), `make-video` (t2v,
`minimax-h3/text-to-video`, 16:9/6 s/2K, 78 cr), `photo-to-video` (i2v,
`minimax-h3/image-to-video`, 78 cr). The validator enforces E6 at load time: unique ids; model
must exist in `kie.ADAPTERS`; preset kind ∈ adapter kinds; `needs` whitelist; title+blurb
required; `example` mandatory (D-018). A tile click produces a job spec with
`requested_provider:"kie"`, the pinned `model`, and merged defaults — the Create-tab expert
flow and the easy flow share the exact same job pipeline. The server honors the explicit model
on job create.

**Tests** (`tests/test_wp6.py`): `test_builtin_catalog_validates`,
`test_upscale_tiles_are_topaz`, `test_e6_rejects_unverified_model`,
`test_e6_rejects_kind_drift`, `test_rejects_duplicate_ids_and_missing_titles`,
`test_job_spec_shape`, `test_presets_route_serves_validated_catalog`,
`test_image_upscale_payload`, `test_image_upscale_factor_4`, `test_video_upscale_payload`,
`test_registered_and_defaulted`, `test_vupscale_is_a_job_kind_and_cloud_only`,
`test_topaz_estimate_uses_pricing`.

## 10. Buddy guide (D-018)

**Built**: entirely in `clawteam/board/static/index.html` (CSS L784–824, tokens-only) + the
validator rule in `presets.py` (`example` mandatory).

**Wiring/logic**:
- `buddyStepsFor(p)` derives the checklist from the preset's `needs` (image → "Add the photo…",
  video → "Paste your video link…", text → "Type what you want to see…", with
  upscale/edit-specific copy). `easyOpen` renders "What we need from you" + inputs.
- `buddyRefresh` recomputes done-ness live (photo: `body.dataset.uploadUrl` set by `easyUpload`
  after `POST /api/media/uploads`; video/text: input values), toggles ✓/○ marks, fills the
  "What you gave us" strip (uploaded photo thumbnail / truncated video chip), and **gates the
  button** — disabled while any `.buddy-step:not(.done)` with copy "One more thing — you can do
  it!" / "A couple more things — keep going!".
- `loadExamples/fillExamples` render "Here is what it can look like" from the first 3 image/video
  library assets (fallback: the preset's validator-mandated `example` sentence).
- `jobProgress(job)` maps job state (and `_3d` sub-stages) to `{pct, doing}` — 5 % "Getting
  ready…", 25 % "Waiting in line…", 60 % "Making it for you…", 90 % "Saving it to your
  library…", 3D: 40 % "Sculpting your 3D character from the photo…" → 60 % "Adding a movable
  skeleton…" → 80 % "Checking it looks like your photo…", 100 % "All done!…" / failure "We hit a
  snag — a grown-up can peek at the Jobs tab." `buddyTrack` polls
  `GET /api/media/jobs/<id>` every 3000 ms until terminal, updating the bar; transient fetch
  errors keep watching. The same machinery drives the 3D Studio tile (`#threed-progress`).

**Tests** (`tests/test_wp6.py::TestBuddyGuide`): `test_every_preset_has_example_text`,
`test_validator_rejects_missing_example`, `test_board_has_buddy_surfaces` (asserts the
`buddy-*` markers, `buddyTrack`, the three section headlines, and `threed-progress` exist).

## 11. 3D Studio — photo to rigged character (WP7/D-017)

**Built**: `clawteam/media/providers/fal.py` (`FalClient`, `FalProvider`, adapters:
`RembgAdapter`, `TripoImageTo3DAdapter`, `MeshyRiggingAdapter`; queue API
`https://queue.fal.run/{model}`, auth **`Authorization: Key <FAL_API_KEY>`** — Key prefix,
not Bearer, enforced and tested), `clawteam/media/openrouter_qa.py` (`vision_qa` on
`google/gemini-2.5-pro`), `clawteam/media/threed.py` (`ThreeDPipeline`); UI tab `#media-3d`.

**Wiring/logic**:
- Routing: kinds `to3d|prep3d|rig3d` are `CLOUD_ONLY_KINDS` and route to fal (unless
  `requested_provider == "kie"`, which fails cleanly — KIE has no 3D adapters).
- `ThreeDPipeline.run()` executes synchronously inside a worker tick for kind `to3d`, with its
  whole state machine persisted in the job field `_3d` (`{source_url, attempts, generate, rig,
  qa}`):
  1. guard https source + fal health → `running`;
  2. **generate** — `tripo3d/h3.1/image-to-3d` (detailed quality, PBR), `wait_sync`
     (2 s→×1.5→20 s backoff, 900 s cap) → parse `model_urls{glb,fbx,...}` + preview render →
     download GLB (`kind:"model3d"` asset) + preview (`kind:"image"`). On retry
     (`attempts > 0`) it switches to the fallback `fal-ai/hunyuan-3d/v3.1/pro/image-to-3d`.
  3. **rig** — `fal-ai/meshy/rigging` on the public GLB URL (walking clip, animation action 92);
     **failure is non-fatal**: records `provider_status="rig skipped: …"` and still delivers.
  4. **forensic QA** — `vision_qa(source_url, preview_url)` returns a strict-JSON verdict
     `{pass, issues, severity}` (fenced JSON tolerated); dormant/failure → None — **never
     blocks delivery**.
  5. **auto-heal** — failed verdict and attempts left (max 1 retry): clear `generate`, bump
     `attempts`, recurse → regeneration on the Hunyuan fallback.
  6. **attach** — create/reuse the CharacterStore record; the rig preview becomes the
     **canonical image**; job `succeeded` with `[model_asset_id, preview_asset_id,
     rigged_asset_id]`; `cost_actual_usd` from the fal estimate (fal bills USD, not credits).
- **Cinematic handoff**: no new movie code — the character lands in Characters and
  "Make My Photo Move" (KIE minimax-h3 i2v, §6/§7) animates it. **Lane honesty (E5)**: Lane A =
  stylized 3D-*looking* imagery (kontext pipeline — UI copy says "3D-look", never "3D model");
  Lane B = true meshes (this pipeline).

**Tests** (`tests/test_wp7.py`, 18; all HTTP faked): `test_submit_builds_key_auth_and_returns_ticket`,
`test_call_sends_key_prefix_not_bearer`, `test_submit_rejects_ticket_missing_fields`,
`test_tripo_payload_pinned_schema`, `test_tripo_parse_normalizes_model_urls`,
`test_meshy_rig_payload_pinned_schema`, `test_rembg_payload`,
`test_provider_dispatch_and_dormant_health`, `test_estimate_is_usd_and_unverified`,
`test_verdict_parse_and_request_shape`, `test_fenced_verdict_still_parses`,
`test_bad_verdict_raises`, `test_dormant_key_raises`,
`test_full_run_succeeds_and_attaches_character`, `test_generate_failure_fails_the_job`,
`test_rig_failure_still_delivers`, `test_https_source_is_enforced`,
`test_kinds_route_to_fal`.

## 12. Extract panel — local OCR/PDF

**Built**: `clawteam/board/ocr_tools.py` (346 lines) + `GET /api/ocr/tools` +
`POST /api/ocr/call` + Extract view UI.

**Wiring/logic**: bridges the local IureOCR MCP server (exe path hardcoded to
`I:\LocalApps\IureOCR\app\iureocr.exe`, override `CLAWTEAM_IUREOCR_EXE`, args `--mcp`,
per-call timeout `CLAWTEAM_OCR_TIMEOUT` default 600 s, `CREATE_NO_WINDOW`). Six tool specs
(`ocr_file`, `extract_text`, `pdf_info`, `render_page`, `edit_pdf_pages`, `ocr_languages`)
with typed args; `build_arguments()` coerces form values (unknown-arg rejection, required
checks, int/bool/enum whitelists — operations `{delete,keep,rotate,reorder}`, degrees
`{90,180,270}` — and `pages` comma-split to 1-based ints). The stdio JSON-RPC client
(`_McpStdioClient`) Popen's the exe, pumps stdout on a background thread with an **EOF
sentinel**, performs the `initialize` handshake (protocol `2024-11-05`), sends newline-delimited
requests with out-of-order line replay, and closes the child gracefully-then-kill. A module
`_LOCK` serializes calls (Tesseract is CPU-heavy). Results normalize to
`{text, images[data-uri]}`. Missing binary ⇒ clean `OcrBridgeError`, surfaced as a
server-status flag. No network, no key.

**Tests** (`tests/test_board_ocr.py`, 10): `test_tool_catalog_lists_exactly_the_six_hardcoded_tools`,
`test_build_arguments_coerces_forms`, parametrized `test_build_arguments_rejects_bad_input`,
`test_call_tool_against_fake_mcp_server` (spawns a fake MCP stdio server),
`test_call_tool_serializes_two_calls_over_one_client`,
`test_call_tool_surfaces_pipe_close_as_bridge_error`,
`test_call_tool_missing_binary_is_a_clean_bridge_error`,
`test_server_status_reflects_env_override`, `test_board_server_imports_the_ocr_bridge`,
`test_create_no_window_flag_zero_on_posix`.

## 13. Stage layer (WP2)

**Built**: `clawteam/stage/` (`manager.py` `StageManager`, `models.py`
`StageInfo/StagePromotion/StageRegistry/StageGCReport`, `__init__.py`
`get_stage_manager`), git plumbing `clawteam/workspace/git.py`, CLI `clawteam stage
create|promote|discard|list|gc` (commands.py L3812–3974). No HTTP surface.

**Wiring/logic**:
- Naming law: `ship/<run>/integration`, `.../lane/<role>`, `.../fork/<decision-id>/<option>`,
  `.../ab/<experiment-id>`; worktrees at `stage_root_for(run)` =
  `CLAWTEAM_STAGE_ROOT` else `D:\w`, path `<root>/<first-8-of-run>/<kind>/...` — short paths
  dodge Windows MAX_PATH, and `ensure_longpaths` sets `core.longpaths=true` per repo
  (idempotent).
- `_create_stage()`: enable longpaths → compute worktree path via `ensure_within_root` →
  crash recovery (stale worktree removed, stale branch deleted, best-effort) →
  `git worktree add -b <branch> <path> <base_ref>`. Lane/fork/ab base off integration
  (`_require_integration` auto-creates it). Registry atomically persisted at
  `<repo>/.clawteam-local/runs/<run>/stages.json`.
- `promote()`: **hard guard** — `approved_by` must equal `"judge"` (case-insensitive) else
  `StageError` and integration is untouched; checkpoints the source worktree
  (`commit_all "[stage] pre-promote checkpoint"`), merges **inside the integration worktree**
  (target branch never checked out elsewhere; conflict ⇒ abort, `(False, output)`, recorded);
  appends a `StagePromotion` audit row either way.
- `discard()` refuses integration; `gc()` drops registry entries whose branch **and** worktree
  are both gone. `clawteam ship` calls `integration_stage(run, team)` (non-fatal) and dumps the
  `StageInfo` into `run.json["stage"]`.

**Tests** (`tests/test_stage.py`, 13; all on a temp git repo with `CLAWTEAM_STAGE_ROOT`
sandboxed and `launch_team` stubbed — the swarm is never touched):
`test_stage_root_defaults_to_short_drive_and_run8`,
`test_integration_stage_creates_branch_worktree_and_longpaths`,
`test_lane_fork_ab_branch_naming`,
`test_promote_rejects_non_judge_and_leaves_integration_untouched`,
`test_promote_merges_judge_approved_lane_into_integration`,
`test_promote_unknown_branch_fails`, `test_discard_removes_worktree_and_branch`,
`test_discard_refuses_integration`, `test_gc_drops_dead_entries_and_keeps_live`,
`test_cli_create_requires_exactly_one_kind`, `test_cli_create_lane_list_discard_gc_roundtrip`,
`test_cli_promote_gates_non_judge`, `test_ship_creates_integration_stage_in_run_json`.

## 14. Autonomy engine (WP4)

**Built**: `clawteam/autonomy/` — `decide.py`, `blockers.py`, `forks.py`, `models.py`
(+ WP3's `governors.py`/`critics.py`/`stuck.py`); CLI `clawteam autonomy decide|blocker|
blockers|forks|governor|findings|stuck` (commands.py `autonomy_app` L3981+). There is no
scheduler process — the engine modules are invoked by the swarm's critic/judge/leader roles
per the template prompts, plus the CLI.

**Wiring/logic**:
- `decide()` (decide.py L68): inputs = question, options (≥1), optional benchmark rows
  (`"App=choice"` strings/tuples), `chosen` (**defaults to the first option** = decision-ladder
  rung 5: pick the simpler option, log it, move on), `confidence` clamped 0..1, `rationale`,
  `forked`. Output: a `DecisionRecord` (`id` = `D-nnn` from `next_decision_id()` scanning the
  decision log for the max id) appended as one JSON line to
  `<repo>/.clawteam-local/runs/<run>/decisions.jsonl`. `_mirror_decision_row()` renders a table
  row and **inserts it before the `## Anchor challenges` heading** in
  `docs/DECISION_LOG.md` (end-append if absent; silent if the file doesn't exist).
- Blocker Cards (blockers.py; `docs/AUTONOMY_POLICY.md` §3):
  `write_blocker(title, needed_from_owner, why_impossible, work_continuing, ship_default)`
  — title+needed+why are mandatory (the three Absolute-Blocker conditions as evidence); ids
  `B-nnn` from `blockers/index.json`; card markdown from `_CARD_TEMPLATE` at
  `blockers/B-nnn.md` with the ship-default ("feature ships disabled/dormant") and
  work-continuing ("all other lanes — swarm never pauses") fields.
  `pending_notification(min_age_minutes=15)` batches never-notified / ≥15-min-old cards;
  `mark_notified()` stamps. **Notify-and-continue only — the swarm never pauses.**
- Fork controller (forks.py): `ForkController(stage_manager, governor=None)`; ledger at
  `runs/<run>/forks.json`. `create_fork_pair()` guard order: options differ →
  `governor.check_fork()` (§15 — wrap-up/soft-stop blocks new forks) → no nested forks
  (same decision still open) → cap `MAX_OPEN_FORKS = 3` → budget share
  (`fork_budget/budget_total ≤ MAX_BUDGET_FRACTION = 0.4`); then **both** options become real
  stage fork branches via `StageManager.create_fork`. `close_fork(decision_id, winner)`: winner
  must be an option; the loser's stage is discarded (best-effort); ledger records the winner —
  the ledger verdict is the source of truth.

**Tests** (`tests/test_autonomy.py`, 19): `test_record_shape_and_jsonl`,
`test_chosen_must_be_an_option`, `test_mirror_row_in_decision_log_with_next_id`,
`test_missing_log_is_silent`, `test_card_written_in_section3_format`,
`test_index_ids_sequence_and_listing`, `test_card_requires_evidence_fields`,
`test_batched_notification_state`, `test_create_pair_makes_both_branches`,
`test_two_options_exactly`, `test_cap_three_open_forks`, `test_no_nested_forks`,
`test_budget_share_cap`, `test_close_records_winner_and_discards_loser`,
`test_close_rejects_unknown_winner`, `test_decide_cli_roundtrip`,
`test_blocker_cli_and_list`, `test_forks_cli_create_close_list`,
`test_forks_cap_error_surfaces`.

## 15. Critic loop, budget governors, stuck detection (WP3)

**Built**: `clawteam/autonomy/critics.py` (`CriticLoop`), `governors.py` (`Governor`),
`stuck.py` (`scan_stalled`); state under `runs/<run>/`: `critic-state.json`,
`governor.json`, `stuck.json`; CLI `clawteam autonomy findings|governor|stuck`.

**Wiring/logic**:
- **Critic loop**: triggers = timer (`CRITIC_INTERVAL_SECONDS = 300`, due immediately if never
  scanned) **or** lane commits since the last scan (`git log --since=<last_scan>
  --branches=ship/<run>/lane/*`). `record_finding(lane, severity, message, evidence)` —
  evidence mandatory ("looks wrong is rejected by the Judge"); severity low|medium|high;
  fingerprint = sha256(lane+message+evidence)[:16]; a repeat within
  `FINDING_COOLDOWN_SECONDS = 1800` **merges** (count+1, ts refreshed) instead of duplicating;
  ids `CF-nnn`. Judge `triage(min_severity="medium")`: ≥ medium → `status="triaged",
  owner="debug"`; lower → `status="dismissed"` (kept, never deleted).
- **Governors**: `KINDS = (wall_clock_hours, llm_tokens, kie_credits, concurrent_agents,
  open_experiments)`. `PRO_DEFAULTS` = 6 h wall-clock, 8 concurrent, 4 open experiments
  (tokens/credits uncapped until the owner sets them); `SIMPLE_DEFAULTS` = 45/60 h, 5, 1.
  `record(kind, amount)` sums flow kinds; `set_used` sets gauge kinds. Verdicts:
  `should_soft_stop()` at ≥ `SOFT_STOP_FRACTION = 0.8` of any cap (stop starting
  forks/experiments); `should_wrap_up()` at ≥ 1.0 (graceful wrap-up — finish integrating green
  work, write the SHIP_REPORT, never abort mid-write); `check_fork()` raises for
  ForkController. Uncapped kinds never trip.
- **Stuck detection**: tasks `pending|in_progress` whose `updated_at` is ≥
  `STALLED_AFTER_MINUTES = 20` old (unparseable timestamps count as stalled); decision table:
  `in_progress` → **respawn**, `pending` → **reassign**; report persisted to `stuck.json` with
  a `prompt` map for the leader watcher (which owns actual execution — `LeaderWatcher` +
  keepalive resume prompts; detection only *names* the action).

**Tests** (`tests/test_wp3.py`, 17): `test_pro_and_simple_defaults`,
`test_record_and_soft_stop_then_wrap_up`, `test_uncapped_kinds_never_trip`,
`test_gauge_kinds_are_set_not_summed`, `test_governor_gates_fork_controller`,
`test_timer_trigger_default_5min`, `test_commit_trigger_sees_lane_commits`,
`test_finding_requires_evidence`, `test_fingerprint_dedupe_within_cooldown`,
`test_judge_triage_routes_medium_plus_to_debug`, `test_fingerprint_is_stable`,
`test_stalled_in_progress_prompts_respawn`,
`test_fresh_pending_is_not_stalled_old_pending_reassigns`,
`test_completed_and_blocked_are_never_stuck`, `test_governor_cli_record_and_verdicts`,
`test_findings_cli_file_and_triage`, `test_stuck_cli`.

## 16. Keep It Simple mode & Parent Gate (WP5)

**Built**: `clawteam/kis/state.py` (the only module; `kis_path()` = `~/.clawteam/kis.json` —
a **fixed root**, deliberately not `CLAWTEAM_DATA_DIR`-derived, mirroring `config.json`);
Board routes `GET/POST /api/kis/mode`, `GET /api/kis/policy`,
`POST /api/kis/parent-gate/set|verify` (KEEP_IT_SIMPLE_SPEC §11). No CLI.

**Wiring/logic**: state shape `{enabled, caps, pin_hash, pin_salt, lockout_until,
failed_attempts}`, atomic writes. **PIN**: `set_pin()` requires ≥4 chars; stored as
`hashlib.scrypt` (n=2^15, r=8, p=1, random 16-byte salt) hex — never plaintext, never logged;
all returned dicts strip PIN material. `verify_pin()`: unconfigured gate refuses; lockout
(`lockout_until` epoch in the future, message with remaining minutes) after
`MAX_FAILED_ATTEMPTS = 5` wrong attempts, `LOCKOUT_SECONDS = 300`, counter reset on lockout or
success; comparison via `hmac.compare_digest`. `gate(action, pin)`: action must be in
`GATED_ACTIONS` = {`disable_keep_it_simple`, `change_caps`, `publish_external`,
`approve_person_photo`, `approve_voice_clone`, `raise_credit_cap`, `delete_project`} — these
gate actions **are** the consent-attestation mechanism (guardian consents, not agent questions
— D-005/F5). Mode: `set_enabled(True)` free; `set_enabled(False)` requires the gate **only once
a PIN exists** (first enable defines the gate). Caps defaults: credits_per_run 40,
credits_per_day_per_profile 150, movie_preset_total 120, movie_gate_approval_above 60,
wall_clock_minutes_per_run 45, concurrent_jobs 2; `set_caps` is gated; unknown keys ignored.
`policy()` serves a clean snapshot `{enabled, gate_configured, locked_out, caps,
gated_actions}`.

**Tests** (`tests/test_wp5.py`, 15): `test_pin_stored_hashed_never_plaintext`,
`test_verify_roundtrip`, `test_unconfigured_gate_refuses`, `test_five_wrong_pins_lock_out`,
`test_gate_actions_cover_spec`, `test_gate_approves_with_pin_rejects_without`,
`test_default_off_and_on_freely`, `test_off_requires_gate`,
`test_off_without_pin_is_free_when_gate_unset`, `test_defaults_match_spec`,
`test_cap_changes_require_gate`, `test_policy_shape_and_no_secret_material`,
`test_mode_route_roundtrip`, `test_parent_gate_routes`, `test_policy_route_clean`.

## 17. One-shot ship & the fullstack-commercial team (WP1/D-014)

**Built**: `clawteam ship` (commands.py L4697) delegating to `launch_team` (L4509); template
`clawteam/templates/fullstack-commercial.toml` (203 lines, 19 roles, 5 seed tasks); Board
`POST /api/team/create`; objective of record `docs/GOAL_MODE_PROMPT.md`.

**Wiring/logic** (`clawteam ship "<prompt>" --mode pro|simple`):
1. validate mode ∈ {pro, simple} (exit 1 otherwise); 2. resolve profile (`--profile` or
`default_profile`); 3. mint `run_id = ship-<uuid4[:8]>`, create `runs/<run>/`; 4. team name
defaults to the run id; 5. `StageManager.integration_stage(run, team)` (non-fatal on failure);
6. write `run.json` (`{run_id, prompt, mode, budget, no_fork, team, template:
"fullstack-commercial", created_at, stage?}`); 7. `launch_team` loads the template, creates the
team via `TeamManager.create_team` + `add_member` per agent (leader `plan` first), creates the
5 seed tasks, resolves the spawn backend (`clawteam.spawn.get_backend` — subprocess, hidden),
applies the runtime profile, renders each role prompt (`{team_name}`/`{goal}` placeholders,
`build_agent_prompt` adds identity/workspace/task/context/coordination/worker-loop sections),
and spawns each agent with keepalive (`plan` as leader). Agents run detached; the command exits 0
after spawning.

**Template design**: leader `plan` (only agent allowed to rewrite the swarm blueprint) +
architect, agent, be-dev, fe-dev, qa, debug, ask, security, devops, archive, prompt-engineer,
critic-code, critic-design, critic-product (read-only evaluators), explorer-a, explorer-b
(fork-cap-aware A/B), judge (read-only except promotion; auto-picks fork winners in Simple
mode), integrator (performs only Judge-approved promotions). Phases: INTAKE → RESEARCH → PLAN
→ BUILD (parallel with CRITIQUE/EXPLORE) → HARDEN → SHIP → IDLE. Every prompt carries:
swarm-blueprint discipline, "never exit after one task — polling IS the job", env-var-names-only
secrets, RGDS tokens only, the no-questions law, governor awareness. The base 6-lane
`templates/agentic-se.toml` is untouched (D-007/F1).

**Tests**: `tests/test_spawn_cli.py::test_ship_cli_creates_team_and_run_record`,
`test_ship_cli_rejects_invalid_mode`; `tests/test_templates.py::TestFullstackCommercial`
(`test_load`, `test_roster_matches_swarm_team_spec` (19-role roster), `test_agents_have_tasks`,
`test_task_owners_match_agents`, `test_task_substitution_keeps_placeholders`,
`test_no_stale_memory_wiring_and_no_secret_literals`,
`test_archive_lane_points_at_agentcore_gateway`); board side:
`test_api_team_create_builds_fullstack_commercial_shell`; stage wiring:
`test_ship_creates_integration_stage_in_run_json`.

## 18. Windows operations scripts

**Built**: `scripts/windows/` — all native PowerShell, no Docker/WSL.

**Wiring/logic**: `Start-Board.ps1` — starts `clawteam board serve` hidden on **8788** (8080 is
commonly taken), writes a generated runner to `.clawteam-local/runs/board.ps1`, logs to
`.clawteam-local/logs/board.log`, opens the browser (`-NoBrowser` to skip; `-External` would bind
0.0.0.0 — never used, H5). `Start-PhotoTunnel.ps1` — idempotent `cloudflared tunnel run
clawteam-photos` → loopback :18790 (silent no-op if config/exe missing or a live pid file
exists). `Start-Swarm.ps1` — hidden supervisor (`CreateNoWindow`) running
`clawteam launch`, goal passed via env `CLAWTEAM_GOAL` (quoting-hazard avoidance), heartbeat
loop, exits on a `<team>.stop` file; also starts the board. `Stop-Swarm.ps1` — stop file,
kill spawn-registry PIDs + survivors referencing the team, optional
`clawteam team cleanup --force`. `Open-Board-Desktop.ps1` — TCP-probes the board, starts it if
down (15 s wait), opens an Edge/Chrome **app-mode** window (own taskbar entry); avoids CIM/WMI
(broken WMI repo on this machine). `Invoke-Hidden.ps1` — `Start-HiddenScript` helper
(no console flash).

**Tests**: no dedicated suite (operator scripts); behavior verified live and recorded in
`docs/OPERATIONS_ADDENDUM.md` + `CHANGELOG.md` (e.g. CIM fallback for `Get-NetIPAddress`).

## 19. Commercialization contracts (WP9–11 — designed, not yet built)

**Built (contract-only)**: no code exists (verified by grep across `clawteam/`, `scripts/`,
`pyproject.toml`, `package.json` — no stripe/pyinstaller/license routes). Contracts live in
`docs/BUILD_PLAN.md` §3b, anchors A8/A9/B7a/D7/D8, decision D-014, requirements R5–R7 in
`docs/GOAL_MODE_PROMPT.md`.

**The contracts**: **WP9** — every provider/API key lives only on the owner's PC (User env /
server config); the shipped exe is a *remote client* through an authenticated tunnel
(cloudflared/Tailscale) to the same loopback-bound server (never a `0.0.0.0` bind); the exe
carries zero key material, **provable by a strings scan at build time**; key rotation is
admin-auth-only and local. **WP10** — Stripe **$1/month** subscription; `STRIPE_API_KEY`
env-only; webhook handles `checkout.session.completed` and
`customer.subscription.updated|deleted`; server tracks `active|past_due|canceled` with monthly
expiry; the client checks on start + periodically; unlicensed ⇒ paywall → Stripe Checkout.
**WP11** — `build-exe.ps1` (to be written), PyInstaller onedir, RGDS + templates bundled,
clean-profile smoke run, build hash recorded in the SHIP_REPORT.

**Proof when built**: E6 law applies — Stripe/fal/KIE schemas verified at build time; the
gates in `docs/TESTING_AND_ACCEPTANCE.md` (G-TEST, G-SECRET with the D7 strings scan,
G-BIND, G-ANCHOR) must be green on the integration branch.

---

## Cross-cutting engineering law (why everything is shaped this way)

- **Anchors** (`ANCHOR_POINTS.md`): Windows-native, subprocess backend, git worktrees,
  loopback-only (photo host is the sole public exception), stdlib board, stable state roots,
  reserved ports (8788 board, 18790 photo, 18800–18899 new services).
- **Secrets**: env-var *names* only in every file; expansion at runtime; dormant-not-crash.
- **Design**: RGDS tokens only; the literal scan is a build gate, not a style preference.
- **Media**: app-owned job states; estimate-first; no double charge; download-before-complete;
  lane honesty (Lane A stylized vs Lane B true meshes); per-model adapters from verified docs.
- **Autonomy**: no questions except Absolute Blockers (with evidence, batched, never pausing);
  every decision logged; forks when the benchmark can't decide; budgets always on; evidence
  or it didn't happen.
- **Tests**: baseline may only grow (G1: 685 collected 2026-10-27, ~744 functions at HEAD);
  nothing ships while pytest, the RGDS literal scan, or the secret scan is red.
