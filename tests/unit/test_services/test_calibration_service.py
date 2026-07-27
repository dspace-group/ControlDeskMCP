"""Unit tests for controldesk_mcp.services.calibration_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeConnectionError, BridgeOperationError
from controldesk_mcp.models.calibration import (
    CalibrationActivateReferencePageInput,
    CalibrationActivateWorkingPageInput,
    CalibrationRefreshParametersInput,
    CalibrationStartInput,
    CalibrationStopInput,
    ProposedCalibrationApplyInput,
    ProposedCalibrationCancelInput,
    ProposedCalibrationStartInput,
    ProposedCalibrationStopInput,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_bridge():
    bridge._connection = None
    import controldesk_mcp.com_bridge.sta_thread as _sta

    _sta._sta_thread = None
    yield
    bridge._connection = None
    _sta._sta_thread = None


def _make_connected_bridge() -> MagicMock:
    from controldesk_mcp.com_bridge.connection import ConnectionState

    conn = MagicMock()
    conn.state = ConnectionState.CONNECTED
    conn.get_app.return_value = MagicMock()
    bridge._connection = conn
    return conn


# ── Test start_calibration ────────────────────────────────────────────────────


class TestStartCalibration:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"started": True}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import start_calibration

            result = await start_calibration(CalibrationStartInput())

        assert result["started"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("no connection"),
        ):
            from controldesk_mcp.services.calibration_service import start_calibration

            result = await start_calibration(CalibrationStartInput())

        assert result.get("category") is not None


# ── Test stop_calibration ─────────────────────────────────────────────────────


class TestStopCalibration:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"stopped": True}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import stop_calibration

            result = await stop_calibration(CalibrationStopInput())

        assert result["stopped"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[
                MagicMock(),
                BridgeOperationError("stop failed"),
            ],
        ):
            from controldesk_mcp.services.calibration_service import stop_calibration

            result = await stop_calibration(CalibrationStopInput())

        assert result.get("category") is not None


# ── Test activate_reference_page ──────────────────────────────────────────────


class TestActivateReferencePage:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"activated": True, "page": "ReferencePage"}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import activate_reference_page

            result = await activate_reference_page(CalibrationActivateReferencePageInput())

        assert result["activated"] is True
        assert result["page"] == "ReferencePage"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[
                MagicMock(),
                BridgeOperationError("ref page failed"),
            ],
        ):
            from controldesk_mcp.services.calibration_service import activate_reference_page

            result = await activate_reference_page(CalibrationActivateReferencePageInput())

        assert result.get("category") is not None


# ── Test activate_working_page ────────────────────────────────────────────────


class TestActivateWorkingPage:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"activated": True, "page": "WorkingPage"}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import activate_working_page

            result = await activate_working_page(CalibrationActivateWorkingPageInput())

        assert result["activated"] is True
        assert result["page"] == "WorkingPage"


# ── Test refresh_parameters ───────────────────────────────────────────────────


class TestRefreshParameters:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"refreshed": True, "timestamp_utc": "2026-05-04T10:00:00.000Z"}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import refresh_parameters

            result = await refresh_parameters(CalibrationRefreshParametersInput())

        assert result["refreshed"] is True
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[
                MagicMock(),
                BridgeOperationError("refresh failed"),
            ],
        ):
            from controldesk_mcp.services.calibration_service import refresh_parameters

            result = await refresh_parameters(CalibrationRefreshParametersInput())

        assert result.get("category") is not None


# ── Test start_proposed_calibration ──────────────────────────────────────────


class TestStartProposedCalibration:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"started": True, "proposed_calibration_active": True}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import start_proposed_calibration

            result = await start_proposed_calibration(ProposedCalibrationStartInput())

        assert result["started"] is True
        assert result["proposed_calibration_active"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("no connection"),
        ):
            from controldesk_mcp.services.calibration_service import start_proposed_calibration

            result = await start_proposed_calibration(ProposedCalibrationStartInput())

        assert result.get("category") is not None


# ── Test stop_proposed_calibration ────────────────────────────────────────────


class TestStopProposedCalibration:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "stopped": True,
            "changes_applied": False,
            "proposed_calibration_active": False,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import stop_proposed_calibration

            result = await stop_proposed_calibration(ProposedCalibrationStopInput())

        assert result["stopped"] is True
        assert result["changes_applied"] is False
        assert result["proposed_calibration_active"] is False


# ── Test apply_proposed_calibration ──────────────────────────────────────────


class TestApplyProposedCalibration:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"applied": True, "proposed_calibration_active": False}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import apply_proposed_calibration

            result = await apply_proposed_calibration(ProposedCalibrationApplyInput())

        assert result["applied"] is True
        assert result["proposed_calibration_active"] is False

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[
                MagicMock(),
                BridgeOperationError("apply failed"),
            ],
        ):
            from controldesk_mcp.services.calibration_service import apply_proposed_calibration

            result = await apply_proposed_calibration(ProposedCalibrationApplyInput())

        assert result.get("category") is not None


# ── Test cancel_proposed_calibration ─────────────────────────────────────────


class TestCancelProposedCalibration:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"cancelled": True, "proposed_calibration_active": False}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.calibration_service import cancel_proposed_calibration

            result = await cancel_proposed_calibration(ProposedCalibrationCancelInput())

        assert result["cancelled"] is True
        assert result["proposed_calibration_active"] is False

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[
                MagicMock(),
                BridgeOperationError("cancel failed"),
            ],
        ):
            from controldesk_mcp.services.calibration_service import cancel_proposed_calibration

            result = await cancel_proposed_calibration(ProposedCalibrationCancelInput())

        assert result.get("category") is not None


# ── dry_run_start_calibration ──────────────────────────────────────────────────


class TestDryRunStartCalibration:
    @pytest.mark.asyncio
    async def test_reports_would_execute_when_stopped(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        state = {
            "calibration_state": "Stopped",
            "calibration_state_raw": 0,
            "proposed_calibration_state": "Inactive",
            "proposed_calibration_state_raw": 1,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, state],
        ):
            from controldesk_mcp.services.calibration_service import dry_run_start_calibration

            result = await dry_run_start_calibration(CalibrationStartInput(dry_run=True))

        assert result["would_execute"] is True

    @pytest.mark.asyncio
    async def test_reports_would_not_execute_when_already_started(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        state = {
            "calibration_state": "Started",
            "calibration_state_raw": 1,
            "proposed_calibration_state": "Inactive",
            "proposed_calibration_state_raw": 1,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, state],
        ):
            from controldesk_mcp.services.calibration_service import dry_run_start_calibration

            result = await dry_run_start_calibration(CalibrationStartInput(dry_run=True))

        assert result["would_execute"] is False
