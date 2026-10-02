# KEEP_IT_SIMPLE_SPEC — One-Prompt Mode for Kids (and Anyone)

Anchors: A3, C5, C6, D5, F10, E4, E5 in `ANCHOR_POINTS.md`.

## 1. What it is

A persisted toggle ("Keep It Simple", labelled **Keep It Simple**) in the Board header, plus a matching toggle on **each** media
catalog (Developer and Consumer). When ON the runtime is in **one-prompt build mode**: one prompt → whole product, agents solve
their own issues, the user sees a friendly story of progress and a finished result.

Users: owner's 11-year-old (games, websites) and 14-year-old (thinks he knows code). Design for a capable reader with **zero**
codebase knowledge; never condescending.

## 2. Behavior matrix

| Aspect | Pro (OFF) | Keep It Simple (ON) |
|---|---|---|
| Launcher | Ship view with all options | One big box: "What do you want to make?" + **Make it** |
| Examples | none | Idea chips: "a space shooter", "a pet-photo website", "a quiz game", "my own cartoon" |
| Mode flag | `--mode pro` | `--mode simple` |
| Questions | none | none (anchor F5) |
| Forks | surfaced, owner chooses | Judge auto-picks; owner can review later |
| Branches / diffs / logs | visible | hidden; "Under the hood" is **read-only** and collapsed |
| Models / tokens / credits | visible | hidden; friendly "energy" meter + cap |
| Errors | stack traces | "Hit a snag — fixing it…" with auto-retry; never a raw trace |
| Settings | full | none; Parent Gate for anything risky |
| Output | repo + branches | A **Result card**: Play/Open button, screenshot, "Make it better" box, "Save" |
| Front end of builds | RGDS | RGDS (anchor C5) |
| Time cap | 6 h | 45 min |

## 3. Progress story (replaces logs)

Fixed, friendly stages with micro-copy, driven by real run phases:
`Understanding your idea → Looking at how the best ones work → Drawing the plan → Building → Testing → Polishing → Ready!`
Progress is real (derived from phase + task completion), not fake. Each stage can show one thumbnail/screenshot when available.

## 4. "Make it better" loop

The result card has a box ("Change something…"). Input is treated as a new prompt on the **same run/branch** (not a new project), so
iteration is incremental. Undo = revert to the previous integration commit (button "Go back"). All via the existing engine.

## 5. Guard-rails for the 14-year-old

- "Under the hood" shows file tree and code **read-only**. No terminal, no git controls, no model settings.
- A "Show the owner" button exports the project folder + `SHIP_REPORT.md` so the owner can inspect/help.
- Cannot change caps, keys, ports, or delete runs without the Parent Gate.

## 6. Parent Gate

- Guardian sets a PIN on first enable (stored as salted hash — `scrypt`/`pbkdf2` from stdlib — in `~/.clawteam/kis.json`; never plaintext, never logged).
- Gate required to: turn Keep It Simple **off**, change caps, publish anything externally, approve a **photo upload of a person**,
  approve a **voice clone**, raise the credit cap, delete a project.
- 5 wrong PINs → 5-minute lockout.
- Local only, no accounts, no cloud (anchors B7, D3).

## 7. Content & safety policy (Simple mode)

| Area | Rule |
|---|---|
| Prompt filter | Rules-first classifier blocks sexual content, graphic violence, self-harm, hate, real-person impersonation, weapons how-tos, and requests for personal data collection. Blocked prompts get a kind, non-scary redirect ("Let's make something else!") and are logged for the guardian. |
| Likeness | Photos of real people: only the child's own family/self with Parent Gate approval + consent attestation (D5). Images stay on the local asset store; **never** sent to the public photo host without Gate approval. |
| Voice clones | Only of people physically present who consent; Parent Gate; stored locally; labelled synthetic; never exported without Gate. |
| Generated apps | No external network calls, analytics, ads, auth, or data collection unless Gate-approved; no embedded third-party trackers; assets bundled locally. |
| Media output | Provider moderation errors surface as friendly messages; never bypass provider safety filters. |
| Child data | No names/ages stored beyond local display name; nothing leaves the PC except the KIE generation calls the guardian enabled. |

## 8. Spend & time caps (defaults; guardian-editable behind the Gate)

| Cap | Default |
|---|---|
| Credits per single run | 40 |
| Credits per day per profile | 150 |
| Movie preset total | 120 (needs Gate approval above 60) |
| Wall-clock per run | 45 min |
| Concurrent jobs | 2 |
Every action shows the friendly **"energy"** estimate before starting; over-cap actions ask the *Parent Gate*, not the child. These
are Parent Gate approvals, not agent questions — they do not violate F5.

## 9. Simple-mode media catalogs

Each catalog's Simple toggle: hides advanced parameters, shows ≤ 8 big preset tiles (the "Top 8 for you"), forces safe defaults
(`aspect`, `quality`, `duration` presets), shows only energy cost, and uses the preset's `simple` variant (see
`MEDIA_PRESETS_CATALOG.md`). Pro catalogs show all 20 with every knob.

## 10. UI requirements (RGDS)

- Tokens only (anchor C2); larger type scale step and bigger hit targets via RGDS spacing tokens.
- Featured-stroke on the primary "Make it" button (one featured element per page).
- Respect `prefers-reduced-motion`; all progress animations have static fallbacks.
- Keyboard accessible; ARIA live region for progress; reading level ≈ grade 5 for all micro-copy.
- Toggle component is the same in every location, reflects one shared state, and announces changes to screen readers.

## 11. API & storage

`GET/POST /api/kis/mode` · `POST /api/kis/parent-gate/set|verify` · `GET /api/kis/policy`. State: `~/.clawteam/kis.json`
`{enabled, caps, pin_hash, pin_salt, lockout_until}`; per-profile key `ui.keep_it_simple` mirrors `enabled` for the front end.

## 12. Acceptance (see `TESTING_AND_ACCEPTANCE.md` AC-8, AC-9)

Typing "make me a space shooter game" with the toggle ON yields a playable RGDS game with zero questions, no jargon on screen,
within caps; turning the toggle OFF without the PIN is impossible; a blocked prompt produces the friendly redirect.
