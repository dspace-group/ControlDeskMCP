"""Unit tests for instrument MCP tools.

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sources.models.errors import ErrorEnvelope
from sources.models.instrument import (
    ArrangeAction,
    InstrumentAddResult,
    InstrumentArrangeResult,
    InstrumentConnectSignalResult,
    InstrumentDisconnectSignalResult,
    InstrumentDiscoverResult,
    InstrumentInfo,
    InstrumentListInput,
    InstrumentListResult,
    InstrumentManageAction,
    InstrumentManageInput,
    InstrumentRemoveResult,
    InstrumentSignalManageAction,
    InstrumentSignalManageInput,
    InstrumentTypeInfo,
    InstrumentTypeListResult,
)

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)
_INSTR = InstrumentInfo(
    name="SpeedKnob",
    type="Knob",
    x=10,
    y=10,
    width=100,
    height=100,
    main_variable="XCP(5ms)://engine_speed",
)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"sources.services.instrument_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── instrument_list ───────────────────────────────────────────────────────────


class TestInstrumentList:
    @pytest.mark.asyncio
    async def test_returns_list_result(self) -> None:
        expected = InstrumentListResult(
            layout_name="ControlLayout", total_instruments=1, instruments=[_INSTR]
        )
        with _patch_svc("instrument_list", return_value=expected):
            from sources.tools.instrument.management import instrument_list

            result = await instrument_list(InstrumentListInput())

        assert isinstance(result, InstrumentListResult)
        assert result["total_instruments"] == 1

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("instrument_list", return_value=_ERROR):
            from sources.tools.instrument.management import instrument_list

            result = await instrument_list(InstrumentListInput())

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_list_types_returns_type_result(self) -> None:
        types = InstrumentTypeListResult(
            total_types=2,
            instrument_types=[
                InstrumentTypeInfo(
                    type_string="Knob", category="Controls", signal_mode="main_variable"
                ),
                InstrumentTypeInfo(
                    type_string="Time Plotter",
                    category="Data Displays",
                    signal_mode="plotter_signal",
                ),
            ],
        )
        with _patch_svc("instrument_list_types", return_value=types):
            from sources.tools.instrument.management import instrument_list

            result = await instrument_list(InstrumentListInput(list_types=True))

        assert isinstance(result, InstrumentTypeListResult)
        assert result["total_types"] == 2


# ── instrument_manage — add ───────────────────────────────────────────────────


class TestInstrumentManageAdd:
    @pytest.mark.asyncio
    async def test_add_returns_result(self) -> None:
        expected = InstrumentAddResult(
            added=True,
            instrument_name="SpeedKnob",
            instrument_type="Knob",
            x=10,
            y=10,
            width=100,
            height=100,
            timestamp_utc=_TS,
        )
        with _patch_svc("instrument_add", return_value=expected):
            from sources.tools.instrument.management import instrument_manage

            result = await instrument_manage(
                InstrumentManageInput(
                    action=InstrumentManageAction.add,
                    instrument_type="Knob",
                    instrument_name="SpeedKnob",
                )
            )

        assert isinstance(result, InstrumentAddResult)
        assert result["added"] is True

    @pytest.mark.asyncio
    async def test_add_missing_type_returns_error(self) -> None:
        from sources.tools.instrument.management import instrument_manage

        result = await instrument_manage(
            InstrumentManageInput(action=InstrumentManageAction.add, instrument_name="SpeedKnob")
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_add_missing_name_returns_error(self) -> None:
        from sources.tools.instrument.management import instrument_manage

        result = await instrument_manage(
            InstrumentManageInput(action=InstrumentManageAction.add, instrument_type="Knob")
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── instrument_manage — remove ────────────────────────────────────────────────


class TestInstrumentManageRemove:
    @pytest.mark.asyncio
    async def test_remove_returns_result(self) -> None:
        expected = InstrumentRemoveResult(
            removed=True, instrument_name="SpeedKnob", timestamp_utc=_TS
        )
        with _patch_svc("instrument_remove", return_value=expected):
            from sources.tools.instrument.management import instrument_manage

            result = await instrument_manage(
                InstrumentManageInput(
                    action=InstrumentManageAction.remove, instrument_name="SpeedKnob"
                )
            )

        assert isinstance(result, InstrumentRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_name_returns_error(self) -> None:
        from sources.tools.instrument.management import instrument_manage

        result = await instrument_manage(
            InstrumentManageInput(action=InstrumentManageAction.remove)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── instrument_manage — arrange ───────────────────────────────────────────────


class TestInstrumentManageArrange:
    @pytest.mark.asyncio
    async def test_arrange_returns_result(self) -> None:
        expected = InstrumentArrangeResult(
            arranged=True,
            action="align_top",
            instrument_names=["SpeedKnob", "ThrottlePlotter"],
            group_name=None,
            timestamp_utc=_TS,
        )
        with _patch_svc("instrument_arrange", return_value=expected):
            from sources.tools.instrument.management import instrument_manage

            result = await instrument_manage(
                InstrumentManageInput(
                    action=InstrumentManageAction.arrange,
                    instrument_names=["SpeedKnob", "ThrottlePlotter"],
                    arrange_action=ArrangeAction.AlignTop,
                )
            )

        assert isinstance(result, InstrumentArrangeResult)
        assert result["arranged"] is True

    @pytest.mark.asyncio
    async def test_arrange_missing_names_returns_error(self) -> None:
        from sources.tools.instrument.management import instrument_manage

        result = await instrument_manage(
            InstrumentManageInput(
                action=InstrumentManageAction.arrange,
                arrange_action=ArrangeAction.AlignTop,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── instrument_signal_manage ──────────────────────────────────────────────────


class TestInstrumentSignalManage:
    @pytest.mark.asyncio
    async def test_connect_returns_result(self) -> None:
        expected = InstrumentConnectSignalResult(
            connected=True,
            instrument_name="SpeedKnob",
            instrument_type="Knob",
            variable_path="XCP(5ms)://engine_speed",
            connection_mode="main_variable",
            timestamp_utc=_TS,
        )
        with _patch_svc("instrument_connect_signal", return_value=expected):
            from sources.tools.instrument.management import instrument_signal_manage

            result = await instrument_signal_manage(
                InstrumentSignalManageInput(
                    action=InstrumentSignalManageAction.connect,
                    instrument_name="SpeedKnob",
                    variable_path="XCP(5ms)://engine_speed",
                )
            )

        assert isinstance(result, InstrumentConnectSignalResult)
        assert result["connected"] is True

    @pytest.mark.asyncio
    async def test_connect_missing_variable_path_returns_error(self) -> None:
        from sources.tools.instrument.management import instrument_signal_manage

        result = await instrument_signal_manage(
            InstrumentSignalManageInput(
                action=InstrumentSignalManageAction.connect,
                instrument_name="SpeedKnob",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_disconnect_returns_result(self) -> None:
        expected = InstrumentDisconnectSignalResult(
            disconnected=True,
            instrument_name="SpeedKnob",
            variable_path=None,
            timestamp_utc=_TS,
        )
        with _patch_svc("instrument_disconnect_signal", return_value=expected):
            from sources.tools.instrument.management import instrument_signal_manage

            result = await instrument_signal_manage(
                InstrumentSignalManageInput(
                    action=InstrumentSignalManageAction.disconnect,
                    instrument_name="SpeedKnob",
                )
            )

        assert isinstance(result, InstrumentDisconnectSignalResult)
        assert result["disconnected"] is True


# ── instrument_discover ───────────────────────────────────────────────────────


class TestInstrumentDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from unittest.mock import MagicMock

        ctx = MagicMock()
        with (
            patch("sources.tools.instrument.management.get_settings") as mock_settings,
            patch(
                "sources.tools.instrument.management.mcp.evict_stale_domains",
                new_callable=AsyncMock,
            ),
            patch(
                "sources.tools.instrument.management.mcp.activate_domain_tools",
                new_callable=AsyncMock,
            ),
        ):
            mock_settings.return_value.tool_ttl_enabled = False
            from sources.tools.instrument.management import instrument_discover

            result = await instrument_discover(ctx)

        assert isinstance(result, InstrumentDiscoverResult)
        assert len(result["tools"]) == 1
        assert result["tools"][0]["tool_name"] == "instrument_signal_manage"
