"""MCP tools for ControlDesk tool window (panel) management.

Tools implemented (domain: tool window management):

  MAIN (always loaded):
    tool_window_list   — Enumerate all tool windows with name, dock state, visibility
    tool_window_show   — Show (and activate) a named tool window
    tool_window_manage — Combined panel operations: close, get_state, set_dock_state

  ADD_ON lazy (access via tool_window_discover):
    GROUP: WINDOW_QUERY
      tool_window_query — Diagnostic queries: check_exists, get_geometry

  META / Discovery:
    tool_window_discover — Returns a catalogue of all lazy add-on tools and their actions

COM entry point: app.MainWindow.Windows (IXaWindows collection)
Prerequisite: controldesk_app_start_or_attach must have been called; main window must be visible
              for panels to be rendered on screen.
Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations only.
All orchestration is delegated to controldesk_mcp.services.tool_window_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tool_window import (
    ToolActionEntry,
    ToolWindowCheckExistsInput,
    ToolWindowCheckExistsResult,
    ToolWindowCloseInput,
    ToolWindowCloseResult,
    ToolWindowDiscoverResult,
    ToolWindowGetGeometryInput,
    ToolWindowGetGeometryResult,
    ToolWindowGetStateInput,
    ToolWindowGetStateResult,
    ToolWindowListInput,
    ToolWindowListResult,
    ToolWindowManageAction,
    ToolWindowManageInput,
    ToolWindowQueryAction,
    ToolWindowQueryInput,
    ToolWindowSetDockStateInput,
    ToolWindowSetDockStateResult,
    ToolWindowShowInput,
    ToolWindowShowResult,
)
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import tool_window_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — tool_window_list ─────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_tool_window_list",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Enumerates all tool windows (panels) available in the current ControlDesk instance. "
        "Returns the exact caption (name), current dock state, and visibility "
        "status for each window. "
        "Use this as the first step to discover which panels are available and what names to "
        "pass to other tool_window_* tools. "
        "Available panels depend on ControlDesk license and installed features. "
        "Window names returned are the exact strings to pass to tool_window_show, "
        "tool_window_manage, and tool_window_query. "
        "Prerequisite: controldesk_app_start_or_attach must have been called."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.TOOL_WINDOW, ToolGroup.WINDOW_MANAGEMENT),
)
async def tool_window_list(params: ToolWindowListInput) -> ToolWindowListResult | ErrorEnvelope:
    result = await tool_window_service.list_windows()
    if isinstance(result, ErrorEnvelope):
        return result
    return ToolWindowListResult(**paginate(result.model_dump(), params.offset, params.limit, "windows"))


# ── Tool 2 — tool_window_show ─────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_tool_window_show",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Shows and activates a specific named tool window (panel). "
        "If previously closed, it reopens in its last docked position. "
        "If already visible, brings it to foreground. "
        "Window name must exactly match the Caption from tool_window_list(). "
        "Common panels: 'Project', 'Variables', 'Measurement Data Pool', "
        "'Measurement Configuration', 'Platforms/Devices', 'Interpreter', "
        "'Messages', 'Properties', 'Mappings', 'BusNavigator', 'LayoutEditor'. "
        "Prerequisite: ControlDesk running; main window visible (app_set_window_visible(True)). "
        "Use tool_window_query(action='check_exists') first if panel availability is uncertain."
    ),
    annotations=AnnotationInfo(read_only=False),
    meta=MetaInfo(ToolDomain.TOOL_WINDOW, ToolGroup.WINDOW_MANAGEMENT),
)
async def tool_window_show(params: ToolWindowShowInput) -> ToolWindowShowResult | ErrorEnvelope:
    return await tool_window_service.show_window(params)


# ── Tool 3 — tool_window_manage ───────────────────────────────────────────────


@mcp.tool(
    name="controldesk_tool_window_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages tool window state and docking (mutating operations only). "
        "Set 'action' to specify what to do: "
        "'close' — close (hide) a panel; the underlying domain is not affected; "
        "save_layout=True (default) preserves dock position for next show (requires window_name); "
        "'set_dock_state' — change the docking mode of a panel "
        "(requires window_name and dock_state; "
        "dock_state values: Docked, DockedAsDocument, AutoHidden, Floating, Closed). "
        "Use tool_window_discover for get_state, check_exists, and get_geometry operations."
    ),
    annotations=AnnotationInfo(read_only=False),
    meta=MetaInfo(ToolDomain.TOOL_WINDOW, ToolGroup.WINDOW_MANAGEMENT),
)
async def tool_window_manage(
    params: ToolWindowManageInput,
) -> ToolWindowCloseResult | ToolWindowSetDockStateResult | ErrorEnvelope:
    action = params.action

    if params.window_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="window_name is required for all tool_window_manage actions.",
            recovery_hint=(
                "Set window_name to the exact caption of the panel (use tool_window_list to discover names)."
            ),
        )

    if action == ToolWindowManageAction.close:
        return await tool_window_service.close_window(
            ToolWindowCloseInput(
                window_name=params.window_name,
                save_layout=params.save_layout,
            )
        )

    # set_dock_state
    if params.dock_state is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="dock_state is required for set_dock_state.",
            recovery_hint=("Set dock_state to one of: Docked, DockedAsDocument, AutoHidden, Floating, Closed."),
        )
    return await tool_window_service.set_window_dock_state(
        ToolWindowSetDockStateInput(
            window_name=params.window_name,
            dock_state=params.dock_state,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via tool_window_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: WINDOW_QUERY ───────────────────────────────────────────────────────
# ── Tool 4 — tool_window_query ────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_tool_window_query",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Read-only queries for tool windows (readOnlyHint=true). "
        "Set 'action' to specify what to do: "
        "'get_state' — query current dock state and visibility of a panel (requires window_name); "
        "'check_exists' — check whether a named panel exists in this ControlDesk instance "
        "(returns true/false; does NOT raise if absent; case-sensitive; requires window_name); "
        "'get_geometry' — return position and size of a panel in pixels "
        "(Left, Top, Width, Height from screen top-left; requires window_name; "
        "coordinates are only meaningful for Floating windows). "
        "Use tool_window_list first to discover available window names."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.TOOL_WINDOW, ToolGroup.WINDOW_MANAGEMENT),
)
async def tool_window_query(
    params: ToolWindowQueryInput,
) -> ToolWindowGetStateResult | ToolWindowCheckExistsResult | ToolWindowGetGeometryResult | ErrorEnvelope:
    if params.window_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="window_name is required for all tool_window_query actions.",
            recovery_hint=(
                "Set window_name to the exact caption of the panel (use tool_window_list to discover names)."
            ),
        )

    if params.action == ToolWindowQueryAction.get_state:
        return await tool_window_service.get_window_state(ToolWindowGetStateInput(window_name=params.window_name))

    if params.action == ToolWindowQueryAction.check_exists:
        return await tool_window_service.check_window_exists(ToolWindowCheckExistsInput(window_name=params.window_name))

    # get_geometry
    return await tool_window_service.get_window_geometry(ToolWindowGetGeometryInput(window_name=params.window_name))


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 5 — tool_window_discover ─────────────────────────────────────────────


@mcp.tool(
    name="controldesk_tool_window_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available tool window operations "
        "that are not loaded by default. Call this tool first when you need to "
        "check whether a panel exists or inspect its geometry. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.TOOL_WINDOW, ToolGroup.WINDOW_MANAGEMENT),
)
async def tool_window_discover(ctx: Context) -> ToolWindowDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.TOOL_WINDOW, ctx)
    return ToolWindowDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="controldesk_tool_window_query",
                purpose=(
                    "Read-only queries: get current dock state and visibility, "
                    "check whether a panel exists, or get its screen position and dimensions."
                ),
                actions=["get_state", "check_exists", "get_geometry"],
                required_params_per_action={
                    "get_state": ["window_name"],
                    "check_exists": ["window_name"],
                    "get_geometry": ["window_name"],
                },
            ),
        ]
    )
