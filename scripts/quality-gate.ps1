param()
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

# ── Python server ─────────────────────────────────────────────────────────────
Write-Host '--- Installing dependencies ---' -ForegroundColor Cyan
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host 'ERROR: uv is not available on PATH.' -ForegroundColor Red
    Write-Host 'Install uv: https://docs.astral.sh/uv/getting-started/installation/' -ForegroundColor Red
    exit 1
}

& uv sync --extra dev
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '--- Ruff lint (E/F/W/I/N/T20) ---' -ForegroundColor Cyan
& uv run ruff check controldesk_mcp tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '--- Ruff format check ---' -ForegroundColor Cyan
& uv run ruff format --check controldesk_mcp tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ── MCP tool decorator validation ─────────────────────────────────────────────
# Rule: Every @mcp.tool() MUST have name=, description=, and annotations=
Write-Host '--- MCP tool decorators ---' -ForegroundColor Cyan
& uv run python scripts/validate_mcp_tools.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ── Layer boundary enforcement ────────────────────────────────────────────────
# Rule: controldesk_mcp/server/ and controldesk_mcp/tools/ must NEVER import com_bridge internals
# directly. Only controldesk_mcp.com_bridge.dispatch is permitted.
Write-Host '--- Layering check ---' -ForegroundColor Cyan
& .\scripts\check_layer_boundaries.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ── Tests ─────────────────────────────────────────────────────────────────────
Write-Host '--- Pytest ---' -ForegroundColor Cyan
& uv run pytest tests/unit/ -q -m 'not integration'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Quality gate passed.' -ForegroundColor Green
