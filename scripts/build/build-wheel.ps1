<#
.SYNOPSIS
    Build a distributable wheel (.whl) for the ControlDesk MCP Server.

.DESCRIPTION
    Uses hatch to produce a platform-independent Python wheel that can be
    transferred to any Windows machine and installed with
    scripts/build/install-wheel.ps1 (or directly with pip).

    Output: dist\controldesk_mcp_server-<version>-py3-none-any.whl

.PARAMETER OutputDir
    Destination folder for the final wheel file.
    Default: dist\ inside the repo root.
    If a different path is given, the wheel is also copied there after build.

.PARAMETER Clean
    Delete the dist\ folder before building to ensure a fresh artifact.
    Useful when bumping the version to avoid stale wheels.

.EXAMPLE
    # Standard build — wheel lands in dist\
    ./scripts/build-wheel.ps1

    # Clean build, copy to a shared network folder
    ./scripts/build-wheel.ps1 -Clean -OutputDir "\\server\share\wheels"

    # Clean build, copy to Desktop for easy transfer
    ./scripts/build-wheel.ps1 -Clean -OutputDir "$env:USERPROFILE\Desktop"
#>
param(
    [string]$OutputDir = "",
    [switch]$Clean,
    [switch]$Help
)

# ── Display help if requested ────────────────────────────────────────────────
if ($Help) {
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "=== Build Wheel for ControlDesk MCP Server ===" -ForegroundColor Cyan
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "SYNOPSIS" -ForegroundColor Yellow
    Write-Host "  Build a distributable wheel (.whl) for the ControlDesk MCP Server." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "DESCRIPTION" -ForegroundColor Yellow
    Write-Host "  Uses hatch to produce a platform-independent Python wheel that can be" -ForegroundColor White
    Write-Host "  transferred to any Windows machine and installed with install-wheel.ps1" -ForegroundColor White
    Write-Host "  or directly with pip." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  Output: dist\\controldesk_mcp_server-<version>-py3-none-any.whl" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "PARAMETERS" -ForegroundColor Yellow
    Write-Host "  -OutputDir <path>" -ForegroundColor Cyan
    Write-Host "    Destination folder for the wheel file. Default: dist\" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -Clean" -ForegroundColor Cyan
    Write-Host "    Delete dist\ before building (useful when bumping version)." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -Help" -ForegroundColor Cyan
    Write-Host "    Show this help message." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "EXAMPLES" -ForegroundColor Yellow
    Write-Host "  # Standard build — wheel lands in dist\" -ForegroundColor Green
    Write-Host "  .\scripts\build\build-wheel.ps1" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Clean build, copy to a shared network folder" -ForegroundColor Green
    Write-Host "  .\scripts\build\build-wheel.ps1 -Clean -OutputDir `"\\\\server\\share\\wheels`"" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Clean build, copy to Desktop for easy transfer" -ForegroundColor Green
    Write-Host "  .\scripts\build\build-wheel.ps1 -Clean -OutputDir `"`$env:USERPROFILE\\Desktop`"" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    exit 0
}

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..\..

$repoRoot = (Get-Location).Path
$defaultDist = Join-Path $repoRoot "dist"
$targetDir = if ($OutputDir -and $OutputDir -ne "") { $OutputDir } else { $defaultDist }

Write-Host ""
Write-Host "=== ControlDesk MCP Server — Build Wheel ===" -ForegroundColor Cyan
Write-Host ""

# ── Verify we are inside the repo ─────────────────────────────────────────────
if (-not (Test-Path (Join-Path $repoRoot "pyproject.toml"))) {
    Write-Host "ERROR: pyproject.toml not found. Run this script from the repo root." -ForegroundColor Red
    exit 1
}

# ── Activate project-scoped pip configuration ─────────────────────────────────
$pipIni = Join-Path $repoRoot '.pip\pip.ini'
if (Test-Path $pipIni) {
    $env:PIP_CONFIG_FILE = $pipIni
    $indexLine = Select-String -Path $pipIni -Pattern '^\s*index-url\s*=' | Select-Object -First 1
    Write-Host "PIP_CONFIG_FILE = .pip\pip.ini" -ForegroundColor Green
    if ($indexLine) {
        Write-Host "  $($indexLine.Line.Trim())" -ForegroundColor Gray
    }
}

# ── Ensure build frontend is installed ────────────────────────────────────────
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: uv is required to build this project." -ForegroundColor Red
    exit 1
}

Write-Host "Python  : $(python --version 2>&1)"
Write-Host "Repo    : $repoRoot"
Write-Host ""

# ── Optional: clean dist\ before build ────────────────────────────────────────
if ($Clean -and (Test-Path $defaultDist)) {
    Write-Host "Cleaning dist\ ..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $defaultDist
    Write-Host "  Cleaned." -ForegroundColor Green
    Write-Host ""
}

