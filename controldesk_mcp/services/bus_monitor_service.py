"""Service facade for ControlDesk bus monitor operations.

Owns: orchestration of monitor lifecycle and data export over the BusNavigator COM hierarchy.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.bus_monitor import (
    BusMonitorClearAllAborted,
    BusMonitorClearAllInput,
    BusMonitorClearAllResult,
    BusMonitorConfigureInput,
    BusMonitorConfigureResult,
    BusMonitorCreateInput,
    BusMonitorCreateResult,
    BusMonitorGetStateInput,
    BusMonitorGetStateResult,
    BusMonitorListInput,
    BusMonitorListResult,
    BusMonitorLoadDataInput,
    BusMonitorLoadDataResult,
    BusMonitorRemoveInput,
    BusMonitorRemoveResult,
    BusMonitorRenameInput,
    BusMonitorRenameResult,
    BusMonitorSaveDataInput,
    BusMonitorSaveDataResult,
    BusMonitorSaveDataWithTimeAxisInput,
    BusMonitorSaveDataWithTimeAxisResult,
    BusMonitorStartInput,
    BusMonitorStartResult,
    BusMonitorStopInput,
    BusMonitorStopResult,
)
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def create_monitor(params: BusMonitorCreateInput) -> BusMonitorCreateResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.create_monitor,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusMonitorCreateResult(
            monitor_name=result["monitor_name"],
            system_index=result["system_index"],
            bus_type=result["bus_type"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def dry_run_create_monitor(
    params: BusMonitorCreateInput,
) -> DryRunPreviewResult | ErrorEnvelope:
    """Preview bus_monitor_create without creating anything.

    Checks whether a monitor with the requested name already exists on the
    target physical bus access (a safe, read-only COM call) and reports
    whether the create would succeed.
    """
    state_result = await get_monitor_state(
        BusMonitorGetStateInput(
            monitor_name=params.monitor_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
        )
    )
    already_exists = not isinstance(state_result, ErrorEnvelope)
    return DryRunPreviewResult(
        tool="bus_monitor_create",
        action="create",
        target=params.monitor_name,
        would_execute=not already_exists,
        current_state={"already_exists": already_exists},
        message=(
            f"Monitor '{params.monitor_name}' already exists on system {params.system_index} "
            f"({params.bus_type.value}) — create would fail with a duplicate-name error."
            if already_exists
            else f"No monitor named '{params.monitor_name}' exists on system "
            f"{params.system_index} ({params.bus_type.value}) — create would succeed."
        ),
    )


async def configure_monitor(
    params: BusMonitorConfigureInput,
) -> BusMonitorConfigureResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.configure_monitor,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
            params.update_rate_ms,
            params.buffer_size_frames,
            params.buffer_mode.value,
            params.enable_j1939_pgn_resolving,
        )
        return BusMonitorConfigureResult(
            monitor_name=result["monitor_name"],
            update_rate_ms=result["update_rate_ms"],
            buffer_size_frames=result["buffer_size_frames"],
            buffer_mode=result["buffer_mode"],
            enable_j1939_pgn_resolving=result["enable_j1939_pgn_resolving"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def start_monitor(params: BusMonitorStartInput) -> BusMonitorStartResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.start_monitor,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusMonitorStartResult(
            monitor_name=params.monitor_name,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def stop_monitor(params: BusMonitorStopInput) -> BusMonitorStopResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.stop_monitor,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusMonitorStopResult(
            monitor_name=params.monitor_name,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def get_monitor_state(
    params: BusMonitorGetStateInput,
) -> BusMonitorGetStateResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.get_monitor_state,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusMonitorGetStateResult(
            monitor_name=result["monitor_name"],
            state=result["state"],
            is_running=result["is_running"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def list_monitors(params: BusMonitorListInput) -> BusMonitorListResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        monitors = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.list_monitors,
            app,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusMonitorListResult(
            system_index=params.system_index,
            bus_type=params.bus_type.value,
            total_count=len(monitors),
            monitors=monitors,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_monitor(params: BusMonitorRemoveInput) -> BusMonitorRemoveResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.remove_monitor,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusMonitorRemoveResult(
            monitor_name=params.monitor_name,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def clear_all_monitors(
    params: BusMonitorClearAllInput,
) -> BusMonitorClearAllAborted | BusMonitorClearAllResult | ErrorEnvelope:
    if not params.confirm:
        return BusMonitorClearAllAborted()
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.clear_all_monitors,
            app,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusMonitorClearAllResult(
            cleared=True,
            monitors_removed=result["monitors_removed"],
            system_index=params.system_index,
            bus_type=params.bus_type.value,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def save_monitor_data(
    params: BusMonitorSaveDataInput,
) -> BusMonitorSaveDataResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.save_monitor_data,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
            params.output_file_path,
        )
        return BusMonitorSaveDataResult(
            monitor_name=result["monitor_name"],
            output_file_path=result["output_file_path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def save_monitor_data_with_time_axis(
    params: BusMonitorSaveDataWithTimeAxisInput,
) -> BusMonitorSaveDataWithTimeAxisResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.save_monitor_data_with_time_axis,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
            params.output_file_path,
            params.time_axis.value,
        )
        return BusMonitorSaveDataWithTimeAxisResult(
            monitor_name=result["monitor_name"],
            output_file_path=result["output_file_path"],
            time_axis=result["time_axis"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def load_monitor_data(
    params: BusMonitorLoadDataInput,
) -> BusMonitorLoadDataResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.load_monitor_data,
            app,
            params.monitor_name,
            params.system_index,
            params.bus_type.value,
            params.log_file_path,
            params.log_file_section,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusMonitorLoadDataResult(
            monitor_name=result["monitor_name"],
            log_file_path=result["log_file_path"],
            log_file_section=result["log_file_section"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def rename_monitor(params: BusMonitorRenameInput) -> BusMonitorRenameResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_monitor_com.rename_monitor,
            app,
            params.monitor_name,
            params.new_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusMonitorRenameResult(
            old_name=result["old_name"],
            new_name=result["new_name"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)
