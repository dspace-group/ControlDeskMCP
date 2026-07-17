"""Pydantic input and response models for the measurement domain.

Domain: ControlDesk Measurement (signal management, lifecycle, trigger rules,
        data loggers, rasters, recordings, bookmarks).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from sources.models.base import DictModelMixin  # noqa: TCH002


def _validate_abs_path(field_name: str, v: str) -> str:
    """Reject relative paths and directory-traversal segments."""
    p = Path(v)
    if not p.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path.")
    if ".." in p.parts:
        raise ValueError(f"{field_name} must not contain '..' segments.")
    return v


# ── Enums ───────────────────────────────────────────────────────────────────────


class MeasurementState(str, Enum):
    """Current measurement acquisition state."""

    Measuring = "Measuring"
    NotMeasuring = "NotMeasuring"


class RecordingState(str, Enum):
    """Data logger or recorder state."""

    Running = "Running"
    Stopped = "Stopped"
    Paused = "Paused"


class StopConditionType(str, Enum):
    """Stop condition trigger type."""

    TimeLimit = "TimeLimit"
    Trigger = "Trigger"
    SampleCount = "SampleCount"


class ConditionType(str, Enum):
    """Trigger condition direction: start or stop condition on the recorder."""

    start = "start"
    stop = "stop"


class DataLoggerFileFormat(str, Enum):
    """Output file format for data loggers."""

    MF4 = "MF4"
    ASC = "ASC"
    CSV = "CSV"


class AutoSaveFormat(str, Enum):
    """Auto-save format for global measurement settings."""

    MF4 = "MF4"
    ASC = "ASC"


class MeasurementQueryAction(str, Enum):
    """Actions for measurement_query read-only tool."""

    get_state = "get_state"
    get_configuration = "get_configuration"
    list_signals = "list_signals"


class MeasurementManageAction(str, Enum):
    """Actions for measurement_manage consolidated tool (mutating only)."""

    configure_buffer = "configure_buffer"
    configure_settings = "configure_settings"
    signal_add = "signal_add"
    signal_remove = "signal_remove"


class MeasurementRasterManageAction(str, Enum):
    """Actions for measurement_raster_manage consolidated tool."""

    raster_add = "raster_add"
    raster_list = "raster_list"
    raster_remove = "raster_remove"


class TriggerManageAction(str, Enum):
    """Actions for trigger_manage consolidated tool."""

    rule_create = "rule_create"
    rule_remove = "rule_remove"
    condition_time_limit = "condition_time_limit"
    condition_trigger_based = "condition_trigger_based"


class RecordingManageAction(str, Enum):
    """Actions for recording_manage consolidated tool."""

    list_recordings = "list_recordings"
    export_recording = "export_recording"
    import_recording = "import_recording"
    bookmark_add = "bookmark_add"
    bookmark_list = "bookmark_list"
    bookmark_remove = "bookmark_remove"


class DataLoggerManageAction(str, Enum):
    """Actions for data_logger_manage consolidated tool."""

    create = "create"
    configure = "configure"
    start = "start"
    stop = "stop"
    list = "list"
    remove = "remove"


# ── Input models ────────────────────────────────────────────────────────────────


class MeasurementSignalAddInput(BaseModel):
    """Input for measurement_signal_add."""

    connection_path: str = Field(
        description=(
            "Fully qualified connection path in format PlatformName(RasterName)://VariableName "
            "(e.g., 'XCP(5ms)://control_out', 'XCP()://SignalGenOutput_2')."
        ),
        examples=["XCP(5ms)://control_out", "XCP()://SignalGenOutput_2"],
    )


class MeasurementSignalRemoveInput(BaseModel):
    """Input for measurement_signal_remove."""

    connection_path: str = Field(
        description=(
            "Connection path of the signal to remove "
            "(e.g., 'XCP(5ms)://control_out'). Must match exactly as shown in "
            "measurement_list_signals."
        ),
        examples=["XCP(5ms)://control_out"],
    )


class MeasurementListSignalsInput(BaseModel):
    """Input for measurement_list_signals."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class MeasurementConfigureBufferInput(BaseModel):
    """Input for measurement_configure_buffer."""

    buffer_size_seconds: float = Field(
        description=(
            "Ring buffer size in seconds (e.g., 10.0). Determines how much historical data "
            "is retained before new samples overwrite old."
        ),
        examples=[10.0, 30.0],
    )
    warning_enabled: bool = Field(
        default=False,
        description="Set to True to enable overflow warning. Defaults to False.",
        examples=[False, True],
    )
    warning_time_seconds: float = Field(
        default=3.0,
        description=(
            "If warning_enabled is True, alert when buffer has less than this many seconds "
            "remaining. Defaults to 3.0."
        ),
        examples=[3.0, 5.0],
    )


