# MEDIA_PRESETS_CATALOG — Top 20 Developer + Top 20 Consumer One-Shot Presets

Extends `docs/MEDIA_STUDIO.md`. Anchors: A5, A6, D4, D5, E1–E6.

> **How "top 20" was chosen**: ranked by (1) how often the use case appears in leading image/video/AI-creator products
> (e.g., Canva, Figma, Midjourney, Runway, Pika, Luma, CapCut, Kling, HeyGen, ElevenLabs, Suno) and developer workflows
> (app stores, docs sites, marketing pages, game dev), and (2) feasibility on kie.ai + local FFmpeg/ComfyUI. This is a
> reasoned editorial ranking, **not** measured usage data — the agent should re-check it with the Benchmark Rule and may
> reorder or swap entries (log it). Model names below are **capability slots**; resolve each to a concrete KIE model at build time
> by reading `docs.kie.ai` (anchor E6). Costs are placeholders until a live task reports `creditsConsumed`.

## 1. Preset schema (declarative; JSON or TOML under `clawteam/media/presets/`)

```json
{
  "id": "consumer.pixar-clone",
  "catalog": "consumer",
  "rank": 1,
  "title": "Pixar-style 3D Clone",
  "tagline": "Turn a photo into your own animated-movie character",
  "inputs": [{"name":"photo","type":"image","required":true,"consent":"likeness"},
             {"name":"name","type":"text","required":true}],
  "stages": [
    {"id":"canonical","kind":"i2i","provider_pref":"kie","family":"image-edit","params":{"style":"3d-animated-film"},"est_credits":10},
    {"id":"turnaround","kind":"i2i","needs":["canonical"],"family":"image-edit","params":{"views":["front","side","back"]},"est_credits":15}
  ],
  "caps": {"max_credits": 40, "max_seconds": 900},
  "simple": {"visible": true, "title": "Make me a cartoon!", "hide_params": ["views","style"],
             "defaults": {"quality":"standard"}, "parent_gate": ["likeness"], "max_credits": 25},
  "lane": "A",
  "labels": {"honest_3d": "3D-style"},
  "outputs": ["image"]
}
```
Validator rules: unique ids · every `needs` resolves · est sum ≤ caps · `consent` tags map to Parent Gate/attestation · Lane A presets
never use the word "model" for outputs · every preset has a `simple` block (visible or `visible:false` with reason).

## 2. Universal preset contract

1. Shows route + **total** estimate before starting (E4). 2. One submit per stage; resumable (E2). 3. Downloads before success (E3).
4. Saves a `pipeline` record linking stage job ids. 5. Surfaces partial results as they finish. 6. Lane honesty label (E5).
7. Likeness/voice stages require consent attestation (D5). 8. Cancel stops further stages; completed stages are kept.

## 3. Developer catalog — Top 20

Audience: professional developers/product teams. Simple toggle exposes ≤ 8 safe tiles (marked ★) with defaults.

