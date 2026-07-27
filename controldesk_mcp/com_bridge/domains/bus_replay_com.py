"""COM bridge for ControlDesk bus replay operations.

Provides low-level COM interface wrappers for replay lifecycle management.
All functions run on the STA thread via com_bridge.dispatch().

Key considerations:
- Persistent refs (cached): IBnReplay objects held across multiple tool calls
- Transient refs (one-call): IBnReplays enumeration for read-only discovery
- Error handling: Raise exceptions for all error conditions; dispatch handles wrapping
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgeOperationError, BridgePreconditionError
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)

# ── Cached replay references (persistent across calls) ────────────────────────────
# Replays are held in a dict keyed by (system_index, bus_type, replay_name)
# to maintain consistent COM references for Activated flag management

_replay_cache: dict[tuple[int, str, str], Any] = {}

# Replay mode string → COM integer mapping
_REPLAY_MODE_TO_INT: dict[str, int] = {
    "Infinite": 0,
    "NumberOfPasses": 1,
    "Duration": 2,
}
_INT_TO_REPLAY_MODE: dict[int, str] = {v: k for k, v in _REPLAY_MODE_TO_INT.items()}

# Run state COM integer → string mapping
_INT_TO_RUN_STATE: dict[int, str] = {
    0: "Stopped",
    1: "Running",
}


def _cache_key(system_index: int, bus_type: str, replay_name: str) -> tuple[int, str, str]:
    """Generate cache key for a replay."""
    return (system_index, bus_type, replay_name)


def _get_physical_bus_access(
    app: Any,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> Any:
    """Navigate BusNavigator hierarchy to PhysicalBusAccess.

    Path: app.BusNavigator.Systems[system_idx].BusPlatforms[bus_platform_idx]
          .<BusType>BusSystem.PhysicalBusAccesses[physical_bus_access_idx]
    """
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

    try:
        bus_platform = system.BusPlatforms.Item(bus_platform_index)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Bus platform index {bus_platform_index} not found on system {system_index}.",
            error_code="BRIDGE_BAD_INPUT",
            recovery_hint="Check bus_platform_index.",
        ) from exc

    # Get the appropriate bus system (CANBusSystem, LINBusSystem, etc.)
    try:
        bus_system_attr = f"{bus_type}BusSystem"
        bus_system = getattr(bus_platform, bus_system_attr)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Bus type '{bus_type}' not available on bus platform {bus_platform_index}.",
            error_code="BRIDGE_BAD_INPUT",
            recovery_hint="Check bus_type (CAN, LIN, FlexRay, Ethernet).",
        ) from exc

    try:
        physical_bus_access = bus_system.PhysicalBusAccesses.Item(physical_bus_access_index)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Physical bus access index {physical_bus_access_index} not found.",
            error_code="BRIDGE_BAD_INPUT",
            recovery_hint="Check physical_bus_access_index.",
        ) from exc

    return physical_bus_access


def _timestamp_utc() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ── Tool 1: create_replay ───────────────────────────────────────────────────────


def create_replay(
    app: Any,
    replay_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Create a new replay on a physical bus access.

    Returns: dict with created=True, replay_name, system_index, bus_type, state,
             activated
    Raises: BridgeOperationError on COM error
    """
    try:
        pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
        replays = pba.Replays

        # Create replay via Replays.Add(name)
        replay = replays.Add(replay_name)

        # Cache the replay reference for later operations
        cache_key = _cache_key(system_index, bus_type, replay_name)
        _replay_cache[cache_key] = replay

        return {
            "created": True,
            "replay_name": replay_name,
            "system_index": system_index,
            "bus_type": bus_type,
            "state": "Stopped",
            "activated": False,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to create replay '{replay_name}' on system {system_index}, "
            f"bus type {bus_type}. "
            f"Replay name may already exist or system/bus configuration may be invalid.",
            exc,
        )


# ── Tool 2: configure_replay ───────────────────────────────────────────────────


