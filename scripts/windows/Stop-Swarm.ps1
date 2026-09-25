<#
.SYNOPSIS
    Gracefully stop a hidden ClawTeam swarm + board and clean up team state.

.DESCRIPTION
    1. Creates the stop file that ends the hidden supervisor.
    2. Kills agent PIDs recorded in ~/.clawteam/teams/<team>/spawn_registry.json.
    3. Kills any surviving processes whose command line references the team.
    4. Optionally stops the web board.
    5. Runs `clawteam team cleanup <team> --force`.

.EXAMPLE
    .\Stop-Swarm.ps1 -Team se-swarm
    .\Stop-Swarm.ps1 -Team se-swarm -KeepTeamData
#>
param(
    [string]$Team = "se-swarm",
    [switch]$KeepTeamData,
    [switch]$KeepBoard
)

$ErrorActionPreference = 'Continue'
$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$RunDir = Join-Path $Repo '.clawteam-local\run'
$env:PATH = "$Repo\.venv\Scripts;$HOME\.local\bin;$env:PATH"

# 1. Signal the supervisor to exit.
$stopFile = Join-Path $RunDir "$Team.stop"
Set-Content -LiteralPath $stopFile -Value (Get-Date -Format s)

# 2. Kill agent PIDs from the spawn registry.
$registry = Join-Path $HOME ".clawteam\teams\$Team\spawn_registry.json"
if (Test-Path -LiteralPath $registry) {
    try {
        $reg = Get-Content -LiteralPath $registry -Raw | ConvertFrom-Json
        foreach ($prop in $reg.PSObject.Properties) {
            $entry = $prop.Value
            $agentPid = $entry.pid
            if ($agentPid -and $agentPid -gt 0) {
                Write-Host "Stopping agent '$($prop.Name)' (pid $agentPid)"
                Stop-Process -Id $agentPid -Force -ErrorAction SilentlyContinue
            }
        }
    } catch {
        Write-Warning "Could not parse spawn registry: $_"
    }
}

# 3. Belt and suspenders: any process still referencing the team.
Get-CimInstance Win32_Process -Filter "Name = 'claude.exe' or Name = 'cmd.exe' or Name = 'python.exe'" |
    Where-Object { $_.CommandLine -and $_.CommandLine -like "*--team $Team*" } |
    ForEach-Object {
        Write-Host "Stopping leftover process $($_.Name) (pid $($_.ProcessId))"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

# 4. Supervisor + board.
foreach ($pidFile in @((Join-Path $RunDir "$Team-supervisor.pid"), (Join-Path $RunDir 'board.pid'))) {
    if ($KeepBoard -and $pidFile -like '*board.pid') { continue }
    if (Test-Path -LiteralPath $pidFile) {
        $p = (Get-Content -LiteralPath $pidFile -Raw).Trim()
        if ($p -match '^\d+$') { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue }
        Remove-Item -LiteralPath $pidFile -ErrorAction SilentlyContinue
    }
}

# 5. Team cleanup.
if (-not $KeepTeamData) {
    Write-Host "Cleaning up team '$Team'..."
    & clawteam team cleanup $Team --force 2>&1 | Write-Host
}

Write-Host "Swarm '$Team' stopped."
