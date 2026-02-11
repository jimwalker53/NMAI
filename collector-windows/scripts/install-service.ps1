# NMIA Windows Collector - Service Installation Script
# Requires: Python 3.11+, pip
# Usage: Run as Administrator
#   .\install-service.ps1 [-ServiceName "NMIACollector"] [-Port 9000] [-InstallDir "C:\NMIA\Collector"]
#
# This script:
#   1. Creates the install directory and copies collector files
#   2. Creates a Python virtual environment and installs the package
#   3. Creates a wrapper batch script for running uvicorn
#   4. Registers and starts the Windows service using sc.exe (or NSSM if available)

param(
    [string]$ServiceName = "NMIACollector",
    [int]$Port = 9000,
    [string]$InstallDir = "C:\NMIA\Collector",
    [string]$NmiaServerUrl = "http://localhost:8000",
    [string]$ConnectorInstanceId = "",
    [string]$PythonPath = ""
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

function Find-Python {
    # If explicit path provided, use it
    if ($PythonPath -and (Test-Path $PythonPath)) {
        return $PythonPath
    }

    # Search common locations
    $candidates = @(
        "python",
        "python3",
        "C:\Python313\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )

    foreach ($candidate in $candidates) {
        try {
            $version = & $candidate --version 2>&1
            if ($version -match "Python 3\.1[1-9]") {
                Write-Ok "Found Python: $candidate ($version)"
                return $candidate
            }
        }
        catch {
            # Not found, try next
        }
    }

    return $null
}

function Find-NSSM {
    try {
        $nssm = Get-Command nssm -ErrorAction Stop
        return $nssm.Source
    }
    catch {
        # Check common install locations
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
Write-Host "NMIA Windows Collector - Service Installer" -ForegroundColor White
Write-Host "============================================" -ForegroundColor White
Write-Host "  Service Name:  $ServiceName"
Write-Host "  Port:          $Port"
Write-Host "  Install Dir:   $InstallDir"
Write-Host "  NMIA Server:   $NmiaServerUrl"
Write-Host ""

# Check for admin privileges
if (-not (Test-Administrator)) {
    Write-Err "This script must be run as Administrator."
    Write-Host "  Right-click PowerShell and select 'Run as Administrator'." -ForegroundColor Yellow
    exit 1
}
Write-Ok "Running as Administrator"

# Check if service already exists
$existingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Warn "Service '$ServiceName' already exists (Status: $($existingService.Status))."
    $confirm = Read-Host "  Do you want to stop and reinstall? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Host "Aborted." -ForegroundColor Yellow
        exit 0
    }

    Write-Step "Stopping existing service"
    try {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        sc.exe delete $ServiceName | Out-Null
        Write-Ok "Existing service removed"
    }
    catch {
        Write-Warn "Could not cleanly remove existing service: $_"
    }
}

# Find Python
Write-Step "Locating Python"
$python = Find-Python
if (-not $python) {
    Write-Err "Python 3.11+ not found. Please install Python and try again."
    Write-Host "  Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# ---------------------------------------------------------------------------
# Step 1: Create install directory and copy files
# ---------------------------------------------------------------------------

Write-Step "Creating install directory"

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Ok "Created $InstallDir"
}
else {
    Write-Ok "Directory already exists: $InstallDir"
}

# Determine source directory (script is in collector-windows/scripts/)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceDir = Split-Path -Parent $scriptDir

Write-Step "Copying collector files"

# Copy pyproject.toml
Copy-Item -Path "$sourceDir\pyproject.toml" -Destination "$InstallDir\pyproject.toml" -Force
Write-Ok "Copied pyproject.toml"

# Copy src directory
$srcDestDir = Join-Path $InstallDir "src"
if (-not (Test-Path $srcDestDir)) {
    New-Item -ItemType Directory -Path $srcDestDir -Force | Out-Null
}
Copy-Item -Path "$sourceDir\src\*" -Destination $srcDestDir -Recurse -Force
Write-Ok "Copied src/ directory"

# Create data directory
$dataDir = Join-Path $InstallDir "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir -Force | Out-Null
    Write-Ok "Created data directory"
}

# ---------------------------------------------------------------------------
# Step 2: Create virtual environment and install dependencies
# ---------------------------------------------------------------------------

Write-Step "Setting up Python virtual environment"

$venvDir = Join-Path $InstallDir "venv"

if (Test-Path $venvDir) {
    Write-Warn "Existing venv found; removing and recreating"
    Remove-Item -Path $venvDir -Recurse -Force
}

& $python -m venv $venvDir
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to create virtual environment"
    exit 1
}
Write-Ok "Created venv at $venvDir"

$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"

Write-Step "Installing collector package"

& $venvPip install --upgrade pip --quiet
& $venvPip install "$InstallDir" --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Err "Failed to install collector package"
    exit 1
}
Write-Ok "Collector package installed"

# ---------------------------------------------------------------------------
# Step 3: Create .env file with configuration
# ---------------------------------------------------------------------------

Write-Step "Creating configuration"

$envFile = Join-Path $InstallDir ".env"
$envContent = @"
# NMIA Windows Collector Configuration
# Generated by install-service.ps1 on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

NMIA_NMIA_SERVER_URL=$NmiaServerUrl
NMIA_CONNECTOR_INSTANCE_ID=$ConnectorInstanceId
NMIA_CERTUTIL_PATH=certutil.exe
NMIA_LOG_LEVEL=INFO
NMIA_DATA_DIR=$dataDir
"@

