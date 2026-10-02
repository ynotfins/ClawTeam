# HYGIENE_REPORT — Pre-Bootstrap Pass (2026-10-02)

Scope: hygiene + governing-docs only, per `docs/PRE_BOOTSTRAP_PROMPT.md` and the owner's
pre-bootstrap run instructions. No product features were built. No secret values were
written, printed, or logged anywhere in this pass — only environment-variable **names**.

## 0. Environment note — why a single `pytest` invocation could not be used for the baseline

Repeated attempts to run the **whole suite in one process**
(`pytest --basetemp=.clawteam-local/pytest-tmp -q`) were cut short by a real OS-level
`KeyboardInterrupt` delivered to the `python.exe` process roughly 7 seconds into every
attempt (confirmed 5× across plain foreground runs, a `Start-Process -NoNewWindow` run, and a
fully detached `-WindowStyle Hidden` run with its own console — ruling out the IDE/tooling
console as the source). This machine has **Process Lasso** running (`Get-ScheduledTask`
showed `Process Lasso Management Console (GUI)` and its session agent as `Running`) alongside
30+ pre-existing long-lived `python.exe` processes from the live swarm — consistent with a
CPU-governor/instance-management tool terminating a new sustained-CPU `python.exe` after a
short window. Evidence this is CPU-pattern-based, not simple wall-clock: a slow, mostly
I/O-bound test group (`test_spawn_backends.py` + 4 others) ran for **105 s** without being
touched, while fast, CPU-bound full-suite runs died at ~7 s every time.

