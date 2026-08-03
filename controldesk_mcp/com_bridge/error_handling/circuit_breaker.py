"""Per-operation circuit breaker for COM call protection.

Prevents cascading COM calls to a frozen or unavailable ControlDesk instance
by short-circuiting repeated calls after the failure threshold is reached.

States:
    CLOSED    — normal operation; failures are counted.
    OPEN      — circuit tripped; calls rejected until cool-down expires.
    HALF_OPEN — probe state after cool-down; one call is allowed through.

Configuration defaults (per operation):
    failure_threshold = 3   consecutive failures within the rolling window
    window_seconds    = 60  rolling window for counting failures
    cooldown_seconds  = 30  time in OPEN state before probing

Operations with circuit breakers:
    start_controldesk, platform_connect, experiment_load_and_activate
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from threading import Lock

from controldesk_mcp.com_bridge.errors import BridgeCircuitOpenError


class CircuitState(Enum):
    CLOSED = auto()
    OPEN = auto()
    HALF_OPEN = auto()


@dataclass
class CircuitBreaker:
    """Failure-counting circuit breaker for a single MCP operation.

    All methods are thread-safe (protected by an internal :class:`threading.Lock`).

    Args:
        operation: MCP tool name used in error messages and circuit registry.
        failure_threshold: Number of failures within *window_seconds* to trip the circuit.
        window_seconds: Rolling window length for counting failures.
        cooldown_seconds: Time the circuit stays OPEN before moving to HALF_OPEN.
    """

    operation: str
    failure_threshold: int = 3
    window_seconds: float = 60.0
    cooldown_seconds: float = 30.0

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False, repr=False)
    _failure_timestamps: list[float] = field(default_factory=list, init=False, repr=False)
    _opened_at: float | None = field(default=None, init=False, repr=False)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def state(self) -> CircuitState:
        """Current circuit state (thread-safe read)."""
        with self._lock:
            return self._state

    def is_call_allowed(self) -> bool:
        """Return ``True`` if a call may proceed, ``False`` if the circuit is OPEN.

        Automatically transitions OPEN → HALF_OPEN when the cool-down expires.
        """
        with self._lock:
            return self._evaluate(time.monotonic())

    def record_success(self) -> None:
        """Record a successful call; resets the circuit to CLOSED."""
        with self._lock:
            self._failure_timestamps.clear()
            self._state = CircuitState.CLOSED
            self._opened_at = None

    def record_failure(self) -> None:
        """Record a failed call; trips the circuit if the threshold is reached."""
        with self._lock:
            now = time.monotonic()
            cutoff = now - self.window_seconds
            self._failure_timestamps = [t for t in self._failure_timestamps if t > cutoff]
            self._failure_timestamps.append(now)

            if self._state is CircuitState.HALF_OPEN:
                self._open(now)
            elif len(self._failure_timestamps) >= self.failure_threshold:
                self._open(now)

    def assert_call_allowed(self) -> None:
        """Raise :class:`BridgeCircuitOpenError` if the circuit is OPEN.

        Call this before any protected COM dispatch.
        """
        with self._lock:
            now = time.monotonic()
            if not self._evaluate(now):
                remaining = self.cooldown_seconds - (now - (self._opened_at or now))
                remaining = max(0.0, remaining)
                raise BridgeCircuitOpenError(
                    f"Circuit OPEN for '{self.operation}' — cool-down expires in {remaining:.0f} s.",
                    recovery_hint=(
                        f"Wait {remaining:.0f} s and retry, or call "
                        "controldesk_app_start_or_attach to reset the connection."
                    ),
                )

    def _evaluate(self, now: float) -> bool:
        if self._state is CircuitState.CLOSED:
            return True
        if self._state is CircuitState.OPEN:
            if self._opened_at is not None and (now - self._opened_at) >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
                return True
            return False
        return True  # HALF_OPEN — allow one probe

    def _open(self, now: float) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = now


# ── Registry of guarded operations ────────────────────────────────────────────

_breakers: dict[str, CircuitBreaker] = {
    "controldesk_app_start_or_attach": CircuitBreaker("controldesk_app_start_or_attach"),
    "platform_connect": CircuitBreaker("platform_connect"),
    "experiment_load_and_activate": CircuitBreaker("experiment_load_and_activate"),
}


def get_breaker(operation: str) -> CircuitBreaker | None:
    """Return the :class:`CircuitBreaker` for *operation*, or ``None`` if not guarded."""
    return _breakers.get(operation)
