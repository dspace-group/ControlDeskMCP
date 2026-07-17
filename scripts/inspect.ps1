<#
.SYNOPSIS
    Launch the MCP Inspector connected to the ControlDesk MCP server.

.DESCRIPTION
    Checks for Node.js / npx, installs Python dependencies, then starts
    the MCP Inspector (https://github.com/modelcontextprotocol/inspector)
    wired to the server via stdio transport.

    The Inspector opens a browser UI at http://localhost:5173 and lets you
    browse all registered Tools, Resources, and Prompts, send test calls, and
    watch server notifications — without needing a full LLM host.

    The server process is spawned by the Inspector as a child process, so a
    single Ctrl+C stops both.

.NOTES
    Requires Node.js >= 18 (npx) on PATH.
    The first run downloads @modelcontextprotocol/inspector from npm; subsequent
    runs use the npx cache.

.EXAMPLE
    ./scripts/inspect.ps1
#>
param()

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

# ── Prerequisite: Node.js / npx ───────────────────────────────────────────────
if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Host ''
    Write-Host 'ERROR: npx not found on PATH.' -ForegroundColor Red
    Write-Host '       Install Node.js >= 18 from https://nodejs.org and re-run.' -ForegroundColor Red
    Write-Host ''
    exit 1
}

$nodeVersion = node --version 2>&1
Write-Host "Node.js : $nodeVersion"

# ── Python dependencies ───────────────────────────────────────────────────────
Write-Host '--- Ensuring Python dependencies ---' -ForegroundColor Cyan
Ensure-PythonDependencies

# ── Environment ───────────────────────────────────────────────────────────────
$env:PYTHONPATH = (Get-Location).Path
$env:LOG_LEVEL = "INFO"

Write-Host ''
Write-Host '=== ControlDesk MCP — Inspector ===' -ForegroundColor Cyan
Write-Host ''
Write-Host '  UI   : http://localhost:5173' -ForegroundColor Green
Write-Host '  Server : python -m sources  (stdio transport)' -ForegroundColor Green
Write-Host '  PYTHONPATH : ' + $env:PYTHONPATH
Write-Host ''
Write-Host 'The Inspector spawns the server as a child process.' -ForegroundColor Yellow
Write-Host 'Press Ctrl+C to stop both.' -ForegroundColor Yellow
Write-Host ''

# ── Launch ────────────────────────────────────────────────────────────────────
# -y  : auto-confirm the one-time npx package download (no interactive prompt)
npx -y @modelcontextprotocol/inspector python -m sources
