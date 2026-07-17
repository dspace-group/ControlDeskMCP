"""Unit tests for sources.services.layout_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sources.com_bridge as bridge
from sources.com_bridge.errors import BridgeConnectionError, BridgePreconditionError

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


# ── layout_list ───────────────────────────────────────────────────────────────


class TestLayoutList:
    @pytest.mark.asyncio
    async def test_returns_layout_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        layouts = [
            {
                "name": "ControlLayout",
                "file_path": "C:/test/ControlLayout.cdl",
                "is_open": True,
                "is_active": True,
                "editing_mode": "Runtime",
            }
        ]

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, layouts],
        ):
            from sources.services.layout_service import layout_list

            result = await layout_list()

        assert result.total_layouts == 1
        assert result.layouts[0].name == "ControlLayout"

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("disconnected"),
        ):
            from sources.services.layout_service import layout_list

            result = await layout_list()

        assert "error_code" in result


# ── layout_create ──────────────────────────────────────────────────────────────


class TestLayoutCreate:
    @pytest.mark.asyncio
    async def test_returns_create_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"name": "NewLayout", "file_path": "C:/test/NewLayout.cdl"}

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.layout_service import layout_create

            result = await layout_create("NewLayout")

        assert result.created is True
        assert result.name == "NewLayout"

    @pytest.mark.asyncio
    async def test_returns_error_on_precondition_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgePreconditionError("no experiment", error_code="E001"),
        ):
            from sources.services.layout_service import layout_create

            result = await layout_create("NewLayout")

        assert "error_code" in result


# ── layout_open ────────────────────────────────────────────────────────────────


class TestLayoutOpen:
    @pytest.mark.asyncio
    async def test_returns_open_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "name": "ControlLayout",
            "file_path": "C:/test/ControlLayout.cdl",
            "editing_mode": "Runtime",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.layout_service import layout_open

            result = await layout_open("ControlLayout")

        assert result.opened is True
        assert result.name == "ControlLayout"


# ── layout_close ───────────────────────────────────────────────────────────────


class TestLayoutClose:
    @pytest.mark.asyncio
    async def test_returns_close_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"name": "ControlLayout", "saved_before_close": True}

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.layout_service import layout_close

            result = await layout_close("ControlLayout", save_before_close=True)

        assert result.closed is True
        assert result.saved_before_close is True


# ── layout_configure ───────────────────────────────────────────────────────────


class TestLayoutConfigure:
    @pytest.mark.asyncio
    async def test_returns_configure_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"name": "ControlLayout", "editing_mode": "Runtime"}

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.layout_service import layout_configure

            result = await layout_configure("ControlLayout", "Runtime")

        assert result.configured is True
        assert result.editing_mode == "Runtime"


# ── layout_export ───────────────────────────────────────────────────────────────


class TestLayoutExport:
    @pytest.mark.asyncio
    async def test_returns_export_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"layout_name": "ControlLayout", "export_path": "C:/out/export.lax"}

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.layout_service import layout_export

            result = await layout_export("C:/out/export.lax")

        assert result.exported is True
        assert result.layout_name == "ControlLayout"
