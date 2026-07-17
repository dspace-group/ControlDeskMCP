"""COM wrappers for the ControlDesk BusNavigator Monitor interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry point:
  app.BusNavigator.Systems[idx]
    .BusPlatforms[bus_platform_idx]
    .{CANBusSystem|LINBusSystem|FlexRayBusSystem|EthernetBusSystem}
    .PhysicalBusAccesses[bus_access_idx]
    .Monitors
"""

from __future__ import annotations

from typing import Any

from sources.com_bridge.error_handling.hresult import map_com_error
from sources.com_bridge.errors import BridgePreconditionError

# Bus-type → COM property name on the bus platform object.
_BUS_TYPE_PROPERTY: dict[str, str] = {
    "CAN": "CANBusSystem",
    "LIN": "LINBusSystem",
    "FlexRay": "FlexRayBusSystem",
    "Ethernet": "EthernetBusSystem",
}

# BufferMode string → COM integer mapping.
_BUFFER_MODE_TO_INT: dict[str, int] = {
    "FixedBuffer": 0,
    "RingBuffer": 1,
}
_INT_TO_BUFFER_MODE: dict[int, str] = {v: k for k, v in _BUFFER_MODE_TO_INT.items()}

# TimeAxis string → COM integer mapping.
_TIME_AXIS_TO_INT: dict[str, int] = {
    "Relative": 0,
    "Absolute": 1,
    "RecordingTime": 2,
}

# Log file format → COM integer mapping (IBnLogFileFormat enum).
# 0=None, 1=CSV, 2=ASC, 3=MDF, 4=PCAPNG
_LOG_FILE_FORMAT: dict[str, int] = {
    ".asc": 2,
    ".csv": 1,
    ".mdf": 3,
    ".mf4": 3,
    ".pcapng": 4,
}

# Monitor RunState COM integer → string mapping.
_INT_TO_RUN_STATE: dict[int, str] = {
    0: "Stopped",
    1: "Running",
}


# ── Navigation helpers ────────────────────────────────────────────────────────


def _get_physical_bus_access(
    app: Any,
    system_index: int,
    bus_platform_index: int,
    bus_type: str,
    physical_bus_access_index: int,
) -> Any:
    """Navigate the BusNavigator hierarchy to a PhysicalBusAccess COM object."""
    try:
        bus_nav = app.BusNavigator
    except Exception as exc:
        raise BridgePreconditionError(
            "BusNavigator is not available. Ensure a BusNavigator project is open.",
            error_code="BRIDGE_NO_BUS_NAVIGATOR",
            recovery_hint="Open a BusNavigator project before using bus monitor tools.",
        ) from exc

    try:
        systems = bus_nav.Systems
        system = systems.Item(system_index)
    except Exception as exc:
        raise BridgePreconditionError(
            f"System at index {system_index} not found in BusNavigator.",
            error_code="BRIDGE_SYSTEM_NOT_FOUND",
            recovery_hint="Check system_index; use 0 for transceiver, 1 for receiver.",
        ) from exc

    try:
        bus_platform = system.BusPlatforms.Item(bus_platform_index)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Bus platform at index {bus_platform_index} not found on system {system_index}.",
            error_code="BRIDGE_BUS_PLATFORM_NOT_FOUND",
            recovery_hint="Check bus_platform_index; typically 0.",
        ) from exc

    prop_name = _BUS_TYPE_PROPERTY.get(bus_type)
    if not prop_name:
        raise BridgePreconditionError(
            f"Unsupported bus type '{bus_type}'. Must be one of: CAN, LIN, FlexRay, Ethernet.",
            error_code="BRIDGE_INVALID_BUS_TYPE",
            recovery_hint="Use CAN, LIN, FlexRay, or Ethernet.",
        )

    try:
        bus_system = getattr(bus_platform, prop_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Bus system '{prop_name}' not available on bus platform {bus_platform_index}.",
            error_code="BRIDGE_BUS_SYSTEM_NOT_FOUND",
            recovery_hint=f"Ensure the bus platform supports {bus_type}.",
        ) from exc

    try:
        pba = bus_system.PhysicalBusAccesses.Item(physical_bus_access_index)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Physical bus access at index {physical_bus_access_index} not found.",
            error_code="BRIDGE_BUS_ACCESS_NOT_FOUND",
            recovery_hint="Check physical_bus_access_index; typically 0.",
        ) from exc

    return pba


