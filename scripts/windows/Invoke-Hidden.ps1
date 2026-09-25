<#
.SYNOPSIS
    Launch a PowerShell script completely invisibly in the background on Windows.

.DESCRIPTION
    Starts powershell.exe with CreateNoWindow = true (zero console flash, no taskbar
    entry) running the given -File script. All output should be redirected by the
    script itself (or wrap with an outer script that does `*>> log`).
    Dot-source this file:  . .\Invoke-Hidden.ps1

.EXAMPLE
    . .\Invoke-Hidden.ps1
    $pid = Start-HiddenScript -ScriptPath "D:\repo\.clawteam-local\run\board.ps1"
#>

function Start-HiddenScript {
    param(
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [string[]]$ScriptParameters = @(),
        [string]$WorkingDirectory = (Get-Location).Path
    )

    if (-not (Test-Path -LiteralPath $ScriptPath)) {
        throw "Script not found: $ScriptPath"
    }

    $full = Convert-Path -LiteralPath $ScriptPath
    $quoted = $ScriptParameters | ForEach-Object {
        if ($_ -match '\s') { "`"$_`"" } else { $_ }
    }
    $paramLine = ($quoted -join ' ')

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
    $psi.Arguments = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File `"$full`" $paramLine"
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true   # invisible: no window, no flash, no taskbar entry
    $psi.WorkingDirectory = $WorkingDirectory

    $proc = [System.Diagnostics.Process]::Start($psi)
    return $proc.Id
}
