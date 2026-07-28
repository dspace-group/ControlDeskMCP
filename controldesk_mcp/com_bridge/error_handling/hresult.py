"""HRESULT classifier — converts raw COM exceptions to typed BridgeError subclasses.

Classification priority (highest first):
  1. Exact HRESULT lookup in ``_HRESULT_MAP``.
  2. Facility-based fallback (FACILITY_RPC → BridgeConnectionError,
     FACILITY_DISPATCH → BridgeVersionError).
  3. ``BRIDGE_UNKNOWN`` catch-all.

``DISP_E_EXCEPTION`` (0x80020009) is the HRESULT ControlDesk uses for virtually all
internal errors.  The actual description lives in ``IErrorInfo`` — ``e.args[2][2]``.
"""

from __future__ import annotations

from controldesk_mcp.com_bridge.errors import (
    BridgeConnectionError,
    BridgeError,
    BridgeOperationError,
    BridgeUiBlockedError,
    BridgeVersionError,
)

# Mask to convert signed 32-bit HRESULT to unsigned int for lookup.
_HRESULT_MASK: int = 0xFFFFFFFF

# Facility codes extracted from bits [16..26] of the HRESULT.
_FACILITY_RPC: int = 1  # RPC / COM runtime errors
_FACILITY_DISPATCH: int = 2  # IDispatch / Automation errors

# HRESULT → (error_code, BridgeError subclass, retryable, recovery_hint)
_HRESULT_MAP: dict[int, tuple[str, type[BridgeError], bool, str]] = {
    # ── RPC / connection errors ────────────────────────────────────────────────
    0x80010001: (
        "COM_UI_BLOCKING",
        BridgeUiBlockedError,
        True,
        "Dismiss the open ControlDesk dialog, or set Platform.DisplayStatusInformation = False before long operations.",
    ),
    0x80010108: (
        "COM_DISCONNECTED",
        BridgeConnectionError,
        True,
        "ControlDesk disconnected. Call controldesk_app_start_or_attach to re-establish the connection.",
    ),
    0x8001010E: (
        "COM_WRONG_THREAD",
        BridgeOperationError,
        False,
        "STA executor not initialised — this is a server configuration error.",
    ),
    0x80010105: (
        "COM_SERVER_FAULT",
        BridgeConnectionError,
        True,
        "ControlDesk reported a server fault. Restart ControlDesk if the issue persists.",
    ),
    0x800706BA: (
        "COM_SERVER_UNAVAILABLE",
        BridgeConnectionError,
        True,
        "ControlDesk is not running. Start ControlDesk and retry.",
    ),
    # ── COM server lifecycle ───────────────────────────────────────────────────
    0x80004007: (
        "COM_SERVER_STOPPING",
        BridgeConnectionError,
        True,
        "ControlDesk is shutting down. Wait and call controldesk_app_start_or_attach.",
    ),
    # ── IDispatch / Automation errors ─────────────────────────────────────────
    0x80020003: (
        "COM_VERSION_MISMATCH",
        BridgeVersionError,
        False,
        "Method not found — verify the ControlDesk version matches CONTROLDESK_VERSION.",
    ),
    0x80020005: (
        "BRIDGE_INVALID_ARGUMENT",
        BridgeOperationError,
        False,
        "Wrong argument type passed to ControlDesk. Fix the parameter value.",
    ),
    0x80020006: (
        "COM_VERSION_MISMATCH",
        BridgeVersionError,
        False,
        "Property name not recognised — verify the ControlDesk version matches CONTROLDESK_VERSION.",
    ),
    0x80020009: (
        "BRIDGE_OPERATION_FAILED",
        BridgeOperationError,
        False,
        "Check the ControlDesk Messages pane and use the correlation_id to locate the log entry.",
    ),
    0x8002000B: (
        "BRIDGE_INVALID_ARGUMENT",
        BridgeOperationError,
        False,
        "Collection index out of range. Check the parameter value.",
    ),
    0x8002000E: (
        "BRIDGE_INVALID_ARGUMENT",
        BridgeOperationError,
        False,
        "Wrong number of arguments. Fix the tool call.",
    ),
    # ── Generic Win32 / system errors ─────────────────────────────────────────
    0x80004002: (
        "BRIDGE_OPERATION_FAILED",
        BridgeOperationError,
        False,
        "Interface not supported on this COM object.",
    ),
    0x80000001: (
        "BRIDGE_OPERATION_FAILED",
        BridgeOperationError,
        False,
        "Method not implemented in this ControlDesk version.",
    ),
    0x80004005: (
        "BRIDGE_OPERATION_FAILED",
        BridgeOperationError,
        False,
        "Check the ControlDesk Messages pane and use the correlation_id to locate the log entry.",
    ),
    0x80070005: (
        "BRIDGE_ACCESS_DENIED",
        BridgeOperationError,
        False,
        "Check dSPACE license and user rights.",
    ),
    0x8007000E: (
        "BRIDGE_OUT_OF_MEMORY",
        BridgeOperationError,
        True,
        "Free resources and retry.",
    ),
    0x80040112: (
        "BRIDGE_NOT_LICENSED",
        BridgeOperationError,
        False,
        "Install the correct dSPACE license.",
    ),
    0x80070057: (
        "BRIDGE_INVALID_ARGUMENT",
        BridgeOperationError,
        False,
        "Invalid argument passed to ControlDesk. Fix the parameter value.",
    ),
}