Set-Content -Path $envFile -Value $envContent -Encoding UTF8
Write-Ok "Created .env at $envFile"

# ---------------------------------------------------------------------------
# Step 4: Create wrapper batch script
# ---------------------------------------------------------------------------

Write-Step "Creating service wrapper script"

$wrapperScript = Join-Path $InstallDir "run-collector.bat"
$uvicornPath = Join-Path $venvDir "Scripts\uvicorn.exe"

$wrapperContent = @"
@echo off
REM NMIA Windows Collector - Service Wrapper
REM This script is executed by the Windows Service Manager

cd /d "$InstallDir"
"$uvicornPath" nmia_collector.main:app --host 0.0.0.0 --port $Port --log-level info
"@

Set-Content -Path $wrapperScript -Value $wrapperContent -Encoding ASCII
Write-Ok "Created wrapper at $wrapperScript"

# ---------------------------------------------------------------------------
# Step 5: Register as Windows service
# ---------------------------------------------------------------------------

Write-Step "Registering Windows service"

$nssmPath = Find-NSSM

if ($nssmPath) {
    # Use NSSM (Non-Sucking Service Manager) - preferred method
    Write-Ok "Found NSSM at $nssmPath"

    & $nssmPath install $ServiceName $wrapperScript
    if ($LASTEXITCODE -ne 0) {
        Write-Err "NSSM install failed"
        exit 1
    }

    # Configure NSSM settings
    & $nssmPath set $ServiceName DisplayName "NMIA Windows Collector"
    & $nssmPath set $ServiceName Description "Collects ADCS certificate inventory and pushes to NMIA platform"
    & $nssmPath set $ServiceName Start SERVICE_AUTO_START
    & $nssmPath set $ServiceName AppDirectory $InstallDir
    & $nssmPath set $ServiceName AppStdout "$dataDir\collector-stdout.log"
    & $nssmPath set $ServiceName AppStderr "$dataDir\collector-stderr.log"
    & $nssmPath set $ServiceName AppRotateFiles 1
    & $nssmPath set $ServiceName AppRotateBytes 10485760

    Write-Ok "Service registered with NSSM"
}
else {
    # Fall back to sc.exe
    Write-Warn "NSSM not found; using sc.exe (NSSM is recommended for better process management)"
    Write-Host "  Download NSSM from: https://nssm.cc/download" -ForegroundColor Yellow

    # sc.exe requires a binary, not a batch file. We create a wrapper using
    # the Python executable directly with the uvicorn module.
    $binPath = "`"$venvPython`" -m uvicorn nmia_collector.main:app --host 0.0.0.0 --port $Port"

    sc.exe create $ServiceName `
        binPath= "$wrapperScript" `
        DisplayName= "NMIA Windows Collector" `
        start= auto

    if ($LASTEXITCODE -ne 0) {
        Write-Err "sc.exe create failed. You may need to install NSSM for reliable service management."
        Write-Host ""
        Write-Host "  Alternative: run manually with:" -ForegroundColor Yellow
        Write-Host "    cd $InstallDir" -ForegroundColor Yellow
        Write-Host "    .\venv\Scripts\uvicorn.exe nmia_collector.main:app --host 0.0.0.0 --port $Port" -ForegroundColor Yellow
        exit 1
    }

    # Set description
    sc.exe description $ServiceName "Collects ADCS certificate inventory and pushes to NMIA platform"

    Write-Ok "Service registered with sc.exe"
}

# ---------------------------------------------------------------------------
# Step 6: Start the service
# ---------------------------------------------------------------------------

Write-Step "Starting service"

try {
    Start-Service -Name $ServiceName
    Start-Sleep -Seconds 3

    $svc = Get-Service -Name $ServiceName
    if ($svc.Status -eq "Running") {
        Write-Ok "Service is running"
    }
    else {
        Write-Warn "Service status: $($svc.Status)"
        Write-Host "  Check logs at: $dataDir" -ForegroundColor Yellow
    }
}
catch {
    Write-Warn "Could not start service automatically: $_"
    Write-Host "  Try starting manually: Start-Service $ServiceName" -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Service Name:    $ServiceName"
Write-Host "  Install Dir:     $InstallDir"
Write-Host "  Listening on:    http://0.0.0.0:$Port"
Write-Host "  Health Check:    http://localhost:$Port/health"
Write-Host "  API Docs:        http://localhost:$Port/docs"
Write-Host "  Config File:     $envFile"
Write-Host "  Logs:            $dataDir"
Write-Host ""
Write-Host "  Quick Test:" -ForegroundColor Cyan
Write-Host "    curl http://localhost:$Port/health"
Write-Host ""
Write-Host "  Trigger Collection:" -ForegroundColor Cyan
Write-Host "    Invoke-RestMethod -Method POST -Uri http://localhost:$Port/collector/v1/adcs/run ``"
Write-Host "      -ContentType 'application/json' -Body '{`"mode`":`"inventory`"}'  "
Write-Host ""
Write-Host "  Manage Service:" -ForegroundColor Cyan
Write-Host "    Stop-Service $ServiceName"
Write-Host "    Start-Service $ServiceName"
Write-Host "    Restart-Service $ServiceName"
Write-Host ""
