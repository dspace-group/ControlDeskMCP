"""MCP tools for ControlDesk variable read/write management.

Tools implemented (domain: variable management):

  MAIN (always loaded):
    variable_find   — Find a variable by name or path; return full metadata
    variable_read   — Read a variable (scalar/curve/map/array_element/string)
    variable_write  — Write a variable (scalar/array_element/string/curve/map)

  ADD_ON lazy (access via variable_discover):
    GROUP: DISCOVERY
      variable_list              — List ops: list_all, list_array_elements, list_group_variables
    GROUP: PAGE_MANAGEMENT
      data_set_manage            — Page activation: activate_working_page, activate_reference_page
    GROUP: VARIABLE_DESCRIPTIONS
      variable_description_manage — Description ops: list, activate, remove

  META / Discovery:
    variable_discover — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.variable_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.models.variable import (
    DataSetActivateReferencePageResult,
    DataSetActivateWorkingPageResult,
    DataSetManageAction,
    DataSetManageInput,
    ToolActionEntry,
    VariableDescriptionActivateInput,
    VariableDescriptionActivateResult,
    VariableDescriptionListInput,
    VariableDescriptionListResult,
    VariableDescriptionManageAction,
    VariableDescriptionManageInput,
    VariableDescriptionRemoveInput,
    VariableDescriptionRemoveResult,
    VariableDiscoverResult,
    VariableFindInput,
    VariableFindResult,
    VariableListAction,
    VariableListAllResult,
    VariableListArrayElementsInput,
    VariableListArrayElementsResult,
    VariableListGroupVariablesInput,
    VariableListGroupVariablesResult,
    VariableListInput,
    VariableReadArrayElementInput,
    VariableReadArrayElementResult,
    VariableReadCurveInput,
    VariableReadCurveResult,
    VariableReadInput,
    VariableReadMapInput,
    VariableReadMapResult,
    VariableReadScalarInput,
    VariableReadScalarResult,
    VariableReadStringInput,
    VariableReadStringResult,
    VariableReadType,
    VariableWriteAction,
    VariableWriteArrayElementInput,
    VariableWriteArrayElementResult,
    VariableWriteCurveInput,
    VariableWriteCurveResult,
    VariableWriteDryRunResult,
    VariableWriteInput,
    VariableWriteMapInput,
    VariableWriteMapResult,
    VariableWriteScalarInput,
    VariableWriteScalarResult,
    VariableWriteStringInput,
    VariableWriteStringResult,
)
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import variable_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — variable_find ────────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_variable_find",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Locates a variable or signal by its name or fully qualified connection path in the "
        "active variable description. Returns complete variable metadata including type, "
        "readability, write-ability, limits, and identifiers. Call this tool first before "
        "reading or writing a variable to confirm it exists and determine which read/write "
        "tool to use next. "
        "If the variable is a Curve, Map, or Array, the response indicates so and recommends "
        "using specialized read/write tools. "
        "Preconditions: the platform must be connected and a variable description must be "
        "loaded (use platform_manage(action='add_variable_description') to load one). "
        "Online calibration is NOT required to find/inspect variables — it is only "
        "required to read or write actual ECU values via variable_read/variable_write. "
        "To list all variables or browse groups in the variable description, call "
        "variable_discover first, then use variable_list."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.VARIABLE, ToolGroup.DISCOVERY),
)
async def variable_find(params: VariableFindInput) -> VariableFindResult | ErrorEnvelope:
    return await variable_service.find_variable(params)


# ── Tool 2 — variable_read ────────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_variable_read",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Reads the current value of a variable from the ECU. "
        "Set read_type to specify the variable kind: "
        "'scalar' — numeric Parameter or Measurement value (requires variable_name); "
        "'curve' — 1-D lookup table, returns axis + function values (requires variable_name); "
        "'map' — 2-D lookup table, returns X-axis, Y-axis, function matrix (requires variable_name); "
        "'array_element' — single element of an array variable (requires element_path); "
        "'string' — ECU string label or calibration identifier (requires variable_name). "
        "Preconditions: online calibration must be running; variable must be readable."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.VARIABLE, ToolGroup.READ),
)
async def variable_read(
    params: VariableReadInput,
) -> (
    VariableReadScalarResult
    | VariableReadCurveResult
    | VariableReadMapResult
    | VariableReadArrayElementResult
    | VariableReadStringResult
    | ErrorEnvelope
):
    if params.read_type == VariableReadType.scalar:
        if params.variable_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="variable_name is required when read_type='scalar'.",
                recovery_hint=("Set variable_name to the name or connection path of the scalar variable."),
            )
        return await variable_service.read_scalar_variable(
            VariableReadScalarInput(variable_name=params.variable_name, value_format=params.value_format)
        )

    if params.read_type == VariableReadType.curve:
        if params.variable_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="variable_name is required when read_type='curve'.",
                recovery_hint=("Set variable_name to the name or connection path of the curve variable."),
            )
        return await variable_service.read_curve_variable(
            VariableReadCurveInput(variable_name=params.variable_name, value_format=params.value_format)
        )

    if params.read_type == VariableReadType.map:
        if params.variable_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="variable_name is required when read_type='map'.",
                recovery_hint=("Set variable_name to the name or connection path of the map variable."),
            )
        return await variable_service.read_map_variable(
            VariableReadMapInput(variable_name=params.variable_name, value_format=params.value_format)
        )

    if params.read_type == VariableReadType.array_element:
        if params.element_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="element_path is required when read_type='array_element'.",
                recovery_hint=(
                    "Set element_path to the fully qualified array element path, e.g. 'XCP()://ParamVector[0]'."
                ),
            )
        return await variable_service.read_array_element(
            VariableReadArrayElementInput(element_path=params.element_path, value_format=params.value_format)
        )

    # string
    if params.variable_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="variable_name is required when read_type='string'.",
            recovery_hint=("Set variable_name to the name or connection path of the string variable."),
        )
    return await variable_service.read_string_variable(VariableReadStringInput(variable_name=params.variable_name))


# ── Tool 3 — variable_write ───────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_variable_write",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Writes a new value to a variable on the ECU working page. "
        "Set 'action' to specify the write type: "
        "'scalar' — numeric Parameter (requires variable_name and value); "
        "'array_element' — single element of a parameter array (requires element_path and value); "
        "'string' — ECU string label or identifier (requires variable_name and value as string); "
        "'curve' — 1-D lookup table (requires variable_name and function_values list of floats; "
        "axis_values optional); "
        "'map' — 2-D lookup table (requires variable_name and function_values 2-D list; "
        "x_axis_values, y_axis_values optional). "
        "Preconditions: online calibration running; working data set activated "
        "(call variable_discover first, then data_set_manage(action='activate_working_page')); "
        "variable must be writable. "
        "Dry-run: set dry_run=True to preview the change without writing to the ECU — the tool "
        "reads the current value and returns a diff (current_value, proposed_value, would_change) "
        "without modifying any ECU state. Use this before committing high-impact changes."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.VARIABLE, ToolGroup.WRITE),
)
async def variable_write(
    params: VariableWriteInput,
) -> (
    VariableWriteDryRunResult
    | VariableWriteScalarResult
    | VariableWriteArrayElementResult
    | VariableWriteStringResult
    | VariableWriteCurveResult
    | VariableWriteMapResult
    | ErrorEnvelope
):
    # ── Dry-run: read current value and return diff without writing ────────────
    if params.dry_run:
        name = params.variable_name or params.element_path
        proposed = params.value if params.value is not None else params.function_values
        if name is None or proposed is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message=(
                    "variable_name (or element_path) and value (or function_values) are required for dry_run=True."
                ),
                recovery_hint="Set the target variable identifier and the proposed value.",
            )
        return await variable_service.dry_run_write(
            action=params.action.value,
            variable_name=name,
            proposed_value=proposed,
            value_format=params.value_format.value,
        )

    action = params.action

    if action == VariableWriteAction.scalar:
        if params.variable_name is None or params.value is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="variable_name and value are required for action='scalar'.",
                recovery_hint="Set variable_name and value for the scalar parameter to write.",
            )
        return await variable_service.write_scalar_variable(
            VariableWriteScalarInput(
                variable_name=params.variable_name,
                value=params.value,
                value_format=params.value_format,
            )
        )

    if action == VariableWriteAction.array_element:
        if params.element_path is None or params.value is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="element_path and value are required for action='array_element'.",
                recovery_hint="Set element_path (e.g. 'XCP()://ParamVector[0]') and value.",
            )
        return await variable_service.write_array_element(
            VariableWriteArrayElementInput(
                element_path=params.element_path,
                value=params.value,
                value_format=params.value_format,
            )
        )

    if action == VariableWriteAction.string:
        if params.variable_name is None or params.value is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="variable_name and value are required for action='string'.",
                recovery_hint="Set variable_name and value (as string) for the string variable.",
            )
        return await variable_service.write_string_variable(
            VariableWriteStringInput(variable_name=params.variable_name, value=str(params.value))
        )

    if action == VariableWriteAction.curve:
        if params.variable_name is None or params.function_values is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="variable_name and function_values are required for action='curve'.",
                recovery_hint=("Set variable_name and function_values (list of floats) for the curve."),
            )
        return await variable_service.write_curve_variable(
            VariableWriteCurveInput(
                variable_name=params.variable_name,
                function_values=params.function_values,
                axis_values=params.axis_values,
                value_format=params.value_format,
            )
        )

    # map
    if params.variable_name is None or params.function_values is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="variable_name and function_values are required for action='map'.",
            recovery_hint=("Set variable_name and function_values (2-D list of floats) for the map."),
        )
    return await variable_service.write_map_variable(
        VariableWriteMapInput(
            variable_name=params.variable_name,
            function_values=params.function_values,
            x_axis_values=params.x_axis_values,
            y_axis_values=params.y_axis_values,
            value_format=params.value_format,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via variable_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: DISCOVERY ──────────────────────────────────────────────────────────
# ── Tool 4 — variable_list ────────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_variable_list",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "List operations for variables. "
        "Set 'action' to specify what to list: "
        "'list_all' — enumerate all variables grouped by type (Parameter, Measurement, "
        "Curve, Map, etc.); "
        "'list_array_elements' — list all sub-elements of an array variable "
        "(requires variable_name; use offset/limit for pagination); "
        "'list_group_variables' — list variables in a specific group path "
        "(group_path defaults to root; use offset/limit for pagination). "
        "Preconditions: online calibration must be running."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.VARIABLE, ToolGroup.DISCOVERY),
)
async def variable_list(
    params: VariableListInput,
) -> VariableListAllResult | VariableListArrayElementsResult | VariableListGroupVariablesResult | ErrorEnvelope:
    if params.action == VariableListAction.list_all:
        return await variable_service.list_all_variables()

    if params.action == VariableListAction.list_array_elements:
        if params.variable_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="variable_name is required for action='list_array_elements'.",
                recovery_hint=("Set variable_name to the name or connection path of the array variable."),
            )
        result = await variable_service.list_array_elements(
            VariableListArrayElementsInput(
                variable_name=params.variable_name,
                offset=params.offset,
                limit=params.limit,
            )
        )
        if isinstance(result, ErrorEnvelope):
            return result
        return VariableListArrayElementsResult(**paginate(result.model_dump(), params.offset, params.limit, "elements"))

    # list_group_variables
    result = await variable_service.list_group_variables(
        VariableListGroupVariablesInput(
            group_path=params.group_path,
            offset=params.offset,
            limit=params.limit,
        )
    )
    if isinstance(result, ErrorEnvelope):
        return result
    return VariableListGroupVariablesResult(**paginate(result.model_dump(), params.offset, params.limit, "variables"))


# ── GROUP: PAGE_MANAGEMENT ────────────────────────────────────────────────────
# ── Tool 5 — data_set_manage ──────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_variable_data_set_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages ECU memory page activation for calibration sessions. "
        "Set 'action' to specify which page to activate: "
        "'activate_working_page' — activate the working (RAM) page; mandatory before any "
        "variable_write operation; live parameter edits take effect immediately; "
        "'activate_reference_page' — activate the reference (flash) page; read-only snapshot "
        "of factory calibration; use for comparison only; writes are not supported. "
        "Preconditions: online calibration must be running; variable description must be loaded."
    ),
    annotations=AnnotationInfo(read_only=False),
    meta=MetaInfo(ToolDomain.CALIBRATION, ToolGroup.PAGE_MANAGEMENT),
)
async def data_set_manage(
    params: DataSetManageInput,
) -> DataSetActivateWorkingPageResult | DataSetActivateReferencePageResult | ErrorEnvelope:
    if params.action == DataSetManageAction.activate_working_page:
        return await variable_service.activate_working_page()
    # activate_reference_page
    return await variable_service.activate_reference_page()


# ── GROUP: VARIABLE_DESCRIPTIONS ──────────────────────────────────────────────
# ── Tool 6 — variable_description_manage ─────────────────────────────────────


@mcp.tool(
    name="controldesk_variable_description_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages variable descriptions (A2L-based calibration databases) for a platform. "
        "Set 'action' to specify what to do: "
        "'list' — enumerate all loaded variable descriptions for a platform "
        "(requires platform_name; use offset/limit for pagination); "
        "'activate' — set the active variable description (requires platform_name and "
        "variable_description_name; stop online calibration first); "
        "'remove' — remove a variable description from a platform (requires platform_name and "
        "variable_description_name; cannot remove the currently active description; "
        "calibration must NOT be running). "
        "Preconditions vary by action — see action descriptions above."
    ),
    annotations=AnnotationInfo(read_only=False),
    meta=MetaInfo(ToolDomain.VARIABLE, ToolGroup.VARIABLE_DESCRIPTIONS),
)
async def variable_description_manage(
    params: VariableDescriptionManageInput,
) -> (
    VariableDescriptionListResult | VariableDescriptionActivateResult | VariableDescriptionRemoveResult | ErrorEnvelope
):
    if params.platform_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="platform_name is required for all variable_description_manage actions.",
            recovery_hint="Set platform_name to the name of the platform (e.g., 'XCP').",
        )

    if params.action == VariableDescriptionManageAction.list:
        result = await variable_service.list_variable_descriptions(
            VariableDescriptionListInput(
                platform_name=params.platform_name,
                offset=params.offset,
                limit=params.limit,
            )
        )
        if isinstance(result, ErrorEnvelope):
            return result
        return VariableDescriptionListResult(
            **paginate(result.model_dump(), params.offset, params.limit, "variable_descriptions")
        )

    if params.variable_description_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="variable_description_name is required for activate and remove actions.",
            recovery_hint=("Set variable_description_name to the name of the variable description."),
        )

    if params.action == VariableDescriptionManageAction.activate:
        return await variable_service.activate_variable_description(
            VariableDescriptionActivateInput(
                platform_name=params.platform_name,
                variable_description_name=params.variable_description_name,
            )
        )

    # remove
    return await variable_service.remove_variable_description(
        VariableDescriptionRemoveInput(
            platform_name=params.platform_name,
            variable_description_name=params.variable_description_name,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 7 — variable_discover ────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_variable_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available variable management operations "
        "that are not loaded by default. ALWAYS call this tool first when you need to: "
        "list all variables or signals in the active variable description, "
        "browse variable groups, list variable descriptions, activate a variable description, "
        "or manage data set pages. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.VARIABLE, ToolGroup.DISCOVERY),
)
async def variable_discover(ctx: Context) -> VariableDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.VARIABLE, ctx)
    return VariableDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="controldesk_variable_list",
                purpose=("List all variables by type, list array elements, or list variables within a group."),
                actions=["list_all", "list_array_elements", "list_group_variables"],
                required_params_per_action={
                    "list_all": [],
                    "list_array_elements": ["variable_name"],
                    "list_group_variables": [],
                },
            ),
            ToolActionEntry(
                tool_name="controldesk_variable_data_set_manage",
                purpose=("Activate working (RAM) or reference (flash) memory page for calibration sessions."),
                actions=["activate_working_page", "activate_reference_page"],
                required_params_per_action={
                    "activate_working_page": [],
                    "activate_reference_page": [],
                },
            ),
            ToolActionEntry(
                tool_name="controldesk_variable_description_manage",
                purpose=("List, activate, or remove variable descriptions (A2L calibration databases) for a platform."),
                actions=["list", "activate", "remove"],
                required_params_per_action={
                    "list": ["platform_name"],
                    "activate": ["platform_name", "variable_description_name"],
                    "remove": ["platform_name", "variable_description_name"],
                },
            ),
        ]
    )
