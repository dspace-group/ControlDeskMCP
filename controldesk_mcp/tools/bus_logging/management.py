"""MCP tools for ControlDesk bus logging.

Tools implemented (domain: bus logging):

  MAIN (always loaded):
    bus_logger_create        — Create a new bus logger on a physical bus access
    bus_logger_configure     — Configure logger settings (file, duration, format, rolling)
    bus_logger_manage        — Lifecycle operations: start, stop, get_state, list

  ADD_ON lazy (access via bus_logging_discover):
    GROUP: LOGGER_ADMIN
      bus_logger_admin_manage — Admin operations: remove, clear_all, set_activated, rename
    GROUP: FILTER_MANAGEMENT
      bus_filter_create      — Create a new message filter
      bus_filter_configure   — Configure filter rules
      bus_filter_manage      — Lifecycle operations: start, stop, list, remove

  META / Discovery:
    bus_logging_discover     — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.bus_logging_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.bus_logging import (
    BusFilterConfigureInput,
    BusFilterConfigureResult,
    BusFilterCreateInput,
    BusFilterCreateResult,
    BusFilterListInput,
    BusFilterListResult,
    BusFilterManageAction,
    BusFilterManageInput,
    BusFilterRemoveInput,
    BusFilterRemoveResult,
    BusFilterStartInput,
    BusFilterStartResult,
    BusFilterStopInput,
    BusFilterStopResult,
    BusLoggerAdminManageAction,
    BusLoggerAdminManageInput,
    BusLoggerClearAllAborted,
    BusLoggerClearAllInput,
    BusLoggerClearAllResult,
    BusLoggerConfigureInput,
    BusLoggerConfigureResult,
    BusLoggerCreateInput,
    BusLoggerCreateResult,
    BusLoggerGetStateInput,
    BusLoggerGetStateResult,
    BusLoggerListInput,
    BusLoggerListResult,
    BusLoggerManageAction,
    BusLoggerManageInput,
    BusLoggerQueryAction,
    BusLoggerQueryInput,
    BusLoggerRemoveInput,
    BusLoggerRemoveResult,
    BusLoggerRenameInput,
    BusLoggerRenameResult,
    BusLoggerSetActivatedInput,
    BusLoggerSetActivatedResult,
    BusLoggerStartInput,
    BusLoggerStartResult,
    BusLoggerStopInput,
    BusLoggerStopResult,
    BusLoggingDiscoverResult,
    ToolActionEntry,
)
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import bus_logging_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — bus_logger_create ──────────────────────────────────────────────────


@mcp.tool(
    name="bus_logger_create",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Creates a new bus logger on a specified physical bus access. "
        + "The logger will capture all bus frames (CAN messages, LIN frames, "
        + "FlexRay frames, or Ethernet packets) on that channel. "
        + "After creation, configure the logger via bus_logger_configure before starting. "
        + "Logger names must be unique within a physical bus access. "
        + "Dry-run: set dry_run=True to preview the create — the tool checks whether a "
        + "logger with that name already exists without creating anything."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.LOGGER_MANAGEMENT),
)
async def bus_logger_create(
    params: BusLoggerCreateInput,
) -> BusLoggerCreateResult | DryRunPreviewResult | ErrorEnvelope:
    if params.dry_run:
        return await bus_logging_service.dry_run_create_logger(params)
    return await bus_logging_service.create_logger(params)


# ── Tool 2 — bus_logger_configure ───────────────────────────────────────────────


@mcp.tool(
    name="bus_logger_configure",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Configures all logger settings including output file path, logging duration, "
        + "format options, and file rolling behavior. "
        + "Must be called BEFORE bus_logger_start. "
        + "The logger will write frames to the specified output file "
        + "in either ASC (ASCII) or BLF (Binary Log Format). "
        + "Configuration options include file path and overwrite, duration, "
        + "format options (time axis, bus statistics, continuous ring logging), "
        + "and file rolling (automatic rollover by time or size)."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.LOGGER_MANAGEMENT),
)
async def bus_logger_configure(
    params: BusLoggerConfigureInput,
) -> BusLoggerConfigureResult | ErrorEnvelope:
    return await bus_logging_service.configure_logger(params)


# ── Tool 3 — bus_logger_manage ──────────────────────────────────────────────────


@mcp.tool(
    name="bus_logger_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages bus logger lifecycle operations (mutating only). "
        "Set 'action' to specify what to do: "
        "'start' — activate and start logging (requires logger_name). "
        "Do not call 'start' if the logger is already running — a repeated call returns "
        "an error and does not restart it; call 'stop' first. "
        "'stop' — stop logging and deactivate, flushing buffered frames to disk (requires logger_name). "
        "Use bus_logging_discover to query state or list loggers (bus_logger_query) "
        "and for admin operations (remove, clear_all, set_activated, rename)."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.LOGGER_MANAGEMENT),
)
async def bus_logger_manage(
    params: BusLoggerManageInput,
) -> BusLoggerStartResult | BusLoggerStopResult | ErrorEnvelope:
    if params.action == BusLoggerManageAction.start:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='start'.",
                recovery_hint="Set logger_name to the name of the logger to start.",
            )
        return await bus_logging_service.start_logger(
            BusLoggerStartInput(
                logger_name=params.logger_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    if params.action == BusLoggerManageAction.stop:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='stop'.",
                recovery_hint="Set logger_name to the name of the logger to stop.",
            )
        return await bus_logging_service.stop_logger(
            BusLoggerStopInput(
                logger_name=params.logger_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    return ErrorEnvelope(
        error_code="INVALID_ACTION",
        category="INPUT_VALIDATION",
        message=f"Unknown action '{params.action}' for bus_logger_manage.",
        recovery_hint="Use 'start' or 'stop'.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via bus_logging_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: LOGGER_QUERY ────────────────────────────────────────────────────────────
# ── Tool 4 — bus_logger_query ───────────────────────────────────────────────────


@mcp.tool(
    name="bus_logger_query",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Read-only queries for bus loggers (readOnlyHint=true). "
        "Set 'action' to specify what to do: "
        "'get_state' — query current state (Running/Stopped) and activation status (requires logger_name); "
        "'list' — enumerate all loggers on a physical bus access with pagination. "
        "Use bus_logging_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.LOGGER_MANAGEMENT),
)
async def bus_logger_query(
    params: BusLoggerQueryInput,
) -> BusLoggerGetStateResult | BusLoggerListResult | ErrorEnvelope:
    if params.action == BusLoggerQueryAction.get_state:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='get_state'.",
                recovery_hint="Set logger_name to the name of the logger to query.",
            )
        return await bus_logging_service.get_logger_state(
            BusLoggerGetStateInput(
                logger_name=params.logger_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    # list
    result = await bus_logging_service.list_loggers(
        BusLoggerListInput(
            system_index=params.system_index,
            bus_type=params.bus_type,
            bus_platform_index=params.bus_platform_index,
            physical_bus_access_index=params.physical_bus_access_index,
            limit=params.limit,
            offset=params.offset,
        )
    )
    if isinstance(result, ErrorEnvelope):
        return result
    return BusLoggerListResult(**paginate(result.model_dump(), params.offset, params.limit, "loggers"))


# ── GROUP: LOGGER_ADMIN ────────────────────────────────────────────────────────────
# ── Tool 5 — bus_logger_admin_manage ───────────────────────────────────────────────


@mcp.tool(
    name="bus_logger_admin_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages bus logger administrative operations. "
        "Set 'action' to specify what to do: "
        "'remove' — remove a specific logger (requires logger_name; stop first to avoid data loss); "
        "'clear_all' — remove all loggers from a physical bus access (requires confirm=True; destructive); "
        "'set_activated' — set or clear the Activated flag independently "
        "(requires logger_name and activated); "
        "'rename' — rename an existing logger (requires logger_name and new_name). "
        "Use bus_logger_manage for lifecycle operations (start, stop, get_state, list)."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.LOGGER_MANAGEMENT),
)
async def bus_logger_admin_manage(
    params: BusLoggerAdminManageInput,
) -> (
    BusLoggerRemoveResult
    | BusLoggerClearAllResult
    | BusLoggerClearAllAborted
    | BusLoggerSetActivatedResult
    | BusLoggerRenameResult
    | ErrorEnvelope
):
    if params.action == BusLoggerAdminManageAction.remove:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='remove'.",
                recovery_hint="Set logger_name to the name of the logger to remove.",
            )
        return await bus_logging_service.remove_logger(
            BusLoggerRemoveInput(
                logger_name=params.logger_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    if params.action == BusLoggerAdminManageAction.clear_all:
        return await bus_logging_service.clear_all_loggers(
            BusLoggerClearAllInput(
                system_index=params.system_index,
                bus_type=params.bus_type,
                bus_platform_index=params.bus_platform_index,
                physical_bus_access_index=params.physical_bus_access_index,
                confirm=params.confirm,
            )
        )
    if params.action == BusLoggerAdminManageAction.set_activated:
        if params.logger_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="logger_name is required when action='set_activated'.",
                recovery_hint="Set logger_name to the name of the logger.",
            )
        if params.activated is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="activated is required when action='set_activated'.",
                recovery_hint="Set activated=True to activate or activated=False to deactivate.",
            )
        return await bus_logging_service.set_logger_activated(
            BusLoggerSetActivatedInput(
                logger_name=params.logger_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
                activated=params.activated,
            )
        )
    # rename
    if params.logger_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="logger_name is required when action='rename'.",
            recovery_hint="Set logger_name to the current name of the logger to rename.",
        )
    if params.new_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="new_name is required when action='rename'.",
            recovery_hint="Set new_name to the desired new name for the logger.",
        )
    return await bus_logging_service.rename_logger(
        BusLoggerRenameInput(
            logger_name=params.logger_name,
            new_name=params.new_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
            bus_platform_index=params.bus_platform_index,
            physical_bus_access_index=params.physical_bus_access_index,
        )
    )


# ── GROUP: FILTER_MANAGEMENT ──────────────────────────────────────────────────
# ── Tool 5 — bus_filter_create ────────────────────────────────────────────────


@mcp.tool(
    name="bus_filter_create",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Creates a new message filter on a specified physical bus access. "
        + "Filters selectively pass or block frames "
        + "based on message ID, mask, and direction rules. "
        + "After creation, configure the filter via bus_filter_configure before starting. "
        + "Filter names must be unique within a physical bus access."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.FILTER_MANAGEMENT),
)
async def bus_filter_create(params: BusFilterCreateInput) -> BusFilterCreateResult | ErrorEnvelope:
    return await bus_logging_service.create_filter(params)


# ── Tool 6 — bus_filter_configure ─────────────────────────────────────────────


@mcp.tool(
    name="bus_filter_configure",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Configures filter rules including the filter direction (pass or block) "
        + "and the message ID/mask criteria. "
        + "Filters can include or exclude specific message IDs or ID ranges "
        + "based on an acceptance mask."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.FILTER_MANAGEMENT),
)
async def bus_filter_configure(
    params: BusFilterConfigureInput,
) -> BusFilterConfigureResult | ErrorEnvelope:
    return await bus_logging_service.configure_filter(params)


# ── Tool 7 — bus_filter_manage ────────────────────────────────────────────────


@mcp.tool(
    name="bus_filter_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages bus filter lifecycle operations. "
        "Set 'action' to specify what to do: "
        "'start' — activate and start filtering (requires filter_name); "
        "'stop' — stop filtering and deactivate, restoring unfiltered traffic (requires filter_name); "
        "'list' — enumerate all filters on a physical bus access with pagination; "
        "'remove' — remove a specific filter permanently (requires filter_name). "
        "Use bus_filter_create to create a new filter and bus_filter_configure to set its rules."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.FILTER_MANAGEMENT),
)
async def bus_filter_manage(
    params: BusFilterManageInput,
) -> BusFilterStartResult | BusFilterStopResult | BusFilterListResult | BusFilterRemoveResult | ErrorEnvelope:
    if params.action == BusFilterManageAction.start:
        if params.filter_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="filter_name is required when action='start'.",
                recovery_hint="Set filter_name to the name of the filter to start.",
            )
        return await bus_logging_service.start_filter(
            BusFilterStartInput(
                filter_name=params.filter_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    if params.action == BusFilterManageAction.stop:
        if params.filter_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="filter_name is required when action='stop'.",
                recovery_hint="Set filter_name to the name of the filter to stop.",
            )
        return await bus_logging_service.stop_filter(
            BusFilterStopInput(
                filter_name=params.filter_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    if params.action == BusFilterManageAction.list:
        result = await bus_logging_service.list_filters(
            BusFilterListInput(
                system_index=params.system_index,
                bus_type=params.bus_type,
                bus_platform_index=params.bus_platform_index,
                physical_bus_access_index=params.physical_bus_access_index,
                limit=params.limit,
                offset=params.offset,
            )
        )
        if isinstance(result, ErrorEnvelope):
            return result
        return BusFilterListResult(**paginate(result.model_dump(), params.offset, params.limit, "filters"))
    # remove
    if params.filter_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="filter_name is required when action='remove'.",
            recovery_hint="Set filter_name to the name of the filter to remove.",
        )
    return await bus_logging_service.remove_filter(
        BusFilterRemoveInput(
            filter_name=params.filter_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 8 — bus_logging_discover ────────────────────────────────────────────


@mcp.tool(
    name="bus_logging_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available bus logging operations "
        "that are not loaded by default. Call this tool first when you need to manage "
        "bus logger admin operations (remove, clear_all, set_activated, rename) "
        "or bus message filters. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_LOGGING, ToolGroup.LOGGER_MANAGEMENT),
)
async def bus_logging_discover(ctx: Context) -> BusLoggingDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.BUS_LOGGING, ctx)
    return BusLoggingDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="bus_logger_query",
                purpose="Read-only queries: get logger state (Running/Stopped) or list all loggers on a bus access.",
                actions=["get_state", "list"],
                required_params_per_action={
                    "get_state": ["logger_name", "system_index", "bus_type"],
                    "list": ["system_index", "bus_type"],
                },
            ),
            ToolActionEntry(
                tool_name="bus_logger_admin_manage",
                purpose=("Perform administrative operations on bus loggers: remove, clear_all, set_activated, rename."),
                actions=["remove", "clear_all", "set_activated", "rename"],
                required_params_per_action={
                    "remove": ["logger_name"],
                    "clear_all": ["confirm"],
                    "set_activated": ["logger_name", "activated"],
                    "rename": ["logger_name", "new_name"],
                },
            ),
            ToolActionEntry(
                tool_name="bus_filter_create",
                purpose="Create a new message filter on a physical bus access.",
                actions=["create"],
                required_params_per_action={
                    "create": ["filter_name", "system_index", "bus_type"],
                },
            ),
            ToolActionEntry(
                tool_name="bus_filter_configure",
                purpose="Configure filter rules (pass/block mode and message ID/mask criteria).",
                actions=["configure"],
                required_params_per_action={
                    "configure": ["filter_name", "system_index", "bus_type"],
                },
            ),
            ToolActionEntry(
                tool_name="bus_filter_manage",
                purpose="Manage bus filter lifecycle: start, stop, list, or remove filters.",
                actions=["start", "stop", "list", "remove"],
                required_params_per_action={
                    "start": ["filter_name"],
                    "stop": ["filter_name"],
                    "list": [],
                    "remove": ["filter_name"],
                },
            ),
        ]
    )
