<#
.SYNOPSIS
    Open the ClawTeam board as a desktop app window (no browser UI).

.DESCRIPTION
    Ensures the board is serving on the given port (starts it hidden if not),
    then opens it in an Edge/Chrome app-mode window: standalone window, own
    taskbar entry, no tabs/address bar. The Desktop "ClawTeam Board" shortcut
    points here. Avoids CIM cmdlets (Get-Net*) because this machine's WMI
    repository is partially broken ("Invalid class").

.EXAMPLE
    .\Open-Board-Desktop.ps1                # default port 8788
    .\Open-Board-Desktop.ps1 -Port 9000     # custom port
#>
param(
    [int]$Port = 8788
)

$ErrorActionPreference = 'Stop'
$Url = "http://127.0.0.1:$Port/"

function Test-PortListening {
    param([int]$Number)
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $task = $client.ConnectAsync('127.0.0.1', $Number)
            if ($task.Wait(1000) -and $client.Connected) { return $true }
            return $false
        } finally { $client.Dispose() }
    } catch { return $false }
}

if (-not (Test-PortListening $Port)) {
    & (Join-Path $PSScriptRoot 'Start-Board.ps1') -Port $Port -NoBrowser
    # Wait up to 15s for the HTTP endpoint to answer.
    $deadline = (Get-Date).AddSeconds(15)
    while ((Get-Date) -lt $deadline) {
        if (Test-PortListening $Port) { break }
        Start-Sleep -Milliseconds 500
    }
}

# App-mode window: prefer Edge (preinstalled on Win11), fall back to Chrome,
# then to the default browser.
$browser = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($browser) {
    Start-Process $browser -ArgumentList "--app=$Url", '--window-size=1440,920'
} else {
    Start-Process $Url
}
