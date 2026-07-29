"""Unit tests for controldesk_mcp.com_bridge.domains.instrument_com."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

from controldesk_mcp.com_bridge.domains.instrument_com import instrument_get_info, instrument_list


class _OpaqueMainVariableWithPath:
    @property
    def Path(self):
        return "XCP()://air_mass"

    @property
    def Connection(self):
        raise Exception("connection unavailable")

    def __str__(self) -> str:
        return "<COMObject <unknown>>"


class _OpaqueMainVariableWithConnectionPath:
    @property
    def Path(self):
        raise Exception("path unavailable")

    @property
    def Connection(self):
        connection = MagicMock()
        variable = MagicMock()
        type(variable).Path = PropertyMock(return_value="XCP(5ms)://control_out")
        type(connection).Variable = PropertyMock(return_value=variable)
        return connection

    def __str__(self) -> str:
        return "<COMObject <unknown>>"


class _OpaqueMainVariableUnresolved:
    @property
    def Path(self):
        raise Exception("path unavailable")

    @property
    def Connection(self):
        raise Exception("connection unavailable")

    def __str__(self) -> str:
        return "<COMObject <unknown>>"


def _make_position() -> MagicMock:
    pos = MagicMock()
    type(pos).X = PropertyMock(return_value=10)
    type(pos).Y = PropertyMock(return_value=20)
    type(pos).Width = PropertyMock(return_value=300)
    type(pos).Height = PropertyMock(return_value=200)
    return pos


def _make_app_with_instruments(instruments_list: list[MagicMock]) -> MagicMock:
    app = MagicMock()
    layout = MagicMock()
    type(layout).Name = PropertyMock(return_value="ControlLayout")

    instruments = MagicMock()
    type(instruments).Count = PropertyMock(return_value=len(instruments_list))

    def _item(key):
        if isinstance(key, int):
            return instruments_list[key]
        for instr in instruments_list:
            if str(instr.Name) == str(key):
                return instr
        raise Exception(f"Instrument '{key}' not found")

    instruments.Item.side_effect = _item
    layout.Instruments = instruments

    layout_mgmt = MagicMock()
    layout_mgmt.ActiveLayout = layout
    app.LayoutManagement = layout_mgmt
    return app


def test_instrument_list_extracts_main_variable_path_from_mainvariable_path() -> None:
    instr = MagicMock()
    type(instr).Name = PropertyMock(return_value="Display1")
    type(instr).TypeString = PropertyMock(return_value="Display")
    type(instr).Position = PropertyMock(return_value=_make_position())
    type(instr).MainVariable = PropertyMock(return_value=_OpaqueMainVariableWithPath())

    app = _make_app_with_instruments([instr])
    result = instrument_list(app)

    assert result["layout_name"] == "ControlLayout"
    assert len(result["instruments"]) == 1
    assert result["instruments"][0]["main_variable"] == "XCP()://air_mass"
    assert result["instruments"][0]["main_variable_source"] == "main_variable.path"


def test_instrument_get_info_uses_connection_variable_path_fallback_for_plotter_signal() -> None:
    signal = MagicMock()
    type(signal).MainVariable = PropertyMock(return_value=_OpaqueMainVariableWithConnectionPath())

    signals = MagicMock()
    type(signals).Count = PropertyMock(return_value=1)
    signals.Item.return_value = signal

    axis = MagicMock()
    axis.Signals = signals

    y_axes = MagicMock()
    type(y_axes).Count = PropertyMock(return_value=1)
    y_axes.Item.return_value = axis

    plot = MagicMock()
    plot.YAxes = y_axes

    instr = MagicMock()
    type(instr).Name = PropertyMock(return_value="TimePlotter1")
    type(instr).TypeString = PropertyMock(return_value="Time Plotter")
    type(instr).Position = PropertyMock(return_value=_make_position())
    type(instr).ActivePlot = PropertyMock(return_value=plot)

    app = _make_app_with_instruments([instr])
    with patch("controldesk_mcp.com_bridge.domains.instrument_com._as_plotter_signal", side_effect=lambda s: s):
        result = instrument_get_info(app, "TimePlotter1")

    assert len(result["signal_connections"]) == 1
    assert result["signal_connections"][0]["variable_path"] == "XCP(5ms)://control_out"
    assert result["signal_connections"][0]["variable_path_source"] == "connection.variable.path"


def test_instrument_get_info_emits_unresolved_sentinel_for_opaque_mainvariable() -> None:
    instr = MagicMock()
    type(instr).Name = PropertyMock(return_value="Display1")
    type(instr).TypeString = PropertyMock(return_value="Display")
    type(instr).Position = PropertyMock(return_value=_make_position())
    type(instr).MainVariable = PropertyMock(return_value=_OpaqueMainVariableUnresolved())

    app = _make_app_with_instruments([instr])
    result = instrument_get_info(app, "Display1")

    assert len(result["signal_connections"]) == 1
    assert result["signal_connections"][0]["variable_path"] == "<unresolved>"
    assert result["signal_connections"][0]["variable_path_unavailable_reason"] == "opaque_main_variable"
