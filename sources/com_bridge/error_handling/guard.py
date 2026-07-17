"""Async COM guard — timeout enforcement, HRESULT classification, retry, and circuit breaking.

Wraps every COM dispatch call with:
  - correlation ID generation (UUID4 for tracing retries across MCP server log lines)
  - asyncio timeout enforcement (catches UI-blocking modal dialogs)
  - HRESULT classification via :func:`map_com_error`
  - exponential backoff retry for transient / retryable errors
  - circuit breaker integration (records success / failure per operation)

Two public interfaces:

``com_guard`` — per-call async context manager (single attempt, no retry)::

    corr_id = str(uuid.uuid4())
    async with com_guard("start_controldesk", corr_id=corr_id):
        result = await com_bridge.dispatch(conn.connect, version)
``guarded_dispatch`` — retry-capable helper::

    result = await guarded_dispatch(fn, *args, operation="start_controldesk")

Retry schedule (retryable errors only):
    Attempt 1 → fail
    Wait  500 ms ± 200 ms jitter → Attempt 2
    Wait 1000 ms ± 200 ms jitter → Attempt 3
    → raise final BridgeError
"""

from __future__ import annotations

import asyncio
import random
import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable

from sources.com_bridge.error_handling.circuit_breaker import CircuitBreaker, get_breaker
from sources.com_bridge.error_handling.hresult import map_com_error
from sources.com_bridge.errors import BridgeError, BridgeTimeoutError
from sources.utils.logger import get_logger

_log = get_logger(__name__)

# Retry configuration
_MAX_ATTEMPTS: int = 3
_BASE_DELAY_MS: int = 500
_JITTER_MS: int = 200


def _jittered_delay(attempt: int) -> float:
    """Return seconds to wait before *attempt* (1-based), with ±jitter."""
    base_ms = _BASE_DELAY_MS * attempt
    jitter_ms = random.randint(-_JITTER_MS, _JITTER_MS)  # noqa: S311 — non-crypto use
    return max(0.0, (base_ms + jitter_ms) / 1000.0)


@asynccontextmanager
async def com_guard(
    operation: str,
    *,
    corr_id: str,
    timeout_ms: int = 8000,
) -> AsyncIterator[None]:
    """Single-attempt COM guard: timeout enforcement + HRESULT classification.

    Wraps one COM call with an :func:`asyncio.timeout` and converts any raw
    ``pywintypes.com_error`` or :class:`asyncio.TimeoutError` into a typed
    :class:`BridgeError` subclass.  Does **not** retry — use :func:`guarded_dispatch`
    for retry behaviour.

    Args:
        operation: MCP tool name that triggered this COM call (used in error messages
            and circuit breaker lookup).
        corr_id: UUID that links the error to an ILoLog entry.
        timeout_ms: Wall-clock timeout for the enclosed COM call.

    Raises:
        BridgeTimeoutError: The call exceeded *timeout_ms*.
        BridgeError subclass: Any classified COM failure.
    """
    try:
        async with asyncio.timeout(timeout_ms / 1000.0):
            yield
    except asyncio.TimeoutError as exc:
        _timeout_exc = BridgeTimeoutError(
            f"'{operation}' timed out after {timeout_ms} ms — "
            "ControlDesk may be waiting for user input.",
            error_code="COM_TIMEOUT",
            recovery_hint=(
                "Dismiss any open ControlDesk dialog, "
                "or set Platform.DisplayStatusInformation = False before long operations."
            ),
        )
        _timeout_exc.correlation_id = corr_id
        raise _timeout_exc from exc
    except BridgeError as exc:
        exc.correlation_id = exc.correlation_id or corr_id
        raise  # already classified upstream
    except Exception as exc:  # noqa: BLE001
        raise map_com_error(exc, interface=operation, correlation_id=corr_id) from exc


# ── Retry-capable dispatch helper ─────────────────────────────────────────────


async def guarded_dispatch(
    fn: Callable[..., Any],
    *args: Any,
    operation: str,
    timeout_ms: int = 8000,
    max_attempts: int = _MAX_ATTEMPTS,
) -> Any:
    """Dispatch *fn(*args)* through the COM guard with retry and circuit breaking.

    This is the primary entry point for tool code.  It:
    1. Checks the circuit breaker (raises :class:`BridgeCircuitOpenError` if OPEN).
    2. Runs *fn* inside :func:`com_guard` for timeout + classification.
    3. On retryable failure, waits with exponential backoff + jitter and retries.
    4. Records success / failure in the circuit breaker after the final outcome.

    Args:
        fn: Callable to execute on the STA thread via :func:`com_bridge.dispatch`.
        *args: Positional arguments forwarded to *fn*.
        operation: MCP tool name — used as the circuit breaker key and in error messages.
            Must match the registry key in :func:`get_breaker` for circuit breaking to apply.
        timeout_ms: Per-attempt timeout in milliseconds.
        max_attempts: Maximum number of attempts before re-raising the error.

    Returns:
        The return value of *fn*.

    Raises:
        BridgeCircuitOpenError: Circuit is OPEN for this operation.
        BridgeError subclass: The last COM error after all retry attempts are exhausted.
    """
    import sources.com_bridge as _bridge  # noqa: PLC0415 — deferred to avoid circular import

    breaker: CircuitBreaker | None = get_breaker(operation)

    if breaker is not None:
        breaker.assert_call_allowed()

    corr_id = str(uuid.uuid4())
    _log.debug("guarded_dispatch: %s start corr=%s", operation, corr_id)

    last_exc: BridgeError | None = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            delay = _jittered_delay(attempt - 1)
            _log.debug(
                "guarded_dispatch: retry %d/%d after %.3f s (corr=%s)",
                attempt,
                max_attempts,
                delay,
                corr_id,
            )
            await asyncio.sleep(delay)

        try:
            async with com_guard(operation, corr_id=corr_id, timeout_ms=timeout_ms):
                result = await _bridge.dispatch(fn, *args, timeout_ms=timeout_ms)

            if breaker is not None:
                breaker.record_success()
            _log.debug("guarded_dispatch: %s ok corr=%s", operation, corr_id)
            return result

        except BridgeError as exc:
            last_exc = exc
            if breaker is not None:
                breaker.record_failure()
            _log.warning(
                "guarded_dispatch: error on %s attempt %d/%d [%s] corr=%s",
                operation,
                attempt,
                max_attempts,
                exc.error_code,
                corr_id,
            )
            if attempt >= max_attempts or not exc.retryable:
                exc.correlation_id = exc.correlation_id or corr_id
                raise

    if last_exc is not None:
        raise last_exc
