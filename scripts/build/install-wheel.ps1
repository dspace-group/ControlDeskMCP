<#
.SYNOPSIS
    Install the ControlDesk MCP Server from a .whl file and verify the setup.

.DESCRIPTION
    - Validates the wheel file exists.
    - Creates an isolated virtual environment (recommended) or installs into
      the current Python environment.
    - Installs the wheel; pip resolves and downloads dependencies (mcp, pydantic,
      pydantic-settings) from PyPI automatically.
    - Verifies the 'controldesk-mcp' entry point is callable.
    - Prints a ready-to-paste mcp.json snippet for VS Code and other clients.

.PARAMETER WheelPath
    Optional path to a .whl file built by scripts/build/build-wheel.ps1.
    If omitted, the script auto-detects a wheel in the same folder as this script.

.PARAMETER VenvDir
    Directory to create the virtual environment in.
    Default: C:\tools\controldesk-mcp-venv
    Pass 'skip' to install into the currently active Python environment (no venv).

.PARAMETER Force
    Recreate the virtual environment from scratch if it already exists.

.EXAMPLE
    # Auto-detect the wheel next to this script
    ./scripts/install-wheel.ps1

    # Standard isolated install with explicit wheel path
    ./scripts/install-wheel.ps1 -WheelPath "C:\share\controldesk_mcp_server-0.1.0-py3-none-any.whl"

    # Custom venv location
    ./scripts/install-wheel.ps1 -WheelPath ".\dist\controldesk_mcp_server-0.1.0-py3-none-any.whl" -VenvDir "C:\envs\cd-mcp"

    # Force clean venv (reinstall)
    ./scripts/install-wheel.ps1 -WheelPath ".\dist\controldesk_mcp_server-0.1.0-py3-none-any.whl" -Force

    # Install into current environment (no venv)
    ./scripts/install-wheel.ps1 -WheelPath ".\dist\controldesk_mcp_server-0.1.0-py3-none-any.whl" -VenvDir skip
#>
param(
    [Parameter(Mandatory = $false, HelpMessage = "Path to the .whl file from build-wheel.ps1")]
    [string]$WheelPath,

    [string]$VenvDir = "C:\tools\controldesk-mcp-venv",

    [string]$PipIndexUrl = "",

    [switch]$Force,
    [switch]$Help
)

$scriptCommand = ".\$([System.IO.Path]::GetFileName($PSCommandPath))"

