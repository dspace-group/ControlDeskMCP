"""Unit tests for bus_replay MCP tools (5 tools after consolidation)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sources.models.bus_replay import (
    BusReplayAdminManageAction,
    BusReplayAdminManageInput,
    BusReplayClearAllAborted,
    BusReplayClearAllResult,
    BusReplayConfigureInput,
    BusReplayConfigureResult,
    BusReplayCreateInput,
    BusReplayCreateResult,
    BusReplayGetStateResult,
    BusReplayListResult,
    BusReplayManageAction,
    BusReplayManageInput,
    BusReplayQueryAction,
    BusReplayQueryInput,
    BusReplayRemoveResult,
    BusReplayRenameResult,
    BusReplaySetActivatedResult,
    BusReplayStartResult,
    BusReplayStopResult,
    BusType,
    ReplayMode,
)
from sources.models.errors import ErrorEnvelope

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"sources.services.bus_replay_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── bus_replay_create ─────────────────────────────────────────────────────────


class TestBusReplayCreate:
    @pytest.mark.asyncio
    async def test_creates_replay_successfully(self) -> None:
        expected = BusReplayCreateResult(
            created=True,
            replay_name="CANReplay",
            system_index=0,
            bus_type="CAN",
            state="Stopped",
            activated=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("create_replay", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_create

            result = await bus_replay_create(
                BusReplayCreateInput(replay_name="CANReplay", system_index=0, bus_type=BusType.CAN)
            )

        assert isinstance(result, BusReplayCreateResult)
        assert result["created"] is True
        assert result["replay_name"] == "CANReplay"

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("create_replay", return_value=_ERROR):
            from sources.tools.bus_replay.management import bus_replay_create

            result = await bus_replay_create(
                BusReplayCreateInput(replay_name="CANReplay", system_index=0, bus_type=BusType.CAN)
            )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"

    @pytest.mark.asyncio
    async def test_dry_run_delegates_to_preview_without_creating(self) -> None:
        from sources.models.base import DryRunPreviewResult

        preview = DryRunPreviewResult(
            tool="bus_replay_create",
            action="create",
            target="CANReplay",
            would_execute=True,
            current_state={"already_exists": False},
            message="No replay named 'CANReplay' exists — create would succeed.",
        )
        with (
            _patch_svc("dry_run_create_replay", return_value=preview) as mock_dry_run,
            _patch_svc("create_replay", return_value=_ERROR) as mock_create,
        ):
            from sources.tools.bus_replay.management import bus_replay_create

            result = await bus_replay_create(
                BusReplayCreateInput(
                    replay_name="CANReplay", system_index=0, bus_type=BusType.CAN, dry_run=True
                )
            )

        assert isinstance(result, DryRunPreviewResult)
        assert result["would_execute"] is True
        mock_dry_run.assert_awaited_once()
        mock_create.assert_not_awaited()


# ── bus_replay_configure ──────────────────────────────────────────────────────


class TestBusReplayConfigure:
    @pytest.mark.asyncio
    async def test_configures_successfully(self) -> None:
        expected = BusReplayConfigureResult(
            configured=True,
            replay_name="CANReplay",
            log_file_full_path="C:\\Logs\\recorded.asc",
            replay_mode="NumberOfPasses",
            number_of_passes=3,
            duration_seconds=0.0,
            start_monitor_on_replay=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("configure_replay", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_configure

            result = await bus_replay_configure(
                BusReplayConfigureInput(
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                    log_file_full_path="C:\\Logs\\recorded.asc",
                    replay_mode=ReplayMode.NumberOfPasses,
                    number_of_passes=3,
                )
            )

        assert isinstance(result, BusReplayConfigureResult)
        assert result["configured"] is True
        assert result["number_of_passes"] == 3

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("configure_replay", return_value=_ERROR):
            from sources.tools.bus_replay.management import bus_replay_configure

            result = await bus_replay_configure(
                BusReplayConfigureInput(
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                    log_file_full_path="C:\\Logs\\recorded.asc",
                )
            )

        assert isinstance(result, ErrorEnvelope)


# ── bus_replay_manage ─────────────────────────────────────────────────────────


class TestBusReplayManage:
    @pytest.mark.asyncio
    async def test_start_returns_started_on_success(self) -> None:
        expected = BusReplayStartResult(
            started=True,
            replay_name="CANReplay",
            state="Running",
            activated=True,
            timestamp_utc=_TS,
        )
        with _patch_svc("start_replay", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_manage

            result = await bus_replay_manage(
                BusReplayManageInput(
                    action=BusReplayManageAction.start,
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusReplayStartResult)
        assert result["started"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_start_missing_replay_name_returns_error(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_manage

        result = await bus_replay_manage(
            BusReplayManageInput(
                action=BusReplayManageAction.start,
                system_index=0,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_stop_returns_stopped_on_success(self) -> None:
        expected = BusReplayStopResult(
            stopped=True,
            replay_name="CANReplay",
            state="Stopped",
            activated=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("stop_replay", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_manage

            result = await bus_replay_manage(
                BusReplayManageInput(
                    action=BusReplayManageAction.stop,
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusReplayStopResult)
        assert result["stopped"] is True
        assert result["state"] == "Stopped"

    @pytest.mark.asyncio
    async def test_stop_missing_replay_name_returns_error(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_manage

        result = await bus_replay_manage(
            BusReplayManageInput(
                action=BusReplayManageAction.stop,
                system_index=0,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_get_state_returns_running(self) -> None:
        expected = BusReplayGetStateResult(
            replay_name="CANReplay",
            state="Running",
            is_running=True,
            activated=True,
            log_file_path="C:\\Logs\\recorded.asc",
            replay_mode="Infinite",
            timestamp_utc=_TS,
        )
        with _patch_svc("get_replay_state", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_query

            result = await bus_replay_query(
                BusReplayQueryInput(
                    action=BusReplayQueryAction.get_state,
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusReplayGetStateResult)
        assert result["is_running"] is True
        assert result["state"] == "Running"

    @pytest.mark.asyncio
    async def test_get_state_missing_replay_name_returns_error(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_query

        result = await bus_replay_query(
            BusReplayQueryInput(
                action=BusReplayQueryAction.get_state,
                system_index=0,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_returns_replays(self) -> None:
        expected = BusReplayListResult(
            system_index=0,
            bus_type="CAN",
            total_count=1,
            replays=[{"name": "CANReplay", "state": "Running", "activated": True}],
            timestamp_utc=_TS,
        )
        with _patch_svc("list_replays", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_query

            result = await bus_replay_query(
                BusReplayQueryInput(
                    action=BusReplayQueryAction.list,
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusReplayListResult)
        assert result["total_count"] == 1
        assert len(result["replays"]) == 1

    @pytest.mark.asyncio
    async def test_list_returns_error_envelope(self) -> None:
        with _patch_svc("list_replays", return_value=_ERROR):
            from sources.tools.bus_replay.management import bus_replay_query

            result = await bus_replay_query(
                BusReplayQueryInput(
                    action=BusReplayQueryAction.list,
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, ErrorEnvelope)


# ── bus_replay_admin_manage ───────────────────────────────────────────────────


class TestBusReplayAdminManage:
    @pytest.mark.asyncio
    async def test_remove_returns_removed_on_success(self) -> None:
        expected = BusReplayRemoveResult(removed=True, replay_name="CANReplay", timestamp_utc=_TS)
        with _patch_svc("remove_replay", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_admin_manage

            result = await bus_replay_admin_manage(
                BusReplayAdminManageInput(
                    action=BusReplayAdminManageAction.remove,
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusReplayRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_replay_name_returns_error(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_admin_manage

        result = await bus_replay_admin_manage(
            BusReplayAdminManageInput(
                action=BusReplayAdminManageAction.remove,
                system_index=0,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_clear_all_when_confirmed(self) -> None:
        expected = BusReplayClearAllResult(cleared=True, replays_removed=2, timestamp_utc=_TS)
        with _patch_svc("clear_all_replays", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_admin_manage

            result = await bus_replay_admin_manage(
                BusReplayAdminManageInput(
                    action=BusReplayAdminManageAction.clear_all,
                    system_index=0,
                    bus_type=BusType.CAN,
                    confirm=True,
                )
            )

        assert isinstance(result, BusReplayClearAllResult)
        assert result["cleared"] is True
        assert result["replays_removed"] == 2

    @pytest.mark.asyncio
    async def test_clear_all_aborted_when_not_confirmed(self) -> None:
        expected = BusReplayClearAllAborted()
        with _patch_svc("clear_all_replays", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_admin_manage

            result = await bus_replay_admin_manage(
                BusReplayAdminManageInput(
                    action=BusReplayAdminManageAction.clear_all,
                    system_index=0,
                    bus_type=BusType.CAN,
                    confirm=False,
                )
            )

        assert isinstance(result, BusReplayClearAllAborted)
        assert result["cleared"] is False

    @pytest.mark.asyncio
    async def test_set_activated_true_on_success(self) -> None:
        expected = BusReplaySetActivatedResult(
            activated=True,
            replay_name="CANReplay",
            state="Stopped",
            previous_activated=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("set_replay_activated", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_admin_manage

            result = await bus_replay_admin_manage(
                BusReplayAdminManageInput(
                    action=BusReplayAdminManageAction.set_activated,
                    replay_name="CANReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                    activated=True,
                )
            )

        assert isinstance(result, BusReplaySetActivatedResult)
        assert result["activated"] is True

    @pytest.mark.asyncio
    async def test_set_activated_missing_replay_name_returns_error(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_admin_manage

        result = await bus_replay_admin_manage(
            BusReplayAdminManageInput(
                action=BusReplayAdminManageAction.set_activated,
                system_index=0,
                bus_type=BusType.CAN,
                activated=True,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_set_activated_missing_activated_returns_error(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_admin_manage

        result = await bus_replay_admin_manage(
            BusReplayAdminManageInput(
                action=BusReplayAdminManageAction.set_activated,
                replay_name="CANReplay",
                system_index=0,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename_returns_renamed_on_success(self) -> None:
        expected = BusReplayRenameResult(
            renamed=True, old_name="CANReplay", new_name="TxReplay", timestamp_utc=_TS
        )
        with _patch_svc("rename_replay", return_value=expected):
            from sources.tools.bus_replay.management import bus_replay_admin_manage

            result = await bus_replay_admin_manage(
                BusReplayAdminManageInput(
                    action=BusReplayAdminManageAction.rename,
                    replay_name="CANReplay",
                    new_name="TxReplay",
                    system_index=0,
                    bus_type=BusType.CAN,
                )
            )

        assert isinstance(result, BusReplayRenameResult)
        assert result["renamed"] is True
        assert result["old_name"] == "CANReplay"
        assert result["new_name"] == "TxReplay"

    @pytest.mark.asyncio
    async def test_rename_missing_replay_name_returns_error(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_admin_manage

        result = await bus_replay_admin_manage(
            BusReplayAdminManageInput(
                action=BusReplayAdminManageAction.rename,
                system_index=0,
                bus_type=BusType.CAN,
                new_name="TxReplay",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename_missing_new_name_returns_error(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_admin_manage

        result = await bus_replay_admin_manage(
            BusReplayAdminManageInput(
                action=BusReplayAdminManageAction.rename,
                replay_name="CANReplay",
                system_index=0,
                bus_type=BusType.CAN,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── bus_replay_discover ───────────────────────────────────────────────────────


class TestBusReplayDiscover:
    @pytest.mark.asyncio
    async def test_returns_one_tool(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_discover

        result = await bus_replay_discover(AsyncMock())

        assert result["status"] == "ok"
        assert len(result["tools"]) == 2

    @pytest.mark.asyncio
    async def test_discover_has_admin_manage_tool(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_discover

        result = await bus_replay_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "bus_replay_admin_manage" in tool_names

    @pytest.mark.asyncio
    async def test_discover_admin_manage_actions(self) -> None:
        from sources.tools.bus_replay.management import bus_replay_discover

        result = await bus_replay_discover(AsyncMock())

        admin_tool = next(t for t in result["tools"] if t["tool_name"] == "bus_replay_admin_manage")
        assert "remove" in admin_tool["actions"]
        assert "clear_all" in admin_tool["actions"]
        assert "set_activated" in admin_tool["actions"]
        assert "rename" in admin_tool["actions"]


class TestBusReplayInputModels:
    """Test input model validation and serialization."""

    def test_bus_replay_create_input_validation(self) -> None:
        params = BusReplayCreateInput(replay_name="test", system_index=0, bus_type=BusType.CAN)
        assert params.replay_name == "test"
        assert params.bus_type == BusType.CAN
        assert params.bus_platform_index == 0
        assert params.physical_bus_access_index == 0

    def test_bus_replay_configure_input_modes(self) -> None:
        params1 = BusReplayConfigureInput(
            replay_name="test",
            system_index=0,
            bus_type=BusType.CAN,
            log_file_full_path="C:\\test.asc",
            replay_mode=ReplayMode.Infinite,
        )
        assert params1.replay_mode == ReplayMode.Infinite

        params2 = BusReplayConfigureInput(
            replay_name="test",
            system_index=0,
            bus_type=BusType.CAN,
            log_file_full_path="C:\\test.asc",
            replay_mode=ReplayMode.NumberOfPasses,
            number_of_passes=5,
        )
        assert params2.number_of_passes == 5

        params3 = BusReplayConfigureInput(
            replay_name="test",
            system_index=0,
            bus_type=BusType.CAN,
            log_file_full_path="C:\\test.asc",
            replay_mode=ReplayMode.Duration,
            duration_seconds=30.0,
        )
        assert params3.duration_seconds == 30.0
