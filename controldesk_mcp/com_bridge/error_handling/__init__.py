"""Error handling components for the COM bridge.

Groups all error-related concerns in one place:
  hresult         — HRESULT → exception classifier
  circuit_breaker — per-operation failure counter
  preconditions   — domain-state checks before COM calls
  guard           — async timeout, retry, and circuit-breaking wrapper
"""

from __future__ import annotations

from controldesk_mcp.com_bridge.error_handling.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    get_breaker,
)
from controldesk_mcp.com_bridge.error_handling.guard import com_guard, guarded_dispatch
from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.error_handling.preconditions import (
    check_64bit_process,
    check_calibration_started,
    check_experiment_active,
    check_measurement_not_active,
    check_platform_connected,
)

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "get_breaker",
    "com_guard",
    "guarded_dispatch",
    "map_com_error",
    "check_64bit_process",
    "check_calibration_started",
    "check_experiment_active",
    "check_measurement_not_active",
    "check_platform_connected",
]
