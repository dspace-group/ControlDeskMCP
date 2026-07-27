"""COM wrappers for the ControlDesk IXaWindows / IXaWindow interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry point:
  app.MainWindow.Windows   (IXaWindows collection)
  app.MainWindow.Windows.Item(name)   (IXaWindow — individual tool window)

IXaWindow properties / methods used:
  .Caption       → str   (read-only — the exact name string for .Item())
  .Visible       → bool  (read-only — True when not Closed)
  .State         → int   (read/write — ToolWindowState COM enum integer)
  .Show()        → void  (open and activate)
  .Close(bool)   → void  (hide; bool = save layout)

IXaWindows methods used:
  .Count         → int
  .Contains(str) → bool  (safe existence check — does NOT raise on missing name)
  .Item(str)     → IXaWindow  (raises COM error when name not found)

WindowState enum (WindowState.cs — dSPACE.ToolAutomation.ControlDeskNG):
  None = -1, Docked = 3, AutoHidden = 4, Floating = 5, Closed = 6, DockedAsDocument = 7
"""

from __future__ import annotations

from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgePreconditionError

# ── ToolWindowState integer mapping ──────────────────────────────────────────
# Confirmed from WindowState.cs in ControlDeskNGAutomationInterfaceDefinitions:
#   namespace dSPACE.ToolAutomation.ControlDeskNG
#   None = -1, Docked = 3, AutoHidden = 4, Floating = 5, Closed = 6, DockedAsDocument = 7
_STATE_TO_INT: dict[str, int] = {
    "Docked": 3,
    "AutoHidden": 4,
    "Floating": 5,
    "Closed": 6,
    "DockedAsDocument": 7,
}
_INT_TO_STATE: dict[int, str] = {v: k for k, v in _STATE_TO_INT.items()}


def _parse_state(raw: Any) -> str:
    """Convert a COM ToolWindowState value (int or str) to its canonical string name."""
    if isinstance(raw, int):
        return _INT_TO_STATE.get(raw, str(raw))
    # pywin32 may return a string directly for some COM enum types
    raw_str = str(raw)
    if raw_str in _STATE_TO_INT:
        return raw_str
    # Try parsing as integer string
    try:
        return _INT_TO_STATE.get(int(raw_str), raw_str)
    except (ValueError, TypeError):
        return raw_str


def _get_windows(app: Any) -> Any:
    """Return the IXaWindows collection from app.MainWindow."""
    try:
        return app.MainWindow.Windows
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMainWindow", method="Windows") from exc


def _get_window_item(windows: Any, window_name: str) -> Any:
    """Return the IXaWindow for *window_name*; raises BridgePreconditionError if not found."""
    try:
        return windows.Item(window_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Tool window '{window_name}' does not exist in this ControlDesk instance. "
            "Call tool_window_list() to see available panels.",
            error_code="BRIDGE_WINDOW_NOT_FOUND",
            recovery_hint=(
                "Use tool_window_list() to enumerate available panel names. "
                "Window names are case-sensitive and must match the Caption property exactly."
            ),
        ) from exc


# ── list_windows ──────────────────────────────────────────────────────────────


def list_windows(app: Any) -> list[dict[str, Any]]:
    """Return a list of dicts describing every tool window in the main window.

    Each dict has keys: ``name``, ``caption``, ``is_visible``, ``dock_state``.
    """
    windows = _get_windows(app)
    try:
        count = int(windows.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindows", method="Count") from exc

    result: list[dict[str, Any]] = []
    for i in range(1, count + 1):
        try:
            win = windows.Item(i)
            caption = str(win.Caption)
            raw_state = win.State
            dock_state = _parse_state(raw_state)
            is_visible = bool(win.Visible)
            result.append(
                {
                    "name": caption,
                    "caption": caption,
                    "is_visible": is_visible,
                    "dock_state": dock_state,
                }
            )
        except Exception:  # noqa: BLE001
            # Some ControlDesk window types (e.g. document tabs, special panels)
            # raise DISP_E_EXCEPTION when their properties are accessed during
            # enumeration.  Skip these silently — they are not usable as tool
            # windows and should not abort the entire list.
            continue

    return result


# ── show_window ───────────────────────────────────────────────────────────────


def show_window(app: Any, window_name: str) -> dict[str, Any]:
    """Show and activate the named tool window.

    Returns a dict with ``caption``, ``is_now_visible``, ``dock_state``.
    Raises :class:`BridgePreconditionError` if the window does not exist.
    """
    windows = _get_windows(app)
    win = _get_window_item(windows, window_name)
    try:
        win.Show()
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="Show") from exc

    try:
        caption = str(win.Caption)
        dock_state = _parse_state(win.State)
        is_visible = bool(win.Visible)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="Caption/State/Visible") from exc

    return {
        "caption": caption,
        "is_now_visible": is_visible,
        "dock_state": dock_state,
    }


