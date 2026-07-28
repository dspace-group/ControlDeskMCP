"""Unit tests for controldesk_mcp.tools.bus_logging.management (8 tools)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from controldesk_mcp.com_bridge.errors import BridgePreconditionError
from controldesk_mcp.models.bus_logging import (
    BusFilterConfigureInput,
    BusFilterConfigureResult,
    BusFilterCreateInput,
    BusFilterCreateResult,
    BusFilterListResult,
    BusFilterManageAction,
    BusFilterManageInput,
    BusFilterRemoveResult,
    BusFilterStartResult,
    BusFilterStopResult,
    BusLoggerAdminManageAction,
    BusLoggerAdminManageInput,
    BusLoggerClearAllAborted,
    BusLoggerClearAllResult,
    BusLoggerConfigureInput,
    BusLoggerConfigureResult,
    BusLoggerCreateInput,
    BusLoggerCreateResult,
    BusLoggerGetStateResult,
    BusLoggerListResult,
    BusLoggerManageAction,
    BusLoggerManageInput,
    BusLoggerQueryAction,
    BusLoggerQueryInput,
    BusLoggerRemoveResult,
    BusLoggerRenameResult,
    BusLoggerSetActivatedResult,
    BusLoggerStartResult,
    BusLoggerStopResult,
    BusType,
)
from controldesk_mcp.models.errors import ErrorEnvelope

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.bus_logging_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── bus_logger_create ─────────────────────────────────────────────────────────


class TestBusLoggerCreate:
    @pytest.mark.asyncio
    async def test_returns_created_on_success(self) -> None:
        expected = BusLoggerCreateResult(
            created=True,
            logger_name="CANRecorder",
            system_index=1,
            bus_type="CAN",
            state="Stopped",
            activated=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("create_logger", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_create

            result = await bus_logger_create(
                BusLoggerCreateInput(logger_name="CANRecorder", system_index=1, bus_type=BusType.CAN)
            )

        assert isinstance(result, BusLoggerCreateResult)
        assert result["created"] is True
        assert result["logger_name"] == "CANRecorder"
        assert result["bus_type"] == "CAN"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("create_logger", return_value=_ERROR):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_create

            result = await bus_logger_create(
                BusLoggerCreateInput(logger_name="L1", system_index=0, bus_type=BusType.CAN)
            )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"

    @pytest.mark.asyncio
    async def test_dry_run_delegates_to_preview_without_creating(self) -> None:
        from controldesk_mcp.models.base import DryRunPreviewResult

        preview = DryRunPreviewResult(
            tool="bus_logger_create",
            action="create",
            target="L1",
            would_execute=True,
            current_state={"already_exists": False},
            message="No logger named 'L1' exists — create would succeed.",
        )
        with (
            _patch_svc("dry_run_create_logger", return_value=preview) as mock_dry_run,
            _patch_svc("create_logger", return_value=_ERROR) as mock_create,
        ):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_create

            result = await bus_logger_create(
                BusLoggerCreateInput(logger_name="L1", system_index=0, bus_type=BusType.CAN, dry_run=True)
            )

        assert isinstance(result, DryRunPreviewResult)
        assert result["would_execute"] is True
        mock_dry_run.assert_awaited_once()
        mock_create.assert_not_awaited()


# ── bus_logger_configure ──────────────────────────────────────────────────────


class TestBusLoggerConfigure:
    @pytest.mark.asyncio
    async def test_returns_configured_on_success(self) -> None:
        expected = BusLoggerConfigureResult(
            configured=True,
            logger_name="CANRecorder",
            log_file_full_path="C:\\Logs\\can.asc",
            overwrite_existing=True,
            max_duration_seconds=30.0,
            enable_bus_statistics=False,
            continuous_ring_mode=False,
            file_rolling_enabled=False,
            time_axis_mode="Relative",
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_logger", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_configure

            result = await bus_logger_configure(
                BusLoggerConfigureInput(
                    logger_name="CANRecorder",
                    system_index=1,
                    bus_type=BusType.CAN,
                    log_file_full_path="C:\\Logs\\can.asc",
                    max_duration_seconds=30.0,
                )
            )

        assert isinstance(result, BusLoggerConfigureResult)
        assert result["configured"] is True
        assert result["logger_name"] == "CANRecorder"
        assert result["log_file_full_path"] == "C:\\Logs\\can.asc"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("configure_logger", return_value=_ERROR):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_configure

            result = await bus_logger_configure(
                BusLoggerConfigureInput(
                    logger_name="L1",
                    system_index=0,
                    bus_type=BusType.CAN,
                    log_file_full_path="C:\\Logs\\x.asc",
                )
            )

        assert isinstance(result, ErrorEnvelope)


# ── bus_logger_manage ─────────────────────────────────────────────────────────


class TestBusLoggerManage:
    @pytest.mark.asyncio
    async def test_start_returns_started_on_success(self) -> None:
        expected = BusLoggerStartResult(
            started=True,
            logger_name="CANRecorder",
            state="Running",
            activated=True,
            timestamp_utc=_TS,
        )
        with _patch_svc("start_logger", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_manage

            result = await bus_logger_manage(
                BusLoggerManageInput(
                    action=BusLoggerManageAction.start,
                    logger_name="CANRecorder",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusLoggerStartResult)
        assert result["started"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_start_missing_logger_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logger_manage

        result = await bus_logger_manage(
            BusLoggerManageInput(action=BusLoggerManageAction.start, system_index=1, bus_type=BusType.CAN)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_stop_returns_stopped_on_success(self) -> None:
        expected = BusLoggerStopResult(
            stopped=True,
            logger_name="CANRecorder",
            state="Stopped",
            activated=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("stop_logger", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_manage

            result = await bus_logger_manage(
                BusLoggerManageInput(
                    action=BusLoggerManageAction.stop,
                    logger_name="CANRecorder",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusLoggerStopResult)
        assert result["stopped"] is True
        assert result["state"] == "Stopped"

    @pytest.mark.asyncio
    async def test_stop_missing_logger_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logger_manage

        result = await bus_logger_manage(
            BusLoggerManageInput(action=BusLoggerManageAction.stop, system_index=1, bus_type=BusType.CAN)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_start_returns_error_on_bridge_error(self) -> None:
        with _patch_svc("start_logger", return_value=_ERROR):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_manage

            result = await bus_logger_manage(
                BusLoggerManageInput(
                    action=BusLoggerManageAction.start,
                    logger_name="L1",
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


# ── bus_logger_admin_manage ───────────────────────────────────────────────────


class TestBusLoggerAdminManage:
    @pytest.mark.asyncio
    async def test_remove_returns_removed_on_success(self) -> None:
        expected = BusLoggerRemoveResult(removed=True, logger_name="CANRecorder", timestamp_utc=_TS)
        with _patch_svc("remove_logger", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

            result = await bus_logger_admin_manage(
                BusLoggerAdminManageInput(
                    action=BusLoggerAdminManageAction.remove,
                    logger_name="CANRecorder",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusLoggerRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_logger_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

        result = await bus_logger_admin_manage(
            BusLoggerAdminManageInput(action=BusLoggerAdminManageAction.remove, system_index=1, bus_type=BusType.CAN)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_clear_all_aborts_when_not_confirmed(self) -> None:
        expected = BusLoggerClearAllAborted()
        with _patch_svc("clear_all_loggers", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

            result = await bus_logger_admin_manage(
                BusLoggerAdminManageInput(
                    action=BusLoggerAdminManageAction.clear_all,
                    system_index=1,
                    bus_type=BusType.CAN,
                    confirm=False,
                )
            )

        assert isinstance(result, BusLoggerClearAllAborted)
        assert result["cleared"] is False

    @pytest.mark.asyncio
    async def test_clear_all_returns_cleared_when_confirmed(self) -> None:
        expected = BusLoggerClearAllResult(
            cleared=True,
            loggers_removed=3,
            system_index=1,
            bus_type="CAN",
            timestamp_utc=_TS,
        )
        with _patch_svc("clear_all_loggers", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

            result = await bus_logger_admin_manage(
                BusLoggerAdminManageInput(
                    action=BusLoggerAdminManageAction.clear_all,
                    system_index=1,
                    bus_type=BusType.CAN,
                    confirm=True,
                )
            )

        assert isinstance(result, BusLoggerClearAllResult)
        assert result["cleared"] is True
        assert result["loggers_removed"] == 3

    @pytest.mark.asyncio
    async def test_set_activated_returns_result_on_success(self) -> None:
        expected = BusLoggerSetActivatedResult(
            activated=True,
            logger_name="CANRecorder",
            state="Stopped",
            previous_activated=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("set_logger_activated", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

            result = await bus_logger_admin_manage(
                BusLoggerAdminManageInput(
                    action=BusLoggerAdminManageAction.set_activated,
                    logger_name="CANRecorder",
                    system_index=1,
                    bus_type=BusType.CAN,
                    activated=True,
                )
            )

        assert isinstance(result, BusLoggerSetActivatedResult)
        assert result["activated"] is True
        assert result["previous_activated"] is False

    @pytest.mark.asyncio
    async def test_set_activated_missing_logger_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

        result = await bus_logger_admin_manage(
            BusLoggerAdminManageInput(
                action=BusLoggerAdminManageAction.set_activated,
                system_index=1,
                bus_type=BusType.CAN,
                activated=True,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_set_activated_missing_activated_flag_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

        result = await bus_logger_admin_manage(
            BusLoggerAdminManageInput(
                action=BusLoggerAdminManageAction.set_activated,
                logger_name="CANRecorder",
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename_returns_renamed_on_success(self) -> None:
        expected = BusLoggerRenameResult(renamed=True, old_name="CAN Logger", new_name="TxLogger", timestamp_utc=_TS)
        with _patch_svc("rename_logger", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

            result = await bus_logger_admin_manage(
                BusLoggerAdminManageInput(
                    action=BusLoggerAdminManageAction.rename,
                    logger_name="CAN Logger",
                    new_name="TxLogger",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusLoggerRenameResult)
        assert result["old_name"] == "CAN Logger"
        assert result["new_name"] == "TxLogger"

    @pytest.mark.asyncio
    async def test_rename_missing_logger_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

        result = await bus_logger_admin_manage(
            BusLoggerAdminManageInput(
                action=BusLoggerAdminManageAction.rename,
                new_name="TxLogger",
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename_missing_new_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logger_admin_manage

        result = await bus_logger_admin_manage(
            BusLoggerAdminManageInput(
                action=BusLoggerAdminManageAction.rename,
                logger_name="CAN Logger",
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── bus_logging_discover ──────────────────────────────────────────────────────


class TestBusLoggerQuery:
    @pytest.mark.asyncio
    async def test_get_state_returns_state_on_success(self) -> None:
        expected = BusLoggerGetStateResult(
            logger_name="CANRecorder",
            state="Running",
            is_running=True,
            activated=True,
            log_file_path="C:\\Logs\\can.asc",
            timestamp_utc=_TS,
        )
        with _patch_svc("get_logger_state", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_query

            result = await bus_logger_query(
                BusLoggerQueryInput(
                    action=BusLoggerQueryAction.get_state,
                    logger_name="CANRecorder",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusLoggerGetStateResult)
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_list_returns_loggers_on_success(self) -> None:
        expected = BusLoggerListResult(
            system_index=1,
            bus_type="CAN",
            total_count=2,
            loggers=[
                {"name": "CANRecorder", "state": "Running", "activated": True},
                {"name": "ErrorLogger", "state": "Stopped", "activated": False},
            ],
        )
        with _patch_svc("list_loggers", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_logger_query

            result = await bus_logger_query(
                BusLoggerQueryInput(action=BusLoggerQueryAction.list, system_index=1, bus_type=BusType.CAN)
            )

        assert isinstance(result, BusLoggerListResult)
        assert result["total_count"] == 2


class TestBusLoggingDiscover:
    @pytest.mark.asyncio
    async def test_returns_four_tools(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logging_discover

        result = await bus_logging_discover(AsyncMock())

        assert result["status"] == "ok"
        assert len(result["tools"]) == 5

    @pytest.mark.asyncio
    async def test_discover_has_query_tool(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logging_discover

        result = await bus_logging_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "controldesk_bus_logger_query" in tool_names

    @pytest.mark.asyncio
    async def test_discover_has_admin_manage_tool(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logging_discover

        result = await bus_logging_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "controldesk_bus_logger_admin_manage" in tool_names

    @pytest.mark.asyncio
    async def test_discover_admin_manage_actions(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_logging_discover

        result = await bus_logging_discover(AsyncMock())

        admin_tool = next(t for t in result["tools"] if t["tool_name"] == "controldesk_bus_logger_admin_manage")
        assert "remove" in admin_tool["actions"]
        assert "clear_all" in admin_tool["actions"]
        assert "set_activated" in admin_tool["actions"]
        assert "rename" in admin_tool["actions"]


# ── bus_filter_create ─────────────────────────────────────────────────────────


class TestBusFilterCreate:
    @pytest.mark.asyncio
    async def test_returns_created_on_success(self) -> None:
        expected = BusFilterCreateResult(
            created=True,
            filter_name="CANFilter",
            system_index=1,
            bus_type="CAN",
            state="Stopped",
            activated=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("create_filter", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_create

            result = await bus_filter_create(
                BusFilterCreateInput(filter_name="CANFilter", system_index=1, bus_type=BusType.CAN)
            )

        assert isinstance(result, BusFilterCreateResult)
        assert result["created"] is True
        assert result["filter_name"] == "CANFilter"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("create_filter", return_value=_ERROR):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_create

            result = await bus_filter_create(
                BusFilterCreateInput(filter_name="F1", system_index=0, bus_type=BusType.CAN)
            )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


# ── bus_filter_configure ──────────────────────────────────────────────────────


class TestBusFilterConfigure:
    @pytest.mark.asyncio
    async def test_returns_configured_on_success(self) -> None:
        expected = BusFilterConfigureResult(
            filter_name="CANFilter",
            loggers_count=1,
            monitors_count=0,
            replays_count=0,
            note="Filter applied to 1 logger(s).",
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_filter", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_configure

            result = await bus_filter_configure(
                BusFilterConfigureInput(
                    filter_name="CANFilter",
                    system_index=1,
                    bus_type=BusType.CAN,
                    message_id=256,
                )
            )

        assert isinstance(result, BusFilterConfigureResult)
        assert result["filter_name"] == "CANFilter"
        assert result["loggers_count"] == 1


# ── bus_filter_start/stop/list/remove (consolidated) ─────────────────────────


class TestBusFilterManage:
    @pytest.mark.asyncio
    async def test_start_returns_started_on_success(self) -> None:
        expected = BusFilterStartResult(
            started=True,
            filter_name="CANFilter",
            started_loggers=["CANRecorder"],
            started_replays=[],
            timestamp_utc=_TS,
        )
        with _patch_svc("start_filter", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

            result = await bus_filter_manage(
                BusFilterManageInput(
                    action=BusFilterManageAction.start,
                    filter_name="CANFilter",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusFilterStartResult)
        assert result["started"] is True
        assert result["filter_name"] == "CANFilter"

    @pytest.mark.asyncio
    async def test_start_missing_filter_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

        result = await bus_filter_manage(
            BusFilterManageInput(
                action=BusFilterManageAction.start,
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_stop_returns_stopped_on_success(self) -> None:
        expected = BusFilterStopResult(stopped=True, filter_name="CANFilter", timestamp_utc=_TS)
        with _patch_svc("stop_filter", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

            result = await bus_filter_manage(
                BusFilterManageInput(
                    action=BusFilterManageAction.stop,
                    filter_name="CANFilter",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusFilterStopResult)
        assert result["stopped"] is True

    @pytest.mark.asyncio
    async def test_stop_missing_filter_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

        result = await bus_filter_manage(
            BusFilterManageInput(
                action=BusFilterManageAction.stop,
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_returns_filters_on_success(self) -> None:
        expected = BusFilterListResult(
            total_count=1,
            filters=[{"name": "CANFilter", "state": "Running", "activated": True}],
        )
        with _patch_svc("list_filters", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

            result = await bus_filter_manage(
                BusFilterManageInput(
                    action=BusFilterManageAction.list,
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusFilterListResult)
        assert result["total_count"] == 1
        assert result["filters"][0]["name"] == "CANFilter"

    @pytest.mark.asyncio
    async def test_list_returns_empty_on_success(self) -> None:
        expected = BusFilterListResult(total_count=0, filters=[])
        with _patch_svc("list_filters", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

            result = await bus_filter_manage(
                BusFilterManageInput(
                    action=BusFilterManageAction.list,
                    system_index=0,
                    bus_type=BusType.LIN,
                )
            )

        assert isinstance(result, BusFilterListResult)
        assert result["total_count"] == 0
        assert result["filters"] == []

    @pytest.mark.asyncio
    async def test_list_returns_error_envelope(self) -> None:
        with _patch_svc("list_filters", return_value=_ERROR):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

            result = await bus_filter_manage(
                BusFilterManageInput(
                    action=BusFilterManageAction.list,
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_remove_returns_removed_on_success(self) -> None:
        expected = BusFilterRemoveResult(removed=True, filter_name="CANFilter", timestamp_utc=_TS)
        with _patch_svc("remove_filter", return_value=expected):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

            result = await bus_filter_manage(
                BusFilterManageInput(
                    action=BusFilterManageAction.remove,
                    filter_name="CANFilter",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusFilterRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_filter_name_returns_error(self) -> None:
        from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

        result = await bus_filter_manage(
            BusFilterManageInput(
                action=BusFilterManageAction.remove,
                system_index=1,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_remove_returns_error_envelope(self) -> None:
        with _patch_svc("remove_filter", return_value=_ERROR):
            from controldesk_mcp.tools.bus_logging.management import bus_filter_manage

            result = await bus_filter_manage(
                BusFilterManageInput(
                    action=BusFilterManageAction.remove,
                    filter_name="X",
                    system_index=1,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


# ── COM domain wrapper tests ─────────────────────────────────────────────────


class TestBusLoggingComHelpers:
    """Unit tests for controldesk_mcp.com_bridge.domains.bus_logging_com helpers."""

    def test_get_physical_bus_access_unknown_bus_type(self) -> None:
        from controldesk_mcp.com_bridge.domains.bus_logging_com import _get_physical_bus_access

        app = MagicMock()
        with pytest.raises(BridgePreconditionError, match="Unknown bus_type"):
            _get_physical_bus_access(app, 0, 0, "INVALID", 0)

    def test_get_logger_by_name_not_found(self) -> None:
        from controldesk_mcp.com_bridge.domains.bus_logging_com import _get_logger_by_name

        loggers = MagicMock()
        loggers.Count = 0
        with pytest.raises(BridgePreconditionError, match="not found"):
            _get_logger_by_name(loggers, "NonExistent")

    def test_get_filter_by_name_not_found(self) -> None:
        from controldesk_mcp.com_bridge.domains.bus_logging_com import _get_filter_by_name

        filters = MagicMock()
        filters.Count = 0
        with pytest.raises(BridgePreconditionError, match="not found"):
            _get_filter_by_name(filters, "NonExistent")

    def test_get_logger_by_name_found(self) -> None:
        from controldesk_mcp.com_bridge.domains.bus_logging_com import _get_logger_by_name

        lgr_mock = MagicMock()
        lgr_mock.Name = "MyLogger"
        loggers = MagicMock()
        loggers.Count = 1
        loggers.Item.return_value = lgr_mock

        result = _get_logger_by_name(loggers, "MyLogger")
        assert result is lgr_mock

    def test_get_filter_by_name_found(self) -> None:
        from controldesk_mcp.com_bridge.domains.bus_logging_com import _get_filter_by_name

        flt_mock = MagicMock()
        flt_mock.Name = "MyFilter"
        filters = MagicMock()
        filters.Count = 1
        filters.Item.return_value = flt_mock

        result = _get_filter_by_name(filters, "MyFilter")
        assert result is flt_mock
