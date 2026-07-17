<#
.SYNOPSIS
    One-time developer setup for the ControlDesk MCP Server repository.

.DESCRIPTION
    Run this script once after cloning the repository. It will:
      1. Verify Python 3.11+ is available on PATH.
      2. (Optional) Detect and configure a pip proxy / custom index URL.
      3. Create a virtual environment at .venv\ in the repo root.
      4. Install the package in editable mode with all dev dependencies.
      5. Run smoke tests to confirm the environment is working.

    After this script completes, activate the venv with:
        .\.venv\Scripts\Activate.ps1

.PARAMETER PipIndexUrl
    Optional. Override the pip index URL (e.g. corporate Artifactory proxy).
    When omitted the script checks for an existing .pip\pip.ini. If neither
    is present, standard PyPI (https://pypi.org/simple) is used.

.PARAMETER SkipVenv
    Install directly into the current Python environment instead of creating
    a virtual environment. Use this if you manage envs externally (conda, uv, etc.).

.PARAMETER SkipTests
    Skip the smoke test run at the end. Useful in headless/CI contexts
    where tests are run separately.

.EXAMPLE
    # Standard setup — creates .venv\, installs deps, runs smoke tests
    .\scripts\setup.ps1

    # Corporate network with Artifactory
    .\scripts\setup.ps1 -PipIndexUrl "https://artifactory.example.com/api/pypi/pypi-remote/simple"

    # Use existing environment, skip tests
    .\scripts\setup.ps1 -SkipVenv -SkipTests
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

$repoRoot = (Get-Location).Path
$venvDir = Join-Path $repoRoot '.venv'
$pipIni = Join-Path $repoRoot '.pip\pip.ini'

Write-Host ""
Write-Host "=== ControlDesk MCP Server — Developer Setup ===" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Verify Python 3.11+ ───────────────────────────────────────────────
Write-Host "Step 1/5  Checking Python version ..." -ForegroundColor White

$pythonCmd = $null
foreach ($candidate in @('python', 'python3', 'py')) {
    if (Get-Command $candidate -ErrorAction SilentlyContinue) {
        $pythonCmd = $candidate
        break
    }
}

if (-not $pythonCmd) {
    Write-Host "ERROR: Python is not on PATH. Install Python 3.11+ from https://python.org and re-run." -ForegroundColor Red
    exit 1
}

$versionOutput = & $pythonCmd --version 2>&1
$versionString = ($versionOutput -replace 'Python ', '').Trim()
$parts = $versionString.Split('.')
if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
    Write-Host "ERROR: Python 3.11+ is required. Found: $versionString" -ForegroundColor Red
    exit 1
}

Write-Host "  OK  Python $versionString" -ForegroundColor Green
Write-Host ""

# ── Step 2: Pip configuration ─────────────────────────────────────────────────
Write-Host "Step 2/5  Checking pip configuration ..." -ForegroundColor White

$pipArgs = @()   # extra args appended to every pip call

if ($PipIndexUrl -ne "") {
    # Explicit override — write it into the project pip.ini so this session and
    # all subsequent pip calls in this shell use it. The change will show in
    # git diff; commit it if your whole team uses the same Artifactory instance.
    $pipIniContent = Get-Content $pipIni -Raw
    $pipIniContent = $pipIniContent -replace '(?m)^index-url\s*=.*$', "index-url = $PipIndexUrl"
    Set-Content -Path $pipIni -Value $pipIniContent.TrimEnd() -Encoding UTF8
    Write-Host "  Updated .pip\pip.ini  →  index-url = $PipIndexUrl" -ForegroundColor Yellow
    Write-Host "  (Tip: commit the change if your whole team uses the same proxy.)" -ForegroundColor Gray
}

# Always activate the project-scoped pip config for this session
$env:PIP_CONFIG_FILE = $pipIni
$indexLine = Select-String -Path $pipIni -Pattern '^\s*index-url\s*=' | Select-Object -First 1
Write-Host "  PIP_CONFIG_FILE = .pip\pip.ini" -ForegroundColor Green
if ($indexLine) {
    Write-Host "  $($indexLine.Line.Trim())" -ForegroundColor Gray
}

Write-Host ""

# ── Step 3: Create virtual environment ────────────────────────────────────────
if ($SkipVenv) {
    Write-Host "Step 3/5  Skipping venv creation (-SkipVenv)." -ForegroundColor Gray
    $pip = "pip"
}
else {
    Write-Host "Step 3/5  Creating virtual environment at .venv\ ..." -ForegroundColor White

    if (Test-Path $venvDir) {
        Write-Host "  .venv\ already exists — skipping creation." -ForegroundColor Gray
    }
    else {
        & $pythonCmd -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to create virtual environment." -ForegroundColor Red
            exit 1
        }
        Write-Host "  Created." -ForegroundColor Green
    }

    $pip = Join-Path $venvDir 'Scripts\pip.exe'
    if (-not (Test-Path $pip)) {
        Write-Host "ERROR: pip not found in venv ($pip). Something went wrong with venv creation." -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK  Using pip from .venv\" -ForegroundColor Green
}
Write-Host ""

# ── Step 4: Install package + dev dependencies ────────────────────────────────
Write-Host "Step 4/5  Installing package in editable mode with dev dependencies ..." -ForegroundColor White
Write-Host "          (pip install -e .[dev])" -ForegroundColor Gray
Write-Host ""

$installArgs = @("install", "-e", ".[dev]") + $pipArgs
& $pip @installArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: pip install failed (exit $LASTEXITCODE)." -ForegroundColor Red
    if (-not (Test-Path $pipIni) -or -not (Select-String -Path $pipIni -Pattern 'index-url' -Quiet)) {
        Write-Host ""
        Write-Host "If you are on a restricted network, try:" -ForegroundColor Yellow
        Write-Host "  .\scripts\setup.ps1 -PipIndexUrl `"https://your-proxy/simple`"" -ForegroundColor Yellow
        Write-Host "  Or edit .pip\pip.ini and set index-url to your Artifactory URL." -ForegroundColor Yellow
    }
    exit 1
}

Write-Host ""
Write-Host "  Installed." -ForegroundColor Green
Write-Host ""

# ── Step 5: Smoke tests ────────────────────────────────────────────────────────
if ($SkipTests) {
    Write-Host "Step 5/5  Skipping smoke tests (-SkipTests)." -ForegroundColor Gray
}
else {
    Write-Host "Step 5/5  Running smoke tests (no ControlDesk required) ..." -ForegroundColor White
    Write-Host ""

    $pytest = if ($SkipVenv) { "pytest" } else { Join-Path $venvDir 'Scripts\pytest.exe' }
    & $pytest -q -m "not integration" --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "WARNING: Some tests failed. Review the output above." -ForegroundColor Yellow
        Write-Host "         The environment is installed but may have issues." -ForegroundColor Yellow
    }
    else {
        Write-Host ""
        Write-Host "  All smoke tests passed." -ForegroundColor Green
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

if (-not $SkipVenv) {
    Write-Host "  Activate your environment:" -ForegroundColor White
    Write-Host "    .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    python -m sources          # start the MCP server (stdio)" -ForegroundColor Gray
Write-Host "    .\scripts\quality-gate.ps1 # lint + format + tests" -ForegroundColor Gray
Write-Host "    .\scripts\inspect.ps1      # MCP Inspector UI (browser)" -ForegroundColor Gray
Write-Host ""
Write-Host "  Build a wheel for distribution:" -ForegroundColor White
Write-Host "    .\scripts\build\build-wheel.ps1" -ForegroundColor Gray
Write-Host ""
