# Vendored RGDS web assets

- Package: `@r3lentless/rgds-web` 1.1.0 (form-factor release; repo tgz, npm publish pending)
- Source artifact: `dist-packages/r3lentless-rgds-web-1.1.0.tgz` from the RGDS
  monorepo (`D:\github\r3lentless-grind-design-system`), extracted verbatim.
- tgz SHA-256: `31e611e2d5165bc2aad859f462962de088f028c57b5e40d053dcb0271372cc29`
- tokens.css SHA-256: `425c87fbb3c3d26377364758fc53cdeffde58be42ff892d26294bec7aa364fc2`
- Discovery manifest: `C:\Users\ynotf\.rgds\RGDS_MANIFEST.json` (v1.0.1, production)
- Figma Team Library: `R3lentless-Grind Design System — RGDS`,
  file `KbhSAUCrADaqhxOm7jM2FC`

Do not hand-edit these files. To upgrade: bump the version here, re-extract
from the new release tgz, and update `rgds.version` in `design/theme.tokens.json`.

The board's theme authority chain: RGDS manifest → Figma library → these
vendored tokens → board domain layer (`design/theme.tokens.json`, aliases and
board-specific extras only, no color values).
