"""Envelope builder — converts a BridgeError into a structured MCP error response.

Converts any :class:`BridgeError` subclass into a structured :class:`ErrorEnvelope`
and produces the JSON payload that MCP tool handlers return on failure.

The builder is the single place where:
  - BridgeError subclass is mapped to an ``ErrorEnvelope.category`` string.
  - ``to_markdown()`` generates the human-readable card.
  - ``structuredContent`` is populated for LLM agent parsing.

Usage::

    from controldesk_mcp.models.envelope_builder import build_envelope, tool_error_result

    # In a tool handler:
    except BridgeError as exc:
        return tool_error_result(exc)

    # When a correlation_id is available:
    except BridgeError as exc:
        return tool_error_result(exc, correlation_id=corr_id)
"""

from __future__ import annotations

from controldesk_mcp.com_bridge.errors import (
    BridgeCircuitOpenError,
    BridgeConnectionError,
    BridgeError,
    BridgeOperationError,
    BridgePreconditionError,
    BridgeTimeoutError,
    BridgeUiBlockedError,
    BridgeVersionError,
)
from controldesk_mcp.models.errors import ErrorEnvelope

# Mapping from BridgeError subclass → ErrorEnvelope.category
_CATEGORY_MAP: dict[type[BridgeError], str] = {
    BridgeConnectionError: "CONNECTION",
    BridgeUiBlockedError: "UI_BLOCKING",
    BridgeCircuitOpenError: "CIRCUIT",
    BridgePreconditionError: "PRECONDITION",
    BridgeTimeoutError: "TIMEOUT",
    BridgeVersionError: "VERSION_MISMATCH",
    BridgeOperationError: "OPERATION",
}

# error_code override → category (for codes that carry more specific category info)
_CODE_CATEGORY_MAP: dict[str, str] = {
    "BRIDGE_ACCESS_DENIED": "SYSTEM",
    "BRIDGE_OUT_OF_MEMORY": "SYSTEM",
    "BRIDGE_NOT_LICENSED": "SYSTEM",
    "BRIDGE_BAD_INPUT": "INPUT_VALIDATION",
    "BRIDGE_UNKNOWN": "UNKNOWN",
}


def _resolve_category(exc: BridgeError) -> str:
    """Determine the ErrorEnvelope category for *exc*."""
    if exc.error_code in _CODE_CATEGORY_MAP:
        return _CODE_CATEGORY_MAP[exc.error_code]
    category = _CATEGORY_MAP.get(type(exc))
    if category:
        return category
    for cls in type(exc).__mro__:
        if cls in _CATEGORY_MAP:
            return _CATEGORY_MAP[cls]
    return "UNKNOWN"


def build_envelope(
    exc: BridgeError,
    *,
    correlation_id: str = "",
    com_interface: str | None = None,
    com_method: str | None = None,
) -> ErrorEnvelope:
    """Build an :class:`ErrorEnvelope` from a :class:`BridgeError`.

    Args:
        exc: The caught BridgeError subclass.
        correlation_id: UUID linking this error to an ILoLog entry.
        com_interface: COM interface name, if available from the domain wrapper.
        com_method: COM method name, if available from the domain wrapper.

    Returns:
        A fully-populated :class:`ErrorEnvelope`.
    """
    category = _resolve_category(exc)

    detail = ""
    if exc.hresult is not None:
        detail = f"HRESULT=0x{exc.hresult:08X}"

    # Fall back to the correlation_id stored on the exception when the caller
    # does not pass one explicitly (the common case in service code).
    effective_corr_id = correlation_id or getattr(exc, "correlation_id", "")

    return ErrorEnvelope(
        error_code=exc.error_code,
        category=category,  # type: ignore[arg-type]
        message=str(exc),
        detail=detail,
        hresult=exc.hresult,
        com_interface=com_interface,
        com_method=com_method,
        retryable=exc.retryable,
        recovery_hint=exc.recovery_hint,
        correlation_id=effective_corr_id,
    )


def tool_error_result(
    exc: BridgeError,
    *,
    correlation_id: str = "",
    com_interface: str | None = None,
    com_method: str | None = None,
) -> str:
    """Return a JSON-serialised error payload suitable for returning from an MCP tool.

    This produces the ``model_dump_json()`` string that the tool handler returns
    when an error is caught.  The JSON contains both the ``ErrorEnvelope`` fields
    and a ``markdown`` key with the human-readable card.

    Args:
        exc: The caught :class:`BridgeError`.
        correlation_id: UUID linking to an ILoLog entry (empty if not available).
        com_interface: COM interface name for context (optional, from domain wrapper).
        com_method: COM method name for context (optional, from domain wrapper).

    Returns:
        JSON string.
    """
    envelope = build_envelope(
        exc,
        correlation_id=correlation_id,
        com_interface=com_interface,
        com_method=com_method,
    )
    payload = envelope.model_dump()
    payload["markdown"] = envelope.to_markdown()
    import json  # noqa: PLC0415

    return json.dumps(payload)
