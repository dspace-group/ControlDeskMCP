"""Unit tests for controldesk_mcp/com_bridge/domains/calibration_com.py.

All tests mock the COM app object — no ControlDesk required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import controldesk_mcp.com_bridge.domains.calibration_com as cal_com
from controldesk_mcp.com_bridge.errors import BridgeOperationError

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_app() -> MagicMock:
    """Return a minimal mock ControlDesk COM app."""
    app = MagicMock()
    # CalibrationManagement (and ProposedCalibration hangs off it)
    mgmt = MagicMock()
    app.CalibrationManagement = mgmt
    return app


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset calibration_com module-level cache before and after each test."""
    cal_com._calibration_mgmt = None
    cal_com._proposed_calibration = None
    yield
    cal_com._calibration_mgmt = None
    cal_com._proposed_calibration = None


# ── calibration_start ─────────────────────────────────────────────────────────


class TestCalibrationStart:
    def test_returns_started_true(self) -> None:
        app = _make_app()
        result = cal_com.calibration_start(app)
        assert result["started"] is True

    def test_calls_start_online_calibration(self) -> None:
        app = _make_app()
        cal_com.calibration_start(app)
        app.CalibrationManagement.StartOnlineCalibration.assert_called_once()

    def test_caches_management_ref(self) -> None:
        app = _make_app()
        cal_com.calibration_start(app)
        assert cal_com._calibration_mgmt is app.CalibrationManagement

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.StartOnlineCalibration.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.calibration_start(app)

    def test_clears_cache_on_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.StartOnlineCalibration.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.calibration_start(app)
        assert cal_com._calibration_mgmt is None


# ── calibration_stop ──────────────────────────────────────────────────────────


class TestCalibrationStop:
    def test_returns_stopped_true(self) -> None:
        app = _make_app()
        result = cal_com.calibration_stop(app)
        assert result["stopped"] is True

    def test_calls_stop_online_calibration(self) -> None:
        app = _make_app()
        cal_com.calibration_stop(app)
        app.CalibrationManagement.StopOnlineCalibration.assert_called_once()

    def test_uses_cached_mgmt_ref(self) -> None:
        cached = MagicMock()
        cal_com._calibration_mgmt = cached
        app = _make_app()
        cal_com.calibration_stop(app)
        cached.StopOnlineCalibration.assert_called_once()
        # app.CalibrationManagement should NOT have been accessed
        app.CalibrationManagement.StopOnlineCalibration.assert_not_called()

    def test_clears_cache_after_stop(self) -> None:
        app = _make_app()
        cal_com._calibration_mgmt = app.CalibrationManagement
        cal_com.calibration_stop(app)
        assert cal_com._calibration_mgmt is None

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.StopOnlineCalibration.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.calibration_stop(app)


# ── calibration_activate_reference_page ───────────────────────────────────────


class TestCalibrationActivateReferencePage:
    def test_returns_activated_true(self) -> None:
        app = _make_app()
        result = cal_com.calibration_activate_reference_page(app)
        assert result["activated"] is True
        assert result["page"] == "ReferencePage"

    def test_calls_activate_reference_page(self) -> None:
        app = _make_app()
        cal_com.calibration_activate_reference_page(app)
        app.CalibrationManagement.ActivateReferencePageForSupportingPlatforms.assert_called_once()

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        method = app.CalibrationManagement.ActivateReferencePageForSupportingPlatforms
        method.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.calibration_activate_reference_page(app)


# ── calibration_activate_working_page ─────────────────────────────────────────


class TestCalibrationActivateWorkingPage:
    def test_returns_activated_true(self) -> None:
        app = _make_app()
        result = cal_com.calibration_activate_working_page(app)
        assert result["activated"] is True
        assert result["page"] == "WorkingPage"

    def test_calls_activate_working_page(self) -> None:
        app = _make_app()
        cal_com.calibration_activate_working_page(app)
        app.CalibrationManagement.ActivateWorkingPageForSupportingPlatforms.assert_called_once()

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        method = app.CalibrationManagement.ActivateWorkingPageForSupportingPlatforms
        method.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.calibration_activate_working_page(app)


# ── calibration_refresh_parameters ────────────────────────────────────────────


class TestCalibrationRefreshParameters:
    def test_returns_refreshed_true(self) -> None:
        app = _make_app()
        result = cal_com.calibration_refresh_parameters(app)
        assert result["refreshed"] is True
        assert result["timestamp_utc"].endswith("Z")

    def test_calls_refresh_parameters(self) -> None:
        app = _make_app()
        cal_com.calibration_refresh_parameters(app)
        app.CalibrationManagement.RefreshConnectedParameters.assert_called_once()

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.RefreshConnectedParameters.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.calibration_refresh_parameters(app)


