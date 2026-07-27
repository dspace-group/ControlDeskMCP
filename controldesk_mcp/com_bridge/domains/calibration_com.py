"""COM bridge for ControlDesk online calibration operations.

Provides low-level COM interface wrappers for calibration lifecycle management.
All functions run on the STA thread via com_bridge.dispatch().

Key considerations:
- Persistent refs: IXaCalibrationManagement cached from calibration_start through
  calibration_stop; IXaProposedCalibration cached from proposed_calibration_start
  through apply/cancel/stop.
- Transient refs: calibration_refresh_parameters re-uses cached management ref.
- Error handling: Raise exceptions for all error conditions; dispatch handles wrapping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from controldesk_mcp.com_bridge.domains.platform_com import _get_platform
from controldesk_mcp.com_bridge.errors import BridgeOperationError
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)

# ── Persistent COM references ────────────────────────────────────────────────────

_calibration_mgmt: Any = None
_proposed_calibration: Any = None


def _timestamp_utc() -> str:
    """Return current UTC timestamp as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ── Tool 1: calibration_start ────────────────────────────────────────────────────


def calibration_start(app: Any) -> dict[str, Any]:
    """Start online calibration on all connected platforms.

    Acquires and caches IXaCalibrationManagement for subsequent calls.

    Returns: dict with started=True
    Raises: BridgeOperationError on COM error
    """
    global _calibration_mgmt
    try:
        _calibration_mgmt = app.CalibrationManagement
        _calibration_mgmt.StartOnlineCalibration()
        return {"started": True}
    except Exception as exc:
        _calibration_mgmt = None
        raise BridgeOperationError(
            "Failed to start online calibration. Ensure at least one platform is connected "
            "and a variable description is loaded.",
        ) from exc


# ── Tool 2: calibration_stop ─────────────────────────────────────────────────────


def calibration_stop(app: Any) -> dict[str, Any]:
    """Stop online calibration on all platforms.

    Uses cached IXaCalibrationManagement and releases it after the call.

    Returns: dict with stopped=True
    Raises: BridgeOperationError on COM error
    """
    global _calibration_mgmt
    try:
        mgmt = _calibration_mgmt or app.CalibrationManagement
        mgmt.StopOnlineCalibration()
        return {"stopped": True}
    except Exception as exc:
        raise BridgeOperationError(
            "Failed to stop online calibration.",
        ) from exc
    finally:
        _calibration_mgmt = None


# ── Tool 3: calibration_activate_reference_page ──────────────────────────────────


def calibration_activate_reference_page(app: Any) -> dict[str, Any]:
    """Switch all platforms to the ECU reference (flash) page.

    Requires active calibration session.

    Returns: dict with activated=True, page="ReferencePage"
    Raises: BridgeOperationError on COM error
    """
    global _calibration_mgmt
    try:
        mgmt = _calibration_mgmt or app.CalibrationManagement
        _calibration_mgmt = mgmt
        mgmt.ActivateReferencePageForSupportingPlatforms()
        return {"activated": True, "page": "ReferencePage"}
    except Exception as exc:
        raise BridgeOperationError(
            "Failed to activate reference page. Ensure online calibration is running.",
        ) from exc


# ── Tool 4: calibration_activate_working_page ────────────────────────────────────


def calibration_activate_working_page(app: Any) -> dict[str, Any]:
    """Switch all platforms back to the ECU working (RAM) page.

    Requires active calibration session.

    Returns: dict with activated=True, page="WorkingPage"
    Raises: BridgeOperationError on COM error
    """
    global _calibration_mgmt
    try:
        mgmt = _calibration_mgmt or app.CalibrationManagement
        _calibration_mgmt = mgmt
        mgmt.ActivateWorkingPageForSupportingPlatforms()
        return {"activated": True, "page": "WorkingPage"}
    except Exception as exc:
        raise BridgeOperationError(
            "Failed to activate working page. Ensure online calibration is running.",
        ) from exc


# ── Tool 5: calibration_refresh_parameters ───────────────────────────────────────


def calibration_refresh_parameters(app: Any) -> dict[str, Any]:
    """Re-upload ECU parameter values to refresh the ControlDesk view.

    Requires active calibration session.

    Returns: dict with refreshed=True, timestamp_utc
    Raises: BridgeOperationError on COM error
    """
    global _calibration_mgmt
    try:
        mgmt = _calibration_mgmt or app.CalibrationManagement
        _calibration_mgmt = mgmt
        mgmt.RefreshConnectedParameters()
        return {"refreshed": True, "timestamp_utc": _timestamp_utc()}
    except Exception as exc:
        raise BridgeOperationError(
            "Failed to refresh calibration parameters. "
            "Ensure online calibration is running and ECU is connected.",
        ) from exc


# ── Tool 6: proposed_calibration_start ───────────────────────────────────────────


def proposed_calibration_start(app: Any) -> dict[str, Any]:
    """Start a proposed calibration session (staged-write mode).

    Acquires and caches IXaProposedCalibration via CalibrationManagement.

    Returns: dict with started=True, proposed_calibration_active=True
    Raises: BridgeOperationError on COM error
    """
    global _proposed_calibration
    try:
        _proposed_calibration = app.CalibrationManagement.ProposedCalibration
        _proposed_calibration.Start()
        return {"started": True, "proposed_calibration_active": True}
    except Exception as exc:
        _proposed_calibration = None
        raise BridgeOperationError(
            "Failed to start proposed calibration. Ensure online calibration is running "
            "and no proposed session is already active.",
        ) from exc


# ── Tool 7: proposed_calibration_stop ────────────────────────────────────────────


