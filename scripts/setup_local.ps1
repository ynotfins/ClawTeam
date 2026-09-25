<#
.SYNOPSIS
    One-shot local setup for the ClawTeam agentic-se swarm on Windows (no Docker).

.DESCRIPTION
    1. Creates .venv in the repo and installs the framework editable: pip install -e ".[dev]"
    2. Verifies native tooling: python, node/npx, ffmpeg, git, claude
    3. Ensures ~/.local/bin (claude.exe) is on the user PATH
    4. Installs the clawteam skill into ~/.claude/skills (Claude Code discovers it)
    5. Applies runtime config to ~/.clawteam (subprocess backend, profiles, hook, template, theme)
    6. Health-checks the local OpenMemory (oi-openmemory-prod) - non-fatal

.EXAMPLE
    .\scripts\setup_local.ps1
    .\scripts\setup_local.ps1 -SkipInstall   # skip venv/pip (already installed)
#>
param(
    [switch]$SkipInstall,
    [switch]$SkipSkill
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent (Split-Path -Parent $PSCommandRoot)
Set-Location -LiteralPath $Repo

Write-Host "== ClawTeam local setup ($Repo) ==" -ForegroundColor Cyan

# ---- 1. venv + editable install ------------------------------------------
$VenvPython = Join-Path $Repo '.venv\Scripts\python.exe'
if (-not $SkipInstall) {
    if (-not (Test-Path $VenvPython)) {
        Write-Host "Creating .venv ..."
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "python -m venv failed (need Python 3.10+ on PATH)" }
    }
    Write-Host "Installing clawteam editable (pip install -e .[dev]) ..."
    & $VenvPython -m pip install --upgrade pip --quiet
    & $VenvPython -m pip install -e ".[dev]" --quiet
    if ($LASTEXITCODE -ne 0) { throw "pip install -e . failed" }
}

# ---- 2. tooling checks -----------------------------------------------------
function Test-Tool([string]$Name) {
    if (Get-Command $Name -ErrorAction SilentlyContinue) { return "SET" }
    return "MISSING"
}
$claudeLocal = Join-Path $HOME '.local\bin\claude.exe'
Write-Host ""
Write-Host "Tooling (native, no Docker):"
Write-Host ("  python : {0}" -f (Test-Tool python))
Write-Host ("  node   : {0}" -f (Test-Tool node))
Write-Host ("  npx    : {0}" -f (Test-Tool npx))
Write-Host ("  ffmpeg : {0}" -f (Test-Tool ffmpeg))
Write-Host ("  git    : {0}" -f (Test-Tool git))
Write-Host ("  claude : {0}{1}" -f (Test-Tool claude), $(if (Test-Path $claudeLocal) { " (found at ~/.local/bin/claude.exe)" } else { "" }))
Write-Host ("  clawteam (venv): {0}" -f $(if (Test-Path (Join-Path $Repo '.venv\Scripts\clawteam.exe')) { "SET" } else { "MISSING" }))

# ---- 3. ensure ~/.local/bin on user PATH -----------------------------------
$userPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
if ($userPath -notlike "*$HOME\.local\bin*" -and (Test-Path $claudeLocal)) {
    [Environment]::SetEnvironmentVariable('PATH', "$HOME\.local\bin;$userPath", 'User')
    Write-Host ""
    Write-Host "Added ~/.local/bin to user PATH (new terminals only)."
}

# ---- 4. skill install -------------------------------------------------------
if (-not $SkipSkill) {
    $skillSrc = Join-Path $Repo 'skills\clawteam'
    $claudeCfg = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { Join-Path $HOME '.claude' }
    $skillDst = Join-Path $claudeCfg 'skills\clawteam'
    if (Test-Path $skillSrc) {
        New-Item -ItemType Directory -Force -Path (Split-Path $skillDst) | Out-Null
        if (Test-Path $skillDst) { Remove-Item -Recurse -Force $skillDst }
        Copy-Item -Recurse $skillSrc $skillDst
        Write-Host "Skill installed: $skillDst"
    }
}

# ---- 5. runtime config -------------------------------------------------------
$env:PATH = "$Repo\.venv\Scripts;$HOME\.local\bin;$env:PATH"
& $VenvPython (Join-Path $Repo 'scripts\apply_runtime_config.py')

# ---- 6. OpenMemory health ----------------------------------------------------
Write-Host ""
& $VenvPython (Join-Path $Repo 'scripts\memory\openmemory_check.py')
if ($LASTEXITCODE -ne 0) {
    Write-Warning "OpenMemory unreachable - memory features degrade gracefully until it is started."
}

# ---- secrets presence (names only) -------------------------------------------
Write-Host ""
Write-Host "Secret environment variables (names only, values never shown):"
foreach ($v in @('OPENROUTER_API_KEY', 'TWILIO_API_KEY', 'SENDGRID_API_KEY', 'OPENMEMORY_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_API_KEY')) {
    $state = if ([Environment]::GetEnvironmentVariable($v)) { 'SET' } elseif (Get-ChildItem "Env:$v" -ErrorAction SilentlyContinue) { 'SET' } else { 'MISSING' }
    Write-Host ("  {0,-22} {1}" -f $v, $state)
}

Write-Host ""
Write-Host "Setup complete. Launch the swarm:"
Write-Host "  powershell -File scripts\windows\Start-Swarm.ps1 -Goal `"<your goal>`""
Write-Host "Dashboard: http://127.0.0.1:8788  (Stop-Swarm.ps1 to stop)"
