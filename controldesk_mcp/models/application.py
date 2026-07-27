"""Pydantic input and response models for the application lifecycle domain.

Domain: ControlDesk application lifecycle (start_controldesk, stop_controldesk, window management).

Convention: every tool domain owns its own models module under controldesk_mcp/models/<domain>.py.
This keeps requests.py minimal (bootstrap only) and prevents model sprawl as new domains
are added (e.g. controldesk_mcp/models/project.py, controldesk_mcp/models/calibration.py).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from controldesk_mcp.models.base import DictModelMixin

# ── Manage-action enums ───────────────────────────────────────────────────────


class AppWindowManageAction(str, Enum):
    """Actions supported by app_window_manage."""

    set_visible = "set_visible"
    get_visibility = "get_visibility"
    set_state = "set_state"
    get_state = "get_state"
    set_position = "set_position"
    set_fullscreen = "set_fullscreen"


# ── Enums ─────────────────────────────────────────────────────────────────────


class MainWindowState(str, Enum):
    """ControlDesk main window display states."""

    Normal = "Normal"
    Minimized = "Minimized"
    Maximized = "Maximized"
    Hidden = "Hidden"


# ── Input models ──────────────────────────────────────────────────────────────


class AppStartOrAttachInput(BaseModel):
    """Input for start_controldesk."""

    controldesk_version: str = Field(
        default="",
        description=(
            "ControlDesk version to connect to in YYYY-L format (e.g. '2026-A'). "
            "Leave empty to auto-detect the latest installed version."
        ),
        examples=["2026-A", "2025-B", ""],
    )
    make_visible: bool = Field(
        default=True,
        description=(
            "If True the main window becomes visible after attach. "
            "Set to False for headless/background automation."
        ),
        examples=[True, False],
    )
    initial_window_state: MainWindowState = Field(
        default=MainWindowState.Normal,
        description=(
            "Initial window display state after making it visible. "
            "One of: 'Normal', 'Maximized', 'Minimized', 'Hidden'."
        ),
        examples=["Normal", "Maximized"],
    )
    force_version_switch: bool = Field(
        default=False,
        description=(
            "When True and a different ControlDesk version is already running, "
            "quit the running version and start the requested version. "
            "Only set to True after the user has explicitly confirmed the switch. "
            "Has no effect when controldesk_version is empty."
        ),
        examples=[False, True],
    )
    dry_run: bool = Field(
        default=False,
        description=(
            "When True, previews whether start_controldesk would need to quit a different "
            "running ControlDesk version and whether the active project has unsaved changes, "
            "without quitting or launching anything."
        ),
    )


class AppSetWindowVisibleInput(BaseModel):
    """Input for app_set_window_visible."""

    visible: bool = Field(
        description="True to show the window, False to hide it.",
        examples=[True, False],
    )


class AppSetWindowStateInput(BaseModel):
    """Input for app_set_window_state."""

    window_state: MainWindowState = Field(
        description=(
            "Desired display state: 'Normal' (standard window), 'Maximized' (full screen), "
            "'Minimized' (taskbar), or 'Hidden' (not visible)."
        ),
        examples=["Maximized", "Normal"],
    )


class AppQuitInput(BaseModel):
    """Input for stop_controldesk."""

    save_all_projects: bool = Field(
        default=True,
        description=(
            "If True all modified projects are saved before quitting. "
            "If False unsaved changes are discarded."
        ),
        examples=[True, False],
    )
    dry_run: bool = Field(
        default=False,
        description=(
            "When True, checks whether the active project has unsaved changes and returns "
            "a preview without quitting ControlDesk. Use this to preview the impact of "
            "save_all_projects=False before committing it."
        ),
    )


class AppSetWindowPositionInput(BaseModel):
    """Input for app_set_window_position."""

    left: int = Field(
        description=(
            "Horizontal position of the window's left edge in pixels from the screen's "
            "left boundary (e.g. 0 for left edge, 1920 for right edge of a 1080p monitor)."
        ),
        examples=[0, 1920],
    )
    top: int = Field(
        description=(
            "Vertical position of the window's top edge in pixels from the screen's "
            "top boundary (e.g. 0 for top of screen)."
        ),
        examples=[0, 100],
    )
    width: int = Field(
        gt=0,
        description="Window width in pixels. Must be positive (e.g. 1920 for full HD width).",
        examples=[1920, 1280],
    )
    height: int = Field(
        gt=0,
        description="Window height in pixels. Must be positive (e.g. 1080 for full HD height).",
        examples=[1080, 720],
    )


class AppSetFullscreenInput(BaseModel):
    """Input for app_set_fullscreen."""

    enabled: bool = Field(
        description=(
            "True to enable full-screen mode (covers entire display, hides taskbar); "
            "False to disable and return to normal windowed mode."
        ),
        examples=[True, False],
    )


class AppGetLogsInput(BaseModel):
    """Input for app_get_logs."""

    newest_first: bool = Field(
        default=True,
        description="If True, return newer log files first based on last-write time.",
        examples=[True, False],
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of log files to return.",
        examples=[20, 50, 100],
    )
    log_folder_override: str | None = Field(
        default=None,
        description=(
            "Optional absolute folder path to search first. "
            "If omitted, ControlDesk-compatible default locations under LOCALAPPDATA are used."
        ),
        examples=["C:\\Users\\user\\AppData\\Local\\dSPACE\\ControlDesk\\Log"],
    )


class AppWindowManageInput(BaseModel):
    """Consolidated input for app_window_manage."""

    action: AppWindowManageAction = Field(
        description=(
            "Operation to perform: 'set_visible', 'get_visibility', 'set_state', "
            "'get_state', 'set_position', or 'set_fullscreen'."
        )
    )
    visible: bool | None = Field(
        default=None,
        description="Required for: set_visible. True to show the window, False to hide it.",
        examples=[True, False],
    )
    window_state: MainWindowState | None = Field(
        default=None,
        description=(
            "Required for: set_state. " "One of: 'Normal', 'Maximized', 'Minimized', 'Hidden'."
        ),
        examples=["Maximized", "Normal"],
    )
    left: int | None = Field(
        default=None,
        description="Required for: set_position. Left edge in pixels from screen left.",
        examples=[0, 1920],
    )
    top: int | None = Field(
        default=None,
        description="Required for: set_position. Top edge in pixels from screen top.",
        examples=[0, 100],
    )
    width: int | None = Field(
        default=None,
        description="Required for: set_position. Window width in pixels (must be positive).",
        examples=[1920, 1280],
    )
    height: int | None = Field(
        default=None,
        description="Required for: set_position. Window height in pixels (must be positive).",
        examples=[1080, 720],
    )
    enabled: bool | None = Field(
        default=None,
        description="Required for: set_fullscreen. True to enable, False to disable.",
        examples=[True, False],
    )


# ── Response models ───────────────────────────────────────────────────────────


class AppStartOrAttachResult(DictModelMixin, BaseModel):
    """Successful response from start_controldesk."""

    status: Literal["ok"] = "ok"
    action: Literal["launched", "attached"]
    is_new_instance: bool
    controldesk_version: str
    window_visible: bool
    window_state: str
    launched_at_utc: str | None = Field(
        default=None,
        description=(
            "UTC timestamp of when ControlDesk finished launching. "
            "None when attaching to an already-running instance."
        ),
    )
    timestamp_utc: str


class AppVersionConfirmationRequired(DictModelMixin, BaseModel):
    """Response when a version switch needs explicit user confirmation."""

    status: Literal["confirmation_required"] = "confirmation_required"
    running_version: str
    requested_version: str
    message: str
    timestamp_utc: str


class AppSetWindowVisibleResult(DictModelMixin, BaseModel):
    """Successful response from app_set_window_visible."""

    visibility_set: Literal[True] = True
    is_now_visible: bool
    timestamp_utc: str


class AppGetWindowVisibilityResult(DictModelMixin, BaseModel):
    """Successful response from app_get_window_visibility."""

    is_visible: bool
    timestamp_utc: str


class AppSetWindowStateResult(DictModelMixin, BaseModel):
    """Successful response from app_set_window_state."""

    state_set: Literal[True] = True
    window_state: str
    timestamp_utc: str


class AppGetWindowStateResult(DictModelMixin, BaseModel):
    """Successful response from app_get_window_state."""

    window_state: str
    is_visible: bool
    timestamp_utc: str


class AppQuitResult(DictModelMixin, BaseModel):
    """Successful response from stop_controldesk."""

    quit: Literal[True] = True
    timestamp_utc: str


class AppSetWindowPositionResult(DictModelMixin, BaseModel):
    """Successful response from app_set_window_position."""

    positioned: Literal[True] = True
    left: int
    top: int
    width: int
    height: int
    timestamp_utc: str


class AppSetFullscreenResult(DictModelMixin, BaseModel):
    """Successful response from app_set_fullscreen."""

    fullscreen_set: Literal[True] = True
    fullscreen_enabled: bool
    timestamp_utc: str


class AppLogFileEntry(DictModelMixin, BaseModel):
    """Single ControlDesk log file entry."""

    path: str
    name: str
    size_bytes: int
    last_write_time_utc: str


class AppGetLogsResult(DictModelMixin, BaseModel):
    """Successful response from app_get_logs."""

    status: Literal["ok"] = "ok"
    file_pattern: str
    searched_folders: list[str]
    resolved_log_folders: list[str]
    files: list[AppLogFileEntry]
    total_found: int
    timestamp_utc: str


# ── Discover result models ────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the application domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class AppDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from app_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
