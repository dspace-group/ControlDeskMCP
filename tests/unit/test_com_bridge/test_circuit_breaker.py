"""Unit tests for controldesk_mcp.com_bridge.error_handling.circuit_breaker."""

from __future__ import annotations

import time

import pytest

from controldesk_mcp.com_bridge.error_handling.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_breaker,
)
from controldesk_mcp.com_bridge.errors import BridgeCircuitOpenError


class TestCircuitBreakerInitialState:
    def test_starts_closed(self) -> None:
        cb = CircuitBreaker("test_iface")
        assert cb.state is CircuitState.CLOSED

    def test_call_allowed_when_closed(self) -> None:
        cb = CircuitBreaker("test_iface")
        assert cb.is_call_allowed() is True

    def test_assert_does_not_raise_when_closed(self) -> None:
        cb = CircuitBreaker("test_iface")
        cb.assert_call_allowed()  # must not raise


class TestCircuitBreakerOpening:
    def test_trips_after_threshold_failures(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.CLOSED  # 2 < 3
        cb.record_failure()
        assert cb.state is CircuitState.OPEN

    def test_call_blocked_when_open(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=1)
        cb.record_failure()
        assert cb.is_call_allowed() is False

    def test_assert_raises_circuit_open_error(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=1)
        cb.record_failure()
        with pytest.raises(BridgeCircuitOpenError) as exc_info:
            cb.assert_call_allowed()
        assert exc_info.value.error_code == "CIRCUIT_OPEN"
        assert exc_info.value.retryable is True

    def test_failure_message_contains_interface(self) -> None:
        cb = CircuitBreaker("my_interface", failure_threshold=1)
        cb.record_failure()
        with pytest.raises(BridgeCircuitOpenError) as exc_info:
            cb.assert_call_allowed()
        assert "my_interface" in str(exc_info.value)


class TestCircuitBreakerRecovery:
    def test_success_resets_to_closed(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        cb.record_success()
        assert cb.state is CircuitState.CLOSED

    def test_success_clears_failure_count(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        # Two new failures should NOT trip (counter was cleared)
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.CLOSED


class TestCircuitBreakerHalfOpen:
    def test_transitions_to_half_open_after_cooldown(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        assert cb.state is CircuitState.OPEN
        time.sleep(0.1)
        assert cb.is_call_allowed() is True
        assert cb.state is CircuitState.HALF_OPEN

    def test_half_open_success_closes_circuit(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        time.sleep(0.1)
        cb.is_call_allowed()  # transitions to HALF_OPEN
        cb.record_success()
        assert cb.state is CircuitState.CLOSED

    def test_half_open_failure_reopens_circuit(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=1, cooldown_seconds=0.05)
        cb.record_failure()
        time.sleep(0.1)
        cb.is_call_allowed()  # transitions to HALF_OPEN
        cb.record_failure()
        assert cb.state is CircuitState.OPEN


class TestCircuitBreakerWindowPruning:
    def test_old_failures_outside_window_are_pruned(self) -> None:
        cb = CircuitBreaker("iface", failure_threshold=3, window_seconds=0.05)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.1)  # failures expire
        cb.record_failure()  # fresh failure — count resets to 1
        assert cb.state is CircuitState.CLOSED


class TestCircuitBreakerRegistry:
    def test_guarded_interfaces_exist(self) -> None:
        assert get_breaker("start_controldesk") is not None
        assert get_breaker("platform_connect") is not None
        assert get_breaker("experiment_load_and_activate") is not None

    def test_unguarded_interface_returns_none(self) -> None:
        assert get_breaker("some_unguarded_method") is None

    def test_registry_returns_circuit_breaker_instance(self) -> None:
        breaker = get_breaker("start_controldesk")
        assert isinstance(breaker, CircuitBreaker)