# ── Run python -m build --wheel ───────────────────────────────────────────────
Write-Host "Building wheel ..." -ForegroundColor Cyan
uv run --with build python -m build --wheel --outdir $defaultDist
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: 'uv run --with build python -m build' failed (exit $LASTEXITCODE)." -ForegroundColor Red
    Write-Host "       Check pyproject.toml and the output above for details." -ForegroundColor Red
    exit 1
}

# ── Locate the built wheel ────────────────────────────────────────────────────
$wheel = Get-ChildItem -Path $defaultDist -Filter "*.whl" -ErrorAction SilentlyContinue |
Sort-Object LastWriteTime -Descending |
Select-Object -First 1

if (-not $wheel) {
    Write-Host "ERROR: No .whl file found in $defaultDist after build." -ForegroundColor Red
    exit 1
}

# ── Copy to a custom output directory if requested ────────────────────────────
$finalPath = $wheel.FullName

if ($OutputDir -and $OutputDir -ne "" -and
    ([System.IO.Path]::GetFullPath($OutputDir) -ne [System.IO.Path]::GetFullPath($defaultDist))) {

    if (-not (Test-Path $targetDir)) {
        Write-Host "Creating output directory: $targetDir" -ForegroundColor Yellow
        New-Item -ItemType Directory -Path $targetDir | Out-Null
    }

    Copy-Item $wheel.FullName -Destination $targetDir -Force
    $finalPath = Join-Path $targetDir $wheel.Name
    Write-Host "Wheel copied to: $finalPath" -ForegroundColor Green
}

# ── Generate README.md in dist folder ─────────────────────────────────────────
Write-Host ""
Write-Host "Generating README.md ..." -ForegroundColor Cyan

$bundledPipBullet = ""
$bundledPipNote = ""
if (Test-Path $pipIni) {
    $bundledPipBullet = "- **.pip\\pip.ini** — Optional bundled pip configuration for proxy / Artifactory installs"
    $bundledPipNote = @"

If this package includes `.pip\pip.ini`, `install-wheel.ps1` will use it automatically.
"@
}

$readmeContent = @"
# ControlDesk MCP Server Installation

This folder contains everything needed to install the ControlDesk MCP Server.

## Contents

- **controldesk_mcp_server-0.1.0-py3-none-any.whl** — The installable package
- **install-wheel.ps1** — Automated installation script (recommended)
- **README.md** — This file
$bundledPipBullet

## Quick Start (Recommended)

### 1. Run the Installation Script

``````powershell
.\install-wheel.ps1
``````

The script will:
- Create a clean virtual environment
- Install the wheel and all dependencies
- Verify the installation
- Print MCP client configuration snippets

### 2. Configure Your MCP Client

Copy the path from the script output into your MCP client config:

**VS Code** (`.vscode/mcp.json`):
```json
{
  "servers": {
    "ControlDesk MCP": {
      "command": "C:\\tools\\controldesk-mcp-venv\\Scripts\\controldesk-mcp.exe",
      "args": [],
      "type": "stdio"
    }
  }
}
```