# ── proposed_calibration_start ────────────────────────────────────────────────


class TestProposedCalibrationStart:
    def test_returns_started_true(self) -> None:
        app = _make_app()
        result = cal_com.proposed_calibration_start(app)
        assert result["started"] is True
        assert result["proposed_calibration_active"] is True

    def test_calls_start_on_proposed_calibration(self) -> None:
        app = _make_app()
        cal_com.proposed_calibration_start(app)
        app.CalibrationManagement.ProposedCalibration.Start.assert_called_once()

    def test_caches_proposed_calibration_ref(self) -> None:
        app = _make_app()
        cal_com.proposed_calibration_start(app)
        assert cal_com._proposed_calibration is app.CalibrationManagement.ProposedCalibration

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.ProposedCalibration.Start.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.proposed_calibration_start(app)

    def test_clears_cache_on_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.ProposedCalibration.Start.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.proposed_calibration_start(app)
        assert cal_com._proposed_calibration is None


# ── proposed_calibration_stop ─────────────────────────────────────────────────


class TestProposedCalibrationStop:
    def test_returns_stopped_true(self) -> None:
        app = _make_app()
        result = cal_com.proposed_calibration_stop(app)
        assert result["stopped"] is True
        assert result["changes_applied"] is False
        assert result["proposed_calibration_active"] is False

    def test_calls_stop_on_proposed_calibration(self) -> None:
        app = _make_app()
        cal_com.proposed_calibration_stop(app)
        app.CalibrationManagement.ProposedCalibration.Stop.assert_called_once()

    def test_uses_cached_proposed_ref(self) -> None:
        cached = MagicMock()
        cal_com._proposed_calibration = cached
        app = _make_app()
        cal_com.proposed_calibration_stop(app)
        cached.Stop.assert_called_once()
        app.CalibrationManagement.ProposedCalibration.Stop.assert_not_called()

    def test_clears_cache_after_stop(self) -> None:
        app = _make_app()
        cal_com.proposed_calibration_stop(app)
        assert cal_com._proposed_calibration is None

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.ProposedCalibration.Stop.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.proposed_calibration_stop(app)


# ── proposed_calibration_apply ────────────────────────────────────────────────


class TestProposedCalibrationApply:
    def test_returns_applied_true(self) -> None:
        app = _make_app()
        result = cal_com.proposed_calibration_apply(app)
        assert result["applied"] is True
        assert result["proposed_calibration_active"] is False

    def test_calls_apply_on_proposed_calibration(self) -> None:
        app = _make_app()
        cal_com.proposed_calibration_apply(app)
        app.CalibrationManagement.ProposedCalibration.Apply.assert_called_once()

    def test_clears_cache_after_apply(self) -> None:
        app = _make_app()
        cal_com.proposed_calibration_apply(app)
        assert cal_com._proposed_calibration is None

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.ProposedCalibration.Apply.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.proposed_calibration_apply(app)


# ── proposed_calibration_cancel ───────────────────────────────────────────────


class TestProposedCalibrationCancel:
    def test_returns_cancelled_true(self) -> None:
        app = _make_app()
        result = cal_com.proposed_calibration_cancel(app)
        assert result["cancelled"] is True
        assert result["proposed_calibration_active"] is False

    def test_calls_cancel_on_proposed_calibration(self) -> None:
        app = _make_app()
        cal_com.proposed_calibration_cancel(app)
        app.CalibrationManagement.ProposedCalibration.Cancel.assert_called_once()

    def test_clears_cache_after_cancel(self) -> None:
        app = _make_app()
        cal_com.proposed_calibration_cancel(app)
        assert cal_com._proposed_calibration is None

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        app.CalibrationManagement.ProposedCalibration.Cancel.side_effect = Exception("COM error")
        with pytest.raises(BridgeOperationError):
            cal_com.proposed_calibration_cancel(app)


# ── clear_cache ───────────────────────────────────────────────────────────────


class TestClearCache:
    def test_clears_both_caches(self) -> None:
        cal_com._calibration_mgmt = MagicMock()
        cal_com._proposed_calibration = MagicMock()
        cal_com.clear_cache()
        assert cal_com._calibration_mgmt is None
        assert cal_com._proposed_calibration is None


# ── calibration_get_state ─────────────────────────────────────────────────────


