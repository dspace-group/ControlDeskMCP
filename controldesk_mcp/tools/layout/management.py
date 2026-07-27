"""MCP tools for ControlDesk layout management.

Tools implemented (domain: layout management):

  MAIN (always loaded):
    layout_list    — Enumerate all layouts in the active experiment
    layout_manage  — Combined lifecycle operations: create, open, save, close, activate,
                     get_info, configure
    layout_discover — Returns catalogue of all lazy add-on tools and their actions

  ADD_ON lazy (access via layout_discover):
    GROUP: LAYOUT_IO
      layout_io_manage — Export/import layouts and connection files

COM entry point: app.LayoutManagement (IXaLayoutManagement)
Prerequisite: start_controldesk must have been called; experiment must be open.
Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations only.
All orchestration is delegated to controldesk_mcp.services.layout_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.layout import (
    LayoutActivateResult,
    LayoutCloseResult,
    LayoutConfigureResult,
    LayoutCreateResult,
    LayoutDiscoverResult,
    LayoutExportConnectionFileResult,
    LayoutExportResult,
    LayoutGetInfoResult,
    LayoutImportConnectionFileResult,
    LayoutImportResult,
    LayoutIoManageAction,
    LayoutIoManageInput,
    LayoutListInput,
    LayoutListResult,
    LayoutManageAction,
    LayoutManageInput,
    LayoutOpenResult,
    LayoutQueryInput,
    LayoutSaveResult,
    ToolActionEntry,
)
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import layout_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — layout_list ──────────────────────────────────────────────────────


@mcp.tool(
    name="layout_list",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Enumerates all layouts in the currently open ControlDesk experiment. "
        "Returns name, file path, open state, active state, and editing mode for each layout. "
        "Use this as the first step to discover which layouts exist and their exact names. "
        "Layout names returned are the exact strings to pass to layout_manage and layout_io_manage. "
        "Prerequisite: start_controldesk must have been called and an experiment must be open."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.LAYOUT, ToolGroup.LAYOUT_MANAGEMENT),
)
async def layout_list(params: LayoutListInput) -> LayoutListResult | ErrorEnvelope:
    result = await layout_service.layout_list()
    if isinstance(result, ErrorEnvelope):
        return result
    return LayoutListResult(**paginate(result.model_dump(), params.offset, params.limit, "layouts"))


# ── Tool 2 — layout_query ─────────────────────────────────────────────────────


@mcp.tool(
    name="layout_query",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Read-only queries for ControlDesk layouts (readOnlyHint=true). "
        "'get_info' — retrieve metadata (name, file_path, is_open, is_active, editing_mode) "
        "for a layout (requires name). "
        "Use layout_list to discover available layout names."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.LAYOUT, ToolGroup.LAYOUT_MANAGEMENT),
)
async def layout_query(params: LayoutQueryInput) -> LayoutGetInfoResult | ErrorEnvelope:
    if params.name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="name is required for action='get_info'.",
            recovery_hint="Set name to the layout name (use layout_list to discover available names).",
        )
    return await layout_service.layout_get_info(params.name)


# ── Tool 3 — layout_manage ────────────────────────────────────────────────────


@mcp.tool(
    name="layout_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages the lifecycle and configuration of ControlDesk layouts (mutating operations only). "
        "Set 'action' to specify what to do: "
        "'create' — create a new empty layout (requires name; replay risk: calling "
        "'create' again with the same name returns an error and does not create a second layout); "
        "'open' — open an existing layout and make it visible (requires name); "
        "'save' — save a layout to its .cdl file (requires name); "
        "'close' — close an open layout; save_before_close defaults to True (requires name); "
        "'activate' — bring a layout to the foreground (requires name); "
        "'configure' — set the editing mode of a layout "
        "(requires name and editing_mode: Design, Runtime, Hybrid). "
        "Use layout_query to get layout metadata. "
        "Use layout_list to discover available layout names. "
        "Use layout_discover to access export/import operations. "
        "Prerequisite: start_controldesk must have been called."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.LAYOUT, ToolGroup.LAYOUT_MANAGEMENT),
)
async def layout_manage(
    params: LayoutManageInput,
) -> (
    LayoutCreateResult
    | LayoutOpenResult
    | LayoutSaveResult
    | LayoutCloseResult
    | LayoutActivateResult
    | LayoutGetInfoResult
    | LayoutConfigureResult
    | ErrorEnvelope
):
    action = params.action

    if (
        action
        in (
            LayoutManageAction.create,
            LayoutManageAction.open,
            LayoutManageAction.save,
            LayoutManageAction.close,
            LayoutManageAction.activate,
            LayoutManageAction.configure,
        )
        and params.name is None
    ):
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message=f"name is required for action='{action.value}'.",
            recovery_hint=("Set name to the layout name (use layout_list to discover available names)."),
        )

    if action == LayoutManageAction.create:
        return await layout_service.layout_create(params.name)

    if action == LayoutManageAction.open:
        return await layout_service.layout_open(params.name)

    if action == LayoutManageAction.save:
        return await layout_service.layout_save(params.name)

    if action == LayoutManageAction.close:
        return await layout_service.layout_close(params.name, params.save_before_close)

    if action == LayoutManageAction.activate:
        return await layout_service.layout_activate(params.name)

    # configure
    if params.editing_mode is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="editing_mode is required for action='configure'.",
            recovery_hint="Set editing_mode to one of: Design, Runtime, Hybrid.",
        )
    return await layout_service.layout_configure(params.name, params.editing_mode.value)


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via layout_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: LAYOUT_IO ──────────────────────────────────────────────────────────
# ── Tool 4 — layout_io_manage ─────────────────────────────────────────────────


@mcp.tool(
    name="layout_io_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Performs layout file I/O operations. "
        "Set 'action' to specify what to do: "
        "'export' — export the currently active layout to a .lax file (requires export_path); "
        "'import' — import a .lax layout file into the active experiment (requires import_path); "
        "'import_connection_file' — import a .cdx signal connection file into the experiment "
        "(requires connection_file_path); "
        "'export_connection_file' — export signal connections from the active layout "
        "to a .cdx file (requires connection_file_path). "
        "Call layout_discover first to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False),
    meta=MetaInfo(ToolDomain.LAYOUT, ToolGroup.LAYOUT_IO),
)
async def layout_io_manage(
    params: LayoutIoManageInput,
) -> (
    LayoutExportResult
    | LayoutImportResult
    | LayoutImportConnectionFileResult
    | LayoutExportConnectionFileResult
    | ErrorEnvelope
):
    action = params.action

    if action == LayoutIoManageAction.export:
        if params.export_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="export_path is required for action='export'.",
                recovery_hint="Provide the full file path for the .lax export file.",
            )
        return await layout_service.layout_export(params.export_path)

    if action == LayoutIoManageAction.import_:
        if params.import_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="import_path is required for action='import'.",
                recovery_hint="Provide the full file path of the .lax file to import.",
            )
        return await layout_service.layout_import(params.import_path)

    if action == LayoutIoManageAction.import_connection_file:
        if params.connection_file_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="connection_file_path is required for action='import_connection_file'.",
                recovery_hint="Provide the full file path of the .cdx connection file.",
            )
        return await layout_service.layout_import_connection_file(params.connection_file_path)

    # export_connection_file
    if params.connection_file_path is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="connection_file_path is required for action='export_connection_file'.",
            recovery_hint="Provide the full file path for the .cdx export file.",
        )
    return await layout_service.layout_export_connection_file(params.connection_file_path)


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 3 — layout_discover ──────────────────────────────────────────────────


@mcp.tool(
    name="layout_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available layout operations "
        "that are not loaded by default. Call this tool first when you need to "
        "export or import layouts or connection files. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True),
    meta=MetaInfo(ToolDomain.LAYOUT, ToolGroup.LAYOUT_MANAGEMENT),
)
async def layout_discover(ctx: Context) -> LayoutDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.LAYOUT, ctx)
    return LayoutDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="layout_io_manage",
                purpose=("Export/import layouts (.lax) and signal connection files (.cdx) for the active experiment."),
                actions=["export", "import", "import_connection_file", "export_connection_file"],
                required_params_per_action={
                    "export": ["export_path"],
                    "import": ["import_path"],
                    "import_connection_file": ["connection_file_path"],
                    "export_connection_file": ["connection_file_path"],
                },
            ),
        ]
    )
