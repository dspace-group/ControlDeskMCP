<#
.SYNOPSIS
    Kill any running ControlDesk MCP server process and restart it.

.DESCRIPTION
    Finds Python processes running `sources` (the MCP server module), terminates
    them, then relaunches the server in the background. Useful after editing any
    file under sources/ that requires a live server reload.

.PARAMETER Transport
    MCP transport to use. Defaults to 'stdio'. Set to 'http' for SSE/HTTP.

.EXAMPLE
    ./scripts/restart-mcp.ps1
    ./scripts/restart-mcp.ps1 -Transport http
#>
param(
    [ValidateSet("stdio", "http")]
    [string]$Transport = "stdio"
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

function Test-CriticalPythonModules {
    python -c "import pydantic, mcp" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Test-OptionalSettingsModule {
    python -c "import pydantic_settings" 2>$null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-PythonDependencies {
    if (-not (Test-CriticalPythonModules)) {
        Write-Host "Critical Python modules missing — installing runtime dependencies..." -ForegroundColor Yellow
        python -m pip install "pydantic>=2.0" "mcp>=1.6.0"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to install critical runtime dependencies." -ForegroundColor Red
            Write-Host "Run manually: python -m pip install \"pydantic>=2.0\" \"mcp>=1.6.0\"" -ForegroundColor Red
            exit 1
        }
    }

    if (-not (Test-OptionalSettingsModule)) {
        Write-Host "Optional module pydantic-settings missing — attempting install..." -ForegroundColor Yellow
        python -m pip install "pydantic-settings>=2.0"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "WARNING: pydantic-settings install failed; continuing with fallback settings mode." -ForegroundColor Yellow
        }
    }
}

Write-Host "=== ControlDesk MCP Server — Restart ===" -ForegroundColor Cyan
Write-Host ""

# ── Kill running MCP server instances ────────────────────────────────────────
$killed = 0
Get-Process -Name python -ErrorAction SilentlyContinue | ForEach-Object {
    $cmdLine = (Get-WmiObject Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    if ($cmdLine -match "-m sources") {
        Write-Host "Stopping PID $($_.Id) — $cmdLine" -ForegroundColor Yellow
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        $killed++
    }
}

if ($killed -eq 0) {
    Write-Host "No running MCP server found." -ForegroundColor DarkGray
}
else {
    Write-Host "Stopped $killed process(es)." -ForegroundColor Green
    Start-Sleep -Milliseconds 500
}

Write-Host ""

# ── Verify dependencies ───────────────────────────────────────────────────────
Ensure-PythonDependencies

# ── Environment ───────────────────────────────────────────────────────────────
$env:PYTHONPATH = (Get-Location).Path
$env:LOG_LEVEL = "INFO"

Write-Host "Starting MCP server (Transport: $Transport) ..." -ForegroundColor Green
Write-Host "PYTHONPATH : $env:PYTHONPATH"
Write-Host ""
Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

# ── Launch ────────────────────────────────────────────────────────────────────
if ($Transport -eq "http") {
    python -m sources --transport streamable-http
}
else {
    python -m sources
}
