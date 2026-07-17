"""Unit tests for sources.services.measurement_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sources.com_bridge as bridge
from sources.com_bridge.errors import BridgeConnectionError, BridgeOperationError
from sources.models.measurement import (
    DataLoggerConfigureInput,
    DataLoggerCreateInput,
    DataLoggerListInput,
    DataLoggerRemoveInput,
    DataLoggerStartInput,
    DataLoggerStopInput,
    MeasurementBookmarkAddInput,
    MeasurementBookmarkListInput,
    MeasurementBookmarkRemoveInput,
    MeasurementConfigureBufferInput,
    MeasurementConfigureSettingsInput,
    MeasurementExportRecordingInput,
    MeasurementGetConfigurationInput,
    MeasurementGetStateInput,
    MeasurementImportRecordingInput,
    MeasurementListRecordingsInput,
    MeasurementListSignalsInput,
    MeasurementRasterAddInput,
    MeasurementRasterListInput,
    MeasurementRasterRemoveInput,
    MeasurementSignalAddInput,
    MeasurementSignalRemoveInput,
    MeasurementStartInput,
    MeasurementStopInput,
    TriggerConditionTimeLimitInput,
    TriggerConditionTriggerBasedInput,
    TriggerRuleCreateInput,
    TriggerRuleRemoveInput,
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


# ── Test signal_add ───────────────────────────────────────────────────────────


class TestSignalAdd:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "added": True,
            "connection_path": "XCP(5ms)://control_out",
            "variable_name": "control_out",
            "platform_name": "XCP",
            "raster_name": "5ms",
            "is_connected": True,
            "active": True,
            "recording_enabled": True,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import signal_add

            result = await signal_add(
                MeasurementSignalAddInput(connection_path="XCP(5ms)://control_out")
            )

        assert result["added"] is True
        assert result["connection_path"] == "XCP(5ms)://control_out"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("signal add failed"),
        ):
            from sources.services.measurement_service import signal_add

            result = await signal_add(
                MeasurementSignalAddInput(connection_path="XCP(5ms)://control_out")
            )

        assert result.get("category") is not None


# ── Test signal_remove ────────────────────────────────────────────────────────


class TestSignalRemove:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "removed": True,
            "connection_path": "XCP(5ms)://control_out",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import signal_remove

            result = await signal_remove(
                MeasurementSignalRemoveInput(connection_path="XCP(5ms)://control_out")
            )

        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("remove failed")],
        ):
            from sources.services.measurement_service import signal_remove

            result = await signal_remove(
                MeasurementSignalRemoveInput(connection_path="XCP(5ms)://control_out")
            )

        assert result.get("category") is not None


# ── Test list_signals ─────────────────────────────────────────────────────────


class TestListSignals:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "total_count": 1,
            "signals": [{"connection_path": "XCP(5ms)://control_out"}],
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import list_signals

            result = await list_signals(MeasurementListSignalsInput())

        assert result["total_count"] == 1


# ── Test configure_buffer ─────────────────────────────────────────────────────


class TestConfigureBuffer:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "configured": True,
            "buffer_size_seconds": 10.0,
            "warning_enabled": False,
            "warning_time_seconds": 3.0,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import configure_buffer

            result = await configure_buffer(
                MeasurementConfigureBufferInput(buffer_size_seconds=10.0)
            )

        assert result["configured"] is True
        assert result["buffer_size_seconds"] == 10.0

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("buffer config failed")],
        ):
            from sources.services.measurement_service import configure_buffer

            result = await configure_buffer(
                MeasurementConfigureBufferInput(buffer_size_seconds=10.0)
            )

        assert result.get("category") is not None


# ── Test get_configuration ────────────────────────────────────────────────────


class TestGetConfiguration:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "buffer": {
                "size_seconds": 10.0,
                "warning_enabled": False,
                "warning_time_seconds": 3.0,
            },
            "signal_count": 0,
            "signals": [],
            "platforms_connected": ["XCP"],
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import get_configuration

            result = await get_configuration(MeasurementGetConfigurationInput())

        assert "buffer" in result
        assert result["signal_count"] == 0


# ── Test start_measurement ────────────────────────────────────────────────────


class TestStartMeasurement:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "started": True,
            "platforms_measuring": ["XCP"],
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import start_measurement

            result = await start_measurement(MeasurementStartInput())

        assert result["started"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("no connection"),
        ):
            from sources.services.measurement_service import start_measurement

            result = await start_measurement(MeasurementStartInput())

        assert result.get("category") is not None


# ── Test stop_measurement ─────────────────────────────────────────────────────


class TestStopMeasurement:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {"stopped": True, "timestamp_utc": "2026-05-04T10:00:00.000Z"}

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import stop_measurement

            result = await stop_measurement(MeasurementStopInput())

        assert result["stopped"] is True


# ── Test get_measurement_state ────────────────────────────────────────────────


class TestGetMeasurementState:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "state": "Measuring",
            "is_measuring": True,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import get_measurement_state

            result = await get_measurement_state(MeasurementGetStateInput())

        assert result["state"] == "Measuring"
        assert result["is_measuring"] is True


# ── Test create_trigger_rule ──────────────────────────────────────────────────


class TestCreateTriggerRule:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "created": True,
            "rule_name": "StartCondition",
            "expression": "control_out < -0.1",
            "mappings": {"control_out": "XCP(5ms)://control_out"},
            "enabled": True,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import create_trigger_rule

            result = await create_trigger_rule(
                TriggerRuleCreateInput(
                    rule_name="StartCondition",
                    expression="control_out < -0.1",
                    signal_mappings={"control_out": "XCP(5ms)://control_out"},
                )
            )

        assert result["created"] is True
        assert result["rule_name"] == "StartCondition"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("rule create failed")],
        ):
            from sources.services.measurement_service import create_trigger_rule

            result = await create_trigger_rule(
                TriggerRuleCreateInput(
                    rule_name="StartCondition",
                    expression="control_out < -0.1",
                    signal_mappings={"control_out": "XCP(5ms)://control_out"},
                )
            )

        assert result["category"] is not None


# ── Test remove_trigger_rule ──────────────────────────────────────────────────


class TestRemoveTriggerRule:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "removed": True,
            "rule_name": "StartCondition",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import remove_trigger_rule

            result = await remove_trigger_rule(TriggerRuleRemoveInput(rule_name="StartCondition"))

        assert result["removed"] is True


# ── Test configure_time_limit_condition ───────────────────────────────────────


class TestConfigureTimeLimitCondition:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "configured": True,
            "condition_type": "TimeLimit",
            "enabled": True,
            "time_limit_seconds": 10.0,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import (
                configure_time_limit_condition,
            )

            result = await configure_time_limit_condition(
                TriggerConditionTimeLimitInput(enabled=True, time_limit_seconds=10.0)
            )

        assert result["configured"] is True
        assert result["condition_type"] == "TimeLimit"


# ── Test configure_trigger_based_condition ────────────────────────────────────


class TestConfigureTriggerBasedCondition:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "configured": True,
            "condition_type": "start",
            "rule_name": "StartCondition",
            "enabled": True,
            "trigger_delay_seconds": 0.0,
            "recording_cycles": 1,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import (
                configure_trigger_based_condition,
            )

            result = await configure_trigger_based_condition(
                TriggerConditionTriggerBasedInput(
                    condition_type="start", rule_name="StartCondition"
                )
            )

        assert result["configured"] is True
        assert result["rule_name"] == "StartCondition"


# ── Test list_recordings ──────────────────────────────────────────────────────


class TestListRecordings:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "total_count": 1,
            "recordings": [
                {
                    "index": 0,
                    "filename": "Recording.mf4",
                    "length_seconds": 15.0,
                    "signal_count": 2,
                    "signals": [],
                }
            ],
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import list_recordings

            result = await list_recordings(MeasurementListRecordingsInput())

        assert result["total_count"] == 1


# ── Test export_recording ─────────────────────────────────────────────────────


class TestExportRecording:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "exported": True,
            "export_path": "C:\\exports\\my_recording.mf4",
            "file_size_bytes": 1024,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import export_recording

            result = await export_recording(
                MeasurementExportRecordingInput(
                    recording_index=0,
                    export_path="C:\\exports\\my_recording.mf4",
                )
            )

        assert result["exported"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("export failed")],
        ):
            from sources.services.measurement_service import export_recording

            result = await export_recording(
                MeasurementExportRecordingInput(
                    recording_index=0,
                    export_path="C:\\exports\\my_recording.mf4",
                )
            )

        assert result.get("category") is not None


# ── Test import_recording ─────────────────────────────────────────────────────


class TestImportRecording:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "imported": True,
            "import_path": "C:\\archives\\old.mf4",
            "new_recording_index": 2,
            "filename": "old.mf4",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import import_recording

            result = await import_recording(
                MeasurementImportRecordingInput(import_path="C:\\archives\\old.mf4")
            )

        assert result["imported"] is True


# ── Test add_bookmark ─────────────────────────────────────────────────────────


class TestAddBookmark:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "added": True,
            "title": "Test event",
            "description": "",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
            "bookmark_timestamp": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import add_bookmark

            result = await add_bookmark(MeasurementBookmarkAddInput(title="Test event"))

        assert result["added"] is True
        assert result["title"] == "Test event"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("bookmark add failed")],
        ):
            from sources.services.measurement_service import add_bookmark

            result = await add_bookmark(MeasurementBookmarkAddInput(title="Test event"))

        assert result.get("category") is not None


# ── Test list_bookmarks ───────────────────────────────────────────────────────


class TestListBookmarks:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "recording_index": 0,
            "total_bookmarks": 1,
            "bookmarks": [{"title": "Event", "description": "", "timestamp_seconds": 5.0}],
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import list_bookmarks

            result = await list_bookmarks(MeasurementBookmarkListInput(recording_index=0))

        assert result["total_bookmarks"] == 1


# ── Test create_data_logger ───────────────────────────────────────────────────


class TestCreateDataLogger:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "created": True,
            "logger_name": "CAN_Logger",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import create_data_logger

            result = await create_data_logger(DataLoggerCreateInput(logger_name="CAN_Logger"))

        assert result["created"] is True
        assert result["logger_name"] == "CAN_Logger"

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("create logger failed")],
        ):
            from sources.services.measurement_service import create_data_logger

            result = await create_data_logger(DataLoggerCreateInput(logger_name="CAN_Logger"))

        assert result.get("category") is not None


# ── Test configure_data_logger ────────────────────────────────────────────────


class TestConfigureDataLogger:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "configured": True,
            "logger_name": "CAN_Logger",
            "output_file_path": "C:\\Logs\\can_log.mf4",
            "file_format": "MF4",
            "overwrite_existing": True,
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import configure_data_logger

            result = await configure_data_logger(
                DataLoggerConfigureInput(
                    logger_name="CAN_Logger",
                    output_file_path="C:\\Logs\\can_log.mf4",
                )
            )

        assert result["configured"] is True


# ── Test start_data_logger ────────────────────────────────────────────────────


class TestStartDataLogger:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "started": True,
            "logger_name": "CAN_Logger",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import start_data_logger

            result = await start_data_logger(DataLoggerStartInput(logger_name="CAN_Logger"))

        assert result["started"] is True


# ── Test stop_data_logger ─────────────────────────────────────────────────────


class TestStopDataLogger:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "stopped": True,
            "logger_name": "CAN_Logger",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import stop_data_logger

            result = await stop_data_logger(DataLoggerStopInput(logger_name="CAN_Logger"))

        assert result["stopped"] is True


# ── Test list_data_loggers ────────────────────────────────────────────────────


class TestListDataLoggers:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "total_loggers": 1,
            "loggers": [
                {
                    "logger_name": "CAN_Logger",
                    "state": "Stopped",
                    "output_file_path": "C:\\Logs\\can_log.mf4",
                    "file_format": "MF4",
                }
            ],
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import list_data_loggers

            result = await list_data_loggers(DataLoggerListInput())

        assert result["total_loggers"] == 1


# ── Test remove_data_logger ───────────────────────────────────────────────────


class TestRemoveDataLogger:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "removed": True,
            "logger_name": "CAN_Logger",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import remove_data_logger

            result = await remove_data_logger(DataLoggerRemoveInput(logger_name="CAN_Logger"))

        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("remove logger failed")],
        ):
            from sources.services.measurement_service import remove_data_logger

            result = await remove_data_logger(DataLoggerRemoveInput(logger_name="CAN_Logger"))

        assert result.get("category") is not None


# ── Test add_raster ───────────────────────────────────────────────────────────


class TestAddRaster:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "added": True,
            "platform_name": "XCP",
            "raster_name": "XCP_5ms",
            "raster_interval_ms": 5.0,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import add_raster

            result = await add_raster(
                MeasurementRasterAddInput(platform_name="XCP", raster_interval_ms=5.0)
            )

        assert result["added"] is True
        assert result["raster_interval_ms"] == 5.0


# ── Test list_rasters ─────────────────────────────────────────────────────────


class TestListRasters:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "total_rasters": 1,
            "rasters": [
                {
                    "platform_name": "XCP",
                    "raster_name": "XCP_5ms",
                    "raster_interval_ms": 5.0,
                }
            ],
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import list_rasters

            result = await list_rasters(MeasurementRasterListInput())

        assert result["total_rasters"] == 1


# ── Test remove_raster ────────────────────────────────────────────────────────


class TestRemoveRaster:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "removed": True,
            "platform_name": "XCP",
            "raster_name": "XCP_5ms",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import remove_raster

            result = await remove_raster(
                MeasurementRasterRemoveInput(platform_name="XCP", raster_name="XCP_5ms")
            )

        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("remove raster failed")],
        ):
            from sources.services.measurement_service import remove_raster

            result = await remove_raster(
                MeasurementRasterRemoveInput(platform_name="XCP", raster_name="XCP_5ms")
            )

        assert result.get("category") is not None


# ── Test configure_settings ───────────────────────────────────────────────────


class TestConfigureSettings:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "configured": True,
            "data_pool_path": "C:\\MeasurementData",
            "auto_save_enabled": True,
            "auto_save_format": "MF4",
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import configure_settings

            result = await configure_settings(
                MeasurementConfigureSettingsInput(data_pool_path="C:\\MeasurementData")
            )

        assert result["configured"] is True


# ── Test remove_bookmark ──────────────────────────────────────────────────────


class TestRemoveBookmark:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        expected = {
            "removed": True,
            "recording_index": 0,
            "bookmark_index": 1,
            "timestamp_utc": "2026-05-04T10:00:00.000Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, expected],
        ):
            from sources.services.measurement_service import remove_bookmark

            result = await remove_bookmark(
                MeasurementBookmarkRemoveInput(recording_index=0, bookmark_index=1)
            )

        assert result["removed"] is True
        assert result["bookmark_index"] == 1

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[MagicMock(), BridgeOperationError("remove bookmark failed")],
        ):
            from sources.services.measurement_service import remove_bookmark

            result = await remove_bookmark(
                MeasurementBookmarkRemoveInput(recording_index=0, bookmark_index=1)
            )

        assert result.get("category") is not None
