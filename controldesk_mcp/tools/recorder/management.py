"""MCP tools for ControlDesk main recorder management.

Tools implemented (domain: recorder):

  MAIN (always loaded):
    recorder_main_start  — Start main recorder (write MF4 file)
    recorder_main_stop   — Stop main recorder and finalize output file
    recorder_main_manage — Combined operations: configure, get_state, invoke_trigger

  ADD_ON lazy (access via recorder_discover):
    GROUP: SIGNAL_MANAGEMENT
      recorder_signal_manage — Signal list operations: add_signal, remove_signal, list_signals
    GROUP: CONFIG_MANAGEMENT
      recorder_config_manage — Export/import recorder config: export, import_signals

  META / Discovery:
    recorder_discover — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.recorder_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.recorder import (
    RecorderConfigManageAction,
    RecorderConfigManageInput,
    RecorderDiscoverResult,
    RecorderMainAddSignalInput,
    RecorderMainAddSignalResult,
    RecorderMainConfigureInput,
    RecorderMainConfigureResult,
    RecorderMainExportInput,
    RecorderMainExportResult,
    RecorderMainGetStateInput,
    RecorderMainGetStateResult,
    RecorderMainImportSignalsInput,
    RecorderMainImportSignalsResult,
    RecorderMainInvokeTriggerInput,
    RecorderMainInvokeTriggerResult,
    RecorderMainListSignalsInput,
    RecorderMainListSignalsResult,
    RecorderMainManageAction,
    RecorderMainManageInput,
    RecorderMainRemoveSignalInput,
    RecorderMainRemoveSignalResult,
    RecorderMainStartInput,
    RecorderMainStartResult,
    RecorderMainStopInput,
    RecorderMainStopResult,
    RecorderQueryInput,
    RecorderSignalManageAction,
    RecorderSignalManageInput,
    ToolActionEntry,
)
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import recorder_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — recorder_main_start ─────────────────────────────────────────────


@mcp.tool(
    name="controldesk_recorder_main_start",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Starts the main recorder. The recorder begins writing sampled signals to the "
        "configured output MF4 file. Use with_trigger=True if trigger-based start/stop "
        "conditions are configured — recording will wait for the start trigger to fire. "
        "Call AFTER measurement_start to ensure buffers are populated and AFTER "
        "recorder_main_manage(action='configure') to set the output filename. "
        "Preconditions: measurement must be running; recorder must be configured. "
        "Do not call if recording is already active — a repeated call returns an error; "
        "call recorder_main_stop first to end the current recording before starting a new one. "
        "Dry-run: set dry_run=True to preview the start — the tool checks whether the "
        "recorder is already running without starting it."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.RECORDER, ToolGroup.RECORDER_MANAGEMENT),
)
async def recorder_main_start(
    params: RecorderMainStartInput,
) -> RecorderMainStartResult | DryRunPreviewResult | ErrorEnvelope:
    if params.dry_run:
        return await recorder_service.dry_run_start_recorder(params)
    return await recorder_service.start_recorder(params)


# ── Tool 2 — recorder_main_stop ──────────────────────────────────────────────


@mcp.tool(
    name="controldesk_recorder_main_stop",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Stops the main recorder. Any open output MF4 file is finalized and closed. "
        "Call this BEFORE measurement_stop to ensure all buffered data is written to disk. "
        "After this call, the output file is complete and ready for analysis. "
        "Preconditions: recording must be active (recorder_main_start was called). "
        "Dry-run: set dry_run=True to preview the stop — the tool checks whether the "
        "recorder is currently running without stopping it."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.RECORDER, ToolGroup.RECORDER_MANAGEMENT),
)
async def recorder_main_stop(
    params: RecorderMainStopInput,
) -> RecorderMainStopResult | DryRunPreviewResult | ErrorEnvelope:
    if params.dry_run:
        return await recorder_service.dry_run_stop_recorder(params)
    return await recorder_service.stop_recorder(params)


# ── Tool 3 — recorder_main_manage ────────────────────────────────────────────


@mcp.tool(
    name="controldesk_recorder_main_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages recorder configuration and trigger (mutating only). "
        "Set 'action' to specify what to do: "
        "'configure' — configure the recorder output filename, sequential naming, and "
        "integration settings (requires base_filename; must be called before start); "
        "'invoke_trigger' — bypass the start trigger and begin recording immediately "
        "(recorder must be in WaitingForTrigger state). "
        "Use recorder_discover to get recorder state (recorder_query) and to access "
        "signal management and export/import operations."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.RECORDER, ToolGroup.RECORDER_MANAGEMENT),
)
async def recorder_main_manage(
    params: RecorderMainManageInput,
) -> RecorderMainConfigureResult | RecorderMainInvokeTriggerResult | ErrorEnvelope:
    action = params.action

    if action == RecorderMainManageAction.configure:
        if params.base_filename is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="base_filename is required for configure.",
                recovery_hint=("Set base_filename to the output MF4 file name (e.g., 'Recording.mf4')."),
            )
        return await recorder_service.configure_main_recorder(
            RecorderMainConfigureInput(
                base_filename=params.base_filename,
                automatic_naming_enabled=params.automatic_naming_enabled,
                automatic_naming_start_index=params.automatic_naming_start_index,
                automatic_naming_minimum_digits=params.automatic_naming_minimum_digits,
                add_to_experiment_enabled=params.add_to_experiment_enabled,
                open_in_data_pool_enabled=params.open_in_data_pool_enabled,
                write_to_file_enabled=params.write_to_file_enabled,
                automatic_signal_configuration_enabled=params.automatic_signal_configuration_enabled,
                description=params.description,
            )
        )

    # invoke_trigger
    return await recorder_service.invoke_trigger(RecorderMainInvokeTriggerInput())


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via recorder_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: RECORDER_QUERY ───────────────────────────────────────────────────────────
# ── Tool 4 — recorder_query ───────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_recorder_query",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Read-only queries for main recorder state (readOnlyHint=true). "
        "'get_state' — get current recorder state (Idling/WaitingForTrigger/Running). "
        "Use recorder_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.RECORDER, ToolGroup.RECORDER_MANAGEMENT),
)
async def recorder_query(params: RecorderQueryInput) -> RecorderMainGetStateResult | ErrorEnvelope:
    return await recorder_service.get_state(RecorderMainGetStateInput())


# ── GROUP: SIGNAL_MANAGEMENT ───────────────────────────────────────────────────────
# ── Tool 5 — recorder_signal_manage ───────────────────────────────────────────────


@mcp.tool(
    name="controldesk_recorder_signal_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages the recorder signal list. "
        "Set 'action' to specify what to do: "
        "'add_signal' — add a signal to the recorder signal list "
        "(requires connection_path; recording must NOT be active); "
        "'remove_signal' — remove a signal from the recorder signal list "
        "(requires connection_path; recording must NOT be active); "
        "'list_signals' — list all signals assigned to the recorder "
        "(paginated; use offset/limit). "
        "Use recorder_main_manage(action='configure') to configure the recorder."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.RECORDER, ToolGroup.RECORDER_MANAGEMENT),
)
async def recorder_signal_manage(
    params: RecorderSignalManageInput,
) -> RecorderMainAddSignalResult | RecorderMainRemoveSignalResult | RecorderMainListSignalsResult | ErrorEnvelope:
    action = params.action

    if action == RecorderSignalManageAction.add_signal:
        if params.connection_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="connection_path is required for add_signal.",
                recovery_hint="Set connection_path to the signal connection path.",
            )
        return await recorder_service.add_signal(RecorderMainAddSignalInput(connection_path=params.connection_path))

    if action == RecorderSignalManageAction.remove_signal:
        if params.connection_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="connection_path is required for remove_signal.",
                recovery_hint="Set connection_path to the signal connection path.",
            )
        return await recorder_service.remove_signal(
            RecorderMainRemoveSignalInput(connection_path=params.connection_path)
        )

    # list_signals
    result = await recorder_service.list_signals(RecorderMainListSignalsInput(offset=params.offset, limit=params.limit))
    if isinstance(result, ErrorEnvelope):
        return result
    return RecorderMainListSignalsResult(**paginate(result.model_dump(), params.offset, params.limit, "signals"))


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via recorder_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: CONFIG_MANAGEMENT ──────────────────────────────────────────────────
# ── Tool 5 — recorder_config_manage ──────────────────────────────────────────


@mcp.tool(
    name="controldesk_recorder_config_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages recorder configuration file export and import. "
        "Set 'action' to specify what to do: "
        "'export' — export the recorder configuration (signal list, settings) to a file "
        "(requires full_path; recorder must NOT be recording); "
        "'import_signals' — import signal definitions from a previously exported configuration "
        "file, replacing the current signal list "
        "(requires full_path; recorder must NOT be recording). "
        "Use recorder_main_manage(action='configure') to configure the recorder for recording."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.RECORDER, ToolGroup.RECORDER_MANAGEMENT),
)
async def recorder_config_manage(
    params: RecorderConfigManageInput,
) -> RecorderMainExportResult | RecorderMainImportSignalsResult | ErrorEnvelope:
    if params.full_path is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="full_path is required for export and import_signals.",
            recovery_hint="Set full_path to the absolute path of the configuration file.",
        )

    if params.action == RecorderConfigManageAction.export:
        return await recorder_service.export_recorder(
            RecorderMainExportInput(
                full_path=params.full_path,
                overwrite_existing=params.overwrite_existing,
            )
        )
    # import_signals
    return await recorder_service.import_signals_from_file(RecorderMainImportSignalsInput(full_path=params.full_path))


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 6 — recorder_discover ───────────────────────────────────────────────


@mcp.tool(
    name="controldesk_recorder_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available recorder operations "
        "that are not loaded by default. Call this tool first when you need to "
        "manage recorder signals or export/import recorder configurations. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.RECORDER, ToolGroup.RECORDER_MANAGEMENT),
)
async def recorder_discover(ctx: Context) -> RecorderDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.RECORDER, ctx)
    return RecorderDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="controldesk_recorder_query",
                purpose="Read-only query for current recorder state (Idling/WaitingForTrigger/Running).",
                actions=["get_state"],
                required_params_per_action={"get_state": []},
            ),
            ToolActionEntry(
                tool_name="controldesk_recorder_signal_manage",
                purpose=(
                    "Add or remove signals from the recorder signal list, or list all currently assigned signals."
                ),
                actions=["add_signal", "remove_signal", "list_signals"],
                required_params_per_action={
                    "add_signal": ["connection_path"],
                    "remove_signal": ["connection_path"],
                    "list_signals": [],
                },
            ),
            ToolActionEntry(
                tool_name="controldesk_recorder_config_manage",
                purpose=(
                    "Export recorder configuration to file or import signals "
                    "from a previously exported configuration file."
                ),
                actions=["export", "import_signals"],
                required_params_per_action={
                    "export": ["full_path"],
                    "import_signals": ["full_path"],
                },
            ),
        ]
    )
