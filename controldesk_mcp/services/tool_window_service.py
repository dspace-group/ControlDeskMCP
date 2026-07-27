"""Service facade for ControlDesk tool window (panel) management operations.

Owns: orchestration of tool window show/hide/dock-state operations.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tool_window import (
    ToolWindowCheckExistsInput,
    ToolWindowCheckExistsResult,
    ToolWindowCloseInput,
    ToolWindowCloseResult,
    ToolWindowGetGeometryInput,
    ToolWindowGetGeometryResult,
    ToolWindowGetStateInput,
    ToolWindowGetStateResult,
    ToolWindowInfo,
    ToolWindowListResult,
    ToolWindowSetDockStateInput,
    ToolWindowSetDockStateResult,
    ToolWindowShowInput,
    ToolWindowShowResult,
)
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _get_app():
    return com_bridge.get_connection().get_app()


async def list_windows() -> ToolWindowListResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        windows = await com_bridge.dispatch(com_bridge.domains.tool_window_com.list_windows, app)
        return ToolWindowListResult(
            total_windows=len(windows),
            windows=[ToolWindowInfo(**w) for w in windows],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("tool_window_list failed: %s", exc)
        return build_envelope(exc)


async def show_window(params: ToolWindowShowInput) -> ToolWindowShowResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.tool_window_com.show_window, app, params.window_name
        )
        return ToolWindowShowResult(
            window_name=params.window_name,
            caption=result["caption"],
            is_now_visible=result["is_now_visible"],
            dock_state=result["dock_state"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("tool_window_show('%s') failed: %s", params.window_name, exc)
        return build_envelope(exc)


async def close_window(params: ToolWindowCloseInput) -> ToolWindowCloseResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.tool_window_com.close_window,
            app,
            params.window_name,
            params.save_layout,
        )
        return ToolWindowCloseResult(
            window_name=params.window_name,
            caption=result["caption"],
            layout_saved=result["layout_saved"],
            is_now_visible=result["is_now_visible"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("tool_window_close('%s') failed: %s", params.window_name, exc)
        return build_envelope(exc)


async def get_window_state(
    params: ToolWindowGetStateInput,
) -> ToolWindowGetStateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.tool_window_com.get_window_state, app, params.window_name
        )
        return ToolWindowGetStateResult(
            window_name=params.window_name,
            caption=result["caption"],
            is_visible=result["is_visible"],
            dock_state=result["dock_state"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("tool_window_get_state('%s') failed: %s", params.window_name, exc)
        return build_envelope(exc)


async def set_window_dock_state(
    params: ToolWindowSetDockStateInput,
) -> ToolWindowSetDockStateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.tool_window_com.set_window_dock_state,
            app,
            params.window_name,
            params.dock_state.value,
        )
        return ToolWindowSetDockStateResult(
            window_name=params.window_name,
            caption=result["caption"],
            dock_state=result["dock_state"],
            is_visible=result["is_visible"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning(
            "tool_window_set_dock_state('%s', '%s') failed: %s",
            params.window_name,
            params.dock_state,
            exc,
        )
        return build_envelope(exc)


async def check_window_exists(
    params: ToolWindowCheckExistsInput,
) -> ToolWindowCheckExistsResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        exists = await com_bridge.dispatch(
            com_bridge.domains.tool_window_com.check_window_exists, app, params.window_name
        )
        return ToolWindowCheckExistsResult(
            window_name=params.window_name,
            exists=exists,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("tool_window_check_exists('%s') failed: %s", params.window_name, exc)
        return build_envelope(exc)


async def get_window_geometry(
    params: ToolWindowGetGeometryInput,
) -> ToolWindowGetGeometryResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.tool_window_com.get_window_geometry, app, params.window_name
        )
        return ToolWindowGetGeometryResult(
            window_name=params.window_name,
            caption=result["caption"],
            left=result["left"],
            top=result["top"],
            width=result["width"],
            height=result["height"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("tool_window_get_geometry('%s') failed: %s", params.window_name, exc)
        return build_envelope(exc)
