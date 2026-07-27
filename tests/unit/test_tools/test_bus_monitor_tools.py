"""Unit tests for controldesk_mcp.tools.bus_monitor.monitoring (5 tools)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.bus_monitor import (
    BufferMode,
    BusMonitorClearAllAborted,
    BusMonitorClearAllResult,
    BusMonitorConfigureInput,
    BusMonitorConfigureResult,
    BusMonitorCreateInput,
    BusMonitorCreateResult,
    BusMonitorGetStateResult,
    BusMonitorListResult,
    BusMonitorLoadDataInput,
    BusMonitorLoadDataResult,
    BusMonitorManageAction,
    BusMonitorManageInput,
    BusMonitorQueryAction,
    BusMonitorQueryInput,
    BusMonitorRemoveResult,
    BusMonitorRenameResult,
    BusMonitorSaveDataResult,
    BusMonitorSaveDataWithTimeAxisResult,
    BusMonitorSaveInput,
    BusMonitorStartResult,
    BusMonitorStopResult,
    BusType,
    TimeAxis,
)
from controldesk_mcp.models.errors import ErrorEnvelope

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.bus_monitor_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── bus_monitor_create ────────────────────────────────────────────────────────


class TestBusMonitorCreate:
    @pytest.mark.asyncio
    async def test_creates_monitor_successfully(self) -> None:
        expected = BusMonitorCreateResult(
            monitor_name="CANMonitor",
            system_index=1,
            bus_type="CAN",
            timestamp_utc=_TS,
        )
        with _patch_svc("create_monitor", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_create

            result = await bus_monitor_create(
                BusMonitorCreateInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusMonitorCreateResult)
        assert result["created"] is True
        assert result["monitor_name"] == "CANMonitor"
        assert result["system_index"] == 1
        assert result["bus_type"] == "CAN"
        assert result["state"] == "Stopped"

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("create_monitor", return_value=_ERROR):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_create

            result = await bus_monitor_create(
                BusMonitorCreateInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"

    @pytest.mark.asyncio
    async def test_dry_run_delegates_to_preview_without_creating(self) -> None:
        from controldesk_mcp.models.base import DryRunPreviewResult

        preview = DryRunPreviewResult(
            tool="bus_monitor_create",
            action="create",
            target="CANMonitor",
            would_execute=True,
            current_state={"already_exists": False},
            message="No monitor named 'CANMonitor' exists — create would succeed.",
        )
        with (
            _patch_svc("dry_run_create_monitor", return_value=preview) as mock_dry_run,
            _patch_svc("create_monitor", return_value=_ERROR) as mock_create,
        ):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_create

            result = await bus_monitor_create(
                BusMonitorCreateInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                    dry_run=True,
                )
            )

        assert isinstance(result, DryRunPreviewResult)
        assert result["would_execute"] is True
        mock_dry_run.assert_awaited_once()
        mock_create.assert_not_awaited()


# ── bus_monitor_configure ─────────────────────────────────────────────────────


class TestBusMonitorConfigure:
    @pytest.mark.asyncio
    async def test_configures_successfully(self) -> None:
        expected = BusMonitorConfigureResult(
            monitor_name="CANMonitor",
            update_rate_ms=50,
            buffer_size_frames=20000,
            buffer_mode="FixedBuffer",
            enable_j1939_pgn_resolving=True,
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_monitor", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_configure

            result = await bus_monitor_configure(
                BusMonitorConfigureInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                    update_rate_ms=50,
                    buffer_size_frames=20000,
                    buffer_mode=BufferMode.FixedBuffer,
                    enable_j1939_pgn_resolving=True,
                )
            )

        assert isinstance(result, BusMonitorConfigureResult)
        assert result["configured"] is True
        assert result["update_rate_ms"] == 50
        assert result["buffer_size_frames"] == 20000
        assert result["buffer_mode"] == "FixedBuffer"
        assert result["enable_j1939_pgn_resolving"] is True

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("configure_monitor", return_value=_ERROR):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_configure

            result = await bus_monitor_configure(
                BusMonitorConfigureInput(
                    monitor_name="Missing",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


# ── bus_monitor_manage ────────────────────────────────────────────────────────


class TestBusMonitorManage:
    @pytest.mark.asyncio
    async def test_start_returns_started_on_success(self) -> None:
        expected = BusMonitorStartResult(monitor_name="CANMonitor", timestamp_utc=_TS)
        with _patch_svc("start_monitor", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

            result = await bus_monitor_manage(
                BusMonitorManageInput(
                    action=BusMonitorManageAction.start,
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusMonitorStartResult)
        assert result["started"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_start_missing_monitor_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

        result = await bus_monitor_manage(
            BusMonitorManageInput(
                action=BusMonitorManageAction.start,
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_stop_returns_stopped_on_success(self) -> None:
        expected = BusMonitorStopResult(monitor_name="CANMonitor", timestamp_utc=_TS)
        with _patch_svc("stop_monitor", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

            result = await bus_monitor_manage(
                BusMonitorManageInput(
                    action=BusMonitorManageAction.stop,
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusMonitorStopResult)
        assert result["stopped"] is True
        assert result["state"] == "Stopped"

    @pytest.mark.asyncio
    async def test_stop_missing_monitor_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

        result = await bus_monitor_manage(
            BusMonitorManageInput(
                action=BusMonitorManageAction.stop,
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_remove_returns_removed_on_success(self) -> None:
        expected = BusMonitorRemoveResult(monitor_name="CANMonitor", timestamp_utc=_TS)
        with _patch_svc("remove_monitor", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

            result = await bus_monitor_manage(
                BusMonitorManageInput(
                    action=BusMonitorManageAction.remove,
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusMonitorRemoveResult)
        assert result["removed"] is True
        assert result["monitor_name"] == "CANMonitor"

    @pytest.mark.asyncio
    async def test_remove_missing_monitor_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

        result = await bus_monitor_manage(
            BusMonitorManageInput(
                action=BusMonitorManageAction.remove,
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_clear_all_when_confirmed(self) -> None:
        expected = BusMonitorClearAllResult(
            cleared=True, monitors_removed=3, system_index=1, bus_type="CAN", timestamp_utc=_TS
        )
        with _patch_svc("clear_all_monitors", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

            result = await bus_monitor_manage(
                BusMonitorManageInput(
                    action=BusMonitorManageAction.clear_all,
                    system_index=1,
                    bus_type=BusType.CAN,
                    confirm=True,
                )
            )

        assert isinstance(result, BusMonitorClearAllResult)
        assert result["cleared"] is True
        assert result["monitors_removed"] == 3

    @pytest.mark.asyncio
    async def test_clear_all_aborted_when_not_confirmed(self) -> None:
        expected = BusMonitorClearAllAborted()
        with _patch_svc("clear_all_monitors", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

            result = await bus_monitor_manage(
                BusMonitorManageInput(
                    action=BusMonitorManageAction.clear_all,
                    system_index=1,
                    bus_type=BusType.CAN,
                    confirm=False,
                )
            )

        assert isinstance(result, BusMonitorClearAllAborted)
        assert result["cleared"] is False

    @pytest.mark.asyncio
    async def test_rename_returns_renamed_on_success(self) -> None:
        expected = BusMonitorRenameResult(
            old_name="CANMonitor", new_name="RxMonitor", timestamp_utc=_TS
        )
        with _patch_svc("rename_monitor", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

            result = await bus_monitor_manage(
                BusMonitorManageInput(
                    action=BusMonitorManageAction.rename,
                    monitor_name="CANMonitor",
                    new_name="RxMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusMonitorRenameResult)
        assert result["renamed"] is True
        assert result["old_name"] == "CANMonitor"
        assert result["new_name"] == "RxMonitor"

    @pytest.mark.asyncio
    async def test_rename_missing_monitor_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

        result = await bus_monitor_manage(
            BusMonitorManageInput(
                action=BusMonitorManageAction.rename,
                system_index=1,
                bus_type=BusType.CAN,
                new_name="RxMonitor",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename_missing_new_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_manage

        result = await bus_monitor_manage(
            BusMonitorManageInput(
                action=BusMonitorManageAction.rename,
                monitor_name="CANMonitor",
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── bus_monitor_query ─────────────────────────────────────────────────────────


class TestBusMonitorQuery:
    @pytest.mark.asyncio
    async def test_get_state_returns_running(self) -> None:
        expected = BusMonitorGetStateResult(
            monitor_name="CANMonitor", state="Running", is_running=True, timestamp_utc=_TS
        )
        with _patch_svc("get_monitor_state", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_query

            result = await bus_monitor_query(
                BusMonitorQueryInput(
                    action=BusMonitorQueryAction.get_state,
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusMonitorGetStateResult)
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_list_returns_monitors(self) -> None:
        expected = BusMonitorListResult(
            system_index=1,
            bus_type="CAN",
            total_count=1,
            monitors=[{"name": "Mon1", "state": "Stopped"}],
            timestamp_utc=_TS,
        )
        with _patch_svc("list_monitors", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_query

            result = await bus_monitor_query(
                BusMonitorQueryInput(
                    action=BusMonitorQueryAction.list, system_index=1, bus_type=BusType.CAN
                )
            )

        assert isinstance(result, BusMonitorListResult)
        assert result["total_count"] == 1


# ── bus_monitor_save ──────────────────────────────────────────────────────────


class TestBusMonitorSave:
    @pytest.mark.asyncio
    async def test_saves_without_time_axis(self) -> None:
        expected = BusMonitorSaveDataResult(
            monitor_name="CANMonitor",
            output_file_path="C:\\Logs\\out.mf4",
            timestamp_utc=_TS,
        )
        with _patch_svc("save_monitor_data", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_save

            result = await bus_monitor_save(
                BusMonitorSaveInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                    output_file_path="C:\\Logs\\out.mf4",
                )
            )

        assert isinstance(result, BusMonitorSaveDataResult)
        assert result["saved"] is True
        assert result["output_file_path"] == "C:\\Logs\\out.mf4"

    @pytest.mark.asyncio
    async def test_saves_with_time_axis(self) -> None:
        expected = BusMonitorSaveDataWithTimeAxisResult(
            monitor_name="CANMonitor",
            output_file_path="C:\\Logs\\out.mf4",
            time_axis="Absolute",
            timestamp_utc=_TS,
        )
        with _patch_svc("save_monitor_data_with_time_axis", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_save

            result = await bus_monitor_save(
                BusMonitorSaveInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                    output_file_path="C:\\Logs\\out.mf4",
                    time_axis=TimeAxis.Absolute,
                )
            )

        assert isinstance(result, BusMonitorSaveDataWithTimeAxisResult)
        assert result["saved"] is True
        assert result["time_axis"] == "Absolute"

    @pytest.mark.asyncio
    async def test_save_returns_error_on_service_error(self) -> None:
        with _patch_svc("save_monitor_data", return_value=_ERROR):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_save

            result = await bus_monitor_save(
                BusMonitorSaveInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                    output_file_path="C:\\Logs\\out.mf4",
                )
            )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


# ── bus_monitor_load_data ─────────────────────────────────────────────────────


class TestBusMonitorLoadData:
    @pytest.mark.asyncio
    async def test_loads_data_successfully(self) -> None:
        expected = BusMonitorLoadDataResult(
            monitor_name="CANMonitor",
            log_file_path="C:\\Logs\\capture.asc",
            log_file_section=0,
            timestamp_utc=_TS,
        )
        with _patch_svc("load_monitor_data", return_value=expected):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_load_data

            result = await bus_monitor_load_data(
                BusMonitorLoadDataInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                    log_file_path="C:\\Logs\\capture.asc",
                )
            )

        assert isinstance(result, BusMonitorLoadDataResult)
        assert result["loaded"] is True
        assert result["log_file_path"] == "C:\\Logs\\capture.asc"
        assert result["log_file_section"] == 0

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("load_monitor_data", return_value=_ERROR):
            from controldesk_mcp.tools.bus_monitor.monitoring import bus_monitor_load_data

            result = await bus_monitor_load_data(
                BusMonitorLoadDataInput(
                    monitor_name="CANMonitor",
                    system_index=1,
                    bus_type=BusType.CAN,
                    log_file_path="C:\\Logs\\capture.asc",
                )
            )

        assert isinstance(result, ErrorEnvelope)
