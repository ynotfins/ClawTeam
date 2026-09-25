<#
.SYNOPSIS
    Phone-safe control surface for the ClawTeam swarm (used over SSH from the phone).

.DESCRIPTION
    A deliberately small, safe command menu so a phone session (anyclaw shell skill,
    Termux, any SSH client) can drive the swarm without typing long paths.

    ssh ynotf@<pc-ip>
      D:\github\ClawTeam\scripts\phone\swarm.cmd status
      D:\github\ClawTeam\scripts\phone\swarm.cmd start -Goal "Build X"
      D:\github\ClawTeam\scripts\phone\swarm.cmd task "Fix login bug" agent
      D:\github\ClawTeam\scripts\phone\swarm.cmd stop

.EXAMPLE
    powershell -File scripts\phone\swarm.ps1 status
#>
param(
    [Parameter(Position = 0)][string]$Action = 'status',
    [Parameter(Position = 1, ValueFromRemainingArguments = $true)][string[]]$Rest
)

$Repo = 'D:\github\ClawTeam'
$Clawteam = Join-Path $Repo '.venv\Scripts\clawteam.exe'
$Team = 'se-swarm'
$env:PATH = "$Repo\.venv\Scripts;$HOME\.local\bin;$env:PATH"

function Usage {
    Write-Host "swarm <action> [args]"
    Write-Host "  status                  board show + team status + agent registry"
    Write-Host "  start -Goal `"<goal>`"   launch the hidden 6-lane swarm (OpenRouter GLM-5.3)"
    Write-Host "  stop                    stop swarm + board, clean team"
    Write-Host "  task `"<subject>`" [owner]  inject a task (default owner: agent)"
    Write-Host "  message <agent> `<text`>  send an inbox message to an agent"
    Write-Host "  log [lines]             tail the swarm log (default 40)"
    Write-Host "  board                   board URL + serve on LAN if not running"
}

switch ($Action.ToLower()) {
    'status' {
        Write-Host "== teams =="
        & $Clawteam team discover 2>&1
        Write-Host "`n== board ($Team) =="
        & $Clawteam board show $Team 2>&1
        Write-Host "`n== running agents =="
        & $Clawteam team status $Team 2>&1
    }
    'start' {
        $goal = $null
        for ($i = 0; $i -lt $Rest.Count - 1; $i++) {
            if ($Rest[$i] -eq '-Goal') { $goal = $Rest[$i + 1] }
        }
        if (-not $goal) { Write-Host "usage: swarm start -Goal `"<goal>`""; exit 1 }
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Repo 'scripts\windows\Start-Swarm.ps1') -Goal $goal -ExternalBoard
    }
    'stop' {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Repo 'scripts\windows\Stop-Swarm.ps1') -Team $Team
    }
    'task' {
        $subject = $Rest | Select-Object -First 1
        $owner = if ($Rest.Count -ge 2) { $Rest[1] } else { 'agent' }
        if (-not $subject) { Write-Host "usage: swarm task `"<subject>`" [owner]"; exit 1 }
        & $Clawteam task create $Team $subject -o $owner
    }
    'message' {
        $to = $Rest | Select-Object -First 1
        $text = ($Rest | Select-Object -Skip 1) -join ' '
        if (-not $to -or -not $text) { Write-Host "usage: swarm message <agent> `<text`>"; exit 1 }
        & $Clawteam inbox send $Team $to $text
    }
    'log' {
        $n = if ($Rest) { [int]$Rest[0] } else { 40 }
        $logFile = Join-Path $Repo ".clawteam-local\logs\$Team.log"
        if (Test-Path $logFile) { Get-Content $logFile -Tail $n } else { Write-Host "no log yet at $logFile" }
    }
    'board' {
        $ip = (Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet|WSL|Hyper-V' -and $_.IPAddress -notmatch '^169\.254' } |
            Select-Object -First 1).IPAddress
        Write-Host "Board: http://${ip}:8788  (start with: swarm.cmd start, or Start-Board.ps1 -External)"
    }
    default { Usage }
}
