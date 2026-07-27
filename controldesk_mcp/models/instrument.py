"""Pydantic input and response models for the instrument management domain.

Domain: ControlDesk Layout Instrument Management — IViTopLevelInstruments.

Convention: every tool domain owns its own models module under controldesk_mcp/models/<domain>.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from controldesk_mcp.models.base import DictModelMixin

# ── Enums ─────────────────────────────────────────────────────────────────────


class InstrumentType(str, Enum):
    """Instrument type strings accepted by Instruments.Add() first argument.

    These are the exact strings as defined in the ControlDesk instrument library.
    """

    TimePlotter = "Time Plotter"
    Knob = "Knob"
    VariableArray = "variable Array"
    TableEditor = "Table Editor"
    Display = "Display"
    Gauge = "Gauge"
    Bar = "Bar"
    AnimatedNeedle = "Animated Needle"
    MultiStateDisplay = "Multi State Display"
    OnOffButton = "On/Off Button"
    PushButton = "Push Button"
    Slider = "Slider"
    NumericInput = "Numeric Input"
    CheckButton = "Check Button"
    RadioButton = "Radio Button"
    SelectionBox = "Selection Box"
    Frame = "Frame"
    StaticText = "Static Text"
    Browser = "Browser"
    XYPlotter = "XY Plotter"
    SteeringController = "Steering Controller"


class SignalConnectionMode(str, Enum):
    """Determines how a signal is connected to an instrument.

    Resolved automatically based on instrument type.
    """

    MainVariable = "main_variable"
    PlotterSignal = "plotter_signal"
    ArrayRow = "array_row"
    SubInstrument = "sub_instrument"


class ArrangeAction(str, Enum):
    """Arrangement actions for instrument_manage(action='arrange')."""

    AlignTop = "align_top"
    AlignBottom = "align_bottom"
    AlignLeft = "align_left"
    AlignRight = "align_right"
    CenterHorizontally = "center_horizontally"
    CenterVertically = "center_vertically"
    SpaceEvenlyHorizontal = "space_evenly_horizontal"
    SpaceEvenlyVertical = "space_evenly_vertical"
    Group = "group"
    Ungroup = "ungroup"


class InstrumentQueryAction(str, Enum):
    """Actions for instrument_query read-only tool."""

    get_info = "get_info"


class InstrumentManageAction(str, Enum):
    """Actions for instrument_manage tool (mutating only)."""

    add = "add"
    remove = "remove"
    move = "move"
    configure = "configure"
    arrange = "arrange"


class InstrumentSignalManageAction(str, Enum):
    """Actions for instrument_signal_manage tool."""

    connect = "connect"
    disconnect = "disconnect"


# ── Sub-models ────────────────────────────────────────────────────────────────


class InstrumentInfo(DictModelMixin, BaseModel):
    """Metadata for a single instrument on the active layout."""

    name: str
    type: str
    x: int
    y: int
    width: int
    height: int
    main_variable: Optional[str] = None


class InstrumentTypeInfo(DictModelMixin, BaseModel):
    """Entry in the instrument type catalogue."""

    type_string: str
    category: str
    signal_mode: Optional[str] = None


class SignalConnection(DictModelMixin, BaseModel):
    """A signal connection entry (for Plotter instruments)."""

    axis_index: Optional[int] = None
    signal_index: Optional[int] = None
    variable_path: str
    color: Optional[str] = None


# ── Input models ──────────────────────────────────────────────────────────────


class InstrumentListInput(BaseModel):
    """Input for instrument_list."""

    offset: int = Field(default=0, ge=0, description="Zero-based start index for pagination.")
    limit: int = Field(
        default=50, ge=1, le=200, description="Maximum number of instruments to return."
    )
    list_types: bool = Field(
        default=False,
        description=(
            "If True, returns available instrument types from the library "
            "instead of instruments placed on the active layout."
        ),
    )


class InstrumentQueryInput(BaseModel):
    """Input for instrument_query (read-only actions)."""

    action: InstrumentQueryAction = InstrumentQueryAction.get_info
    instrument_name: Optional[str] = Field(
        default=None,
        description="Name of the instrument to query. Required for action='get_info'.",
        examples=["SpeedKnob"],
    )


class InstrumentManageInput(BaseModel):
    """Input for instrument_manage — mutating operations only."""

    action: InstrumentManageAction = Field(
        description=(
            "Operation to perform: "
            "'add' (requires instrument_type, instrument_name; optional x, y, width, height), "
            "'remove' (requires instrument_name), "
            "'move' (requires instrument_name; optional x, y, width, height), "
            "'configure' (requires instrument_name; optional caption, back_color, fore_color, show_border), "
            "'arrange' (requires instrument_names list and arrange_action)."
        )
    )
    instrument_name: Optional[str] = Field(
        default=None,
        description=(
            "Name of the target instrument. Required for add, remove, move, configure. "
            "For read-only instrument info, use instrument_query instead."
        ),
        examples=["SpeedKnob", "ThrottlePlotter"],
    )
    instrument_names: Optional[list[str]] = Field(
        default=None,
        description="List of instrument names for action='arrange'.",
        examples=[["SpeedKnob", "ThrottlePlotter"]],
    )
    instrument_type: Optional[str] = Field(
        default=None,
        description=(
            "Instrument type string for action='add'. "
            "Use instrument_list(list_types=True) to get valid values. "
            "Examples: 'Time Plotter', 'Knob', 'Display', 'variable Array'."
        ),
    )
    x: Optional[int] = Field(default=None, description="Left position in layout pixels.", ge=0)
    y: Optional[int] = Field(default=None, description="Top position in layout pixels.", ge=0)
    width: Optional[int] = Field(default=None, description="Width in layout pixels.", ge=1)
    height: Optional[int] = Field(default=None, description="Height in layout pixels.", ge=1)
    caption: Optional[str] = Field(default=None, description="Caption text for action='configure'.")
    back_color: Optional[str] = Field(
        default=None,
        description="Background color in '#RRGGBB' hex format for action='configure'.",
        examples=["#FFFFFF", "#000000"],
    )
    fore_color: Optional[str] = Field(
        default=None,
        description="Foreground color in '#RRGGBB' hex format for action='configure'.",
        examples=["#000000", "#0000FF"],
    )
    show_border: Optional[bool] = Field(
        default=None, description="Border visibility for action='configure'."
    )
    arrange_action: Optional[ArrangeAction] = Field(
        default=None,
        description=(
            "Arrangement sub-action for action='arrange'. "
            "Values: 'align_top', 'align_bottom', 'align_left', 'align_right', "
            "'center_horizontally', 'center_vertically', "
            "'space_evenly_horizontal', 'space_evenly_vertical', 'group', 'ungroup'."
        ),
    )
    offset: int = Field(default=0, ge=0, description="Reserved for future list pagination.")
    limit: int = Field(default=50, ge=1, le=200, description="Reserved for future list pagination.")


class InstrumentSignalManageInput(BaseModel):
    """Input for instrument_signal_manage — connect/disconnect signals."""

    action: InstrumentSignalManageAction = Field(
        description=(
            "Signal operation: "
            "'connect' (requires instrument_name and variable_path; optional signal_color, axis_index), "
            "'disconnect' (requires instrument_name; optional variable_path, axis_index)."
        )
    )
    instrument_name: str = Field(
        description="Name of the target instrument.",
        examples=["ThrottlePlotter", "SpeedKnob"],
    )
    variable_path: Optional[str] = Field(
        default=None,
        description=(
            "Fully qualified variable path in format 'PlatformName(RasterName)://VariableUniqueName'. "
            "Required for action='connect'. Optional for 'disconnect' (omit to clear all connections). "
            "Example: 'XCP(5ms)://throttle_position'."
        ),
    )
    signal_color: Optional[str] = Field(
        default=None,
        description=(
            "Signal line color for Plotter instruments. RGB hex format '#RRGGBB'. "
            "Example: '#0000FF' for blue."
        ),
    )
    axis_index: int = Field(
        default=0,
        ge=0,
        description="For Plotter instruments: Y-axis index to add/remove the signal. Defaults to 0.",
    )


# ── Result models ─────────────────────────────────────────────────────────────


class InstrumentListResult(DictModelMixin, BaseModel):
    """Result of instrument_list (instruments on layout)."""

    layout_name: str
    total_instruments: int
    instruments: list[InstrumentInfo]


class InstrumentTypeListResult(DictModelMixin, BaseModel):
    """Result of instrument_list(list_types=True)."""

    total_types: int
    instrument_types: list[InstrumentTypeInfo]


class InstrumentAddResult(DictModelMixin, BaseModel):
    """Result of instrument_manage(action='add')."""

    added: bool
    instrument_name: str
    instrument_type: str
    x: int
    y: int
    width: int
    height: int
    timestamp_utc: str


class InstrumentRemoveResult(DictModelMixin, BaseModel):
    """Result of instrument_manage(action='remove')."""

    removed: bool
    instrument_name: str
    timestamp_utc: str


class InstrumentGetInfoResult(DictModelMixin, BaseModel):
    """Result of instrument_manage(action='get_info')."""

    instrument_name: str
    instrument_type: str
    x: int
    y: int
    width: int
    height: int
    signal_connections: list[SignalConnection]


class InstrumentMoveResult(DictModelMixin, BaseModel):
    """Result of instrument_manage(action='move')."""

    moved: bool
    instrument_name: str
    x: int
    y: int
    width: int
    height: int
    timestamp_utc: str


class InstrumentConfigureResult(DictModelMixin, BaseModel):
    """Result of instrument_manage(action='configure')."""

    configured: bool
    instrument_name: str
    caption: Optional[str] = None
    back_color: Optional[str] = None
    fore_color: Optional[str] = None
    show_border: Optional[bool] = None
    timestamp_utc: str


class InstrumentArrangeResult(DictModelMixin, BaseModel):
    """Result of instrument_manage(action='arrange')."""

    arranged: bool
    action: str
    instrument_names: list[str]
    group_name: Optional[str] = None
    timestamp_utc: str


class InstrumentConnectSignalResult(DictModelMixin, BaseModel):
    """Result of instrument_signal_manage(action='connect')."""

    connected: bool
    instrument_name: str
    instrument_type: str
    variable_path: str
    connection_mode: str
    timestamp_utc: str


class InstrumentDisconnectSignalResult(DictModelMixin, BaseModel):
    """Result of instrument_signal_manage(action='disconnect')."""

    disconnected: bool
    instrument_name: str
    variable_path: Optional[str] = None
    timestamp_utc: str


# ── Discovery model ───────────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Describes a single tool with its supported actions and required parameters."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class InstrumentDiscoverResult(DictModelMixin, BaseModel):
    """Result of instrument_discover."""

    tools: list[ToolActionEntry]
