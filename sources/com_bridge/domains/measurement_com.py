"""COM bridge for ControlDesk measurement operations.

Provides low-level COM interface wrappers for:
- Signal management (add/remove/list)
- Buffer configuration
- Measurement lifecycle (start/stop/state)
- Trigger rules (create/remove/configure conditions)
- Recordings (list/export/import)
- Bookmarks (add/list/remove)
- Data loggers (create/configure/start/stop/list/remove)
- Rasters (add/list/remove)
- Global settings

All functions run on the STA thread via com_bridge.dispatch().

Key considerations:
- _measurement_data_mgmt is cached from measurement_start to measurement_stop
- _trigger_rules_cache keyed by rule_name (persistent until removed)
- _data_loggers_cache keyed by logger_name (persistent until removed)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sources.com_bridge.errors import BridgeOperationError
from sources.utils.logger import get_logger

_log = get_logger(__name__)

# ── Persistent COM references ─────────────────────────────────────────────────

_measurement_data_mgmt: Any = None
_trigger_rules_cache: dict[str, Any] = {}
_data_loggers_cache: dict[str, Any] = {}


def _timestamp_utc() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _get_mdm(app: Any) -> Any:
    """Get MeasurementDataManagement from cache or from app."""
    global _measurement_data_mgmt
    if _measurement_data_mgmt is None:
        _measurement_data_mgmt = app.MeasurementDataManagement
    return _measurement_data_mgmt


# ── Tool 1: signal_add ────────────────────────────────────────────────────────


def signal_add(app: Any, connection_path: str) -> dict[str, Any]:
    """Add a signal to the measurement configuration.

    Returns: dict with added=True and signal metadata
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration
        signals = config.Signals
        signal = signals.Add(connection_path)

        return {
            "added": True,
            "connection_path": connection_path,
            "variable_name": str(signal.Name),
            "platform_name": str(signal.PlatformName),
            "raster_name": str(signal.RasterName),
            "is_connected": bool(signal.IsConnected),
            "active": bool(signal.Active),
            "recording_enabled": bool(signal.RecordingEnabled),
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to add signal '{connection_path}'. "
            f"Variable may not exist or platform may not be connected."
        )


# ── Tool 2: signal_remove ─────────────────────────────────────────────────────


def signal_remove(app: Any, connection_path: str) -> dict[str, Any]:
    """Remove a signal from the measurement configuration.

    Returns: dict with removed=True and connection_path
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration
        signals = config.Signals
        signal = signals.Item(connection_path)
        signals.Remove(signal)

        return {
            "removed": True,
            "connection_path": connection_path,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to remove signal '{connection_path}'. "
            f"Ensure measurement is stopped and the signal exists."
        )


# ── Tool 3: list_signals ──────────────────────────────────────────────────────


def list_signals(app: Any) -> dict[str, Any]:
    """List all configured signals in the measurement configuration.

    Returns: dict with total_count and signals array
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration
        signals = config.Signals

        signals_list = []
        for i in range(signals.Count):
            sig = signals.Item(i)
            if sig:
                signals_list.append(
                    {
                        "connection_path": str(sig.ConnectionPath),
                        "variable_name": str(sig.Name),
                        "platform_name": str(sig.PlatformName),
                        "raster_name": str(sig.RasterName),
                        "is_connected": bool(sig.IsConnected),
                        "active": bool(sig.Active),
                        "recording_enabled": bool(sig.RecordingEnabled),
                    }
                )

        return {
            "total_count": len(signals_list),
            "signals": signals_list,
        }
    except Exception:
        raise BridgeOperationError(
            "Failed to enumerate measurement signals. Ensure online calibration is running."
        )


# ── Tool 4: configure_buffer ──────────────────────────────────────────────────


