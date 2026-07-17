"""Unit tests for sources.services.bus_monitor_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sources.com_bridge as bridge
from sources.com_bridge.errors import BridgeConnectionError, BridgeOperationError
from sources.models.bus_monitor import (
    BusMonitorClearAllInput,
    BusMonitorCreateInput,
    BusMonitorListInput,
    BusMonitorStartInput,
    BusType,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_bridge():
    bridge._connection = None
    import sources.com_bridge.sta_thread as _sta

    _sta._sta_thread = None
    yield
    bridge._connection = None
    _sta._sta_thread = None


def _make_connected_bridge() -> MagicMock:
    from sources.com_bridge.connection import ConnectionState

    conn = MagicMock()
    conn.state = ConnectionState.CONNECTED
    conn.get_app.return_value = MagicMock()
    bridge._connection = conn
    return conn


# ── create_monitor ────────────────────────────────────────────────────────────


class TestCreateMonitor:
    @pytest.mark.asyncio
    async def test_returns_monitor_result_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"monitor_name": "CANMonitor", "system_index": 0, "bus_type": "CAN"}

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.bus_monitor_service import create_monitor

            result = await create_monitor(
                BusMonitorCreateInput(
                    monitor_name="CANMonitor", system_index=0, bus_type=BusType.CAN
                )
            )

        assert result["monitor_name"] == "CANMonitor"
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("disc"),
        ):
            from sources.services.bus_monitor_service import create_monitor

            result = await create_monitor(
                BusMonitorCreateInput(
                    monitor_name="CANMonitor", system_index=0, bus_type=BusType.CAN
                )
            )

        assert "error_code" in result


# ── start_monitor ─────────────────────────────────────────────────────────────


class TestStartMonitor:
    @pytest.mark.asyncio
    async def test_returns_start_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, None],
        ):
            from sources.services.bus_monitor_service import start_monitor

            result = await start_monitor(
                BusMonitorStartInput(
                    monitor_name="CANMonitor", system_index=0, bus_type=BusType.CAN
                )
            )

        assert result["monitor_name"] == "CANMonitor"
        assert "timestamp_utc" in result


# ── list_monitors ─────────────────────────────────────────────────────────────


class TestListMonitors:
    @pytest.mark.asyncio
    async def test_returns_monitors_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, [{"monitor_name": "CANMonitor"}]],
        ):
            from sources.services.bus_monitor_service import list_monitors

            result = await list_monitors(BusMonitorListInput(system_index=0, bus_type=BusType.CAN))

        assert result["total_count"] == 1


# ── clear_all_monitors — confirm guard ────────────────────────────────────────


class TestClearAllMonitors:
    @pytest.mark.asyncio
    async def test_aborts_without_confirm(self) -> None:
        _make_connected_bridge()

        from sources.services.bus_monitor_service import clear_all_monitors

        result = await clear_all_monitors(
            BusMonitorClearAllInput(confirm=False, system_index=0, bus_type=BusType.CAN)
        )

        assert result.get("cleared") is False or "aborted" in str(result).lower()


# ── dry_run_create_monitor ──────────────────────────────────────────


class TestDryRunCreateMonitor:
    @pytest.mark.asyncio
    async def test_reports_would_execute_when_no_conflict(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("Monitor 'CANMonitor' not found."),
        ):
            from sources.services.bus_monitor_service import dry_run_create_monitor

            result = await dry_run_create_monitor(
                BusMonitorCreateInput(
                    monitor_name="CANMonitor", system_index=0, bus_type=BusType.CAN, dry_run=True
                )
            )

        assert result["would_execute"] is True
        assert result["current_state"]["already_exists"] is False

    @pytest.mark.asyncio
    async def test_reports_would_not_execute_when_already_exists(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        existing_state = {
            "monitor_name": "CANMonitor",
            "state": "Stopped",
            "is_running": False,
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, existing_state],
        ):
            from sources.services.bus_monitor_service import dry_run_create_monitor

            result = await dry_run_create_monitor(
                BusMonitorCreateInput(
                    monitor_name="CANMonitor", system_index=0, bus_type=BusType.CAN, dry_run=True
                )
            )

        assert result["would_execute"] is False
        assert result["current_state"]["already_exists"] is True
