"""COM wrappers for ControlDesk Bus Logging interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry point:
  app.BusNavigator.Systems[idx].BusPlatforms[bus_platform_idx]
    .{CANBusSystem|LINBusSystem|FlexRayBusSystem|EthernetBusSystem}
    .PhysicalBusAccesses[bus_access_idx].Loggers
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgePreconditionError

_BUS_TYPE_PROPERTY: dict[str, str] = {
    "CAN": "CANBusSystem",
    "LIN": "LINBusSystem",
    "FlexRay": "FlexRayBusSystem",
    "Ethernet": "EthernetBusSystem",
}

_TIME_AXIS_MAP: dict[str, int] = {
    "Absolute": 0,
    "Relative": 1,
}

_ROLLING_TYPE_MAP: dict[str, int] = {
    "Time": 0,
    "Size": 1,
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _get_physical_bus_access(
    app: Any,
    system_index: int,
    bus_platform_index: int,
    bus_type: str,
    physical_bus_access_index: int,
) -> Any:
    """Navigate the BusNavigator hierarchy to a PhysicalBusAccess."""
    try:
        bus_nav = app.BusNavigator
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="BusNavigator") from exc

    try:
        system = bus_nav.Systems.Item(system_index)
    except Exception as exc:
        raise BridgePreconditionError(
            f"System index {system_index} not found in BusNavigator.",
            error_code="BRIDGE_BAD_INPUT",
            recovery_hint="Check system_index; use 0 for transceiver, 1 for receiver.",
        ) from exc

    bus_prop = _BUS_TYPE_PROPERTY.get(bus_type)
    if bus_prop is None:
        msg = f"Unknown bus_type '{bus_type}'. Use CAN, LIN, FlexRay, or Ethernet."
        raise BridgePreconditionError(
            msg,
            error_code="BRIDGE_BAD_INPUT",
            recovery_hint="Pass one of: CAN, LIN, FlexRay, Ethernet.",
        )

    try:
        platform = system.BusPlatforms.Item(bus_platform_index)
        bus_system = getattr(platform, bus_prop)
        pba = bus_system.PhysicalBusAccesses.Item(physical_bus_access_index)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Bus platform {bus_platform_index} / {bus_type} / physical access {physical_bus_access_index} not found.",
            error_code="BRIDGE_BAD_INPUT",
            recovery_hint="Verify bus_platform_index, bus_type, and physical_bus_access_index.",
        ) from exc

    return pba


def _get_logger_by_name(loggers: Any, logger_name: str) -> Any:
    """Find a logger by name in a Loggers collection."""
    try:
        for i in range(loggers.Count):
            lgr = loggers.Item(i)
            if lgr.Name == logger_name:
                return lgr
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLoggers", method="Item") from exc
    raise BridgePreconditionError(
        f"Logger '{logger_name}' not found.",
        error_code="BRIDGE_BAD_INPUT",
        recovery_hint=(f"Create the logger first with bus_logger_create(logger_name='{logger_name}')."),
    )


# ── Logger CRUD ────────────────────────────────────────────────────────────────


def create_logger(
    app: Any,
    logger_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    try:
        pba.Loggers.Add(logger_name)
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLoggers", method="Add") from exc

    return {
        "created": True,
        "logger_name": logger_name,
        "system_index": system_index,
        "bus_type": bus_type,
        "state": "Stopped",
        "activated": False,
        "timestamp_utc": _utc_now(),
    }


def configure_logger(
    app: Any,
    logger_name: str,
    system_index: int,
    bus_type: str,
    log_file_full_path: str,
    overwrite_existing: bool = True,
    max_duration_seconds: float = 0.0,
    enable_bus_statistics: bool = False,
    continuous_ring_mode: bool = False,
    file_rolling_enabled: bool = False,
    file_rolling_type: str = "Time",
    file_rolling_interval_seconds: float = 3600.0,
    time_axis_mode: str = "Relative",
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    lgr = _get_logger_by_name(pba.Loggers, logger_name)
    try:
        cfg = lgr.Configuration
        cfg.LogFileFullPath = log_file_full_path
        cfg.OverwriteMode = overwrite_existing
        cfg.Duration = max_duration_seconds
        cfg.EnableBusStatistics = enable_bus_statistics
        cfg.Continuous = continuous_ring_mode
        cfg.FileRollingEnabled = file_rolling_enabled
        if file_rolling_enabled:
            rolling_int = _ROLLING_TYPE_MAP.get(file_rolling_type, 0)
            cfg.FileRollingType = rolling_int
            if file_rolling_type == "Size":
                cfg.FileRollingSize = file_rolling_interval_seconds
            else:
                cfg.FileRollingTime = file_rolling_interval_seconds
        axis_int = _TIME_AXIS_MAP.get(time_axis_mode, 1)
        cfg.TimeAxis = axis_int
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLogger", method="Configuration") from exc

    return {
        "configured": True,
        "logger_name": logger_name,
        "log_file_full_path": log_file_full_path,
        "overwrite_existing": overwrite_existing,
        "max_duration_seconds": max_duration_seconds,
        "enable_bus_statistics": enable_bus_statistics,
        "continuous_ring_mode": continuous_ring_mode,
        "file_rolling_enabled": file_rolling_enabled,
        "time_axis_mode": time_axis_mode,
        "timestamp_utc": _utc_now(),
    }


def start_logger(
    app: Any,
    logger_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    lgr = _get_logger_by_name(pba.Loggers, logger_name)
    try:
        lgr.Activated = True
        lgr.Start()
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLogger", method="Start") from exc

    return {
        "started": True,
        "logger_name": logger_name,
        "state": "Running",
        "activated": True,
        "timestamp_utc": _utc_now(),
    }


def stop_logger(
    app: Any,
    logger_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    lgr = _get_logger_by_name(pba.Loggers, logger_name)
    try:
        lgr.Stop()
        lgr.Activated = False
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLogger", method="Stop") from exc

    return {
        "stopped": True,
        "logger_name": logger_name,
        "state": "Stopped",
        "activated": False,
        "timestamp_utc": _utc_now(),
    }


def get_logger_state(
    app: Any,
    logger_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    lgr = _get_logger_by_name(pba.Loggers, logger_name)
    try:
        state_raw = lgr.State
        activated = bool(lgr.Activated)
        file_path = str(lgr.Configuration.LogFileFullPath)
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLogger", method="State") from exc

    is_running = state_raw == 1 or str(state_raw).lower() == "running"
    state_str = "Running" if is_running else "Stopped"

    return {
        "logger_name": logger_name,
        "state": state_str,
        "is_running": is_running,
        "activated": activated,
        "log_file_path": file_path,
        "timestamp_utc": _utc_now(),
    }


def list_loggers(
    app: Any,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    try:
        loggers_com = pba.Loggers
        items: list[dict[str, Any]] = []
        for i in range(loggers_com.Count):
            lgr = loggers_com.Item(i)
            state_raw = lgr.State
            is_running = state_raw == 1 or str(state_raw).lower() == "running"
            items.append(
                {
                    "name": str(lgr.Name),
                    "state": "Running" if is_running else "Stopped",
                    "activated": bool(lgr.Activated),
                    "log_file_path": str(lgr.Configuration.LogFileFullPath),
                }
            )
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLoggers", method="Enumerate") from exc

    return {
        "system_index": system_index,
        "bus_type": bus_type,
        "total_count": len(items),
        "loggers": items,
    }


def remove_logger(
    app: Any,
    logger_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    lgr = _get_logger_by_name(pba.Loggers, logger_name)
    try:
        lgr.Remove()
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLogger", method="Remove") from exc

    return {
        "removed": True,
        "logger_name": logger_name,
        "timestamp_utc": _utc_now(),
    }


def clear_all_loggers(
    app: Any,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    try:
        count = pba.Loggers.Count
        pba.Loggers.Clear()
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLoggers", method="Clear") from exc

    return {
        "cleared": True,
        "loggers_removed": count,
        "system_index": system_index,
        "bus_type": bus_type,
        "timestamp_utc": _utc_now(),
    }


def set_logger_activated(
    app: Any,
    logger_name: str,
    system_index: int,
    bus_type: str,
    activated: bool,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    lgr = _get_logger_by_name(pba.Loggers, logger_name)
    try:
        prev = bool(lgr.Activated)
        lgr.Activated = activated
        state_raw = lgr.State
        is_running = state_raw == 1 or str(state_raw).lower() == "running"
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLogger", method="Activated") from exc

    return {
        "activated": activated,
        "logger_name": logger_name,
        "state": "Running" if is_running else "Stopped",
        "previous_activated": prev,
        "timestamp_utc": _utc_now(),
    }


# ── Filter CRUD ────────────────────────────────────────────────────────────────


def _get_filter_by_name(filters: Any, filter_name: str) -> Any:
    """Find a filter by name in a Filters collection."""
    try:
        for i in range(filters.Count):
            flt = filters.Item(i)
            if flt.Name == filter_name:
                return flt
    except Exception as exc:
        raise map_com_error(exc, interface="IBnFilters", method="Item") from exc
    raise BridgePreconditionError(
        f"Filter '{filter_name}' not found.",
        error_code="BRIDGE_BAD_INPUT",
        recovery_hint=(f"Create the filter first with bus_filter_create(filter_name='{filter_name}')."),
    )


def create_filter(
    app: Any,
    filter_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    try:
        pba.Filters.Add(filter_name)
    except Exception as exc:
        raise map_com_error(exc, interface="IBnFilters", method="Add") from exc

    return {
        "created": True,
        "filter_name": filter_name,
        "system_index": system_index,
        "bus_type": bus_type,
        "state": "Stopped",
        "activated": False,
        "timestamp_utc": _utc_now(),
    }


def configure_filter(
    app: Any,
    filter_name: str,
    system_index: int,
    bus_type: str,
    filter_mode: str = "Pass",
    message_id: int = 0,
    message_mask: int = 0x7FF,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Return metadata about a filter's sub-collections.

    Note: IBnCANFilter is a grouping container only. Message-level filtering
    (FilterMode, MessageID, MessageMask) is not accessible via the public COM API.
    This tool returns the current sub-collection counts for diagnostic purposes.
    """
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    flt = _get_filter_by_name(pba.Filters, filter_name)
    try:
        loggers_count = flt.Loggers.Count
        monitors_count = flt.Monitors.Count
        replays_count = flt.Replays.Count
    except Exception as exc:
        raise map_com_error(exc, interface="IBnFilter", method="Configure") from exc

    return {
        "filter_name": filter_name,
        "loggers_count": loggers_count,
        "monitors_count": monitors_count,
        "replays_count": replays_count,
        "note": (
            "IBnCANFilter is a grouping container. "
            "Message-level filtering (FilterMode, MessageID, MessageMask) "
            "is not available via the public COM API."
        ),
        "timestamp_utc": _utc_now(),
    }


