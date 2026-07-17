"""Pydantic input models for the variable management domain.

Domain: ControlDesk variable read/write (variable_find, variable_read_scalar,
variable_write_scalar, variable_read_curve, etc.).

Convention: one models module per domain under sources/models/<domain>.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field

from sources.models.base import DictModelMixin

# ── Enums ─────────────────────────────────────────────────────────────────────


class VariableType(str, Enum):
    """Variable type as returned by the ControlDesk COM Type property."""

    Parameter = "Parameter"
    Measurement = "Measurement"
    String = "String"
    Curve = "Curve"
    Map = "Map"
    ValueBlock = "ValueBlock"
    Struct = "Struct"
    MeasurementArray = "MeasurementArray"
    CommonAxis = "CommonAxis"
    Calculated = "Calculated"


class ValueFormat(str, Enum):
    """Value format for read/write operations."""

    Converted = "Converted"  # Physical value in engineering units
    Source = "Source"  # Raw value in hardware units


class SearchMode(str, Enum):
    """Variable lookup search mode for variable_find."""

    name = "name"
    path = "path"


class VariableReadType(str, Enum):
    """Read operation type for the consolidated variable_read tool."""

    scalar = "scalar"
    curve = "curve"
    map = "map"
    array_element = "array_element"
    string = "string"


# ── Input models ──────────────────────────────────────────────────────────────


class VariableFindInput(BaseModel):
    """Input for variable_find."""

    identifier: str = Field(
        description=(
            "Variable name (e.g., 'air_mass', 'f_Kp_1') OR fully qualified "
            "connection path (e.g., 'XCP()://ParamVector[0]', 'XCP(5ms)://control_out'). "
            "Names are matched by simple string; paths must use the "
            "PlatformName(RasterName)://VariableName format."
        ),
        examples=["f_Kp_1", "XCP()://f_Kp_1"],
    )
    search_mode: Optional[SearchMode] = Field(
        default=None,
        description=(
            "Optional. Defaults to 'name' if identifier looks like a simple name, "
            "else 'path'. Explicitly set to force behavior."
        ),
    )


class VariableGetInfoInput(BaseModel):
    """Input for variable_get_info."""

    variable_name: str = Field(
        description=(
            "Simple variable name (e.g., 'f_Kp_1') or connection path " "(e.g., 'XCP()://f_Kp_1')."
        ),
        examples=["f_Kp_1", "control_out"],
    )


class VariableReadScalarInput(BaseModel):
    """Input for variable_read_scalar."""

    variable_name: str = Field(
        description=(
            "Name or connection path of the variable "
            "(e.g., 'control_out', 'XCP(5ms)://control_out')."
        ),
        examples=["control_out", "f_Kp_1"],
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description=(
            "Defaults to 'Converted' (physical value in engineering units). "
            "Set to 'Source' for raw hardware value."
        ),
    )


class VariableWriteScalarInput(BaseModel):
    """Input for variable_write_scalar."""

    variable_name: str = Field(
        description=(
            "Name or connection path of the parameter "
            "(e.g., 'f_Kp_1', 'XCP()://SignalAmplitude')."
        ),
        examples=["f_Kp_1", "SignalAmplitude"],
    )
    value: Union[float, int, str] = Field(
        description=(
            "New value to write in physical (engineering) units. "
            "For strings, pass as a string; for floats/ints, pass as number."
        ),
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description=(
            "Defaults to 'Converted' (physical value). "
            "Set to 'Source' to write raw hardware value (advanced; rarely used)."
        ),
    )


class VariableReadCurveInput(BaseModel):
    """Input for variable_read_curve."""

    variable_name: str = Field(
        description=(
            "Name or connection path of the curve variable "
            "(e.g., 'abs_sinp2_cosp2_table', 'XCP()://FuelInjectionCurve')."
        ),
        examples=["abs_sinp2_cosp2_table"],
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description=(
            "Defaults to 'Converted' (physical/engineering values). "
            "Set to 'Source' for raw hardware values."
        ),
    )


class VariableWriteCurveInput(BaseModel):
    """Input for variable_write_curve."""

    variable_name: str = Field(
        description="Name or connection path of the curve variable.",
        examples=["abs_sinp2_cosp2_table"],
    )
    function_values: list[float] = Field(
        description=(
            "New function values (Y-axis lookup table). "
            "Must be same length as current function values."
        ),
    )
    axis_values: Optional[list[float]] = Field(
        default=None,
        description=(
            "Optional. New axis values (X-axis). "
            "Leave undefined to keep current axis unchanged. "
            "Only set if recalibrating the input range."
        ),
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description="Defaults to 'Converted'. Set to 'Source' to write raw hardware values.",
    )


class VariableReadMapInput(BaseModel):
    """Input for variable_read_map."""

    variable_name: str = Field(
        description=(
            "Name or connection path of the map variable "
            "(e.g., 'Rec2Sine_z_table', 'XCP()://FuelMap')."
        ),
        examples=["Rec2Sine_z_table"],
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description="Defaults to 'Converted'. Set to 'Source' for raw hardware values.",
    )


class VariableWriteMapInput(BaseModel):
    """Input for variable_write_map."""

    variable_name: str = Field(
        description="Name or connection path of the map variable.",
        examples=["Rec2Sine_z_table"],
    )
    function_values: list[list[float]] = Field(
        description=(
            "New function matrix (2-D array). Must have same [rows, cols] as current map. "
            "Each row is a list of column values."
        ),
    )
    x_axis_values: Optional[list[float]] = Field(
        default=None,
        description=(
            "Optional. New X-axis values. Leave undefined to keep current X-axis unchanged."
        ),
    )
    y_axis_values: Optional[list[float]] = Field(
        default=None,
        description=(
            "Optional. New Y-axis values. Leave undefined to keep current Y-axis unchanged."
        ),
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description="Defaults to 'Converted'. Set to 'Source' for raw hardware values.",
    )


class VariableListArrayElementsInput(BaseModel):
    """Input for variable_list_array_elements."""

    variable_name: str = Field(
        description=(
            "Name or connection path of the array variable "
            "(e.g., 'ParamVector', 'XCP()://ParamVector')."
        ),
        examples=["ParamVector"],
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


class VariableReadArrayElementInput(BaseModel):
    """Input for variable_read_array_element."""

    element_path: str = Field(
        description=(
            "Fully qualified path to the array element "
            "(e.g., 'XCP()://ParamVector[0]', 'XCP(5ms)://MeasureArray[3]')."
        ),
        examples=["XCP()://ParamVector[0]"],
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description="Defaults to 'Converted'.",
    )


class VariableWriteArrayElementInput(BaseModel):
    """Input for variable_write_array_element."""

    element_path: str = Field(
        description=("Fully qualified path to the array element (e.g., 'XCP()://ParamVector[0]')."),
        examples=["XCP()://ParamVector[0]"],
    )
    value: Union[float, int, str] = Field(
        description="New value in physical (engineering) units.",
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description="Defaults to 'Converted'.",
    )


class VariableListGroupVariablesInput(BaseModel):
    """Input for variable_list_group_variables."""

    group_path: str = Field(
        default="",
        description=(
            "Optional. Path to a specific group (e.g., 'Engine Control/Fuel Injection'). "
            "Defaults to root group if omitted."
        ),
        examples=["Engine Control", "Engine Control/Fuel Injection"],
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


class VariableDescriptionListInput(BaseModel):
    """Input for variable_description_list."""

    platform_name: str = Field(
        description=(
            "Name of the platform to query (e.g., 'XCP'). "
            "Use platform_list to enumerate valid names."
        ),
        examples=["XCP", "SCALEXIO_1"],
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


class VariableDescriptionActivateInput(BaseModel):
    """Input for variable_description_activate."""

    platform_name: str = Field(
        description="Name of the platform (e.g., 'XCP').",
        examples=["XCP"],
    )
    variable_description_name: str = Field(
        description=(
            "Name of the variable description to activate (e.g., 'myecu_v2'). "
            "Must match a loaded description name."
        ),
        examples=["myecu_v2"],
    )


class VariableDescriptionRemoveInput(BaseModel):
    """Input for variable_description_remove."""

    platform_name: str = Field(
        description="Name of the platform (e.g., 'XCP').",
        examples=["XCP"],
    )
    variable_description_name: str = Field(
        description=(
            "Name of the variable description to remove (e.g., 'myecu'). "
            "The active description cannot be removed."
        ),
        examples=["myecu"],
    )


class VariableReadStringInput(BaseModel):
    """Input for variable_read_string."""

    variable_name: str = Field(
        description=(
            "Name or connection path of the string variable "
            "(e.g., 'ECU_Label', 'XCP()://CalibID')."
        ),
        examples=["ECU_Label"],
    )


class VariableWriteStringInput(BaseModel):
    """Input for variable_write_string."""

    variable_name: str = Field(
        description=("Name or connection path of the string variable (e.g., 'ECU_Label')."),
        examples=["ECU_Label"],
    )
    value: str = Field(
        description=(
            "New string value to write (e.g., 'Calibration_v2.0.0'). "
            "Must not exceed the variable's maximum string length."
        ),
        examples=["Calibration_v2.0.0"],
    )


class VariableReadInput(BaseModel):
    """Input for the consolidated variable_read tool."""

    read_type: VariableReadType = Field(
        description=(
            "Type of variable to read. "
            "'scalar' — numeric Parameter or Measurement; "
            "'curve' — 1-D lookup table (axis + function values); "
            "'map' — 2-D lookup table (X-axis, Y-axis, function matrix); "
            "'array_element' — single element of an array (requires element_path); "
            "'string' — ECU string label or calibration identifier."
        ),
        examples=["scalar", "curve", "array_element"],
    )
    variable_name: Optional[str] = Field(
        default=None,
        description=(
            "Name or connection path of the variable "
            "(e.g., 'control_out', 'FuelCurve', 'XCP()://CalibID'). "
            "Required for read_type: scalar, curve, map, string."
        ),
        examples=["control_out", "FuelCurve"],
    )
    element_path: Optional[str] = Field(
        default=None,
        description=(
            "Fully qualified path to an array element "
            "(e.g., 'XCP()://ParamVector[0]'). "
            "Required for read_type='array_element'."
        ),
        examples=["XCP()://ParamVector[0]"],
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description=(
            "Defaults to 'Converted' (physical value in engineering units). "
            "Set to 'Source' for raw hardware value. "
            "Ignored for read_type='string'."
        ),
    )


class VariableWriteSimpleType(str, Enum):
    """Write operation type for the consolidated variable_write_simple tool."""

    scalar = "scalar"
    array_element = "array_element"
    string = "string"


class VariableWriteSimpleInput(BaseModel):
    """Input for the consolidated variable_write_simple tool."""

    write_type: VariableWriteSimpleType = Field(
        description=(
            "Type of variable to write. "
            "'scalar' — numeric Parameter (requires variable_name and value); "
            "'array_element' — single element of an array (requires element_path and value); "
            "'string' — ECU string label or identifier (requires variable_name and value as string)."
        ),
        examples=["scalar", "array_element", "string"],
    )
    variable_name: Optional[str] = Field(
        default=None,
        description=(
            "Name or connection path of the variable (e.g., 'f_Kp_1', 'ECU_Label'). "
            "Required for write_type: scalar, string."
        ),
        examples=["f_Kp_1", "ECU_Label"],
    )
    element_path: Optional[str] = Field(
        default=None,
        description=(
            "Fully qualified path to an array element (e.g., 'XCP()://ParamVector[0]'). "
            "Required for write_type='array_element'."
        ),
        examples=["XCP()://ParamVector[0]"],
    )
    value: Union[float, int, str] = Field(
        description=(
            "New value to write. For scalar/array_element: numeric (float or int). "
            "For string: a string value not exceeding the variable's maximum length."
        ),
    )
    value_format: ValueFormat = Field(
        default=ValueFormat.Converted,
        description=(
            "Defaults to 'Converted' (physical value in engineering units). "
            "Set to 'Source' for raw hardware value. "
            "Ignored for write_type='string'."
        ),
    )


# ── Result models (Category B — COM bridge returns raw dicts) ─────────────────


class VariableFindResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    found: bool
    variable_type: str = ""
    identifier: dict = {}
    name: str = ""
    is_readable: bool = False
    is_writable: bool = False
    is_changeable_only_during_initialization: bool = False
    unit: str = ""
    description: str = ""


class VariableGetInfoResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    found: bool
    variable_type: str = ""
    identifier: dict = {}
    name: str = ""
    is_readable: bool = False
    is_writable: bool = False
    is_changeable_only_during_initialization: bool = False
    unit: str = ""
    description: str = ""


class VariableListAllResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_count: int
    by_type: dict = {}


class VariableReadScalarResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    variable_name: str
    variable_type: str
    value: object
    value_format: str
    unit: str
    timestamp_utc: str


class VariableWriteScalarResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    written: bool
    variable_name: str
    variable_type: str
    value_written: object
    value_format: str
    unit: str
    timestamp_utc: str


class VariableWriteDryRunResult(DictModelMixin, BaseModel):
    """Response from variable_write when dry_run=True."""

    model_config = {"extra": "allow"}
    dry_run: bool = True
    action: str
    variable_name: str
    current_value: object
    proposed_value: object
    value_format: str
    unit: str = ""
    would_change: bool


class VariableReadCurveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    variable_name: str
    variable_type: str
    axis: dict = {}
    function_values: dict = {}
    value_format: str
    timestamp_utc: str


class VariableWriteCurveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    written: bool
    variable_name: str
    function_values_count: int
    axis_values_count: int
    value_format: str
    timestamp_utc: str


class VariableReadMapResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    variable_name: str
    variable_type: str
    x_axis: dict = {}
    y_axis: dict = {}
    function_values: dict = {}
    value_format: str
    timestamp_utc: str


class VariableWriteMapResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    written: bool
    variable_name: str
    rows: int
    cols: int
    value_format: str
    timestamp_utc: str


class VariableListArrayElementsResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_count: int
    elements: list[dict] = []


class VariableReadArrayElementResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    variable_name: str
    array_path: str
    index: int
    value: object
    unit: str
    timestamp_utc: str


class VariableWriteArrayElementResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    written: bool
    variable_name: str
    array_path: str
    index: int
    value_written: object
    timestamp_utc: str


class VariableListGroupVariablesResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    total_count: int
    group_path: str
    variables: list[dict] = []


class DataSetActivateWorkingPageResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    activated: bool
    data_set: str


class DataSetActivateReferencePageResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    activated: bool
    data_set: str


class VariableDescriptionListResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    platform_name: str
    total_count: int
    variable_descriptions: list[dict] = []


class VariableDescriptionActivateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    activated: bool
    platform_name: str
    variable_description_name: str


class VariableDescriptionRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    removed: bool
    platform_name: str
    variable_description_name: str
    timestamp_utc: str


class VariableReadStringResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    variable_name: str
    variable_type: str
    value: str
    timestamp_utc: str


class VariableWriteStringResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    written: bool
    variable_name: str
    value_written: str
    timestamp_utc: str


# ── Consolidated action enums ─────────────────────────────────────────────────


class VariableWriteAction(str, Enum):
    """Actions for the consolidated variable_write tool."""

    scalar = "scalar"
    array_element = "array_element"
    string = "string"
    curve = "curve"
    map = "map"


class VariableListAction(str, Enum):
    """Actions for the consolidated variable_list tool."""

    list_all = "list_all"
    list_array_elements = "list_array_elements"
    list_group_variables = "list_group_variables"


class DataSetManageAction(str, Enum):
    """Actions for the consolidated data_set_manage tool."""

    activate_working_page = "activate_working_page"
    activate_reference_page = "activate_reference_page"


class VariableDescriptionManageAction(str, Enum):
    """Actions for the consolidated variable_description_manage tool."""

    list = "list"
    activate = "activate"
    remove = "remove"


# ── Consolidated input models ─────────────────────────────────────────────────


class VariableWriteInput(BaseModel):
    """Input for the consolidated variable_write tool."""

    action: VariableWriteAction
    variable_name: Optional[str] = None
    element_path: Optional[str] = None
    value: Optional[Union[float, int, str]] = None
    value_format: ValueFormat = ValueFormat.Converted
    function_values: Optional[list] = None
    axis_values: Optional[list[float]] = None
    x_axis_values: Optional[list[float]] = None
    y_axis_values: Optional[list[float]] = None
    dry_run: bool = Field(
        default=False,
        description=(
            "When True, validates the target variable and returns the current value "
            "together with the proposed value without writing to the ECU. "
            "Use this to preview a change before committing it."
        ),
    )


class VariableListInput(BaseModel):
    """Input for the consolidated variable_list tool."""

    action: VariableListAction
    variable_name: Optional[str] = None
    group_path: str = ""
    offset: int = Field(default=0, ge=0, description="Zero-based offset for pagination.")
    limit: int = Field(
        default=200, ge=1, le=1000, description="Maximum number of records to return per call."
    )


class DataSetManageInput(BaseModel):
    """Input for the consolidated data_set_manage tool."""

    action: DataSetManageAction


class VariableDescriptionManageInput(BaseModel):
    """Input for the consolidated variable_description_manage tool."""

    action: VariableDescriptionManageAction
    platform_name: Optional[str] = None
    variable_description_name: Optional[str] = None
    offset: int = Field(default=0, ge=0, description="Zero-based offset for pagination.")
    limit: int = Field(
        default=200, ge=1, le=1000, description="Maximum number of records to return per call."
    )


# ── Discover result models ─────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the variable domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class VariableDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from variable_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
