<#
.SYNOPSIS
    One-time developer setup for the ControlDesk MCP Server repository.

.DESCRIPTION
    Run this script once after cloning the repository. It will:
      1. Verify Python 3.11+ and uv are available on PATH.
      2. Optionally configure UV_INDEX_URL for restricted networks.
      3. Create/update the project environment with uv.
      4. Install package dependencies including dev tools.

.PARAMETER PipIndexUrl
    Optional package index URL (for example corporate Artifactory).
    Value is mapped to UV_INDEX_URL for this run.

.PARAMETER SkipVenv
    Deprecated and ignored. uv manages the project virtual environment.

.PARAMETER SkipTests
    Deprecated and ignored. Setup no longer runs tests.

.EXAMPLE
    .\scripts\setup.ps1

.EXAMPLE
    .\scripts\setup.ps1 -PipIndexUrl "https://artifactory.example.com/api/pypi/pypi-remote/simple"

.EXAMPLE
    .\scripts\setup.ps1 -SkipTests
    (Accepted for backward compatibility; no effect.)
#>

param(
    [string]$PipIndexUrl = "",
    [switch]$SkipVenv,
    [switch]$SkipTests,
    [switch]$Help
)

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

function Refresh-PathFromRegistry {
    $machinePath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
    $userPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
    if ($machinePath -or $userPath) {
        $env:Path = ($machinePath, $userPath -join ';').Trim(';')
    }
}

function Add-ToPathIfExists {
    param([string]$Directory)

    if ($Directory -and (Test-Path $Directory) -and $env:Path -notlike "*$Directory*") {
        $env:Path = "$Directory;$env:Path"
    }
}

function Resolve-UvCommand {
    $uvCommand = Get-Command uv -ErrorAction SilentlyContinue
    if ($uvCommand) {
        return $uvCommand
    }

    # Common install locations for uv on Windows (winget and user-level installs).
    $candidateDirectories = @(
        (Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links'),
        (Join-Path $env:USERPROFILE '.local\bin')
    )

    $userBase = python -c "import site; print(site.USER_BASE)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $userBase) {
        $candidateDirectories += (Join-Path $userBase 'Scripts')
    }

    foreach ($directory in $candidateDirectories) {
        Add-ToPathIfExists -Directory $directory
    }

    return (Get-Command uv -ErrorAction SilentlyContinue)
}

function Install-UvWithPip {
    Write-Host "  Attempting user-level install with python -m pip ..." -ForegroundColor Yellow
    python -m pip install --user uv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to install uv with pip (exit $LASTEXITCODE)." -ForegroundColor Red
        return $false
    }

    $userBase = python -c "import site; print(site.USER_BASE)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $userBase) {
        Add-ToPathIfExists -Directory (Join-Path $userBase 'Scripts')
    }

    return $true
}

function Ensure-UvInstalled {
    if (Resolve-UvCommand) {
        return
    }

    Write-Host "  uv not found on PATH - attempting installation..." -ForegroundColor Yellow

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  Trying winget install for uv..." -ForegroundColor Gray
        winget install --id=astral-sh.uv -e --source winget --silent
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  winget install failed (exit $LASTEXITCODE)." -ForegroundColor Yellow
            Write-Host "  Falling back to python -m pip install --user uv ..." -ForegroundColor Yellow
            if (-not (Install-UvWithPip)) {
                Write-Host "Install uv manually: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Red
                exit 1
            }
        }
    }
    else {
        Write-Host "  winget is unavailable; falling back to python -m pip install --user uv ..." -ForegroundColor Yellow
        if (-not (Install-UvWithPip)) {
            Write-Host "Install uv manually: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Red
            exit 1
        }
    }

    # Installers often update PATH for new shells only; refresh for this process.
    Refresh-PathFromRegistry

    if (-not (Resolve-UvCommand)) {
        Write-Host "ERROR: uv was installed but is still not resolvable on PATH." -ForegroundColor Red
        Write-Host "Close and reopen VS Code, then rerun setup." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "=== ControlDesk MCP Server - Developer Setup ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: Verify Python 3.11+
Write-Host "Step 1/4  Checking Python version ..." -ForegroundColor White
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python 3.11+ is required and must be on PATH." -ForegroundColor Red
    exit 1
}

if ($pythonVersion -match '^Python\s+(\d+)\.(\d+)') {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
    if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
        Write-Host "ERROR: Python 3.11+ is required. Found: $pythonVersion" -ForegroundColor Red
        exit 1
    }
}
Write-Host "  OK  $pythonVersion" -ForegroundColor Green
Write-Host ""

# Step 2: Verify uv and optional index override
Write-Host "Step 2/4  Checking uv ..." -ForegroundColor White
Ensure-UvInstalled
Write-Host "  OK  $(uv --version 2>&1)" -ForegroundColor Green

if ($PipIndexUrl -ne "") {
    $env:UV_INDEX_URL = $PipIndexUrl
    Write-Host "  UV_INDEX_URL = $PipIndexUrl" -ForegroundColor Yellow
}
elseif ($env:UV_INDEX_URL) {
    Write-Host "  UV_INDEX_URL = $($env:UV_INDEX_URL)" -ForegroundColor Gray
}
Write-Host ""

# Step 3: uv-managed environment
Write-Host "Step 3/4  Preparing uv project environment ..." -ForegroundColor White
if ($SkipVenv) {
    Write-Host "  NOTE: -SkipVenv is deprecated and ignored in uv mode." -ForegroundColor Yellow
}
Write-Host "  uv manages the local .venv automatically." -ForegroundColor Gray
Write-Host ""

# Step 4: Install dependencies
Write-Host "Step 4/4  Installing dependencies with uv ..." -ForegroundColor White
Write-Host "          (uv sync --extra dev)" -ForegroundColor Gray
uv sync --extra dev
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: uv sync failed (exit $LASTEXITCODE)." -ForegroundColor Red
    Write-Host "If needed, pass -PipIndexUrl with your internal package index." -ForegroundColor Yellow
    exit 1
}
Write-Host "  Installed." -ForegroundColor Green
Write-Host ""

if ($SkipTests) {
    Write-Host "  NOTE: -SkipTests is deprecated and ignored; setup no longer runs tests." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    uv run python -m controldesk_mcp   # start the MCP server (stdio)" -ForegroundColor Gray
Write-Host "    .\scripts\quality-gate.ps1 # lint + format + tests" -ForegroundColor Gray
Write-Host "    .\scripts\inspect.ps1      # MCP Inspector UI (browser)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Build a wheel for distribution:" -ForegroundColor White
Write-Host "    .\scripts\build\build-wheel.ps1" -ForegroundColor Gray
