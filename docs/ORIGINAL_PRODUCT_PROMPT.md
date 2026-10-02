# ORIGINAL_PRODUCT_PROMPT — Verbatim Owner Product Intent (SSOT)

> **This file wins over paraphrases.** Every other doc in this pack (`PRODUCT_SPEC.md`,
> `BUILD_PLAN.md`, `SWARM_TEAM_SPEC.md`, `KEEP_IT_SIMPLE_SPEC.md`, `MEDIA_PRESETS_CATALOG.md`,
> the `*_ADDENDUM.md` files, `ONE_SHOT_BOOTSTRAP_PROMPT.md`) is a derived elaboration of the
> intent captured here. `ANCHOR_POINTS.md` encodes the immutable laws *derived from* this
> prompt — if a derived doc and this file ever disagree, this file is correct and the derived
> doc is the one that needs fixing (log the fix as a `DECISION_LOG.md` row).
>
> Recorded 2026-10-02 from the owner's (Tony / `ynotfins`) product request, transcribed
> verbatim (not summarized, not softened) below.

## Owner's product intent (verbatim)

> Fully autonomous runtime: one prompt → ship; frictionless git worktree stage/exec layer;
> continuous critics + A/B explorers + Judge; fork-both-ways when options diverge; no
> questions except Absolute Blockers (Top-Apps Benchmark otherwise); Keep It Simple toggle on
> Board + both media catalogs for ages 11/14 with RGDS front end + Parent Gate; Media one-shot
> on KIE_API_KEY with Top-20 Dev + Top-20 Consumer presets (3D-style/Pixar-like clones, voice
> clones, movies); OpenHands only if best (keep latitude); BLUEPRINT.md + ANCHOR_POINTS.md
> lock drift.

## Phrase-by-phrase map to where each clause is encoded

This is a navigation aid only — the quote above is the single source of truth; the table
below shows where each clause has been elaborated into buildable detail and which
`ANCHOR_POINTS.md` IDs lock it.

| Clause | Elaborated in | Anchors |
|---|---|---|
| "Fully autonomous runtime: one prompt → ship" | `PRODUCT_SPEC.md` §1, §4 FR-SWARM; `SWARM_TEAM_SPEC.md` | A1, A4, F9 |
| "frictionless git worktree stage/exec layer" | `BUILD_PLAN.md` WP2; `ARCHITECTURE_ADDENDUM.md` §5 | B3 |
| "continuous critics + A/B explorers + Judge" | `SWARM_TEAM_SPEC.md` §4–§6; `BUILD_PLAN.md` WP3 | F7 |
| "fork-both-ways when options diverge" | `AUTONOMY_POLICY.md` §5; `SWARM_TEAM_SPEC.md` §7 | F6 |
| "no questions except Absolute Blockers (Top-Apps Benchmark otherwise)" | `AUTONOMY_POLICY.md` §2–§4 | F5 |
| "Keep It Simple toggle on Board + both media catalogs for ages 11/14 with RGDS front end + Parent Gate" | `KEEP_IT_SIMPLE_SPEC.md` | A3, C5, C6, D5 |
| "Media one-shot on KIE_API_KEY with Top-20 Dev + Top-20 Consumer presets" | `MEDIA_PRESETS_CATALOG.md`; `PRODUCT_SPEC.md` FR-MEDIA | A5, A6 |
| "3D-style/Pixar-like clones, voice clones, movies" | `MEDIA_PRESETS_CATALOG.md` §4 (flagship chain: `consumer.pixar-clone` → `consumer.voice-clone` → `consumer.talking-clone` → `consumer.movie-from-clone`) | E5, D5 |
| "OpenHands only if best (keep latitude)" | `OPENHANDS_EVALUATION.md` | A7, FR-OH |
| "BLUEPRINT.md + ANCHOR_POINTS.md lock drift" | `ANCHOR_POINTS.md` (this repo's precedence rule); `BLUEPRINT.md` | F2 |

## Non-negotiable reading

Any agent that believes a derived doc has diluted, softened, or reinterpreted a clause above
must not silently "improve" it. Fix the derived doc to match this file, or — if this file
itself seems wrong — log an `ANCHOR-CHALLENGE` in `docs/DECISION_LOG.md` and keep building to
the letter of this file until the owner responds (`AUTONOMY_POLICY.md` §3).