# ── close_window ──────────────────────────────────────────────────────────────


def close_window(app: Any, window_name: str, save_layout: bool = True) -> dict[str, Any]:
    """Close (hide) the named tool window.

    *save_layout* controls whether the panel's dock configuration is saved.
    Returns a dict with ``caption``, ``layout_saved``, ``is_now_visible``.
    Raises :class:`BridgePreconditionError` if the window does not exist.
    """
    windows = _get_windows(app)
    win = _get_window_item(windows, window_name)
    try:
        caption = str(win.Caption)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="Caption") from exc

    try:
        win.Close(save_layout)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="Close") from exc

    try:
        is_visible = bool(win.Visible)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="Visible") from exc

    return {
        "caption": caption,
        "layout_saved": save_layout,
        "is_now_visible": is_visible,
    }


# ── get_window_state ──────────────────────────────────────────────────────────


def get_window_state(app: Any, window_name: str) -> dict[str, Any]:
    """Return the dock state and visibility of the named tool window.

    Returns a dict with ``caption``, ``is_visible``, ``dock_state``.
    Raises :class:`BridgePreconditionError` if the window does not exist.
    """
    windows = _get_windows(app)
    win = _get_window_item(windows, window_name)
    try:
        caption = str(win.Caption)
        dock_state = _parse_state(win.State)
        is_visible = bool(win.Visible)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="Caption/State/Visible") from exc

    return {
        "caption": caption,
        "is_visible": is_visible,
        "dock_state": dock_state,
    }


# ── set_window_dock_state ─────────────────────────────────────────────────────


def set_window_dock_state(app: Any, window_name: str, dock_state: str) -> dict[str, Any]:
    """Set the docking mode of the named tool window.

    *dock_state* must be one of: ``"Docked"``, ``"DockedAsDocument"``,
    ``"AutoHidden"``, ``"Floating"``, ``"Closed"``.

    Returns a dict with ``caption``, ``dock_state``, ``is_visible``.
    Raises :class:`BridgePreconditionError` if the window does not exist or the
    state value is invalid.
    """
    state_int = _STATE_TO_INT.get(dock_state)
    if state_int is None:
        raise BridgePreconditionError(
            f"Unknown dock state '{dock_state}'. "
            "Use one of: Docked, DockedAsDocument, AutoHidden, Floating, Closed.",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint=(
                "Pass one of: 'Docked', 'DockedAsDocument', 'AutoHidden', 'Floating', 'Closed'."
            ),
        )

    windows = _get_windows(app)
    win = _get_window_item(windows, window_name)

    try:
        caption = str(win.Caption)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="Caption") from exc

    try:
        win.State = state_int
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="State") from exc

    try:
        actual_state = _parse_state(win.State)
        is_visible = bool(win.Visible)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="State/Visible") from exc

    return {
        "caption": caption,
        "dock_state": actual_state,
        "is_visible": is_visible,
    }


# ── get_window_geometry ───────────────────────────────────────────────────────


def get_window_geometry(app: Any, window_name: str) -> dict[str, Any]:
    """Return the position and size of the named tool window.

    Reads ``Left``, ``Top``, ``Width``, ``Height`` from ``IXaWindow``.
    Returns a dict with ``caption``, ``left``, ``top``, ``width``, ``height``.
    Note: coordinates are meaningful only when the window is Floating or Docked;
    Closed/AutoHidden windows may return 0 for some fields.
    Raises :class:`BridgePreconditionError` if the window does not exist.
    """
    windows = _get_windows(app)
    win = _get_window_item(windows, window_name)
    try:
        caption = str(win.Caption)
        left = int(win.Left)
        top = int(win.Top)
        width = int(win.Width)
        height = int(win.Height)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindow", method="Left/Top/Width/Height") from exc

    return {
        "caption": caption,
        "left": left,
        "top": top,
        "width": width,
        "height": height,
    }


# ── check_window_exists ───────────────────────────────────────────────────────


def check_window_exists(app: Any, window_name: str) -> bool:
    """Return True if *window_name* exists in the main window's tool window collection.

    Uses ``IXaWindows.Contains()`` which is the safe guard before ``Item()`` calls.
    Does NOT raise if the window is absent — returns ``False`` instead.
    Raises a :class:`BridgeError` only if the COM call itself fails (ControlDesk not running).
    """
    windows = _get_windows(app)
    try:
        return bool(windows.Contains(window_name))
    except Exception as exc:
        raise map_com_error(exc, interface="IXaWindows", method="Contains") from exc
