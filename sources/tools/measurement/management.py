"""MCP tools for ControlDesk measurement operations.

Tools implemented (domain: measurement):

  MAIN (always loaded):
    measurement_start   — Start measurement on all connected platforms
    measurement_stop    — Stop measurement on all platforms
    measurement_manage  — Core operations: get_state, get_configuration,
                          configure_buffer, configure_settings,
                          signal_add, signal_remove, list_signals

  ADD_ON lazy (access via measurement_discover):
    GROUP: RASTERS
      measurement_raster_manage — Raster operations: raster_add, raster_list, raster_remove

    GROUP: TRIGGERS
      trigger_manage    — Trigger lifecycle: rule_create, rule_remove,
                          condition_time_limit, condition_trigger_based

    GROUP: RECORDINGS
      recording_manage  — Recordings and bookmarks: list_recordings,
                          export_recording, import_recording,
                          bookmark_add, bookmark_list, bookmark_remove

    GROUP: DATA_LOGGING
      data_logger_manage — Data logger lifecycle: create, configure,
                           start, stop, list, remove

  META / Discovery:
    measurement_discover — Returns catalogue of all lazy add-on tools

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to sources.services.measurement_service.
"""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import Context

from sources.config.settings import get_settings
from sources.models.errors import ErrorEnvelope
from sources.models.measurement import (
    DataLoggerConfigureInput,
    DataLoggerCreateInput,
    DataLoggerListInput,
    DataLoggerManageAction,
    DataLoggerManageInput,
    DataLoggerRemoveInput,
    DataLoggerStartInput,
    DataLoggerStopInput,
    MeasurementBookmarkAddInput,
    MeasurementBookmarkListInput,
    MeasurementBookmarkRemoveInput,
    MeasurementConfigureBufferInput,
    MeasurementConfigureSettingsInput,
    MeasurementDiscoverResult,
    MeasurementExportRecordingInput,
    MeasurementGetConfigurationInput,
    MeasurementGetStateInput,
    MeasurementImportRecordingInput,
    MeasurementListRecordingsInput,
    MeasurementListSignalsInput,
    MeasurementManageAction,
    MeasurementManageInput,
    MeasurementQueryAction,
    MeasurementQueryInput,
    MeasurementRasterAddInput,
    MeasurementRasterListInput,
    MeasurementRasterManageAction,
    MeasurementRasterManageInput,
    MeasurementRasterRemoveInput,
    MeasurementSignalAddInput,
    MeasurementSignalRemoveInput,
    MeasurementStartInput,
    MeasurementStopInput,
    RecordingManageAction,
    RecordingManageInput,
    ToolActionEntry,
    TriggerConditionTimeLimitInput,
    TriggerConditionTriggerBasedInput,
    TriggerManageAction,
    TriggerManageInput,
    TriggerRuleCreateInput,
    TriggerRuleRemoveInput,
)
from sources.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from sources.server.app import mcp
from sources.server.server import MCPToolCategory
from sources.services import measurement_service
from sources.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — measurement_start ────────────────────────────────────────────────


@mcp.tool(
    name="measurement_start",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Starts measurement on all connected platforms. The measurement process begins "
        "sampling all configured signals at their specified raster rates into the measurement "
        "buffer. This must be called BEFORE recorder_main_start to ensure data is being "
        "buffered. "
        "Preconditions: online calibration must be running; at least one platform "
        "must be connected. "
        "Do not call if measurement is already running — calling again while active returns "
        "an error and does not restart or reset measurement."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.RECORDING),
)
async def measurement_start(params: MeasurementStartInput) -> object:
    return await measurement_service.start_measurement(params)


# ── Tool 2 — measurement_stop ─────────────────────────────────────────────────


@mcp.tool(
    name="measurement_stop",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Stops measurement on all platforms. All recorders are stopped automatically. "
        "This should be called AFTER recorder_main_stop to allow final data to be written. "
        "Preconditions: measurement must be running (started via measurement_start)."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.RECORDING),
)
async def measurement_stop(params: MeasurementStopInput) -> object:
    return await measurement_service.stop_measurement(params)


