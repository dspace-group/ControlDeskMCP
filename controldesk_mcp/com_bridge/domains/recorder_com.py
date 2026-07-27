"""COM bridge for ControlDesk main recorder operations.

Provides low-level COM interface wrappers for:
- Main recorder configuration (filename, naming, integration settings)
- Signal management (add/remove/list signals in recorder)
- Recorder lifecycle (start/stop/get_state)

All functions run on the STA thread via com_bridge.dispatch().

Key considerations:
- _main_recorder is cached from recorder_main_configure through recorder_main_stop
- recorder_main_list_signals and recorder_main_get_state are transient: they
  re-obtain the recorder reference from app.MeasurementDataManagement.MainRecorder
  on every call rather than using the cache

RecordingState enum (dSPACE.ToolAutomation.ControlDeskNG.RecordingState):
  Idling = 0          -- recorder not started / stopped
  WaitingForTrigger = 1  -- started with trigger, waiting for start condition
  Running = 2         -- recording is active
Note: Pause/Resume do NOT exist on IXaMainRecorder (confirmed from IXaMainRecorder.g.cs).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from controldesk_mcp.com_bridge.errors import BridgeOperationError
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)

# ── RecordingState enum mapping ───────────────────────────────────────────────

_RECORDING_STATE: dict[int, str] = {
    0: "Idling",
    1: "WaitingForTrigger",
    2: "Running",
}


def _parse_recording_state(raw: Any) -> str:
    """Map a COM RecordingState integer (or string) to its canonical name."""
    try:
        return _RECORDING_STATE.get(int(raw), str(raw))
    except (ValueError, TypeError):
        raw_str = str(raw)
        if raw_str in _RECORDING_STATE.values():
            return raw_str
        return raw_str


# ── Persistent COM reference ──────────────────────────────────────────────────

_main_recorder: Any = None


def _timestamp_utc() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _get_recorder(app: Any) -> Any:
    """Return cached recorder, falling back to live app reference."""
    global _main_recorder
    if _main_recorder is None:
        _main_recorder = app.MeasurementDataManagement.MainRecorder
    return _main_recorder


def _parse_connection_path(connection_path: str) -> dict[str, str]:
    """Extract platform_name, raster_name, variable_name from connection path."""
    match = re.match(r"^([^(]+)\(([^)]*)\)://(.+)$", connection_path)
    if match:
        return {
            "platform_name": match.group(1),
            "raster_name": match.group(2),
            "variable_name": match.group(3),
        }
    return {
        "platform_name": "",
        "raster_name": "",
        "variable_name": connection_path,
    }


# ── Tool 1: configure_main_recorder ──────────────────────────────────────────


def configure_main_recorder(
    app: Any,
    base_filename: str,
    automatic_naming_enabled: bool,
    automatic_naming_start_index: int,
    automatic_naming_minimum_digits: int,
    add_to_experiment_enabled: bool,
    open_in_data_pool_enabled: bool,
    write_to_file_enabled: bool,
    automatic_signal_configuration_enabled: bool,
    description: str,
) -> dict[str, Any]:
    """Configure the main recorder and cache the COM reference.

    Returns: dict with configured=True and applied settings
    Raises: BridgeOperationError on COM error
    """
    global _main_recorder
    try:
        recorder = app.MeasurementDataManagement.MainRecorder
        _main_recorder = recorder

        recorder.BaseFileName = base_filename
        recorder.AutomaticNamingEnabled = automatic_naming_enabled
        recorder.AutomaticNamingStartIndex = automatic_naming_start_index
        recorder.AutomaticNamingMinimumDigits = automatic_naming_minimum_digits
        recorder.AddToExperimentEnabled = add_to_experiment_enabled
        recorder.OpenInMeasurementDataPoolEnabled = open_in_data_pool_enabled
        recorder.WriteToFileEnabled = write_to_file_enabled
        recorder.AutomaticSignalConfigurationEnabled = automatic_signal_configuration_enabled
        recorder.Description = description

        return {
            "configured": True,
            "base_filename": base_filename,
            "automatic_naming_enabled": automatic_naming_enabled,
            "add_to_experiment_enabled": add_to_experiment_enabled,
            "open_in_data_pool_enabled": open_in_data_pool_enabled,
            "write_to_file_enabled": write_to_file_enabled,
            "automatic_signal_configuration_enabled": automatic_signal_configuration_enabled,
            "description": description,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception as exc:
        raise BridgeOperationError(f"Failed to configure main recorder: {exc}") from exc


# ── Tool 2: add_signal ────────────────────────────────────────────────────────


def add_signal(app: Any, connection_path: str) -> dict[str, Any]:
    """Add a signal to the main recorder's signal list.

    Looks up the IXaMeasurementSignal by connection_path from
    MeasurementConfiguration.Signals and inserts it into the recorder.

    Returns: dict with added=True and connection_path
    Raises: BridgeOperationError on COM error
    """
    try:
        recorder = _get_recorder(app)
        meas_signals = app.MeasurementDataManagement.MeasurementConfiguration.Signals
        if not meas_signals.Contains(connection_path):
            raise BridgeOperationError(f"Signal '{connection_path}' not found in measurement configuration")
        sig = meas_signals.Item(connection_path)
        recorder.Signals.Insert(sig)
        return {
            "added": True,
            "connection_path": connection_path,
            "timestamp_utc": _timestamp_utc(),
        }
    except BridgeOperationError:
        raise
    except Exception as exc:
        raise BridgeOperationError(f"Failed to add signal '{connection_path}' to main recorder: {exc}") from exc


# ── Tool 3: remove_signal ─────────────────────────────────────────────────────


def remove_signal(app: Any, connection_path: str) -> dict[str, Any]:
    """Remove a signal from the main recorder's signal list.

    Returns: dict with removed=True and connection_path
    Raises: BridgeOperationError on COM error
    """
    try:
        recorder = _get_recorder(app)
        recorder.Signals.Remove(connection_path)
        return {
            "removed": True,
            "connection_path": connection_path,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception as exc:
        raise BridgeOperationError(f"Failed to remove signal '{connection_path}' from main recorder: {exc}") from exc


# ── Tool 4: list_signals (transient) ─────────────────────────────────────────


def list_signals(app: Any) -> dict[str, Any]:
    """List all signals in the main recorder's signal list.

    Transient: always re-obtains the recorder reference from the app.
    Returns: dict with total_count and signals list
    Raises: BridgeOperationError on COM error
    """
    try:
        recorder = app.MeasurementDataManagement.MainRecorder
        signals_col = recorder.Signals
        signals = []
        count = signals_col.Count
        for i in range(count):
            sig = signals_col.Item(i)
            try:
                platform_name = str(sig.PlatformName) if hasattr(sig, "PlatformName") else ""
                raster_name = str(sig.RasterName) if hasattr(sig, "RasterName") else ""
                variable_name = str(sig.VariableName) if hasattr(sig, "VariableName") else ""
            except Exception:
                platform_name = raster_name = variable_name = ""
            if platform_name and raster_name and variable_name:
                cp = f"{platform_name}({raster_name})://{variable_name}"
            elif variable_name:
                cp = variable_name
            else:
                cp = str(sig)
            signals.append(
                {
                    "connection_path": cp,
                    "variable_name": variable_name,
                    "platform_name": platform_name,
                    "raster_name": raster_name,
                    "active": bool(getattr(sig, "Active", True)),
                    "recording_enabled": bool(getattr(sig, "RecordingEnabled", True)),
                }
            )
        return {"total_count": count, "signals": signals}
    except Exception as exc:
        raise BridgeOperationError(f"Failed to list recorder signals: {exc}") from exc


# ── Tool 5: start_recorder ────────────────────────────────────────────────────


def start_recorder(
    app: Any,
    with_trigger: bool,
    overwrite_existing: bool,
) -> dict[str, Any]:
    """Start the main recorder.

    Returns: dict with started=True, base_filename, state
    Raises: BridgeOperationError on COM error
    """
    try:
        recorder = _get_recorder(app)
        recorder.Start(with_trigger, overwrite_existing)
        base_filename = ""
        try:
            base_filename = str(recorder.BaseFileName)
        except Exception:
            pass
        return {
            "started": True,
            "base_filename": base_filename,
            "with_trigger": with_trigger,
            "state": "Running",
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception as exc:
        raise BridgeOperationError(f"Failed to start main recorder: {exc}") from exc


# ── Tool 6: stop_recorder ─────────────────────────────────────────────────────


def stop_recorder(app: Any) -> dict[str, Any]:
    """Stop the main recorder and finalize the output file.

    Returns: dict with stopped=True and output_files list
    Raises: BridgeOperationError on COM error
    """
    global _main_recorder
    try:
        recorder = _get_recorder(app)
        output_files: list[str] = []
        try:
            base_filename = str(recorder.BaseFileName)
            if base_filename:
                output_files = [base_filename]
        except Exception:
            pass
        recorder.Stop()
        _main_recorder = None
        return {
            "stopped": True,
            "output_files": output_files,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception as exc:
        raise BridgeOperationError(f"Failed to stop main recorder: {exc}") from exc


# ── Tool 7: get_state (transient) ─────────────────────────────────────────────


def get_state(app: Any) -> dict[str, Any]:
    """Return current state of the main recorder.

    Transient: always re-obtains the recorder reference from the app.
    Returns: dict with state (Idling/WaitingForTrigger/Running) and is_running
    Raises: BridgeOperationError on COM error
    """
    try:
        recorder = app.MeasurementDataManagement.MainRecorder
        raw_state = recorder.State
        state_str = _parse_recording_state(raw_state)
        is_running = state_str == "Running"
        last_files: list[str] = []
        try:
            base_filename = str(recorder.BaseFileName)
            if base_filename:
                last_files = [base_filename]
        except Exception:
            pass
        return {
            "state": state_str,
            "is_running": is_running,
            "last_recorded_files": last_files,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception as exc:
        raise BridgeOperationError(f"Failed to get recorder state: {exc}") from exc


# ── Cache management ──────────────────────────────────────────────────────────


def clear_cache() -> None:
    """Reset all cached COM references (for testing and cleanup)."""
    global _main_recorder
    _main_recorder = None


# ── Tool 8: invoke_trigger ────────────────────────────────────────────────────


def invoke_trigger(app: Any) -> dict[str, Any]:
    """Bypass the start trigger and begin recording immediately.

    Only valid when state is WaitingForTrigger. Calls IXaMainRecorder.InvokeTrigger().
    Returns: dict with triggered=True and new state
    Raises: BridgeOperationError on COM error
    """
    try:
        recorder = _get_recorder(app)
        recorder.InvokeTrigger()
        raw_state = recorder.State
        state_str = _parse_recording_state(raw_state)
        return {
            "triggered": True,
            "state": state_str,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception as exc:
        raise BridgeOperationError(f"Failed to invoke trigger: {exc}") from exc


# ── Tool 9: export_recorder ───────────────────────────────────────────────────


def export_recorder(app: Any, full_path: str, overwrite_existing: bool) -> dict[str, Any]:
    """Export the recorder configuration to a file.

    Calls IXaMainRecorder.Export(FullPath, OverwriteExisting).
    Returns: dict with exported=True and full_path
    Raises: BridgeOperationError on COM error
    """
    try:
        recorder = _get_recorder(app)
        recorder.Export(full_path, overwrite_existing)
        return {
            "exported": True,
            "full_path": full_path,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception as exc:
        raise BridgeOperationError(f"Failed to export recorder to '{full_path}': {exc}") from exc


# ── Tool 10: import_signals ───────────────────────────────────────────────────


def import_signals(app: Any, full_path: str) -> dict[str, Any]:
    """Import signals from a previously exported recorder file.

    Calls IXaMainRecorder.ImportSignals(FullPath).
    Returns: dict with imported=True and full_path
    Raises: BridgeOperationError on COM error
    """
    try:
        recorder = _get_recorder(app)
        recorder.ImportSignals(full_path)
        return {
            "imported": True,
            "full_path": full_path,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception as exc:
        raise BridgeOperationError(f"Failed to import signals from '{full_path}': {exc}") from exc
