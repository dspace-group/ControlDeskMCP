# PyInstaller spec for ControlDesk MCP Server — Windows single-file executable.
#
# Build from the repository root:
#   uv run pyinstaller packaging/ControlDeskMCP.spec

from pathlib import Path

project_root = Path(SPECPATH).parent

a = Analysis(
    [str(project_root / "controldesk_mcp" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # pywin32 is lazy-imported by the COM bridge after MCP initialization.
        "win32com",
        "win32com.client",
        "pywintypes",
        "pythoncom",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ControlDeskMCP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # stdio transport requires a console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=None,
)