class TestCalibrationGetState:
    def test_returns_started_when_state_1(self) -> None:
        app = _make_app()
        app.CalibrationManagement.State = 1
        app.CalibrationManagement.ProposedCalibration.State = 1
        result = cal_com.calibration_get_state(app)
        assert result["calibration_state"] == "Started"
        assert result["calibration_state_raw"] == 1

    def test_returns_stopped_when_state_0(self) -> None:
        app = _make_app()
        app.CalibrationManagement.State = 0
        app.CalibrationManagement.ProposedCalibration.State = 1
        result = cal_com.calibration_get_state(app)
        assert result["calibration_state"] == "Stopped"
        assert result["calibration_state_raw"] == 0

    def test_returns_proposed_active_when_state_0(self) -> None:
        app = _make_app()
        app.CalibrationManagement.State = 1
        app.CalibrationManagement.ProposedCalibration.State = 0
        result = cal_com.calibration_get_state(app)
        assert result["proposed_calibration_state"] == "Active"
        assert result["proposed_calibration_state_raw"] == 0

    def test_returns_proposed_inactive_when_state_1(self) -> None:
        app = _make_app()
        app.CalibrationManagement.State = 1
        app.CalibrationManagement.ProposedCalibration.State = 1
        result = cal_com.calibration_get_state(app)
        assert result["proposed_calibration_state"] == "Inactive"
        assert result["proposed_calibration_state_raw"] == 1

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        state_mock = MagicMock()
        state_mock.__int__ = MagicMock(side_effect=Exception("COM fail"))
        app.CalibrationManagement.State = state_mock
        with pytest.raises(BridgeOperationError):
            cal_com.calibration_get_state(app)


# ── calibration_copy_working_page_to_reference ────────────────────────────────


class TestCalibrationCopyWorkingPageToReference:
    def test_returns_copied_true(self) -> None:
        app = _make_app()
        plat = MagicMock()
        with patch(
            "controldesk_mcp.com_bridge.domains.calibration_com._get_platform",
            return_value=plat,
        ):
            result = cal_com.calibration_copy_working_page_to_reference(app, "XCP")
        assert result["copied"] is True
        assert result["platform_name"] == "XCP"
        assert result["source_page"] == "WorkingPage"
        assert result["target_page"] == "ReferencePage"

    def test_calls_copy_working_to_reference(self) -> None:
        app = _make_app()
        plat = MagicMock()
        with patch(
            "controldesk_mcp.com_bridge.domains.calibration_com._get_platform",
            return_value=plat,
        ):
            cal_com.calibration_copy_working_page_to_reference(app, "XCP")
        plat.CopyWorkingPageToReferencePage.assert_called_once()

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        plat = MagicMock()
        plat.CopyWorkingPageToReferencePage.side_effect = Exception("COM error")
        with patch(
            "controldesk_mcp.com_bridge.domains.calibration_com._get_platform",
            return_value=plat,
        ):
            with pytest.raises(BridgeOperationError):
                cal_com.calibration_copy_working_page_to_reference(app, "XCP")


# ── calibration_copy_reference_page_to_working ────────────────────────────────


class TestCalibrationCopyReferencePageToWorking:
    def test_returns_copied_true(self) -> None:
        app = _make_app()
        plat = MagicMock()
        with patch(
            "controldesk_mcp.com_bridge.domains.calibration_com._get_platform",
            return_value=plat,
        ):
            result = cal_com.calibration_copy_reference_page_to_working(app, "XCP")
        assert result["copied"] is True
        assert result["platform_name"] == "XCP"
        assert result["source_page"] == "ReferencePage"
        assert result["target_page"] == "WorkingPage"

    def test_calls_copy_reference_to_working(self) -> None:
        app = _make_app()
        plat = MagicMock()
        with patch(
            "controldesk_mcp.com_bridge.domains.calibration_com._get_platform",
            return_value=plat,
        ):
            cal_com.calibration_copy_reference_page_to_working(app, "XCP")
        plat.CopyReferencePageToWorkingPage.assert_called_once()

    def test_raises_on_com_error(self) -> None:
        app = _make_app()
        plat = MagicMock()
        plat.CopyReferencePageToWorkingPage.side_effect = Exception("COM error")
        with patch(
            "controldesk_mcp.com_bridge.domains.calibration_com._get_platform",
            return_value=plat,
        ):
            with pytest.raises(BridgeOperationError):
                cal_com.calibration_copy_reference_page_to_working(app, "XCP")
