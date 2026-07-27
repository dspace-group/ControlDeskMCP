"""MCP tools for ControlDesk bus replay.

Tools implemented (domain: bus replay):

  MAIN (always loaded):
    bus_replay_create    — Create a new bus replay on a physical bus access
    bus_replay_configure — Configure replay settings (file, mode, duration)
    bus_replay_manage    — Lifecycle operations: start, stop, get_state, list

  ADD_ON lazy (access via bus_replay_discover):
    bus_replay_admin_manage — Admin operations: remove, clear_all, set_activated, rename

  META / Discovery:
    bus_replay_discover  — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.bus_replay_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.bus_replay import (
    BusReplayAdminManageAction,
    BusReplayAdminManageInput,
    BusReplayClearAllAborted,
    BusReplayClearAllInput,
    BusReplayClearAllResult,
    BusReplayConfigureInput,
    BusReplayConfigureResult,
    BusReplayCreateInput,
    BusReplayCreateResult,
    BusReplayDiscoverResult,
    BusReplayGetStateInput,
    BusReplayGetStateResult,
    BusReplayListInput,
    BusReplayListResult,
    BusReplayManageAction,
    BusReplayManageInput,
    BusReplayQueryAction,
    BusReplayQueryInput,
    BusReplayRemoveInput,
    BusReplayRemoveResult,
    BusReplayRenameInput,
    BusReplayRenameResult,
    BusReplaySetActivatedInput,
    BusReplaySetActivatedResult,
    BusReplayStartInput,
    BusReplayStartResult,
    BusReplayStopInput,
    BusReplayStopResult,
    BusReplayToolActionEntry,
)
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import bus_replay_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — bus_replay_create ──────────────────────────────────────────────────


@mcp.tool(
    name="bus_replay_create",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Creates a new bus replay on a specified physical bus access. "
        + "The replay will transmit previously recorded bus frames (from a log file) onto the bus. "
        + "After creation, configure the replay via bus_replay_configure before starting. "
        + "Replay names must be unique within a physical bus access. "
        + "Dry-run: set dry_run=True to preview the create — the tool checks whether a "
        + "replay with that name already exists without creating anything."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_REPLAY, ToolGroup.REPLAY_MANAGEMENT),
)
async def bus_replay_create(
    params: BusReplayCreateInput,
) -> BusReplayCreateResult | DryRunPreviewResult | ErrorEnvelope:
    if params.dry_run:
        return await bus_replay_service.dry_run_create_replay(params)
    return await bus_replay_service.create_replay(params)


# ── Tool 2 — bus_replay_configure ───────────────────────────────────────────────


@mcp.tool(
    name="bus_replay_configure",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Configures all replay settings including source log file path, replay mode "
        + "(Infinite/NumberOfPasses/Duration), and mode-specific parameters. "
        + "Must be called BEFORE bus_replay_start. "
        + "The replay will read frames from the specified log file (ASC or BLF format) "
        + "and transmit them onto the bus according to the selected mode."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_REPLAY, ToolGroup.REPLAY_MANAGEMENT),
)
async def bus_replay_configure(
    params: BusReplayConfigureInput,
) -> BusReplayConfigureResult | ErrorEnvelope:
    return await bus_replay_service.configure_replay(params)


# ── Tool 3 — bus_replay_manage ──────────────────────────────────────────────────


@mcp.tool(
    name="bus_replay_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages bus replay lifecycle operations (mutating only). "
        "Set 'action' to specify what to do: "
        "'start' — activate and start replay (requires replay_name). "
        "Do not call 'start' if the replay is already running — a repeated call returns "
        "an error and does not restart it; call 'stop' first. "
        "'stop' — stop and deactivate replay, ceasing frame transmission (requires replay_name). "
        "Use bus_replay_discover to query state or list replays (bus_replay_query) and for "
        "admin operations (remove, clear_all, set_activated, rename)."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_REPLAY, ToolGroup.REPLAY_MANAGEMENT),
)
async def bus_replay_manage(
    params: BusReplayManageInput,
) -> BusReplayStartResult | BusReplayStopResult | ErrorEnvelope:
    if params.action == BusReplayManageAction.start:
        if params.replay_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="replay_name is required when action='start'.",
                recovery_hint="Set replay_name to the name of the replay to start.",
            )
        return await bus_replay_service.start_replay(
            BusReplayStartInput(
                replay_name=params.replay_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
                bus_platform_index=params.bus_platform_index,
                physical_bus_access_index=params.physical_bus_access_index,
            )
        )
    # stop is the only remaining action
    if params.replay_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="replay_name is required when action='stop'.",
            recovery_hint="Set replay_name to the name of the replay to stop.",
        )
    return await bus_replay_service.stop_replay(
        BusReplayStopInput(
            replay_name=params.replay_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
            bus_platform_index=params.bus_platform_index,
            physical_bus_access_index=params.physical_bus_access_index,
        )
    )


# ── GROUP: REPLAY_QUERY ────────────────────────────────────────────────────────────
# ── Tool 4 — bus_replay_query ───────────────────────────────────────────────────


@mcp.tool(
    name="bus_replay_query",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Read-only queries for bus replays (readOnlyHint=true). "
        "Set 'action' to specify what to do: "
        "'get_state' — query current state (Running/Stopped) and activation status (requires replay_name); "
        "'list' — enumerate all replays on a physical bus access with pagination. "
        "Use bus_replay_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_REPLAY, ToolGroup.REPLAY_MANAGEMENT),
)
async def bus_replay_query(
    params: BusReplayQueryInput,
) -> BusReplayGetStateResult | BusReplayListResult | ErrorEnvelope:
    if params.action == BusReplayQueryAction.get_state:
        if params.replay_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="replay_name is required when action='get_state'.",
                recovery_hint="Set replay_name to the name of the replay to query.",
            )
        return await bus_replay_service.get_replay_state(
            BusReplayGetStateInput(
                replay_name=params.replay_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
                bus_platform_index=params.bus_platform_index,
                physical_bus_access_index=params.physical_bus_access_index,
            )
        )
    # list
    result = await bus_replay_service.list_replays(
        BusReplayListInput(
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
    return BusReplayListResult(
        **paginate(result.model_dump(), params.offset, params.limit, "replays")
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON tools — lazy-loaded, access via bus_replay_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 4 — bus_replay_admin_manage ───────────────────────────────────────────


@mcp.tool(
    name="bus_replay_admin_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Performs administrative operations on bus replays. "
        "Set 'action' to specify what to do: "
        "'remove' — remove a specific replay (requires replay_name; stop first); "
        "'clear_all' — remove all replays from a physical bus access (requires confirm=True; ⚠️ destructive); "
        "'set_activated' — set or clear the Activated flag independently (requires replay_name and activated); "
        "'rename' — rename an existing replay (requires replay_name and new_name). "
        "For lifecycle operations (start, stop, get_state, list) use bus_replay_manage."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_REPLAY, ToolGroup.REPLAY_MANAGEMENT),
)
async def bus_replay_admin_manage(
    params: BusReplayAdminManageInput,
) -> (
    BusReplayRemoveResult
    | BusReplayClearAllResult
    | BusReplayClearAllAborted
    | BusReplaySetActivatedResult
    | BusReplayRenameResult
    | ErrorEnvelope
):
    if params.action == BusReplayAdminManageAction.remove:
        if params.replay_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="replay_name is required when action='remove'.",
                recovery_hint="Set replay_name to the name of the replay to remove.",
            )
        return await bus_replay_service.remove_replay(
            BusReplayRemoveInput(
                replay_name=params.replay_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
                bus_platform_index=params.bus_platform_index,
                physical_bus_access_index=params.physical_bus_access_index,
            )
        )
    if params.action == BusReplayAdminManageAction.clear_all:
        return await bus_replay_service.clear_all_replays(
            BusReplayClearAllInput(
                system_index=params.system_index,
                bus_type=params.bus_type,
                bus_platform_index=params.bus_platform_index,
                physical_bus_access_index=params.physical_bus_access_index,
                confirm=params.confirm,
            )
        )
    if params.action == BusReplayAdminManageAction.set_activated:
        if params.replay_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="replay_name is required when action='set_activated'.",
                recovery_hint="Set replay_name to the name of the replay.",
            )
        if params.activated is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="activated is required when action='set_activated'.",
                recovery_hint="Set activated=True to activate or activated=False to deactivate.",
            )
        return await bus_replay_service.set_replay_activated(
            BusReplaySetActivatedInput(
                replay_name=params.replay_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
                activated=params.activated,
                bus_platform_index=params.bus_platform_index,
                physical_bus_access_index=params.physical_bus_access_index,
            )
        )
    # rename
    if params.replay_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="replay_name is required when action='rename'.",
            recovery_hint="Set replay_name to the current name of the replay to rename.",
        )
    if params.new_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="new_name is required when action='rename'.",
            recovery_hint="Set new_name to the desired new name for the replay.",
        )
    return await bus_replay_service.rename_replay(
        BusReplayRenameInput(
            replay_name=params.replay_name,
            new_name=params.new_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
            bus_platform_index=params.bus_platform_index,
            physical_bus_access_index=params.physical_bus_access_index,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 5 — bus_replay_discover ───────────────────────────────────────────────


@mcp.tool(
    name="bus_replay_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available bus replay operations "
        "that are not loaded by default. Call this tool first when you need to perform "
        "admin operations on bus replays (remove, clear_all, set_activated, rename). "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_REPLAY, ToolGroup.REPLAY_MANAGEMENT),
)
async def bus_replay_discover(ctx: Context) -> BusReplayDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.BUS_REPLAY, ctx)
    return BusReplayDiscoverResult(
        tools=[
            BusReplayToolActionEntry(
                tool_name="bus_replay_query",
                purpose="Read-only queries: get replay state (Running/Stopped) or list all replays on a bus access.",
                actions=["get_state", "list"],
                required_params_per_action={
                    "get_state": ["replay_name", "system_index", "bus_type"],
                    "list": ["system_index", "bus_type"],
                },
            ),
            BusReplayToolActionEntry(
                tool_name="bus_replay_admin_manage",
                purpose=(
                    "Perform administrative operations on bus replays: "
                    "remove, clear_all, set_activated, rename."
                ),
                actions=["remove", "clear_all", "set_activated", "rename"],
                required_params_per_action={
                    "remove": ["replay_name"],
                    "clear_all": ["confirm"],
                    "set_activated": ["replay_name", "activated"],
                    "rename": ["replay_name", "new_name"],
                },
            ),
        ]
    )