def proposed_calibration_stop(app: Any) -> dict[str, Any]:
    """Stop proposed calibration session without applying staged changes.

    Uses cached IXaProposedCalibration and releases it after the call.

    Returns: dict with stopped=True, changes_applied=False, proposed_calibration_active=False
    Raises: BridgeOperationError on COM error
    """
    global _proposed_calibration
    try:
        pc = _proposed_calibration or app.CalibrationManagement.ProposedCalibration
        pc.Stop()
        return {"stopped": True, "changes_applied": False, "proposed_calibration_active": False}
    except Exception as exc:
        raise BridgeOperationError(
            "Failed to stop proposed calibration. Ensure a proposed session is currently active.",
        ) from exc
    finally:
        _proposed_calibration = None


# ── Tool 8: proposed_calibration_apply ───────────────────────────────────────────


def proposed_calibration_apply(app: Any) -> dict[str, Any]:
    """Commit staged proposed calibration changes to the ECU working page.

    Uses cached IXaProposedCalibration and releases it after the call.

    Returns: dict with applied=True, proposed_calibration_active=False
    Raises: BridgeOperationError on COM error
    """
    global _proposed_calibration
    try:
        pc = _proposed_calibration or app.CalibrationManagement.ProposedCalibration
        pc.Apply()
        return {"applied": True, "proposed_calibration_active": False}
    except Exception as exc:
        raise BridgeOperationError(
            "Failed to apply proposed calibration. Ensure a proposed session is active "
            "and online calibration is running.",
        ) from exc
    finally:
        _proposed_calibration = None


# ── Tool 9: proposed_calibration_cancel ──────────────────────────────────────────


def proposed_calibration_cancel(app: Any) -> dict[str, Any]:
    """Cancel proposed calibration and revert ECU to pre-session values.

    Uses cached IXaProposedCalibration and releases it after the call.

    Returns: dict with cancelled=True, proposed_calibration_active=False
    Raises: BridgeOperationError on COM error
    """
    global _proposed_calibration
    try:
        pc = _proposed_calibration or app.CalibrationManagement.ProposedCalibration
        pc.Cancel()
        return {"cancelled": True, "proposed_calibration_active": False}
    except Exception as exc:
        raise BridgeOperationError(
            "Failed to cancel proposed calibration. Ensure a proposed session is currently active.",
        ) from exc
    finally:
        _proposed_calibration = None


# ── Cache management ─────────────────────────────────────────────────────────────


def clear_cache() -> None:
    """Clear all cached COM references. Called on shutdown."""
    global _calibration_mgmt, _proposed_calibration
    _calibration_mgmt = None
    _proposed_calibration = None


# ── Tool 10: calibration_get_state ───────────────────────────────────────────────


def calibration_get_state(app: Any) -> dict[str, Any]:
    """Query the current online calibration and proposed calibration state.

    Returns global calibration state from CalibrationManagement.State (0=stopped, 1=started)
    and proposed calibration state from ProposedCalibration.State (0=active, 1=inactive).

    Returns: dict with calibration_state, proposed_calibration_state, raw integer values
    Raises: BridgeOperationError on COM error
    """
    try:
        mgmt = app.CalibrationManagement
        cal_state_int = int(mgmt.State)
        pc_state_int = int(mgmt.ProposedCalibration.State)
        return {
            "calibration_state": "Started" if cal_state_int == 1 else "Stopped",
            "calibration_state_raw": cal_state_int,
            "proposed_calibration_state": "Active" if pc_state_int == 0 else "Inactive",
            "proposed_calibration_state_raw": pc_state_int,
        }
    except Exception as exc:
        raise BridgeOperationError(
            "Failed to query calibration state. Ensure an active experiment is open.",
        ) from exc


# ── Tool 11: calibration_copy_working_page_to_reference ──────────────────────────


def calibration_copy_working_page_to_reference(app: Any, platform_name: str) -> dict[str, Any]:
    """Copy the working page contents to the reference page for a specific platform.

    This operation saves the current working-page parameter values as the new reference
    baseline. Online calibration and measurement MUST be stopped before calling this function.
    The platform must be connected to the ECU.

    Returns: dict with copied=True, platform_name, source_page, target_page
    Raises: BridgePreconditionError if platform not found; BridgeOperationError on COM error
    """
    plat = _get_platform(app, platform_name)  # raises BridgePreconditionError if not found
    try:
        plat.CopyWorkingPageToReferencePage()
        return {
            "copied": True,
            "platform_name": platform_name,
            "source_page": "WorkingPage",
            "target_page": "ReferencePage",
        }
    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to copy working page to reference page for platform '{platform_name}'. "
            "Ensure online calibration and measurement are stopped and the platform is connected.",
        ) from exc


# ── Tool 12: calibration_copy_reference_page_to_working ──────────────────────────


def calibration_copy_reference_page_to_working(app: Any, platform_name: str) -> dict[str, Any]:
    """Copy the reference page contents to the working page for a specific platform.

    This operation restores the working page to the reference baseline values, reverting
    any live edits made since calibration started. Online calibration and measurement MUST
    be stopped before calling this function. The platform must be connected to the ECU.

    Returns: dict with copied=True, platform_name, source_page, target_page
    Raises: BridgePreconditionError if platform not found; BridgeOperationError on COM error
    """
    plat = _get_platform(app, platform_name)  # raises BridgePreconditionError if not found
    try:
        plat.CopyReferencePageToWorkingPage()
        return {
            "copied": True,
            "platform_name": platform_name,
            "source_page": "ReferencePage",
            "target_page": "WorkingPage",
        }
    except Exception as exc:
        raise BridgeOperationError(
            f"Failed to copy reference page to working page for platform '{platform_name}'. "
            "Ensure online calibration and measurement are stopped and the platform is connected.",
        ) from exc