def configure_buffer(
    app: Any,
    buffer_size_seconds: float,
    warning_enabled: bool = False,
    warning_time_seconds: float = 3.0,
) -> dict[str, Any]:
    """Configure the measurement ring buffer.

    Returns: dict with configured=True and buffer settings
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration
        buffer = config.Buffer
        buffer.Size = buffer_size_seconds
        buffer.WarningEnabled = warning_enabled
        if warning_enabled:
            buffer.WarningTime = warning_time_seconds

        return {
            "configured": True,
            "buffer_size_seconds": buffer_size_seconds,
            "warning_enabled": warning_enabled,
            "warning_time_seconds": warning_time_seconds,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            "Failed to configure measurement buffer. Ensure measurement is stopped."
        )


# ── Tool 5: get_configuration ─────────────────────────────────────────────────


def get_configuration(app: Any) -> dict[str, Any]:
    """Get current measurement configuration state.

    Returns: dict with buffer, signal_count, signals, platforms_connected
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration
        buffer = config.Buffer
        signals = config.Signals

        signals_summary = []
        for i in range(signals.Count):
            sig = signals.Item(i)
            if sig:
                signals_summary.append(
                    {
                        "connection_path": str(sig.ConnectionPath),
                        "platform_name": str(sig.PlatformName),
                        "raster_name": str(sig.RasterName),
                    }
                )

        platforms = []
        try:
            for i in range(config.Platforms.Count):
                p = config.Platforms.Item(i)
                if p:
                    platforms.append(str(p.Name))
        except Exception:
            pass

        return {
            "buffer": {
                "size_seconds": float(buffer.Size),
                "warning_enabled": bool(buffer.WarningEnabled),
                "warning_time_seconds": float(buffer.WarningTime),
            },
            "signal_count": len(signals_summary),
            "signals": signals_summary,
            "platforms_connected": platforms,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            "Failed to get measurement configuration. Ensure online calibration is running."
        )


# ── Tool 6: start_measurement ─────────────────────────────────────────────────


def start_measurement(app: Any) -> dict[str, Any]:
    """Start measurement on all connected platforms.

    Caches the MeasurementDataManagement reference for the session.

    Returns: dict with started=True and timestamp
    Raises: BridgeOperationError on COM error
    """
    global _measurement_data_mgmt
    try:
        mdm = app.MeasurementDataManagement
        _measurement_data_mgmt = mdm
        mdm.Start()

        platforms = []
        try:
            for i in range(app.ActiveExperiment.Platforms.Count):
                p = app.ActiveExperiment.Platforms.Item(i)
                if p:
                    platforms.append(str(p.Name))
        except Exception:
            pass

        return {
            "started": True,
            "platforms_measuring": platforms,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            "Failed to start measurement. Ensure online calibration is running "
            "and at least one platform is connected."
        )


# ── Tool 7: stop_measurement ──────────────────────────────────────────────────


def stop_measurement(app: Any) -> dict[str, Any]:  # noqa: ARG001
    """Stop measurement on all platforms.

    Releases the cached MeasurementDataManagement reference.

    Returns: dict with stopped=True and timestamp
    Raises: BridgeOperationError on COM error
    """
    global _measurement_data_mgmt
    try:
        mdm = _measurement_data_mgmt
        if mdm is None:
            mdm = app.MeasurementDataManagement
        mdm.Stop()
        return {
            "stopped": True,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            "Failed to stop measurement. Ensure measurement is currently running."
        )
    finally:
        _measurement_data_mgmt = None


# ── Tool 8: get_measurement_state ─────────────────────────────────────────────


def get_measurement_state(app: Any) -> dict[str, Any]:
    """Query current measurement state (transient lookup).

    Returns: dict with state, is_measuring, timestamp_utc
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        state_val = str(mdm.State)
        is_measuring = "measuring" in state_val.lower() and "not" not in state_val.lower()

        return {
            "state": "Measuring" if is_measuring else "NotMeasuring",
            "is_measuring": is_measuring,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError("Failed to get measurement state.")


# ── Tool 9: create_trigger_rule ───────────────────────────────────────────────


def create_trigger_rule(
    app: Any,
    rule_name: str,
    expression: str,
    signal_mappings: dict[str, str],
) -> dict[str, Any]:
    """Create a trigger rule and cache it for later condition assignment.

    Returns: dict with created=True, rule_name, expression, mappings, enabled
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        trigger_rules = mdm.TriggerRules
        rule = trigger_rules.Add(rule_name)

        # Configure expression
        rule.Expression = expression

        # Add signal mappings
        for alias, path in signal_mappings.items():
            rule.SignalMappings.Add(alias, path)

        # Cache the rule for later assignment
        _trigger_rules_cache[rule_name] = rule

        return {
            "created": True,
            "rule_name": rule_name,
            "expression": expression,
            "mappings": signal_mappings,
            "enabled": True,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to create trigger rule '{rule_name}'. "
            f"Ensure all signals in mappings exist in measurement configuration "
            f"and expression is valid."
        )


