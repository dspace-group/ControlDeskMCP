"""MCP tools for ControlDesk application lifecycle.

Tools implemented (domain: application lifecycle):

  MAIN (always loaded):
    start_controldesk — Launch or attach to ControlDesk (entry point for all automation)
    stop_controldesk            — Gracefully shut down ControlDesk
        app_get_logs        — Return available ControlDesk application log file paths

  ADD_ON lazy (access via app_discover):
    GROUP: WINDOW_MANAGEMENT
      app_window_manage — Window visibility, state, position, and fullscreen operations
                          (actions: set_visible, get_visibility, set_state, get_state,
                                    set_position, set_fullscreen)

  META / Discovery:
    app_discover        — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.application_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.application import (
    AppDiscoverResult,
    AppGetLogsInput,
    AppGetLogsResult,
    AppGetWindowStateResult,
    AppGetWindowVisibilityResult,
    AppQuitInput,
    AppQuitResult,
    AppSetFullscreenInput,
    AppSetFullscreenResult,
    AppSetWindowPositionInput,
    AppSetWindowPositionResult,
    AppSetWindowStateInput,
    AppSetWindowStateResult,
    AppSetWindowVisibleInput,
    AppSetWindowVisibleResult,
    AppStartOrAttachInput,
    AppStartOrAttachResult,
    AppVersionConfirmationRequired,
    AppWindowManageAction,
    AppWindowManageInput,
    ToolActionEntry,
)
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import application_service


def _to_dict(data):
    """Normalize service return (BaseModel or dict) to a plain dict."""
    if hasattr(data, "model_dump"):
        return data.model_dump()
    return data


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — start_controldesk ─────────────────────────────────────────────


@mcp.tool(
    name="controldesk_app_start_or_attach",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Starts a new ControlDesk instance or attaches to an existing running instance. "
        + "If ControlDesk is not running, this launches a new process. "
        + "If already running, this returns a handle to the existing application "
        + "without launching a second copy. "
        + "This is the entry point for all ControlDesk automation. "
        + "All other tools depend on a successful call to this tool first. "
        + "WARNING: if force_version_switch=True and a different ControlDesk version "
        + "is already running, this quits the running instance (discarding unsaved "
        + "work) before starting the requested version. "
        + "Dry-run: set dry_run=True to preview whether a forced version switch would "
        + "be needed and whether the active project has unsaved changes, without "
        + "quitting or launching anything."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=True),
    meta=MetaInfo(ToolDomain.APPLICATION, ToolGroup.LIFECYCLE),
)
async def start_controldesk(
    params: AppStartOrAttachInput,
) -> AppStartOrAttachResult | AppVersionConfirmationRequired | DryRunPreviewResult | ErrorEnvelope:
    if params.dry_run:
        data = await application_service.dry_run_start_or_attach(params)
        data_dict = _to_dict(data)
        if "error_code" in data_dict:
            return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
        return DryRunPreviewResult(**data_dict)
    data = await application_service.start_or_attach(params)
    data_dict = _to_dict(data)
    if "error_code" in data_dict:
        return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
    if data_dict.get("status") == "confirmation_required":
        return AppVersionConfirmationRequired(**data_dict)
    return AppStartOrAttachResult(**data_dict)


# ── Tool 2 — stop_controldesk ────────────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_app_stop",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Gracefully shuts down the ControlDesk application. "
        + "All windows are closed, COM objects are released, "
        + "and the ControlDesk process terminates. "
        + "Optionally saves all open projects before shutting down. "
        + "Dry-run: set dry_run=True to preview the shutdown — the tool checks whether the "
        + "active project has unsaved changes and reports the impact of save_all_projects "
        + "without quitting ControlDesk."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.APPLICATION, ToolGroup.LIFECYCLE),
)
async def stop_controldesk(
    params: AppQuitInput,
) -> AppQuitResult | DryRunPreviewResult | ErrorEnvelope:
    if params.dry_run:
        data = await application_service.dry_run_quit_application(params)
        data_dict = _to_dict(data)
        if "error_code" in data_dict:
            return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
        return DryRunPreviewResult(**data_dict)
    data = await application_service.quit_application(params)
    data_dict = _to_dict(data)
    if "error_code" in data_dict:
        return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
    return AppQuitResult(**data_dict)


# ── Tool 3 — app_get_logs ───────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_app_get_logs",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Returns available ControlDesk application log file paths for diagnostics. "
        "Use this when a tool call failed, timed out, or ControlDesk crashed and you "
        "need to inspect what happened in ControlDesk logs. "
        "By default, this searches ControlDesk-compatible log folders under LOCALAPPDATA "
        "and returns files matching ControlDesk*.log."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.APPLICATION, ToolGroup.LIFECYCLE),
)
async def app_get_logs(params: AppGetLogsInput) -> AppGetLogsResult | ErrorEnvelope:
    data = await application_service.get_logs(params)
    data_dict = _to_dict(data)
    if "error_code" in data_dict:
        return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
    return AppGetLogsResult(**data_dict)


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via app_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 4 — app_window_manage ───────────────────────────────────────────────


@mcp.tool(
    name="controldesk_app_window_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages ControlDesk main window operations. "
        "Set 'action' to specify what to do: "
        "'set_visible' — show or hide the window (requires visible); "
        "'get_visibility' — query whether the window is currently visible; "
        "'set_state' — set display state Normal/Maximized/Minimized/Hidden (requires window_state); "
        "'get_state' — query current display state; "
        "'set_position' — position and resize the window in pixels "
        "(requires left, top, width, height); "
        "'set_fullscreen' — enable or disable full-screen mode (requires enabled). "
        "Full-screen differs from Maximized: full-screen removes the window frame entirely."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.APPLICATION, ToolGroup.WINDOW_MANAGEMENT),
)
async def app_window_manage(
    params: AppWindowManageInput,
) -> (
    AppSetWindowVisibleResult
    | AppGetWindowVisibilityResult
    | AppSetWindowStateResult
    | AppGetWindowStateResult
    | AppSetWindowPositionResult
    | AppSetFullscreenResult
    | ErrorEnvelope
):
    if params.action == AppWindowManageAction.set_visible:
        if params.visible is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="visible is required when action='set_visible'.",
                recovery_hint="Set visible=True to show the window or visible=False to hide it.",
            )
        data = await application_service.set_window_visible(AppSetWindowVisibleInput(visible=params.visible))
        data_dict = _to_dict(data)
        if "error_code" in data_dict:
            return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
        return AppSetWindowVisibleResult(**data_dict)

    if params.action == AppWindowManageAction.get_visibility:
        data = await application_service.get_window_visibility()
        data_dict = _to_dict(data)
        if "error_code" in data_dict:
            return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
        return AppGetWindowVisibilityResult(**data_dict)

    if params.action == AppWindowManageAction.set_state:
        if params.window_state is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="window_state is required when action='set_state'.",
                recovery_hint="Set window_state to one of: Normal, Maximized, Minimized, Hidden.",
            )
        data = await application_service.set_window_state(AppSetWindowStateInput(window_state=params.window_state))
        data_dict = _to_dict(data)
        if "error_code" in data_dict:
            return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
        return AppSetWindowStateResult(**data_dict)

    if params.action == AppWindowManageAction.get_state:
        data = await application_service.get_window_state()
        data_dict = _to_dict(data)
        if "error_code" in data_dict:
            return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
        return AppGetWindowStateResult(**data_dict)

    if params.action == AppWindowManageAction.set_position:
        for field_name in ("left", "top", "width", "height"):
            if getattr(params, field_name) is None:
                return ErrorEnvelope(
                    error_code="MISSING_PARAM",
                    category="INPUT_VALIDATION",
                    message=f"{field_name} is required when action='set_position'.",
                    recovery_hint=f"Set {field_name} to the desired pixel value.",
                )
        data = await application_service.set_window_position(
            AppSetWindowPositionInput(
                left=params.left,
                top=params.top,
                width=params.width,
                height=params.height,
            )
        )
        data_dict = _to_dict(data)
        if "error_code" in data_dict:
            return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
        return AppSetWindowPositionResult(**data_dict)

    # set_fullscreen
    if params.enabled is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="enabled is required when action='set_fullscreen'.",
            recovery_hint="Set enabled=True to enable full-screen or enabled=False to disable.",
        )
    data = await application_service.set_fullscreen(AppSetFullscreenInput(enabled=params.enabled))
    data_dict = _to_dict(data)
    if "error_code" in data_dict:
        return ErrorEnvelope(**{k: v for k, v in data_dict.items() if k != "markdown"})
    return AppSetFullscreenResult(**data_dict)


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 5 — app_discover ────────────────────────────────────────────────────


@mcp.tool(
    name="controldesk_app_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available application management operations "
        "that are not loaded by default. Call this tool first when you need to manage "
        "the ControlDesk window (visibility, state, position, or full-screen). "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.APPLICATION, ToolGroup.LIFECYCLE),
)
async def app_discover(ctx: Context) -> AppDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.APPLICATION, ctx)
    return AppDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="controldesk_app_window_manage",
                purpose="Manage ControlDesk main window: visibility, state, position, fullscreen.",
                actions=[
                    "set_visible",
                    "get_visibility",
                    "set_state",
                    "get_state",
                    "set_position",
                    "set_fullscreen",
                ],
                required_params_per_action={
                    "set_visible": ["visible"],
                    "get_visibility": [],
                    "set_state": ["window_state"],
                    "get_state": [],
                    "set_position": ["left", "top", "width", "height"],
                    "set_fullscreen": ["enabled"],
                },
            ),
        ]
    )