def configure_replay(
    app: Any,
    replay_name: str,
    system_index: int,
    bus_type: str,
    log_file_full_path: str,
    log_file_section: int = 0,
    replay_mode: str = "Infinite",
    number_of_passes: int = 1,
    duration_seconds: float = 0.0,
    start_monitor_on_replay: bool = False,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Configure replay playback settings.

    Sets source file, replay mode (Infinite/NumberOfPasses/Duration), and options.
    Must be called BEFORE start_replay.

    Returns: dict with configured=True, replay_name, log_file_full_path, etc.
    Raises: BridgeOperationError on COM error
    """
    try:
        # Retrieve cached replay or fetch from hierarchy
        cache_key = _cache_key(system_index, bus_type, replay_name)
        replay = _replay_cache.get(cache_key)

        if replay is None:
            # Fetch replay by name from PhysicalBusAccess
            pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
            replays = pba.Replays
            replay = replays.Item(replay_name)
            _replay_cache[cache_key] = replay

        # Access Configuration property
        config = replay.Configuration

        # Set source file and section
        config.LogFileFullPath = log_file_full_path
        config.LogFileSection = log_file_section

        # Set replay mode and mode-specific parameters
        config.Mode = _REPLAY_MODE_TO_INT.get(replay_mode, 0)

        if replay_mode == "NumberOfPasses":
            config.NumberOfPasses = number_of_passes
        elif replay_mode == "Duration":
            config.Duration = duration_seconds

        # Monitor integration option
        config.StartMonitorOnReplay = start_monitor_on_replay

        return {
            "configured": True,
            "replay_name": replay_name,
            "log_file_full_path": log_file_full_path,
            "replay_mode": replay_mode,
            "number_of_passes": number_of_passes,
            "duration_seconds": duration_seconds if replay_mode == "Duration" else 0.0,
            "start_monitor_on_replay": start_monitor_on_replay,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to configure replay '{replay_name}'. Source log file may not exist or replay may be running.",
            exc,
        )


# ── Tool 3: start_replay ────────────────────────────────────────────────────────


def start_replay(
    app: Any,
    replay_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Activate and start replay transmission.

    Sets Activated=True and calls Start().

    Returns: dict with started=True, replay_name, state, activated, etc.
    Raises: BridgeOperationError on COM error
    """
    try:
        # Retrieve cached replay
        cache_key = _cache_key(system_index, bus_type, replay_name)
        replay = _replay_cache.get(cache_key)

        if replay is None:
            pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
            replays = pba.Replays
            replay = replays.Item(replay_name)
            _replay_cache[cache_key] = replay

        # Set Activated flag (safety gate before Start)
        replay.Activated = True

        # Call Start() to begin transmission
        replay.Start()

        # Fetch current state
        state_raw = replay.State
        state = _INT_TO_RUN_STATE.get(int(state_raw), str(state_raw))

        return {
            "started": True,
            "replay_name": replay_name,
            "state": state,
            "activated": True,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to start replay '{replay_name}'. Ensure the replay is configured and source log file is readable.",
            exc,
        )


# ── Tool 4: stop_replay ─────────────────────────────────────────────────────────


def stop_replay(
    app: Any,
    replay_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Stop replay and deactivate.

    Calls Stop() and sets Activated=False.

    Returns: dict with stopped=True, replay_name, state, activated
    Raises: BridgeOperationError on COM error
    """
    try:
        # Retrieve cached replay
        cache_key = _cache_key(system_index, bus_type, replay_name)
        replay = _replay_cache.get(cache_key)

        if replay is None:
            pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
            replays = pba.Replays
            replay = replays.Item(replay_name)
            _replay_cache[cache_key] = replay

        # Call Stop()
        replay.Stop()

        # Set Activated=False
        replay.Activated = False

        # Fetch current state
        state_raw = replay.State
        state = _INT_TO_RUN_STATE.get(int(state_raw), str(state_raw))

        return {
            "stopped": True,
            "replay_name": replay_name,
            "state": state,
            "activated": False,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to stop replay '{replay_name}'. Ensure replay is currently running.",
            exc,
        )


# ── Tool 5: get_replay_state ────────────────────────────────────────────────────


def get_replay_state(
    app: Any,
    replay_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Query current replay state (transient lookup).

    Fetches replay by name and returns state, activated status, config.

    Returns: dict with replay_name, state, is_running, activated, etc.
    Raises: BridgeOperationError on COM error
    """
    try:
        pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
        replays = pba.Replays

        replay = replays.Item(replay_name)

        state_raw = replay.State
        state = _INT_TO_RUN_STATE.get(int(state_raw), str(state_raw))
        is_running = state == "Running"
        activated = bool(replay.Activated)

        config = replay.Configuration
        log_file_path = config.LogFileFullPath if config else ""
        replay_mode_raw = int(config.Mode) if config else 0
        replay_mode = _INT_TO_REPLAY_MODE.get(replay_mode_raw, str(replay_mode_raw))

        return {
            "replay_name": replay_name,
            "state": state,
            "is_running": is_running,
            "activated": activated,
            "log_file_path": log_file_path,
            "replay_mode": replay_mode,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to get replay state. Replay '{replay_name}' may not exist.",
            exc,
        )


# ── Tool 6: list_replays ────────────────────────────────────────────────────────


def list_replays(
    app: Any,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Enumerate all replays on a physical bus access (transient lookup).

    Returns: dict with system_index, bus_type, total_count, replays array
    Raises: BridgeOperationError on COM error
    """
    try:
        pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
        replays_collection = pba.Replays

        replays_list = []
        for i in range(replays_collection.Count):
            replay = replays_collection.Item(i)
            if replay:
                state_raw = replay.State
                state = _INT_TO_RUN_STATE.get(int(state_raw), str(state_raw))
                activated = bool(replay.Activated)
                config = replay.Configuration
                log_file_path = config.LogFileFullPath if config else ""
                replay_mode_raw = int(config.Mode) if config else 0
                replay_mode = _INT_TO_REPLAY_MODE.get(replay_mode_raw, str(replay_mode_raw))

                replays_list.append(
                    {
                        "name": replay.Name,
                        "state": state,
                        "activated": activated,
                        "log_file_path": log_file_path,
                        "replay_mode": replay_mode,
                    }
                )

        return {
            "system_index": system_index,
            "bus_type": bus_type,
            "total_count": len(replays_list),
            "replays": replays_list,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to list replays on system {system_index}, bus type {bus_type}. "
            f"System or bus configuration may be invalid.",
            exc,
        )


# ── Tool 7: remove_replay ───────────────────────────────────────────────────────


def remove_replay(
    app: Any,
    replay_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Remove a specific replay (transient operation).

    Returns: dict with removed=True, replay_name
    Raises: BridgeOperationError on COM error
    """
    try:
        pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
        replays = pba.Replays

        replay = replays.Item(replay_name)

        replay.Remove()

        # Remove from cache
        cache_key = _cache_key(system_index, bus_type, replay_name)
        _replay_cache.pop(cache_key, None)

        return {
            "removed": True,
            "replay_name": replay_name,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to remove replay '{replay_name}'. Ensure replay is stopped before removing.",
            exc,
        )


# ── Tool 8: clear_all_replays ───────────────────────────────────────────────────


def clear_all_replays(
    app: Any,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Remove all replays from a physical bus access (transient operation).

    Returns: dict with cleared=True, replays_removed count
    Raises: BridgeOperationError on COM error
    """
    try:
        pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
        replays = pba.Replays

        count = replays.Count
        replays.Clear()

        # Clear cache entries for this bus access
        cache_key_prefix = (system_index, bus_type)
        keys_to_remove = [k for k in _replay_cache.keys() if k[:2] == cache_key_prefix]
        for k in keys_to_remove:
            _replay_cache.pop(k, None)

        return {
            "cleared": True,
            "replays_removed": count,
            "system_index": system_index,
            "bus_type": bus_type,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to clear replays on system {system_index}, bus type {bus_type}. Ensure all replays are stopped.",
            exc,
        )


# ── Tool 9: set_replay_activated ────────────────────────────────────────────────


def set_replay_activated(
    app: Any,
    replay_name: str,
    system_index: int,
    bus_type: str,
    activated: bool,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Set or clear the Activated flag on a replay.

    Returns: dict with activated flag, replay_name, state, previous_activated
    Raises: BridgeOperationError on COM error
    """
    try:
        # Retrieve cached replay
        cache_key = _cache_key(system_index, bus_type, replay_name)
        replay = _replay_cache.get(cache_key)

        if replay is None:
            pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
            replays = pba.Replays
            replay = replays.Item(replay_name)
            _replay_cache[cache_key] = replay

        previous_activated = bool(replay.Activated)

        # Set activation flag
        replay.Activated = activated

        state_raw = replay.State
        state_after = _INT_TO_RUN_STATE.get(int(state_raw), str(state_raw))

        return {
            "activated": activated,
            "replay_name": replay_name,
            "state": state_after,
            "previous_activated": previous_activated,
            "timestamp_utc": _timestamp_utc(),
        }

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to set activation state on replay '{replay_name}'. "
            f"Replay may not exist or may be running. "
            f"Ensure replay is stopped before deactivating.",
            exc,
        )


# ── Cache management ────────────────────────────────────────────────────────────


def clear_cache() -> None:
    """Clear all cached replay references. Called on shutdown."""
    global _replay_cache
    _replay_cache.clear()


# ── rename_replay ─────────────────────────────────────────────────────────────


def rename_replay(
    app: Any,
    replay_name: str,
    new_name: str,
    system_index: int,
    bus_type: str,
    bus_platform_index: int = 0,
    physical_bus_access_index: int = 0,
) -> dict[str, Any]:
    """Rename an existing replay."""
    try:
        cache_key = _cache_key(system_index, bus_type, replay_name)
        replay = _replay_cache.get(cache_key)

        if replay is None:
            pba = _get_physical_bus_access(app, system_index, bus_type, bus_platform_index, physical_bus_access_index)
            replays = pba.Replays
            replay = replays.Item(replay_name)

        replay.Name = new_name

        # Evict stale cache entry and cache under new name
        _replay_cache.pop(cache_key, None)
        new_key = _cache_key(system_index, bus_type, new_name)
        _replay_cache[new_key] = replay

        return {"old_name": replay_name, "new_name": new_name}

    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to rename replay '{replay_name}' to '{new_name}'.",
            exc,
        )
