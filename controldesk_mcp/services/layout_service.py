"""Service facade for ControlDesk layout management operations.

Owns: orchestration of layout lifecycle — create, open, save, close, activate,
      configure, export, import, and connection file I/O.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.layout import (
    LayoutActivateResult,
    LayoutCloseResult,
    LayoutConfigureResult,
    LayoutCreateResult,
    LayoutExportConnectionFileResult,
    LayoutExportResult,
    LayoutGetInfoResult,
    LayoutImportConnectionFileResult,
    LayoutImportResult,
    LayoutInfo,
    LayoutListResult,
    LayoutOpenResult,
    LayoutSaveResult,
)
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _get_app():
    return com_bridge.get_connection().get_app()


# ── layout_list ───────────────────────────────────────────────────────────────


async def layout_list() -> LayoutListResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        layouts = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_list, app)
        return LayoutListResult(
            total_layouts=len(layouts),
            layouts=[LayoutInfo(**lay) for lay in layouts],
        )
    except BridgeError as exc:
        _log.warning("layout_list failed: %s", exc)
        return build_envelope(exc)


# ── layout_create ──────────────────────────────────────────────────────────────


async def layout_create(name: str) -> LayoutCreateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_create, app, name)
        return LayoutCreateResult(
            created=True,
            name=result["name"],
            file_path=result["file_path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_create('%s') failed: %s", name, exc)
        return build_envelope(exc)


# ── layout_open ───────────────────────────────────────────────────────────────


async def layout_open(name: str) -> LayoutOpenResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_open, app, name)
        return LayoutOpenResult(
            opened=True,
            name=result["name"],
            file_path=result["file_path"],
            editing_mode=result["editing_mode"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_open('%s') failed: %s", name, exc)
        return build_envelope(exc)


# ── layout_save ───────────────────────────────────────────────────────────────


async def layout_save(name: str) -> LayoutSaveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_save, app, name)
        return LayoutSaveResult(
            saved=True,
            name=result["name"],
            file_path=result["file_path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_save('%s') failed: %s", name, exc)
        return build_envelope(exc)


# ── layout_close ──────────────────────────────────────────────────────────────


async def layout_close(name: str, save_before_close: bool) -> LayoutCloseResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_close, app, name, save_before_close)
        return LayoutCloseResult(
            closed=True,
            name=result["name"],
            saved_before_close=result["saved_before_close"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_close('%s') failed: %s", name, exc)
        return build_envelope(exc)


# ── layout_activate ────────────────────────────────────────────────────────────


async def layout_activate(name: str) -> LayoutActivateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_activate, app, name)
        return LayoutActivateResult(
            activated=True,
            name=result["name"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_activate('%s') failed: %s", name, exc)
        return build_envelope(exc)


# ── layout_get_info ────────────────────────────────────────────────────────────


async def layout_get_info(name: str) -> LayoutGetInfoResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_get_info, app, name)
        return LayoutGetInfoResult(
            name=result["name"],
            file_path=result["file_path"],
            is_open=result["is_open"],
            is_active=result["is_active"],
            editing_mode=result["editing_mode"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_get_info('%s') failed: %s", name, exc)
        return build_envelope(exc)


# ── layout_configure ───────────────────────────────────────────────────────────


async def layout_configure(name: str, editing_mode: str) -> LayoutConfigureResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_configure, app, name, editing_mode)
        return LayoutConfigureResult(
            configured=True,
            name=result["name"],
            editing_mode=result["editing_mode"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_configure('%s', '%s') failed: %s", name, editing_mode, exc)
        return build_envelope(exc)


# ── layout_export ───────────────────────────────────────────────────────────────


async def layout_export(export_path: str) -> LayoutExportResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_export, app, export_path)
        return LayoutExportResult(
            exported=True,
            layout_name=result["layout_name"],
            export_path=result["export_path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_export('%s') failed: %s", export_path, exc)
        return build_envelope(exc)


# ── layout_import ───────────────────────────────────────────────────────────────


async def layout_import(import_path: str) -> LayoutImportResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.layout_com.layout_import, app, import_path)
        return LayoutImportResult(
            imported=True,
            layout_name=result["layout_name"],
            import_path=result["import_path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_import('%s') failed: %s", import_path, exc)
        return build_envelope(exc)


# ── layout_import_connection_file ───────────────────────────────────────────────


async def layout_import_connection_file(
    connection_file_path: str,
) -> LayoutImportConnectionFileResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.layout_com.layout_import_connection_file,
            app,
            connection_file_path,
        )
        return LayoutImportConnectionFileResult(
            imported=True,
            connection_file_path=result["connection_file_path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_import_connection_file('%s') failed: %s", connection_file_path, exc)
        return build_envelope(exc)


# ── layout_export_connection_file ───────────────────────────────────────────────


async def layout_export_connection_file(
    connection_file_path: str,
) -> LayoutExportConnectionFileResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.layout_com.layout_export_connection_file,
            app,
            connection_file_path,
        )
        return LayoutExportConnectionFileResult(
            exported=True,
            connection_file_path=result["connection_file_path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("layout_export_connection_file('%s') failed: %s", connection_file_path, exc)
        return build_envelope(exc)
