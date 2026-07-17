"""Pydantic input and response models for the tool window management domain.

Domain: ControlDesk tool window (panel) management — IXaWindows / IXaWindow.

Convention: every tool domain owns its own models module under sources/models/<domain>.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from sources.models.base import DictModelMixin

# ── Enums ─────────────────────────────────────────────────────────────────────


class ToolWindowState(str, Enum):
    """ControlDesk tool window docking states.

    Confirmed from XaWindowTests.cs (WindowState enum):
      WindowState.Docked, WindowState.DockedAsDocument,
      WindowState.AutoHidden, WindowState.Floating, WindowState.Closed
    """

    Docked = "Docked"
    DockedAsDocument = "DockedAsDocument"
    AutoHidden = "AutoHidden"
    Floating = "Floating"
    Closed = "Closed"


# ── Input models ──────────────────────────────────────────────────────────────


class ToolWindowShowInput(BaseModel):
    """Input for tool_window_show."""

    window_name: str = Field(
        description=(
            "Exact caption of the panel to show (case-sensitive). "
            "Use tool_window_list() to discover available names. "
            "Common panels: 'Project', 'Variables', 'Measurement Data Pool', "
            "'Measurement Configuration', 'Platforms/Devices', 'Interpreter', "
            "'Messages', 'Properties', 'Mappings', 'BusNavigator', 'LayoutEditor'."
        ),
        examples=["Variables", "Messages", "Project"],
    )


class ToolWindowCloseInput(BaseModel):
    """Input for tool_window_close."""

    window_name: str = Field(
        description=(
            "Exact caption of the panel to close (case-sensitive). "
            "Use tool_window_list() to discover available names."
        ),
        examples=["Messages", "Measurement Configuration"],
    )
    save_layout: bool = Field(
        default=True,
        description=(
            "If True the panel's dock position and layout configuration is saved before closing. "
            "If False layout is discarded. Defaults to True."
        ),
        examples=[True, False],
    )


class ToolWindowGetStateInput(BaseModel):
    """Input for tool_window_get_state."""

    window_name: str = Field(
        description=(
            "Exact caption of the panel to query (case-sensitive). "
            "Use tool_window_list() to discover available names."
        ),
        examples=["Variables", "Measurement Data Pool"],
    )


class ToolWindowSetDockStateInput(BaseModel):
    """Input for tool_window_set_dock_state."""

    window_name: str = Field(
        description=(
            "Exact caption of the panel to configure (case-sensitive). "
            "Use tool_window_list() to discover available names."
        ),
        examples=["Variables", "Platforms/Devices"],
    )
    dock_state: ToolWindowState = Field(
        description=(
            "Target dock state: 'Docked' (anchored to one edge), "
            "'DockedAsDocument' (full content area tab), "
            "'AutoHidden' (collapsed to sidebar tab), "
            "'Floating' (independent floating window), "
            "or 'Closed' (hidden entirely)."
        ),
        examples=["Docked", "AutoHidden", "Floating"],
    )


class ToolWindowCheckExistsInput(BaseModel):
    """Input for tool_window_check_exists."""

    window_name: str = Field(
        description=(
            "Exact caption of the panel to check (case-sensitive). "
            "Returns false (not an error) if the panel does not exist."
        ),
        examples=["BusNavigator", "EESPort Configurations"],
    )


# ── Response models ───────────────────────────────────────────────────────────


class ToolWindowListInput(BaseModel):
    """Input for tool_window_list."""

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


class ToolWindowInfo(BaseModel):
    """State snapshot for one tool window panel."""

    name: str
    caption: str
    is_visible: bool
    dock_state: str


class ToolWindowListResult(DictModelMixin, BaseModel):
    """Successful response from tool_window_list."""

    model_config = {"extra": "allow"}

    status: Literal["ok"] = "ok"
    total_windows: int
    windows: list[ToolWindowInfo]
    timestamp_utc: str


class ToolWindowShowResult(DictModelMixin, BaseModel):
    """Successful response from tool_window_show."""

    shown: Literal[True] = True
    window_name: str
    caption: str
    is_now_visible: bool
    dock_state: str
    timestamp_utc: str


class ToolWindowCloseResult(DictModelMixin, BaseModel):
    """Successful response from tool_window_close."""

    closed: Literal[True] = True
    window_name: str
    caption: str
    layout_saved: bool
    is_now_visible: bool
    timestamp_utc: str


class ToolWindowGetStateResult(DictModelMixin, BaseModel):
    """Successful response from tool_window_get_state."""

    window_name: str
    caption: str
    is_visible: bool
    dock_state: str
    timestamp_utc: str


class ToolWindowSetDockStateResult(DictModelMixin, BaseModel):
    """Successful response from tool_window_set_dock_state."""

    state_set: Literal[True] = True
    window_name: str
    caption: str
    dock_state: str
    is_visible: bool
    timestamp_utc: str


class ToolWindowCheckExistsResult(DictModelMixin, BaseModel):
    """Successful response from tool_window_check_exists."""

    window_name: str
    exists: bool
    timestamp_utc: str


class ToolWindowGetGeometryInput(BaseModel):
    """Input for tool_window_get_geometry."""

    window_name: str = Field(
        description=(
            "Exact caption of the panel to query (case-sensitive). "
            "Use tool_window_list() to discover available names."
        ),
        examples=["Variables", "Platforms/Devices"],
    )


class ToolWindowGetGeometryResult(DictModelMixin, BaseModel):
    """Successful response from tool_window_get_geometry."""

    window_name: str
    caption: str
    left: int
    top: int
    width: int
    height: int
    timestamp_utc: str


# ── Action enums ──────────────────────────────────────────────────────────────


class ToolWindowManageAction(str, Enum):
    """Actions for tool_window_manage consolidated tool (mutating only)."""

    close = "close"
    set_dock_state = "set_dock_state"


class ToolWindowQueryAction(str, Enum):
    """Actions for tool_window_query read-only consolidated tool."""

    get_state = "get_state"
    check_exists = "check_exists"
    get_geometry = "get_geometry"


# ── Consolidated input models ─────────────────────────────────────────────────


class ToolWindowManageInput(BaseModel):
    """Input for tool_window_manage (mutating actions only)."""

    action: ToolWindowManageAction
    window_name: Optional[str] = None
    save_layout: bool = True
    dock_state: Optional[ToolWindowState] = None


class ToolWindowQueryInput(BaseModel):
    """Input for tool_window_query (read-only actions)."""

    action: ToolWindowQueryAction
    window_name: Optional[str] = None


# ── Discover result models ─────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the tool window domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class ToolWindowDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from tool_window_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
