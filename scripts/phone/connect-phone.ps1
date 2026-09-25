<#
.SYNOPSIS
    Pair and connect the S26 Ultra to this PC over Android wireless debugging.

.DESCRIPTION
    On the phone: Settings > Developer options > Wireless debugging.
      - If never paired here before: tap "Pair device with pairing code" and note
        IP:PORT + 6-digit code, then run with -PairIpPort and -PairCode.
      - Main screen shows the connection IP:PORT (different from pairing port).
    After connecting, this script detects anyclaw/openclaw/claw apps and prints
    their versions, and enables reverse TCP forwarding so the phone can reach
    the PC board via http://localhost:8788 even without LAN firewall changes.

.EXAMPLE
    .\connect-phone.ps1 -IpPort 192.168.1.212:37847
    .\connect-phone.ps1 -IpPort 192.168.1.212:37847 -PairIpPort 192.168.1.212:39215 -PairCode 481920
#>
param(
    [Parameter(Mandatory = $true)][string]$IpPort,
    [string]$PairIpPort = "",
    [string]$PairCode = ""
)

if ($PairIpPort -and $PairCode) {
    Write-Host "Pairing with $PairIpPort (code from phone screen)..."
    adb pair $PairIpPort $PairCode
}

Write-Host "Connecting to $IpPort ..."
adb connect $IpPort
adb devices -l

$pkgs = adb shell pm list packages 2>$null | Select-String -Pattern 'claw'
if ($pkgs) {
    Write-Host "`nClaw apps installed on phone:"
    foreach ($p in $pkgs) {
        $name = ($p -replace 'package:','').Trim()
        $ver = (adb shell dumpsys package $name 2>$null | Select-String 'versionName' | Select-Object -First 1)
        Write-Host ("  {0}  {1}" -f $name, $ver)
    }
} else {
    Write-Host "`nNo claw-named packages visible (anyclaw may use a different package id)."
}

# Reverse forward: phone can open http://localhost:8788 -> PC board, no firewall needed.
adb reverse tcp:8788 tcp:8788 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "`nReverse forward set: on the phone open http://localhost:8788 for the board."
}

Write-Host "`nUSB-style control from PC is now live (adb -s $IpPort shell ...)."