class MeasurementGetConfigurationInput(BaseModel):
    """Input for measurement_get_configuration (no parameters required)."""


class MeasurementStartInput(BaseModel):
    """Input for measurement_start (no parameters required)."""


class MeasurementStopInput(BaseModel):
    """Input for measurement_stop (no parameters required)."""


class MeasurementGetStateInput(BaseModel):
    """Input for measurement_get_state (no parameters required)."""


class TriggerRuleCreateInput(BaseModel):
    """Input for trigger_rule_create."""

    rule_name: str = Field(
        description=(
            "Unique name for the trigger rule (e.g., 'StartCondition', 'HighThrottleEvent')."
        ),
        examples=["StartCondition", "HighThrottleEvent"],
    )
    expression: str = Field(
        description=(
            "Logical expression evaluated against signal aliases "
            "(e.g., 'control_out < -0.1', 'rpm > 3000 AND throttle > 50')."
        ),
        examples=["control_out < -0.1", "rpm > 3000 AND throttle > 50"],
    )
    signal_mappings: dict[str, str] = Field(
        description=(
            "Mapping of alias names to connection paths "
            "(e.g., {'control_out': 'XCP(5ms)://control_out'}). "
            "Each key is the alias used in the expression; value is the connection path."
        ),
        examples=[{"control_out": "XCP(5ms)://control_out"}],
    )


class TriggerRuleRemoveInput(BaseModel):
    """Input for trigger_rule_remove."""

    rule_name: str = Field(
        description="Name of the trigger rule to remove (e.g., 'StartCondition').",
        examples=["StartCondition"],
    )


class TriggerConditionTimeLimitInput(BaseModel):
    """Input for trigger_condition_time_limit."""

    enabled: bool = Field(
        description="Set to True to enable time-limit stop condition; False to disable.",
        examples=[True, False],
    )
    time_limit_seconds: float = Field(
        description=(
            "Duration in seconds after which to stop recording (e.g., 10.0). "
            "Ignored if enabled is False."
        ),
        examples=[10.0, 30.0],
    )


class TriggerConditionTriggerBasedInput(BaseModel):
    """Input for trigger_condition_trigger_based."""

    condition_type: ConditionType = Field(
        description=(
            "Whether to configure the start condition (recorder waits for trigger before "
            "recording begins) or stop condition (recording stops when triggered)."
        ),
        examples=["start", "stop"],
    )
    rule_name: str = Field(
        description="Name of the trigger rule to attach (created via trigger_rule_create).",
        examples=["StartCondition"],
    )
    enabled: bool = Field(
        default=True,
        description="Set to False to disable the condition without detaching. Defaults to True.",
        examples=[True, False],
    )
    trigger_delay_seconds: float = Field(
        default=0.0,
        description=(
            "Pre-trigger delay (start condition only): capture this many seconds of data BEFORE "
            "the trigger fires. Defaults to 0.0."
        ),
        examples=[0.0, 0.2, 0.5],
    )
    recording_cycles: int = Field(
        default=1,
        description=(
            "Number of times the trigger should fire before stop condition takes effect "
            "(start condition only). Defaults to 1."
        ),
        examples=[1, 3],
    )


