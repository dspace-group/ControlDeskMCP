"""Service facade for ControlDesk measurement operations.

Owns: orchestration of measurement lifecycle, signals, triggers, loggers, rasters.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from sources import com_bridge
from sources.com_bridge.errors import BridgeError
from sources.models.envelope_builder import build_envelope
from sources.models.errors import ErrorEnvelope
from sources.models.measurement import (
    DataLoggerConfigureInput,
    DataLoggerConfigureResult,
    DataLoggerCreateInput,
    DataLoggerCreateResult,
    DataLoggerListInput,
    DataLoggerListResult,
    DataLoggerRemoveInput,
    DataLoggerRemoveResult,
    DataLoggerStartInput,
    DataLoggerStartResult,
    DataLoggerStopInput,
    DataLoggerStopResult,
    MeasurementBookmarkAddInput,
    MeasurementBookmarkAddResult,
    MeasurementBookmarkListInput,
    MeasurementBookmarkListResult,
    MeasurementBookmarkRemoveInput,
    MeasurementBookmarkRemoveResult,
    MeasurementConfigureBufferInput,
    MeasurementConfigureBufferResult,
    MeasurementConfigureSettingsInput,
    MeasurementConfigureSettingsResult,
    MeasurementExportRecordingInput,
    MeasurementExportRecordingResult,
    MeasurementGetConfigurationInput,
    MeasurementGetConfigurationResult,
    MeasurementGetStateInput,
    MeasurementGetStateResult,
    MeasurementImportRecordingInput,
    MeasurementImportRecordingResult,
    MeasurementListRecordingsInput,
    MeasurementListRecordingsResult,
    MeasurementListSignalsInput,
    MeasurementListSignalsResult,
    MeasurementRasterAddInput,
    MeasurementRasterAddResult,
    MeasurementRasterListInput,
    MeasurementRasterListResult,
    MeasurementRasterRemoveInput,
    MeasurementRasterRemoveResult,
    MeasurementSignalAddInput,
    MeasurementSignalAddResult,
    MeasurementSignalRemoveInput,
    MeasurementSignalRemoveResult,
    MeasurementStartInput,
    MeasurementStartResult,
    MeasurementStopInput,
    MeasurementStopResult,
    TriggerConditionTimeLimitInput,
    TriggerConditionTimeLimitResult,
    TriggerConditionTriggerBasedInput,
    TriggerConditionTriggerBasedResult,
    TriggerRuleCreateInput,
    TriggerRuleCreateResult,
    TriggerRuleRemoveInput,
    TriggerRuleRemoveResult,
)
from sources.utils.logger import get_logger

_log = get_logger(__name__)


async def signal_add(
    params: MeasurementSignalAddInput,
) -> MeasurementSignalAddResult | ErrorEnvelope:
    """Add a signal to the measurement configuration."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.signal_add,
            app,
            params.connection_path,
        )
        return MeasurementSignalAddResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def signal_remove(
    params: MeasurementSignalRemoveInput,
) -> MeasurementSignalRemoveResult | ErrorEnvelope:
    """Remove a signal from the measurement configuration."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.signal_remove,
            app,
            params.connection_path,
        )
        return MeasurementSignalRemoveResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_signals(
    params: MeasurementListSignalsInput,
) -> MeasurementListSignalsResult | ErrorEnvelope:  # noqa: ARG001
    """List all configured signals."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.list_signals,
            app,
        )
        return MeasurementListSignalsResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def configure_buffer(
    params: MeasurementConfigureBufferInput,
) -> MeasurementConfigureBufferResult | ErrorEnvelope:
    """Configure the measurement buffer."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.configure_buffer,
            app,
            params.buffer_size_seconds,
            params.warning_enabled,
            params.warning_time_seconds,
        )
        return MeasurementConfigureBufferResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def get_configuration(  # noqa: ARG001
    params: MeasurementGetConfigurationInput,
) -> MeasurementGetConfigurationResult | ErrorEnvelope:
    """Get current measurement configuration state."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.get_configuration,
            app,
        )
        return MeasurementGetConfigurationResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def start_measurement(
    params: MeasurementStartInput,
) -> MeasurementStartResult | ErrorEnvelope:  # noqa: ARG001
    """Start measurement on all connected platforms."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.start_measurement,
            app,
        )
        return MeasurementStartResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def stop_measurement(
    params: MeasurementStopInput,
) -> MeasurementStopResult | ErrorEnvelope:  # noqa: ARG001
    """Stop measurement on all platforms."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.stop_measurement,
            app,
        )
        return MeasurementStopResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def get_measurement_state(
    params: MeasurementGetStateInput,
) -> MeasurementGetStateResult | ErrorEnvelope:  # noqa: ARG001
    """Query current measurement state."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.get_measurement_state,
            app,
        )
        return MeasurementGetStateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def create_trigger_rule(
    params: TriggerRuleCreateInput,
) -> TriggerRuleCreateResult | ErrorEnvelope:
    """Create a trigger rule."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.create_trigger_rule,
            app,
            params.rule_name,
            params.expression,
            params.signal_mappings,
        )
        return TriggerRuleCreateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_trigger_rule(
    params: TriggerRuleRemoveInput,
) -> TriggerRuleRemoveResult | ErrorEnvelope:
    """Remove a trigger rule."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.remove_trigger_rule,
            app,
            params.rule_name,
        )
        return TriggerRuleRemoveResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def configure_time_limit_condition(
    params: TriggerConditionTimeLimitInput,
) -> TriggerConditionTimeLimitResult | ErrorEnvelope:
    """Configure time-limit stop condition on the main recorder."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.configure_time_limit_condition,
            app,
            params.enabled,
            params.time_limit_seconds,
        )
        return TriggerConditionTimeLimitResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def configure_trigger_based_condition(
    params: TriggerConditionTriggerBasedInput,
) -> TriggerConditionTriggerBasedResult | ErrorEnvelope:
    """Attach a trigger rule to recorder start/stop condition."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.configure_trigger_based_condition,
            app,
            params.condition_type.value,
            params.rule_name,
            params.enabled,
            params.trigger_delay_seconds,
            params.recording_cycles,
        )
        return TriggerConditionTriggerBasedResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_recordings(
    params: MeasurementListRecordingsInput,
) -> MeasurementListRecordingsResult | ErrorEnvelope:  # noqa: ARG001
    """List all recordings in the measurement data pool."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.list_recordings,
            app,
        )
        return MeasurementListRecordingsResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def export_recording(
    params: MeasurementExportRecordingInput,
) -> MeasurementExportRecordingResult | ErrorEnvelope:
    """Export a recording to an external MF4 file."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.export_recording,
            app,
            params.recording_index,
            params.export_path,
            params.overwrite_existing,
        )
        return MeasurementExportRecordingResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def import_recording(
    params: MeasurementImportRecordingInput,
) -> MeasurementImportRecordingResult | ErrorEnvelope:
    """Import a recording file into the data pool."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.import_recording,
            app,
            params.import_path,
        )
        return MeasurementImportRecordingResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def add_bookmark(
    params: MeasurementBookmarkAddInput,
) -> MeasurementBookmarkAddResult | ErrorEnvelope:
    """Add a bookmark to the current live measurement."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.add_bookmark,
            app,
            params.title,
            params.description,
        )
        return MeasurementBookmarkAddResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_bookmarks(
    params: MeasurementBookmarkListInput,
) -> MeasurementBookmarkListResult | ErrorEnvelope:
    """List all bookmarks in a recording."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.list_bookmarks,
            app,
            params.recording_index,
        )
        return MeasurementBookmarkListResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def create_data_logger(
    params: DataLoggerCreateInput,
) -> DataLoggerCreateResult | ErrorEnvelope:
    """Create a new data logger."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.create_data_logger,
            app,
            params.logger_name,
        )
        return DataLoggerCreateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def configure_data_logger(
    params: DataLoggerConfigureInput,
) -> DataLoggerConfigureResult | ErrorEnvelope:
    """Configure a data logger's output file and format."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.configure_data_logger,
            app,
            params.logger_name,
            params.output_file_path,
            params.file_format.value,
            params.overwrite_existing,
        )
        return DataLoggerConfigureResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def start_data_logger(params: DataLoggerStartInput) -> DataLoggerStartResult | ErrorEnvelope:
    """Start a data logger."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.start_data_logger,
            app,
            params.logger_name,
        )
        return DataLoggerStartResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def stop_data_logger(params: DataLoggerStopInput) -> DataLoggerStopResult | ErrorEnvelope:
    """Stop a data logger."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.stop_data_logger,
            app,
            params.logger_name,
        )
        return DataLoggerStopResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_data_loggers(
    params: DataLoggerListInput,
) -> DataLoggerListResult | ErrorEnvelope:  # noqa: ARG001
    """List all data loggers."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.list_data_loggers,
            app,
        )
        return DataLoggerListResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_data_logger(
    params: DataLoggerRemoveInput,
) -> DataLoggerRemoveResult | ErrorEnvelope:
    """Remove a data logger."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.remove_data_logger,
            app,
            params.logger_name,
        )
        return DataLoggerRemoveResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def add_raster(
    params: MeasurementRasterAddInput,
) -> MeasurementRasterAddResult | ErrorEnvelope:
    """Add a measurement raster for a platform."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.add_raster,
            app,
            params.platform_name,
            params.raster_interval_ms,
        )
        return MeasurementRasterAddResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_rasters(
    params: MeasurementRasterListInput,
) -> MeasurementRasterListResult | ErrorEnvelope:  # noqa: ARG001
    """List all measurement rasters."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.list_rasters,
            app,
        )
        return MeasurementRasterListResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_raster(
    params: MeasurementRasterRemoveInput,
) -> MeasurementRasterRemoveResult | ErrorEnvelope:
    """Remove a measurement raster."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.remove_raster,
            app,
            params.platform_name,
            params.raster_name,
        )
        return MeasurementRasterRemoveResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def configure_settings(
    params: MeasurementConfigureSettingsInput,
) -> MeasurementConfigureSettingsResult | ErrorEnvelope:
    """Configure global measurement settings."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.configure_settings,
            app,
            params.data_pool_path,
            params.auto_save_enabled,
            params.auto_save_format.value if params.auto_save_format is not None else None,
        )
        return MeasurementConfigureSettingsResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_bookmark(
    params: MeasurementBookmarkRemoveInput,
) -> MeasurementBookmarkRemoveResult | ErrorEnvelope:
    """Remove a bookmark from a recording."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.measurement_com.remove_bookmark,
            app,
            params.recording_index,
            params.bookmark_index,
        )
        return MeasurementBookmarkRemoveResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)
