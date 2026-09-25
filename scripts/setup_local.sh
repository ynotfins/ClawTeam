#!/usr/bin/env bash
# One-shot local setup for the ClawTeam agentic-se swarm (Git Bash variant).
# PowerShell users: prefer scripts/setup_local.ps1
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

echo "== ClawTeam local setup ($REPO) =="

# 1. venv + editable install
if [ ! -x ".venv/Scripts/python.exe" ] && [ ! -x ".venv/bin/python" ]; then
    echo "Creating .venv ..."
    python -m venv .venv
fi
VENV_PY=".venv/Scripts/python.exe"
[ -x "$VENV_PY" ] || VENV_PY=".venv/bin/python"

"$VENV_PY" -m pip install --upgrade pip --quiet
"$VENV_PY" -m pip install -e ".[dev]" --quiet
echo "Editable install OK: clawteam $("$VENV_PY" -c 'import clawteam; print()')$("$REPO/.venv/Scripts/clawteam.exe" --version 2>/dev/null || "$REPO/.venv/bin/clawteam" --version 2>/dev/null || echo '')"

# 2. tooling checks
for t in python node npx ffmpeg git; do
    command -v "$t" >/dev/null 2>&1 && echo "  $t : SET" || echo "  $t : MISSING"
done
[ -x "$HOME/.local/bin/claude.exe" ] && echo "  claude : SET (~/.local/bin/claude.exe)" \
    || { command -v claude >/dev/null 2>&1 && echo "  claude : SET" || echo "  claude : MISSING"; }

# 3. runtime config (template + theme + profiles + hook -> ~/.clawteam)
"$VENV_PY" scripts/apply_runtime_config.py

# 4. OpenMemory health (non-fatal)
"$VENV_PY" scripts/memory/openmemory_check.py || echo "WARN: OpenMemory unreachable (degrades gracefully)"

# 5. secrets presence (names only)
echo "Secret env vars (names only):"
for v in OPENROUTER_API_KEY TWILIO_API_KEY SENDGRID_API_KEY OPENMEMORY_API_KEY OPENAI_API_KEY ANTHROPIC_API_KEY; do
    [ -n "${!v:-}" ] && echo "  $v=SET" || echo "  $v=MISSING"
done

echo "Setup complete. See BOOTSTRAP.md for activation."
