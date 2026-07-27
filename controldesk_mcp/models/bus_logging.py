"""Pydantic input and response models for the bus logging domain.

Domain: ControlDesk Bus Logging (CAN/LIN/FlexRay/Ethernet frame recording).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from controldesk_mcp.models.base import DictModelMixin

# ── Enums ───────────────────────────────────────────────────────────────────────


class BusType(str, Enum):
    """Supported bus protocol types."""

    CAN = "CAN"
    LIN = "LIN"
    FlexRay = "FlexRay"
    Ethernet = "Ethernet"


class TimeAxis(str, Enum):
    """Time axis type for ASC log files."""

    Absolute = "Absolute"
    Relative = "Relative"


class FileRollingType(str, Enum):
    """File rolling trigger type."""

    Time = "Time"
    Size = "Size"


# ── Logger input models ─────────────────────────────────────────────────────────


class BusLoggerCreateInput(BaseModel):
    """Input for bus_logger_create."""

    logger_name: str = Field(
        description="Unique name for the logger (e.g. 'CANRecorder', 'RxLogger').",
        examples=["CANRecorder", "RxLogger"],
    )
    system_index: int = Field(
        description=("Zero-based index of the target system (e.g. 0 for transceiver, 1 for receiver)."),
        examples=[0, 1],
    )
    bus_type: BusType = Field(
        description="Bus protocol type: CAN, LIN, FlexRay, or Ethernet.",
        examples=["CAN"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Zero-based index of the bus platform on the system (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Zero-based index of the physical bus access channel (e.g. 0).",
        examples=[0],
    )
    dry_run: bool = Field(
        default=False,
        description=(
            "When True, checks whether a logger with this name already exists on the "
            "target physical bus access and returns a preview without creating anything. "
            "Use this to preview a create before committing it."
        ),
    )


class BusLoggerConfigureInput(BaseModel):
    """Input for bus_logger_configure."""

    logger_name: str = Field(
        description="Name of the logger to configure (as created via bus_logger_create).",
        examples=["CANRecorder"],
    )
    system_index: int = Field(
        description="System index (must match the system where the logger was created).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (must match the bus type where the logger was created).",
        examples=["CAN"],
    )
    log_file_full_path: str = Field(
        description=("Absolute file system path for the output log file (e.g. 'C:\\\\Logs\\\\can_recording.asc')."),
        examples=["C:\\Logs\\can_recording.asc"],
    )
    overwrite_existing: bool = Field(
        default=True,
        description="Set to False to append to existing file (e.g. True).",
        examples=[True, False],
    )
    max_duration_seconds: float = Field(
        default=0.0,
        description="Max logging duration in seconds; 0 = unlimited (e.g. 30.0).",
        examples=[0.0, 30.0],
    )
    enable_bus_statistics: bool = Field(
        default=False,
        description="Include bus statistics frames in the log (e.g. False).",
        examples=[False, True],
    )
    continuous_ring_mode: bool = Field(
        default=False,
        description="Enable continuous ring logging; wraps when limit reached (e.g. False).",
        examples=[False, True],
    )
    file_rolling_enabled: bool = Field(
        default=False,
        description="Enable automatic file rolling (e.g. False).",
        examples=[False, True],
    )
    file_rolling_type: FileRollingType = Field(
        default=FileRollingType.Time,
        description="Roll by elapsed time or file size (e.g. 'Time').",
        examples=["Time", "Size"],
    )
    file_rolling_interval_seconds: float = Field(
        default=3600.0,
        description=("Time interval for rolling in seconds if file_rolling_type is Time (e.g. 3600.0)."),
        examples=[3600.0],
    )
    time_axis_mode: TimeAxis = Field(
        default=TimeAxis.Relative,
        description=("Time axis for ASC format: Absolute or Relative. Ignored for BLF (e.g. 'Relative')."),
        examples=["Relative", "Absolute"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index (e.g. 0).",
        examples=[0],
    )


class BusLoggerStartInput(BaseModel):
    """Input for bus_logger_start."""

    logger_name: str = Field(
        description="Name of the logger to start (e.g. 'CANRecorder').",
        examples=["CANRecorder"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )


class BusLoggerStopInput(BaseModel):
    """Input for bus_logger_stop."""

    logger_name: str = Field(
        description="Name of the logger to stop (e.g. 'CANRecorder').",
        examples=["CANRecorder"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )


class BusLoggerGetStateInput(BaseModel):
    """Input for bus_logger_get_state."""

    logger_name: str = Field(
        description="Name of the logger (e.g. 'CANRecorder').",
        examples=["CANRecorder"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )


class BusLoggerListInput(BaseModel):
    """Input for bus_logger_list."""

    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type to filter results (e.g. 'CAN').",
        examples=["CAN"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index (e.g. 0).",
        examples=[0],
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


class BusLoggerRemoveInput(BaseModel):
    """Input for bus_logger_remove."""

    logger_name: str = Field(
        description="Name of the logger to remove (e.g. 'CANRecorder').",
        examples=["CANRecorder"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )


class BusLoggerClearAllInput(BaseModel):
    """Input for bus_logger_clear_all."""

    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index (e.g. 0).",
        examples=[0],
    )
    confirm: bool = Field(
        default=False,
        description=("Must be True to proceed; safety guard against accidental invocation (e.g. True)."),
        examples=[True, False],
    )


class BusLoggerSetActivatedInput(BaseModel):
    """Input for bus_logger_set_activated."""

    logger_name: str = Field(
        description="Name of the logger to activate or deactivate (e.g. 'CANRecorder').",
        examples=["CANRecorder"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    activated: bool = Field(
        description="True to activate; False to deactivate (e.g. True).",
        examples=[True, False],
    )


# ── Filter input models ─────────────────────────────────────────────────────────


class BusFilterCreateInput(BaseModel):
    """Input for bus_filter_create."""

    filter_name: str = Field(
        description="Unique name for the filter (e.g. 'CANFilter', 'EngineFrames').",
        examples=["CANFilter", "EngineFrames"],
    )
    system_index: int = Field(
        description="Zero-based index of the target system (e.g. 0 or 1).",
        examples=[0, 1],
    )
    bus_type: BusType = Field(
        description="Bus protocol type: CAN, LIN, FlexRay, or Ethernet.",
        examples=["CAN"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index (e.g. 0).",
        examples=[0],
    )


class BusFilterConfigureInput(BaseModel):
    """Input for bus_filter_configure."""

    filter_name: str = Field(
        description="Name of the filter to configure (e.g. 'CANFilter').",
        examples=["CANFilter"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    filter_mode: str = Field(
        default="Pass",
        description=("Filter mode: 'Pass' (only matching pass) or 'Block' (matching blocked) (e.g. 'Pass')."),
        examples=["Pass", "Block"],
    )
    message_id: int = Field(
        default=0,
        description="Message ID to match; 0 matches all (e.g. 256).",
        examples=[0, 256],
    )
    message_mask: int = Field(
        default=0x7FF,
        description="Acceptance mask; 0x7FF for exact match, 0x000 for all (e.g. 2047).",
        examples=[2047, 0],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index (e.g. 0).",
        examples=[0],
    )


class BusFilterStartInput(BaseModel):
    """Input for bus_filter_start."""

    filter_name: str = Field(
        description="Name of the filter to start (e.g. 'CANFilter').",
        examples=["CANFilter"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )


class BusFilterStopInput(BaseModel):
    """Input for bus_filter_stop."""

    filter_name: str = Field(
        description="Name of the filter to stop (e.g. 'CANFilter').",
        examples=["CANFilter"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )


class BusFilterListInput(BaseModel):
    """Input for bus_filter_list."""

    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index (e.g. 0).",
        examples=[0],
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


class BusFilterRemoveInput(BaseModel):
    """Input for bus_filter_remove."""

    filter_name: str = Field(
        description="Name of the filter to remove (e.g. 'CANFilter').",
        examples=["CANFilter"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )


class BusLoggerRenameInput(BaseModel):
    """Input for bus_logger_rename."""

    logger_name: str = Field(
        description="Current name of the logger to rename.",
        examples=["CAN Logger"],
    )
    new_name: str = Field(
        description="New name for the logger. Must be unique within the physical bus access.",
        examples=["TxLogger"],
    )
    system_index: int = Field(
        description="Zero-based index of the target system.",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus protocol type: CAN, LIN, FlexRay, or Ethernet.",
        examples=["CAN"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Zero-based index of the bus platform on the system.",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Zero-based index of the physical bus access channel.",
        examples=[0],
    )


class BusLoggerRenameResult(DictModelMixin, BaseModel):
    """Successful response from bus_logger_rename."""

    renamed: Literal[True] = True
    old_name: str
    new_name: str
    timestamp_utc: str


# ── Consolidated logger manage input ────────────────────────────────────────────


class BusLoggerQueryAction(str, Enum):
    """Actions for bus_logger_query read-only tool."""

    get_state = "get_state"
    list = "list"


class BusLoggerManageAction(str, Enum):
    """Action for the consolidated bus_logger_manage tool (mutating only)."""

    start = "start"
    stop = "stop"


class BusLoggerQueryInput(BaseModel):
    """Input for bus_logger_query (read-only actions)."""

    action: BusLoggerQueryAction = Field(
        description=(
            "Read-only action to perform on a bus logger. "
            "'get_state' — query current state and activation status (requires logger_name); "
            "'list' — enumerate all loggers on a physical bus access."
        ),
        examples=["get_state", "list"],
    )
    system_index: int = Field(description="System index (e.g. 1).", examples=[1])
    bus_type: BusType = Field(description="Bus type (e.g. 'CAN').", examples=["CAN"])
    logger_name: Optional[str] = Field(
        default=None,
        description="Name of the logger. Required for: get_state.",
        examples=["CANRecorder"],
    )
    bus_platform_index: int = Field(default=0, description="Bus platform index.", examples=[0])
    physical_bus_access_index: int = Field(default=0, description="Physical bus access index.", examples=[0])
    limit: int = Field(default=200, ge=1, le=1000, description="Maximum records for 'list'.")
    offset: int = Field(default=0, ge=0, description="Zero-based offset for 'list' pagination.")


class BusLoggerManageInput(BaseModel):
    """Input for bus_logger_manage (mutating actions only: start, stop)."""

    action: BusLoggerManageAction = Field(
        description=(
            "Mutating action to perform on a bus logger. "
            "'start' — activate and start logging (requires logger_name); "
            "'stop' — stop logging and deactivate (requires logger_name)."
        ),
        examples=["start", "stop"],
    )
    system_index: int = Field(description="System index (e.g. 1).", examples=[1])
    bus_type: BusType = Field(description="Bus type (e.g. 'CAN').", examples=["CAN"])
    logger_name: Optional[str] = Field(
        default=None,
        description="Name of the logger. Required for: start, stop.",
        examples=["CANRecorder"],
    )
    bus_platform_index: int = Field(default=0, description="Bus platform index.", examples=[0])
    physical_bus_access_index: int = Field(default=0, description="Physical bus access index.", examples=[0])


class BusLoggerAdminManageAction(str, Enum):
    """Action for the consolidated bus_logger_admin_manage tool."""

    remove = "remove"
    clear_all = "clear_all"
    set_activated = "set_activated"
    rename = "rename"


class BusLoggerAdminManageInput(BaseModel):
    """Input for bus_logger_admin_manage."""

    action: BusLoggerAdminManageAction = Field(
        description=(
            "Admin action to perform on a bus logger. "
            "'remove' — remove a specific logger (requires logger_name); "
            "'clear_all' — remove all loggers from a physical bus access (requires confirm=True); "
            "'set_activated' — set or clear the Activated flag (requires logger_name and activated); "
            "'rename' — rename an existing logger (requires logger_name and new_name)."
        ),
        examples=["remove", "clear_all", "set_activated", "rename"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    logger_name: Optional[str] = Field(
        default=None,
        description=("Name of the logger. Required for: remove, set_activated, rename. Not required for: clear_all."),
        examples=["CANRecorder"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index (e.g. 0).",
        examples=[0],
    )
    activated: Optional[bool] = Field(
        default=None,
        description="Required for action='set_activated'. True to activate; False to deactivate.",
        examples=[True, False],
    )
    new_name: Optional[str] = Field(
        default=None,
        description="Required for action='rename'. New unique name for the logger.",
        examples=["TxLogger"],
    )
    confirm: bool = Field(
        default=False,
        description="Required for action='clear_all'. Must be True to proceed.",
        examples=[True, False],
    )


class BusFilterManageAction(str, Enum):
    """Action for the consolidated bus_filter_manage tool."""

    start = "start"
    stop = "stop"
    list = "list"
    remove = "remove"


class BusFilterManageInput(BaseModel):
    """Input for bus_filter_manage."""

    action: BusFilterManageAction = Field(
        description=(
            "Action to perform on a bus filter. "
            "'start' — activate and start filtering (requires filter_name); "
            "'stop' — stop filtering and deactivate (requires filter_name); "
            "'list' — enumerate all filters on a physical bus access; "
            "'remove' — remove a specific filter (requires filter_name)."
        ),
        examples=["start", "stop", "list", "remove"],
    )
    system_index: int = Field(
        description="System index (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    filter_name: Optional[str] = Field(
        default=None,
        description=("Name of the filter. Required for: start, stop, remove. Not required for: list."),
        examples=["CANFilter"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index (e.g. 0).",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index (e.g. 0).",
        examples=[0],
    )
    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call (used for action='list').",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination (used for action='list').",
    )


# ── Result models (Category B — COM bridge returns raw dicts) ─────────────────


class BusLoggerCreateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    created: bool
    logger_name: str
    system_index: int
    bus_type: str
    state: str
    activated: bool
    timestamp_utc: str


class BusLoggerConfigureResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    logger_name: str
    log_file_full_path: str
    overwrite_existing: bool
    max_duration_seconds: float
    enable_bus_statistics: bool
    continuous_ring_mode: bool
    file_rolling_enabled: bool
    time_axis_mode: str
    timestamp_utc: str


class BusLoggerStartResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    started: bool
    logger_name: str
    state: str
    activated: bool
    timestamp_utc: str


class BusLoggerStopResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    stopped: bool
    logger_name: str
    state: str
    activated: bool
    timestamp_utc: str


class BusLoggerGetStateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    logger_name: str
    state: str
    is_running: bool
    activated: bool
    log_file_path: str
    timestamp_utc: str


class BusLoggerListResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    system_index: int
    bus_type: str
    total_count: int
    loggers: list[dict] = []


class BusLoggerRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    logger_name: str
    timestamp_utc: str


class BusLoggerClearAllResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    cleared: bool
    loggers_removed: int
    system_index: int
    bus_type: str
    timestamp_utc: str


class BusLoggerClearAllAborted(DictModelMixin, BaseModel):
    cleared: Literal[False] = False
    message: str = "Operation aborted. Set 'confirm' to true to proceed with clearing all loggers."


class BusLoggerSetActivatedResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    activated: bool
    logger_name: str
    state: str
    previous_activated: bool
    timestamp_utc: str


class BusFilterCreateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    created: bool
    filter_name: str
    system_index: int
    bus_type: str
    state: str
    activated: bool
    timestamp_utc: str


class BusFilterConfigureResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    filter_name: str
    loggers_count: int
    monitors_count: int
    replays_count: int
    note: str
    timestamp_utc: str


class BusFilterStartResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    started: bool
    filter_name: str
    started_loggers: list[str] = []
    started_replays: list[str] = []
    timestamp_utc: str


class BusFilterStopResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    stopped: bool
    filter_name: str
    timestamp_utc: str


class BusFilterListResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_count: int
    filters: list[dict] = []


class BusFilterRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    filter_name: str
    timestamp_utc: str


# ── Discover result models ────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the bus logging domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class BusLoggingDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from bus_logging_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