# ── Tool 10: remove_trigger_rule ──────────────────────────────────────────────


def remove_trigger_rule(app: Any, rule_name: str) -> dict[str, Any]:
    """Remove a trigger rule.

    Returns: dict with removed=True, rule_name
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        trigger_rules = mdm.TriggerRules
        rule = trigger_rules.Item(rule_name)
        trigger_rules.Remove(rule)

        _trigger_rules_cache.pop(rule_name, None)

        return {
            "removed": True,
            "rule_name": rule_name,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to remove trigger rule '{rule_name}'. "
            f"Rule may not exist or may still be attached to a recorder condition."
        )


# ── Tool 11: configure_time_limit_condition ───────────────────────────────────


def configure_time_limit_condition(
    app: Any,
    enabled: bool,
    time_limit_seconds: float,
) -> dict[str, Any]:
    """Configure time-limit stop condition on the main recorder.

    Returns: dict with configured=True and condition settings
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        recorder = mdm.MainRecorder
        stop_condition = recorder.StopCondition
        stop_condition.Enabled = enabled
        if enabled:
            stop_condition.Type = "TimeLimit"
            stop_condition.TimeLimit = time_limit_seconds

        return {
            "configured": True,
            "condition_type": "TimeLimit",
            "enabled": enabled,
            "time_limit_seconds": time_limit_seconds,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            "Failed to configure time-limit stop condition. Ensure recording is stopped."
        )


# ── Tool 12: configure_trigger_based_condition ────────────────────────────────


def configure_trigger_based_condition(
    app: Any,
    condition_type: str,
    rule_name: str,
    enabled: bool = True,
    trigger_delay_seconds: float = 0.0,
    recording_cycles: int = 1,
) -> dict[str, Any]:
    """Attach a trigger rule to recorder start/stop condition.

    Returns: dict with configured=True and condition details
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        recorder = mdm.MainRecorder

        # Resolve the cached trigger rule
        rule = _trigger_rules_cache.get(rule_name)
        if rule is None:
            rule = mdm.TriggerRules.Item(rule_name)

        if condition_type == "start":
            condition = recorder.StartCondition
            condition.Enabled = enabled
            condition.Trigger = rule
            condition.TriggerDelay = trigger_delay_seconds
            condition.RecordingCycles = recording_cycles
        else:
            condition = recorder.StopCondition
            condition.Enabled = enabled
            condition.Type = "Trigger"
            condition.Trigger = rule

        return {
            "configured": True,
            "condition_type": condition_type,
            "rule_name": rule_name,
            "enabled": enabled,
            "trigger_delay_seconds": trigger_delay_seconds,
            "recording_cycles": recording_cycles,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to configure trigger-based condition. "
            f"Ensure recording is stopped and the trigger rule '{rule_name}' exists."
        )


# ── Tool 13: list_recordings ──────────────────────────────────────────────────


def list_recordings(app: Any) -> dict[str, Any]:
    """List all recordings in the measurement data pool.

    Returns: dict with total_count and recordings array
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        measurements = mdm.Measurements

        recordings_list = []
        for i in range(measurements.Count):
            m = measurements.Item(i)
            if m:
                sig_paths = []
                try:
                    for j in range(m.Signals.Count):
                        s = m.Signals.Item(j)
                        if s:
                            sig_paths.append(str(s.ConnectionPath))
                except Exception:
                    pass

                recordings_list.append(
                    {
                        "index": i,
                        "filename": str(m.FileName),
                        "recording_date_time": str(m.RecordingDateTime),
                        "length_seconds": float(m.Length),
                        "signal_count": len(sig_paths),
                        "signals": sig_paths,
                    }
                )

        return {
            "total_count": len(recordings_list),
            "recordings": recordings_list,
        }
    except Exception:
        raise BridgeOperationError("Failed to list recordings.")


