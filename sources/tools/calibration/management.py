"""MCP tools for ControlDesk online calibration.

Tools implemented (domain: online calibration):

  MAIN (always loaded):
    calibration_start  — Start online calibration on all platforms
    calibration_stop   — Stop online calibration on all platforms
    calibration_manage — Mutating page operations: activate_reference_page,
                         activate_working_page, refresh_parameters

  ADD_ON lazy (access via calibration_discover):
    GROUP: CALIBRATION_QUERY
      calibration_query   — Read-only state query: get_state

    GROUP: PROPOSED_CALIBRATION
      proposed_calibration_manage — Proposed calibration lifecycle: start, stop, apply, cancel

    GROUP: PAGE_MANAGEMENT
      calibration_page_manage — Page copy operations: copy_working_to_reference,
                                copy_reference_to_working

  META / Discovery:
    calibration_discover — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to sources.services.calibration_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from sources.config.settings import get_settings
from sources.models.base import DryRunPreviewResult
from sources.models.calibration import (
    CalibrationActivateReferencePageInput,
    CalibrationActivateReferencePageResult,
    CalibrationActivateWorkingPageInput,
    CalibrationActivateWorkingPageResult,
    CalibrationCopyReferencePageToWorkingInput,
    CalibrationCopyReferencePageToWorkingResult,
    CalibrationCopyWorkingPageToReferenceInput,
    CalibrationCopyWorkingPageToReferenceResult,
    CalibrationDiscoverResult,
    CalibrationGetStateInput,
    CalibrationGetStateResult,
    CalibrationManageAction,
    CalibrationManageInput,
    CalibrationPageManageAction,
    CalibrationPageManageInput,
    CalibrationQueryInput,
    CalibrationRefreshParametersInput,
    CalibrationRefreshParametersResult,
    CalibrationStartInput,
    CalibrationStartResult,
    CalibrationStopInput,
    CalibrationStopResult,
    ProposedCalibrationApplyInput,
    ProposedCalibrationApplyResult,
    ProposedCalibrationCancelInput,
    ProposedCalibrationCancelResult,
    ProposedCalibrationManageAction,
    ProposedCalibrationManageInput,
    ProposedCalibrationStartInput,
    ProposedCalibrationStartResult,
    ProposedCalibrationStopInput,
    ProposedCalibrationStopResult,
    ToolActionEntry,
)
from sources.models.errors import ErrorEnvelope
from sources.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from sources.server.app import mcp
from sources.server.server import MCPToolCategory
from sources.services import calibration_service

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — calibration_start ───────────────────────────────────────────────────


@mcp.tool(
    name="calibration_start",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Starts online calibration on all platforms in the active experiment simultaneously. "
        "Online calibration is the mode in which ControlDesk actively communicates with "
        "connected ECUs and enables live reading and writing of calibration parameters on "
        "the working page. This is a mandatory prerequisite before any variable read/write "
        "operation can be performed. "
        "Call platform_connect first to confirm at least one platform has connection state "
        "Connected. Do not call this tool if online calibration is already running — call "
        "calibration_stop first. "
        "Dry-run: set dry_run=True to preview the start — the tool checks whether online "
        "calibration is already running without starting it."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.CALIBRATION, ToolGroup.ONLINE_CALIBRATION),
)
async def calibration_start(
    params: CalibrationStartInput,
) -> CalibrationStartResult | DryRunPreviewResult | ErrorEnvelope:
    if params.dry_run:
        return await calibration_service.dry_run_start_calibration(params)
    return await calibration_service.start_calibration(params)


# ── Tool 2 — calibration_stop ────────────────────────────────────────────────────


@mcp.tool(
    name="calibration_stop",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Stops online calibration on all platforms in the active experiment. "
        "After this call, variable read/write operations are no longer possible until "
        "calibration_start is called again. "
        "Call this tool before platform_disconnect and before closing the project. "
        "It is safe to call even when measurement is still running — ControlDesk stops "
        "measurement automatically when calibration is stopped."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.CALIBRATION, ToolGroup.ONLINE_CALIBRATION),
)
async def calibration_stop(params: CalibrationStopInput) -> CalibrationStopResult | ErrorEnvelope:
    return await calibration_service.stop_calibration(params)


# ── Tool 3 — calibration_manage ──────────────────────────────────────────────────


@mcp.tool(
    name="calibration_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages calibration page operations (mutating only). "
        "Set 'action' to specify what to do: "
        "'activate_reference_page' — switch all platforms to the ECU reference (flash) page "
        "(read-only baseline; calibration must be running); "
        "'activate_working_page' — switch all platforms back to the ECU working (RAM) page "
        "to re-enable parameter writes (calibration must be running); "
        "'refresh_parameters' — re-upload all ECU parameter values from the ECU to ControlDesk "
        "(calibration must be running; does not write to ECU). "
        "Use calibration_discover to query calibration state (calibration_query). "
        "Use calibration_start/stop to control online calibration."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.CALIBRATION, ToolGroup.ONLINE_CALIBRATION),
)
async def calibration_manage(
    params: CalibrationManageInput,
) -> (
    CalibrationActivateReferencePageResult
    | CalibrationActivateWorkingPageResult
    | CalibrationRefreshParametersResult
    | ErrorEnvelope
):
    if params.action == CalibrationManageAction.activate_reference_page:
        return await calibration_service.activate_reference_page(
            CalibrationActivateReferencePageInput()
        )
    if params.action == CalibrationManageAction.activate_working_page:
        return await calibration_service.activate_working_page(
            CalibrationActivateWorkingPageInput()
        )
    # refresh_parameters
    return await calibration_service.refresh_parameters(CalibrationRefreshParametersInput())


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via calibration_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: CALIBRATION_QUERY ───────────────────────────────────────────────────────
# ── Tool 4 — calibration_query ───────────────────────────────────────────────────


@mcp.tool(
    name="calibration_query",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Read-only queries for online calibration state (readOnlyHint=true). "
        "'get_state' — query current online calibration state (Started/Stopped) and "
        "proposed calibration state (Active/Inactive). "
        "Use calibration_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.CALIBRATION, ToolGroup.ONLINE_CALIBRATION),
)
async def calibration_query(
    params: CalibrationQueryInput,
) -> CalibrationGetStateResult | ErrorEnvelope:
    return await calibration_service.get_calibration_state(CalibrationGetStateInput())


# ── GROUP: PROPOSED_CALIBRATION ─────────────────────────────────────────────────────
# ── Tool 5 — proposed_calibration_manage ─────────────────────────────────────────────


@mcp.tool(
    name="proposed_calibration_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages proposed calibration session lifecycle. "
        "Set 'action' to specify what to do: "
        "'start' — begin a proposed calibration session; parameter writes are buffered "
        "locally and not sent to the ECU until applied (calibration must be running, "
        "no session must be active); "
        "'stop' — stop the proposed session without applying staged changes; all buffered "
        "changes are discarded (equivalent to rollback); "
        "'apply' — commit all staged parameter changes to the ECU working page "
        "(irreversible within session; at least one change must be staged); "
        "'cancel' — cancel the proposed session and revert all staged changes, restoring "
        "the ECU working page to pre-session values. "
        "Always pair start with either apply or cancel."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.CALIBRATION, ToolGroup.PROPOSED_CALIBRATION),
)
async def proposed_calibration_manage(
    params: ProposedCalibrationManageInput,
) -> (
    ProposedCalibrationStartResult
    | ProposedCalibrationStopResult
    | ProposedCalibrationApplyResult
    | ProposedCalibrationCancelResult
    | ErrorEnvelope
):
    if params.action == ProposedCalibrationManageAction.start:
        return await calibration_service.start_proposed_calibration(ProposedCalibrationStartInput())
    if params.action == ProposedCalibrationManageAction.stop:
        return await calibration_service.stop_proposed_calibration(ProposedCalibrationStopInput())
    if params.action == ProposedCalibrationManageAction.apply:
        return await calibration_service.apply_proposed_calibration(ProposedCalibrationApplyInput())
    # cancel
    return await calibration_service.cancel_proposed_calibration(ProposedCalibrationCancelInput())


# ── GROUP: PAGE_MANAGEMENT ────────────────────────────────────────────────────
# ── Tool 5 — calibration_page_manage ─────────────────────────────────────────


@mcp.tool(
    name="calibration_page_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages ECU calibration page copy operations (requires platform_name). "
        "Set 'action' to specify what to do: "
        "'copy_working_to_reference' — copy the working (RAM) page values to the reference "
        "(flash) page, making current tuned values the new baseline "
        "(calibration and measurement must be STOPPED); "
        "'copy_reference_to_working' — copy the reference (flash) page values back to the "
        "working (RAM) page, reverting all live edits to the factory baseline "
        "(calibration and measurement must be STOPPED). "
        "The platform must remain connected to the ECU for both operations."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.CALIBRATION, ToolGroup.PAGE_MANAGEMENT),
)
async def calibration_page_manage(
    params: CalibrationPageManageInput,
) -> (
    CalibrationCopyWorkingPageToReferenceResult
    | CalibrationCopyReferencePageToWorkingResult
    | ErrorEnvelope
):
    if params.platform_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="platform_name is required for page copy operations.",
            recovery_hint="Set platform_name to the name of the platform to copy pages for.",
        )
    if params.action == CalibrationPageManageAction.copy_working_to_reference:
        return await calibration_service.copy_working_page_to_reference(
            CalibrationCopyWorkingPageToReferenceInput(platform_name=params.platform_name)
        )
    # copy_reference_to_working
    return await calibration_service.copy_reference_page_to_working(
        CalibrationCopyReferencePageToWorkingInput(platform_name=params.platform_name)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 6 — calibration_discover ────────────────────────────────────────────


@mcp.tool(
    name="calibration_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available calibration operations "
        "that are not loaded by default. Call this tool first when you need to manage "
        "proposed calibration sessions or perform ECU page copy operations. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.CALIBRATION, ToolGroup.ONLINE_CALIBRATION),
)
async def calibration_discover(ctx: Context) -> CalibrationDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.CALIBRATION, ctx)
    return CalibrationDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="calibration_query",
                purpose="Read-only query for current calibration state (Started/Stopped) and proposed session state.",
                actions=["get_state"],
                required_params_per_action={"get_state": []},
            ),
            ToolActionEntry(
                tool_name="proposed_calibration_manage",
                purpose=(
                    "Manage proposed calibration session lifecycle: "
                    "start, stop, apply, or cancel a proposed session."
                ),
                actions=["start", "stop", "apply", "cancel"],
                required_params_per_action={
                    "start": [],
                    "stop": [],
                    "apply": [],
                    "cancel": [],
                },
            ),
            ToolActionEntry(
                tool_name="calibration_page_manage",
                purpose=(
                    "Copy ECU calibration pages: working-to-reference or "
                    "reference-to-working (requires platform_name)."
                ),
                actions=["copy_working_to_reference", "copy_reference_to_working"],
                required_params_per_action={
                    "copy_working_to_reference": ["platform_name"],
                    "copy_reference_to_working": ["platform_name"],
                },
            ),
        ]
    )
