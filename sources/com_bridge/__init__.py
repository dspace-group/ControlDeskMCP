"""COM bridge public API.

This is the ONLY module that code outside ``com_bridge/`` may import.

Usage:
    from sources.com_bridge import startup, shutdown, dispatch, get_connection, domains
    # Use domains.application_com for application-specific COM wrappers
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Callable

from sources.com_bridge import domains
from sources.com_bridge import sta_thread as _sta
from sources.com_bridge.connection import ComConnection, ConnectionState
from sources.com_bridge.detector import is_version_installed, normalize_user_version
from sources.com_bridge.errors import BridgeTimeoutError
from sources.utils.logger import get_logger

__all__ = [
    "startup",
    "shutdown",
    "dispatch",
    "get_connection",
    "ensure_connected",
    "get_connected_version",
    "disconnect_for_switch",
    "is_version_installed",
    "normalize_user_version",
    "domains",
]

_log = get_logger(__name__)

# Single COM connection instance — only accessed on the STA thread.
_connection: ComConnection | None = None


def get_connection() -> ComConnection:
    """Return the active :class:`ComConnection`. Raises if bridge is not started."""
    if _connection is None:
        msg = "COM bridge not started. Call startup() first."
        raise RuntimeError(msg)
    return _connection


async def startup() -> None:
    """Start the STA thread only. Fast — completes in milliseconds.

    Called from the server lifespan so ``initialize`` responds immediately.
    COM connection is deferred: ``ensure_connected()`` establishes it on the
    first ``start_controldesk`` tool call.
    """
    global _connection  # noqa: PLW0603
    _sta.startup()
    _connection = ComConnection()  # DISCONNECTED state — no COM call yet
    _log.debug("STA thread ready; COM connection deferred until first tool call")


async def ensure_connected(controldesk_version: str = "") -> bool:
    """Guarantee the COM bridge is connected, (re)starting if necessary.

    ``startup()`` leaves the connection in DISCONNECTED state.
    The first ``start_controldesk`` call hits this path and establishes the
    COM connection lazily.

    Returns:
        ``True`` if a new connection was established, ``False`` if already connected.
    """
    global _connection  # noqa: PLW0603
    if _connection is None:
        # Bridge not started at all — start STA thread first.
        await startup()
        # Fall through: DISCONNECTED → connect below.
    if _connection.state is ConnectionState.CONNECTED:
        return False
    # DISCONNECTED (deferred first connect) or RECONNECTING/FAILED.
    future = _sta.get_sta_thread().submit(_connection.connect, controldesk_version)
    launched: bool = await asyncio.wrap_future(future)
    return launched


def get_connected_version() -> str:
    """Return the ControlDesk version the bridge is currently connected to.

    Returns:
        Version string like ``"2026-A"``, or empty string when the bridge has
        not yet connected (DISCONNECTED state) or was never started.
    """
    if _connection is None:
        return ""
    return _connection.get_connected_version()


async def disconnect_for_switch() -> None:
    """Release the current COM connection so a different version can be started.

    This does *not* quit ControlDesk — the caller is responsible for calling
    ``quit_application`` on the COM app object before invoking this function.
    After this returns, the connection is in DISCONNECTED state and
    ``ensure_connected(new_version)`` will launch the new version.
    """
    global _connection  # noqa: PLW0603
    if _connection is not None and _connection.state is ConnectionState.CONNECTED:
        try:
            future = _sta.get_sta_thread().submit(_connection.disconnect)
            await asyncio.wrap_future(future)
        except Exception as exc:  # noqa: BLE001
            _log.warning("COM disconnect during version switch (continuing): %s", exc)


async def shutdown() -> None:
    """Disconnect from ControlDesk and stop the STA thread."""
    global _connection  # noqa: PLW0603
    if _connection is not None:
        try:
            future = _sta.get_sta_thread().submit(_connection.disconnect)
            await asyncio.wrap_future(future)
        except Exception as exc:  # noqa: BLE001
            _log.warning("COM disconnect error (ignored on shutdown): %s", exc)
        _connection = None
    _sta.shutdown()


async def dispatch(fn: Callable[..., Any], *args: Any, timeout_ms: int = 8000) -> Any:
    """Submit *fn(*args)* to the STA thread and await the result.

    Args:
        fn: Callable to execute on the STA thread (typically a domain wrapper).
        *args: Arguments forwarded to *fn*.
        timeout_ms: Wall-clock timeout in milliseconds.

    Returns:
        The return value of *fn*.

    Raises:
        BridgeTimeoutError: The call exceeded *timeout_ms*.
        BridgeError subclass: Any classified COM failure from *fn*.
        RuntimeError: Bridge not started.
    """
    future: concurrent.futures.Future[Any] = _sta.get_sta_thread().submit(fn, *args)
    timeout_s = timeout_ms / 1000.0
    try:
        return await asyncio.wait_for(asyncio.wrap_future(future), timeout=timeout_s)
    except TimeoutError as exc:
        future.cancel()
        raise BridgeTimeoutError(f"COM call timed out after {timeout_ms} ms") from exc