class MeasurementListRecordingsInput(BaseModel):
    """Input for measurement_list_recordings."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class MeasurementExportRecordingInput(BaseModel):
    """Input for measurement_export_recording."""

    recording_index: int = Field(
        description=(
            "Zero-based index of the recording in the data pool "
            "(e.g., 0 for the first recording)."
        ),
        examples=[0, 1],
    )
    export_path: str = Field(
        description=(
            "Full file system path where the MF4 file will be written "
            "(e.g., 'C:\\\\exports\\\\my_recording.mf4')."
        ),
        examples=["C:\\exports\\my_recording.mf4"],
    )
    overwrite_existing: bool = Field(
        default=True,
        description="If True, overwrite existing output file. Defaults to True.",
        examples=[True, False],
    )

    @field_validator("export_path")
    @classmethod
    def _validate_export_path(cls, v: str) -> str:
        return _validate_abs_path("export_path", v)


class MeasurementImportRecordingInput(BaseModel):
    """Input for measurement_import_recording."""

    import_path: str = Field(
        description=(
            "Full file system path to the MF4 file to import "
            "(e.g., 'C:\\\\archives\\\\old_recording.mf4')."
        ),
        examples=["C:\\archives\\old_recording.mf4"],
    )

    @field_validator("import_path")
    @classmethod
    def _validate_import_path(cls, v: str) -> str:
        return _validate_abs_path("import_path", v)


class MeasurementBookmarkAddInput(BaseModel):
    """Input for measurement_bookmark_add."""

    title: str = Field(
        description=(
            "Short title for the bookmark (e.g., 'Throttle spike', 'System error detected')."
        ),
        examples=["Throttle spike", "System error detected"],
    )
    description: str = Field(
        default="",
        description="Optional longer description or notes.",
        examples=["Throttle suddenly increased to max during transient test", ""],
    )


class MeasurementBookmarkListInput(BaseModel):
    """Input for measurement_bookmark_list."""

    recording_index: int = Field(
        description=(
            "Zero-based index of the recording in the data pool "
            "(e.g., 0 for the first recording)."
        ),
        examples=[0, 1],
    )
    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class DataLoggerCreateInput(BaseModel):
    """Input for data_logger_create."""

    logger_name: str = Field(
        description="Unique name for the data logger (e.g., 'CAN_Logger', 'HighRateLogger').",
        examples=["CAN_Logger", "HighRateLogger"],
    )


class DataLoggerConfigureInput(BaseModel):
    """Input for data_logger_configure."""

    logger_name: str = Field(
        description="Name of the data logger to configure (e.g., 'CAN_Logger').",
        examples=["CAN_Logger"],
    )
    output_file_path: str = Field(
        description=(
            "Absolute file path for the output MF4 file "
            "(e.g., 'C:\\\\Logs\\\\can_log.mf4'). Directory must exist."
        ),
        examples=["C:\\Logs\\can_log.mf4"],
    )
    file_format: DataLoggerFileFormat = Field(
        default=DataLoggerFileFormat.MF4,
        description="File format: 'MF4' (default), 'ASC', 'CSV'.",
        examples=["MF4", "ASC", "CSV"],
    )
    overwrite_existing: bool = Field(
        default=True,
        description="If True, overwrite existing output file. Defaults to True.",
        examples=[True, False],
    )


class DataLoggerStartInput(BaseModel):
    """Input for data_logger_start."""

    logger_name: str = Field(
        description="Name of the data logger to start (e.g., 'CAN_Logger').",
        examples=["CAN_Logger"],
    )


class DataLoggerStopInput(BaseModel):
    """Input for data_logger_stop."""

    logger_name: str = Field(
        description="Name of the data logger to stop (e.g., 'CAN_Logger').",
        examples=["CAN_Logger"],
    )


class DataLoggerListInput(BaseModel):
    """Input for data_logger_list."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class DataLoggerRemoveInput(BaseModel):
    """Input for data_logger_remove."""

    logger_name: str = Field(
        description="Name of the data logger to remove (e.g., 'CAN_Logger').",
        examples=["CAN_Logger"],
    )


class MeasurementRasterAddInput(BaseModel):
    """Input for measurement_raster_add."""

    platform_name: str = Field(
        description="Name of the platform to add the raster to (e.g., 'XCP').",
        examples=["XCP"],
    )
    raster_interval_ms: float = Field(
        description=(
            "Sampling interval in milliseconds (e.g., 1.0 for 1ms, 5.0 for 5ms, 10.0 for 10ms)."
        ),
        examples=[1.0, 5.0, 10.0],
    )


