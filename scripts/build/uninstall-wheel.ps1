<#
.SYNOPSIS
    Uninstall the ControlDesk MCP Server and verify removal.

.DESCRIPTION
    - Removes the package from pip (or venv).
    - Deletes the virtual environment directory (if used).
    - Verifies that 'controldesk-mcp' is no longer callable.
    - Optionally removes client configuration files (mcp.json, claude_desktop_config.json).

.PARAMETER VenvDir
    Directory where the virtual environment was created.
    Default: C:\tools\controldesk-mcp-venv
    Pass 'current' to uninstall from the currently active Python environment.

.PARAMETER RemoveConfigs
    If set, also remove MCP client configuration files:
    - .vscode\mcp.json (VS Code, current workspace only)
    - %APPDATA%\Claude\claude_desktop_config.json (Claude Desktop)
    - %USERPROFILE%\.cursor\mcp.json (Cursor global config)
    
    Use with caution — this may affect other MCP servers if they are configured.

.PARAMETER Verbose
    Show detailed removal steps and final verification output.

.EXAMPLE
    # Standard uninstall (remove venv but keep configs)
    ./scripts/build/uninstall-wheel.ps1

    # Uninstall from current Python environment (no venv to delete)
    ./scripts/build/uninstall-wheel.ps1 -VenvDir current

    # Uninstall everything including client configs (use with caution)
    ./scripts/build/uninstall-wheel.ps1 -RemoveConfigs

    # Custom venv location
    ./scripts/build/uninstall-wheel.ps1 -VenvDir "C:\envs\cd-mcp"

    # Clean uninstall with full reporting
    ./scripts/build/uninstall-wheel.ps1 -RemoveConfigs -Verbose
#>
param(
    [string]$VenvDir = "C:\tools\controldesk-mcp-venv",

    [switch]$RemoveConfigs,

    [switch]$Verbose,
    [switch]$Help
)

# ── Display help if requested ────────────────────────────────────────────────
if ($Help) {
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "=== Uninstall ControlDesk MCP Server ===" -ForegroundColor Cyan
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "SYNOPSIS" -ForegroundColor Yellow
    Write-Host "  Uninstall the ControlDesk MCP Server and verify removal." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "DESCRIPTION" -ForegroundColor Yellow
    Write-Host "  - Removes the package from pip (or venv)" -ForegroundColor White
    Write-Host "  - Deletes the virtual environment directory (if used)" -ForegroundColor White
    Write-Host "  - Verifies that 'controldesk-mcp' is no longer callable" -ForegroundColor White
    Write-Host "  - Optionally removes client configuration files (with backups)" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "PARAMETERS" -ForegroundColor Yellow
    Write-Host "  -VenvDir <path>" -ForegroundColor Cyan
    Write-Host "    Directory where the virtual environment was created." -ForegroundColor White
    Write-Host "    Default: C:\\tools\\controldesk-mcp-venv" -ForegroundColor White
    Write-Host "    Pass 'current' to uninstall from the current Python environment." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -RemoveConfigs" -ForegroundColor Cyan
    Write-Host "    Also remove MCP client configuration files (with timestamped backups):" -ForegroundColor White
    Write-Host "      - .vscode\\mcp.json (VS Code workspace)" -ForegroundColor White
    Write-Host "      - %APPDATA%\\Claude\\claude_desktop_config.json (Claude Desktop)" -ForegroundColor White
    Write-Host "      - %USERPROFILE%\\.cursor\\mcp.json (Cursor global)" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -Verbose" -ForegroundColor Cyan
    Write-Host "    Show detailed removal steps and verification output." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  -Help" -ForegroundColor Cyan
    Write-Host "    Show this help message." -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "EXAMPLES" -ForegroundColor Yellow
    Write-Host "  # Standard uninstall (remove venv but keep configs)" -ForegroundColor Green
    .\scripts\build\uninstall-wheel.ps1" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Uninstall from current Python environment (no venv)" -ForegroundColor Green
    Write-Host "  .\scripts\build\uninstall-wheel.ps1 -VenvDir current" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Also remove client configs (with backups)" -ForegroundColor Green
    Write-Host "  .\scripts\build\uninstall-wheel.ps1 -RemoveConfigs" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Custom venv location" -ForegroundColor Green
    Write-Host "  .\scripts\build\uninstall-wheel.ps1 -VenvDir `"C:\\envs\\cd-mcp`"" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    Write-Host "  # Full cleanup with detailed reporting" -ForegroundColor Green
    Write-Host "  .\scripts\build\uninstall-wheel.ps1 -RemoveConfigs -Verbose" -ForegroundColor White
    Write-Host "`n" -ForegroundColor Cyan
    exit 0
}

