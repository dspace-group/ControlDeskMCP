"""MCP tools for ControlDesk bus monitoring.

Tools implemented (domain: bus monitor):

  MAIN (always loaded):
    bus_monitor_create    — Create a new monitor on a physical bus access
    bus_monitor_configure — Configure monitor display/buffer settings
    bus_monitor_manage    — Lifecycle operations: start, stop, get_state, list, remove,
                            clear_all, rename

  ADD_ON lazy (access via bus_monitor_discover):
    GROUP: MONITOR_MANAGEMENT
      bus_monitor_save      — Save monitor buffer to a log file (with optional time axis)
      bus_monitor_load_data — Load a log file into the monitor buffer

  META / Discovery:
    bus_monitor_discover  — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.bus_monitor_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.bus_monitor import (
    BusMonitorClearAllAborted,
    BusMonitorClearAllInput,
    BusMonitorClearAllResult,
    BusMonitorConfigureInput,
    BusMonitorConfigureResult,
    BusMonitorCreateInput,
    BusMonitorCreateResult,
    BusMonitorDiscoverResult,
    BusMonitorGetStateInput,
    BusMonitorGetStateResult,
    BusMonitorListInput,
    BusMonitorListResult,
    BusMonitorLoadDataInput,
    BusMonitorLoadDataResult,
    BusMonitorManageAction,
    BusMonitorManageInput,
    BusMonitorQueryAction,
    BusMonitorQueryInput,
    BusMonitorRemoveInput,
    BusMonitorRemoveResult,
    BusMonitorRenameInput,
    BusMonitorRenameResult,
    BusMonitorSaveDataInput,
    BusMonitorSaveDataResult,
    BusMonitorSaveDataWithTimeAxisInput,
    BusMonitorSaveDataWithTimeAxisResult,
    BusMonitorSaveInput,
    BusMonitorStartInput,
    BusMonitorStartResult,
    BusMonitorStopInput,
    BusMonitorStopResult,
    ToolActionEntry,
)
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import bus_monitor_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — bus_monitor_create ──────────────────────────────────────────────


@mcp.tool(
    name="bus_monitor_create",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Creates a new bus monitor on a specified physical bus access. "
        + "The monitor will capture and display all bus frames (CAN messages, LIN frames, "
        + "FlexRay frames, or Ethernet packets) on that channel in real-time "
        + "within the BusNavigator instrument. "
        + "After creation, configure the monitor via bus_monitor_configure before starting. "
        + "Monitor names must be unique within a physical bus access. "
        + "Dry-run: set dry_run=True to preview the create — the tool checks whether a "
        + "monitor with that name already exists without creating anything."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_MONITOR, ToolGroup.MONITOR_MANAGEMENT),
)
async def bus_monitor_create(
    params: BusMonitorCreateInput,
) -> BusMonitorCreateResult | DryRunPreviewResult | ErrorEnvelope:
    if params.dry_run:
        return await bus_monitor_service.dry_run_create_monitor(params)
    return await bus_monitor_service.create_monitor(params)


# ── Tool 2 — bus_monitor_configure ───────────────────────────────────────────


@mcp.tool(
    name="bus_monitor_configure",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Configures monitor display and buffering behavior. "
        + "Settings control how frames are captured, buffered, and refreshed "
        + "in the BusNavigator UI. "
        + "Must be called BEFORE bus_monitor_start. "
        + "Configuration options include update rate (ms), buffer size (frames), "
        + "buffer mode (FixedBuffer or RingBuffer), "
        + "and J1939 PGN resolving (CAN only)."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_MONITOR, ToolGroup.MONITOR_MANAGEMENT),
)
async def bus_monitor_configure(
    params: BusMonitorConfigureInput,
) -> BusMonitorConfigureResult | ErrorEnvelope:
    return await bus_monitor_service.configure_monitor(params)


# ── Tool 3 — bus_monitor_manage ──────────────────────────────────────────────


@mcp.tool(
    name="bus_monitor_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages bus monitor lifecycle operations (mutating only). "
        "Set 'action' to specify what to do: "
        "'start' — activate and start monitoring (requires monitor_name). "
        "Do not call 'start' if the monitor is already running — a repeated call returns "
        "an error and does not restart it; call 'stop' first. "
        "'stop' — stop monitoring, frames remain in buffer (requires monitor_name); "
        "'remove' — remove a specific monitor (requires monitor_name; stop first); "
        "'clear_all' — remove all monitors and their buffered data (requires confirm=True; destructive); "
        "'rename' — rename an existing monitor (requires monitor_name and new_name). "
        "Use bus_monitor_discover to query state or list monitors (bus_monitor_query)."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.BUS_MONITOR, ToolGroup.MONITOR_MANAGEMENT),
)
async def bus_monitor_manage(
    params: BusMonitorManageInput,
) -> (
    BusMonitorStartResult
    | BusMonitorStopResult
    | BusMonitorRemoveResult
    | BusMonitorClearAllResult
    | BusMonitorClearAllAborted
    | BusMonitorRenameResult
    | ErrorEnvelope
):
    if params.action == BusMonitorManageAction.start:
        if params.monitor_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="monitor_name is required when action='start'.",
                recovery_hint="Set monitor_name to the name of the monitor to start.",
            )
        return await bus_monitor_service.start_monitor(
            BusMonitorStartInput(
                monitor_name=params.monitor_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    if params.action == BusMonitorManageAction.stop:
        if params.monitor_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="monitor_name is required when action='stop'.",
                recovery_hint="Set monitor_name to the name of the monitor to stop.",
            )
        return await bus_monitor_service.stop_monitor(
            BusMonitorStopInput(
                monitor_name=params.monitor_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    if params.action == BusMonitorManageAction.remove:
        if params.monitor_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="monitor_name is required when action='remove'.",
                recovery_hint="Set monitor_name to the name of the monitor to remove.",
            )
        return await bus_monitor_service.remove_monitor(
            BusMonitorRemoveInput(
                monitor_name=params.monitor_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    if params.action == BusMonitorManageAction.clear_all:
        return await bus_monitor_service.clear_all_monitors(
            BusMonitorClearAllInput(
                system_index=params.system_index,
                bus_type=params.bus_type,
                bus_platform_index=params.bus_platform_index,
                physical_bus_access_index=params.physical_bus_access_index,
                confirm=params.confirm,
            )
        )
    # rename
    if params.monitor_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="monitor_name is required when action='rename'.",
            recovery_hint="Set monitor_name to the current name of the monitor to rename.",
        )
    if params.new_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="new_name is required when action='rename'.",
            recovery_hint="Set new_name to the desired new name for the monitor.",
        )
    return await bus_monitor_service.rename_monitor(
        BusMonitorRenameInput(
            monitor_name=params.monitor_name,
            new_name=params.new_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
            bus_platform_index=params.bus_platform_index,
            physical_bus_access_index=params.physical_bus_access_index,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via bus_monitor_discover
# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via bus_monitor_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: MONITOR_MANAGEMENT ─────────────────────────────────────────────────
# ── GROUP: MONITOR_QUERY ────────────────────────────────────────────────────────────
# ── Tool 4 — bus_monitor_query ───────────────────────────────────────────────────


@mcp.tool(
    name="bus_monitor_query",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Read-only queries for bus monitors (readOnlyHint=true). "
        "Set 'action' to specify what to do: "
        "'get_state' — query current state (Running/Stopped) (requires monitor_name); "
        "'list' — enumerate all monitors on a physical bus access with pagination. "
        "Use bus_monitor_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_MONITOR, ToolGroup.MONITOR_MANAGEMENT),
)
async def bus_monitor_query(
    params: BusMonitorQueryInput,
) -> BusMonitorGetStateResult | BusMonitorListResult | ErrorEnvelope:
    if params.action == BusMonitorQueryAction.get_state:
        if params.monitor_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="monitor_name is required when action='get_state'.",
                recovery_hint="Set monitor_name to the name of the monitor to query.",
            )
        return await bus_monitor_service.get_monitor_state(
            BusMonitorGetStateInput(
                monitor_name=params.monitor_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
            )
        )
    # list
    result = await bus_monitor_service.list_monitors(
        BusMonitorListInput(
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
    return BusMonitorListResult(**paginate(result.model_dump(), params.offset, params.limit, "monitors"))


# ── Tool 5 — bus_monitor_save ────────────────────────────────────────────────────


@mcp.tool(
    name="bus_monitor_save",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Saves the current monitor buffer contents to a log file on disk. "
        "This captures a snapshot of the frames currently in the monitor's buffer "
        "at the time of the call. "
        "The monitor does not need to be stopped to save data. "
        "Optionally provide time_axis to control the time representation: "
        "'Absolute' (UTC wall-clock timestamps), "
        "'Relative' (seconds from start of monitoring), "
        "or 'RecordingTime' (hardware recording time). "
        "When time_axis is omitted, uses default save behavior."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_MONITOR, ToolGroup.MONITOR_MANAGEMENT),
)
async def bus_monitor_save(
    params: BusMonitorSaveInput,
) -> BusMonitorSaveDataResult | BusMonitorSaveDataWithTimeAxisResult | ErrorEnvelope:
    if params.time_axis is not None:
        return await bus_monitor_service.save_monitor_data_with_time_axis(
            BusMonitorSaveDataWithTimeAxisInput(
                monitor_name=params.monitor_name,
                system_index=params.system_index,
                bus_type=params.bus_type,
                output_file_path=params.output_file_path,
                time_axis=params.time_axis,
            )
        )
    return await bus_monitor_service.save_monitor_data(
        BusMonitorSaveDataInput(
            monitor_name=params.monitor_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
            output_file_path=params.output_file_path,
        )
    )


# ── Tool 5 — bus_monitor_load_data ───────────────────────────────────────────


@mcp.tool(
    name="bus_monitor_load_data",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Loads a previously saved log file into the monitor buffer for offline viewing. "
        + "This is the inverse of bus_monitor_save — it reads an existing .asc, .csv, "
        + ".mdf, .mf4, or .pcapng log file and fills the monitor buffer with its contents. "
        + "After loading, the bus frames are visible in the BusNavigator instrument. "
        + "The monitor does not need to be running to load data. "
        + "Use log_file_section=0 for single-session log files; increment for multi-session files."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_MONITOR, ToolGroup.MONITOR_MANAGEMENT),
)
async def bus_monitor_load_data(
    params: BusMonitorLoadDataInput,
) -> BusMonitorLoadDataResult | ErrorEnvelope:
    return await bus_monitor_service.load_monitor_data(params)


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 6 — bus_monitor_discover ────────────────────────────────────────────


@mcp.tool(
    name="bus_monitor_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available bus monitor operations "
        "that are not loaded by default. Call this tool first when you need to save "
        "monitor buffer data to a file or load a log file into a monitor. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.BUS_MONITOR, ToolGroup.MONITOR_MANAGEMENT),
)
async def bus_monitor_discover(ctx: Context) -> BusMonitorDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.BUS_MONITOR, ctx)
    return BusMonitorDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="bus_monitor_query",
                purpose="Read-only queries: get monitor state (Running/Stopped) or list all monitors on a bus access.",
                actions=["get_state", "list"],
                required_params_per_action={
                    "get_state": ["monitor_name", "system_index", "bus_type"],
                    "list": ["system_index", "bus_type"],
                },
            ),
            ToolActionEntry(
                tool_name="bus_monitor_save",
                purpose=(
                    "Save the current monitor buffer contents to a log file on disk. "
                    "Optionally specify a time axis (Absolute, Relative, RecordingTime)."
                ),
                actions=["save"],
                required_params_per_action={
                    "save": ["monitor_name", "system_index", "bus_type", "output_file_path"],
                },
            ),
            ToolActionEntry(
                tool_name="bus_monitor_load_data",
                purpose="Load a previously saved log file into the monitor buffer for offline viewing.",
                actions=["load"],
                required_params_per_action={
                    "load": ["monitor_name", "system_index", "bus_type", "log_file_path"],
                },
            ),
        ]
    )
