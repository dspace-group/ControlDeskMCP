"""Unit tests for sources.services.variable_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sources.com_bridge as bridge
from sources.com_bridge.errors import BridgeConnectionError, BridgeOperationError
from sources.models.variable import (
    VariableFindInput,
    VariableReadScalarInput,
    VariableWriteScalarInput,
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


# ── find_variable ─────────────────────────────────────────────────────────────


class TestFindVariable:
    @pytest.mark.asyncio
    async def test_returns_variable_info(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"name": "f_Kp_1", "type": "Parameter", "found": True}

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.variable_service import find_variable

            result = await find_variable(VariableFindInput(identifier="f_Kp_1"))

        assert result["name"] == "f_Kp_1"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("not connected"),
        ):
            from sources.services.variable_service import find_variable

            result = await find_variable(VariableFindInput(identifier="f_Kp_1"))

        assert "error_code" in result


# ── read_scalar ───────────────────────────────────────────────────────────────


class TestReadScalar:
    @pytest.mark.asyncio
    async def test_returns_scalar_value(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "variable_name": "control_out",
            "value": 3.14,
            "unit": "V",
            "variable_type": "Measurement",
            "value_format": "Converted",
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.variable_service import read_scalar_variable

            result = await read_scalar_variable(
                VariableReadScalarInput(variable_name="control_out")
            )

        assert result["value"] == 3.14

    @pytest.mark.asyncio
    async def test_returns_error_on_operation_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("variable not found", error_code="BRIDGE_OPERATION"),
        ):
            from sources.services.variable_service import read_scalar_variable

            result = await read_scalar_variable(
                VariableReadScalarInput(variable_name="nonexistent")
            )

        assert "error_code" in result


# ── write_scalar ──────────────────────────────────────────────────────────────


class TestWriteScalar:
    @pytest.mark.asyncio
    async def test_returns_write_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "variable_name": "f_Kp_1",
            "written_value": 2.5,
            "success": True,
            "written": True,
            "variable_type": "Parameter",
            "value_written": 2.5,
            "value_format": "Converted",
            "unit": "",
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from sources.services.variable_service import write_scalar_variable

            result = await write_scalar_variable(
                VariableWriteScalarInput(variable_name="f_Kp_1", value=2.5)
            )

        assert result["written_value"] == 2.5
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "sources.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("disconnected"),
        ):
            from sources.services.variable_service import write_scalar_variable

            result = await write_scalar_variable(
                VariableWriteScalarInput(variable_name="f_Kp_1", value=2.5)
            )

        assert "error_code" in result