$ErrorActionPreference = 'Stop'

Write-Host ""
Write-Host "=== ControlDesk MCP Server — Uninstall ===" -ForegroundColor Cyan
Write-Host ""

# ── Determine uninstall target ────────────────────────────────────────────────
if ($VenvDir -eq "current") {
    Write-Host "Mode    : current Python environment (no venv)" -ForegroundColor Yellow
    $pipExe = "pip"
}
else {
    $VenvDir = [System.IO.Path]::GetFullPath($VenvDir)
    Write-Host "Venv    : $VenvDir" -ForegroundColor White
    $pipExe = Join-Path $VenvDir "Scripts\pip.exe"

    if (-not (Test-Path $pipExe)) {
        Write-Host ""
        Write-Host "WARNING: Virtual environment not found at $VenvDir" -ForegroundColor Yellow
        Write-Host "         The server may have already been uninstalled or the path is incorrect." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "To uninstall from the current Python environment instead, run:" -ForegroundColor Yellow
        Write-Host "  .\scripts\build\uninstall-wheel.ps1 -VenvDir current" -ForegroundColor Cyan
        Write-Host ""
        exit 0
    }
}

# ── Uninstall the package ─────────────────────────────────────────────────────
Write-Host ""
Write-Host "Uninstalling package from pip ..." -ForegroundColor Cyan

& $pipExe uninstall controldesk-mcp-server --yes 2>&1 | ForEach-Object {
    if ($Verbose) { Write-Host "  $_" -ForegroundColor DarkGray }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: pip uninstall returned non-zero exit code." -ForegroundColor Yellow
    Write-Host "           The package may have already been removed." -ForegroundColor Yellow
}

# ── Remove the virtual environment directory ─────────────────────────────────
if ($VenvDir -ne "current" -and (Test-Path $VenvDir)) {
    Write-Host "Removing virtual environment directory ..." -ForegroundColor Cyan
    try {
        Remove-Item -Recurse -Force $VenvDir -ErrorAction Stop
        Write-Host "  Removed: $VenvDir" -ForegroundColor Green
    }
    catch {
        Write-Host "  Remove-Item failed (files may be locked) — retrying with cmd rmdir ..." -ForegroundColor Yellow
        & cmd /c "rmdir /s /q `"$VenvDir`""
        if ($LASTEXITCODE -eq 0 -and -not (Test-Path $VenvDir)) {
            Write-Host "  Removed: $VenvDir" -ForegroundColor Green
        }
        else {
            Write-Host "  WARNING: Could not remove virtual environment directory." -ForegroundColor Yellow
            Write-Host "  Some files are still locked by a running process." -ForegroundColor Yellow
            Write-Host "  Close any applications using the venv (e.g. MCP server, Python processes)" -ForegroundColor Yellow
            Write-Host "  and then delete it manually:" -ForegroundColor Yellow
            Write-Host "    Remove-Item -Recurse -Force `"$VenvDir`"" -ForegroundColor White
        }
    }
}

# ── Verify uninstall ──────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Verifying uninstall ..." -ForegroundColor Cyan

$found = $false

if ($VenvDir -eq "current") {
    # Check if command is on PATH
    if (Get-Command controldesk-mcp -ErrorAction SilentlyContinue) {
        Write-Host "  WARNING: 'controldesk-mcp' is still available on PATH" -ForegroundColor Yellow
        $found = $true
    }
    else {
        Write-Host "  ✓ 'controldesk-mcp' is not on PATH" -ForegroundColor Green
    }
}
else {
    # Check if entry point exists in the now-deleted venv
    $entryExe = Join-Path $VenvDir "Scripts\controldesk-mcp.exe"
    if (Test-Path $entryExe) {
        Write-Host "  WARNING: Entry point still exists at $entryExe" -ForegroundColor Yellow
        $found = $true
    }
    else {
        Write-Host "  ✓ Entry point removed" -ForegroundColor Green
    }

    # Check if venv directory still exists
    if (Test-Path $VenvDir) {
        Write-Host "  WARNING: Virtual environment directory still exists" -ForegroundColor Yellow
        $found = $true
    }
    else {
        Write-Host "  ✓ Virtual environment directory removed" -ForegroundColor Green
    }
}

