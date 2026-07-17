"""Service facade for ControlDesk bus replay operations.

Owns: orchestration of replay lifecycle over the COM BusNavigator hierarchy.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sources import com_bridge
from sources.com_bridge.errors import BridgeError
from sources.models.base import DryRunPreviewResult
from sources.models.bus_replay import (
    BusReplayClearAllAborted,
    BusReplayClearAllInput,
    BusReplayClearAllResult,
    BusReplayConfigureInput,
    BusReplayConfigureResult,
    BusReplayCreateInput,
    BusReplayCreateResult,
    BusReplayGetStateInput,
    BusReplayGetStateResult,
    BusReplayListInput,
    BusReplayListResult,
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
)
from sources.models.envelope_builder import build_envelope
from sources.models.errors import ErrorEnvelope
from sources.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


async def create_replay(params: BusReplayCreateInput) -> BusReplayCreateResult | ErrorEnvelope:
    """Create a new bus replay."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.create_replay,
            app,
            params.replay_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayCreateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def dry_run_create_replay(
    params: BusReplayCreateInput,
) -> DryRunPreviewResult | ErrorEnvelope:
    """Preview bus_replay_create without creating anything.

    Checks whether a replay with the requested name already exists on the
    target physical bus access (a safe, read-only COM call) and reports
    whether the create would succeed.
    """
    state_result = await get_replay_state(
        BusReplayGetStateInput(
            replay_name=params.replay_name,
            system_index=params.system_index,
            bus_type=params.bus_type,
            bus_platform_index=params.bus_platform_index,
            physical_bus_access_index=params.physical_bus_access_index,
        )
    )
    already_exists = not isinstance(state_result, ErrorEnvelope)
    return DryRunPreviewResult(
        tool="bus_replay_create",
        action="create",
        target=params.replay_name,
        would_execute=not already_exists,
        current_state={"already_exists": already_exists},
        message=(
            f"Replay '{params.replay_name}' already exists on system {params.system_index} "
            f"({params.bus_type.value}) — create would fail with a duplicate-name error."
            if already_exists
            else f"No replay named '{params.replay_name}' exists on system "
            f"{params.system_index} ({params.bus_type.value}) — create would succeed."
        ),
    )


async def configure_replay(
    params: BusReplayConfigureInput,
) -> BusReplayConfigureResult | ErrorEnvelope:
    """Configure replay playback settings."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.configure_replay,
            app,
            params.replay_name,
            params.system_index,
            params.bus_type.value,
            params.log_file_full_path,
            params.log_file_section,
            params.replay_mode.value,
            params.number_of_passes,
            params.duration_seconds,
            params.start_monitor_on_replay,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayConfigureResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def start_replay(params: BusReplayStartInput) -> BusReplayStartResult | ErrorEnvelope:
    """Activate and start replay."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.start_replay,
            app,
            params.replay_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayStartResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def stop_replay(params: BusReplayStopInput) -> BusReplayStopResult | ErrorEnvelope:
    """Stop replay and deactivate."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.stop_replay,
            app,
            params.replay_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayStopResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def get_replay_state(
    params: BusReplayGetStateInput,
) -> BusReplayGetStateResult | ErrorEnvelope:
    """Query current replay state."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.get_replay_state,
            app,
            params.replay_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayGetStateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_replays(params: BusReplayListInput) -> BusReplayListResult | ErrorEnvelope:
    """List all replays on a physical bus access."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.list_replays,
            app,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayListResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_replay(params: BusReplayRemoveInput) -> BusReplayRemoveResult | ErrorEnvelope:
    """Remove a specific replay."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.remove_replay,
            app,
            params.replay_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayRemoveResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def clear_all_replays(
    params: BusReplayClearAllInput,
) -> BusReplayClearAllAborted | BusReplayClearAllResult | ErrorEnvelope:
    """Clear all replays from a physical bus access."""
    try:
        if not params.confirm:
            return BusReplayClearAllAborted()

        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.clear_all_replays,
            app,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayClearAllResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def set_replay_activated(
    params: BusReplaySetActivatedInput,
) -> BusReplaySetActivatedResult | ErrorEnvelope:
    """Set or clear the Activated flag on a replay."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.set_replay_activated,
            app,
            params.replay_name,
            params.system_index,
            params.bus_type.value,
            params.activated,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplaySetActivatedResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def rename_replay(params: BusReplayRenameInput) -> BusReplayRenameResult | ErrorEnvelope:
    """Rename an existing replay."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.bus_replay_com.rename_replay,
            app,
            params.replay_name,
            params.new_name,
            params.system_index,
            params.bus_type.value,
            params.bus_platform_index,
            params.physical_bus_access_index,
        )
        return BusReplayRenameResult(
            old_name=result["old_name"],
            new_name=result["new_name"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)