# ── Tool 14: export_recording ─────────────────────────────────────────────────


def export_recording(
    app: Any,
    recording_index: int,
    export_path: str,
    overwrite_existing: bool = True,
) -> dict[str, Any]:
    """Export a recording from the data pool to an external MF4 file.

    Returns: dict with exported=True, export_path
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        measurements = mdm.Measurements
        recording = measurements.Item(recording_index)
        recording.Export(export_path, overwrite_existing)

        import os

        file_size = 0
        try:
            file_size = os.path.getsize(export_path)
        except Exception:
            pass

        return {
            "exported": True,
            "export_path": export_path,
            "file_size_bytes": file_size,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to export recording at index {recording_index} to '{export_path}'. "
            f"Ensure the recording exists and the destination directory is writable."
        )


# ── Tool 15: import_recording ─────────────────────────────────────────────────


def import_recording(app: Any, import_path: str) -> dict[str, Any]:
    """Import a recording file into the measurement data pool.

    Returns: dict with imported=True, import_path, new_recording_index
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        measurements = mdm.Measurements
        measurements.Load(import_path)
        count_after = measurements.Count

        import os

        filename = os.path.basename(import_path)

        return {
            "imported": True,
            "import_path": import_path,
            "new_recording_index": count_after - 1,
            "filename": filename,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to import recording from '{import_path}'. "
            f"Ensure the file exists and is a valid MF4 recording."
        )


# ── Tool 16: add_bookmark ─────────────────────────────────────────────────────


def add_bookmark(app: Any, title: str, description: str = "") -> dict[str, Any]:
    """Add a bookmark to the current live measurement.

    Returns: dict with added=True, title, description, timestamps
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        current_measurement = mdm.CurrentMeasurement
        bookmarks = current_measurement.Bookmarks
        bookmarks.AddNow(title, description)

        ts = _timestamp_utc()
        return {
            "added": True,
            "title": title,
            "description": description,
            "timestamp_utc": ts,
            "bookmark_timestamp": ts,
        }
    except Exception:
        raise BridgeOperationError(
            "Failed to add bookmark. Ensure measurement is currently running."
        )


# ── Tool 17: list_bookmarks ───────────────────────────────────────────────────


def list_bookmarks(app: Any, recording_index: int) -> dict[str, Any]:
    """List all bookmarks in a recording.

    Returns: dict with recording_index, total_bookmarks, bookmarks array
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        recording = mdm.Measurements.Item(recording_index)
        bookmarks = recording.Bookmarks

        bookmarks_list = []
        for i in range(bookmarks.Count):
            bm = bookmarks.Item(i)
            if bm:
                bookmarks_list.append(
                    {
                        "title": str(bm.Title),
                        "description": str(bm.Description),
                        "timestamp_seconds": float(bm.Timestamp),
                    }
                )

        return {
            "recording_index": recording_index,
            "total_bookmarks": len(bookmarks_list),
            "bookmarks": bookmarks_list,
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to list bookmarks for recording at index {recording_index}. "
            f"Ensure the recording exists."
        )


# ── Tool 18: create_data_logger ───────────────────────────────────────────────