| # | ID | Preset | Pipeline (stages) | Output | ★KIS |
|---|---|---|---|---|---|
| 1 | `dev.app-icon-set` | App icon + adaptive icon set | t2i (concept ×4) → select → i2i variants → local resize/export (Android adaptive, iOS, web favicon) | PNG set + manifest | ★ |
| 2 | `dev.hero-image` | Landing-page hero image | t2i (hero) → upscale → local WebP/AVIF export | image set | ★ |
| 3 | `dev.ui-mockup` | UI screen mockup from description | t2i (screen concept, RGDS-neutral palette prompt) → upscale | image | |
| 4 | `dev.product-demo-video` | 15–30 s product demo clip | script → storyboard stills → i2v shots → music → local stitch | MP4 | ★ |
| 5 | `dev.explainer-video` | Feature explainer video | script → narration (TTS) → b-roll i2v → captions (local) → stitch | MP4 | |
| 6 | `dev.screenshot-beautifier` | Store/marketing screenshots | upload shots → device-frame/background t2i → composite (local) | image set | ★ |
| 7 | `dev.og-social-cards` | OG/Twitter/LinkedIn cards | t2i background → local text overlay (templated) → export sizes | PNG set | ★ |
| 8 | `dev.app-store-assets` | App Store/Play listing pack | icon + 5 screenshots frames + feature graphic + promo video | asset pack | |
| 9 | `dev.docs-diagrams` | Doc illustrations/diagrams | t2i (clean vector-look) → upscale | image set | |
| 10 | `dev.game-sprites` | 2D sprite sheet | t2i character → i2i poses/walk-cycle frames → local sheet pack | sprite sheet + JSON atlas | ★ |
| 11 | `dev.game-tiles-bg` | Tileset + parallax backgrounds | t2i tiles/bg layers → seamless pass (local) → atlas | tiles + layers | |
| 12 | `dev.game-trailer` | Game trailer | key art → i2v shots → music/sfx → stitch | MP4 | |
| 13 | `dev.brand-kit` | Logo + brand explorations | t2i logo concepts → pick → variants (mono/inverse) → palette suggestion mapped to RGDS slots | image set + palette JSON | ★ |
| 14 | `dev.3d-style-mascot` | 3D-style mascot with turnaround | t2i/i2i mascot → turnaround views → expression sheet | image set (Lane A) | ★ |
| 15 | `dev.motion-loop` | Looping UI/hero animation | t2i frame → i2v loop → local loop-trim/optimize to MP4/WebM/GIF | video | |
| 16 | `dev.screen-recording-polish` | Demo recording enhancer | upload clip → local FFmpeg stabilize/crop/zoom/caption → optional upscale | MP4 | |
| 17 | `dev.avatar-presenter` | AI presenter for tutorials | script → TTS → avatar/lip-sync video → stitch | MP4 | |
| 18 | `dev.test-fixtures` | Synthetic image/video fixtures for tests | t2i batch with seeds → manifest | fixtures + JSON | |
| 19 | `dev.changelog-video` | Release-notes video | changelog text → scenes → TTS → stitch | MP4 | |
| 20 | `dev.pitch-deck-visuals` | Investor/pitch visuals | t2i slides art → consistent style via reference → export | image set | |

Honesty: `#14` is Lane A — copy must say "3D-style".

## 4. Consumer catalog — Top 20

Audience: families, creators, kids (via Simple mode). ★ = shown in Simple mode's "Top 8 for you".

| # | ID | Preset | Pipeline (stages) | Output | Consent | ★KIS |
|---|---|---|---|---|---|---|
| 1 | `consumer.pixar-clone` | **Pixar-style 3D clone** (photo → character) | i2i canonical (3D-animated-film look) → turnaround/expressions | image set (Lane A) | likeness | ★ |
| 2 | `consumer.3d-character-clone` | **3D character clone** (realistic-stylized, game-ready look) | i2i stylize → turnaround → expression sheet | image set (Lane A; say "3D-style") | likeness | ★ |
| 3 | `consumer.clone-scene` | Put my clone in a scene | clone canonical + scene prompt → i2i → optional i2v 5 s | image/video | likeness | ★ |
| 4 | `consumer.voice-clone` | **Voice clone** speak-anything | consent attestation → voice sample → voice-clone adapter → TTS test lines | audio | **voice** | ★ |
| 5 | `consumer.talking-clone` | Make my clone talk | clone image + text → TTS (cloned voice) → lip-sync/avatar video | video | likeness+voice | ★ |
| 6 | `consumer.movie-from-clone` | **Full movie from my clones** | idea → script → character cast (clone canonicals) → storyboard → per-scene i2v shots → voice per character → music → local stitch + titles | MP4 (multi-minute, scene-capped) | likeness+voice | ★ |
| 7 | `consumer.animated-short` | 30–60 s animated short | idea → script → storyboard → i2v shots → narration → music → stitch | MP4 | — | ★ |
| 8 | `consumer.storybook` | Illustrated storybook | story → 8–12 consistent illustrations → layout (local) → PDF/video read-aloud | PDF/MP4 | — | |
| 9 | `consumer.pet-cartoon` | Pet → cartoon star | pet photo → i2i toon/3D-style → scene video | image/video | — | ★ |
| 10 | `consumer.family-cartoon` | Family portrait → animated-movie poster | multi-photo → i2i unify style → poster layout | image | likeness | |
| 11 | `consumer.sticker-pack` | Sticker/emoji pack | clone or prompt → 8 expressions → background removal → export | PNG set | likeness (opt.) | |
| 12 | `consumer.photo-restore` | Restore/colorize old photos | upload → upscale/restore → colorize | image | likeness | |
| 13 | `consumer.avatar-pfp` | Profile avatars in styles | photo → N style variants | image set | likeness | |
| 14 | `consumer.music-video` | Song → music video | music gen (or upload) → shot list → i2v shots → beat-synced stitch | MP4 | — | |
| 15 | `consumer.song-maker` | Make a song | lyrics/prompt → music gen → cover art | audio+image | — | ★ |
| 16 | `consumer.birthday-card` | Animated greeting card | text + photo/clone → scene → voice message → short video | MP4 | likeness (opt.) | |
| 17 | `consumer.comic-strip` | Comic strip / manga page | story → panels (consistent character) → bubbles (local) → page | image/PDF | — | |
| 18 | `consumer.game-character-sheet` | Game character + backstory | prompt → character art → stats/backstory text → card | image | — | |
| 19 | `consumer.wallpaper-pack` | Wallpapers / phone themes | prompt → t2i set → upscale → exports | image set | — | |
| 20 | `consumer.sports-highlight` | My-moment highlight reel | clips/photos → local FFmpeg edit → music → titles | MP4 | likeness | |

