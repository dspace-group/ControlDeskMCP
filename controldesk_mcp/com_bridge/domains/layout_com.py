"""COM wrappers for ControlDesk layout management interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry points:
  app.LayoutManagement                      (IXaLayoutManagement)
  app.LayoutManagement.Layouts              (IXaLayouts collection)
  app.LayoutManagement.ActiveLayout         (IXaLayoutDocument)

IXaLayoutManagement properties used:
  .Layouts       → IXaLayouts  (collection of all layouts in the experiment)
  .ActiveLayout  → IXaLayoutDocument  (currently active layout)

IXaLayouts methods used:
  .Count                        → int
  .Item(name)                   → IXaLayout
  .Add(name)                    → IXaLayout
  .Import(path)                 → void
  .ImportConnectionFile(path)   → void
  .ExportConnectionFile(path)   → void

IXaLayout properties / methods used:
  .Name          → str   (read-only)
  .FilePath      → str   (read-only)
  .IsOpen        → bool  (read-only)
  .EditingMode   → int   (read/write — LayoutEditingMode enum integer)
  .Open()        → void  (open and display the layout)
  .Close(bool)   → void  (close; bool = save before close)
  .Save()        → void  (save to .cdl file)
  .Activate()    → void  (bring to foreground)

IXaLayoutDocument methods:
  .Export(path)  → void  (export active layout to .lax file)

LayoutEditingMode integer values (ControlDesk COM enum):
  Design  = 0
  Runtime = 1
  Hybrid  = 2
"""

from __future__ import annotations

from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgeOperationError, BridgePreconditionError

# ── Editing mode mapping ───────────────────────────────────────────────────────

_EDITING_MODE_TO_INT: dict[str, int] = {
    "Design": 0,
    "Runtime": 1,
    "Hybrid": 2,
}
_INT_TO_EDITING_MODE: dict[int, str] = {v: k for k, v in _EDITING_MODE_TO_INT.items()}


def _parse_editing_mode(raw: Any) -> str:
    """Convert a COM LayoutEditingMode value (int or str) to its canonical string name."""
    if isinstance(raw, int):
        return _INT_TO_EDITING_MODE.get(raw, str(raw))
    raw_str = str(raw)
    if raw_str in _EDITING_MODE_TO_INT:
        return raw_str
    try:
        return _INT_TO_EDITING_MODE.get(int(raw_str), raw_str)
    except (ValueError, TypeError):
        return raw_str


# ── Precondition guards ───────────────────────────────────────────────────────


def _get_layout_management(app: Any) -> Any:
    """Return app.LayoutManagement; raises BridgePreconditionError on failure."""
    try:
        return app.LayoutManagement
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="LayoutManagement") from exc


def _get_layouts(app: Any) -> Any:
    """Return the IXaLayouts collection."""
    mgmt = _get_layout_management(app)
    try:
        return mgmt.Layouts
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayoutManagement", method="Layouts") from exc


def _get_layout_item(layouts: Any, name: str) -> Any:
    """Return the IXaLayout for *name*; raises BridgePreconditionError if not found."""
    try:
        return layouts.Item(name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Layout '{name}' does not exist in the active experiment. Call layout_list to see available layouts.",
            error_code="BRIDGE_LAYOUT_NOT_FOUND",
            recovery_hint=("Use layout_list() to enumerate available layout names. Layout names are case-sensitive."),
        ) from exc


# ── layout_list ───────────────────────────────────────────────────────────────


