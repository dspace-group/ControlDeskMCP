"""Pydantic input and response models for the bus monitor domain.

Domain: ControlDesk bus monitoring (bus_monitor_create, bus_monitor_configure, etc.).

Convention: one models module per domain under controldesk_mcp/models/<domain>.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from controldesk_mcp.models.base import DictModelMixin

# ── Enums ─────────────────────────────────────────────────────────────────────


class BusType(str, Enum):
    """Supported bus protocol types for bus monitoring."""

    CAN = "CAN"
    LIN = "LIN"
    FlexRay = "FlexRay"
    Ethernet = "Ethernet"


class RunState(str, Enum):
    """Bus monitor run states."""

    Running = "Running"
    Stopped = "Stopped"


class BufferMode(str, Enum):
    """Buffer behavior when the monitor buffer is full."""

    FixedBuffer = "FixedBuffer"
    RingBuffer = "RingBuffer"


class TimeAxis(str, Enum):
    """Time axis modes for saving monitor data."""

    Absolute = "Absolute"
    Relative = "Relative"
    RecordingTime = "RecordingTime"


# ── Input models ──────────────────────────────────────────────────────────────


class BusMonitorCreateInput(BaseModel):
    """Input for bus_monitor_create."""

    monitor_name: str = Field(
        description=(
            "Unique name for the monitor (e.g. 'CANMonitor', 'RxDisplay'). "
            "Must not duplicate existing monitor names on this physical bus access."
        ),
        examples=["CANMonitor", "RxDisplay"],
    )
    system_index: int = Field(
        description=(
            "Zero-based index of the target system (e.g. 0 = transceiver/sender, 1 = receiver)."
        ),
        examples=[0, 1],
    )
    bus_type: BusType = Field(
        description="Bus protocol type: CAN, LIN, FlexRay, or Ethernet.",
        examples=["CAN", "LIN"],
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
            "When True, checks whether a monitor with this name already exists on the "
            "target physical bus access and returns a preview without creating anything. "
            "Use this to preview a create before committing it."
        ),
    )


class BusMonitorConfigureInput(BaseModel):
    """Input for bus_monitor_configure."""

    monitor_name: str = Field(
        description="Name of the monitor to configure (as created via bus_monitor_create).",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="System index (must match the system where the monitor was created).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (must match the bus type where the monitor was created).",
        examples=["CAN"],
    )
    update_rate_ms: int = Field(
        default=100,
        description=(
            "UI refresh rate in milliseconds (e.g. 100 = refresh every 100ms). "
            "Valid range: 10–5000 ms."
        ),
        examples=[100, 50],
    )
    buffer_size_frames: int = Field(
        default=10000,
        description=(
            "Maximum number of frames to buffer in memory (e.g. 10000). "
            "Larger values use more memory but allow longer capture history."
        ),
        examples=[10000, 20000],
    )
    buffer_mode: BufferMode = Field(
        default=BufferMode.RingBuffer,
        description=(
            "Behavior when buffer is full: 'FixedBuffer' (stop capturing) "
            "or 'RingBuffer' (overwrite oldest frames)."
        ),
        examples=["RingBuffer", "FixedBuffer"],
    )
    enable_j1939_pgn_resolving: bool = Field(
        default=False,
        description=(
            "Enable J1939 parameter group name resolving for CAN frames. Ignored for non-CAN buses."
        ),
        examples=[False, True],
    )


class BusMonitorStartInput(BaseModel):
    """Input for bus_monitor_start."""

    monitor_name: str = Field(
        description="Name of the monitor to start.",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="System index (must match the system where the monitor exists).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (must match the bus type where the monitor exists).",
        examples=["CAN"],
    )


class BusMonitorStopInput(BaseModel):
    """Input for bus_monitor_stop."""

    monitor_name: str = Field(
        description="Name of the monitor to stop.",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="System index.",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type.",
        examples=["CAN"],
    )


class BusMonitorGetStateInput(BaseModel):
    """Input for bus_monitor_get_state."""

    monitor_name: str = Field(
        description="Name of the monitor.",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="System index.",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type.",
        examples=["CAN"],
    )


class BusMonitorListInput(BaseModel):
    """Input for bus_monitor_list."""

    system_index: int = Field(
        description="System index.",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (filters results to only this bus type).",
        examples=["CAN"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index.",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index.",
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


class BusMonitorRemoveInput(BaseModel):
    """Input for bus_monitor_remove."""

    monitor_name: str = Field(
        description="Name of the monitor to remove.",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="System index.",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type.",
        examples=["CAN"],
    )


class BusMonitorClearAllInput(BaseModel):
    """Input for bus_monitor_clear_all."""

    system_index: int = Field(
        description="System index.",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type.",
        examples=["CAN"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index.",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index.",
        examples=[0],
    )
    confirm: bool = Field(
        description=(
            "Must be true to proceed. Acts as a safety guard against accidental invocation."
        ),
        examples=[True, False],
    )


class BusMonitorSaveDataInput(BaseModel):
    """Input for bus_monitor_save_data."""

    monitor_name: str = Field(
        description="Name of the monitor whose buffer to save (e.g. 'CANMonitor').",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="Zero-based index of the target system (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus protocol type: CAN, LIN, FlexRay, or Ethernet.",
        examples=["CAN"],
    )
    output_file_path: str = Field(
        description=(
            "Absolute path for the output log file "
            "(e.g. 'C:\\\\Logs\\\\monitor_data.mf4'). Directory must exist."
        ),
        examples=["C:\\Logs\\monitor_data.mf4"],
    )


class BusMonitorSaveDataWithTimeAxisInput(BaseModel):
    """Input for bus_monitor_save_data_with_time_axis."""

    monitor_name: str = Field(
        description="Name of the monitor whose buffer to save (e.g. 'CANMonitor').",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="Zero-based index of the target system (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus protocol type: CAN, LIN, FlexRay, or Ethernet.",
        examples=["CAN"],
    )
    output_file_path: str = Field(
        description=(
            "Absolute path for the output log file (e.g. 'C:\\\\Logs\\\\monitor_abs.mf4')."
        ),
        examples=["C:\\Logs\\monitor_abs.mf4"],
    )
    time_axis: TimeAxis = Field(
        description=(
            "Time axis mode: 'Absolute' (UTC wall-clock timestamps), "
            "'Relative' (seconds from start), or 'RecordingTime' (hardware recording time)."
        ),
        examples=["Absolute", "Relative"],
    )


class BusMonitorLoadDataInput(BaseModel):
    """Input for bus_monitor_load_data."""

    monitor_name: str = Field(
        description="Name of the monitor to load data into (e.g. 'CANMonitor').",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="Zero-based index of the target system (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus protocol type: CAN, LIN, FlexRay, or Ethernet.",
        examples=["CAN"],
    )
    log_file_path: str = Field(
        description=(
            "Absolute path to the log file to load into the monitor buffer "
            "(e.g. 'C:\\\\Logs\\\\capture.asc'). File must exist."
        ),
        examples=["C:\\Logs\\capture.asc"],
    )
    log_file_section: int = Field(
        default=0,
        description=(
            "Zero-based section index within the log file. "
            "Multi-session log files may contain multiple sections. Use 0 for single-session files."
        ),
        examples=[0],
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


class BusMonitorRenameInput(BaseModel):
    """Input for bus_monitor_rename."""

    monitor_name: str = Field(
        description="Current name of the monitor to rename.",
        examples=["CANMonitor"],
    )
    new_name: str = Field(
        description="New name for the monitor. Must be unique within the physical bus access.",
        examples=["RxMonitor"],
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


class BusMonitorQueryAction(str, Enum):
    """Actions for bus_monitor_query read-only tool."""

    get_state = "get_state"
    list = "list"


class BusMonitorManageAction(str, Enum):
    """Action for the consolidated bus_monitor_manage tool (mutating only)."""

    start = "start"
    stop = "stop"
    remove = "remove"
    clear_all = "clear_all"
    rename = "rename"


class BusMonitorQueryInput(BaseModel):
    """Input for bus_monitor_query (read-only actions)."""

    action: BusMonitorQueryAction = Field(
        description=(
            "Read-only action to perform on a bus monitor. "
            "'get_state' — query current state (Running/Stopped) (requires monitor_name); "
            "'list' — enumerate all monitors on a physical bus access with pagination."
        ),
        examples=["get_state", "list"],
    )
    system_index: int = Field(description="System index.", examples=[1])
    bus_type: BusType = Field(description="Bus type (e.g. 'CAN').", examples=["CAN"])
    monitor_name: Optional[str] = Field(
        default=None,
        description="Name of the monitor. Required for: get_state.",
        examples=["CANMonitor"],
    )
    bus_platform_index: int = Field(default=0, description="Bus platform index.", examples=[0])
    physical_bus_access_index: int = Field(
        default=0, description="Physical bus access index.", examples=[0]
    )
    limit: int = Field(default=200, ge=1, le=1000, description="Maximum records for 'list'.")
    offset: int = Field(default=0, ge=0, description="Zero-based offset for 'list' pagination.")


class BusMonitorManageInput(BaseModel):
    """Input for bus_monitor_manage (mutating actions only)."""

    action: BusMonitorManageAction = Field(
        description=(
            "Mutating action to perform on a bus monitor. "
            "'start' — activate and start monitoring (requires monitor_name); "
            "'stop' — stop monitoring (requires monitor_name); "
            "'remove' — remove a specific monitor (requires monitor_name; stop first); "
            "'clear_all' — remove all monitors from a physical bus access (requires confirm=True); "
            "'rename' — rename an existing monitor (requires monitor_name and new_name). "
            "Use bus_monitor_query to query state or list monitors."
        ),
        examples=["start", "stop", "remove"],
    )
    system_index: int = Field(
        description="System index.",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    monitor_name: Optional[str] = Field(
        default=None,
        description=(
            "Name of the monitor. Required for: start, stop, remove, rename. "
            "Not required for: clear_all."
        ),
        examples=["CANMonitor"],
    )
    bus_platform_index: int = Field(
        default=0,
        description="Bus platform index.",
        examples=[0],
    )
    physical_bus_access_index: int = Field(
        default=0,
        description="Physical bus access index.",
        examples=[0],
    )
    confirm: bool = Field(
        default=False,
        description="Required for action='clear_all'. Must be True to proceed.",
        examples=[True, False],
    )
    new_name: Optional[str] = Field(
        default=None,
        description="Required for action='rename'. New unique name for the monitor.",
        examples=["RxMonitor"],
    )


class BusMonitorSaveInput(BaseModel):
    """Input for bus_monitor_save."""

    monitor_name: str = Field(
        description="Name of the monitor whose buffer to save (e.g. 'CANMonitor').",
        examples=["CANMonitor"],
    )
    system_index: int = Field(
        description="Zero-based index of the target system (e.g. 1).",
        examples=[1],
    )
    bus_type: BusType = Field(
        description="Bus protocol type: CAN, LIN, FlexRay, or Ethernet.",
        examples=["CAN"],
    )
    output_file_path: str = Field(
        description=(
            "Absolute path for the output log file "
            "(e.g. 'C:\\\\Logs\\\\monitor_data.mf4'). Directory must exist."
        ),
        examples=["C:\\Logs\\monitor_data.mf4"],
    )
    time_axis: Optional[TimeAxis] = Field(
        default=None,
        description=(
            "Optional. Time axis mode: 'Absolute' (UTC wall-clock timestamps), "
            "'Relative' (seconds from start), or 'RecordingTime' (hardware recording time). "
            "When omitted, uses default save behavior without explicit time axis selection."
        ),
        examples=["Absolute", "Relative"],
    )


# ── Response models ───────────────────────────────────────────────────────────


class BusMonitorCreateResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_create."""

    created: Literal[True] = True
    monitor_name: str
    system_index: int
    bus_type: str
    state: Literal["Stopped"] = "Stopped"
    timestamp_utc: str


class BusMonitorConfigureResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_configure."""

    configured: Literal[True] = True
    monitor_name: str
    update_rate_ms: int
    buffer_size_frames: int
    buffer_mode: str
    enable_j1939_pgn_resolving: bool
    timestamp_utc: str


class BusMonitorStartResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_start."""

    started: Literal[True] = True
    monitor_name: str
    state: Literal["Running"] = "Running"
    timestamp_utc: str


class BusMonitorStopResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_stop."""

    stopped: Literal[True] = True
    monitor_name: str
    state: Literal["Stopped"] = "Stopped"
    timestamp_utc: str


class BusMonitorGetStateResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_get_state."""

    monitor_name: str
    state: str
    is_running: bool
    timestamp_utc: str


class BusMonitorListResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_list."""

    model_config = {"extra": "allow"}

    system_index: int
    bus_type: str
    total_count: int
    monitors: list[dict]
    timestamp_utc: str


class BusMonitorRemoveResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_remove."""

    removed: Literal[True] = True
    monitor_name: str
    timestamp_utc: str


class BusMonitorClearAllResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_clear_all."""

    cleared: bool
    monitors_removed: int
    system_index: int
    bus_type: str
    timestamp_utc: str


class BusMonitorClearAllAborted(DictModelMixin, BaseModel):
    """Response when bus_monitor_clear_all confirm is False."""

    cleared: Literal[False] = False
    message: str = "Operation aborted. Set 'confirm' to true to proceed with clearing all monitors."


class BusMonitorSaveDataResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_save_data."""

    saved: Literal[True] = True
    monitor_name: str
    output_file_path: str
    timestamp_utc: str


class BusMonitorSaveDataWithTimeAxisResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_save_data_with_time_axis."""

    saved: Literal[True] = True
    monitor_name: str
    output_file_path: str
    time_axis: str
    timestamp_utc: str


class BusMonitorLoadDataResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_load_data."""

    loaded: Literal[True] = True
    monitor_name: str
    log_file_path: str
    log_file_section: int
    timestamp_utc: str


class BusMonitorRenameResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_rename."""

    renamed: Literal[True] = True
    old_name: str
    new_name: str
    timestamp_utc: str


# ── Discover result models ────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the bus monitor domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class BusMonitorDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from bus_monitor_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
