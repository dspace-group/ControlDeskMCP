"""Pydantic input and response models for the layout management domain.

Domain: ControlDesk Layout Management — IXaLayoutManagement / IXaLayouts / IXaLayout.

Convention: every tool domain owns its own models module under sources/models/<domain>.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from sources.models.base import DictModelMixin

# ── Enums ─────────────────────────────────────────────────────────────────────


class LayoutEditingMode(str, Enum):
    """Editing mode for a ControlDesk layout document."""

    Design = "Design"
    Runtime = "Runtime"
    Hybrid = "Hybrid"


class LayoutQueryAction(str, Enum):
    """Actions for layout_query read-only tool."""

    get_info = "get_info"


class LayoutManageAction(str, Enum):
    """Actions for layout_manage tool (mutating only)."""

    create = "create"
    open = "open"
    save = "save"
    close = "close"
    activate = "activate"
    configure = "configure"


class LayoutIoManageAction(str, Enum):
    """Actions for layout_io_manage tool."""

    export = "export"
    import_ = "import"
    import_connection_file = "import_connection_file"
    export_connection_file = "export_connection_file"


# ── Sub-models ────────────────────────────────────────────────────────────────


class LayoutInfo(DictModelMixin, BaseModel):
    """Metadata for a single layout entry."""

    name: str
    file_path: str
    is_open: bool
    is_active: bool
    editing_mode: str


# ── Input models ──────────────────────────────────────────────────────────────


class LayoutListInput(BaseModel):
    """Input for layout_list."""

    offset: int = Field(default=0, ge=0, description="Zero-based start index for pagination.")
    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of layouts to return.")


class LayoutQueryInput(BaseModel):
    """Input for layout_query (read-only actions)."""

    action: LayoutQueryAction = LayoutQueryAction.get_info
    name: Optional[str] = Field(
        default=None,
        description="Layout name. Required for action='get_info'.",
        examples=["ControlLayout"],
    )


class LayoutManageInput(BaseModel):
    """Input for layout_manage — mutating operations only."""

    action: LayoutManageAction = Field(
        description=(
            "Operation to perform: "
            "'create' (requires name), "
            "'open' (requires name), "
            "'save' (requires name), "
            "'close' (requires name; optional save_before_close), "
            "'activate' (requires name), "
            "'configure' (requires name and editing_mode)."
        )
    )
    name: Optional[str] = Field(
        default=None,
        description="Layout name. Required for all actions except none.",
        examples=["ControlLayout", "DiagnosticsPanel"],
    )
    save_before_close: bool = Field(
        default=True,
        description="For action='close': if True save before closing. Defaults to True.",
    )
    editing_mode: Optional[LayoutEditingMode] = Field(
        default=None,
        description=(
            "For action='configure': editing mode to set. " "Values: 'Design', 'Runtime', 'Hybrid'."
        ),
    )
    offset: int = Field(default=0, ge=0, description="Reserved for future list pagination.")
    limit: int = Field(default=50, ge=1, le=200, description="Reserved for future list pagination.")


class LayoutIoManageInput(BaseModel):
    """Input for layout_io_manage — I/O operations."""

    action: LayoutIoManageAction = Field(
        description=(
            "I/O operation to perform: "
            "'export' (requires export_path), "
            "'import' (requires import_path), "
            "'import_connection_file' (requires connection_file_path), "
            "'export_connection_file' (requires connection_file_path)."
        )
    )
    export_path: Optional[str] = Field(
        default=None,
        description=(
            "Absolute path for 'export' action. "
            "Must end with '.lax'. Example: 'C:\\\\Exports\\\\ControlLayout.lax'."
        ),
    )
    import_path: Optional[str] = Field(
        default=None,
        description=(
            "Absolute path of the .lax file for 'import' action. "
            "Example: 'C:\\\\Exports\\\\ControlLayout.lax'."
        ),
    )
    connection_file_path: Optional[str] = Field(
        default=None,
        description=(
            "Absolute path for 'import_connection_file' or 'export_connection_file'. "
            "Must end with '.cdx'. Example: 'C:\\\\Exports\\\\connections.cdx'."
        ),
    )


# ── Result models ─────────────────────────────────────────────────────────────


class LayoutListResult(DictModelMixin, BaseModel):
    """Result of layout_list."""

    total_layouts: int
    layouts: list[LayoutInfo]


class LayoutCreateResult(DictModelMixin, BaseModel):
    """Result of layout_manage(action='create')."""

    created: bool
    name: str
    file_path: str
    timestamp_utc: str


class LayoutOpenResult(DictModelMixin, BaseModel):
    """Result of layout_manage(action='open')."""

    opened: bool
    name: str
    file_path: str
    editing_mode: str
    timestamp_utc: str


class LayoutSaveResult(DictModelMixin, BaseModel):
    """Result of layout_manage(action='save')."""

    saved: bool
    name: str
    file_path: str
    timestamp_utc: str


class LayoutCloseResult(DictModelMixin, BaseModel):
    """Result of layout_manage(action='close')."""

    closed: bool
    name: str
    saved_before_close: bool
    timestamp_utc: str


class LayoutActivateResult(DictModelMixin, BaseModel):
    """Result of layout_manage(action='activate')."""

    activated: bool
    name: str
    timestamp_utc: str


class LayoutGetInfoResult(DictModelMixin, BaseModel):
    """Result of layout_manage(action='get_info')."""

    name: str
    file_path: str
    is_open: bool
    is_active: bool
    editing_mode: str
    timestamp_utc: str


class LayoutConfigureResult(DictModelMixin, BaseModel):
    """Result of layout_manage(action='configure')."""

    configured: bool
    name: str
    editing_mode: str
    timestamp_utc: str


class LayoutExportResult(DictModelMixin, BaseModel):
    """Result of layout_io_manage(action='export')."""

    exported: bool
    layout_name: str
    export_path: str
    timestamp_utc: str


class LayoutImportResult(DictModelMixin, BaseModel):
    """Result of layout_io_manage(action='import')."""

    imported: bool
    layout_name: str
    import_path: str
    timestamp_utc: str


class LayoutImportConnectionFileResult(DictModelMixin, BaseModel):
    """Result of layout_io_manage(action='import_connection_file')."""

    imported: bool
    connection_file_path: str
    timestamp_utc: str


class LayoutExportConnectionFileResult(DictModelMixin, BaseModel):
    """Result of layout_io_manage(action='export_connection_file')."""

    exported: bool
    connection_file_path: str
    timestamp_utc: str


# ── Discovery model ───────────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Describes a single tool with its supported actions and required parameters."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class LayoutDiscoverResult(DictModelMixin, BaseModel):
    """Result of layout_discover."""

    tools: list[ToolActionEntry]
