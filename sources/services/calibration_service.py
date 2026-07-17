"""Service facade for ControlDesk online calibration operations.

Owns: orchestration of calibration lifecycle over the COM CalibrationManagement
      and ProposedCalibration interfaces.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from sources import com_bridge
from sources.com_bridge.errors import BridgeError
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
    CalibrationGetStateInput,
    CalibrationGetStateResult,
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
    ProposedCalibrationStartInput,
    ProposedCalibrationStartResult,
    ProposedCalibrationStopInput,
    ProposedCalibrationStopResult,
)
from sources.models.envelope_builder import build_envelope
from sources.models.errors import ErrorEnvelope
from sources.utils.logger import get_logger

_log = get_logger(__name__)


async def start_calibration(
    params: CalibrationStartInput,
) -> CalibrationStartResult | ErrorEnvelope:  # noqa: ARG001
    """Start online calibration on all connected platforms."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.calibration_start,
            app,
        )
        return CalibrationStartResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def dry_run_start_calibration(
    params: CalibrationStartInput,  # noqa: ARG001
) -> DryRunPreviewResult | ErrorEnvelope:
    """Preview calibration_start without starting anything.

    Checks whether online calibration is already running (a safe, read-only
    COM call) and reports whether the start would succeed.
    """
    state_result = await get_calibration_state(CalibrationGetStateInput())
    if isinstance(state_result, ErrorEnvelope):
        return state_result
    is_running = state_result.calibration_state == "Started"
    return DryRunPreviewResult(
        tool="calibration_start",
        action="start",
        target="online_calibration",
        would_execute=not is_running,
        current_state={"calibration_state": state_result.calibration_state},
        message=(
            "Online calibration is already running — start would fail; "
            "call calibration_stop first."
            if is_running
            else "Online calibration is not running — start would succeed."
        ),
    )


async def stop_calibration(
    params: CalibrationStopInput,
) -> CalibrationStopResult | ErrorEnvelope:  # noqa: ARG001
    """Stop online calibration on all platforms."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.calibration_stop,
            app,
        )
        return CalibrationStopResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def activate_reference_page(
    params: CalibrationActivateReferencePageInput,
) -> CalibrationActivateReferencePageResult | ErrorEnvelope:  # noqa: ARG001
    """Switch all platforms to the ECU reference (flash) page."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.calibration_activate_reference_page,
            app,
        )
        return CalibrationActivateReferencePageResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def activate_working_page(  # noqa: ARG001
    params: CalibrationActivateWorkingPageInput,
) -> CalibrationActivateWorkingPageResult | ErrorEnvelope:
    """Switch all platforms back to the ECU working (RAM) page."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.calibration_activate_working_page,
            app,
        )
        return CalibrationActivateWorkingPageResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def refresh_parameters(  # noqa: ARG001
    params: CalibrationRefreshParametersInput,
) -> CalibrationRefreshParametersResult | ErrorEnvelope:
    """Re-upload ECU parameter values to refresh the ControlDesk view."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.calibration_refresh_parameters,
            app,
        )
        return CalibrationRefreshParametersResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def start_proposed_calibration(  # noqa: ARG001
    params: ProposedCalibrationStartInput,
) -> ProposedCalibrationStartResult | ErrorEnvelope:
    """Start a proposed calibration session (staged-write mode)."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.proposed_calibration_start,
            app,
        )
        return ProposedCalibrationStartResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def stop_proposed_calibration(  # noqa: ARG001
    params: ProposedCalibrationStopInput,
) -> ProposedCalibrationStopResult | ErrorEnvelope:
    """Stop proposed calibration session without applying staged changes."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.proposed_calibration_stop,
            app,
        )
        return ProposedCalibrationStopResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def apply_proposed_calibration(  # noqa: ARG001
    params: ProposedCalibrationApplyInput,
) -> ProposedCalibrationApplyResult | ErrorEnvelope:
    """Commit staged proposed calibration changes to the ECU working page."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.proposed_calibration_apply,
            app,
        )
        return ProposedCalibrationApplyResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def cancel_proposed_calibration(
    params: ProposedCalibrationCancelInput,
) -> ProposedCalibrationCancelResult | ErrorEnvelope:  # noqa: ARG001
    """Cancel proposed calibration and revert ECU to pre-session values."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.proposed_calibration_cancel,
            app,
        )
        return ProposedCalibrationCancelResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def get_calibration_state(
    params: CalibrationGetStateInput,
) -> CalibrationGetStateResult | ErrorEnvelope:  # noqa: ARG001
    """Query the current online calibration and proposed calibration state."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.calibration_get_state,
            app,
        )
        return CalibrationGetStateResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def copy_working_page_to_reference(
    params: CalibrationCopyWorkingPageToReferenceInput,
) -> CalibrationCopyWorkingPageToReferenceResult | ErrorEnvelope:
    """Copy the working page contents to the reference page for a specific platform."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.calibration_copy_working_page_to_reference,
            app,
            params.platform_name,
        )
        return CalibrationCopyWorkingPageToReferenceResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def copy_reference_page_to_working(
    params: CalibrationCopyReferencePageToWorkingInput,
) -> CalibrationCopyReferencePageToWorkingResult | ErrorEnvelope:
    """Copy the reference page contents to the working page for a specific platform."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.calibration_com.calibration_copy_reference_page_to_working,
            app,
            params.platform_name,
        )
        return CalibrationCopyReferencePageToWorkingResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)