def start_filter(
    app: Any,
    filter_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Start all loggers and replays that belong to this filter group."""
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    flt = _get_filter_by_name(pba.Filters, filter_name)
    started_loggers: list[str] = []
    started_replays: list[str] = []
    try:
        for i in range(flt.Loggers.Count):
            lgr = flt.Loggers.Item(i)
            lgr.Start()
            started_loggers.append(str(lgr.Name))
        for i in range(flt.Replays.Count):
            rep = flt.Replays.Item(i)
            rep.Start()
            started_replays.append(str(rep.Name))
    except Exception as exc:
        raise map_com_error(exc, interface="IBnFilter", method="Start") from exc

    return {
        "started": True,
        "filter_name": filter_name,
        "started_loggers": started_loggers,
        "started_replays": started_replays,
        "timestamp_utc": _utc_now(),
    }


def stop_filter(
    app: Any,
    filter_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Stop all loggers and replays that belong to this filter group."""
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    flt = _get_filter_by_name(pba.Filters, filter_name)
    stopped_loggers: list[str] = []
    stopped_replays: list[str] = []
    try:
        for i in range(flt.Loggers.Count):
            lgr = flt.Loggers.Item(i)
            lgr.Stop()
            stopped_loggers.append(str(lgr.Name))
        for i in range(flt.Replays.Count):
            rep = flt.Replays.Item(i)
            rep.Stop()
            stopped_replays.append(str(rep.Name))
    except Exception as exc:
        raise map_com_error(exc, interface="IBnFilter", method="Stop") from exc

    return {
        "stopped": True,
        "filter_name": filter_name,
        "stopped_loggers": stopped_loggers,
        "stopped_replays": stopped_replays,
        "timestamp_utc": _utc_now(),
    }


def list_filters(
    app: Any,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    try:
        filters_com = pba.Filters
        items: list[dict[str, Any]] = []
        for i in range(filters_com.Count):
            flt = filters_com.Item(i)
            items.append(
                {
                    "name": str(flt.Name),
                    "loggers_count": flt.Loggers.Count,
                    "monitors_count": flt.Monitors.Count,
                    "replays_count": flt.Replays.Count,
                }
            )
    except Exception as exc:
        raise map_com_error(exc, interface="IBnFilters", method="Enumerate") from exc

    return {
        "total_filters": len(items),
        "filters": items,
        "timestamp_utc": _utc_now(),
    }


def remove_filter(
    app: Any,
    filter_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    flt = _get_filter_by_name(pba.Filters, filter_name)
    try:
        flt.Remove()
    except Exception as exc:
        raise map_com_error(exc, interface="IBnFilter", method="Remove") from exc

    return {
        "removed": True,
        "filter_name": filter_name,
        "timestamp_utc": _utc_now(),
    }


# ── rename_logger ─────────────────────────────────────────────────────────────


def rename_logger(
    app: Any,
    logger_name: str,
    new_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Rename an existing logger."""
    pba = _get_physical_bus_access(app, system_index, bus_platform_index, bus_type, physical_bus_access_index)
    lgr = _get_logger_by_name(pba.Loggers, logger_name)
    try:
        lgr.Name = new_name
        return {"old_name": logger_name, "new_name": new_name}
    except Exception as exc:
        raise map_com_error(exc, interface="IBnLogger", method="Name") from exc
