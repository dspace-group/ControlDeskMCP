"""Unit tests for controldesk_mcp.services.instrument_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeConnectionError, BridgePreconditionError

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


# ── instrument_list ────────────────────────────────────────────────────────────


class TestInstrumentList:
    @pytest.mark.asyncio
    async def test_returns_instrument_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "layout_name": "ControlLayout",
            "instruments": [
                {
                    "name": "SpeedKnob",
                    "type": "Knob",
                    "x": 10,
                    "y": 10,
                    "width": 100,
                    "height": 100,
                    "main_variable": "XCP(5ms)://engine_speed",
                }
            ],
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.instrument_service import instrument_list

            result = await instrument_list()

        assert result.total_instruments == 1
        assert result.instruments[0].name == "SpeedKnob"
        assert result.layout_name == "ControlLayout"

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("disconnected"),
        ):
            from controldesk_mcp.services.instrument_service import instrument_list

            result = await instrument_list()

        assert "error_code" in result


# ── instrument_list_types ──────────────────────────────────────────────────────


class TestInstrumentListTypes:
    @pytest.mark.asyncio
    async def test_returns_type_catalog(self) -> None:
        types = [
            {
                "type_string": "Time Plotter",
                "category": "Data Displays",
                "signal_mode": "plotter_signal",
            },
            {"type_string": "Knob", "category": "Controls", "signal_mode": "main_variable"},
        ]

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            return_value=types,
        ):
            from controldesk_mcp.services.instrument_service import instrument_list_types

            result = await instrument_list_types()

        assert result.total_types == 2
        assert result.instrument_types[0].type_string == "Time Plotter"


# ── instrument_add ─────────────────────────────────────────────────────────────


class TestInstrumentAdd:
    @pytest.mark.asyncio
    async def test_returns_add_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "instrument_name": "SpeedKnob",
            "instrument_type": "Knob",
            "x": 10,
            "y": 10,
            "width": 100,
            "height": 100,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.instrument_service import instrument_add

            result = await instrument_add("Knob", "SpeedKnob", 10, 10, 100, 100)

        assert result.added is True
        assert result.instrument_name == "SpeedKnob"
        assert result.instrument_type == "Knob"

    @pytest.mark.asyncio
    async def test_returns_error_on_precondition_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgePreconditionError("no active layout", error_code="BRIDGE_NO_ACTIVE_LAYOUT"),
        ):
            from controldesk_mcp.services.instrument_service import instrument_add

            result = await instrument_add("Knob", "SpeedKnob", 10, 10, 100, 100)

        assert "error_code" in result


# ── instrument_remove ──────────────────────────────────────────────────────────


class TestInstrumentRemove:
    @pytest.mark.asyncio
    async def test_returns_remove_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, None],
        ):
            from controldesk_mcp.services.instrument_service import instrument_remove

            result = await instrument_remove("SpeedKnob")

        assert result.removed is True
        assert result.instrument_name == "SpeedKnob"


# ── instrument_connect_signal ──────────────────────────────────────────────────


class TestInstrumentConnectSignal:
    @pytest.mark.asyncio
    async def test_returns_connect_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "instrument_name": "SpeedKnob",
            "instrument_type": "Knob",
            "variable_path": "XCP(5ms)://engine_speed",
            "connection_mode": "main_variable",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.instrument_service import instrument_connect_signal

            result = await instrument_connect_signal("SpeedKnob", "XCP(5ms)://engine_speed", None, 0)

        assert result.connected is True
        assert result.connection_mode == "main_variable"


# ── instrument_arrange ─────────────────────────────────────────────────────────


class TestInstrumentArrange:
    @pytest.mark.asyncio
    async def test_returns_arrange_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "action": "align_top",
            "instrument_names": ["SpeedKnob", "ThrottlePlotter"],
            "group_name": None,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.instrument_service import instrument_arrange

            result = await instrument_arrange(["SpeedKnob", "ThrottlePlotter"], "align_top")

        assert result.arranged is True
        assert result.action == "align_top"
        assert len(result.instrument_names) == 2
