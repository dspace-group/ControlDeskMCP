"""Pydantic input models for the recorder domain.

Domain: ControlDesk Main Recorder Management (MF4 file output, signal
        selection, lifecycle control — configure/start/stop).
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from controldesk_mcp.models.base import DictModelMixin


def _validate_abs_path(field_name: str, v: str) -> str:
    """Reject relative paths and directory-traversal segments."""
    p = Path(v)
    if not p.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path.")
    if ".." in p.parts:
        raise ValueError(f"{field_name} must not contain '..' segments.")
    return v


# ── Enums ────────────────────────────────────────────────────────────────────


class RecordingState(str, Enum):
    """Main recorder operational state (dSPACE.ToolAutomation.ControlDeskNG.RecordingState)."""

    Idling = "Idling"
    WaitingForTrigger = "WaitingForTrigger"
    Running = "Running"


# ── Input models ─────────────────────────────────────────────────────────────


class RecorderMainConfigureInput(BaseModel):
    """Input for recorder_main_configure."""

    base_filename: str = Field(
        description=(
            "Output file name without directory (e.g., 'Recording.mf4'). Must end in '.mf4'."
        ),
        examples=["Recording.mf4", "TestRun.mf4"],
    )
    automatic_naming_enabled: bool = Field(
        default=False,
        description=(
            "Set to True to enable sequential naming "
            "(e.g., Recording_010.mf4, Recording_011.mf4). Defaults to False."
        ),
        examples=[False, True],
    )
    automatic_naming_start_index: int = Field(
        default=1,
        description=(
            "Starting counter for sequential naming (e.g., 10 → starts at 010). Defaults to 1."
        ),
        examples=[1, 10],
    )
    automatic_naming_minimum_digits: int = Field(
        default=3,
        description=(
            "Minimum number of digits in the sequential counter "
            "(e.g., 3 → '010', '011'). Defaults to 3."
        ),
        examples=[3, 4],
    )
    add_to_experiment_enabled: bool = Field(
        default=False,
        description=(
            "Set to True to automatically add completed MF4 files to the active "
            "experiment. Defaults to False."
        ),
        examples=[False, True],
    )
    open_in_data_pool_enabled: bool = Field(
        default=False,
        description=(
            "Set to True to auto-open completed files in the Measurement Data Pool "
            "window. Defaults to False."
        ),
        examples=[False, True],
    )
    write_to_file_enabled: bool = Field(
        default=True,
        description=(
            "Set to False for event-based (non-file) recording (advanced use). Defaults to True."
        ),
        examples=[True, False],
    )
    automatic_signal_configuration_enabled: bool = Field(
        default=True,
        description=(
            "If True the recorder automatically adds/removes signals to match the "
            "current measurement signal list. Defaults to True."
        ),
        examples=[True, False],
    )
    description: str = Field(
        default="",
        description=(
            "Optional description stored inside the MF4 recording file. "
            "Defaults to empty string."
        ),
        examples=["", "Test run on bench A"],
    )


class RecorderMainAddSignalInput(BaseModel):
    """Input for recorder_main_add_signal."""

    connection_path: str = Field(
        description=(
            "Connection path of the signal to add "
            "(e.g., 'XCP(5ms)://control_out'). "
            "Must exist in the measurement configuration."
        ),
        examples=["XCP(5ms)://control_out", "XCP(100ms)://rpm"],
    )


class RecorderMainRemoveSignalInput(BaseModel):
    """Input for recorder_main_remove_signal."""

    connection_path: str = Field(
        description=(
            "Connection path of the signal to remove "
            "(e.g., 'XCP(5ms)://control_out'). "
            "Must match exactly as shown in recorder_main_list_signals."
        ),
        examples=["XCP(5ms)://control_out"],
    )


class RecorderMainListSignalsInput(BaseModel):
    """Input for recorder_main_list_signals."""

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


class RecorderMainStartInput(BaseModel):
    """Input for recorder_main_start."""

    with_trigger: bool = Field(
        default=False,
        description=(
            "Set to True if trigger-based start/stop conditions are configured. "
            "Recording waits for the start trigger to fire. Defaults to False."
        ),
        examples=[False, True],
    )
    overwrite_existing: bool = Field(
        default=True,
        description=(
            "Set to False to append to an existing file instead of overwriting. "
            "Defaults to True."
        ),
        examples=[True, False],
    )
    dry_run: bool = Field(
        default=False,
        description=(
            "When True, checks whether the recorder is already running and returns a "
            "preview without starting it. Use this to preview a start before committing it."
        ),
    )


class RecorderMainStopInput(BaseModel):
    """Input for recorder_main_stop."""

    dry_run: bool = Field(
        default=False,
        description=(
            "When True, checks whether the recorder is currently running and returns a "
            "preview without stopping it. Use this to preview a stop before committing it."
        ),
    )


class RecorderMainGetStateInput(BaseModel):
    """Input for recorder_main_get_state (no parameters required)."""


class RecorderMainInvokeTriggerInput(BaseModel):
    """Input for recorder_main_invoke_trigger (no parameters required)."""


class RecorderMainExportInput(BaseModel):
    """Input for recorder_main_export."""

    full_path: str = Field(
        description=(
            "Absolute file path for the exported recorder configuration file "
            "(e.g., 'C:\\\\Recordings\\\\recorder_config.mf4r'). "
            "Directory must exist and be writable."
        ),
        examples=["C:\\Recordings\\recorder_config.mf4r"],
    )
    overwrite_existing: bool = Field(
        default=False,
        description="If True overwrite an existing file at full_path. Defaults to False.",
        examples=[False, True],
    )

    @field_validator("full_path")
    @classmethod
    def _validate_full_path(cls, v: str) -> str:
        return _validate_abs_path("full_path", v)


class RecorderMainImportSignalsInput(BaseModel):
    """Input for recorder_main_import_signals."""

    full_path: str = Field(
        description=(
            "Absolute file path of a previously exported recorder configuration file "
            "from which signal definitions will be imported."
        ),
        examples=["C:\\Recordings\\recorder_config.mf4r"],
    )

    @field_validator("full_path")
    @classmethod
    def _validate_full_path(cls, v: str) -> str:
        return _validate_abs_path("full_path", v)


# ── Result models (Category B — COM bridge returns raw dicts) ─────────────────


class RecorderMainConfigureResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    base_filename: str
    automatic_naming_enabled: bool
    add_to_experiment_enabled: bool
    open_in_data_pool_enabled: bool
    write_to_file_enabled: bool
    automatic_signal_configuration_enabled: bool
    description: str
    timestamp_utc: str


class RecorderMainAddSignalResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    added: bool
    connection_path: str
    timestamp_utc: str


class RecorderMainRemoveSignalResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    connection_path: str
    timestamp_utc: str


class RecorderMainListSignalsResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_count: int
    signals: list[dict] = []


class RecorderMainStartResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    started: bool
    base_filename: str
    with_trigger: bool
    state: str
    timestamp_utc: str


class RecorderMainStopResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    stopped: bool
    output_files: list[str] = []
    timestamp_utc: str


class RecorderMainGetStateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    state: str
    is_running: bool
    last_recorded_files: list[str] = []
    timestamp_utc: str


class RecorderMainInvokeTriggerResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    triggered: bool
    state: str
    timestamp_utc: str


class RecorderMainExportResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    exported: bool
    full_path: str
    timestamp_utc: str


class RecorderMainImportSignalsResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    imported: bool
    full_path: str
    timestamp_utc: str


# ── Action enums ──────────────────────────────────────────────────────────────


class RecorderQueryAction(str, Enum):
    """Actions for recorder_query read-only tool."""

    get_state = "get_state"


class RecorderMainManageAction(str, Enum):
    """Actions for recorder_main_manage consolidated tool (mutating only)."""

    configure = "configure"
    invoke_trigger = "invoke_trigger"


class RecorderSignalManageAction(str, Enum):
    """Actions for recorder_signal_manage consolidated tool."""

    add_signal = "add_signal"
    remove_signal = "remove_signal"
    list_signals = "list_signals"


class RecorderConfigManageAction(str, Enum):
    """Actions for recorder_config_manage consolidated tool."""

    export = "export"
    import_signals = "import_signals"


# ── Consolidated input models ─────────────────────────────────────────────────


class RecorderQueryInput(BaseModel):
    """Input for recorder_query (read-only actions)."""

    action: RecorderQueryAction = RecorderQueryAction.get_state


class RecorderMainManageInput(BaseModel):
    """Input for recorder_main_manage (mutating actions only)."""

    action: RecorderMainManageAction

    # configure fields
    base_filename: Optional[str] = None
    automatic_naming_enabled: bool = False
    automatic_naming_start_index: int = 1
    automatic_naming_minimum_digits: int = 3
    add_to_experiment_enabled: bool = False
    open_in_data_pool_enabled: bool = False
    write_to_file_enabled: bool = True
    automatic_signal_configuration_enabled: bool = True
    description: str = ""


class RecorderSignalManageInput(BaseModel):
    """Input for recorder_signal_manage."""

    action: RecorderSignalManageAction
    connection_path: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=200, ge=1, le=1000)


class RecorderConfigManageInput(BaseModel):
    """Input for recorder_config_manage."""

    action: RecorderConfigManageAction
    full_path: Optional[str] = None
    overwrite_existing: bool = False

    @field_validator("full_path")
    @classmethod
    def _validate_full_path(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return _validate_abs_path("full_path", v)


# ── Discover result models ─────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the recorder domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class RecorderDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from recorder_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