# ── Tool 3 — measurement_manage ───────────────────────────────────────────────


@mcp.tool(
    name="measurement_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages core measurement configuration and signal operations (mutating only). "
        "Set 'action' to specify what to do: "
        "'configure_buffer' — set buffer size and overflow warning (requires buffer_size_seconds); "
        "'configure_settings' — set data pool path and auto-save behavior; "
        "'signal_add' — add a variable signal (requires connection_path; replay risk: "
        "calling 'signal_add' again with the same connection_path may fail with a duplicate-signal "
        "error, so check measurement_query(action='list_signals') first); "
        "'signal_remove' — remove a signal (requires connection_path). "
        "Use measurement_discover to query state/configuration/signals (measurement_query) and for "
        "raster management, trigger rules, recordings, bookmarks, and data loggers."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.RECORDING),
)
async def measurement_manage(params: MeasurementManageInput) -> object:
    if params.action == MeasurementManageAction.configure_buffer:
        if params.buffer_size_seconds is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="buffer_size_seconds is required when action='configure_buffer'.",
                recovery_hint="Set buffer_size_seconds to the desired buffer duration.",
            )
        return await measurement_service.configure_buffer(
            MeasurementConfigureBufferInput(
                buffer_size_seconds=params.buffer_size_seconds,
                warning_enabled=params.warning_enabled,
                warning_time_seconds=params.warning_time_seconds,
            )
        )
    if params.action == MeasurementManageAction.configure_settings:
        return await measurement_service.configure_settings(
            MeasurementConfigureSettingsInput(
                data_pool_path=params.data_pool_path,
                auto_save_enabled=params.auto_save_enabled,
                auto_save_format=params.auto_save_format,
            )
        )
    if params.action == MeasurementManageAction.signal_add:
        if params.connection_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="connection_path is required when action='signal_add'.",
                recovery_hint="Set connection_path to the signal path (e.g., 'XCP(5ms)://signal').",
            )
        return await measurement_service.signal_add(
            MeasurementSignalAddInput(connection_path=params.connection_path)
        )
    if params.action == MeasurementManageAction.signal_remove:
        if params.connection_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="connection_path is required when action='signal_remove'.",
                recovery_hint="Set connection_path to the signal path to remove.",
            )
        return await measurement_service.signal_remove(
            MeasurementSignalRemoveInput(connection_path=params.connection_path)
        )
    # signal_add
    if params.connection_path is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="connection_path is required when action='signal_add'.",
            recovery_hint="Set connection_path to the signal path (e.g., 'XCP(5ms)://signal').",
        )
    return await measurement_service.signal_add(
        MeasurementSignalAddInput(connection_path=params.connection_path)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via measurement_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: MEASUREMENT_QUERY ───────────────────────────────────────────────────────────
# ── Tool 4 — measurement_query ───────────────────────────────────────────────────


@mcp.tool(
    name="measurement_query",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Read-only queries for measurement state and signals (readOnlyHint=true). "
        "Set 'action' to specify what to do: "
        "'get_state' — query current state (Measuring/NotMeasuring); "
        "'get_configuration' — get buffer size, signal count, and platform connectivity; "
        "'list_signals' — enumerate configured signals with metadata (paginated). "
        "Use measurement_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.RECORDING),
)
async def measurement_query(params: MeasurementQueryInput) -> object:
    if params.action == MeasurementQueryAction.get_state:
        return await measurement_service.get_measurement_state(MeasurementGetStateInput())
    if params.action == MeasurementQueryAction.get_configuration:
        return await measurement_service.get_configuration(MeasurementGetConfigurationInput())
    # list_signals
    result = await measurement_service.list_signals(
        MeasurementListSignalsInput(limit=params.limit, offset=params.offset)
    )
    if isinstance(result, ErrorEnvelope):
        return result
    from sources.models.measurement import MeasurementListSignalsResult

    return MeasurementListSignalsResult(
        **paginate(result.model_dump(), params.offset, params.limit, "signals")
    )


# ── GROUP: RASTERS ─────────────────────────────────────────────────────────────────
# ── Tool 5 — measurement_raster_manage ───────────────────────────────────────────


@mcp.tool(
    name="measurement_raster_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages measurement rasters (sampling intervals). "
        "Set 'action' to specify what to do: "
        "'raster_add' — add a sampling raster for a platform "
        "(requires platform_name, raster_interval_ms; measurement must NOT be running); "
        "'raster_list' — list all configured rasters; "
        "'raster_remove' — remove a raster "
        "(requires platform_name, raster_name; measurement must NOT be running). "
        "Use measurement_discover to access this tool."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.RECORDING),
)
async def measurement_raster_manage(params: MeasurementRasterManageInput) -> object:
    if params.action == MeasurementRasterManageAction.raster_add:
        if params.platform_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name is required when action='raster_add'.",
                recovery_hint="Set platform_name to the platform to add the raster to.",
            )
        if params.raster_interval_ms is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="raster_interval_ms is required when action='raster_add'.",
                recovery_hint="Set raster_interval_ms (e.g., 5.0 for 5ms).",
            )
        return await measurement_service.add_raster(
            MeasurementRasterAddInput(
                platform_name=params.platform_name,
                raster_interval_ms=params.raster_interval_ms,
            )
        )
    if params.action == MeasurementRasterManageAction.raster_list:
        result = await measurement_service.list_rasters(
            MeasurementRasterListInput(limit=params.limit, offset=params.offset)
        )
        if isinstance(result, ErrorEnvelope):
            return result
        from sources.models.measurement import MeasurementRasterListResult

        return MeasurementRasterListResult(
            **paginate(result.model_dump(), params.offset, params.limit, "rasters")
        )
    # raster_remove
    if params.platform_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="platform_name is required when action='raster_remove'.",
            recovery_hint="Set platform_name to the platform owning the raster.",
        )
    if params.raster_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="raster_name is required when action='raster_remove'.",
            recovery_hint="Set raster_name to the name of the raster to remove.",
        )
    return await measurement_service.remove_raster(
        MeasurementRasterRemoveInput(
            platform_name=params.platform_name,
            raster_name=params.raster_name,
        )
    )


