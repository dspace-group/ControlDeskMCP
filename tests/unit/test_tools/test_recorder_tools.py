"""Unit tests for recorder MCP tools.

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.recorder import (
    RecorderConfigManageAction,
    RecorderConfigManageInput,
    RecorderDiscoverResult,
    RecorderMainAddSignalResult,
    RecorderMainConfigureResult,
    RecorderMainExportResult,
    RecorderMainGetStateResult,
    RecorderMainImportSignalsResult,
    RecorderMainInvokeTriggerResult,
    RecorderMainListSignalsResult,
    RecorderMainManageAction,
    RecorderMainManageInput,
    RecorderMainRemoveSignalResult,
    RecorderMainStartInput,
    RecorderMainStartResult,
    RecorderMainStopInput,
    RecorderMainStopResult,
    RecorderQueryAction,
    RecorderQueryInput,
    RecorderSignalManageAction,
    RecorderSignalManageInput,
)

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.recorder_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


class TestRecorderMainStart:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = RecorderMainStartResult(
            started=True,
            base_filename="Recording.mf4",
            with_trigger=False,
            state="Running",
            timestamp_utc=_TS,
        )
        with _patch_svc("start_recorder", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_main_start

            result = await recorder_main_start(RecorderMainStartInput())

        assert isinstance(result, RecorderMainStartResult)
        assert result["started"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("start_recorder", return_value=_ERROR):
            from controldesk_mcp.tools.recorder.management import recorder_main_start

            result = await recorder_main_start(RecorderMainStartInput())

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"

    @pytest.mark.asyncio
    async def test_dry_run_delegates_to_preview_without_starting(self) -> None:
        from controldesk_mcp.models.base import DryRunPreviewResult

        preview = DryRunPreviewResult(
            tool="recorder_main_start",
            action="start",
            target="main_recorder",
            would_execute=True,
            current_state={"state": "Stopped", "is_running": False},
            message="Recorder is not running — start would succeed.",
        )
        with (
            _patch_svc("dry_run_start_recorder", return_value=preview) as mock_dry_run,
            _patch_svc("start_recorder", return_value=_ERROR) as mock_start,
        ):
            from controldesk_mcp.tools.recorder.management import recorder_main_start

            result = await recorder_main_start(RecorderMainStartInput(dry_run=True))

        assert isinstance(result, DryRunPreviewResult)
        assert result["would_execute"] is True
        mock_dry_run.assert_awaited_once()
        mock_start.assert_not_awaited()


class TestRecorderMainStop:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = RecorderMainStopResult(
            stopped=True,
            output_files=["C:\\Recordings\\Recording.mf4"],
            timestamp_utc=_TS,
        )
        with _patch_svc("stop_recorder", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_main_stop

            result = await recorder_main_stop(RecorderMainStopInput())

        assert isinstance(result, RecorderMainStopResult)
        assert result["stopped"] is True
        assert len(result["output_files"]) == 1

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("stop_recorder", return_value=_ERROR):
            from controldesk_mcp.tools.recorder.management import recorder_main_stop

            result = await recorder_main_stop(RecorderMainStopInput())

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_dry_run_delegates_to_preview_without_stopping(self) -> None:
        from controldesk_mcp.models.base import DryRunPreviewResult

        preview = DryRunPreviewResult(
            tool="recorder_main_stop",
            action="stop",
            target="main_recorder",
            would_execute=True,
            current_state={"state": "Running", "is_running": True},
            message="Recorder is running — stop would succeed.",
        )
        with (
            _patch_svc("dry_run_stop_recorder", return_value=preview) as mock_dry_run,
            _patch_svc("stop_recorder", return_value=_ERROR) as mock_stop,
        ):
            from controldesk_mcp.tools.recorder.management import recorder_main_stop

            result = await recorder_main_stop(RecorderMainStopInput(dry_run=True))

        assert isinstance(result, DryRunPreviewResult)
        assert result["would_execute"] is True
        mock_dry_run.assert_awaited_once()
        mock_stop.assert_not_awaited()


class TestRecorderQuery:
    @pytest.mark.asyncio
    async def test_get_state(self) -> None:
        expected = RecorderMainGetStateResult(
            state="Idling",
            is_running=False,
            last_recorded_files=[],
            timestamp_utc=_TS,
        )
        with _patch_svc("get_state", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_query

            result = await recorder_query(RecorderQueryInput(action=RecorderQueryAction.get_state))

        assert isinstance(result, RecorderMainGetStateResult)
        assert result["state"] == "Idling"
        assert result["is_running"] is False

    @pytest.mark.asyncio
    async def test_get_state_returns_error(self) -> None:
        with _patch_svc("get_state", return_value=_ERROR):
            from controldesk_mcp.tools.recorder.management import recorder_query

            result = await recorder_query(RecorderQueryInput(action=RecorderQueryAction.get_state))

        assert isinstance(result, ErrorEnvelope)


class TestRecorderMainManage:
    @pytest.mark.asyncio
    async def test_configure(self) -> None:
        expected = RecorderMainConfigureResult(
            configured=True,
            base_filename="Recording.mf4",
            automatic_naming_enabled=False,
            add_to_experiment_enabled=False,
            open_in_data_pool_enabled=False,
            write_to_file_enabled=True,
            automatic_signal_configuration_enabled=True,
            description="",
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_main_recorder", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_main_manage

            result = await recorder_main_manage(
                RecorderMainManageInput(
                    action=RecorderMainManageAction.configure,
                    base_filename="Recording.mf4",
                )
            )

        assert isinstance(result, RecorderMainConfigureResult)
        assert result["configured"] is True
        assert result["base_filename"] == "Recording.mf4"

    @pytest.mark.asyncio
    async def test_configure_missing_base_filename(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_main_manage

        result = await recorder_main_manage(
            RecorderMainManageInput(
                action=RecorderMainManageAction.configure,
                base_filename=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_configure_returns_error(self) -> None:
        with _patch_svc("configure_main_recorder", return_value=_ERROR):
            from controldesk_mcp.tools.recorder.management import recorder_main_manage

            result = await recorder_main_manage(
                RecorderMainManageInput(
                    action=RecorderMainManageAction.configure,
                    base_filename="Recording.mf4",
                )
            )

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_invoke_trigger(self) -> None:
        expected = RecorderMainInvokeTriggerResult(
            triggered=True,
            state="Running",
            timestamp_utc=_TS,
        )
        with _patch_svc("invoke_trigger", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_main_manage

            result = await recorder_main_manage(RecorderMainManageInput(action=RecorderMainManageAction.invoke_trigger))

        assert isinstance(result, RecorderMainInvokeTriggerResult)
        assert result["triggered"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_invoke_trigger_returns_error(self) -> None:
        with _patch_svc("invoke_trigger", return_value=_ERROR):
            from controldesk_mcp.tools.recorder.management import recorder_main_manage

            result = await recorder_main_manage(RecorderMainManageInput(action=RecorderMainManageAction.invoke_trigger))

        assert isinstance(result, ErrorEnvelope)


class TestRecorderSignalManage:
    @pytest.mark.asyncio
    async def test_add_signal(self) -> None:
        expected = RecorderMainAddSignalResult(
            added=True,
            connection_path="XCP(5ms)://control_out",
            timestamp_utc=_TS,
        )
        with _patch_svc("add_signal", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_signal_manage

            result = await recorder_signal_manage(
                RecorderSignalManageInput(
                    action=RecorderSignalManageAction.add_signal,
                    connection_path="XCP(5ms)://control_out",
                )
            )

        assert isinstance(result, RecorderMainAddSignalResult)
        assert result["added"] is True
        assert result["connection_path"] == "XCP(5ms)://control_out"

    @pytest.mark.asyncio
    async def test_add_signal_missing_connection_path(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_signal_manage

        result = await recorder_signal_manage(
            RecorderSignalManageInput(
                action=RecorderSignalManageAction.add_signal,
                connection_path=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_remove_signal(self) -> None:
        expected = RecorderMainRemoveSignalResult(
            removed=True,
            connection_path="XCP(5ms)://control_out",
            timestamp_utc=_TS,
        )
        with _patch_svc("remove_signal", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_signal_manage

            result = await recorder_signal_manage(
                RecorderSignalManageInput(
                    action=RecorderSignalManageAction.remove_signal,
                    connection_path="XCP(5ms)://control_out",
                )
            )

        assert isinstance(result, RecorderMainRemoveSignalResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_signal_missing_connection_path(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_signal_manage

        result = await recorder_signal_manage(
            RecorderSignalManageInput(
                action=RecorderSignalManageAction.remove_signal,
                connection_path=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_signals(self) -> None:
        signals = [{"connection_path": "XCP(5ms)://control_out", "platform_name": "XCP"}]
        expected = RecorderMainListSignalsResult(total_count=1, signals=signals)
        with _patch_svc("list_signals", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_signal_manage

            result = await recorder_signal_manage(
                RecorderSignalManageInput(action=RecorderSignalManageAction.list_signals)
            )

        assert isinstance(result, RecorderMainListSignalsResult)
        assert result["total_count"] == 1
        assert result["signals"] == signals

    @pytest.mark.asyncio
    async def test_list_signals_returns_error(self) -> None:
        with _patch_svc("list_signals", return_value=_ERROR):
            from controldesk_mcp.tools.recorder.management import recorder_signal_manage

            result = await recorder_signal_manage(
                RecorderSignalManageInput(action=RecorderSignalManageAction.list_signals)
            )

        assert isinstance(result, ErrorEnvelope)


class TestRecorderConfigManage:
    @pytest.mark.asyncio
    async def test_export(self) -> None:
        expected = RecorderMainExportResult(
            exported=True,
            full_path="C:\\Recordings\\recorder_config.mf4r",
            timestamp_utc=_TS,
        )
        with _patch_svc("export_recorder", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_config_manage

            result = await recorder_config_manage(
                RecorderConfigManageInput(
                    action=RecorderConfigManageAction.export,
                    full_path="C:\\Recordings\\recorder_config.mf4r",
                )
            )

        assert isinstance(result, RecorderMainExportResult)
        assert result["exported"] is True
        assert result["full_path"] == "C:\\Recordings\\recorder_config.mf4r"

    @pytest.mark.asyncio
    async def test_import_signals(self) -> None:
        expected = RecorderMainImportSignalsResult(
            imported=True,
            full_path="C:\\Recordings\\recorder_config.mf4r",
            timestamp_utc=_TS,
        )
        with _patch_svc("import_signals_from_file", return_value=expected):
            from controldesk_mcp.tools.recorder.management import recorder_config_manage

            result = await recorder_config_manage(
                RecorderConfigManageInput(
                    action=RecorderConfigManageAction.import_signals,
                    full_path="C:\\Recordings\\recorder_config.mf4r",
                )
            )

        assert isinstance(result, RecorderMainImportSignalsResult)
        assert result["imported"] is True

    @pytest.mark.asyncio
    async def test_missing_full_path_returns_error(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_config_manage

        result = await recorder_config_manage(
            RecorderConfigManageInput(
                action=RecorderConfigManageAction.export,
                full_path=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_export_returns_error(self) -> None:
        with _patch_svc("export_recorder", return_value=_ERROR):
            from controldesk_mcp.tools.recorder.management import recorder_config_manage

            result = await recorder_config_manage(
                RecorderConfigManageInput(
                    action=RecorderConfigManageAction.export,
                    full_path="C:\\Recordings\\recorder_config.mf4r",
                )
            )

        assert isinstance(result, ErrorEnvelope)


class TestRecorderDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_discover

        result = await recorder_discover(AsyncMock())

        assert isinstance(result, RecorderDiscoverResult)
        assert result["status"] == "ok"
        assert len(result["tools"]) == 3

    @pytest.mark.asyncio
    async def test_discover_has_query_tool(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_discover

        result = await recorder_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "recorder_query" in tool_names

    @pytest.mark.asyncio
    async def test_discover_has_signal_manage_tool(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_discover

        result = await recorder_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "recorder_signal_manage" in tool_names

    @pytest.mark.asyncio
    async def test_discover_has_config_manage_tool(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_discover

        result = await recorder_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "recorder_config_manage" in tool_names

    @pytest.mark.asyncio
    async def test_discover_signal_manage_actions(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_discover

        result = await recorder_discover(AsyncMock())

        signal_tool = next(t for t in result["tools"] if t["tool_name"] == "recorder_signal_manage")
        assert "add_signal" in signal_tool["actions"]
        assert "remove_signal" in signal_tool["actions"]
        assert "list_signals" in signal_tool["actions"]

    @pytest.mark.asyncio
    async def test_discover_config_manage_actions(self) -> None:
        from controldesk_mcp.tools.recorder.management import recorder_discover

        result = await recorder_discover(AsyncMock())

        config_tool = next(t for t in result["tools"] if t["tool_name"] == "recorder_config_manage")
        assert "export" in config_tool["actions"]
        assert "import_signals" in config_tool["actions"]
        assert config_tool["required_params_per_action"]["export"] == ["full_path"]
        assert config_tool["required_params_per_action"]["import_signals"] == ["full_path"]


class TestRecorderInputModels:
    def test_manage_input_instantiates(self) -> None:
        assert RecorderMainManageInput(action=RecorderMainManageAction.configure) is not None
        assert RecorderQueryInput(action=RecorderQueryAction.get_state) is not None
        assert RecorderConfigManageInput(action=RecorderConfigManageAction.export) is not None

    def test_signal_manage_input_instantiates(self) -> None:
        assert RecorderSignalManageInput(action=RecorderSignalManageAction.list_signals) is not None

    def test_start_stop_instantiate(self) -> None:
        assert RecorderMainStartInput() is not None
        assert RecorderMainStopInput() is not None
