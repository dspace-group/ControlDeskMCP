<#
.SYNOPSIS
    Run the ControlDesk MCP server in HTTP (streamable-http) transport mode.

.DESCRIPTION
    Starts the server bound to a configurable host and port using the
    streamable-http transport.  Use this when connecting from a remote
    machine (e.g. a developer's laptop) to a ControlDesk VM.

    Default host is 0.0.0.0 (all interfaces) so remote clients can reach
    the server.  For local-only HTTP testing use -Host 127.0.0.1.

    The MCP endpoint will be:  http://<host>:<port>/mcp

    SECURITY NOTE
    -------------
    No authentication is configured.  When binding to 0.0.0.0, restrict
    access via Windows Firewall or a network policy.  The script prints the
    firewall command needed to open the port.

.PARAMETER BindHost
    IP address to bind to.
    '0.0.0.0' (default) accepts connections from all network interfaces.
    '127.0.0.1' restricts to local connections only.

.PARAMETER Port
    TCP port to listen on.  Default: 8000.

.PARAMETER LogLevel
    Server log level: DEBUG | INFO | WARNING | ERROR.  Default: INFO.

.PARAMETER DevMode
    When specified, launches via 'python -m sources' (source tree) instead
    of the installed controldesk-mcp executable.  Useful during development.

.EXAMPLE
    # Remote access — bind to all interfaces (default)
    ./scripts/serve-http.ps1

.EXAMPLE
    # Local HTTP only
    ./scripts/serve-http.ps1 -BindHost 127.0.0.1

.EXAMPLE
    # Custom port, debug logging
    ./scripts/serve-http.ps1 -Port 9000 -LogLevel DEBUG

.EXAMPLE
    # Development mode (run from source tree, no wheel needed)
    ./scripts/serve-http.ps1 -DevMode
#>
param(
    [string]$BindHost = "0.0.0.0",

    [ValidateRange(1, 65535)]
    [int]$Port = 8000,

    [ValidateSet("DEBUG", "INFO", "WARNING", "ERROR")]
    [string]$LogLevel = "INFO",

    [switch]$DevMode
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

Write-Host ""
Write-Host "=== ControlDesk MCP Server — HTTP Transport ===" -ForegroundColor Cyan
Write-Host ""

# ── Resolve launcher ─────────────────────────────────────────────────────────
if ($DevMode) {
    # Dev mode: use local source tree
    $pythonVersion = python --version 2>&1
    Write-Host "Mode   : development (python -m sources)"
    Write-Host "Python : $pythonVersion"

    $installed = pip show controldesk-mcp-server 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Dev dependencies not installed — running pip install -e .[dev] ..." -ForegroundColor Yellow
        pip install -e .[dev]
    }
    $env:PYTHONPATH = (Get-Location).Path
    $launcher = { python -m sources }
}
else {
    # Installed wheel: prefer venv exe, fall back to PATH
    $venvExe = "C:\tools\controldesk-mcp-venv\Scripts\controldesk-mcp.exe"
    $pathExe  = (Get-Command controldesk-mcp -ErrorAction SilentlyContinue)?.Source

    if (Test-Path $venvExe) {
        $exePath = $venvExe
    }
    elseif ($pathExe) {
        $exePath = $pathExe
    }
    else {
        Write-Host "ERROR: controldesk-mcp executable not found." -ForegroundColor Red
        Write-Host "       Install the wheel first:  .\scripts\build\install-wheel.ps1" -ForegroundColor Red
        Write-Host "       Or run in dev mode:       .\scripts\serve-http.ps1 -DevMode" -ForegroundColor Red
        Write-Host ""
        exit 1
    }

    Write-Host "Mode : installed wheel"
    Write-Host "Exe  : $exePath"
    $launcher = { & $exePath }
}

# ── Environment variables ────────────────────────────────────────────────────
$env:MCP_TRANSPORT = "streamable-http"
$env:MCP_HOST      = $BindHost
$env:MCP_PORT      = "$Port"
$env:LOG_LEVEL     = $LogLevel

# ── Startup info ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Bind host  : $BindHost"
Write-Host "Port       : $Port"
Write-Host "Log level  : $LogLevel"
Write-Host ""
Write-Host "MCP endpoint: http://$($BindHost -eq '0.0.0.0' ? '<this-machine-ip>' : $BindHost):$Port/mcp" -ForegroundColor Green
Write-Host ""

if ($BindHost -eq "0.0.0.0") {
    Write-Host "SECURITY: Server is accessible from all network interfaces." -ForegroundColor Yellow
    Write-Host "          No authentication is configured."  -ForegroundColor Yellow
    Write-Host "          To open Windows Firewall for port $Port, run once (as Administrator):" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  New-NetFirewallRule -DisplayName 'ControlDesk MCP HTTP' ``" -ForegroundColor DarkYellow
    Write-Host "      -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow" -ForegroundColor DarkYellow
    Write-Host ""
}

Write-Host "Starting server — press Ctrl+C to stop." -ForegroundColor Green
Write-Host ""

# ── Launch ───────────────────────────────────────────────────────────────────
& $launcher