Flagship chain (the requested path): **#1/#2 clone → #4 voice → #5 talking clone → #6 full movie.** The movie preset must support casting
several saved characters, a per-character voice, and scene-by-scene resumability so a 20-minute build can survive a restart.
Movie length defaults: Simple ≤ 2 min; Pro ≤ 10 min (configurable; cost-gated).

## 5. Simple variants — rules

- ≤ 8 tiles in the "Top 8 for you" grid; big cards, one-sentence titles ("Make me a cartoon!").
- All parameters preset; only the creative input(s) are asked.
- Cost shown as "energy"; caps from `KEEP_IT_SIMPLE_SPEC.md` §8; over-cap → Parent Gate.
- Consent/likeness/voice presets route through the Parent Gate before stage 1.
- Safety filters (policy §7) run on every text input.

## 6. Capability registry (agent builds; maps slots → adapters)

| Capability slot | Needed by | Provider preference | Notes |
|---|---|---|---|
| `t2i`, `i2i`/edit | most | KIE (Flux Kontext exists) or local ComfyUI for drafts | exists today |
| `i2v`, `t2v` | video presets | KIE (Runway exists; add others if verified) | exists today |
| `upscale` | many | local RealESRGAN (installed) or KIE upscale | HANDOFF §4 lists options; decide via Benchmark Rule |
| `tts` / `voice-clone` | voice, movie, presenter | KIE audio family (**verify exists**) | else mark preset dormant, never fake |
| `lipsync` / `avatar` | talking clone, presenter | KIE (**verify**) | else dormant |
| `music` | song, music video, trailers | KIE (**verify**) | else dormant |
| `bg-remove`, `layout`, `stitch`, `captions`, `export` | many | **local** (FFmpeg/PIL if allowed, else FFmpeg-only) | no provider cost |

If a slot has no verified adapter, presets depending on it are shown as **"Coming soon (needs <slot>)"** — never faked. This is a
documented dormant state (anchor D2), not a blocker.

## 7. One-shot prompt box behavior

1. User types free text ("make my dog a Pixar star and a 20-second movie").
2. `intent.py` maps to one preset or a composed pipeline (rule-based keywords first; LLM fallback via OpenRouter profile).
3. UI shows: chosen preset(s), inputs still needed (upload slot), **total estimate**, caps, consent steps.
4. One tap runs the whole pipeline; results stream into Library as stages finish.
5. In Simple mode the same, with friendly copy and Gate prompts only where required.

## 8. Tests for presets (minimum)

Schema validation of all 40 · each preset's stage graph resolves · estimate ≤ cap · mocked-provider run of one preset per catalog
end-to-end · resume after simulated restart (no duplicate submit) · cap breach pauses · Simple variants hide forbidden params ·
consent gates enforced · no color literals in the UI that renders them.
