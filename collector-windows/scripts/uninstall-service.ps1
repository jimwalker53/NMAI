# NMIA Windows Collector - Service Uninstallation Script
# Usage: Run as Administrator
#   .\uninstall-service.ps1 [-ServiceName "NMIACollector"] [-InstallDir "C:\NMIA\Collector"] [-RemoveFiles]

param(
    [string]$ServiceName = "NMIACollector",
    [string]$InstallDir = "C:\NMIA\Collector",
    [switch]$RemoveFiles = $false
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "=== $Message ===" -ForegroundColor Cyan
}

function Write-Ok {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Write-Err {
    param([string]$Message)
    Write-Host "  [ERROR] $Message" -ForegroundColor Red
}

function Test-Administrator {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Find-NSSM {
    try {
        $nssm = Get-Command nssm -ErrorAction Stop
        return $nssm.Source
    }
    catch {
        $nssmPaths = @(
            "C:\nssm\nssm.exe",
            "C:\Tools\nssm\nssm.exe",
            "$env:ProgramFiles\nssm\nssm.exe"
        )
        foreach ($path in $nssmPaths) {
            if (Test-Path $path) {
                return $path
            }
        }
        return $null
    }
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "NMIA Windows Collector - Service Uninstaller" -ForegroundColor White
Write-Host "==============================================" -ForegroundColor White
Write-Host "  Service Name:  $ServiceName"
Write-Host "  Install Dir:   $InstallDir"
Write-Host "  Remove Files:  $RemoveFiles"
Write-Host ""

# Check for admin privileges
if (-not (Test-Administrator)) {
    Write-Err "This script must be run as Administrator."
    Write-Host "  Right-click PowerShell and select 'Run as Administrator'." -ForegroundColor Yellow
    exit 1
}
Write-Ok "Running as Administrator"

# ---------------------------------------------------------------------------
# Step 1: Stop the service
# ---------------------------------------------------------------------------

Write-Step "Stopping service"

$service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($service) {
    if ($service.Status -eq "Running") {
        try {
            Stop-Service -Name $ServiceName -Force
            Start-Sleep -Seconds 3
            Write-Ok "Service stopped"
        }
        catch {
            Write-Warn "Could not stop service gracefully: $_"
            Write-Host "  Attempting to kill the process..." -ForegroundColor Yellow

            # Try to find and kill the process
            try {
                $wmiService = Get-WmiObject -Class Win32_Service -Filter "Name='$ServiceName'"
                if ($wmiService -and $wmiService.ProcessId -gt 0) {
                    Stop-Process -Id $wmiService.ProcessId -Force -ErrorAction SilentlyContinue
                    Start-Sleep -Seconds 2
                    Write-Ok "Process killed"
                }
            }
            catch {
                Write-Warn "Could not kill process: $_"
            }
        }
    }
    else {
        Write-Ok "Service is not running (Status: $($service.Status))"
    }
}
else {
    Write-Warn "Service '$ServiceName' not found"
}

# ---------------------------------------------------------------------------
# Step 2: Remove the service registration
# ---------------------------------------------------------------------------

Write-Step "Removing service registration"

$nssmPath = Find-NSSM
$serviceExists = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue

if ($serviceExists) {
    if ($nssmPath) {
        Write-Host "  Using NSSM to remove service..." -ForegroundColor Gray
        & $nssmPath remove $ServiceName confirm
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Service removed via NSSM"
        }
        else {
            Write-Warn "NSSM removal failed; trying sc.exe"
            sc.exe delete $ServiceName
            if ($LASTEXITCODE -eq 0) {
                Write-Ok "Service removed via sc.exe"
            }
            else {
                Write-Err "Failed to remove service. Try manually: sc.exe delete $ServiceName"
            }
        }
    }
    else {
        sc.exe delete $ServiceName
        if ($LASTEXITCODE -eq 0) {
            Write-Ok "Service removed via sc.exe"
        }
        else {
            Write-Err "Failed to remove service. Try manually: sc.exe delete $ServiceName"
        }
    }
}
else {
    Write-Ok "Service was not registered (already removed)"
}

# ---------------------------------------------------------------------------
# Step 3: Optionally remove installation files
# ---------------------------------------------------------------------------

if ($RemoveFiles) {
    Write-Step "Removing installation files"

    if (Test-Path $InstallDir) {
        $confirm = Read-Host "  Are you sure you want to delete $InstallDir and all contents? (y/N)"
        if ($confirm -eq "y" -or $confirm -eq "Y") {
            try {
                Remove-Item -Path $InstallDir -Recurse -Force
                Write-Ok "Removed $InstallDir"
            }
            catch {
                Write-Err "Could not remove $InstallDir : $_"
                Write-Host "  Some files may be locked. Try removing manually after reboot." -ForegroundColor Yellow
            }
        }
        else {
            Write-Ok "Skipped file removal (user cancelled)"
        }
    }
    else {
        Write-Ok "Install directory does not exist: $InstallDir"
    }
}
else {
    Write-Host ""
    Write-Host "  Files were NOT removed. To also remove files, run:" -ForegroundColor Yellow
    Write-Host "    .\uninstall-service.ps1 -RemoveFiles" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Or remove manually:" -ForegroundColor Yellow
    Write-Host "    Remove-Item -Path '$InstallDir' -Recurse -Force" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host "  Uninstallation Complete!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""

# Verify service is gone
$finalCheck = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($finalCheck) {
    Write-Warn "Service still appears registered. A reboot may be required."
}
else {
    Write-Ok "Service '$ServiceName' is fully removed"
}

if (Test-Path $InstallDir) {
    Write-Host "  Install directory still exists at: $InstallDir" -ForegroundColor Gray
}

Write-Host ""
