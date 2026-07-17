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
Ensure-UvEnvironment

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
    uv run python -m sources --transport streamable-http
}
else {
    uv run python -m sources
}
