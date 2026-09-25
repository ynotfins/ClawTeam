<#
.SYNOPSIS
    One-time admin setup that makes this PC controllable from your phone.

.DESCRIPTION
    Run once from an elevated PowerShell (it self-elevates via UAC if needed):
      1. Installs the Windows OpenSSH Server (optional feature).
      2. Starts sshd and sets it to auto-start.
      3. Opens firewall ports on the LOCAL SUBNET only:
         - 22   (SSH - authenticates with your Windows account credentials)
         - 8788 (ClawTeam board web dashboard)
      4. Prints this PC's LAN IP and the exact commands to use from the phone.

    Authentication note: Windows OpenSSH authenticates against your Windows user
    account (ynotf) - i.e. your Windows credentials, exactly as required.
    If you sign in with a Microsoft account, the SSH password is your Microsoft
    account password (a PIN will not work over SSH).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\phone\Enable-PhoneControl.ps1
#>

# ---- self-elevate -----------------------------------------------------------
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
           ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Requesting administrator rights (UAC)..."
    Start-Process powershell.exe -Verb RunAs -Wait -ArgumentList @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    )
    return
}

$ErrorActionPreference = 'Stop'

# ---- 1. OpenSSH Server --------------------------------------------------------
$cap = Get-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0'
if ($cap.State -ne 'Installed') {
    Write-Host "Installing OpenSSH Server (optional feature)..."
    Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
} else {
    Write-Host "OpenSSH Server already installed."
}

# ---- 2. Service ---------------------------------------------------------------
Set-Service -Name sshd -StartupType Automatic
Start-Service sshd -ErrorAction SilentlyContinue
Write-Host ("sshd: {0} (startup: {1})" -f (Get-Service sshd).Status, (Get-Service sshd).StartType)

# ---- 3. Firewall (local subnet only) ------------------------------------------
foreach ($rule in @(
    @{ Name = 'ClawTeam SSH (phone control)'; Port = 22 },
    @{ Name = 'ClawTeam Board (phone dashboard)'; Port = 8788 }
)) {
    $existing = Get-NetFirewallRule -DisplayName $rule.Name -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName $rule.Name -Direction Inbound -Action Allow `
            -Protocol TCP -LocalPort $rule.Port -RemoteAddress LocalSubnet | Out-Null
        Write-Host "Firewall rule added: $($rule.Name) (TCP $($rule.Port), local subnet)"
    } else {
        Write-Host "Firewall rule exists: $($rule.Name)"
    }
}

# ---- 4. Phone instructions -----------------------------------------------------
$ip = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.InterfaceAlias -notmatch 'Loopback|vEthernet|WSL|Hyper-V' -and $_.IPAddress -notmatch '^169\.254' } |
    Select-Object -First 1).IPAddress
$user = $env:USERNAME

Write-Host ""
Write-Host "================ PHONE CONTROL READY ================" -ForegroundColor Cyan
Write-Host "From the phone (any SSH client / anyclaw shell skill):"
Write-Host "  ssh $user@$ip        (password = your Windows account password)"
Write-Host ""
Write-Host "Then run the swarm control menu:"
Write-Host "  D:\github\ClawTeam\scripts\phone\swarm.cmd status"
Write-Host "  D:\github\ClawTeam\scripts\phone\swarm.cmd start -Goal `"<goal>`""
Write-Host "  D:\github\ClawTeam\scripts\phone\swarm.cmd stop"
Write-Host ""
Write-Host "Dashboard from the phone browser (once board started with -External):"
Write-Host "  http://${ip}:8788"
Write-Host "=====================================================" -ForegroundColor Cyan