def layout_list(app: Any) -> list[dict[str, Any]]:
    """Return a list of dicts describing every layout in the active experiment.

    Each dict has keys: ``name``, ``file_path``, ``is_open``, ``is_active``, ``editing_mode``.
    """
    layouts = _get_layouts(app)
    try:
        mgmt = _get_layout_management(app)
        active_layout = None
        try:
            active_layout = mgmt.ActiveLayout
        except Exception:
            pass

        active_name: str | None = None
        if active_layout is not None:
            try:
                active_name = str(active_layout.Name)
            except Exception:
                pass

        count = int(layouts.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayouts", method="Count") from exc

    result: list[dict[str, Any]] = []
    for i in range(count):
        try:
            layout = layouts.Item(i)
            name = str(layout.Name)
            file_path = str(layout.FilePath) if hasattr(layout, "FilePath") else ""
            is_open = bool(layout.IsOpen) if hasattr(layout, "IsOpen") else False
            editing_mode = _parse_editing_mode(layout.EditingMode) if hasattr(layout, "EditingMode") else "Unknown"
            is_active = name == active_name
            result.append(
                {
                    "name": name,
                    "file_path": file_path,
                    "is_open": is_open,
                    "is_active": is_active,
                    "editing_mode": editing_mode,
                }
            )
        except Exception as exc:
            raise map_com_error(exc, interface="IXaLayouts", method="Item") from exc

    return result


# ── layout_create ──────────────────────────────────────────────────────────────


def layout_create(app: Any, name: str) -> dict[str, Any]:
    """Create a new layout in the active experiment.

    Returns dict with: name, file_path.
    """
    layouts = _get_layouts(app)
    try:
        layout = layouts.Add(name)
        file_path = str(layout.FilePath) if hasattr(layout, "FilePath") else ""
        return {"name": name, "file_path": file_path}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayouts", method="Add") from exc


# ── layout_open ───────────────────────────────────────────────────────────────


def layout_open(app: Any, name: str) -> dict[str, Any]:
    """Open an existing layout and make it visible.

    Returns dict with: name, file_path, editing_mode.
    """
    layouts = _get_layouts(app)
    layout = _get_layout_item(layouts, name)
    try:
        layout.Open()
        file_path = str(layout.FilePath) if hasattr(layout, "FilePath") else ""
        editing_mode = _parse_editing_mode(layout.EditingMode) if hasattr(layout, "EditingMode") else "Unknown"
        return {"name": name, "file_path": file_path, "editing_mode": editing_mode}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayout", method="Open") from exc


# ── layout_save ───────────────────────────────────────────────────────────────


def layout_save(app: Any, name: str) -> dict[str, Any]:
    """Save the layout to its .cdl file.

    Returns dict with: name, file_path.
    """
    layouts = _get_layouts(app)
    layout = _get_layout_item(layouts, name)
    try:
        layout.Save()
        file_path = str(layout.FilePath) if hasattr(layout, "FilePath") else ""
        return {"name": name, "file_path": file_path}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayout", method="Save") from exc


# ── layout_close ──────────────────────────────────────────────────────────────


def layout_close(app: Any, name: str, save_before_close: bool) -> dict[str, Any]:
    """Close an open layout.

    Args:
        save_before_close: If True, save before closing.

    Returns dict with: name, saved_before_close.
    """
    layouts = _get_layouts(app)
    layout = _get_layout_item(layouts, name)
    try:
        layout.Close(save_before_close)
        return {"name": name, "saved_before_close": save_before_close}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayout", method="Close") from exc


# ── layout_activate ───────────────────────────────────────────────────────────


def layout_activate(app: Any, name: str) -> dict[str, Any]:
    """Bring a layout to the foreground.

    Returns dict with: name.
    """
    layouts = _get_layouts(app)
    layout = _get_layout_item(layouts, name)
    try:
        layout.Activate()
        return {"name": name}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayout", method="Activate") from exc


# ── layout_get_info ───────────────────────────────────────────────────────────


def layout_get_info(app: Any, name: str) -> dict[str, Any]:
    """Return metadata about a specific layout.

    Returns dict with: name, file_path, is_open, is_active, editing_mode.
    """
    layouts = _get_layouts(app)
    layout = _get_layout_item(layouts, name)
    mgmt = _get_layout_management(app)

    active_name: str | None = None
    try:
        al = mgmt.ActiveLayout
        if al is not None:
            active_name = str(al.Name)
    except Exception:
        pass

    try:
        file_path = str(layout.FilePath) if hasattr(layout, "FilePath") else ""
        is_open = bool(layout.IsOpen) if hasattr(layout, "IsOpen") else False
        editing_mode = _parse_editing_mode(layout.EditingMode) if hasattr(layout, "EditingMode") else "Unknown"
        is_active = name == active_name
        return {
            "name": name,
            "file_path": file_path,
            "is_open": is_open,
            "is_active": is_active,
            "editing_mode": editing_mode,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayout", method="properties") from exc


# ── layout_configure ──────────────────────────────────────────────────────────


def layout_configure(app: Any, name: str, editing_mode: str) -> dict[str, Any]:
    """Set the editing mode for a layout.

    Args:
        editing_mode: One of 'Design', 'Runtime', 'Hybrid'.

    Returns dict with: name, editing_mode.
    """
    mode_int = _EDITING_MODE_TO_INT.get(editing_mode)
    if mode_int is None:
        raise BridgeOperationError(
            f"Invalid editing_mode '{editing_mode}'. Valid values: Design, Runtime, Hybrid.",
        )
    layouts = _get_layouts(app)
    layout = _get_layout_item(layouts, name)
    try:
        layout.EditingMode = mode_int
        return {"name": name, "editing_mode": editing_mode}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayout", method="EditingMode") from exc


# ── layout_export ──────────────────────────────────────────────────────────────


def layout_export(app: Any, export_path: str) -> dict[str, Any]:
    """Export the active layout to a .lax file.

    Returns dict with: layout_name, export_path.
    """
    mgmt = _get_layout_management(app)
    try:
        active_layout = mgmt.ActiveLayout
        if active_layout is None:
            raise BridgePreconditionError(
                "No active layout open. Call layout_open or layout_activate first.",
                error_code="BRIDGE_NO_ACTIVE_LAYOUT",
                recovery_hint="Open and activate a layout before exporting.",
            )
        layout_name = str(active_layout.Name) if hasattr(active_layout, "Name") else ""
        active_layout.Export(export_path)
        return {"layout_name": layout_name, "export_path": export_path}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayoutDocument", method="Export") from exc


# ── layout_import ──────────────────────────────────────────────────────────────


def layout_import(app: Any, import_path: str) -> dict[str, Any]:
    """Import a .lax layout file into the active experiment.

    Returns dict with: layout_name, import_path.
    """
    layouts = _get_layouts(app)
    try:
        layouts.Import(import_path)
        # Attempt to discover the imported layout name from the file path
        import os

        layout_name = os.path.splitext(os.path.basename(import_path))[0]
        return {"layout_name": layout_name, "import_path": import_path}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayouts", method="Import") from exc


# ── layout_import_connection_file ──────────────────────────────────────────────


def layout_import_connection_file(app: Any, connection_file_path: str) -> dict[str, Any]:
    """Import a .cdx signal connection file into the active experiment's layouts.

    Returns dict with: connection_file_path.
    """
    layouts = _get_layouts(app)
    try:
        layouts.ImportConnectionFile(connection_file_path)
        return {"connection_file_path": connection_file_path}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayouts", method="ImportConnectionFile") from exc


# ── layout_export_connection_file ──────────────────────────────────────────────


def layout_export_connection_file(app: Any, connection_file_path: str) -> dict[str, Any]:
    """Export signal connections from the active layout to a .cdx file.

    Returns dict with: connection_file_path.
    """
    layouts = _get_layouts(app)
    try:
        layouts.ExportConnectionFile(connection_file_path)
        return {"connection_file_path": connection_file_path}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayouts", method="ExportConnectionFile") from exc
