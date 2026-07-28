"""MCP tools for ControlDesk instrument management.

Tools implemented (domain: instrument management):

  MAIN (always loaded):
    instrument_list    — Enumerate instruments on the active layout (or list instrument types)
    instrument_query   — Read-only query: get_info for a named instrument
    instrument_manage  — Mutating instrument operations: add, remove, move,
                         configure, arrange
    instrument_discover — Returns catalogue of all lazy add-on tools and their actions

  ADD_ON lazy (access via instrument_discover):
    GROUP: INSTRUMENT_SIGNAL
      instrument_signal_manage — Connect or disconnect variables/signals to/from instruments

COM entry point: app.LayoutManagement.ActiveLayout.Instruments (IViTopLevelInstruments)
Prerequisite: controldesk_app_start_or_attach must have been called; a layout must be active
              (call layout_list + layout_manage(action='activate') first).
Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations only.
All orchestration is delegated to controldesk_mcp.services.instrument_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.instrument import (
    InstrumentAddResult,
    InstrumentArrangeResult,
    InstrumentConfigureResult,
    InstrumentConnectSignalResult,
    InstrumentDisconnectSignalResult,
    InstrumentDiscoverResult,
    InstrumentGetInfoResult,
    InstrumentListInput,
    InstrumentListResult,
    InstrumentManageAction,
    InstrumentManageInput,
    InstrumentMoveResult,
    InstrumentQueryInput,
    InstrumentRemoveResult,
    InstrumentSignalManageAction,
    InstrumentSignalManageInput,
    InstrumentTypeListResult,
    ToolActionEntry,
)
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import instrument_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — instrument_list ──────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_instrument_list",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Enumerates instruments on the active ControlDesk layout, or lists available "
        "instrument types from the instrument library. "
        "Default (list_types=False): returns name, type, position (x, y), size "
        "(width, height), and main_variable for each instrument on the active layout. "
        "With list_types=True: returns all available instrument type strings, their "
        "category (Controls, Data Displays, Calibration, Decorations, Utility), and "
        "signal connection mode — useful before calling instrument_manage(action='add'). "
        "Instrument names returned are the exact strings to pass to instrument_manage and "
        "instrument_signal_manage. "
        "Prerequisite: controldesk_app_start_or_attach must have been called; a layout must be active "
        "(call layout_manage(action='activate') first)."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.INSTRUMENT, ToolGroup.INSTRUMENT_MANAGEMENT),
)
async def instrument_list(
    params: InstrumentListInput,
) -> InstrumentListResult | InstrumentTypeListResult | ErrorEnvelope:
    if params.list_types:
        return await instrument_service.instrument_list_types()

    result = await instrument_service.instrument_list()
    if isinstance(result, ErrorEnvelope):
        return result
    return InstrumentListResult(**paginate(result.model_dump(), params.offset, params.limit, "instruments"))


# ── Tool 2 — instrument_query ─────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_instrument_query",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Read-only queries for instruments on the active ControlDesk layout (readOnlyHint=true). "
        "'get_info' — retrieve detailed metadata including signal connections "
        "(requires instrument_name). "
        "Use instrument_list to discover available instrument names."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.INSTRUMENT, ToolGroup.INSTRUMENT_MANAGEMENT),
)
async def instrument_query(
    params: InstrumentQueryInput,
) -> InstrumentGetInfoResult | ErrorEnvelope:
    if params.instrument_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="instrument_name is required for action='get_info'.",
            recovery_hint=("Set instrument_name to the exact instrument name (use instrument_list to discover names)."),
        )
    return await instrument_service.instrument_get_info(params.instrument_name)


# ── Tool 3 — instrument_manage ────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_instrument_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages instruments on the active ControlDesk layout (mutating operations only). "
        "Set 'action' to specify what to do: "
        "'add' — add a new instrument (requires instrument_type and instrument_name; "
        "optional x, y, width, height; "
        "use instrument_list(list_types=True) for valid type strings; "
        "replay risk: calling 'add' again with the same instrument_name returns an error "
        "and does not create a second instrument); "
        "'remove' — remove an instrument from the layout (requires instrument_name); "
        "'move' — reposition or resize an instrument "
        "(requires instrument_name; optional x, y, width, height); "
        "'configure' — set display properties such as caption, back_color, fore_color, "
        "show_border (requires instrument_name; all properties are optional); "
        "'arrange' — align, distribute, group or ungroup instruments "
        "(requires instrument_names list and arrange_action: "
        "align_top, align_bottom, align_left, align_right, "
        "center_horizontally, center_vertically, "
        "space_evenly_horizontal, space_evenly_vertical, group, ungroup). "
        "Use instrument_query to retrieve instrument metadata. "
        "Use instrument_discover to access signal connect/disconnect operations. "
        "Prerequisite: a layout must be active (layout_manage(action='activate'))."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.INSTRUMENT, ToolGroup.INSTRUMENT_MANAGEMENT),
)
async def instrument_manage(
    params: InstrumentManageInput,
) -> (
    InstrumentAddResult
    | InstrumentRemoveResult
    | InstrumentMoveResult
    | InstrumentConfigureResult
    | InstrumentArrangeResult
    | ErrorEnvelope
):
    action = params.action

    if action == InstrumentManageAction.add:
        if params.instrument_type is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="instrument_type is required for action='add'.",
                recovery_hint=(
                    "Set instrument_type to a valid type string. "
                    "Call instrument_list(list_types=True) to see all available types."
                ),
            )
        if params.instrument_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="instrument_name is required for action='add'.",
                recovery_hint="Set instrument_name to a unique name for the new instrument.",
            )
        return await instrument_service.instrument_add(
            instrument_type=params.instrument_type,
            instrument_name=params.instrument_name,
            x=params.x if params.x is not None else 10,
            y=params.y if params.y is not None else 10,
            width=params.width if params.width is not None else 200,
            height=params.height if params.height is not None else 150,
        )

    if (
        action
        in (
            InstrumentManageAction.remove,
            InstrumentManageAction.move,
            InstrumentManageAction.configure,
        )
        and params.instrument_name is None
    ):
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message=f"instrument_name is required for action='{action.value}'.",
            recovery_hint=("Set instrument_name to the exact instrument name (use instrument_list to discover names)."),
        )

    if action == InstrumentManageAction.remove:
        return await instrument_service.instrument_remove(params.instrument_name)

    if action == InstrumentManageAction.move:
        return await instrument_service.instrument_move(
            instrument_name=params.instrument_name,
            x=params.x,
            y=params.y,
            width=params.width,
            height=params.height,
        )

    if action == InstrumentManageAction.configure:
        return await instrument_service.instrument_configure(
            instrument_name=params.instrument_name,
            caption=params.caption,
            back_color=params.back_color,
            fore_color=params.fore_color,
            show_border=params.show_border,
        )

    # arrange
    if params.instrument_names is None or len(params.instrument_names) == 0:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="instrument_names is required and must not be empty for action='arrange'.",
            recovery_hint=(
                "Set instrument_names to a list of instrument names to arrange together. "
                "Use instrument_list to discover available names."
            ),
        )
    if params.arrange_action is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="arrange_action is required for action='arrange'.",
            recovery_hint=(
                "Set arrange_action to one of: align_top, align_bottom, align_left, align_right, "
                "center_horizontally, center_vertically, "
                "space_evenly_horizontal, space_evenly_vertical, group, ungroup."
            ),
        )
    return await instrument_service.instrument_arrange(
        instrument_names=params.instrument_names,
        arrange_action=params.arrange_action.value,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via instrument_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: INSTRUMENT_SIGNAL ──────────────────────────────────────────────────
# ── Tool 4 — instrument_signal_manage ────────────────────────────────────────


@mcp.tool(
    name="controldesk_instrument_signal_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Connects or disconnects variables/signals to/from instruments on the active layout. "
        "Set 'action' to specify what to do: "
        "'connect' — connect a variable to an instrument "
        "(requires instrument_name and variable_path; "
        "optional signal_color '#RRGGBB', axis_index for Plotter instruments; "
        "connection mode is resolved automatically by instrument type: "
        "simple instruments use MainVariable, Time/XY Plotters use YAxis/Signal, "
        "variable Array uses Row, Table Editor uses SubInstrument); "
        "'disconnect' — remove a signal connection "
        "(requires instrument_name; "
        "optional variable_path and axis_index — omit variable_path to clear all connections). "
        "Use instrument_list to discover instrument names and types. "
        "Use variable_find or variable_discover to find valid variable_path values. "
        "Call instrument_discover first to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False),
    meta=MetaInfo(ToolDomain.INSTRUMENT, ToolGroup.INSTRUMENT_SIGNAL),
)
async def instrument_signal_manage(
    params: InstrumentSignalManageInput,
) -> InstrumentConnectSignalResult | InstrumentDisconnectSignalResult | ErrorEnvelope:
    if params.action == InstrumentSignalManageAction.connect:
        if params.variable_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="variable_path is required for action='connect'.",
                recovery_hint=(
                    "Set variable_path to the fully qualified variable path. "
                    "Use variable_find or variable_discover to discover available paths."
                ),
            )
        return await instrument_service.instrument_connect_signal(
            instrument_name=params.instrument_name,
            variable_path=params.variable_path,
            signal_color=params.signal_color,
            axis_index=params.axis_index,
        )

    # disconnect
    return await instrument_service.instrument_disconnect_signal(
        instrument_name=params.instrument_name,
        variable_path=params.variable_path,
        axis_index=params.axis_index,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 3 — instrument_discover ──────────────────────────────────────────────


@mcp.tool(
    name="controldesk_instrument_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available instrument operations "
        "that are not loaded by default. Call this tool first when you need to "
        "connect or disconnect signals to instruments. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.INSTRUMENT, ToolGroup.INSTRUMENT_MANAGEMENT),
)
async def instrument_discover(ctx: Context) -> InstrumentDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.INSTRUMENT, ctx)
    return InstrumentDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="controldesk_instrument_signal_manage",
                purpose=(
                    "Connect or disconnect variables/signals to/from instruments "
                    "on the active layout. Supports all instrument types including "
                    "Plotter (Time/XY), variable Array, Table Editor, and simple controls."
                ),
                actions=["connect", "disconnect"],
                required_params_per_action={
                    "connect": ["instrument_name", "variable_path"],
                    "disconnect": ["instrument_name"],
                },
            ),
        ]
    )
