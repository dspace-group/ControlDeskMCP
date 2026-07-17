"""Unit tests for sources.services.bus_replay_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sources.com_bridge as bridge
from sources.com_bridge.errors import BridgeConnectionError, BridgeOperationError
from sources.models.bus_replay import (
    BusReplayClearAllInput,
    BusReplayConfigureInput,
    BusReplayCreateInput,
    BusReplayGetStateInput,
    BusReplayListInput,
    BusReplayRemoveInput,
    BusReplaySetActivatedInput,
    BusReplayStartInput,
    BusReplayStopInput,
    BusType,
    ReplayMode,
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


# ── Test create_replay ────────────────────────────────────────────────────────


class TestCreateReplay:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "created": True,
            "replay_name": "CANReplay",
            "system_index": 0,
            "bus_type": "CAN",
            "state": "Stopped",
            "activated": False,
            "timestamp_utc": "2026-04-28T14:37:01.123Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import create_replay

            result = await create_replay(
                BusReplayCreateInput(replay_name="CANReplay", system_index=0, bus_type=BusType.CAN)
            )

        assert result["replay_name"] == "CANReplay"
        assert result["created"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("no connection"),
        ):
            from sources.services.bus_replay_service import create_replay

            result = await create_replay(
                BusReplayCreateInput(replay_name="CANReplay", system_index=0, bus_type=BusType.CAN)
            )

        assert result.get("category") is not None


# ── Test configure_replay ─────────────────────────────────────────────────────


class TestConfigureReplay:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "configured": True,
            "replay_name": "CANReplay",
            "log_file_full_path": "C:\\Logs\\recorded.asc",
            "replay_mode": "NumberOfPasses",
            "number_of_passes": 3,
            "duration_seconds": 0.0,
            "start_monitor_on_replay": False,
            "timestamp_utc": "2026-04-28T14:37:02.456Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import configure_replay

            result = await configure_replay(
                BusReplayConfigureInput(
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                    log_file_full_path="C:\\Logs\\recorded.asc",
                    replay_mode=ReplayMode.NumberOfPasses,
                    number_of_passes=3,
                )
            )

        assert result["configured"] is True
        assert result["number_of_passes"] == 3

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[
                MagicMock(),  # First call: get_app
                BridgeOperationError("config failed"),  # Second call: COM
            ],
        ):
            from sources.services.bus_replay_service import configure_replay

            result = await configure_replay(
                BusReplayConfigureInput(
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                    log_file_full_path="C:\\Logs\\recorded.asc",
                    replay_mode=ReplayMode.Infinite,
                )
            )

        assert result.get("category") is not None


# ── Test start_replay ─────────────────────────────────────────────────────────


class TestStartReplay:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "started": True,
            "replay_name": "CANReplay",
            "state": "Running",
            "activated": True,
            "timestamp_utc": "2026-04-28T14:37:03.789Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import start_replay

            result = await start_replay(
                BusReplayStartInput(replay_name="CANReplay", system_index=0, bus_type=BusType.CAN)
            )

        assert result["started"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[
                MagicMock(),  # First call: get_app
                BridgeOperationError("start failed"),  # Second call: COM
            ],
        ):
            from sources.services.bus_replay_service import start_replay

            result = await start_replay(
                BusReplayStartInput(replay_name="CANReplay", system_index=0, bus_type=BusType.CAN)
            )

        assert result.get("category") is not None


# ── Test stop_replay ──────────────────────────────────────────────────────────


class TestStopReplay:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "stopped": True,
            "replay_name": "CANReplay",
            "state": "Stopped",
            "activated": False,
            "timestamp_utc": "2026-04-28T14:37:04.123Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import stop_replay

            result = await stop_replay(
                BusReplayStopInput(replay_name="CANReplay", system_index=0, bus_type=BusType.CAN)
            )

        assert result["stopped"] is True
        assert result["state"] == "Stopped"


# ── Test get_replay_state ─────────────────────────────────────────────────────


class TestGetReplayState:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "replay_name": "CANReplay",
            "state": "Running",
            "is_running": True,
            "activated": True,
            "log_file_path": "C:\\Logs\\recorded.asc",
            "replay_mode": "NumberOfPasses",
            "timestamp_utc": "2026-04-28T14:37:05.456Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import get_replay_state

            result = await get_replay_state(
                BusReplayGetStateInput(
                    replay_name="CANReplay", system_index=0, bus_type=BusType.CAN
                )
            )

        assert result["is_running"] is True
        assert result["activated"] is True


# ── Test list_replays ────────────────────────────────────────────────────────


class TestListReplays:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "system_index": 0,
            "bus_type": "CAN",
            "total_count": 2,
            "replays": [
                {
                    "name": "CANReplay",
                    "state": "Running",
                    "activated": True,
                    "log_file_path": "C:\\Logs\\recorded.asc",
                    "replay_mode": "NumberOfPasses",
                },
                {
                    "name": "ScenarioPlayback",
                    "state": "Stopped",
                    "activated": False,
                    "log_file_path": "C:\\Logs\\scenario.blf",
                    "replay_mode": "Duration",
                },
            ],
            "timestamp_utc": "2026-04-28T14:37:05.456Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import list_replays

            result = await list_replays(BusReplayListInput(system_index=0, bus_type=BusType.CAN))

        assert result["total_count"] == 2
        assert len(result["replays"]) == 2

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_no_replays(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "system_index": 0,
            "bus_type": "CAN",
            "total_count": 0,
            "replays": [],
            "timestamp_utc": "2026-04-28T14:37:05.456Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import list_replays

            result = await list_replays(BusReplayListInput(system_index=0, bus_type=BusType.CAN))

        assert result["total_count"] == 0
        assert result["replays"] == []


# ── Test remove_replay ────────────────────────────────────────────────────────


class TestRemoveReplay:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "removed": True,
            "replay_name": "CANReplay",
            "timestamp_utc": "2026-04-28T14:37:06.789Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import remove_replay

            result = await remove_replay(
                BusReplayRemoveInput(replay_name="CANReplay", system_index=0, bus_type=BusType.CAN)
            )

        assert result["removed"] is True


# ── Test clear_all_replays ───────────────────────────────────────────────────


class TestClearAllReplays:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success_with_confirm(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "cleared": True,
            "replays_removed": 2,
            "system_index": 0,
            "bus_type": "CAN",
            "timestamp_utc": "2026-04-28T14:37:07.123Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import clear_all_replays

            result = await clear_all_replays(
                BusReplayClearAllInput(system_index=0, bus_type=BusType.CAN, confirm=True)
            )

        assert result["cleared"] is True
        assert result["replays_removed"] == 2

    @pytest.mark.asyncio
    async def test_returns_aborted_without_confirm(self) -> None:
        _make_connected_bridge()

        with patch("sources.com_bridge.dispatch", new_callable=AsyncMock):
            from sources.services.bus_replay_service import clear_all_replays

            result = await clear_all_replays(
                BusReplayClearAllInput(system_index=0, bus_type=BusType.CAN, confirm=False)
            )

        assert result["cleared"] is False
        assert "confirm" in result["message"].lower()


# ── Test set_replay_activated ─────────────────────────────────────────────────


class TestSetReplayActivated:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "activated": True,
            "replay_name": "CANReplay",
            "state": "Stopped",
            "previous_activated": False,
            "timestamp_utc": "2026-04-28T14:45:08.912Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.bus_replay_service import set_replay_activated

            result = await set_replay_activated(
                BusReplaySetActivatedInput(
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                    activated=True,
                )
            )

        assert result["activated"] is True
        assert result["previous_activated"] is False


# ── dry_run_create_replay ───────────────────────────────────────────────────────


class TestDryRunCreateReplay:
    @pytest.mark.asyncio
    async def test_reports_would_execute_when_no_conflict(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("Replay 'CANReplay' not found."),
        ):
            from sources.services.bus_replay_service import dry_run_create_replay

            result = await dry_run_create_replay(
                BusReplayCreateInput(
                    replay_name="CANReplay", system_index=0, bus_type=BusType.CAN, dry_run=True
                )
            )

        assert result["would_execute"] is True
        assert result["current_state"]["already_exists"] is False

    @pytest.mark.asyncio
    async def test_reports_would_not_execute_when_already_exists(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        existing_state = {
            "replay_name": "CANReplay",
            "state": "Stopped",
            "is_running": False,
            "activated": False,
            "log_file_path": "",
            "replay_mode": "Infinite",
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, existing_state],
        ):
            from sources.services.bus_replay_service import dry_run_create_replay

            result = await dry_run_create_replay(
                BusReplayCreateInput(
                    replay_name="CANReplay", system_index=0, bus_type=BusType.CAN, dry_run=True
                )
            )

        assert result["would_execute"] is False
        assert result["current_state"]["already_exists"] is True
