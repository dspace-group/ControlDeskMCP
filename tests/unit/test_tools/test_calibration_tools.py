"""Unit tests for calibration MCP tools.

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.calibration import (
    CalibrationActivateReferencePageResult,
    CalibrationActivateWorkingPageResult,
    CalibrationCopyReferencePageToWorkingResult,
    CalibrationCopyWorkingPageToReferenceResult,
    CalibrationDiscoverResult,
    CalibrationGetStateResult,
    CalibrationManageAction,
    CalibrationManageInput,
    CalibrationPageManageAction,
    CalibrationPageManageInput,
    CalibrationQueryAction,
    CalibrationQueryInput,
    CalibrationRefreshParametersResult,
    CalibrationStartInput,
    CalibrationStartResult,
    CalibrationStopInput,
    CalibrationStopResult,
    ProposedCalibrationApplyResult,
    ProposedCalibrationCancelResult,
    ProposedCalibrationManageAction,
    ProposedCalibrationManageInput,
    ProposedCalibrationStartResult,
    ProposedCalibrationStopResult,
)
from controldesk_mcp.models.errors import ErrorEnvelope

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.calibration_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


class TestCalibrationStart:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = CalibrationStartResult(started=True)
        with _patch_svc("start_calibration", return_value=expected):
            from controldesk_mcp.tools.calibration.management import calibration_start

            result = await calibration_start(CalibrationStartInput())

        assert isinstance(result, CalibrationStartResult)
        assert result["started"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("start_calibration", return_value=_ERROR):
            from controldesk_mcp.tools.calibration.management import calibration_start

            result = await calibration_start(CalibrationStartInput())

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"

    @pytest.mark.asyncio
    async def test_dry_run_delegates_to_preview_without_starting(self) -> None:
        from controldesk_mcp.models.base import DryRunPreviewResult

        preview = DryRunPreviewResult(
            tool="calibration_start",
            action="start",
            target="online_calibration",
            would_execute=True,
            current_state={"calibration_state": "Stopped"},
            message="Online calibration is not running — start would succeed.",
        )
        with (
            _patch_svc("dry_run_start_calibration", return_value=preview) as mock_dry_run,
            _patch_svc("start_calibration", return_value=_ERROR) as mock_start,
        ):
            from controldesk_mcp.tools.calibration.management import calibration_start

            result = await calibration_start(CalibrationStartInput(dry_run=True))

        assert isinstance(result, DryRunPreviewResult)
        assert result["would_execute"] is True
        mock_dry_run.assert_awaited_once()
        mock_start.assert_not_awaited()


class TestCalibrationStop:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = CalibrationStopResult(stopped=True)
        with _patch_svc("stop_calibration", return_value=expected):
            from controldesk_mcp.tools.calibration.management import calibration_stop

            result = await calibration_stop(CalibrationStopInput())

        assert isinstance(result, CalibrationStopResult)
        assert result["stopped"] is True


class TestCalibrationQuery:
    @pytest.mark.asyncio
    async def test_get_state(self) -> None:
        expected = CalibrationGetStateResult(
            calibration_state="Started",
            calibration_state_raw=1,
            proposed_calibration_state="Inactive",
            proposed_calibration_state_raw=0,
        )
        with _patch_svc("get_calibration_state", return_value=expected):
            from controldesk_mcp.tools.calibration.management import calibration_query

            result = await calibration_query(CalibrationQueryInput(action=CalibrationQueryAction.get_state))

        assert isinstance(result, CalibrationGetStateResult)
        assert result["calibration_state"] == "Started"

    @pytest.mark.asyncio
    async def test_get_state_returns_error(self) -> None:
        with _patch_svc("get_calibration_state", return_value=_ERROR):
            from controldesk_mcp.tools.calibration.management import calibration_query

            result = await calibration_query(CalibrationQueryInput(action=CalibrationQueryAction.get_state))

        assert isinstance(result, ErrorEnvelope)


class TestCalibrationManage:
    @pytest.mark.asyncio
    async def test_activate_reference_page(self) -> None:
        expected = CalibrationActivateReferencePageResult(activated=True, page="ReferencePage")
        with _patch_svc("activate_reference_page", return_value=expected):
            from controldesk_mcp.tools.calibration.management import calibration_manage

            result = await calibration_manage(
                CalibrationManageInput(action=CalibrationManageAction.activate_reference_page)
            )

        assert isinstance(result, CalibrationActivateReferencePageResult)
        assert result["activated"] is True
        assert result["page"] == "ReferencePage"

    @pytest.mark.asyncio
    async def test_activate_working_page(self) -> None:
        expected = CalibrationActivateWorkingPageResult(activated=True, page="WorkingPage")
        with _patch_svc("activate_working_page", return_value=expected):
            from controldesk_mcp.tools.calibration.management import calibration_manage

            result = await calibration_manage(
                CalibrationManageInput(action=CalibrationManageAction.activate_working_page)
            )

        assert isinstance(result, CalibrationActivateWorkingPageResult)
        assert result["activated"] is True
        assert result["page"] == "WorkingPage"

    @pytest.mark.asyncio
    async def test_refresh_parameters(self) -> None:
        expected = CalibrationRefreshParametersResult(refreshed=True, timestamp_utc=_TS)
        with _patch_svc("refresh_parameters", return_value=expected):
            from controldesk_mcp.tools.calibration.management import calibration_manage

            result = await calibration_manage(CalibrationManageInput(action=CalibrationManageAction.refresh_parameters))

        assert isinstance(result, CalibrationRefreshParametersResult)
        assert result["refreshed"] is True
        assert result["timestamp_utc"] == _TS


class TestProposedCalibrationManage:
    @pytest.mark.asyncio
    async def test_start(self) -> None:
        expected = ProposedCalibrationStartResult(started=True, proposed_calibration_active=True)
        with _patch_svc("start_proposed_calibration", return_value=expected):
            from controldesk_mcp.tools.calibration.management import proposed_calibration_manage

            result = await proposed_calibration_manage(
                ProposedCalibrationManageInput(action=ProposedCalibrationManageAction.start)
            )

        assert isinstance(result, ProposedCalibrationStartResult)
        assert result["started"] is True
        assert result["proposed_calibration_active"] is True

    @pytest.mark.asyncio
    async def test_stop(self) -> None:
        expected = ProposedCalibrationStopResult(stopped=True, changes_applied=False, proposed_calibration_active=False)
        with _patch_svc("stop_proposed_calibration", return_value=expected):
            from controldesk_mcp.tools.calibration.management import proposed_calibration_manage

            result = await proposed_calibration_manage(
                ProposedCalibrationManageInput(action=ProposedCalibrationManageAction.stop)
            )

        assert isinstance(result, ProposedCalibrationStopResult)
        assert result["stopped"] is True
        assert result["changes_applied"] is False

    @pytest.mark.asyncio
    async def test_apply(self) -> None:
        expected = ProposedCalibrationApplyResult(applied=True, proposed_calibration_active=False)
        with _patch_svc("apply_proposed_calibration", return_value=expected):
            from controldesk_mcp.tools.calibration.management import proposed_calibration_manage

            result = await proposed_calibration_manage(
                ProposedCalibrationManageInput(action=ProposedCalibrationManageAction.apply)
            )

        assert isinstance(result, ProposedCalibrationApplyResult)
        assert result["applied"] is True
        assert result["proposed_calibration_active"] is False

    @pytest.mark.asyncio
    async def test_cancel(self) -> None:
        expected = ProposedCalibrationCancelResult(cancelled=True, proposed_calibration_active=False)
        with _patch_svc("cancel_proposed_calibration", return_value=expected):
            from controldesk_mcp.tools.calibration.management import proposed_calibration_manage

            result = await proposed_calibration_manage(
                ProposedCalibrationManageInput(action=ProposedCalibrationManageAction.cancel)
            )

        assert isinstance(result, ProposedCalibrationCancelResult)
        assert result["cancelled"] is True
        assert result["proposed_calibration_active"] is False


class TestCalibrationPageManage:
    @pytest.mark.asyncio
    async def test_copy_working_to_reference(self) -> None:
        expected = CalibrationCopyWorkingPageToReferenceResult(
            copied=True,
            platform_name="XCP",
            source_page="WorkingPage",
            target_page="ReferencePage",
        )
        with _patch_svc("copy_working_page_to_reference", return_value=expected):
            from controldesk_mcp.tools.calibration.management import calibration_page_manage

            result = await calibration_page_manage(
                CalibrationPageManageInput(
                    action=CalibrationPageManageAction.copy_working_to_reference,
                    platform_name="XCP",
                )
            )

        assert isinstance(result, CalibrationCopyWorkingPageToReferenceResult)
        assert result["copied"] is True
        assert result["platform_name"] == "XCP"
        assert result["source_page"] == "WorkingPage"
        assert result["target_page"] == "ReferencePage"

    @pytest.mark.asyncio
    async def test_copy_reference_to_working(self) -> None:
        expected = CalibrationCopyReferencePageToWorkingResult(
            copied=True,
            platform_name="XCP",
            source_page="ReferencePage",
            target_page="WorkingPage",
        )
        with _patch_svc("copy_reference_page_to_working", return_value=expected):
            from controldesk_mcp.tools.calibration.management import calibration_page_manage

            result = await calibration_page_manage(
                CalibrationPageManageInput(
                    action=CalibrationPageManageAction.copy_reference_to_working,
                    platform_name="XCP",
                )
            )

        assert isinstance(result, CalibrationCopyReferencePageToWorkingResult)
        assert result["copied"] is True
        assert result["platform_name"] == "XCP"
        assert result["source_page"] == "ReferencePage"
        assert result["target_page"] == "WorkingPage"

    @pytest.mark.asyncio
    async def test_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.calibration.management import calibration_page_manage

        result = await calibration_page_manage(
            CalibrationPageManageInput(
                action=CalibrationPageManageAction.copy_working_to_reference,
                platform_name=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_copy_working_to_reference_returns_error(self) -> None:
        with _patch_svc("copy_working_page_to_reference", return_value=_ERROR):
            from controldesk_mcp.tools.calibration.management import calibration_page_manage

            result = await calibration_page_manage(
                CalibrationPageManageInput(
                    action=CalibrationPageManageAction.copy_working_to_reference,
                    platform_name="XCP",
                )
            )

        assert isinstance(result, ErrorEnvelope)


class TestCalibrationDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from controldesk_mcp.tools.calibration.management import calibration_discover

        result = await calibration_discover(AsyncMock())

        assert isinstance(result, CalibrationDiscoverResult)
        assert result["status"] == "ok"
        assert len(result["tools"]) == 3
        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "controldesk_calibration_query" in tool_names
        assert "controldesk_proposed_calibration_manage" in tool_names
        assert "controldesk_calibration_page_manage" in tool_names


class TestCalibrationInputModels:
    """Test that input models instantiate correctly."""

    def test_no_arg_input_models_instantiate(self) -> None:
        assert CalibrationStartInput() is not None
        assert CalibrationStopInput() is not None

    def test_manage_input_instantiates(self) -> None:
        assert CalibrationManageInput(action=CalibrationManageAction.activate_reference_page) is not None
        assert CalibrationQueryInput(action=CalibrationQueryAction.get_state) is not None
        assert ProposedCalibrationManageInput(action=ProposedCalibrationManageAction.start) is not None
        assert CalibrationPageManageInput(action=CalibrationPageManageAction.copy_working_to_reference) is not None
