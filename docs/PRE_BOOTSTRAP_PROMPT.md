# PRE_BOOTSTRAP_PROMPT — Run This BEFORE `ONE_SHOT_BOOTSTRAP_PROMPT.md`

> Paste the block below into the build agent (Zcode GLM / Cursor / any coding agent) **first**. It makes the small cleanup edits the
> doc pack depends on, proves the baseline is green, and stops. When it reports `PRE-BOOTSTRAP COMPLETE`, paste the Full (or Compact)
> prompt from `ONE_SHOT_BOOTSTRAP_PROMPT.md`.
>
> It is self-contained, makes no product changes, asks no questions, and does not push anything.

```
ROLE
You are doing a one-time PRE-BOOTSTRAP cleanup of ClawTeam (D:\github\ClawTeam). This is hygiene only: no product features.
Do not ask me questions. Decide using the rules below, log what you did, and stop at the end. Never push (no `git push` at all).
Never write, print, or echo any secret value; reference env var NAMES only.

OWNER AUTHORIZATION (explicit, one-time)
I, the owner, authorize the exact edits listed below, including the single edit to BLUEPRINT.md (normally only the `plan` lane edits it).
Edit nothing else in BLUEPRINT.md. Do not touch anything under clawteam/board/static/rgds/ (vendored, sha-locked).

READ FIRST (in order)
ANCHOR_POINTS.md, AGENTS.md, .rules/memory-local.md, .rules/security-secrets.md, .rules/design-system.md, docs/BUILD_PLAN.md §6.
Policy being enforced: ALL memory is LOCAL (AgentCore facade via MCP `agentcore-gateway`, local files, loopback DBs).
No OpenMemory/mem0, no Obsidian. `.rules/memory-local.md` and AGENTS.md win over any stale text.

STEP A — BASELINE (before any edit)
A1. `git status` and `git branch --show-current`; record both.
A2. Create and switch to a new local branch from the current one: `chore/pre-bootstrap`.
    (Do the work in the main checkout for this cleanup only; the doc pack files are untracked and must come along.)
A3. Run `pytest --basetemp=.clawteam-local/pytest-tmp -q` and record the exact passed/skipped/failed counts as BASELINE.
    If anything is red before you touch a file, do NOT fix product code: record it in docs/HYGIENE_REPORT.md as "pre-existing failure" and continue.
A4. Note each file's line endings (AGENTS.md is CRLF). Preserve each file's existing line endings on every edit.

STEP B — EDITS (make exactly these; use targeted edits, not whole-file rewrites)
B1. CLAUDE.md
    - Replace the line mentioning "Memory (OpenMemory `oi-openmemory-prod`): `.rules/memory-openmemory.md`" with:
      "Memory (all-local, AgentCore facade): `.rules/memory-local.md`".
    - Replace the line saying the team memory MCP server `openmemory` is registered via `.mcp.json` with one saying the MCP server
      `agentcore-gateway` is registered via `.mcp.json`.
    - Add `ANCHOR_POINTS.md` as the first item in its quick-reference list ("immutable foundations; read before anything else").
B2. templates/agentic-se.toml — the `archive` agent's task text ONLY
    - Replace the OpenMemory / `oi-openmemory-prod` / mem0 wording with: team memory is the AgentCore memory facade via MCP
      `agentcore-gateway` (local only), see `.rules/memory-local.md`; if the tools are unavailable, write the note to local files and say so.
    - Do not change any other lane, any placeholder (`{team_name}`, `{goal}`), or any TOML structure.
    - Run `pytest tests/test_templates.py --basetemp=.clawteam-local/pytest-tmp -q` and require it green.
B3. .rules/security-secrets.md
    - In the recognized-variables table remove the `OPENMEMORY_API_KEY` row.
    - Add rows: `KIE_API_KEY` (kie.ai cloud media; if absent the cloud media lane is dormant) and `BIFROST_MCP_VIRTUAL_KEY`
      (bearer for the agentcore-gateway MCP). Names and purposes only.
B4. .rules/design-system.md
    - It says the npm package `@r3lentless/rgds-web` is "currently 1.0.1". First verify the vendored version in
      clawteam/board/static/rgds/PROVENANCE.md and design/theme.tokens.json (`rgds.version`). Then make the text say the vendored
      version is that verified value (expected 1.1.0). Do not change anything else.
B5. docs/HANDOFF.md
    - §2 and §6 disagree on the test count (640 vs 636). Use the BASELINE counts from A3 in both places (passed / skipped).
B6. .gitignore — add a line `desktop.ini` (keep the existing entries, including `.clawteam-local/`).
B7. BLUEPRINT.md (the ONE authorized edit)
    - §4 table: replace the `.rules/memory-openmemory.md` row with `.rules/memory-local.md` — "All-local memory policy: AgentCore facade via MCP, local files, loopback DBs".
    - §6: remove `OPENMEMORY_API_KEY` from the example secrets list; add `KIE_API_KEY`.
    - §7: replace the OpenMemory text with the all-local policy summary (one short paragraph).
    - Append ONE row to the §8 Decision Log: date today, "Aligned memory policy text to all-local (.rules/memory-local.md); added ANCHOR_POINTS.md", rationale "Pre-bootstrap hygiene, owner-authorized".
    - Do NOT touch §1 (Mission), §2, §3, §5, §9.

STEP C — REPORT-ONLY CHECKS (change nothing here; write findings to docs/HYGIENE_REPORT.md)
C1. clawteam/board/static/rgds.bak-1.0.1/ : is it referenced by any code/test, and does tests/test_board.py's color-literal scan include it?
    Do not delete it. Recommend keep/remove with the evidence.
C2. clawteam/board/static/index.html : list every `var(--nfa-typography-...)` (or similar) fallback containing a px/rem literal, with line numbers,
    and say whether tests/test_board.py permits them. Recommend a fix (RGDS typescale token per case) but do not apply it.
C3. Grep the whole repo (excluding .git, .venv, node_modules, clawteam/board/static/rgds*) for remaining `openmemory`, `OpenMemory`, `mem0`,
    `OPENMEMORY`, `oi-openmemory` references. List each remaining hit with file:line and whether it is (a) historical/changelog (leave),
    (b) stale policy text (should be fixed later), or (c) functional code (flag it). Do not fix (b)/(c) now.

STEP D — VERIFY
D1. `pytest --basetemp=.clawteam-local/pytest-tmp -q` must show the same passed/skipped counts as BASELINE and 0 failed.
    If a count dropped or a test broke, revert the offending edit (`git checkout -- <file>`), re-run, and note it in the report.
D2. Secret check: grep your diff for key-like strings and for the names-with-values pattern (e.g. `KIE_API_KEY=`); there must be none.
D3. `git diff --stat` must show ONLY these files modified: CLAUDE.md, templates/agentic-se.toml, .rules/security-secrets.md,
    .rules/design-system.md, docs/HANDOFF.md, .gitignore, BLUEPRINT.md (+ AGENTS.md if it was already modified by the doc pack install).
    Untracked additions allowed: ANCHOR_POINTS.md, the doc pack under docs/, docs/HYGIENE_REPORT.md.
D4. Confirm line endings were preserved (`git diff` must not show whole-file changes for CRLF files).

STEP E — COMMIT (local only)
Commit everything (the doc pack, the edits, HYGIENE_REPORT.md) on `chore/pre-bootstrap` with message
"chore: install autonomous-runtime doc pack and align memory policy text". Do NOT push. Do NOT touch the `origin` remote.

STEP F — FINISH
Write docs/HYGIENE_REPORT.md (if not already) with: BASELINE counts, FINAL counts, each edit made (file + one line), the Step C findings,
anything skipped and why. Then print exactly:
PRE-BOOTSTRAP COMPLETE — branch chore/pre-bootstrap — tests <passed>/<skipped>/<failed> — report: docs/HYGIENE_REPORT.md
and STOP. Do not start the bootstrap. I will give you that prompt next.
```

## Notes for the owner

- This prompt commits the doc pack on a local branch `chore/pre-bootstrap`. The bootstrap prompt then branches from it (`ship/bootstrap`).
- If you would rather not let any agent edit `BLUEPRINT.md`, delete step B7 before pasting. Everything else is independent of it.
- `docs/HYGIENE_REPORT.md` is the agent's output; the bootstrap prompt's gap audit will read it.
- Steps C1–C3 are report-only on purpose: the px fallbacks in `index.html` and any remaining OpenMemory code paths deserve a deliberate fix inside the bootstrap run (WP8), not a blind edit.
