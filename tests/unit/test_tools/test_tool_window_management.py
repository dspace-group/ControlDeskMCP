"""Unit tests for tool window MCP tools.

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tool_window import (
    ToolWindowCheckExistsResult,
    ToolWindowCloseResult,
    ToolWindowDiscoverResult,
    ToolWindowGetGeometryResult,
    ToolWindowGetStateResult,
    ToolWindowInfo,
    ToolWindowListInput,
    ToolWindowListResult,
    ToolWindowManageAction,
    ToolWindowManageInput,
    ToolWindowQueryAction,
    ToolWindowQueryInput,
    ToolWindowSetDockStateResult,
    ToolWindowShowInput,
    ToolWindowShowResult,
    ToolWindowState,
)

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.tool_window_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


class TestToolWindowList:
    @pytest.mark.asyncio
    async def test_returns_paginated_result(self) -> None:
        windows = [
            ToolWindowInfo(name="Project", caption="Project", is_visible=True, dock_state="Docked"),
            ToolWindowInfo(name="Variables", caption="Variables", is_visible=True, dock_state="AutoHidden"),
        ]
        expected = ToolWindowListResult(total_windows=2, windows=windows, timestamp_utc=_TS)
        with _patch_svc("list_windows", return_value=expected):
            from controldesk_mcp.tools.tool_window.management import tool_window_list

            result = await tool_window_list(ToolWindowListInput())

        assert isinstance(result, ToolWindowListResult)
        assert result["total_windows"] == 2
        assert len(result["windows"]) == 2

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("list_windows", return_value=_ERROR):
            from controldesk_mcp.tools.tool_window.management import tool_window_list

            result = await tool_window_list(ToolWindowListInput())

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


class TestToolWindowShow:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = ToolWindowShowResult(
            window_name="Variables",
            caption="Variables",
            is_now_visible=True,
            dock_state="Docked",
            timestamp_utc=_TS,
        )
        with _patch_svc("show_window", return_value=expected):
            from controldesk_mcp.tools.tool_window.management import tool_window_show

            result = await tool_window_show(ToolWindowShowInput(window_name="Variables"))

        assert isinstance(result, ToolWindowShowResult)
        assert result["shown"] is True
        assert result["window_name"] == "Variables"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("show_window", return_value=_ERROR):
            from controldesk_mcp.tools.tool_window.management import tool_window_show

            result = await tool_window_show(ToolWindowShowInput(window_name="NonExistent"))

        assert isinstance(result, ErrorEnvelope)


class TestToolWindowManage:
    @pytest.mark.asyncio
    async def test_close(self) -> None:
        expected = ToolWindowCloseResult(
            window_name="Messages",
            caption="Messages",
            layout_saved=True,
            is_now_visible=False,
            timestamp_utc=_TS,
        )
        with _patch_svc("close_window", return_value=expected):
            from controldesk_mcp.tools.tool_window.management import tool_window_manage

            result = await tool_window_manage(
                ToolWindowManageInput(
                    action=ToolWindowManageAction.close,
                    window_name="Messages",
                )
            )

        assert isinstance(result, ToolWindowCloseResult)
        assert result["closed"] is True
        assert result["window_name"] == "Messages"

    @pytest.mark.asyncio
    async def test_close_returns_error(self) -> None:
        with _patch_svc("close_window", return_value=_ERROR):
            from controldesk_mcp.tools.tool_window.management import tool_window_manage

            result = await tool_window_manage(
                ToolWindowManageInput(
                    action=ToolWindowManageAction.close,
                    window_name="NonExistent",
                )
            )

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_get_state(self) -> None:
        expected = ToolWindowGetStateResult(
            window_name="Variables",
            caption="Variables",
            is_visible=True,
            dock_state="Docked",
            timestamp_utc=_TS,
        )
        with _patch_svc("get_window_state", return_value=expected):
            from controldesk_mcp.tools.tool_window.management import tool_window_query

            result = await tool_window_query(
                ToolWindowQueryInput(
                    action=ToolWindowQueryAction.get_state,
                    window_name="Variables",
                )
            )

        assert isinstance(result, ToolWindowGetStateResult)
        assert result["window_name"] == "Variables"
        assert result["is_visible"] is True

    @pytest.mark.asyncio
    async def test_get_state_returns_error(self) -> None:
        with _patch_svc("get_window_state", return_value=_ERROR):
            from controldesk_mcp.tools.tool_window.management import tool_window_query

            result = await tool_window_query(
                ToolWindowQueryInput(
                    action=ToolWindowQueryAction.get_state,
                    window_name="NonExistent",
                )
            )

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_set_dock_state(self) -> None:
        expected = ToolWindowSetDockStateResult(
            window_name="Variables",
            caption="Variables",
            dock_state="AutoHidden",
            is_visible=True,
            timestamp_utc=_TS,
        )
        with _patch_svc("set_window_dock_state", return_value=expected):
            from controldesk_mcp.tools.tool_window.management import tool_window_manage

            result = await tool_window_manage(
                ToolWindowManageInput(
                    action=ToolWindowManageAction.set_dock_state,
                    window_name="Variables",
                    dock_state=ToolWindowState.AutoHidden,
                )
            )

        assert isinstance(result, ToolWindowSetDockStateResult)
        assert result["state_set"] is True
        assert result["dock_state"] == "AutoHidden"

    @pytest.mark.asyncio
    async def test_set_dock_state_missing_dock_state(self) -> None:
        from controldesk_mcp.tools.tool_window.management import tool_window_manage

        result = await tool_window_manage(
            ToolWindowManageInput(
                action=ToolWindowManageAction.set_dock_state,
                window_name="Variables",
                dock_state=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_missing_window_name_returns_error(self) -> None:
        from controldesk_mcp.tools.tool_window.management import tool_window_manage

        result = await tool_window_manage(
            ToolWindowManageInput(
                action=ToolWindowManageAction.close,
                window_name=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


class TestToolWindowQuery:
    @pytest.mark.asyncio
    async def test_check_exists_true(self) -> None:
        expected = ToolWindowCheckExistsResult(window_name="BusNavigator", exists=True, timestamp_utc=_TS)
        with _patch_svc("check_window_exists", return_value=expected):
            from controldesk_mcp.tools.tool_window.management import tool_window_query

            result = await tool_window_query(
                ToolWindowQueryInput(
                    action=ToolWindowQueryAction.check_exists,
                    window_name="BusNavigator",
                )
            )

        assert isinstance(result, ToolWindowCheckExistsResult)
        assert result["exists"] is True
        assert result["window_name"] == "BusNavigator"

    @pytest.mark.asyncio
    async def test_check_exists_false(self) -> None:
        expected = ToolWindowCheckExistsResult(window_name="EESPort Configurations", exists=False, timestamp_utc=_TS)
        with _patch_svc("check_window_exists", return_value=expected):
            from controldesk_mcp.tools.tool_window.management import tool_window_query

            result = await tool_window_query(
                ToolWindowQueryInput(
                    action=ToolWindowQueryAction.check_exists,
                    window_name="EESPort Configurations",
                )
            )

        assert isinstance(result, ToolWindowCheckExistsResult)
        assert result["exists"] is False

    @pytest.mark.asyncio
    async def test_get_geometry(self) -> None:
        expected = ToolWindowGetGeometryResult(
            window_name="Variables",
            caption="Variables",
            left=100,
            top=200,
            width=400,
            height=300,
            timestamp_utc=_TS,
        )
        with _patch_svc("get_window_geometry", return_value=expected):
            from controldesk_mcp.tools.tool_window.management import tool_window_query

            result = await tool_window_query(
                ToolWindowQueryInput(
                    action=ToolWindowQueryAction.get_geometry,
                    window_name="Variables",
                )
            )

        assert isinstance(result, ToolWindowGetGeometryResult)
        assert result["left"] == 100
        assert result["width"] == 400

    @pytest.mark.asyncio
    async def test_missing_window_name_returns_error(self) -> None:
        from controldesk_mcp.tools.tool_window.management import tool_window_query

        result = await tool_window_query(
            ToolWindowQueryInput(
                action=ToolWindowQueryAction.check_exists,
                window_name=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_get_geometry_returns_error(self) -> None:
        with _patch_svc("get_window_geometry", return_value=_ERROR):
            from controldesk_mcp.tools.tool_window.management import tool_window_query

            result = await tool_window_query(
                ToolWindowQueryInput(
                    action=ToolWindowQueryAction.get_geometry,
                    window_name="NonExistent",
                )
            )

        assert isinstance(result, ErrorEnvelope)


class TestToolWindowDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from controldesk_mcp.tools.tool_window.management import tool_window_discover

        result = await tool_window_discover(AsyncMock())

        assert isinstance(result, ToolWindowDiscoverResult)
        assert result["status"] == "ok"
        assert len(result["tools"]) == 1
        assert result["tools"][0]["tool_name"] == "controldesk_tool_window_query"

    @pytest.mark.asyncio
    async def test_discover_has_correct_actions(self) -> None:
        from controldesk_mcp.tools.tool_window.management import tool_window_discover

        result = await tool_window_discover(AsyncMock())

        tool = result["tools"][0]
        assert "check_exists" in tool["actions"]
        assert "get_geometry" in tool["actions"]


class TestToolWindowInputModels:
    def test_manage_input_instantiates(self) -> None:
        assert ToolWindowManageInput(action=ToolWindowManageAction.close, window_name="Variables") is not None

    def test_query_input_instantiates(self) -> None:
        assert ToolWindowQueryInput(action=ToolWindowQueryAction.check_exists, window_name="BusNavigator") is not None

    def test_list_input_defaults(self) -> None:
        params = ToolWindowListInput()
        assert params.limit == 200
        assert params.offset == 0
