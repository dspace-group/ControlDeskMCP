"""Unit tests for controldesk_mcp.services.variable_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeConnectionError, BridgeOperationError
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.variable import (
    VariableFindInput,
    VariableReadArrayElementInput,
    VariableReadScalarInput,
    VariableWriteArrayElementInput,
    VariableWriteScalarInput,
)
from controldesk_mcp.services.variable_path_resolver import ResolutionStatus, ResolverResult, ScoredCandidate

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


# ── find_variable ─────────────────────────────────────────────────────────────


class TestFindVariable:
    @pytest.mark.asyncio
    async def test_returns_variable_info(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"name": "f_Kp_1", "type": "Parameter", "found": True}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.variable_service import find_variable

            result = await find_variable(VariableFindInput(identifier="f_Kp_1"))

        assert result["name"] == "f_Kp_1"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("not connected"),
        ):
            from controldesk_mcp.services.variable_service import find_variable

            result = await find_variable(VariableFindInput(identifier="f_Kp_1"))

        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_name_miss_uses_resolver_fallback_and_returns_metadata(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        class _ResolverStub:
            async def resolve(self, _query: str) -> ResolverResult:
                return ResolverResult(
                    status=ResolutionStatus.resolved,
                    resolved_path="XCP()://f_Kp_1",
                    confidence=0.93,
                    candidates=[],
                    attempt_log=["find name variant='f_Kp_1'"],
                    telemetry={"strategy": "find_name", "attempts_count": 1},
                )

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[
                    app_mock,
                    {"found": False},
                    {
                        "found": True,
                        "name": "f_Kp_1",
                        "variable_type": "Parameter",
                        "identifier": {"connection_path": "XCP()://f_Kp_1"},
                    },
                ],
            ),
            patch(
                "controldesk_mcp.services.variable_service._get_variable_path_resolver",
                return_value=_ResolverStub(),
            ),
        ):
            from controldesk_mcp.services.variable_service import find_variable

            result = await find_variable(VariableFindInput(identifier="kp"))

        assert result["found"] is True
        assert result["name"] == "f_Kp_1"
        assert result["resolution_details"]["status"] == "resolved"
        assert result["resolution_details"]["resolved_path"] == "XCP()://f_Kp_1"
        assert result["resolution_details"]["telemetry"]["strategy"] == "find_name"

    @pytest.mark.asyncio
    async def test_name_miss_returns_ambiguous_resolution_details(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        class _ResolverStub:
            async def resolve(self, _query: str) -> ResolverResult:
                return ResolverResult(
                    status=ResolutionStatus.ambiguous,
                    resolved_path=None,
                    confidence=0.65,
                    candidates=[
                        ScoredCandidate(
                            name="air_mass_front",
                            connection_path="XCP()://air_mass_front",
                            score=0.65,
                            rationale="token overlap",
                        )
                    ],
                    attempt_log=["list_all page=1 offset=0 limit=500"],
                    telemetry={"strategy": "list_all_ambiguous", "attempts_count": 1},
                )

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, {"found": False}],
            ),
            patch(
                "controldesk_mcp.services.variable_service._get_variable_path_resolver",
                return_value=_ResolverStub(),
            ),
        ):
            from controldesk_mcp.services.variable_service import find_variable

            result = await find_variable(VariableFindInput(identifier="air mass"))

        assert result["found"] is False
        assert result["resolution_details"]["status"] == "ambiguous"
        assert result["resolution_details"]["confidence"] == 0.65
        assert len(result["resolution_details"]["candidates"]) == 1
        assert result["resolution_details"]["telemetry"]["strategy"] == "list_all_ambiguous"


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

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, com_result],
            ),
            patch(
                "controldesk_mcp.services.variable_service._resolve_variable_name_for_read",
                new_callable=AsyncMock,
                return_value="XCP(5ms)://control_out",
            ),
        ):
            from controldesk_mcp.services.variable_service import read_scalar_variable

            result = await read_scalar_variable(VariableReadScalarInput(variable_name="control_out"))

        assert result["value"] == 3.14

    @pytest.mark.asyncio
    async def test_returns_error_on_operation_error(self) -> None:
        _make_connected_bridge()

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=BridgeOperationError("variable not found", error_code="BRIDGE_OPERATION"),
            ),
            patch(
                "controldesk_mcp.services.variable_service._resolve_variable_name_for_read",
                new_callable=AsyncMock,
                return_value="XCP()://nonexistent",
            ),
        ):
            from controldesk_mcp.services.variable_service import read_scalar_variable

            result = await read_scalar_variable(VariableReadScalarInput(variable_name="nonexistent"))

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

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, com_result],
            ),
            patch(
                "controldesk_mcp.services.variable_service._resolve_variable_name_for_write",
                new_callable=AsyncMock,
                return_value="XCP()://f_Kp_1",
            ),
        ):
            from controldesk_mcp.services.variable_service import write_scalar_variable

            result = await write_scalar_variable(VariableWriteScalarInput(variable_name="f_Kp_1", value=2.5))

        assert result["written_value"] == 2.5
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=BridgeConnectionError("disconnected"),
            ),
            patch(
                "controldesk_mcp.services.variable_service._resolve_variable_name_for_write",
                new_callable=AsyncMock,
                return_value="XCP()://f_Kp_1",
            ),
        ):
            from controldesk_mcp.services.variable_service import write_scalar_variable

            result = await write_scalar_variable(VariableWriteScalarInput(variable_name="f_Kp_1", value=2.5))

        assert "error_code" in result


class TestArrayElementNormalization:
    @pytest.mark.asyncio
    async def test_read_array_element_normalizes_element_path_fields(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "element_path": "XCP()://ParamVector[0]",
            "variable_type": "Measurement",
            "index": 0,
            "value": 12.34,
            "value_format": "Converted",
            "unit": "V",
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.variable_service import read_array_element

            result = await read_array_element(
                VariableReadArrayElementInput(
                    element_path="XCP()://ParamVector[0]",
                )
            )

        assert result["array_path"] == "XCP()://ParamVector"
        assert result["variable_name"] == "XCP()://ParamVector"
        assert result["index"] == 0

    @pytest.mark.asyncio
    async def test_write_array_element_normalizes_element_path_fields(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {
            "written": True,
            "element_path": "XCP()://ParamVector[0]",
            "variable_type": "Parameter",
            "index": 0,
            "value_written": 15,
            "value_format": "Converted",
            "unit": "",
            "timestamp_utc": "2024-01-01T00:00:00Z",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.variable_service import write_array_element

            result = await write_array_element(
                VariableWriteArrayElementInput(
                    element_path="XCP()://ParamVector[0]",
                    value=15,
                )
            )

        assert result["array_path"] == "XCP()://ParamVector"
        assert result["variable_name"] == "XCP()://ParamVector"
        assert result["written"] is True


# ── phase2 resolver and write safety gates ───────────────────────────────────


class TestPhase2Resolution:
    @pytest.mark.asyncio
    async def test_resolve_for_read_returns_ambiguous_error(self) -> None:
        class _ResolverStub:
            async def resolve(self, _query: str, *, hint_query: str | None = None) -> ResolverResult:
                return ResolverResult(
                    status=ResolutionStatus.ambiguous,
                    resolved_path=None,
                    confidence=0.71,
                    candidates=[
                        ScoredCandidate(
                            name="air_mass_front",
                            connection_path="XCP()://air_mass_front",
                            score=0.71,
                            rationale="token overlap",
                        )
                    ],
                    attempt_log=["find name variant='airMass'", "list_all page=1 offset=0 limit=500"],
                )

        with patch(
            "controldesk_mcp.services.variable_service._get_variable_path_resolver",
            return_value=_ResolverStub(),
        ):
            from controldesk_mcp.services.variable_service import _resolve_variable_name_for_read

            result = await _resolve_variable_name_for_read("air mass")

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "VARIABLE_RESOLUTION_AMBIGUOUS"

    @pytest.mark.asyncio
    async def test_resolve_for_write_blocks_non_writable(self) -> None:
        with (
            patch(
                "controldesk_mcp.services.variable_service._resolve_variable_name_for_read",
                new_callable=AsyncMock,
                return_value="XCP()://f_Kp_1",
            ),
            patch(
                "controldesk_mcp.services.variable_service._resolver_find_variable",
                new_callable=AsyncMock,
                return_value={"found": True, "name": "f_Kp_1", "is_writable": False},
            ),
        ):
            from controldesk_mcp.services.variable_service import _resolve_variable_name_for_write

            result = await _resolve_variable_name_for_write("f_Kp_1")

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "VARIABLE_NOT_WRITABLE"

    @pytest.mark.asyncio
    async def test_resolve_for_write_blocks_init_only_when_calibration_started(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with (
            patch(
                "controldesk_mcp.services.variable_service._resolve_variable_name_for_read",
                new_callable=AsyncMock,
                return_value="XCP()://f_InitOnly",
            ),
            patch(
                "controldesk_mcp.services.variable_service._resolver_find_variable",
                new_callable=AsyncMock,
                return_value={
                    "found": True,
                    "name": "f_InitOnly",
                    "is_writable": True,
                    "is_changeable_only_during_initialization": True,
                },
            ),
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, {"calibration_state": "Started"}],
            ),
        ):
            from controldesk_mcp.services.variable_service import _resolve_variable_name_for_write

            result = await _resolve_variable_name_for_write("f_InitOnly")

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "VARIABLE_INIT_ONLY_LOCKED"
