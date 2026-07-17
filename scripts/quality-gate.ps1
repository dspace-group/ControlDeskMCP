param()
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..

# ── Python server ─────────────────────────────────────────────────────────────
Write-Host '--- Installing dependencies ---' -ForegroundColor Cyan
$pythonExe = 'python'
$py312 = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
if ($LASTEXITCODE -eq 0 -and $py312) {
    $pythonExe = $py312.Trim()
}
Write-Host "  Using Python: $pythonExe" -ForegroundColor DarkCyan

& $pythonExe -m pip install --retries 15 --timeout 60 hatchling editables | Out-Null
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$maxAttempts = 3
$attempt = 1
while ($attempt -le $maxAttempts) {
    Write-Host "  Install attempt $attempt/$maxAttempts" -ForegroundColor DarkCyan
    & $pythonExe -m pip install --retries 15 --timeout 60 --no-build-isolation -e '.[dev]' | Out-Null
    if ($LASTEXITCODE -eq 0) {
        break
    }
    if ($attempt -eq $maxAttempts) {
        Write-Host 'Dependency installation failed after multiple attempts.' -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host '  Dependency install failed, retrying...' -ForegroundColor Yellow
    $attempt++
}

Write-Host '--- Ruff lint (E/F/W/I/N/T20) ---' -ForegroundColor Cyan
& $pythonExe -m ruff check sources tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '--- Black format check ---' -ForegroundColor Cyan
& $pythonExe -m black --check sources tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ── MCP tool decorator validation ─────────────────────────────────────────────
# Rule: Every @mcp.tool() MUST have name=, description=, and annotations=
Write-Host '--- MCP tool decorators ---' -ForegroundColor Cyan
& $pythonExe scripts/validate_mcp_tools.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ── Layer boundary enforcement ────────────────────────────────────────────────
# Rule: sources/server/ and sources/tools/ must NEVER import com_bridge internals
# directly. Only sources.com_bridge.dispatch is permitted.
Write-Host '--- Layering check ---' -ForegroundColor Cyan
& .\scripts\check_layer_boundaries.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# ── Tests ─────────────────────────────────────────────────────────────────────
Write-Host '--- Pytest ---' -ForegroundColor Cyan
& $pythonExe -m pytest tests/unit/ -q -m 'not integration'
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host 'Quality gate passed.' -ForegroundColor Green