# ── GROUP: TRIGGERS ───────────────────────────────────────────────────────────
# ── Tool 5 — trigger_manage ───────────────────────────────────────────────────


@mcp.tool(
    name="trigger_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages trigger rules and recorder start/stop conditions. "
        "Set 'action' to specify what to do: "
        "'rule_create' — create a trigger rule with an expression and signal mappings "
        "(requires rule_name, expression, signal_mappings); "
        "'rule_remove' — remove a trigger rule (requires rule_name; detach from conditions first); "
        "'condition_time_limit' — configure a time-limit stop condition on the main recorder "
        "(requires enabled, time_limit_seconds); "
        "'condition_trigger_based' — attach a trigger rule to recorder start or stop condition "
        "(requires enabled, condition_type, rule_name). "
        "Preconditions: online calibration running; signals in mappings must exist."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.TRIGGERS),
)
async def trigger_manage(params: TriggerManageInput) -> object:
    if params.action == TriggerManageAction.rule_create:
        if params.rule_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="rule_name is required when action='rule_create'.",
                recovery_hint="Set rule_name to a unique name for the trigger rule.",
            )
        if params.expression is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="expression is required when action='rule_create'.",
                recovery_hint="Set expression to the logical expression (e.g., 'signal > 0').",
            )
        if params.signal_mappings is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="signal_mappings is required when action='rule_create'.",
                recovery_hint="Set signal_mappings as alias-to-connection-path dict.",
            )
        return await measurement_service.create_trigger_rule(
            TriggerRuleCreateInput(
                rule_name=params.rule_name,
                expression=params.expression,
                signal_mappings=params.signal_mappings,
            )
        )
    if params.action == TriggerManageAction.rule_remove:
        if params.rule_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="rule_name is required when action='rule_remove'.",
                recovery_hint="Set rule_name to the name of the rule to remove.",
            )
        return await measurement_service.remove_trigger_rule(
            TriggerRuleRemoveInput(rule_name=params.rule_name)
        )
    if params.action == TriggerManageAction.condition_time_limit:
        if params.enabled is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="enabled is required when action='condition_time_limit'.",
                recovery_hint="Set enabled=True to activate or enabled=False to disable.",
            )
        if params.time_limit_seconds is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="time_limit_seconds is required when action='condition_time_limit'.",
                recovery_hint="Set time_limit_seconds to the recording duration in seconds.",
            )
        return await measurement_service.configure_time_limit_condition(
            TriggerConditionTimeLimitInput(
                enabled=params.enabled,
                time_limit_seconds=params.time_limit_seconds,
            )
        )
    # condition_trigger_based
    if params.enabled is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="enabled is required when action='condition_trigger_based'.",
            recovery_hint="Set enabled=True to activate the condition.",
        )
    if params.condition_type is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="condition_type is required when action='condition_trigger_based'.",
            recovery_hint="Set condition_type to 'start' or 'stop'.",
        )
    if params.rule_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="rule_name is required when action='condition_trigger_based'.",
            recovery_hint="Set rule_name to the trigger rule to attach.",
        )
    return await measurement_service.configure_trigger_based_condition(
        TriggerConditionTriggerBasedInput(
            condition_type=params.condition_type,
            rule_name=params.rule_name,
            enabled=params.enabled,
            trigger_delay_seconds=params.trigger_delay_seconds,
            recording_cycles=params.recording_cycles,
        )
    )