def _extract_description(exc: Exception) -> str:
    """Extract the most informative description from a COM exception.

    For pywintypes.com_error the layout is:
      args[0]    — HRESULT (int)
      args[1]    — short Win32 message table description
      args[2]    — IErrorInfo tuple (facility, iid, description, helpfile, helpcontext)
      args[2][2] — IErrorInfo.Description set by ControlDesk (most useful for DISP_E_EXCEPTION)
    """
    try:
        if exc.args and len(exc.args) >= 3:
            error_info = exc.args[2]
            if error_info and len(error_info) >= 3 and error_info[2]:
                return str(error_info[2])
    except (IndexError, TypeError):
        pass
    return str(exc)


def map_com_error(
    exc: Exception,
    *,
    interface: str = "",
    method: str = "",
    correlation_id: str = "",
) -> BridgeError:
    """Convert a COM exception to a typed :class:`BridgeError`.

    This function is intended for use inside ``com_bridge/domains/`` wrappers
    where the COM interface name and method name are known.  Higher-level code
    (tools, guard) should not call this directly.

    Args:
        exc: The caught exception (pywintypes.com_error or generic).
        interface: COM interface name for diagnostics (e.g. ``"IXaApplication"``).
        method: COM method name for diagnostics (e.g. ``"Version"``).
        correlation_id: UUID that links this error to an ILoLog entry.

    Returns:
        A :class:`BridgeError` subclass with HRESULT metadata attached.
    """
    hresult: int | None = None
    detail = _extract_description(exc)

    # pywintypes.com_error stores the HRESULT in args[0] as a signed int.
    if exc.args:
        raw = exc.args[0]
        if isinstance(raw, int):
            hresult = raw & _HRESULT_MASK

    location = f"{interface}.{method}" if interface or method else "<unknown>"

    # ── 1. Exact HRESULT lookup ────────────────────────────────────────────────
    if hresult is not None and hresult in _HRESULT_MAP:
        error_code, cls, retryable, recovery_hint = _HRESULT_MAP[hresult]
        result = cls(
            f"COM error {error_code} on {location}: {detail}",
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )
        result.correlation_id = correlation_id
        return result

    # ── 2. Facility-based fallback ─────────────────────────────────────────────
    if hresult is not None:
        facility = (hresult >> 16) & 0x1FFF
        if facility == _FACILITY_RPC:
            result = BridgeConnectionError(
                f"RPC connection error on {location}: {detail}",
                error_code="COM_DISCONNECTED",
                retryable=True,
                recovery_hint="Call controldesk_app_start_or_attach to re-establish the COM connection.",
                hresult=hresult,
            )
            result.correlation_id = correlation_id
            return result
        if facility == _FACILITY_DISPATCH:
            result = BridgeVersionError(
                f"IDispatch error on {location}: {detail}",
                error_code="COM_VERSION_MISMATCH",
                retryable=False,
                recovery_hint=("Verify the ControlDesk version matches CONTROLDESK_VERSION."),
                hresult=hresult,
            )
            result.correlation_id = correlation_id
            return result

    # ── 3. Unknown / non-COM exception ────────────────────────────────────────
    result = BridgeOperationError(
        f"Unexpected COM error on {location}: {detail}",
        error_code="BRIDGE_UNKNOWN",
        retryable=False,
        recovery_hint="Inspect the ControlDesk log via the correlation_id.",
        hresult=hresult,
    )
    result.correlation_id = correlation_id
    return result