# ── Display help if requested ────────────────────────────────────────────────
if ($Help) {
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "=== Install ControlDesk MCP Server from Wheel ===" -ForegroundColor Cyan
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "SYNOPSIS" -ForegroundColor Yellow
    Write-Host "  Install the ControlDesk MCP Server from a .whl file and verify setup." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "DESCRIPTION" -ForegroundColor Yellow
    Write-Host "  - Validates the wheel file exists" -ForegroundColor White
    Write-Host "  - Creates an isolated virtual environment (or uses current Python)" -ForegroundColor White
    Write-Host "  - Installs the wheel; pip resolves dependencies automatically" -ForegroundColor White
    Write-Host "  - Verifies the 'controldesk-mcp' entry point is callable" -ForegroundColor White
    Write-Host "  - Prints ready-to-paste mcp.json snippets for VS Code, Claude, Cursor" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "PARAMETERS" -ForegroundColor Yellow
    Write-Host "  -WheelPath <path>" -ForegroundColor Cyan
    Write-Host "    Optional path to the .whl file built by scripts/build/build-wheel.ps1." -ForegroundColor White
    Write-Host "    If omitted, auto-detects a wheel in the same folder as this script." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -VenvDir <path>" -ForegroundColor Cyan
    Write-Host "    Directory for the virtual environment. Default: C:\\tools\\controldesk-mcp-venv" -ForegroundColor White
    Write-Host "    Pass 'skip' to install into the current Python environment." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -PipIndexUrl <url>" -ForegroundColor Cyan
    Write-Host "    Corporate proxy or custom PyPI index URL (e.g., https://artifactory/simple)." -ForegroundColor White
    Write-Host "    If omitted, looks for .pip\\pip.ini; if not found, uses public PyPI." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -Force" -ForegroundColor Cyan
    Write-Host "    Recreate the virtual environment from scratch if it exists." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -Help" -ForegroundColor Cyan
    Write-Host "    Show this help message." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "EXAMPLES" -ForegroundColor Yellow
    Write-Host "  # Auto-detect the wheel next to this script" -ForegroundColor Green
    Write-Host "  $scriptCommand" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Standard isolated install (recommended)" -ForegroundColor Green
    Write-Host "  $scriptCommand -WheelPath `"C:\\share\\controldesk_mcp_server-0.1.0-py3-none-any.whl`"" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # With corporate proxy" -ForegroundColor Green
    Write-Host "  $scriptCommand -PipIndexUrl `"https://artifactory/simple`"" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Custom venv location" -ForegroundColor Green
    Write-Host "  $scriptCommand -VenvDir `"C:\\envs\\cd-mcp`"" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Force clean venv (reinstall)" -ForegroundColor Green
    Write-Host "  $scriptCommand -Force" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Install into current environment (no venv)" -ForegroundColor Green
    Write-Host "  $scriptCommand -VenvDir skip" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    exit 0
}

$ErrorActionPreference = 'Stop'

# ── Resolve wheel path ───────────────────────────────────────────────────────
if (-not $WheelPath) {
    $wheelCandidates = @(Get-ChildItem -Path $PSScriptRoot -Filter "*.whl" -File | Sort-Object LastWriteTime -Descending)

    if ($wheelCandidates.Count -eq 0) {
        Write-Host "ERROR: No wheel file was found and -WheelPath was not provided." -ForegroundColor Red
        Write-Host "" -ForegroundColor Red
        Write-Host "Expected location:" -ForegroundColor Yellow
        Write-Host "  $PSScriptRoot" -ForegroundColor White
        Write-Host "" -ForegroundColor Red
        Write-Host "Usage:" -ForegroundColor Yellow
        Write-Host "  $scriptCommand [-WheelPath <path-to-wheel>]" -ForegroundColor White
        Write-Host "" -ForegroundColor Red
        Write-Host "For help:" -ForegroundColor Yellow
        Write-Host "  $scriptCommand -Help" -ForegroundColor White
        Write-Host "" -ForegroundColor Red
        exit 1
    }

    $WheelPath = $wheelCandidates[0].FullName
    if ($wheelCandidates.Count -gt 1) {
        Write-Host "No -WheelPath specified. Multiple wheels found; using the newest one:" -ForegroundColor Yellow
    }
    else {
        Write-Host "No -WheelPath specified. Auto-detected wheel:" -ForegroundColor Cyan
    }
    Write-Host "  $WheelPath" -ForegroundColor White
    if ($wheelCandidates.Count -gt 1) {
        Write-Host "  Override with -WheelPath to install a different wheel." -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "=== ControlDesk MCP Server — Install ===" -ForegroundColor Cyan
Write-Host ""

# ── Validate wheel path ────────────────────────────────────────────────────────
$WheelPath = [System.IO.Path]::GetFullPath($WheelPath)

if (-not (Test-Path $WheelPath)) {
    Write-Host "ERROR: Wheel file not found:" -ForegroundColor Red
    Write-Host "       $WheelPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Build it first with: ./scripts/build-wheel.ps1" -ForegroundColor Yellow
    exit 1
}

if (-not $WheelPath.EndsWith(".whl")) {
    Write-Host "ERROR: File does not look like a wheel (.whl extension expected):" -ForegroundColor Red
    Write-Host "       $WheelPath" -ForegroundColor Red
    exit 1
}

$wheelName = [System.IO.Path]::GetFileName($WheelPath)
Write-Host "Wheel   : $wheelName" -ForegroundColor White
Write-Host "Python  : $(python --version 2>&1)" -ForegroundColor White

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: uv is not available on PATH." -ForegroundColor Red
    Write-Host "Install uv: https://docs.astral.sh/uv/getting-started/installation/" -ForegroundColor Red
    exit 1
}

# ── Determine installation target ─────────────────────────────────────────────
$useVenv = ($VenvDir -ne "skip" -and $VenvDir -ne "")

if ($useVenv) {
    $VenvDir = [System.IO.Path]::GetFullPath($VenvDir)
    Write-Host "Venv    : $VenvDir" -ForegroundColor White
    Write-Host ""

    # Recreate if -Force is set
    if ((Test-Path $VenvDir) -and $Force) {
        Write-Host "Removing existing virtual environment (-Force) ..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force $VenvDir
    }

    if (-not (Test-Path $VenvDir)) {
        Write-Host "Creating virtual environment ..." -ForegroundColor Cyan
        uv venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host "ERROR: Failed to create virtual environment at $VenvDir" -ForegroundColor Red
            exit 1
        }
        Write-Host "  Created." -ForegroundColor Green
    }
    else {
        Write-Host "Reusing existing virtual environment." -ForegroundColor Yellow
        # Verify pip is functional; the venv may be in a broken state after a
        # failed uninstall (pip.exe present but pip module missing).
        $pipHealthCheck = & (Join-Path $VenvDir "Scripts\pip.exe") --version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  pip is missing or broken — attempting repair with ensurepip ..." -ForegroundColor Yellow
            & uv pip install --python (Join-Path $VenvDir "Scripts\python.exe") pip 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                Write-Host "  Repair failed — recreating virtual environment from scratch ..." -ForegroundColor Yellow
                Remove-Item -Recurse -Force $VenvDir
                uv venv $VenvDir
                if ($LASTEXITCODE -ne 0) {
                    Write-Host "ERROR: Failed to recreate virtual environment at $VenvDir" -ForegroundColor Red
                    exit 1
                }
                Write-Host "  Recreated." -ForegroundColor Green
            }
            else {
                Write-Host "  pip repaired." -ForegroundColor Green
            }
        }
    }

    $pythonExe = Join-Path $VenvDir "Scripts\python.exe"
    $pipExe = Join-Path $VenvDir "Scripts\pip.exe"
    $entryExe = Join-Path $VenvDir "Scripts\controldesk-mcp.exe"

}
else {
    Write-Host "Mode    : current Python environment (no venv)" -ForegroundColor Yellow
    Write-Host ""
    $pythonExe = "python"
    $pipExe = "pip"

    # Resolve where pip will place console scripts
    $scriptsDir = & python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
    $entryExe = Join-Path $scriptsDir "controldesk-mcp.exe"
}

# ── Activate project-scoped pip configuration (for proxy/offline installs) ─────
# Priority: command-line parameter > .pip/pip.ini file > public PyPI
if ($PipIndexUrl -ne "") {
    $env:PIP_INDEX_URL = $PipIndexUrl
    Write-Host "Pip Config  : -PipIndexUrl parameter" -ForegroundColor Green
    Write-Host "  index-url = $PipIndexUrl" -ForegroundColor Gray
}
else {
    # Calculate repo root (script is at scripts/build/install-wheel.ps1, so go up 2 levels)
    $repoRoot = [System.IO.Path]::GetDirectoryName([System.IO.Path]::GetDirectoryName($PSScriptRoot))
    
    # Look for .pip\pip.ini in repo root or next to wheel
    $pipIniCandidates = @(
        (Join-Path $repoRoot '.pip\pip.ini'),                   # Standard location
        (Join-Path ([System.IO.Path]::GetDirectoryName($WheelPath)) '.pip\pip.ini'),  # Next to wheel
        (Join-Path $env:APPDATA 'pip\pip.ini'),                 # User-wide config
        (Join-Path $env:ProgramData 'pip\pip.ini')              # System-wide config
    )

    $pipConfigFound = $false
    foreach ($pipIni in $pipIniCandidates) {
        if (Test-Path $pipIni) {
            $env:PIP_CONFIG_FILE = $pipIni
            Write-Host "Pip Config  : .pip/pip.ini found" -ForegroundColor Green
            $indexLine = Select-String -Path $pipIni -Pattern '^\s*index-url\s*=' | Select-Object -First 1
            if ($indexLine) {
                Write-Host "  $($indexLine.Line.Trim())" -ForegroundColor Gray
            }
            $pipConfigFound = $true
            break
        }
    }

    if (-not $pipConfigFound) {
        Write-Host "Pip Config  : NONE FOUND (using public PyPI)" -ForegroundColor Yellow
        Write-Host "  WARNING: If on a corporate network with restricted internet," -ForegroundColor DarkYellow
        Write-Host "           this installation will likely fail with connection errors." -ForegroundColor DarkYellow
        Write-Host "`n  To fix, either:" -ForegroundColor DarkYellow
        Write-Host "    1. Pass -PipIndexUrl parameter:" -ForegroundColor White
        Write-Host "       .\install-wheel.ps1 -PipIndexUrl `"https://your-proxy/simple`"" -ForegroundColor Gray
        Write-Host "`n    2. Set environment variable before running this script:" -ForegroundColor White
        Write-Host "       `$env:PIP_INDEX_URL = `"https://your-proxy/simple`"" -ForegroundColor Gray
        Write-Host "`n    3. Create .pip\pip.ini with your proxy settings." -ForegroundColor White
        Write-Host ""
    }
}