def create_data_logger(app: Any, logger_name: str) -> dict[str, Any]:
    """Create a new data logger and cache it.

    Returns: dict with created=True, logger_name
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        data_loggers = mdm.DataLoggers
        logger = data_loggers.Add(logger_name)
        _data_loggers_cache[logger_name] = logger

        return {
            "created": True,
            "logger_name": logger_name,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to create data logger '{logger_name}'. Logger name may already exist."
        )


# ── Tool 19: configure_data_logger ────────────────────────────────────────────


def configure_data_logger(
    app: Any,
    logger_name: str,
    output_file_path: str,
    file_format: str = "MF4",
    overwrite_existing: bool = True,
) -> dict[str, Any]:
    """Configure a data logger's output file and format.

    Returns: dict with configured=True and settings
    Raises: BridgeOperationError on COM error
    """
    try:
        logger = _data_loggers_cache.get(logger_name)
        if logger is None:
            mdm = app.MeasurementDataManagement
            logger = mdm.DataLoggers.Item(logger_name)
            _data_loggers_cache[logger_name] = logger

        logger.OutputFile = output_file_path
        logger.FileFormat = file_format
        logger.OverwriteExisting = overwrite_existing

        return {
            "configured": True,
            "logger_name": logger_name,
            "output_file_path": output_file_path,
            "file_format": file_format,
            "overwrite_existing": overwrite_existing,
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to configure data logger '{logger_name}'. "
            f"Logger may not exist or is currently running."
        )


# ── Tool 20: start_data_logger ────────────────────────────────────────────────


def start_data_logger(app: Any, logger_name: str) -> dict[str, Any]:
    """Start a data logger.

    Returns: dict with started=True, logger_name
    Raises: BridgeOperationError on COM error
    """
    try:
        logger = _data_loggers_cache.get(logger_name)
        if logger is None:
            mdm = app.MeasurementDataManagement
            logger = mdm.DataLoggers.Item(logger_name)
            _data_loggers_cache[logger_name] = logger

        logger.Start()

        return {
            "started": True,
            "logger_name": logger_name,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to start data logger '{logger_name}'. "
            f"Ensure measurement is running and the logger is configured."
        )


# ── Tool 21: stop_data_logger ─────────────────────────────────────────────────


def stop_data_logger(app: Any, logger_name: str) -> dict[str, Any]:
    """Stop a running data logger and finalize its output file.

    Returns: dict with stopped=True, logger_name
    Raises: BridgeOperationError on COM error
    """
    try:
        logger = _data_loggers_cache.get(logger_name)
        if logger is None:
            mdm = app.MeasurementDataManagement
            logger = mdm.DataLoggers.Item(logger_name)
            _data_loggers_cache[logger_name] = logger

        logger.Stop()

        return {
            "stopped": True,
            "logger_name": logger_name,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to stop data logger '{logger_name}'. Logger may not be running."
        )


# ── Tool 22: list_data_loggers ────────────────────────────────────────────────


def list_data_loggers(app: Any) -> dict[str, Any]:
    """List all data loggers with state and configuration.

    Returns: dict with total_loggers and loggers array
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        data_loggers = mdm.DataLoggers

        loggers_list = []
        for i in range(data_loggers.Count):
            logger = data_loggers.Item(i)
            if logger:
                loggers_list.append(
                    {
                        "logger_name": str(logger.Name),
                        "state": str(logger.State),
                        "output_file_path": str(logger.OutputFile),
                        "file_format": str(logger.FileFormat),
                    }
                )

        return {
            "total_loggers": len(loggers_list),
            "loggers": loggers_list,
        }
    except Exception:
        raise BridgeOperationError("Failed to list data loggers.")


# ── Tool 23: remove_data_logger ───────────────────────────────────────────────


def remove_data_logger(app: Any, logger_name: str) -> dict[str, Any]:
    """Remove a data logger from the measurement configuration.

    Returns: dict with removed=True, logger_name
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        data_loggers = mdm.DataLoggers
        logger = data_loggers.Item(logger_name)
        data_loggers.Remove(logger)

        _data_loggers_cache.pop(logger_name, None)

        return {
            "removed": True,
            "logger_name": logger_name,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to remove data logger '{logger_name}'. " f"Logger may be running or not exist."
        )


# ── Tool 24: add_raster ───────────────────────────────────────────────────────


def add_raster(app: Any, platform_name: str, raster_interval_ms: float) -> dict[str, Any]:
    """Add a measurement raster for a platform.

    Returns: dict with added=True, platform_name, raster_name, raster_interval_ms
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration
        rasters = config.Rasters
        raster = rasters.Add(platform_name, raster_interval_ms)

        return {
            "added": True,
            "platform_name": platform_name,
            "raster_name": str(raster.Name),
            "raster_interval_ms": raster_interval_ms,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to add raster at {raster_interval_ms}ms for platform '{platform_name}'. "
            f"Raster interval may not be supported by this platform."
        )


