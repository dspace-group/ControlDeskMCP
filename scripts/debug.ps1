<#
.SYNOPSIS
    Run the ControlDesk MCP server in debug mode with verbose logging.

.DESCRIPTION
    Installs dependencies if needed, then launches the server with
    DEBUG-level logging so you can trace MCP messages and COM calls
    in the terminal. Useful for local development; not for production.

.PARAMETER Transport
    MCP transport to use. Defaults to 'stdio'. Set to 'http' when
    connecting via SSE/Streamable-HTTP instead.

.EXAMPLE
    ./scripts/debug.ps1
    ./scripts/debug.ps1 -Transport http
#>
param(
    [ValidateSet("stdio", "http")]
    [string]$Transport = "stdio"
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

function Ensure-UvEnvironment {
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "ERROR: uv is not available on PATH." -ForegroundColor Red
        Write-Host "Install uv: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Red
        exit 1
    }

    Write-Host "Ensuring uv project environment..." -ForegroundColor Yellow
    uv sync
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: uv sync failed." -ForegroundColor Red
        exit 1
    }
}

Write-Host "=== ControlDesk MCP Server — Debug Mode ===" -ForegroundColor Cyan
Write-Host ""

# ── Environment checks ───────────────────────────────────────────────────────
Ensure-UvEnvironment
$pythonVersion = uv run python --version 2>&1
Write-Host "Python : $pythonVersion"

# ── Debug environment variables ──────────────────────────────────────────────
$env:PYTHONPATH = (Get-Location).Path
$env:LOG_LEVEL = "DEBUG"
$env:MCP_DEBUG = "1"

Write-Host ""
Write-Host "PYTHONPATH : $env:PYTHONPATH"
Write-Host "LOG_LEVEL  : $env:LOG_LEVEL"
Write-Host "Transport  : $Transport"
Write-Host ""
Write-Host "Starting server — press Ctrl+C to stop." -ForegroundColor Green
Write-Host ""

# ── Launch ───────────────────────────────────────────────────────────────────
if ($Transport -eq "http") {
    uv run python -m sources --transport streamable-http
}
else {
    uv run python -m sources
}