# ── Install the wheel ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Installing wheel (dependencies will be downloaded from PyPI) ..." -ForegroundColor Cyan
& uv pip install --python $pythonExe "$WheelPath" --upgrade
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: uv pip install failed (exit $LASTEXITCODE)." -ForegroundColor Red
    Write-Host "       Check the output above. If offline, see SETUP.md — Offline Installation." -ForegroundColor Red
    exit 1
}

# ── Verify entry point ────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Verifying entry point ..." -ForegroundColor Cyan

$entryFound = Test-Path $entryExe

if ($entryFound) {
    Write-Host "  Entry point : $entryExe" -ForegroundColor Green

    # Verify the package imports correctly (fast; does NOT start the stdio server)
    $importCheck = & $pythonExe -c "import controldesk_mcp; print('OK')" 2>&1
    if ($importCheck -match 'OK') {
        Write-Host "  Import check: PASSED" -ForegroundColor Green
    }
    else {
        Write-Host "  Import check: WARN — package installed but import returned unexpected output." -ForegroundColor Yellow
        Write-Host "    $importCheck" -ForegroundColor DarkGray
    }
    Write-Host "  Note: Server runs in stdio mode — VS Code/Claude will spawn it automatically." -ForegroundColor DarkGray
}
else {
    Write-Host "  WARNING: Entry point not found at expected path:" -ForegroundColor Yellow
    Write-Host "           $entryExe" -ForegroundColor Yellow

    if (-not $useVenv) {
        Write-Host ""
        Write-Host "  The Python Scripts directory may not be on your PATH." -ForegroundColor Yellow
        Write-Host "  Add it with:" -ForegroundColor Yellow
        $sd = & python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
        Write-Host "    [System.Environment]::SetEnvironmentVariable('PATH', `$env:PATH + ';$sd', 'User')" -ForegroundColor White
    }
}

