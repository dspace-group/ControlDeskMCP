"""Pydantic input and response models for the bus replay domain.

Domain: ControlDesk Bus Replay (CAN/LIN/FlexRay/Ethernet frame playback).
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


class ReplayMode(str, Enum):
    """Replay playback mode."""

    Infinite = "Infinite"
    NumberOfPasses = "NumberOfPasses"
    Duration = "Duration"


class RunState(str, Enum):
    """Replay runtime state."""

    Running = "Running"
    Stopped = "Stopped"


# ── Replay input models ─────────────────────────────────────────────────────────


class BusReplayCreateInput(BaseModel):
    """Input for bus_replay_create."""

    replay_name: str = Field(
        description=(
            "Unique name for the replay "
            "(e.g. 'CANReplay', 'ScenarioPlayback'). "
            "Must not duplicate existing replay names on this physical bus access."
        ),
        examples=["CANReplay", "ScenarioPlayback"],
    )
    system_index: int = Field(
        description=(
            "Zero-based index of the target system "
            "(0 = transceiver/sender, 1 = receiver, etc.). "
            "Typically 0 for transmission."
        ),
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
        description="Zero-based index of the physical bus access (channel) (e.g. 0).",
        examples=[0],
    )
    dry_run: bool = Field(
        default=False,
        description=(
            "When True, checks whether a replay with this name already exists on the "
            "target physical bus access and returns a preview without creating anything. "
            "Use this to preview a create before committing it."
        ),
    )


class BusReplayConfigureInput(BaseModel):
    """Input for bus_replay_configure."""

    replay_name: str = Field(
        description="Name of the replay to configure (as created via bus_replay_create).",
        examples=["CANReplay"],
    )
    system_index: int = Field(
        description="System index (must match the system where the replay was created).",
        examples=[0],
    )
    bus_type: BusType = Field(
        description="Bus type (must match the bus type where the replay was created).",
        examples=["CAN"],
    )
    log_file_full_path: str = Field(
        description=(
            "Absolute file system path to the source log file (e.g. 'C:\\\\Logs\\\\recorded.asc'). File must exist."
        ),
        examples=["C:\\Logs\\recorded.asc"],
    )
    log_file_section: int = Field(
        default=0,
        description="Zero-based index of the log file section (for multi-section log files).",
        examples=[0],
    )
    replay_mode: ReplayMode = Field(
        default=ReplayMode.Infinite,
        description=(
            "Playback mode: 'Infinite' (loop forever), 'NumberOfPasses' (N repetitions), or 'Duration' (time-limited)."
        ),
        examples=["Infinite", "NumberOfPasses", "Duration"],
    )
    number_of_passes: int = Field(
        default=1,
        description=("Number of times to replay (if replay_mode is 'NumberOfPasses'). Ignored otherwise."),
        examples=[1, 3, 100],
    )
    duration_seconds: float = Field(
        default=0.0,
        description=("Duration in seconds (if replay_mode is 'Duration'). Ignored otherwise. 0.0 = unlimited."),
        examples=[0.0, 30.0, 60.0],
    )
    start_monitor_on_replay: bool = Field(
        default=False,
        description="Set to True to automatically start an associated monitor when replay starts.",
        examples=[False, True],
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


class BusReplayStartInput(BaseModel):
    """Input for bus_replay_start."""

    replay_name: str = Field(
        description="Name of the replay to start (e.g. 'CANReplay').",
        examples=["CANReplay"],
    )
    system_index: int = Field(
        description="System index (must match the system where the replay exists).",
        examples=[0],
    )
    bus_type: BusType = Field(
        description="Bus type (must match the bus type where the replay exists).",
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


class BusReplayStopInput(BaseModel):
    """Input for bus_replay_stop."""

    replay_name: str = Field(
        description="Name of the replay to stop (e.g. 'CANReplay').",
        examples=["CANReplay"],
    )
    system_index: int = Field(
        description="System index (e.g. 0).",
        examples=[0],
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


class BusReplayGetStateInput(BaseModel):
    """Input for bus_replay_get_state."""

    replay_name: str = Field(
        description="Name of the replay (e.g. 'CANReplay').",
        examples=["CANReplay"],
    )
    system_index: int = Field(
        description="System index (e.g. 0).",
        examples=[0],
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


class BusReplayListInput(BaseModel):
    """Input for bus_replay_list."""

    system_index: int = Field(
        description="System index (e.g. 0).",
        examples=[0],
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


class BusReplayRemoveInput(BaseModel):
    """Input for bus_replay_remove."""

    replay_name: str = Field(
        description="Name of the replay to remove (e.g. 'CANReplay').",
        examples=["CANReplay"],
    )
    system_index: int = Field(
        description="System index (e.g. 0).",
        examples=[0],
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


class BusReplayClearAllInput(BaseModel):
    """Input for bus_replay_clear_all."""

    system_index: int = Field(
        description="System index (e.g. 0).",
        examples=[0],
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
        description=("Must be True to proceed. Acts as a safety guard against accidental invocation."),
        examples=[True, False],
    )


class BusReplaySetActivatedInput(BaseModel):
    """Input for bus_replay_set_activated."""

    replay_name: str = Field(
        description=("Name of the replay to activate or deactivate (e.g. 'CANReplay')."),
        examples=["CANReplay"],
    )
    system_index: int = Field(
        description="System index (e.g. 0).",
        examples=[0],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    activated: bool = Field(
        description=(
            "True to activate the replay (required before bus_replay_start); "
            "False to deactivate (required before reconfiguring)."
        ),
        examples=[True, False],
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


class BusReplayRenameInput(BaseModel):
    """Input for bus_replay_rename."""

    replay_name: str = Field(
        description="Current name of the replay to rename.",
        examples=["CAN Replay"],
    )
    new_name: str = Field(
        description="New name for the replay. Must be unique within the physical bus access.",
        examples=["TxReplay"],
    )
    system_index: int = Field(
        description="Zero-based index of the target system.",
        examples=[0],
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


class BusReplayQueryAction(str, Enum):
    """Actions for bus_replay_query read-only tool."""

    get_state = "get_state"
    list = "list"


class BusReplayManageAction(str, Enum):
    """Action for the consolidated bus_replay_manage tool (mutating only)."""

    start = "start"
    stop = "stop"


class BusReplayAdminManageAction(str, Enum):
    """Action for the consolidated bus_replay_admin_manage tool."""

    remove = "remove"
    clear_all = "clear_all"
    set_activated = "set_activated"
    rename = "rename"


class BusReplayQueryInput(BaseModel):
    """Input for bus_replay_query (read-only actions)."""

    action: BusReplayQueryAction = Field(
        description=(
            "Read-only action to perform on a bus replay. "
            "'get_state' — query current state and activation status (requires replay_name); "
            "'list' — enumerate all replays on a physical bus access."
        ),
        examples=["get_state", "list"],
    )
    system_index: int = Field(description="System index (e.g. 0).", examples=[0])
    bus_type: BusType = Field(description="Bus type (e.g. 'CAN').", examples=["CAN"])
    replay_name: Optional[str] = Field(
        default=None,
        description="Name of the replay. Required for: get_state.",
        examples=["CANReplay"],
    )
    bus_platform_index: int = Field(default=0, description="Bus platform index.", examples=[0])
    physical_bus_access_index: int = Field(default=0, description="Physical bus access index.", examples=[0])
    limit: int = Field(default=200, ge=1, le=1000, description="Maximum records for 'list'.")
    offset: int = Field(default=0, ge=0, description="Zero-based offset for 'list' pagination.")


class BusReplayManageInput(BaseModel):
    """Input for bus_replay_manage (mutating actions only: start, stop)."""

    action: BusReplayManageAction = Field(
        description=(
            "Mutating action to perform on a bus replay. "
            "'start' — activate and start replay (requires replay_name); "
            "'stop' — stop and deactivate replay (requires replay_name). "
            "Use bus_replay_query to query state or list replays. "
            "For admin operations use bus_replay_admin_manage."
        ),
        examples=["start", "stop"],
    )
    system_index: int = Field(
        description="System index (e.g. 0).",
        examples=[0],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    replay_name: Optional[str] = Field(
        default=None,
        description="Name of the replay. Required for: start, stop.",
        examples=["CANReplay"],
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


class BusReplayAdminManageInput(BaseModel):
    """Input for bus_replay_admin_manage."""

    action: BusReplayAdminManageAction = Field(
        description=(
            "Admin action to perform on a bus replay. "
            "'remove' — remove a specific replay (requires replay_name; stop first); "
            "'clear_all' — remove all replays from a physical bus access (requires confirm=True; destructive); "
            "'set_activated' — set or clear the Activated flag independently (requires replay_name and activated); "
            "'rename' — rename an existing replay (requires replay_name and new_name)."
        ),
        examples=["remove", "clear_all", "set_activated", "rename"],
    )
    system_index: int = Field(
        description="System index (e.g. 0).",
        examples=[0],
    )
    bus_type: BusType = Field(
        description="Bus type (e.g. 'CAN').",
        examples=["CAN"],
    )
    replay_name: Optional[str] = Field(
        default=None,
        description=("Name of the replay. Required for: remove, set_activated, rename. Not required for: clear_all."),
        examples=["CANReplay"],
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
        description="Required for action='clear_all'. Must be True to proceed.",
        examples=[True, False],
    )
    activated: Optional[bool] = Field(
        default=None,
        description="Required for action='set_activated'. True to activate; False to deactivate.",
        examples=[True, False],
    )
    new_name: Optional[str] = Field(
        default=None,
        description="Required for action='rename'. New unique name for the replay.",
        examples=["TxReplay"],
    )


class BusReplayRenameResult(DictModelMixin, BaseModel):
    """Successful response from bus_replay_rename."""

    renamed: Literal[True] = True
    old_name: str
    new_name: str
    timestamp_utc: str


# ── Result models (Category B — COM bridge returns raw dicts) ─────────────────


class BusReplayCreateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    created: bool
    replay_name: str
    system_index: int
    bus_type: str
    state: str
    activated: bool
    timestamp_utc: str


class BusReplayConfigureResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    replay_name: str
    log_file_full_path: str
    replay_mode: str
    number_of_passes: int
    duration_seconds: float
    start_monitor_on_replay: bool
    timestamp_utc: str


class BusReplayStartResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    started: bool
    replay_name: str
    state: str
    activated: bool
    timestamp_utc: str


class BusReplayStopResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    stopped: bool
    replay_name: str
    state: str
    activated: bool
    timestamp_utc: str


class BusReplayGetStateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    replay_name: str
    state: str
    is_running: bool
    activated: bool
    log_file_path: str
    replay_mode: str
    timestamp_utc: str


class BusReplayListResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    system_index: int
    bus_type: str
    total_count: int
    replays: list[dict] = []
    timestamp_utc: str


class BusReplayRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    replay_name: str
    timestamp_utc: str


class BusReplayClearAllResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    cleared: bool
    replays_removed: int
    timestamp_utc: str


class BusReplayClearAllAborted(DictModelMixin, BaseModel):
    cleared: Literal[False] = False
    message: str = "Operation aborted. Set 'confirm' to true to proceed with clearing all replays."


class BusReplaySetActivatedResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    activated: bool
    replay_name: str
    state: str
    previous_activated: bool
    timestamp_utc: str


# ── Discover result models ────────────────────────────────────────────────────


class BusReplayToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the bus replay domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class BusReplayDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from bus_replay_discover."""

    status: Literal["ok"] = "ok"
    tools: list[BusReplayToolActionEntry]