**Workaround used for both the BASELINE (STEP 0) and FINAL (STEP 5) counts**: the 40 test
files were run in 7 small sequential groups (never run concurrently with each other), each
finishing in a few seconds. Per-group summary lines were captured with `-rA` and tallied by
hand. This is not a code fix and nothing about the repo or its tests was changed to work
around it — it is an operator-machine condition, out of scope for a repo-only hygiene pass,
and is recorded here as required by STEP A3 of `PRE_BOOTSTRAP_PROMPT.md` ("if anything is
red before you touch a file... record it... and continue").

## 1. BASELINE (before any edit, STEP 0/STEP A)

Branch at start: `feat/dev-control-plane-multimedia-studio`. New branch created:
`chore/pre-bootstrap`.

| Metric | Count |
|---|---|
| Passed | 639 |
| Skipped | 2 (expected — see below) |
| Failed | 1 (pre-existing, see below) |
| Total collected | 642 |

**The 1 failure** — `tests/test_event_bus.py::TestHookManager::test_shell_hook` — asserts that
a `shell` hook action running the command `touch {marker}` creates the file. `touch` is not a
Windows `cmd.exe` builtin or a shipped tool on this machine, so the hook's
`subprocess.run(command, shell=True, ...)` fails to create the marker and the assertion fails.
This is a **pre-existing, environment-specific (Windows) test gap**, not something this pass
introduced — no code in `clawteam/events/hooks.py` or its test was touched. `HANDOFF.md`
previously recorded "640 passed, 2 skipped, 0 failed" (2026-09-26); the delta (639/1/2 now vs.
640/0/2 then) is exactly this one test, which has regressed to failing sometime after that
recording, independent of this session. **Not fixed in this pass** (out of scope — hygiene
only, not product code) and not masked — reported honestly in `HANDOFF.md` §2/§6.

**The 2 skips** (both expected, match the historical "2 skipped" baseline):
- `tests/test_spawn_backends.py:1232` — "subprocess keepalive loop not implemented in Windows
  spawn branch (defect reported to plan)"
- `tests/test_task_store_locking.py:40` — "requires fork start method" (POSIX-only test
  skipped on Windows)

## 2. STEP 1 — SSOT + storage docs created/updated

| File | Action |
|---|---|
| `docs/ORIGINAL_PRODUCT_PROMPT.md` | Created — verbatim owner product intent, phrase-to-doc map |
| `docs/STORAGE_AND_DATA_CONTRACT.md` | Created — data roots verified against code (`get_data_dir()`, `config_path()`), PG assignment, memory wiring, migration note, worktree-enrollment friction |
| `ANCHOR_POINTS.md` | B5 rewritten to cite `CLAWTEAM_DATA_DIR` precisely (data root vs. the always-fixed `~/.clawteam/config.json`); new row B6a (PG: dedicated `clawteam` DB/schema inside the existing shared `127.0.0.1:55433` instance, not a new port) |
| `docs/DECISION_LOG.md` | Appended D-009 (storage/PG decision) |
| `docs/OPERATIONS_ADDENDUM.md` | Added `CLAWTEAM_DATA_DIR` row to the env-var table; linked `STORAGE_AND_DATA_CONTRACT.md` |
| `docs/PACK_INDEX.md` | Added `ORIGINAL_PRODUCT_PROMPT.md` and `STORAGE_AND_DATA_CONTRACT.md` to "Start here", the index table, and the lead-agent reading order; `ANCHOR → PRE_BOOTSTRAP → ONE_SHOT` start-here order preserved |
| `AGENTS.md` | Read-first reordered to `ANCHOR → ORIGINAL → STORAGE → BLUEPRINT → pack specs`; added a one-paragraph Mission from the SSOT; added the `pytest --basetemp=...` evidence command; added an explicit "no questions except Absolute Blocker" line |

## 3. STEP 2 — PRE_BOOTSTRAP_PROMPT.md edits (B1–B7)

| # | File | Edit made |
|---|---|---|
| B1 | `CLAUDE.md` | Memory line → `.rules/memory-local.md`; MCP server line → `agentcore-gateway`; added `ANCHOR_POINTS.md` as the first read-first item |
| B2 | `templates/agentic-se.toml` | `archive` agent's task text only: OpenMemory/mem0/`oi-openmemory-prod` wording → AgentCore facade via MCP `agentcore-gateway` (local), with a documented local-file fallback if tools are unavailable. No other lane, placeholder, or TOML structure touched. Verified: `pytest tests/test_templates.py --basetemp=.clawteam-local/pytest-tmp -q` → **25 passed** |
| B3 | `.rules/security-secrets.md` | Removed `OPENMEMORY_API_KEY` row; added `KIE_API_KEY` and `BIFROST_MCP_VIRTUAL_KEY` rows (names/purposes only) |
| B4 | `.rules/design-system.md` | Verified vendored version via `clawteam/board/static/rgds/PROVENANCE.md` (`1.1.0`) and `design/theme.tokens.json` `rgds.version` (`1.1.0`); replaced the stale "npm, currently 1.0.1" line with the verified vendored 1.1.0 text (noting npm publish is pending upstream per `PROVENANCE.md`) |
| B5 | `docs/HANDOFF.md` | §2 and §6 both reconciled to the live baseline: **639 passed / 2 skipped / 1 pre-existing-failed**, with the one failure named and explained in both places |
| B6 | `.gitignore` | Added `desktop.ini` |
| B7 | `BLUEPRINT.md` | §4 table row → `.rules/memory-local.md`; §6 secrets example list: removed `OPENMEMORY_API_KEY`, added `KIE_API_KEY`; §7 rewritten to the all-local memory summary; one row appended to §8 Decision Log. §1/§2/§3/§5/§9 **not touched** (confirmed via `git diff BLUEPRINT.md` — only §4/§6/§7/§8 hunks present) |

## 4. STEP C — report-only findings (nothing fixed; classification only)

### C1 — `clawteam/board/static/rgds.bak-1.0.1/`

- Not referenced by any code (`git grep rgds.bak` across `clawteam/` → no hits).
- The RGDS color-literal test (`tests/test_board.py::test_board_ui_has_no_color_literals`)
  only reads `clawteam/board/static/index.html` directly — it never walks the `static/`
  directory tree, so this backup folder is **not** inside its scan scope either way.
- **Recommendation**: safe to remove (it is a superseded 1.0.1 backup made 2026-09-23, before
  the current 1.1.0 vendor; `.gitignore`'s `rgds.bak-*/` pattern already keeps it out of git).
  Not removed in this pass — report-only per `PRE_BOOTSTRAP_PROMPT.md` STEP C1.

### C2 — `index.html` `var(--nfa-*, <px/rem literal>)` fallbacks

Two separate patterns exist, neither caught by `tests/test_board.py` (its only literal scan,
`test_board_ui_has_no_color_literals`, checks hex/rgb/oklch **color** literals only — it does
not scan for px/rem/spacing literals at all):

**(a) Root-level hardcoded values** (not fallbacks — the primary definition), inside the
`:root` custom-property block:
- Line 98: `--nfa-sizing-buttonMd: 36px;`
- Line 111: `--nfa-typography-bodySmall-size: 12px;`
- Line 114: `--nfa-typography-labelMedium-size: 11px;`

These three mirror `design/theme.tokens.json`'s `domain.sizing.buttonMd` / `domain.typography`
values exactly (anchor C4 permits "dense dashboard text sizes... live in the domain layer,
declared once, referenced by name") — but they are declared a **second time**, verbatim, as
literals in `index.html` rather than being emitted from the token file at render time. This is
a duplication risk (the two copies can drift) rather than a design-law violation per se.

**(b) Defensive `var(--nfa-x, <literal>)` fallbacks** scattered through the stylesheet/inline
styles — 68 total `var(--nfa-*, <px/rem>)` occurrences file-wide; 16 of them are the
`--nfa-typography-*` family specifically:

| Line | Fallback |
|---|---|
| 591 | `var(--nfa-typography-bodySmall-size, 12px)` |
| 689 | `var(--nfa-typography-labelLarge-size, 14px)` |
| 701 | `var(--nfa-typography-titleMedium-size, 18px)` |
| 703 | `var(--nfa-typography-labelMedium-size, 11px)` |
| 711 | `var(--nfa-typography-bodyMedium-size, 15px)` |
| 718 | `var(--nfa-typography-labelMedium-size, 11px)` |
| 725 | `var(--nfa-typography-bodySmall-size, 12px)` |
| 729 | `var(--nfa-typography-labelLarge-size, 14px)` |
| 737 | `var(--nfa-typography-labelMedium-size, 11px)` |
| 743 | `var(--nfa-typography-labelMedium-size, 11px)` |
| 756 | `var(--nfa-typography-labelMedium-size, 11px)` |
| 762 | `var(--nfa-typography-labelMedium-size, 11px)` |
| 768 | `var(--nfa-typography-bodySmall-size, 12px)` |
| 940 | `var(--nfa-typography-bodyLarge-size, 16px)` (inline `style=`) |
| 2029 | `var(--nfa-typography-bodyLarge-size, 16px)` (inline `style=`) |
| 2108 | `var(--nfa-typography-headlineLarge-size, 26px)` (inline `style=`) |

The remaining 52 of the 68 are the same pattern on `--nfa-spacing-*`, `--nfa-radius-*`, and
`--nfa-sizing-*` (e.g. `var(--nfa-spacing-sm, 10px)`, `var(--nfa-radius-chip, 13px)` — seen
repeatedly from line 591 onward). Since the `:root` block always sets every `--nfa-*` variable
before these rules are evaluated, these fallbacks are **currently dead code** (the literal
after the comma never actually applies) — but the literal text is still present in the
source, which is what anchor C2 forbids literally, and `tests/test_board.py` does not
currently enforce it.

**Recommendation (not applied this pass)**: either (i) drop the `, <literal>` fallback
entirely from all 68 sites, since the `:root` block already guarantees the variable is set,
or (ii) if defensive fallbacks are wanted for robustness, point them at another `var(--md-*)`
token instead of a literal (e.g. `var(--nfa-typography-bodySmall-size, var(--md-sys-typescale-body-small-size))`).
Either fix is a WP8/hygiene-grade product change, not a docs change — deliberately deferred to
the bootstrap run per `PRE_BOOTSTRAP_PROMPT.md` STEP C2's own instruction not to blind-fix it
here.

### C3 — Remaining OpenMemory/mem0/`oi-openmemory` references (repo-wide `git grep`, excluding `.venv`, `node_modules`, `clawteam/board/static/rgds*`)

Classified per STEP C3 (leave / stale-text-to-fix-later / functional-flag):

**(a) Historical — leave as-is:**
- `CHANGELOG.md:125` — "All-local memory policy enforced: OpenMemory wiring removed" — this
  *is* the changelog entry documenting the removal; correct to keep verbatim.
- `.mcp.json.bak-20260916` — a dated backup file (not the live `.mcp.json`, which was
  confirmed this pass to register only `agentcore-gateway`, `playwright`, `comfyui`);
  harmless, matches its own filename's "this is a snapshot" intent.

**(b) Stale policy text — flag for a later pass, not fixed here (outside the authorized B1–B7 edit list):**
- `.cursor/rules/memory-openmemory.mdc` — entire file is the old pre-`memory-local.md` rule;
  `AGENTS.md` and `.rules/memory-local.md` already say they win over stale mentions, but the
  stale file itself is still present and could mislead a reader who opens it directly.
- `.cursorrules` (repo root, legacy format) — lines 12–17 still describe the OpenMemory /
  `oi-openmemory-prod` memory law and point at `.rules/memory-openmemory.md`, contradicting
  the canonical `.rules/memory-local.md`.
- `BOOTSTRAP.md:313,354,369` — internally inconsistent with its own line 120 ("OpenMemory
  wiring is removed"): line 313's "Canonical pack" table still lists
  `memory-openmemory.md`; lines 354/369 talk about "OpenMemory is still down" / health-check
  script as if the service is still a live dependency.
- `scripts/setup_local.ps1:11,83-87,93` / `scripts/setup_local.sh:33-34,38` — both still run
  an OpenMemory health check step and list `OPENMEMORY_API_KEY` in their secrets table instead
  of `KIE_API_KEY` / `BIFROST_MCP_VIRTUAL_KEY`. `setup_local.ps1` was **not** executed in this
  pass beyond the isolated, narrow checks in §5 below (running its venv-install / skill-copy /
  OpenMemory-network-probe side effects was out of scope for a docs-only hygiene run).
- `templates/agentic-se.toml:192` — a `[[template.tasks]]` *subject string*
  ("Initialize team memory (oi-openmemory-prod) and archive bootstrap decisions"), **not**
  the `archive` agent's task prompt text that B2 authorized editing. Left untouched per B2's
  explicit scope ("do not change any other lane, any placeholder, or TOML structure").

**(c) Functional code — flag (not removed; still actually runs if invoked):**
- `scripts/memory/openmemory_check.py` — a working script that makes a real HTTP(S) call to
  an OpenMemory-shaped endpoint (`OPENMEMORY_BASE_URL`, default `http://127.0.0.1:8760`) and
  reads `OPENMEMORY_API_KEY` / `OPENMEMORY_USER` from the environment. This directly
  contradicts `.rules/memory-local.md`'s "the previous OpenMemory wiring... is REMOVED."
  Recommend retiring this script (or repointing it at an `agentcore-gateway` health check) in
  a future pass — it is invoked by `scripts/setup_local.ps1` step 6, which this pass did not
  run end-to-end.

## 5. STEP 3 — wiring verification (no secret values printed)

- **`CLAWTEAM_DATA_DIR`**: was unset at session start
  (`[Environment]::GetEnvironmentVariable('CLAWTEAM_DATA_DIR','User')` returned empty — no
  prior `~/.clawteam/{teams,tasks,costs,sessions,media}` subtrees existed either, so no
  migration was needed, see `STORAGE_AND_DATA_CONTRACT.md` §7). **Set** this pass to
  `F:\AgentCore\runtime\clawteam` via `[Environment]::SetEnvironmentVariable(... 'User')`;
  target directory created. New terminals will pick it up; the current shell's in-process
  env was also updated for any same-session checks.
- **`.mcp.json`**: confirmed registers exactly `agentcore-gateway` (+ `playwright`, `comfyui` —
  unrelated dev tools), matching `.rules/memory-local.md`.
- **Secret presence (names only, values never shown or logged)**:

  | Variable | State |
  |---|---|
  | `OPENROUTER_API_KEY` | SET |
  | `TWILIO_API_KEY` | SET |
  | `SENDGRID_API_KEY` | SET |
  | `KIE_API_KEY` | SET |
  | `BIFROST_MCP_VIRTUAL_KEY` | SET |
  | `OPENAI_API_KEY` | SET |
  | `ANTHROPIC_API_KEY` | MISSING (direct-provider lane dormant; not required — OpenRouter is the primary swarm routing path) |

- **`git config core.longpaths true`**: set at `--local` scope on this repo (was already
  `true` at `--global` scope; local now matches explicitly).
- **Worktree enrollment friction**: documented in `STORAGE_AND_DATA_CONTRACT.md` §8
  (`scripts/hooks/sync_blueprint.py` only copies `.mcp.json` into worktrees *at creation
  time*; there is no "resync an existing worktree" command yet — flagged for WP2, not built
  this pass).
- **Postgres**: *not* touched. Per `ANCHOR_POINTS.md` B6a and `STORAGE_AND_DATA_CONTRACT.md`
  §5, the dedicated `clawteam` database/schema inside the shared `127.0.0.1:55433` AgentCore
  instance is a WP2/WP6-time action — creating or altering anything in that shared instance
  is explicitly outside this run's "do not touch AgentCore control-plane" boundary.

## 6. STEP 5 — FINAL verification

Re-ran the same 7-group chunked `pytest` pass (STEP 0 methodology, §0 above) after all edits:

| Metric | BASELINE | FINAL |
|---|---|---|
| Passed | 639 | 639 |
| Skipped | 2 | 2 |
| Failed | 1 (pre-existing `test_shell_hook`) | 1 (same, untouched) |

**0 new failures. 0 dropped passes.** Counts match baseline exactly — see the FINISH line in
the session transcript and `git diff --stat` for the full list of touched files (§2/§3 above).
Secret-value scan of the diff: no `KEY=`-shaped value patterns, no key-like strings — only
variable **names** appear anywhere in the diff.

## 7. Anything skipped, and why

- The one pre-existing test failure (`test_shell_hook`) was **not** fixed — out of scope for a
  hygiene-only pass; documented honestly instead of silently baselining around it.
- STEP C1–C3 findings were **not** fixed — report-only by explicit instruction.
- `scripts/setup_local.ps1`'s full side-effecting flow (venv install, skill copy, OpenMemory
  network probe) was **not** executed — only the narrow, read-only pieces relevant to STEP 3
  (secret-name presence, `.mcp.json` contents) were replicated directly.
- The Postgres `clawteam` DB/schema was **not** created — contract-only this pass (§5 above;
  anchor B6a), to respect "do not touch AgentCore control-plane."
- No `~/.clawteam` → `F:` data migration was performed — none was needed (no prior data root
  existed on this machine; confirmed empty before setting the env var).
