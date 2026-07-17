"""COM wrappers for the ControlDesk IXaApplication interface.

All functions must be called on the STA thread via com_bridge.dispatch().
"""

from __future__ import annotations

import time
from typing import Any

from sources.com_bridge.error_handling.hresult import map_com_error
from sources.com_bridge.errors import BridgePreconditionError, BridgeTimeoutError

# HRESULTs that mean the COM server process is alive but not yet ready.
_STARTUP_HRESULTS: frozenset[int] = frozenset(
    [
        0x800706BA,  # RPC_S_SERVER_UNAVAILABLE — process started, COM not ready
        0x80010108,  # RPC_E_DISCONNECTED       — transient during init
    ]
)
_POLL_INTERVAL_S: float = 0.5

# ControlDesk IXaMainWindow.State COM enum integer values.
# Known limitation: on ControlDesk 2026-A writing State=2 (Maximized) is
# silently coerced by the COM server to 1 (Minimized).  Only Normal (0) and
# Minimized (1) reliably round-trip via COM on this version.  The enum
# mapping is kept complete for forward compatibility with other versions.
_WINDOW_STATE_TO_INT: dict[str, int] = {
    "Normal": 0,
    "Minimized": 1,
    "Maximized": 2,
    "Hidden": 3,
}
_INT_TO_WINDOW_STATE: dict[int, str] = {v: k for k, v in _WINDOW_STATE_TO_INT.items()}
_STATE_INT_MAXIMIZED: int = 2


def get_version(app: Any) -> str:
    """Return the ControlDesk version string."""
    try:
        return str(app.Version)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="Version") from exc


def is_experiment_open(app: Any) -> bool:
    """Return True if ControlDesk has an active experiment open."""
    try:
        return app.ActiveExperiment is not None
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="ActiveExperiment") from exc


def show_window(app: Any, timeout_s: float = 30.0) -> None:
    """Make the ControlDesk main window visible.

    Polls until the ``IXaMainWindow`` COM object is ready, then sets ``Visible=True``.
    This handles the race between ``Dispatch()`` returning and ControlDesk completing
    its internal startup — the window COM object may not exist for several seconds.

    Retries only on transient startup HRESULTs; fails fast on any other error.
    Blocks the STA thread — do not call from asyncio directly.
    """
    deadline = time.monotonic() + timeout_s
    last_exc: Exception | None = None

    while time.monotonic() < deadline:
        try:
            app.MainWindow.Visible = True
            return  # success
        except Exception as exc:  # noqa: BLE001
            raw = exc.args[0] if exc.args else None
            hresult = (raw & 0xFFFFFFFF) if isinstance(raw, int) else None
            if hresult not in _STARTUP_HRESULTS:
                # Not a startup-race error — fail immediately
                raise map_com_error(exc, interface="IXaMainWindow", method="Visible") from exc
            last_exc = exc
            time.sleep(_POLL_INTERVAL_S)

    raise BridgeTimeoutError(
        f"ControlDesk window did not become ready within {timeout_s:.0f}s. "
        "Ensure ControlDesk is installed and not blocked by a dialog.",
        recovery_hint="Increase COM_LAUNCH_TIMEOUT_MS or check ControlDesk installation.",
    ) from last_exc


def quit_application(app: Any) -> None:
    """Send the Quit command to ControlDesk.

    ControlDesk will close after this call. The COM connection will become
    stale — the caller must handle subsequent disconnection errors.
    """
    try:
        app.Quit()
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="Quit") from exc


# ── IXaMainWindow wrappers ────────────────────────────────────────────────────


def set_window_visible(app: Any, visible: bool) -> None:
    """Set the main window visibility (``app.MainWindow.Visible``)."""
    try:
        app.MainWindow.Visible = visible
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMainWindow", method="Visible") from exc


def get_window_visible(app: Any) -> bool:
    """Return the current main window visibility (``app.MainWindow.Visible``)."""
    try:
        return bool(app.MainWindow.Visible)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMainWindow", method="Visible") from exc


def set_window_state(app: Any, state: str) -> None:
    """Set the main window display state (``app.MainWindow.State``).

    *state* must be one of: ``"Normal"``, ``"Maximized"``, ``"Minimized"``,
    or ``"Hidden"``. The string is converted to the COM integer enum value
    before assignment — ControlDesk rejects string values with DISP_E_TYPEMISMATCH.
    """
    state_int = _WINDOW_STATE_TO_INT.get(state)
    if state_int is None:
        raise BridgePreconditionError(
            f"Unknown window state '{state}'. Use one of: Normal, Maximized, Minimized, Hidden.",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Pass one of: 'Normal', 'Maximized', 'Minimized', 'Hidden'.",
        )
    try:
        app.MainWindow.State = state_int
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMainWindow", method="State") from exc


def get_window_state(app: Any) -> str:
    """Return the current main window display state as a string.

    COM returns an integer enum value; this function maps it back to the
    human-readable string (``"Normal"``, ``"Maximized"``, etc.).
    """
    try:
        raw = app.MainWindow.State
        return _INT_TO_WINDOW_STATE.get(int(raw), str(raw))
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMainWindow", method="State") from exc


def set_window_position(app: Any, left: int, top: int, width: int, height: int) -> None:
    """Set the main window geometry (position and size) in pixels.

    Raises :class:`BridgePreconditionError` if the window is maximized or in
    full-screen mode — ControlDesk rejects geometry changes in those states.
    Call ``app_set_window_state('Normal')`` and ``app_set_fullscreen(False)``
    first.
    """
    try:
        raw_state = int(app.MainWindow.State)
        is_fullscreen = bool(app.MainWindow.FullScreenModeEnabled)
    except Exception:  # noqa: BLE001
        raw_state = 0
        is_fullscreen = False

    if raw_state == _STATE_INT_MAXIMIZED or is_fullscreen:
        raise BridgePreconditionError(
            "Cannot set window position: window is maximized or in full-screen mode.",
            error_code="BRIDGE_WINDOW_NOT_NORMAL",
            recovery_hint=(
                "Call app_set_window_state('Normal') and app_set_fullscreen(False) "
                "before calling app_set_window_position."
            ),
        )
    try:
        app.MainWindow.Left = left
        app.MainWindow.Top = top
        app.MainWindow.Width = width
        app.MainWindow.Height = height
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMainWindow", method="Position") from exc


def set_fullscreen(app: Any, enabled: bool) -> None:
    """Enable or disable full-screen mode (``app.MainWindow.FullScreenModeEnabled``)."""
    try:
        app.MainWindow.FullScreenModeEnabled = enabled
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMainWindow", method="FullScreenModeEnabled") from exc
