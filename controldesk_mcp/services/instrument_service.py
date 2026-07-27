"""Service facade for ControlDesk instrument management operations.

Owns: orchestration of instrument lifecycle on the active layout — list, add,
      remove, get_info, move, configure, arrange, and signal connect/disconnect.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.instrument import (
    InstrumentAddResult,
    InstrumentArrangeResult,
    InstrumentConfigureResult,
    InstrumentConnectSignalResult,
    InstrumentDisconnectSignalResult,
    InstrumentGetInfoResult,
    InstrumentInfo,
    InstrumentListResult,
    InstrumentMoveResult,
    InstrumentRemoveResult,
    InstrumentTypeInfo,
    InstrumentTypeListResult,
    SignalConnection,
)
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _get_app():
    return com_bridge.get_connection().get_app()


# ── instrument_list ───────────────────────────────────────────────────────────


async def instrument_list() -> InstrumentListResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.instrument_com.instrument_list, app)
        instruments = [InstrumentInfo(**i) for i in result["instruments"]]
        return InstrumentListResult(
            layout_name=result["layout_name"],
            total_instruments=len(instruments),
            instruments=instruments,
        )
    except BridgeError as exc:
        _log.warning("instrument_list failed: %s", exc)
        return build_envelope(exc)


# ── instrument_list_types ─────────────────────────────────────────────────────


async def instrument_list_types() -> InstrumentTypeListResult | ErrorEnvelope:
    try:
        types = await com_bridge.dispatch(com_bridge.domains.instrument_com.instrument_list_types)
        return InstrumentTypeListResult(
            total_types=len(types),
            instrument_types=[InstrumentTypeInfo(**t) for t in types],
        )
    except BridgeError as exc:
        _log.warning("instrument_list_types failed: %s", exc)
        return build_envelope(exc)


# ── instrument_add ──────────────────────────────────────────────────────────────


async def instrument_add(
    instrument_type: str,
    instrument_name: str,
    x: int,
    y: int,
    width: int,
    height: int,
) -> InstrumentAddResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.instrument_com.instrument_add,
            app,
            instrument_type,
            instrument_name,
            x,
            y,
            width,
            height,
        )
        return InstrumentAddResult(
            added=True,
            instrument_name=result["instrument_name"],
            instrument_type=result["instrument_type"],
            x=result["x"],
            y=result["y"],
            width=result["width"],
            height=result["height"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("instrument_add('%s') failed: %s", instrument_name, exc)
        return build_envelope(exc)


# ── instrument_remove ──────────────────────────────────────────────────────────


async def instrument_remove(instrument_name: str) -> InstrumentRemoveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        await com_bridge.dispatch(
            com_bridge.domains.instrument_com.instrument_remove, app, instrument_name
        )
        return InstrumentRemoveResult(
            removed=True,
            instrument_name=instrument_name,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("instrument_remove('%s') failed: %s", instrument_name, exc)
        return build_envelope(exc)


# ── instrument_get_info ────────────────────────────────────────────────────────


async def instrument_get_info(instrument_name: str) -> InstrumentGetInfoResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.instrument_com.instrument_get_info, app, instrument_name
        )
        connections = [SignalConnection(**c) for c in result["signal_connections"]]
        return InstrumentGetInfoResult(
            instrument_name=result["instrument_name"],
            instrument_type=result["instrument_type"],
            x=result["x"],
            y=result["y"],
            width=result["width"],
            height=result["height"],
            signal_connections=connections,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("instrument_get_info('%s') failed: %s", instrument_name, exc)
        return build_envelope(exc)


# ── instrument_move ────────────────────────────────────────────────────────────


async def instrument_move(
    instrument_name: str,
    x: int | None,
    y: int | None,
    width: int | None,
    height: int | None,
) -> InstrumentMoveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.instrument_com.instrument_move,
            app,
            instrument_name,
            x,
            y,
            width,
            height,
        )
        return InstrumentMoveResult(
            moved=True,
            instrument_name=result["instrument_name"],
            x=result["x"],
            y=result["y"],
            width=result["width"],
            height=result["height"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("instrument_move('%s') failed: %s", instrument_name, exc)
        return build_envelope(exc)


# ── instrument_configure ───────────────────────────────────────────────────────


async def instrument_configure(
    instrument_name: str,
    caption: str | None,
    back_color: str | None,
    fore_color: str | None,
    show_border: bool | None,
) -> InstrumentConfigureResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.instrument_com.instrument_configure,
            app,
            instrument_name,
            caption,
            back_color,
            fore_color,
            show_border,
        )
        return InstrumentConfigureResult(
            configured=True,
            instrument_name=result["instrument_name"],
            caption=result["caption"],
            back_color=result["back_color"],
            fore_color=result["fore_color"],
            show_border=result["show_border"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("instrument_configure('%s') failed: %s", instrument_name, exc)
        return build_envelope(exc)


# ── instrument_arrange ─────────────────────────────────────────────────────────


async def instrument_arrange(
    instrument_names: list[str],
    arrange_action: str,
) -> InstrumentArrangeResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.instrument_com.instrument_arrange,
            app,
            instrument_names,
            arrange_action,
        )
        return InstrumentArrangeResult(
            arranged=True,
            action=result["action"],
            instrument_names=result["instrument_names"],
            group_name=result.get("group_name"),
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("instrument_arrange(%s) failed: %s", instrument_names, exc)
        return build_envelope(exc)


# ── instrument_connect_signal ──────────────────────────────────────────────────


async def instrument_connect_signal(
    instrument_name: str,
    variable_path: str,
    signal_color: str | None,
    axis_index: int,
) -> InstrumentConnectSignalResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.instrument_com.instrument_connect_signal,
            app,
            instrument_name,
            variable_path,
            signal_color,
            axis_index,
        )
        return InstrumentConnectSignalResult(
            connected=True,
            instrument_name=result["instrument_name"],
            instrument_type=result["instrument_type"],
            variable_path=result["variable_path"],
            connection_mode=result["connection_mode"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning(
            "instrument_connect_signal('%s', '%s') failed: %s",
            instrument_name,
            variable_path,
            exc,
        )
        return build_envelope(exc)


# ── instrument_disconnect_signal ───────────────────────────────────────────────


async def instrument_disconnect_signal(
    instrument_name: str,
    variable_path: str | None,
    axis_index: int,
) -> InstrumentDisconnectSignalResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.instrument_com.instrument_disconnect_signal,
            app,
            instrument_name,
            variable_path,
            axis_index,
        )
        return InstrumentDisconnectSignalResult(
            disconnected=True,
            instrument_name=result["instrument_name"],
            variable_path=result["variable_path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning(
            "instrument_disconnect_signal('%s') failed: %s",
            instrument_name,
            exc,
        )
        return build_envelope(exc)