# ── GROUP: RECORDINGS ─────────────────────────────────────────────────────────
# ── Tool 6 — recording_manage ─────────────────────────────────────────────────


@mcp.tool(
    name="recording_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages recordings in the data pool and measurement bookmarks. "
        "Set 'action' to specify what to do: "
        "'list_recordings' — list all completed recordings with metadata; "
        "'export_recording' — export a recording to an MF4 file "
        "(requires recording_index, export_path); "
        "'import_recording' — import an MF4 file into the data pool (requires import_path); "
        "'bookmark_add' — add a bookmark to the current measurement (requires title; "
        "measurement must be running); "
        "'bookmark_list' — list bookmarks from a recording (requires recording_index); "
        "'bookmark_remove' — remove a bookmark (requires recording_index, bookmark_index). "
        "Use measurement_discover to access this tool."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.DATA_EXPORT),
)
async def recording_manage(params: RecordingManageInput) -> object:
    if params.action == RecordingManageAction.list_recordings:
        result = await measurement_service.list_recordings(
            MeasurementListRecordingsInput(limit=params.limit, offset=params.offset)
        )
        if isinstance(result, ErrorEnvelope):
            return result
        from sources.models.measurement import MeasurementListRecordingsResult

        return MeasurementListRecordingsResult(
            **paginate(result.model_dump(), params.offset, params.limit, "recordings")
        )
    if params.action == RecordingManageAction.export_recording:
        if params.recording_index is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="recording_index is required when action='export_recording'.",
                recovery_hint="Set recording_index to the index of the recording to export.",
            )
        if params.export_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="export_path is required when action='export_recording'.",
                recovery_hint="Set export_path to the absolute destination file path.",
            )
        p = Path(params.export_path)
        if not p.is_absolute() or ".." in p.parts:
            return ErrorEnvelope(
                error_code="INVALID_PARAM",
                category="INPUT_VALIDATION",
                message="export_path must be an absolute path without '..' segments.",
                recovery_hint="Provide a fully qualified absolute path.",
            )
        return await measurement_service.export_recording(
            MeasurementExportRecordingInput(
                recording_index=params.recording_index,
                export_path=params.export_path,
                overwrite_existing=params.overwrite_existing,
            )
        )
    if params.action == RecordingManageAction.import_recording:
        if params.import_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="import_path is required when action='import_recording'.",
                recovery_hint="Set import_path to the absolute path of the MF4 file to import.",
            )
        p = Path(params.import_path)
        if not p.is_absolute() or ".." in p.parts:
            return ErrorEnvelope(
                error_code="INVALID_PARAM",
                category="INPUT_VALIDATION",
                message="import_path must be an absolute path without '..' segments.",
                recovery_hint="Provide a fully qualified absolute path.",
            )
        return await measurement_service.import_recording(
            MeasurementImportRecordingInput(import_path=params.import_path)
        )
    if params.action == RecordingManageAction.bookmark_add:
        if params.title is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="title is required when action='bookmark_add'.",
                recovery_hint="Set title to a short description of the bookmark event.",
            )
        return await measurement_service.add_bookmark(
            MeasurementBookmarkAddInput(title=params.title, description=params.description)
        )
    if params.action == RecordingManageAction.bookmark_list:
        if params.recording_index is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="recording_index is required when action='bookmark_list'.",
                recovery_hint="Set recording_index to the index of the recording.",
            )
        result = await measurement_service.list_bookmarks(
            MeasurementBookmarkListInput(
                recording_index=params.recording_index,
                limit=params.limit,
                offset=params.offset,
            )
        )
        if isinstance(result, ErrorEnvelope):
            return result
        from sources.models.measurement import MeasurementBookmarkListResult

        return MeasurementBookmarkListResult(
            **paginate(result.model_dump(), params.offset, params.limit, "bookmarks")
        )
    # bookmark_remove
    if params.recording_index is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="recording_index is required when action='bookmark_remove'.",
            recovery_hint="Set recording_index to the recording containing the bookmark.",
        )
    if params.bookmark_index is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="bookmark_index is required when action='bookmark_remove'.",
            recovery_hint="Use bookmark_list to find the index, then set bookmark_index.",
        )
    return await measurement_service.remove_bookmark(
        MeasurementBookmarkRemoveInput(
            recording_index=params.recording_index,
            bookmark_index=params.bookmark_index,
        )
    )


