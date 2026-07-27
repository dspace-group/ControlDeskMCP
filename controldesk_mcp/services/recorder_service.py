"""Service facade for ControlDesk main recorder operations.

Owns: orchestration of recorder lifecycle, signal management, and
      configuration over the COM MainRecorder interface.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.recorder import (
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
    RecorderMainRemoveSignalInput,
    RecorderMainRemoveSignalResult,
    RecorderMainStartInput,
    RecorderMainStartResult,
    RecorderMainStopInput,
    RecorderMainStopResult,
)
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


async def configure_main_recorder(
    params: RecorderMainConfigureInput,
) -> RecorderMainConfigureResult | ErrorEnvelope:
    """Configure main recorder filename, naming, and integration settings."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.configure_main_recorder,
            app,
            params.base_filename,
            params.automatic_naming_enabled,
            params.automatic_naming_start_index,
            params.automatic_naming_minimum_digits,
            params.add_to_experiment_enabled,
            params.open_in_data_pool_enabled,
            params.write_to_file_enabled,
            params.automatic_signal_configuration_enabled,
            params.description,
        )
        return RecorderMainConfigureResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def add_signal(
    params: RecorderMainAddSignalInput,
) -> RecorderMainAddSignalResult | ErrorEnvelope:
    """Add a signal to the main recorder's signal list."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.add_signal,
            app,
            params.connection_path,
        )
        return RecorderMainAddSignalResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def remove_signal(
    params: RecorderMainRemoveSignalInput,
) -> RecorderMainRemoveSignalResult | ErrorEnvelope:
    """Remove a signal from the main recorder's signal list."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.remove_signal,
            app,
            params.connection_path,
        )
        return RecorderMainRemoveSignalResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_signals(
    params: RecorderMainListSignalsInput,
) -> RecorderMainListSignalsResult | ErrorEnvelope:  # noqa: ARG001
    """List all signals currently assigned to the main recorder."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.list_signals,
            app,
        )
        return RecorderMainListSignalsResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def start_recorder(params: RecorderMainStartInput) -> RecorderMainStartResult | ErrorEnvelope:
    """Start the main recorder."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.start_recorder,
            app,
            params.with_trigger,
            params.overwrite_existing,
        )
        return RecorderMainStartResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def dry_run_start_recorder(
    params: RecorderMainStartInput,
) -> DryRunPreviewResult | ErrorEnvelope:
    """Preview recorder_main_start without starting anything.

    Checks whether the recorder is already running (a safe, read-only COM
    call) and reports whether the start would succeed.
    """
    state_result = await get_state(RecorderMainGetStateInput())
    if isinstance(state_result, ErrorEnvelope):
        return state_result
    is_running = state_result.is_running
    return DryRunPreviewResult(
        tool="recorder_main_start",
        action="start",
        target="main_recorder",
        would_execute=not is_running,
        current_state={"state": state_result.state, "is_running": is_running},
        message=(
            "Recorder is already running — start would fail and would not restart it; "
            "call recorder_main_stop first."
            if is_running
            else "Recorder is not running — start would succeed."
        ),
    )


async def stop_recorder(
    params: RecorderMainStopInput,
) -> RecorderMainStopResult | ErrorEnvelope:  # noqa: ARG001
    """Stop the main recorder and finalize the output file."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.stop_recorder,
            app,
        )
        return RecorderMainStopResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def dry_run_stop_recorder(
    params: RecorderMainStopInput,  # noqa: ARG001
) -> DryRunPreviewResult | ErrorEnvelope:
    """Preview recorder_main_stop without stopping anything.

    Checks whether the recorder is currently running (a safe, read-only COM
    call) and reports whether the stop would succeed.
    """
    state_result = await get_state(RecorderMainGetStateInput())
    if isinstance(state_result, ErrorEnvelope):
        return state_result
    is_running = state_result.is_running
    return DryRunPreviewResult(
        tool="recorder_main_stop",
        action="stop",
        target="main_recorder",
        would_execute=is_running,
        current_state={"state": state_result.state, "is_running": is_running},
        message=(
            "Recorder is running — stop would succeed and finalize the output file."
            if is_running
            else "Recorder is not running — stop would fail (nothing to stop)."
        ),
    )


async def get_state(
    params: RecorderMainGetStateInput,
) -> RecorderMainGetStateResult | ErrorEnvelope:  # noqa: ARG001
    """Return the current state of the main recorder."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.get_state,
            app,
        )
        return RecorderMainGetStateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def invoke_trigger(
    params: RecorderMainInvokeTriggerInput,
) -> RecorderMainInvokeTriggerResult | ErrorEnvelope:  # noqa: ARG001
    """Bypass the start trigger and begin recording immediately."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(com_bridge.domains.recorder_com.invoke_trigger, app)
        return RecorderMainInvokeTriggerResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def export_recorder(
    params: RecorderMainExportInput,
) -> RecorderMainExportResult | ErrorEnvelope:
    """Export the recorder configuration to a file."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.export_recorder,
            app,
            params.full_path,
            params.overwrite_existing,
        )
        return RecorderMainExportResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def import_signals_from_file(
    params: RecorderMainImportSignalsInput,
) -> RecorderMainImportSignalsResult | ErrorEnvelope:
    """Import signals from a previously exported recorder file."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.recorder_com.import_signals,
            app,
            params.full_path,
        )
        return RecorderMainImportSignalsResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)
