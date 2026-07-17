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

Write-Host "=== ControlDesk MCP Server — Debug Mode ===" -ForegroundColor Cyan
Write-Host ""

# ── Environment checks ───────────────────────────────────────────────────────
$pythonVersion = python --version 2>&1
Write-Host "Python : $pythonVersion"

Ensure-PythonDependencies

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
    python -m sources --transport streamable-http
}
else {
    python -m sources
}