# ── GROUP: DATA_LOGGING ───────────────────────────────────────────────────────
# ── Tool 7 — data_logger_manage ───────────────────────────────────────────────


@mcp.tool(
    name="data_logger_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages data logger lifecycle within measurement data management. "
        "Set 'action' to specify what to do: "
        "'create' — create a named data logger (requires logger_name); "
        "'configure' — set output file path and format (requires logger_name, output_file_path; "
        "logger must NOT be running); "
        "'start' — start writing to the output file (requires logger_name; "
        "measurement must be running); "
        "'stop' — stop writing and finalize the output file (requires logger_name); "
        "'list' — list all data loggers with state and file configuration; "
        "'remove' — remove a logger registration (requires logger_name; stop first). "
        "Use measurement_discover to access this tool."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.DATA_LOGGING),
)
async def data_logger_manage(params: DataLoggerManageInput) -> object:
    if params.action == DataLoggerManageAction.create:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='create'.",
                recovery_hint="Set logger_name to a unique name for the data logger.",
            )
        return await measurement_service.create_data_logger(
            DataLoggerCreateInput(logger_name=params.logger_name)
        )
    if params.action == DataLoggerManageAction.configure:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='configure'.",
                recovery_hint="Set logger_name to the name of the logger to configure.",
            )
        if params.output_file_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="output_file_path is required when action='configure'.",
                recovery_hint="Set output_file_path to the absolute destination file path.",
            )
        return await measurement_service.configure_data_logger(
            DataLoggerConfigureInput(
                logger_name=params.logger_name,
                output_file_path=params.output_file_path,
                file_format=params.file_format,
                overwrite_existing=params.overwrite_existing,
            )
        )
    if params.action == DataLoggerManageAction.start:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='start'.",
                recovery_hint="Set logger_name to the name of the logger to start.",
            )
        return await measurement_service.start_data_logger(
            DataLoggerStartInput(logger_name=params.logger_name)
        )
    if params.action == DataLoggerManageAction.stop:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='stop'.",
                recovery_hint="Set logger_name to the name of the logger to stop.",
            )
        return await measurement_service.stop_data_logger(
            DataLoggerStopInput(logger_name=params.logger_name)
        )
    if params.action == DataLoggerManageAction.list:
        result = await measurement_service.list_data_loggers(
            DataLoggerListInput(limit=params.limit, offset=params.offset)
        )
        if isinstance(result, ErrorEnvelope):
            return result
        from sources.models.measurement import DataLoggerListResult

        return DataLoggerListResult(
            **paginate(result.model_dump(), params.offset, params.limit, "loggers")
        )
    # remove
    if params.logger_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="logger_name is required when action='remove'.",
            recovery_hint="Set logger_name to the name of the logger to remove.",
        )
    return await measurement_service.remove_data_logger(
        DataLoggerRemoveInput(logger_name=params.logger_name)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 8 — measurement_discover ─────────────────────────────────────────────


@mcp.tool(
    name="measurement_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available measurement operations "
        "that are not loaded by default. Call this tool first when you need to manage "
        "trigger rules, recording files, bookmarks, or data loggers. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.MEASUREMENT, ToolGroup.RECORDING),
)
async def measurement_discover(ctx: Context) -> MeasurementDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.MEASUREMENT, ctx)
    return MeasurementDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="measurement_query",
                purpose="Read-only queries: get measurement state, get configuration, or list configured signals.",
                actions=["get_state", "get_configuration", "list_signals"],
                required_params_per_action={
                    "get_state": [],
                    "get_configuration": [],
                    "list_signals": [],
                },
            ),
            ToolActionEntry(
                tool_name="measurement_raster_manage",
                purpose=(
                    "Manage measurement rasters (sampling intervals): "
                    "add, list, or remove rasters for platform signal acquisition."
                ),
                actions=["raster_add", "raster_list", "raster_remove"],
                required_params_per_action={
                    "raster_add": ["platform_name", "raster_interval_ms"],
                    "raster_list": [],
                    "raster_remove": ["platform_name", "raster_name"],
                },
            ),
            ToolActionEntry(
                tool_name="trigger_manage",
                purpose=(
                    "Manage trigger rules and recorder start/stop conditions: "
                    "create/remove rules, configure time-limit or trigger-based conditions."
                ),
                actions=[
                    "rule_create",
                    "rule_remove",
                    "condition_time_limit",
                    "condition_trigger_based",
                ],
                required_params_per_action={
                    "rule_create": ["rule_name", "expression", "signal_mappings"],
                    "rule_remove": ["rule_name"],
                    "condition_time_limit": ["enabled", "time_limit_seconds"],
                    "condition_trigger_based": ["enabled", "condition_type", "rule_name"],
                },
            ),
            ToolActionEntry(
                tool_name="recording_manage",
                purpose=(
                    "Manage recordings in the data pool and measurement bookmarks: "
                    "list/export/import recordings, add/list/remove bookmarks."
                ),
                actions=[
                    "list_recordings",
                    "export_recording",
                    "import_recording",
                    "bookmark_add",
                    "bookmark_list",
                    "bookmark_remove",
                ],
                required_params_per_action={
                    "list_recordings": [],
                    "export_recording": ["recording_index", "export_path"],
                    "import_recording": ["import_path"],
                    "bookmark_add": ["title"],
                    "bookmark_list": ["recording_index"],
                    "bookmark_remove": ["recording_index", "bookmark_index"],
                },
            ),
            ToolActionEntry(
                tool_name="data_logger_manage",
                purpose=(
                    "Manage data logger lifecycle: "
                    "create, configure, start, stop, list, or remove data loggers."
                ),
                actions=["create", "configure", "start", "stop", "list", "remove"],
                required_params_per_action={
                    "create": ["logger_name"],
                    "configure": ["logger_name", "output_file_path"],
                    "start": ["logger_name"],
                    "stop": ["logger_name"],
                    "list": [],
                    "remove": ["logger_name"],
                },
            ),
        ]
    )
