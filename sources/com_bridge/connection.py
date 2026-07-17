"""COM connection lifecycle — connect, disconnect, health, reconnect.

Must only be used from the STA thread.

Connection state machine:
    DISCONNECTED ──connect()──► CONNECTED
         ▲                           │
         │ RPC_E_DISCONNECTED        │ health() OK
         │                           ▼
         └──── RECONNECTING ◄────────┘
                    │
                    │ max_retries exceeded
                    ▼
                FAILED (raises BridgeConnectionError)
"""

from __future__ import annotations

import re
from enum import Enum, auto
from typing import Any

from sources.com_bridge.detector import resolve_prog_id
from sources.com_bridge.error_handling.hresult import map_com_error
from sources.com_bridge.errors import BridgeConnectionError
from sources.utils.logger import get_logger

_log = get_logger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = auto()
    CONNECTED = auto()
    RECONNECTING = auto()
    FAILED = auto()


class ComConnection:
    """Owns the root ControlDesk COM application object.

    All methods must be called exclusively from the STA thread.
    """

    def __init__(self, max_retries: int = 3) -> None:
        self._max_retries = max_retries
        self._state = ConnectionState.DISCONNECTED
        self._app: Any = None
        self._prog_id: str = ""

    # ── Public API ─────────────────────────────────────────────────────────────

    def connect(self, controldesk_version: str = "") -> bool:
        """Resolve ProgID from *controldesk_version* and create the COM application object.

        Returns:
            ``True`` if a new ControlDesk instance was launched,
            ``False`` if an already-running instance was attached.
        """
        prog_id = resolve_prog_id(controldesk_version)
        _log.info("Connecting to ControlDesk via '%s'", prog_id)
        self._prog_id = prog_id
        self._app, launched = self._dispatch(prog_id)
        self._state = ConnectionState.CONNECTED
        action = "launched" if launched else "attached to running"
        _log.info("%s ControlDesk ('%s')", action, prog_id)
        return launched

    def disconnect(self) -> None:
        """Release the COM application object."""
        self._release()
        self._state = ConnectionState.DISCONNECTED
        _log.info("Disconnected from ControlDesk")

    def reconnect(self) -> None:
        """Attempt to re-establish a lost connection."""
        self._state = ConnectionState.RECONNECTING
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                _log.info("Reconnect attempt %d/%d", attempt, self._max_retries)
                self._release()
                self._app, _ = self._dispatch(self._prog_id)
                self._state = ConnectionState.CONNECTED
                _log.info("Reconnected to ControlDesk")
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
        self._state = ConnectionState.FAILED
        msg = f"Reconnection failed after {self._max_retries} attempts"
        raise BridgeConnectionError(msg) from last_exc

    def get_app(self) -> Any:
        """Return the COM application object. Raises if not connected."""
        if self._state is not ConnectionState.CONNECTED or self._app is None:
            msg = f"Not connected (state={self._state.name}). Call connect() first."
            raise BridgeConnectionError(msg)
        return self._app

    def health(self) -> dict[str, object]:
        """Return connection health summary (safe to call from any state)."""
        return {
            "connected": self._state is ConnectionState.CONNECTED,
            "state": self._state.name,
            "prog_id": self._prog_id,
        }

    def get_connected_version(self) -> str:
        """Return the user-facing version for the active connection.

        Extracts the ``YYYY-L`` token from the stored ProgID so callers
        never need to parse ProgIDs themselves.

        Returns:
            Version string like ``"2026-A"``, or empty string when
            not connected or the ProgID does not contain a version token.
        """
        if not self._prog_id:
            return ""
        m = re.search(r"(\d{4}-[A-Za-z])$", self._prog_id)
        return m.group(1).upper() if m else ""

    @property
    def state(self) -> ConnectionState:
        return self._state

    # ── Private helpers ────────────────────────────────────────────────────────

    def _dispatch(self, prog_id: str) -> tuple[Any, bool]:
        """Attach to a running ControlDesk instance, or launch a new one.

        Returns:
            ``(app_object, launched)`` — *launched* is ``True`` when a new
            instance was started, ``False`` when an existing one was found.
        """
        try:
            import win32com.client  # noqa: PLC0415

            try:
                app = win32com.client.GetActiveObject(prog_id)
                return app, False  # already running — attached
            except Exception:  # noqa: BLE001
                pass  # not running — fall through to launch

            app = win32com.client.Dispatch(prog_id)
            return app, True
        except Exception as exc:
            raise map_com_error(exc, interface="IApplication", method="Dispatch") from exc

    def _release(self) -> None:
        """Release the COM application reference."""
        if self._app is not None:
            try:
                del self._app
            except Exception:  # noqa: BLE001
                pass
            finally:
                self._app = None
