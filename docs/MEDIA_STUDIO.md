# Multimedia Studio — User & Product Guide

The Media panel in the ClawTeam board is a professional media studio: image and
video generation, a reusable-character workflow, an asset library, and full job
history — with local/cloud routing and cost visibility before every submit.

Design: same RGDS system as the whole app (all four themes). Provider details
never appear in the UI; you see routes ("Local GPU" / "Cloud") and friendly
labels, never raw API schemas.

## Tabs

### Create
Pick a goal — Image, Image→Image, Edit, Video, Animate, Enhance — write a
prompt, optionally attach/point to a source, pick aspect/quality, and the
**estimate line** shows route + cost before you generate. Drafts route
Local GPU when safe; premium/video/edit go cloud.

### Library
Every output lands here permanently (downloaded from the provider before the
job is marked done — nothing expires on you). Filter image/video, reuse any
asset as an input (`↺`), download (`↓`).

### Jobs
Full lifecycle per job: state, route, model, prompt, estimate → actual cost,
timestamps, errors, and one-click **Retry** for recoverable failures.

### Characters
The reusable-identity workflow (see below).

## Character workflow (reusable animated-film characters)

Built for the goal: *photos of a person → a stylized character → consistent
images → scenes → movies* — while being honest that this is **stylized
3D-looking imagery (Lane A), not true 3D models (Lane B, future provider)**.

1. **Create Character** — upload a photo from disk (or paste any public
   https photo link) + name. Two identity-preserving passes run
   automatically: *sculpt* (3D animated-film render) → *stylize* (big-studio
   movie character). ~10 credits. The finished canonical image anchors the
   character.
2. **New look…** — describe pose, clothing, expression, place, or camera
   angle. Every variant is generated from the canonical with an enforced
   "same character, keep identity exactly consistent" wrapper. ~5 credits.
3. **Animate** — describe the shot; the canonical (or a variant) becomes a
   5-second 720p scene registered to the character. ~12 credits.

Variants and scenes stack on the character card; every asset is in the
Library for reuse. A multi-shot "movie" = several scenes from one character —
identity is maintained because every generation references the same canonical.

**Photo input (self-hosted, operator decision 2026-09-26)**: the Characters
tab uploads a personal photo through the board (`POST /api/media/uploads`)
into `~/.clawteam/media/uploads/` under an unguessable token, and serves it
as a **temporary public https link on the operator's own domain**
(`https://photos.miaknuckles.com/<token>.<ext>` via a dedicated cloudflared
tunnel → loopback photo host on 18790). Links auto-expire after 24 h —
expired reads return 410 and a sweep (every 15 min inside the media worker)
deletes the files. The photo host serves *only* token-named image files;
the board API and every other service stay loopback-only. Photos transit the
operator's own Cloudflare edge, never a third-party upload host. Verified
E2E live: upload → public fetch (byte-identical through the edge) → KIE
character creation (10 credits).

## Routing & cost model

| Lane | Provider | Used for | Verified actual cost |
|---|---|---|---|
| Local GPU | ComfyUI + RTX 4070 SUPER | safe image generation, drafts | free |
| Cloud image | KIE `flux1-kontext` | t2img / edit / variants | 5 credits |
| Cloud video | KIE `runway` | t2v / i2v (5 s, 720p/1080p) | 12 credits |

Estimates show before submit; **actuals come from the provider** and are
stored per job. Failed provider generations are auto-refunded upstream;
recoveries re-poll existing tasks instead of resubmitting, so you never pay
twice for one result.

## For engineers

Implementation, lifecycle states, adapter law, and resume semantics:
[`ARCHITECTURE.md`](ARCHITECTURE.md) §3 and the `clawteam/media/` package.
