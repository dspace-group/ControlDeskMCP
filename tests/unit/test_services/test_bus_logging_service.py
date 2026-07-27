"""Unit tests for controldesk_mcp.services.bus_logging_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeConnectionError, BridgeOperationError
from controldesk_mcp.models.bus_logging import (
    BusLoggerClearAllInput,
    BusLoggerCreateInput,
    BusLoggerListInput,
    BusType,
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


# ── create_logger ─────────────────────────────────────────────────────────────


class TestCreateLogger:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "logger_name": "CANRecorder",
            "system_index": 0,
            "bus_type": "CAN",
            "created": True,
            "state": "Stopped",
            "activated": False,
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.bus_logging_service import create_logger

            result = await create_logger(
                BusLoggerCreateInput(logger_name="CANRecorder", system_index=0, bus_type=BusType.CAN)
            )

        assert result["logger_name"] == "CANRecorder"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("no connection"),
        ):
            from controldesk_mcp.services.bus_logging_service import create_logger

            result = await create_logger(
                BusLoggerCreateInput(logger_name="CANRecorder", system_index=0, bus_type=BusType.CAN)
            )

        assert "error_code" in result


# ── list_loggers ──────────────────────────────────────────────────────────────


class TestListLoggers:
    @pytest.mark.asyncio
    async def test_returns_loggers_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "loggers": [{"logger_name": "CANRecorder", "state": "Stopped", "activated": False}],
            "count": 1,
            "system_index": 0,
            "bus_type": "CAN",
            "total_count": 1,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.bus_logging_service import list_loggers

            result = await list_loggers(BusLoggerListInput(system_index=0, bus_type=BusType.CAN))

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("op failed", error_code="BRIDGE_OPERATION"),
        ):
            from controldesk_mcp.services.bus_logging_service import list_loggers

            result = await list_loggers(BusLoggerListInput(system_index=0, bus_type=BusType.CAN))

        assert "error_code" in result


# ── clear_all_loggers — confirm guard ─────────────────────────────────────────


class TestClearAllLoggers:
    @pytest.mark.asyncio
    async def test_aborts_without_confirm(self) -> None:
        _make_connected_bridge()

        from controldesk_mcp.services.bus_logging_service import clear_all_loggers

        result = await clear_all_loggers(BusLoggerClearAllInput(confirm=False, system_index=0, bus_type=BusType.CAN))

        assert result["cleared"] is False

    @pytest.mark.asyncio
    async def test_clears_when_confirmed(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "cleared": True,
            "count": 2,
            "loggers_removed": 2,
            "system_index": 0,
            "bus_type": "CAN",
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.bus_logging_service import clear_all_loggers

            result = await clear_all_loggers(BusLoggerClearAllInput(confirm=True, system_index=0, bus_type=BusType.CAN))

        assert result["cleared"] is True


# ── dry_run_create_logger ──────────────────────────────────────────────────────


class TestDryRunCreateLogger:
    @pytest.mark.asyncio
    async def test_reports_would_execute_when_no_conflict(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("Logger 'CANRecorder' not found."),
        ):
            from controldesk_mcp.services.bus_logging_service import dry_run_create_logger

            result = await dry_run_create_logger(
                BusLoggerCreateInput(logger_name="CANRecorder", system_index=0, bus_type=BusType.CAN, dry_run=True)
            )

        assert result["dry_run"] is True
        assert result["would_execute"] is True
        assert result["current_state"]["already_exists"] is False

    @pytest.mark.asyncio
    async def test_reports_would_not_execute_when_already_exists(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        existing_state = {
            "logger_name": "CANRecorder",
            "state": "Stopped",
            "is_running": False,
            "activated": False,
            "log_file_path": "",
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, existing_state],
        ):
            from controldesk_mcp.services.bus_logging_service import dry_run_create_logger

            result = await dry_run_create_logger(
                BusLoggerCreateInput(logger_name="CANRecorder", system_index=0, bus_type=BusType.CAN, dry_run=True)
            )

        assert result["would_execute"] is False
        assert result["current_state"]["already_exists"] is True