# ── Optional: Remove client configuration files ─────────────────────────────
if ($RemoveConfigs) {
    Write-Host ""
    Write-Host "Removing client configuration files ..." -ForegroundColor Cyan

    $configs = @(
        @{
            Name        = "VS Code workspace config"
            Path        = ".vscode\mcp.json"
            Description = "per-workspace (current folder only)"
        },
        @{
            Name        = "Claude Desktop config"
            Path        = "$env:APPDATA\Claude\claude_desktop_config.json"
            Description = "global"
        },
        @{
            Name        = "Cursor global config"
            Path        = "$env:USERPROFILE\.cursor\mcp.json"
            Description = "global"
        }
    )

    $removed = 0
    $skipped = 0

    foreach ($config in $configs) {
        if (Test-Path $config.Path) {
            # Create a backup before deleting
            $backup = $config.Path + ".backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Copy-Item -Path $config.Path -Destination $backup
            Write-Host "  Backup created: $(Split-Path $backup -Leaf)" -ForegroundColor DarkGray

            # For claude_desktop_config.json, only remove the controldesk entry if it's the only one
            if ($config.Name -eq "Claude Desktop config") {
                $json = Get-Content $config.Path -Raw | ConvertFrom-Json
                if ($json.mcpServers -and $json.mcpServers.controldesk) {
                    $json.mcpServers | Add-Member -Name controldesk -Value $null -Force
                    $json.mcpServers = $json.mcpServers | Select-Object -Property * -ExcludeProperty controldesk
                    $json | ConvertTo-Json -Depth 10 | Set-Content $config.Path
                    Write-Host "  Removed: controldesk entry from $($config.Name) ($($config.Description))" -ForegroundColor Green
                    $removed++
                }
            }
            # Similar for cursor config
            elseif ($config.Name -eq "Cursor global config") {
                $json = Get-Content $config.Path -Raw | ConvertFrom-Json
                if ($json.mcpServers -and $json.mcpServers.controldesk) {
                    $json.mcpServers = $json.mcpServers | Select-Object -Property * -ExcludeProperty controldesk
                    $json | ConvertTo-Json -Depth 10 | Set-Content $config.Path
                    Write-Host "  Removed: controldesk entry from $($config.Name) ($($config.Description))" -ForegroundColor Green
                    $removed++
                }
            }
            # For VS Code, we can delete the whole .vscode\mcp.json since it's workspace-specific
            else {
                Remove-Item -Path $config.Path -Force
                Write-Host "  Removed: $($config.Name) ($($config.Description))" -ForegroundColor Green
                $removed++
            }
        }
        else {
            Write-Host "  Skipped: $($config.Name) not found" -ForegroundColor DarkGray
            $skipped++
        }
    }

    if ($removed -gt 0) {
        Write-Host ""
        Write-Host "Backups saved (in case you need to restore):" -ForegroundColor Yellow
        Get-ChildItem -Path @(".vscode", "$env:APPDATA\Claude", "$env:USERPROFILE\.cursor") `
            -Filter "*mcp.json.backup*" -ErrorAction SilentlyContinue 2>$null |
        ForEach-Object { Write-Host "  $($_.FullName)" }
    }
}

# ── Final summary ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Uninstall complete." -ForegroundColor Green
Write-Host ""

if ($found) {
    Write-Host "STATUS: Some artifacts remain. Manual cleanup may be needed." -ForegroundColor Yellow
}
else {
    Write-Host "STATUS: ControlDesk MCP Server fully removed from this machine." -ForegroundColor Green
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Restart any open MCP clients (VS Code, Claude Desktop, Cursor)." -ForegroundColor White
Write-Host "  2. If you want to reinstall, run: .\scripts\build\install-wheel.ps1 -WheelPath <path-to-wheel>" -ForegroundColor White
Write-Host "  3. If you created backups of configs, they are named *.backup-<timestamp>" -ForegroundColor White
Write-Host ""

if ($RemoveConfigs) {
    Write-Host "⚠️  REMINDER: You removed client configuration files." -ForegroundColor Yellow
    Write-Host "   If you were using other MCP servers, you may need to reconfigure them." -ForegroundColor Yellow
    Write-Host "   Backups were saved if you need to restore." -ForegroundColor Yellow
    Write-Host ""
}
