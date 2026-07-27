"""Unit tests for controldesk_mcp.services.recorder_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeOperationError
from controldesk_mcp.models.recorder import (
    RecorderMainAddSignalInput,
    RecorderMainConfigureInput,
    RecorderMainExportInput,
    RecorderMainGetStateInput,
    RecorderMainImportSignalsInput,
    RecorderMainInvokeTriggerInput,
    RecorderMainListSignalsInput,
    RecorderMainRemoveSignalInput,
    RecorderMainStartInput,
    RecorderMainStopInput,
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


# ── Test configure_main_recorder ─────────────────────────────────────────────


class TestConfigureMainRecorder:
    @pytest.mark.asyncio
    async def test_returns_configured_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "configured": True,
            "base_filename": "Recording.mf4",
            "automatic_naming_enabled": False,
            "add_to_experiment_enabled": False,
            "open_in_data_pool_enabled": False,
            "write_to_file_enabled": True,
            "automatic_signal_configuration_enabled": True,
            "description": "",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import configure_main_recorder

            result = await configure_main_recorder(
                RecorderMainConfigureInput(base_filename="Recording.mf4")
            )

        assert result["configured"] is True
        assert result["base_filename"] == "Recording.mf4"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("configure failed"),
        ):
            from controldesk_mcp.services.recorder_service import configure_main_recorder

            result = await configure_main_recorder(
                RecorderMainConfigureInput(base_filename="Recording.mf4")
            )

        assert result.get("category") is not None


# ── Test add_signal ───────────────────────────────────────────────────────────


class TestAddSignal:
    @pytest.mark.asyncio
    async def test_returns_added_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "added": True,
            "connection_path": "XCP(5ms)://control_out",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import add_signal

            result = await add_signal(
                RecorderMainAddSignalInput(connection_path="XCP(5ms)://control_out")
            )

        assert result["added"] is True
        assert result["connection_path"] == "XCP(5ms)://control_out"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("add signal failed"),
        ):
            from controldesk_mcp.services.recorder_service import add_signal

            result = await add_signal(
                RecorderMainAddSignalInput(connection_path="XCP(5ms)://control_out")
            )

        assert result.get("category") is not None


# ── Test remove_signal ────────────────────────────────────────────────────────


class TestRemoveSignal:
    @pytest.mark.asyncio
    async def test_returns_removed_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "removed": True,
            "connection_path": "XCP(5ms)://control_out",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import remove_signal

            result = await remove_signal(
                RecorderMainRemoveSignalInput(connection_path="XCP(5ms)://control_out")
            )

        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("remove signal failed"),
        ):
            from controldesk_mcp.services.recorder_service import remove_signal

            result = await remove_signal(
                RecorderMainRemoveSignalInput(connection_path="XCP(5ms)://control_out")
            )

        assert result.get("category") is not None


# ── Test list_signals ─────────────────────────────────────────────────────────


class TestListSignals:
    @pytest.mark.asyncio
    async def test_returns_signals_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "total_count": 1,
            "signals": [
                {
                    "connection_path": "XCP(5ms)://control_out",
                    "variable_name": "control_out",
                    "platform_name": "XCP",
                    "raster_name": "5ms",
                    "active": True,
                    "recording_enabled": True,
                }
            ],
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import list_signals

            result = await list_signals(RecorderMainListSignalsInput())

        assert result["total_count"] == 1
        assert len(result["signals"]) == 1

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("list signals failed"),
        ):
            from controldesk_mcp.services.recorder_service import list_signals

            result = await list_signals(RecorderMainListSignalsInput())

        assert result.get("category") is not None


# ── Test start_recorder ───────────────────────────────────────────────────────


class TestStartRecorder:
    @pytest.mark.asyncio
    async def test_returns_started_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "started": True,
            "base_filename": "Recording.mf4",
            "with_trigger": False,
            "state": "Running",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import start_recorder

            result = await start_recorder(RecorderMainStartInput())

        assert result["started"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("start failed"),
        ):
            from controldesk_mcp.services.recorder_service import start_recorder

            result = await start_recorder(RecorderMainStartInput())

        assert result.get("category") is not None


# ── Test stop_recorder ────────────────────────────────────────────────────────


class TestStopRecorder:
    @pytest.mark.asyncio
    async def test_returns_stopped_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "stopped": True,
            "output_files": ["Recording.mf4"],
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import stop_recorder

            result = await stop_recorder(RecorderMainStopInput())

        assert result["stopped"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("stop failed"),
        ):
            from controldesk_mcp.services.recorder_service import stop_recorder

            result = await stop_recorder(RecorderMainStopInput())

        assert result.get("category") is not None


# ── Test get_state ────────────────────────────────────────────────────────────


class TestGetState:
    @pytest.mark.asyncio
    async def test_returns_state_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "state": "Running",
            "is_running": True,
            "last_recorded_files": ["Recording.mf4"],
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import get_state

            result = await get_state(RecorderMainGetStateInput())

        assert result["state"] == "Running"
        assert result["is_running"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("get state failed"),
        ):
            from controldesk_mcp.services.recorder_service import get_state

            result = await get_state(RecorderMainGetStateInput())

        assert result.get("category") is not None


# ── Test invoke_trigger ───────────────────────────────────────────────────────


class TestInvokeTrigger:
    @pytest.mark.asyncio
    async def test_returns_triggered_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "triggered": True,
            "state": "Running",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import invoke_trigger

            result = await invoke_trigger(RecorderMainInvokeTriggerInput())

        assert result["triggered"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("invoke trigger failed"),
        ):
            from controldesk_mcp.services.recorder_service import invoke_trigger

            result = await invoke_trigger(RecorderMainInvokeTriggerInput())

        assert result.get("category") is not None


# ── Test export_recorder ──────────────────────────────────────────────────────


class TestExportRecorder:
    @pytest.mark.asyncio
    async def test_returns_exported_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "exported": True,
            "full_path": "C:\\\\Recordings\\\\cfg.mf4r",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import export_recorder

            result = await export_recorder(
                RecorderMainExportInput(full_path="C:\\\\Recordings\\\\cfg.mf4r")
            )

        assert result["exported"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("export failed"),
        ):
            from controldesk_mcp.services.recorder_service import export_recorder

            result = await export_recorder(RecorderMainExportInput(full_path="C:\\\\cfg.mf4r"))

        assert result.get("category") is not None


# ── Test import_signals_from_file ─────────────────────────────────────────────


class TestImportSignalsFromFile:
    @pytest.mark.asyncio
    async def test_returns_imported_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "imported": True,
            "full_path": "C:\\\\Recordings\\\\cfg.mf4r",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from controldesk_mcp.services.recorder_service import import_signals_from_file

            result = await import_signals_from_file(
                RecorderMainImportSignalsInput(full_path="C:\\\\Recordings\\\\cfg.mf4r")
            )

        assert result["imported"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("import failed"),
        ):
            from controldesk_mcp.services.recorder_service import import_signals_from_file

            result = await import_signals_from_file(
                RecorderMainImportSignalsInput(full_path="C:\\\\cfg.mf4r")
            )

        assert result.get("category") is not None


# ── dry_run_start_recorder / dry_run_stop_recorder ────────────────────────────


class TestDryRunStartRecorder:
    @pytest.mark.asyncio
    async def test_reports_would_execute_when_not_running(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        state = {
            "state": "Stopped",
            "is_running": False,
            "last_recorded_files": [],
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, state],
        ):
            from controldesk_mcp.services.recorder_service import dry_run_start_recorder

            result = await dry_run_start_recorder(RecorderMainStartInput(dry_run=True))

        assert result["would_execute"] is True
        assert result["current_state"]["is_running"] is False

    @pytest.mark.asyncio
    async def test_reports_would_not_execute_when_already_running(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        state = {
            "state": "Running",
            "is_running": True,
            "last_recorded_files": [],
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, state],
        ):
            from controldesk_mcp.services.recorder_service import dry_run_start_recorder

            result = await dry_run_start_recorder(RecorderMainStartInput(dry_run=True))

        assert result["would_execute"] is False


class TestDryRunStopRecorder:
    @pytest.mark.asyncio
    async def test_reports_would_execute_when_running(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        state = {
            "state": "Running",
            "is_running": True,
            "last_recorded_files": [],
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, state],
        ):
            from controldesk_mcp.services.recorder_service import dry_run_stop_recorder

            result = await dry_run_stop_recorder(RecorderMainStopInput(dry_run=True))

        assert result["would_execute"] is True

    @pytest.mark.asyncio
    async def test_reports_would_not_execute_when_not_running(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        state = {
            "state": "Stopped",
            "is_running": False,
            "last_recorded_files": [],
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, state],
        ):
            from controldesk_mcp.services.recorder_service import dry_run_stop_recorder

            result = await dry_run_stop_recorder(RecorderMainStopInput(dry_run=True))

        assert result["would_execute"] is False
