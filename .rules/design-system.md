# Design System — RGDS Authority (Canonical)

**Scope**: every generated output file, code review, markdown readout, dashboard, UI component,
and document produced by any agent in this workspace. No exceptions.

## 1. RGDS is the design system

The canonical frontend/design system is the **R3lentless-Grind Design System (RGDS)** — an
independent org system, not NFA-owned, not AgentCore-owned.

- **Discovery**: `C:\Users\ynotf\.rgds\RGDS_MANIFEST.json` (always start there)
- **Figma Team Library**: `R3lentless-Grind Design System — RGDS`, file `KbhSAUCrADaqhxOm7jM2FC`
- **Web package**: `@r3lentless/rgds-web` (npm, currently 1.0.1)
- **Consumed in this repo**: vendored at `clawteam/board/static/rgds/` with SHA-256
  provenance in `clawteam/board/static/rgds/PROVENANCE.md`

Authority chain (strict order — do not invent): RGDS manifest → published Figma library →
vendored package dist → board domain layer (`design/theme.tokens.json`). Do not create a
competing local theme, token system, component library, or visual foundation. Domain-specific
board UI (kanban semantics, featured-stroke refs, dense-dashboard sizes) is built **on top of**
RGDS tokens as `var(--md-*)` references only — never as restated color values.

## 2. Zero hardcoding law

No color, gradient, shadow, radius, spacing, or font value may ever be hardcoded at the
component level — not in CSS, not in inline `style=""`, not in arbitrary values, not in SVG
fills, not in chart libraries, not in generated markdown styling.

Everything resolves from RGDS tokens:

- **Color / state / elevation / motion**: `--md-sys-color-*`, `--md-rgds-state-*`,
  `--md-sys-elevation-*`, `--md-sys-motion-*` (vendored `rgds/tokens.css`)
- **Shape**: `--md-sys-shape-corner-*` · **Spacing**: `--md-sys-spacing-*`
  · **Typography**: `--md-sys-typescale-*` (font is Inter)
- **Theme switching is RGDS-native**: `:root[data-theme]` with the four RGDS modes
  (`primary-light`, `secondary-light`, `primary-dark`, `secondary-dark`); the board engine
  also persists `rgds-theme` in localStorage (RGDS convention)
- **Featured stroke / rainbow**: `--md-custom-stroke-featured`; the rainbow gradient
  (`--md-custom-rainbow-gradient`) is enabled only where RGDS sets
  `--md-custom-rainbow-enabled: 1` (secondary-dark)
- **Board alias layer**: `index.html` maps legacy board `--*` names to RGDS tokens once, in
  `:root`. Components consume aliases or RGDS vars — never literals. `tests/test_board.py`
  enforces zero color literals in the UI.

The legacy mode ids (`light-google`, `light-orange`, `dark-speakeasy`, `dark-orange`) map via
`legacyModeMap` in `design/theme.tokens.json` (→ `primary-light`, `secondary-light`,
`secondary-dark`, `primary-dark` respectively). Do not invent new theme names.

## 3. Rainbow is stroke-only — the dynamic stroke law

- **No rainbow fills, ever.** Rainbow/featured gradients appear only as box
  strokes (border-box layers) or the featured rotating arc. Every component
  that uses `var(--stroke-gradient)` (or `--md-custom-rainbow-gradient`) as a
  border-box layer must sit it under an **opaque** padding-box fill — never a
  translucent one (`transparent`, low-alpha color-mix), or the rainbow bleeds
  into the interior. `tests/test_board.py` rejects that pattern.
- **Strokes rest faded and brighten toward the pointer.** Box strokes sit at
  reduced saturation at rest; on hover they brighten via
  `--md-rgds-state-hover-chroma`, and a pointer-local ring highlight
  (`--px`/`--py`, fed by the rAF-throttled pointer listener) makes the stroke
  area nearest the mouse glow brighter — matching the Figma RGDS interaction
  states. Featured boxes carry the rotating/pulsating arc (one per page).
- Transitions/animations use `--md-sys-motion-*` durations/easings and respect
  `prefers-reduced-motion`.

## 4. Layout & composition language

- Clean white space driven by `--md-sys-spacing-*`.
- Card components: rounded by `--md-sys-shape-corner-*`, stroked by the mode's featured
  stroke token (rainbow where RGDS enables it), elevated by `--md-sys-elevation-*`.
- Hover/focus/pressed states use `--md-rgds-state-*` tokens — no magic opacity literals.
- Dense dashboard text sizes that RGDS's typescale lacks live in the domain layer
  (`domain.typography` in `design/theme.tokens.json`), declared once, referenced by name.

## 5. Upgrades

When RGDS publishes a new version: re-vendor from the release tgz, update
`rgds.version` in `design/theme.tokens.json` and the hashes in
`clawteam/board/static/rgds/PROVENANCE.md`. Never hand-edit vendored files. Brand seed
finalization happens upstream in the RGDS monorepo (its seeds are PROVISIONAL by design) —
not as local forks here.

## 6. Violations

A deliverable containing any hardcoded style value is **not done**. `debug` lane files a
defect; `agent` lane must refactor to RGDS tokens before the task can be marked completed.