# ── Build the mcp.json command value ──────────────────────────────────────────
# Use the full path to the venv entry point so clients don't need the venv
# activated. If no venv, use the bare command name (must be on PATH).
if ($useVenv) {
    # Escape backslashes for JSON
    $jsonCommand = $entryExe -replace '\\', '\\'
    $commandNote = "Full path to venv entry point (no PATH activation needed)"
}
else {
    $jsonCommand = "controldesk-mcp"
    $commandNote = "Must be on system PATH"
}

# ── Print mcp.json snippets for each client ───────────────────────────────────
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host "  MCP Client Configuration Snippets" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""
if ($useVenv) {
    Write-Host "IMPORTANT: Copy the FULL PATH from the snippets below into your" -ForegroundColor Red
    Write-Host "           config file. Do NOT replace it with just 'controldesk-mcp'." -ForegroundColor Red
    Write-Host "           VS Code error 'spawn ENOENT' means the bare command" -ForegroundColor Red
    Write-Host "           was used instead of the full venv path." -ForegroundColor Red
    Write-Host ""
}

Write-Host ""
Write-Host "── VS Code (.vscode/mcp.json in any workspace) ─────────────" -ForegroundColor Yellow
Write-Host @"
{
  "servers": {
    "ControlDesk MCP": {
      "command": "$jsonCommand",
      "args": [],
      "type": "stdio",
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
"@ -ForegroundColor White

Write-Host ""
Write-Host "── Claude Desktop (%APPDATA%\Claude\claude_desktop_config.json) ──" -ForegroundColor Yellow
Write-Host @"
{
  "mcpServers": {
    "controldesk": {
      "command": "$jsonCommand",
      "args": [],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
"@ -ForegroundColor White

Write-Host ""
Write-Host "── Cursor (~/.cursor/mcp.json or .cursor/mcp.json) ─────────" -ForegroundColor Yellow
Write-Host @"
{
  "mcpServers": {
    "controldesk": {
      "command": "$jsonCommand",
      "args": [],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
"@ -ForegroundColor White

Write-Host ""
Write-Host "Note: $commandNote" -ForegroundColor DarkGray
Write-Host ""
Write-Host ("=" * 60) -ForegroundColor Cyan

# ── Final summary ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Copy the relevant snippet above into your MCP client config." -ForegroundColor White
Write-Host "  2. Restart your MCP client (VS Code / Claude Desktop / Cursor)." -ForegroundColor White
Write-Host "  3. Call the 'health' tool to confirm the server responds." -ForegroundColor White
Write-Host ""

if ($useVenv -and -not $entryFound) {
    Write-Host "IMPORTANT: The venv was created but the entry point was not confirmed." -ForegroundColor Red
    Write-Host "           Run the install again or check pip output above for errors." -ForegroundColor Red
    Write-Host ""
    exit 1
}