# ── Tool 25: list_rasters ─────────────────────────────────────────────────────


def list_rasters(app: Any) -> dict[str, Any]:
    """List all measurement rasters for all platforms.

    Returns: dict with total_rasters and rasters array
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration
        rasters = config.Rasters

        rasters_list = []
        for i in range(rasters.Count):
            raster = rasters.Item(i)
            if raster:
                rasters_list.append(
                    {
                        "platform_name": str(raster.PlatformName),
                        "raster_name": str(raster.Name),
                        "raster_interval_ms": float(raster.Interval),
                    }
                )

        return {
            "total_rasters": len(rasters_list),
            "rasters": rasters_list,
        }
    except Exception:
        raise BridgeOperationError("Failed to list measurement rasters.")


# ── Tool 26: remove_raster ────────────────────────────────────────────────────


def remove_raster(app: Any, platform_name: str, raster_name: str) -> dict[str, Any]:
    """Remove a measurement raster by platform and name.

    Returns: dict with removed=True, platform_name, raster_name
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration
        rasters = config.Rasters
        raster = rasters.Item(raster_name)
        rasters.Remove(raster)

        return {
            "removed": True,
            "platform_name": platform_name,
            "raster_name": raster_name,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to remove raster '{raster_name}' for platform '{platform_name}'. "
            f"Raster may not exist or measurement is running."
        )


# ── Tool 27: configure_settings ───────────────────────────────────────────────


def configure_settings(
    app: Any,
    data_pool_path: str | None = None,
    auto_save_enabled: bool | None = None,
    auto_save_format: str | None = None,
) -> dict[str, Any]:
    """Configure global measurement settings.

    Returns: dict with configured=True and current settings
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        config = mdm.MeasurementConfiguration

        if data_pool_path is not None:
            config.DataPoolPath = data_pool_path
        if auto_save_enabled is not None:
            config.AutoSave.Enabled = auto_save_enabled
        if auto_save_format is not None:
            config.AutoSave.Format = auto_save_format

        current_path = str(config.DataPoolPath)
        current_auto_save = bool(config.AutoSave.Enabled)
        current_format = str(config.AutoSave.Format)

        return {
            "configured": True,
            "data_pool_path": current_path,
            "auto_save_enabled": current_auto_save,
            "auto_save_format": current_format,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            "Failed to configure measurement settings. "
            "Ensure measurement is stopped and data pool path exists."
        )


# ── Tool 28: remove_bookmark ──────────────────────────────────────────────────


def remove_bookmark(app: Any, recording_index: int, bookmark_index: int) -> dict[str, Any]:
    """Remove a bookmark from a recording in the data pool.

    Returns: dict with removed=True, recording_index, bookmark_index
    Raises: BridgeOperationError on COM error
    """
    try:
        mdm = app.MeasurementDataManagement
        recording = mdm.Measurements.Item(recording_index)
        bookmarks = recording.Bookmarks
        bookmark = bookmarks.Item(bookmark_index)
        bookmarks.Remove(bookmark)

        return {
            "removed": True,
            "recording_index": recording_index,
            "bookmark_index": bookmark_index,
            "timestamp_utc": _timestamp_utc(),
        }
    except Exception:
        raise BridgeOperationError(
            f"Failed to remove bookmark at index {bookmark_index} from recording "
            f"{recording_index}. Ensure both indices are valid."
        )


# ── Cache management ──────────────────────────────────────────────────────────


def clear_cache() -> None:
    """Clear all cached COM references. Called on shutdown."""
    global _measurement_data_mgmt
    _measurement_data_mgmt = None
    _trigger_rules_cache.clear()
    _data_loggers_cache.clear()
