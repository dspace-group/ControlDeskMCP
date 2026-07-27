"""Service facade for ControlDesk bus logging operations.

Owns: orchestration of logger and filter lifecycle over the COM BusNavigator hierarchy.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.bus_logging import (
    BusFilterConfigureInput,
    BusFilterConfigureResult,
    BusFilterCreateInput,
    BusFilterCreateResult,
    BusFilterListInput,
    BusFilterListResult,
    BusFilterRemoveInput,
    BusFilterRemoveResult,
    BusFilterStartInput,
    BusFilterStartResult,
    BusFilterStopInput,
    BusFilterStopResult,
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
)
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def create_logger(params: BusLoggerCreateInput) -> BusLoggerCreateResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.create_logger,
            app,
            params.logger_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusLoggerCreateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def dry_run_create_logger(
    params: BusLoggerCreateInput,
) -> DryRunPreviewResult | ErrorEnvelope:
    """Preview bus_logger_create without creating anything.

    Checks whether a logger with the requested name already exists on the
    target physical bus access (a safe, read-only COM call) and reports
    whether the create would succeed.
    """
    state_result = await get_logger_state(
        BusLoggerGetStateInput(
            logger_name=params.logger_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
        )
    )
    already_exists = not isinstance(state_result, ErrorEnvelope)
    return DryRunPreviewResult(
        tool="bus_logger_create",
        action="create",
        target=params.logger_name,
        would_execute=not already_exists,
        current_state={"already_exists": already_exists},
        message=(
            f"Logger '{params.logger_name}' already exists on system {params.system_index} "
            f"({params.bus_type.value}) — create would fail with a duplicate-name error."
            if already_exists
            else f"No logger named '{params.logger_name}' exists on system "
            f"{params.system_index} ({params.bus_type.value}) — create would succeed."
        ),
    )


async def configure_logger(
    params: BusLoggerConfigureInput,
) -> BusLoggerConfigureResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.configure_logger,
            app,
            params.logger_name,
            params.system_index,
            params.bus_type.value,
            params.log_file_full_path,
            params.overwrite_existing,
            params.max_duration_seconds,
            params.enable_bus_statistics,
            params.continuous_ring_mode,
            params.file_rolling_enabled,
            params.file_rolling_type.value,
            params.file_rolling_interval_seconds,
            params.time_axis_mode.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusLoggerConfigureResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def start_logger(params: BusLoggerStartInput) -> BusLoggerStartResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.start_logger,
            app,
            params.logger_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusLoggerStartResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def stop_logger(params: BusLoggerStopInput) -> BusLoggerStopResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.stop_logger,
            app,
            params.logger_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusLoggerStopResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def get_logger_state(
    params: BusLoggerGetStateInput,
) -> BusLoggerGetStateResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.get_logger_state,
            app,
            params.logger_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusLoggerGetStateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_loggers(params: BusLoggerListInput) -> BusLoggerListResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.list_loggers,
            app,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusLoggerListResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_logger(params: BusLoggerRemoveInput) -> BusLoggerRemoveResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.remove_logger,
            app,
            params.logger_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusLoggerRemoveResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def clear_all_loggers(
    params: BusLoggerClearAllInput,
) -> BusLoggerClearAllAborted | BusLoggerClearAllResult | ErrorEnvelope:
    if not params.confirm:
        return BusLoggerClearAllAborted()
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.clear_all_loggers,
            app,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusLoggerClearAllResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def set_logger_activated(
    params: BusLoggerSetActivatedInput,
) -> BusLoggerSetActivatedResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.set_logger_activated,
            app,
            params.logger_name,
            params.system_index,
            params.bus_type.value,
            params.activated,
        )
        return BusLoggerSetActivatedResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def create_filter(params: BusFilterCreateInput) -> BusFilterCreateResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.create_filter,
            app,
            params.filter_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusFilterCreateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def configure_filter(
    params: BusFilterConfigureInput,
) -> BusFilterConfigureResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.configure_filter,
            app,
            params.filter_name,
            params.system_index,
            params.bus_type.value,
            params.filter_mode,
            params.message_id,
            params.message_mask,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusFilterConfigureResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def start_filter(params: BusFilterStartInput) -> BusFilterStartResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.start_filter,
            app,
            params.filter_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusFilterStartResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def stop_filter(params: BusFilterStopInput) -> BusFilterStopResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.stop_filter,
            app,
            params.filter_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusFilterStopResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_filters(params: BusFilterListInput) -> BusFilterListResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.list_filters,
            app,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusFilterListResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_filter(params: BusFilterRemoveInput) -> BusFilterRemoveResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.remove_filter,
            app,
            params.filter_name,
            params.system_index,
            params.bus_type.value,
        )
        return BusFilterRemoveResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def rename_logger(params: BusLoggerRenameInput) -> BusLoggerRenameResult | ErrorEnvelope:
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_logging_com.rename_logger,
            app,
            params.logger_name,
            params.new_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusLoggerRenameResult(
            old_name=result["old_name"],
            new_name=result["new_name"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)