**Claude Desktop** (`%APPDATA%\Claude\claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "controldesk": {
      "command": "C:\\tools\\controldesk-mcp-venv\\Scripts\\controldesk-mcp.exe"
    }
  }
}
```

**Cursor** (`~/.cursor/mcp.json` or `.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "controldesk": {
      "command": "C:\\tools\\controldesk-mcp-venv\\Scripts\\controldesk-mcp.exe"
    }
  }
}
```

> **Important:** Use the **full path** from the install script output, not just `controldesk-mcp`.

---

## Corporate Proxy / Network Issues

If you see connection errors like `Max retries exceeded ... ConnectionResetError`:

``````powershell
.\install-wheel.ps1 ``
  -PipIndexUrl "https://your-artifactory.company.com/artifactory/api/pypi/pypi-remote/simple"
``````

**Or set the environment variable first:**

``````powershell
`$env:PIP_INDEX_URL = "https://your-proxy/simple"
.\install-wheel.ps1
``````
$bundledPipNote

**Alternative PyPI mirrors:**
- Aliyun: `https://mirrors.aliyun.com/pypi/simple/`
- Tsinghua: `https://pypi.tuna.tsinghua.edu.cn/simple`
- Official: `https://pypi.org/simple/`

---

## System Requirements

- Python 3.11 or later (check with `python --version`)
- Windows 10 / 11 / Server 2019+
- Internet connectivity (to download dependencies)

---

## Manual Installation (If Script Unavailable)

``````powershell
# Create virtual environment
uv venv controldesk-mcp-venv

# Install
uv pip install --python .\controldesk-mcp-venv\Scripts\python.exe .\controldesk_mcp_server-0.1.0-py3-none-any.whl
``````

For corporate proxy:
``````powershell
`$env:PIP_INDEX_URL = "https://your-proxy/simple"
uv pip install --python .\controldesk-mcp-venv\Scripts\python.exe .\controldesk_mcp_server-0.1.0-py3-none-any.whl
``````

---

## Troubleshooting

### "Connection aborted" errors
→ See **Corporate Proxy** section above

### "Entry point not found"
→ Run installer again with `-Force` flag:
``````powershell
.\install-wheel.ps1 -Force
``````

### "spawn ENOENT" in VS Code
→ You used the bare command name instead of the full path in your config.
Replace `"command": "controldesk-mcp"` with the **full path** from install script output.

### "ModuleNotFoundError: No module named 'sources'"
→ Installation failed. Re-run with `-Force` and check output for errors:
``````powershell
.\install-wheel.ps1 -Force
``````

---

## Advanced Options

### Custom Virtual Environment Location

``````powershell
.\install-wheel.ps1 ``
  -VenvDir "C:\CustomPath\controldesk-mcp"
``````

### Install Into Current Python (No Virtual Environment)

``````powershell
uv pip install --python python .\controldesk_mcp_server-0.1.0-py3-none-any.whl --user
``````

> ⚠️ Not recommended — using a virtual environment is safer.

---

## Verification

Test the installation:

``````powershell
# Check entry point
C:\tools\controldesk-mcp-venv\Scripts\controldesk-mcp.exe --help

# Or test import
python -c "import sources; print('OK')"
``````

---

## Uninstalling

``````powershell
# Remove virtual environment
Remove-Item -Recurse -Force "C:\tools\controldesk-mcp-venv"

# Remove from MCP client configs
# (edit .vscode/mcp.json, claude_desktop_config.json, etc.)
``````

---

**Generated:** $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@

$readmePath = Join-Path $defaultDist "README.md"
Set-Content -Path $readmePath -Value $readmeContent -Encoding UTF8
Write-Host "  Generated: README.md" -ForegroundColor Green

# ── Copy install script to dist ───────────────────────────────────────────────
$installScriptSource = Join-Path $repoRoot "scripts\build\install-wheel.ps1"
if (Test-Path $installScriptSource) {
    Copy-Item $installScriptSource -Destination $defaultDist -Force
    Write-Host "  Copied: install-wheel.ps1" -ForegroundColor Green
}

if (Test-Path $pipIni) {
    $distPipDir = Join-Path $defaultDist ".pip"
    if (-not (Test-Path $distPipDir)) {
        New-Item -ItemType Directory -Path $distPipDir | Out-Null
    }

    Copy-Item $pipIni -Destination (Join-Path $distPipDir "pip.ini") -Force
    Write-Host "  Copied: .pip\pip.ini" -ForegroundColor Green
}

# ── Copy to custom output directory if requested ───────────────────────────────
if ($OutputDir -and $OutputDir -ne "" -and
    ([System.IO.Path]::GetFullPath($OutputDir) -ne [System.IO.Path]::GetFullPath($defaultDist))) {
    
    Write-Host ""
    Write-Host "Copying to output directory: $targetDir" -ForegroundColor Cyan
    
    @($readmePath, (Join-Path $defaultDist "install-wheel.ps1")) | ForEach-Object {
        if (Test-Path $_) {
            Copy-Item $_ -Destination $targetDir -Force
            $fileName = [System.IO.Path]::GetFileName($_)
            Write-Host "  Copied: $fileName" -ForegroundColor Green
        }
    }

    if (Test-Path $pipIni) {
        $targetPipDir = Join-Path $targetDir ".pip"
        if (-not (Test-Path $targetPipDir)) {
            New-Item -ItemType Directory -Path $targetPipDir | Out-Null
        }

        Copy-Item $pipIni -Destination (Join-Path $targetPipDir "pip.ini") -Force
        Write-Host "  Copied: .pip\pip.ini" -ForegroundColor Green
    }
}

# ── Summary ───────────────────────────────────────────────────────────────────
$size = "{0:N0} KB" -f ($wheel.Length / 1KB)

Write-Host ""
Write-Host "Build complete." -ForegroundColor Green
Write-Host ""
Write-Host "  Output folder: $defaultDist" -ForegroundColor White
Write-Host ""
Write-Host "Generated artifacts:" -ForegroundColor Yellow
Write-Host "  ✓ controldesk_mcp_server-0.1.0-py3-none-any.whl" -ForegroundColor Green
Write-Host "  ✓ README.md                          (installation guide)" -ForegroundColor Green
Write-Host "  ✓ install-wheel.ps1                  (automated installer)" -ForegroundColor Green
if (Test-Path $pipIni) {
    Write-Host "  ✓ .pip\pip.ini                      (bundled pip configuration)" -ForegroundColor Green
}
Write-Host ""
Write-Host "Distribution:" -ForegroundColor Yellow
Write-Host "  1. Share the entire dist\ folder with end users" -ForegroundColor White
if (Test-Path $pipIni) {
    Write-Host "     including the .pip\ folder." -ForegroundColor White
}
else {
    Write-Host "     or all three files listed above." -ForegroundColor White
}
Write-Host "  2. Users read README.md for instructions" -ForegroundColor White
Write-Host "  3. Users run: .\install-wheel.ps1" -ForegroundColor White
Write-Host ""