def _get_monitors(
    app: Any,
    system_index: int,
    bus_platform_index: int,
    bus_type: str,
    physical_bus_access_index: int,
) -> Any:
    """Return the Monitors collection from a PhysicalBusAccess."""
    pba = _get_physical_bus_access(
        app, system_index, bus_platform_index, bus_type, physical_bus_access_index
    )
    try:
        return pba.Monitors
    except Exception as exc:
        raise map_com_error(exc, interface="IBnPhysicalBusAccess", method="Monitors") from exc


def _get_monitor_by_name(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> Any:
    """Retrieve a specific monitor by name from the Monitors collection."""
    monitors = _get_monitors(
        app, system_index, bus_platform_index, bus_type, physical_bus_access_index
    )
    try:
        count = int(monitors.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitors", method="Count") from exc

    for i in range(count):
        try:
            mon = monitors.Item(i)
            if str(mon.Name) == monitor_name:
                return mon
        except Exception:  # noqa: BLE001
            continue

    raise BridgePreconditionError(
        f"Monitor '{monitor_name}' not found on system {system_index}, bus type {bus_type}.",
        error_code="BRIDGE_MONITOR_NOT_FOUND",
        recovery_hint="Use bus_monitor_list to enumerate existing monitors.",
    )


# ── create_monitor ────────────────────────────────────────────────────────────


def create_monitor(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Create a new monitor on the specified physical bus access."""
    monitors = _get_monitors(
        app, system_index, bus_platform_index, bus_type, physical_bus_access_index
    )
    try:
        monitor = monitors.Add(monitor_name)
        return {
            "monitor_name": str(monitor.Name),
            "system_index": system_index,
            "bus_type": bus_type,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitors", method="Add") from exc


# ── configure_monitor ─────────────────────────────────────────────────────────


def configure_monitor(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    update_rate_ms: int = 100,
    buffer_size_frames: int = 10000,
    buffer_mode: str = "RingBuffer",
    enable_j1939_pgn_resolving: bool = False,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Configure monitor display and buffering settings."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    try:
        config = monitor.Configuration
        config.UpdateRate = update_rate_ms
        config.BufferSize = buffer_size_frames
        config.BufferMode = _BUFFER_MODE_TO_INT.get(buffer_mode, 1)
        config.J1939PGNResolving = enable_j1939_pgn_resolving
        return {
            "monitor_name": monitor_name,
            "update_rate_ms": update_rate_ms,
            "buffer_size_frames": buffer_size_frames,
            "buffer_mode": buffer_mode,
            "enable_j1939_pgn_resolving": enable_j1939_pgn_resolving,
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitor", method="Configuration") from exc


# ── start_monitor ─────────────────────────────────────────────────────────────


def start_monitor(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Start monitoring — begin capturing bus frames for real-time display."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    try:
        monitor.Start()
        return {"monitor_name": monitor_name, "state": "Running"}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitor", method="Start") from exc


# ── stop_monitor ──────────────────────────────────────────────────────────────


def stop_monitor(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Stop monitoring — halt frame capture."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    try:
        monitor.Stop()
        return {"monitor_name": monitor_name, "state": "Stopped"}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitor", method="Stop") from exc


# ── get_monitor_state ─────────────────────────────────────────────────────────


def get_monitor_state(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Return the current monitor state (Running or Stopped)."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    try:
        raw_state = monitor.State
        state = _INT_TO_RUN_STATE.get(int(raw_state), str(raw_state))
        return {
            "monitor_name": monitor_name,
            "state": state,
            "is_running": state == "Running",
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitor", method="State") from exc


# ── list_monitors ─────────────────────────────────────────────────────────────


def list_monitors(
    app: Any,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> list[dict[str, Any]]:
    """Enumerate all monitors on a physical bus access."""
    monitors = _get_monitors(
        app, system_index, bus_platform_index, bus_type, physical_bus_access_index
    )
    try:
        count = int(monitors.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitors", method="Count") from exc

    result: list[dict[str, Any]] = []
    for i in range(count):
        try:
            mon = monitors.Item(i)
            raw_state = mon.State
            state = _INT_TO_RUN_STATE.get(int(raw_state), str(raw_state))
            entry: dict[str, Any] = {
                "name": str(mon.Name),
                "state": state,
            }
            try:
                config = mon.Configuration
                entry["update_rate_ms"] = int(config.UpdateRate)
                entry["buffer_size_frames"] = int(config.BufferSize)
                raw_bm = int(config.BufferMode)
                entry["buffer_mode"] = _INT_TO_BUFFER_MODE.get(raw_bm, str(raw_bm))
            except Exception:  # noqa: BLE001
                pass
            result.append(entry)
        except Exception:  # noqa: BLE001
            continue

    return result


# ── remove_monitor ────────────────────────────────────────────────────────────


def remove_monitor(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Remove a specific monitor from the physical bus access."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    try:
        monitor.Remove()
        return {"monitor_name": monitor_name, "removed": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitor", method="Remove") from exc


# ── clear_all_monitors ────────────────────────────────────────────────────────


def clear_all_monitors(
    app: Any,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Remove all monitors from a physical bus access."""
    monitors = _get_monitors(
        app, system_index, bus_platform_index, bus_type, physical_bus_access_index
    )
    try:
        count = int(monitors.Count)
        monitors.Clear()
        return {"monitors_removed": count}
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitors", method="Clear") from exc


# ── save_data ─────────────────────────────────────────────────────────────────


def save_monitor_data(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    output_file_path: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Save the monitor buffer contents to a log file."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    ext = output_file_path.lower().rsplit(".", 1)
    ext = "." + ext[-1] if len(ext) > 1 else ""
    fmt = _LOG_FILE_FORMAT.get(ext, 2)  # default to ASC
    try:
        monitor.SaveDataWithOptions(output_file_path, fmt, 0, False)
        return {"monitor_name": monitor_name, "output_file_path": output_file_path}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitor", method="SaveData") from exc


# ── save_data_with_time_axis ─────────────────────────────────────────────────


def save_monitor_data_with_time_axis(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    output_file_path: str,
    time_axis: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Save the monitor buffer with time axis selection."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    ext = output_file_path.lower().rsplit(".", 1)
    ext = "." + ext[-1] if len(ext) > 1 else ""
    fmt = _LOG_FILE_FORMAT.get(ext, 2)  # default to ASC
    time_axis_int = _TIME_AXIS_TO_INT.get(time_axis)
    if time_axis_int is None:
        raise BridgePreconditionError(
            f"Invalid time_axis '{time_axis}'. Must be Absolute, Relative, or RecordingTime.",
            error_code="BRIDGE_INVALID_TIME_AXIS",
            recovery_hint="Use Absolute, Relative, or RecordingTime.",
        )
    try:
        monitor.SaveDataWithOptions(output_file_path, fmt, time_axis_int, False)
        return {
            "monitor_name": monitor_name,
            "output_file_path": output_file_path,
            "time_axis": time_axis,
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(
            exc, interface="IBnMonitor", method="SaveDataWithTimeAxisSelection"
        ) from exc


# ── load_monitor_data ─────────────────────────────────────────────────────────


def load_monitor_data(
    app: Any,
    monitor_name: str,
    system_index: int,
    bus_type: str,
    log_file_path: str,
    log_file_section: int = 0,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Load a previously saved log file into the monitor buffer for offline viewing."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    try:
        monitor.LoadData(log_file_path, log_file_section)
        return {
            "monitor_name": monitor_name,
            "log_file_path": log_file_path,
            "log_file_section": log_file_section,
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitor", method="LoadData") from exc


# ── rename_monitor ────────────────────────────────────────────────────────────


def rename_monitor(
    app: Any,
    monitor_name: str,
    new_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Rename an existing monitor."""
    monitor = _get_monitor_by_name(
        app, monitor_name, system_index, bus_type, bus_platform_index, physical_bus_access_index
    )
    try:
        monitor.Name = new_name
        return {"old_name": monitor_name, "new_name": new_name}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IBnMonitor", method="Name") from exc
