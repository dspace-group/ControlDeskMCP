"""COM domain wrappers — one module per ControlDesk COM interface domain."""

from __future__ import annotations

from controldesk_mcp.com_bridge.domains import (
    application_com,  # noqa: F401
    bus_logging_com,  # noqa: F401
    bus_monitor_com,  # noqa: F401
    bus_replay_com,  # noqa: F401
    calibration_com,  # noqa: F401
    ecu_diagnostics_com,  # noqa: F401
    instrument_com,  # noqa: F401
    layout_com,  # noqa: F401
    measurement_com,  # noqa: F401
    platform_com,  # noqa: F401
    project_com,  # noqa: F401
    recorder_com,  # noqa: F401
    tool_window_com,  # noqa: F401
    variable_com,  # noqa: F401
)

__all__ = [
    "application_com",
    "bus_logging_com",
    "bus_monitor_com",
    "bus_replay_com",
    "calibration_com",
    "ecu_diagnostics_com",
    "instrument_com",
    "layout_com",
    "measurement_com",
    "platform_com",
    "project_com",
    "recorder_com",
    "tool_window_com",
    "variable_com",
]
