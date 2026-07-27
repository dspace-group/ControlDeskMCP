"""Unit tests for controldesk_mcp.services.tool_window_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeConnectionError, BridgePreconditionError
from controldesk_mcp.models.tool_window import (
    ToolWindowCheckExistsInput,
    ToolWindowShowInput,
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


# ── list_windows ──────────────────────────────────────────────────────────────


class TestListWindows:
    @pytest.mark.asyncio
    async def test_returns_window_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        windows = [
            {
                "name": "Variables",
                "caption": "Variables",
                "is_visible": True,
                "dock_state": "Docked",
            }
        ]

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, windows],
        ):
            from controldesk_mcp.services.tool_window_service import list_windows

            result = await list_windows()

        assert result["total_windows"] == 1
        assert result["windows"][0].name == "Variables"

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("disconnected"),
        ):
            from controldesk_mcp.services.tool_window_service import list_windows

            result = await list_windows()

        assert "error_code" in result


# ── show_window ───────────────────────────────────────────────────────────────


class TestShowWindow:
    @pytest.mark.asyncio
    async def test_returns_show_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "caption": "Variables",
            "is_now_visible": True,
            "dock_state": "Docked",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.tool_window_service import show_window

            result = await show_window(ToolWindowShowInput(window_name="Variables"))

        assert result["window_name"] == "Variables"
        assert result["is_now_visible"] is True

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgePreconditionError("no experiment"),
        ):
            from controldesk_mcp.services.tool_window_service import show_window

            result = await show_window(ToolWindowShowInput(window_name="Variables"))

        assert "error_code" in result


# ── check_window_exists ───────────────────────────────────────────────────────


class TestCheckWindowExists:
    @pytest.mark.asyncio
    async def test_returns_exists_true(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, True],
        ):
            from controldesk_mcp.services.tool_window_service import check_window_exists

            result = await check_window_exists(ToolWindowCheckExistsInput(window_name="Variables"))

        assert result["exists"] is True