class MeasurementRasterListInput(BaseModel):
    """Input for measurement_raster_list."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class MeasurementRasterRemoveInput(BaseModel):
    """Input for measurement_raster_remove."""

    platform_name: str = Field(
        description="Name of the platform (e.g., 'XCP').",
        examples=["XCP"],
    )
    raster_name: str = Field(
        description="Name of the raster to remove (e.g., 'XCP_1ms').",
        examples=["XCP_1ms", "XCP_5ms"],
    )


class MeasurementConfigureSettingsInput(BaseModel):
    """Input for measurement_configure_settings."""

    data_pool_path: Optional[str] = Field(
        default=None,
        description=(
            "Absolute directory path for the measurement data pool "
            "(e.g., 'C:\\\\MeasurementData'). Directory must exist."
        ),
        examples=["C:\\MeasurementData", None],
    )
    auto_save_enabled: Optional[bool] = Field(
        default=None,
        description="If True, recordings are automatically saved when measurement stops.",
        examples=[True, False, None],
    )
    auto_save_format: Optional[AutoSaveFormat] = Field(
        default=None,
        description="Format for auto-saved recordings: 'MF4' (default), 'ASC'.",
        examples=["MF4", "ASC", None],
    )


class MeasurementBookmarkRemoveInput(BaseModel):
    """Input for measurement_bookmark_remove."""

    recording_index: int = Field(
        description="Zero-based index of the recording in the data pool.",
        examples=[0, 1],
    )
    bookmark_index: int = Field(
        description="Zero-based index of the bookmark within the recording's bookmark list.",
        examples=[0, 1],
    )


# ── Result models (Category B — COM bridge returns raw dicts) ─────────────────


class MeasurementSignalAddResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    added: bool
    connection_path: str
    variable_name: str
    platform_name: str
    raster_name: str
    is_connected: bool
    active: bool
    recording_enabled: bool
    timestamp_utc: str


class MeasurementSignalRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    connection_path: str
    timestamp_utc: str


class MeasurementListSignalsResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_count: int
    signals: list[dict] = []


class MeasurementConfigureBufferResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    buffer_size_seconds: float
    warning_enabled: bool
    warning_time_seconds: float
    timestamp_utc: str


class MeasurementGetConfigurationResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    buffer: dict = {}
    signal_count: int
    signals: list[dict] = []
    platforms_connected: list[str] = []
    timestamp_utc: str


class MeasurementStartResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    started: bool
    platforms_measuring: list[str] = []
    timestamp_utc: str


class MeasurementStopResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    stopped: bool
    timestamp_utc: str


class MeasurementGetStateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    state: str
    is_measuring: bool
    timestamp_utc: str


class TriggerRuleCreateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    created: bool
    rule_name: str
    expression: str
    mappings: dict = {}
    enabled: bool
    timestamp_utc: str


class TriggerRuleRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    rule_name: str
    timestamp_utc: str


class TriggerConditionTimeLimitResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    condition_type: str
    enabled: bool
    time_limit_seconds: float
    timestamp_utc: str


class TriggerConditionTriggerBasedResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    condition_type: str
    rule_name: str
    enabled: bool
    trigger_delay_seconds: float
    recording_cycles: int
    timestamp_utc: str


class MeasurementListRecordingsResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_count: int
    recordings: list[dict] = []


class MeasurementExportRecordingResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    exported: bool
    export_path: str
    file_size_bytes: int
    timestamp_utc: str


class MeasurementImportRecordingResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    imported: bool
    import_path: str
    new_recording_index: int
    filename: str
    timestamp_utc: str


class MeasurementBookmarkAddResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    added: bool
    title: str
    description: str
    timestamp_utc: str
    bookmark_timestamp: str


class MeasurementBookmarkListResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    recording_index: int
    total_bookmarks: int
    bookmarks: list[dict] = []


class DataLoggerCreateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    created: bool
    logger_name: str
    timestamp_utc: str


class DataLoggerConfigureResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    logger_name: str
    output_file_path: str
    file_format: str
    overwrite_existing: bool


class DataLoggerStartResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    started: bool
    logger_name: str
    timestamp_utc: str


class DataLoggerStopResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    stopped: bool
    logger_name: str
    timestamp_utc: str


class DataLoggerListResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_loggers: int
    loggers: list[dict] = []


class DataLoggerRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    logger_name: str
    timestamp_utc: str


class MeasurementRasterAddResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    added: bool
    platform_name: str
    raster_name: str
    raster_interval_ms: float
    timestamp_utc: str


class MeasurementRasterListResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_rasters: int
    rasters: list = []


class MeasurementRasterRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    platform_name: str
    raster_name: str
    timestamp_utc: str


class MeasurementConfigureSettingsResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    data_pool_path: str
    auto_save_enabled: bool
    auto_save_format: str
    timestamp_utc: str


class MeasurementBookmarkRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    recording_index: int
    bookmark_index: int
    timestamp_utc: str


# ── Consolidated manage input models ─────────────────────────────────────────


class MeasurementQueryInput(BaseModel):
    """Input for measurement_query (read-only actions)."""

    action: MeasurementQueryAction = Field(
        description=("Read-only action to perform: get_state, get_configuration, or list_signals."),
        examples=["get_state", "get_configuration", "list_signals"],
    )
    limit: int = Field(
        default=200, ge=1, le=1000, description="Pagination limit (for list_signals)."
    )
    offset: int = Field(default=0, ge=0, description="Pagination offset (for list_signals).")


class MeasurementManageInput(BaseModel):
    """Input for measurement_manage consolidated tool (mutating actions only)."""

    action: MeasurementManageAction = Field(
        description=(
            "Mutating action to perform: configure_buffer, "
            "configure_settings, signal_add, or signal_remove."
        ),
        examples=["configure_buffer", "signal_add"],
    )
    connection_path: Optional[str] = Field(
        default=None,
        description="Signal connection path (for signal_add and signal_remove).",
        examples=["XCP(5ms)://control_out"],
    )
    buffer_size_seconds: Optional[float] = Field(
        default=None,
        description="Ring buffer size in seconds (for configure_buffer).",
        examples=[10.0, 30.0],
    )
    warning_enabled: bool = Field(
        default=False,
        description="Enable overflow warning (for configure_buffer).",
    )
    warning_time_seconds: float = Field(
        default=3.0,
        description="Warning threshold in seconds (for configure_buffer).",
    )
    data_pool_path: Optional[str] = Field(
        default=None,
        description="Absolute data pool directory path (for configure_settings).",
        examples=["C:\\MeasurementData"],
    )
    auto_save_enabled: Optional[bool] = Field(
        default=None,
        description="Enable auto-save on measurement stop (for configure_settings).",
    )
    auto_save_format: Optional[AutoSaveFormat] = Field(
        default=None,
        description="Auto-save file format (for configure_settings).",
        examples=["MF4", "ASC"],
    )
    limit: int = Field(default=200, ge=1, le=1000, description="Pagination limit.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


class MeasurementRasterManageInput(BaseModel):
    """Input for measurement_raster_manage consolidated tool."""

    action: MeasurementRasterManageAction = Field(
        description="Action to perform: raster_add, raster_list, or raster_remove.",
        examples=["raster_add", "raster_list"],
    )
    platform_name: Optional[str] = Field(
        default=None,
        description="Platform name (for raster_add and raster_remove).",
        examples=["XCP"],
    )
    raster_interval_ms: Optional[float] = Field(
        default=None,
        description="Sampling interval in ms (for raster_add).",
        examples=[1.0, 5.0, 10.0],
    )
    raster_name: Optional[str] = Field(
        default=None,
        description="Raster name to remove (for raster_remove).",
        examples=["XCP_1ms", "XCP_5ms"],
    )
    limit: int = Field(default=200, ge=1, le=1000, description="Pagination limit.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


class TriggerManageInput(BaseModel):
    """Input for trigger_manage consolidated tool."""

    action: TriggerManageAction = Field(
        description=(
            "Action to perform: rule_create, rule_remove, "
            "condition_time_limit, or condition_trigger_based."
        ),
        examples=["rule_create", "condition_time_limit"],
    )
    rule_name: Optional[str] = Field(
        default=None,
        description="Trigger rule name (for rule_create and rule_remove).",
        examples=["StartCondition"],
    )
    expression: Optional[str] = Field(
        default=None,
        description="Logical expression (for rule_create).",
        examples=["control_out < -0.1"],
    )
    signal_mappings: Optional[dict[str, str]] = Field(
        default=None,
        description="Alias-to-connection-path mappings (for rule_create).",
        examples=[{"control_out": "XCP(5ms)://control_out"}],
    )
    enabled: Optional[bool] = Field(
        default=None,
        description="Enable flag (for condition_time_limit and condition_trigger_based).",
        examples=[True, False],
    )
    time_limit_seconds: Optional[float] = Field(
        default=None,
        description="Duration in seconds (for condition_time_limit).",
        examples=[10.0, 30.0],
    )
    condition_type: Optional[ConditionType] = Field(
        default=None,
        description="Start or stop condition (for condition_trigger_based).",
        examples=["start", "stop"],
    )
    trigger_delay_seconds: float = Field(
        default=0.0,
        description="Pre-trigger delay in seconds (for condition_trigger_based).",
        examples=[0.0, 0.2],
    )
    recording_cycles: int = Field(
        default=1,
        description="Number of trigger cycles before stop (for condition_trigger_based).",
        examples=[1, 3],
    )


class RecordingManageInput(BaseModel):
    """Input for recording_manage consolidated tool."""

    action: RecordingManageAction = Field(
        description=(
            "Action to perform: list_recordings, export_recording, import_recording, "
            "bookmark_add, bookmark_list, or bookmark_remove."
        ),
        examples=["list_recordings", "bookmark_add"],
    )
    recording_index: Optional[int] = Field(
        default=None,
        description="Recording index in data pool (for export_recording, bookmark_list, bookmark_remove).",
        examples=[0, 1],
    )
    export_path: Optional[str] = Field(
        default=None,
        description="Absolute path for exported MF4 (for export_recording).",
        examples=["C:\\exports\\my.mf4"],
    )
    import_path: Optional[str] = Field(
        default=None,
        description="Absolute path to import MF4 (for import_recording).",
        examples=["C:\\archives\\old.mf4"],
    )
    overwrite_existing: bool = Field(
        default=True,
        description="Overwrite existing file (for export_recording).",
    )
    title: Optional[str] = Field(
        default=None,
        description="Bookmark title (for bookmark_add).",
        examples=["Throttle spike"],
    )
    description: str = Field(
        default="",
        description="Bookmark description (for bookmark_add).",
    )
    bookmark_index: Optional[int] = Field(
        default=None,
        description="Bookmark index (for bookmark_remove).",
        examples=[0, 1],
    )
    limit: int = Field(default=200, ge=1, le=1000, description="Pagination limit.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


class DataLoggerManageInput(BaseModel):
    """Input for data_logger_manage consolidated tool."""

    action: DataLoggerManageAction = Field(
        description="Action to perform: create, configure, start, stop, list, or remove.",
        examples=["create", "start"],
    )
    logger_name: Optional[str] = Field(
        default=None,
        description="Data logger name (required for all except list).",
        examples=["CAN_Logger", "HighRateLogger"],
    )
    output_file_path: Optional[str] = Field(
        default=None,
        description="Absolute output file path (for configure).",
        examples=["C:\\Logs\\can_log.mf4"],
    )
    file_format: DataLoggerFileFormat = Field(
        default=DataLoggerFileFormat.MF4,
        description="Output file format (for configure).",
        examples=["MF4", "ASC", "CSV"],
    )
    overwrite_existing: bool = Field(
        default=True,
        description="Overwrite existing output file (for configure).",
    )
    limit: int = Field(default=200, ge=1, le=1000, description="Pagination limit.")
    offset: int = Field(default=0, ge=0, description="Pagination offset.")


# ── Discover result models ────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the measurement domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class MeasurementDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from measurement_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
