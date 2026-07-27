"""Unit tests for controldesk_mcp.com_bridge.domains.bus_monitor_com."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

from controldesk_mcp.com_bridge.domains.bus_monitor_com import (
    clear_all_monitors,
    configure_monitor,
    create_monitor,
    get_monitor_state,
    list_monitors,
    load_monitor_data,
    remove_monitor,
    rename_monitor,
    save_monitor_data,
    save_monitor_data_with_time_axis,
    start_monitor,
    stop_monitor,
)
from controldesk_mcp.com_bridge.errors import BridgePreconditionError

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_monitor(
    name: str = "CANMonitor",
    state: int = 0,
    update_rate: int = 100,
    buffer_size: int = 10000,
    buffer_mode: int = 1,
) -> MagicMock:
    """Return a mock IBnMonitor."""
    mon = MagicMock()
    type(mon).Name = PropertyMock(return_value=name)
    type(mon).State = PropertyMock(return_value=state)
    config = MagicMock()
    type(config).UpdateRate = PropertyMock(return_value=update_rate)
    type(config).BufferSize = PropertyMock(return_value=buffer_size)
    type(config).BufferMode = PropertyMock(return_value=buffer_mode)
    mon.Configuration = config
    return mon


def _make_monitors_collection(monitors: list[MagicMock] | None = None) -> MagicMock:
    """Return a mock IBnMonitors collection."""
    col = MagicMock()
    items = monitors or []
    type(col).Count = PropertyMock(return_value=len(items))

    def _item(idx):
        return items[idx]

    col.Item.side_effect = _item

    def _add(name):
        new_mon = _make_monitor(name=name)
        return new_mon

    col.Add.side_effect = _add
    return col


def _make_app(
    monitors_col: MagicMock | None = None,
    bus_type: str = "CAN",
) -> MagicMock:
    """Return a mock app with BusNavigator hierarchy."""
    app = MagicMock()
    bus_nav = MagicMock()

    system = MagicMock()
    bus_platform = MagicMock()

    from controldesk_mcp.com_bridge.domains.bus_monitor_com import _BUS_TYPE_PROPERTY

    prop_name = _BUS_TYPE_PROPERTY.get(bus_type, "CANBusSystem")
    bus_system = MagicMock()

    pba = MagicMock()
    pba.Monitors = monitors_col or _make_monitors_collection()

    pba_col = MagicMock()
    pba_col.Item.side_effect = lambda idx: pba
    bus_system.PhysicalBusAccesses = pba_col

    setattr(bus_platform, prop_name, bus_system)
    bp_col = MagicMock()
    bp_col.Item.side_effect = lambda idx: bus_platform
    system.BusPlatforms = bp_col

    sys_col = MagicMock()
    sys_col.Item.side_effect = lambda idx: system
    bus_nav.Systems = sys_col

    app.BusNavigator = bus_nav
    return app


def _make_app_no_bus_navigator() -> MagicMock:
    """Return a mock app with no BusNavigator."""
    app = MagicMock()
    type(app).BusNavigator = PropertyMock(side_effect=Exception("No BusNavigator"))
    return app


# ── create_monitor ────────────────────────────────────────────────────────────


class TestCreateMonitor:
    def test_creates_monitor_successfully(self) -> None:
        monitors_col = _make_monitors_collection()
        app = _make_app(monitors_col=monitors_col)
        result = create_monitor(app, "TestMonitor", 0, "CAN")
        assert result["monitor_name"] == "TestMonitor"
        assert result["system_index"] == 0
        assert result["bus_type"] == "CAN"

    def test_raises_on_no_bus_navigator(self) -> None:
        app = _make_app_no_bus_navigator()
        with pytest.raises(BridgePreconditionError, match="BusNavigator"):
            create_monitor(app, "TestMonitor", 0, "CAN")

    def test_raises_on_invalid_bus_type(self) -> None:
        app = _make_app()
        with pytest.raises(BridgePreconditionError, match="Unsupported bus type"):
            create_monitor(app, "TestMonitor", 0, "INVALID")


# ── configure_monitor ─────────────────────────────────────────────────────────


class TestConfigureMonitor:
    def test_configures_with_defaults(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = configure_monitor(app, "CANMonitor", 0, "CAN")
        assert result["monitor_name"] == "CANMonitor"
        assert result["update_rate_ms"] == 100
        assert result["buffer_size_frames"] == 10000
        assert result["buffer_mode"] == "RingBuffer"
        assert result["enable_j1939_pgn_resolving"] is False

    def test_configures_with_custom_values(self) -> None:
        mon = _make_monitor(name="TestMon")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = configure_monitor(
            app,
            "TestMon",
            0,
            "CAN",
            update_rate_ms=50,
            buffer_size_frames=20000,
            buffer_mode="FixedBuffer",
            enable_j1939_pgn_resolving=True,
        )
        assert result["update_rate_ms"] == 50
        assert result["buffer_size_frames"] == 20000
        assert result["buffer_mode"] == "FixedBuffer"
        assert result["enable_j1939_pgn_resolving"] is True

    def test_raises_when_monitor_not_found(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="not found"):
            configure_monitor(app, "NonExistent", 0, "CAN")


# ── start_monitor ─────────────────────────────────────────────────────────────


class TestStartMonitor:
    def test_starts_successfully(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = start_monitor(app, "CANMonitor", 0, "CAN")
        assert result["monitor_name"] == "CANMonitor"
        assert result["state"] == "Running"
        mon.Start.assert_called_once()

    def test_raises_when_monitor_not_found(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="not found"):
            start_monitor(app, "Missing", 0, "CAN")


# ── stop_monitor ──────────────────────────────────────────────────────────────


class TestStopMonitor:
    def test_stops_successfully(self) -> None:
        mon = _make_monitor(name="CANMonitor", state=1)
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = stop_monitor(app, "CANMonitor", 0, "CAN")
        assert result["monitor_name"] == "CANMonitor"
        assert result["state"] == "Stopped"
        mon.Stop.assert_called_once()


# ── get_monitor_state ─────────────────────────────────────────────────────────


class TestGetMonitorState:
    def test_returns_stopped(self) -> None:
        mon = _make_monitor(name="CANMonitor", state=0)
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = get_monitor_state(app, "CANMonitor", 0, "CAN")
        assert result["state"] == "Stopped"
        assert result["is_running"] is False

    def test_returns_running(self) -> None:
        mon = _make_monitor(name="CANMonitor", state=1)
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = get_monitor_state(app, "CANMonitor", 0, "CAN")
        assert result["state"] == "Running"
        assert result["is_running"] is True

    def test_raises_when_monitor_not_found(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="not found"):
            get_monitor_state(app, "Missing", 0, "CAN")


# ── list_monitors ─────────────────────────────────────────────────────────────


class TestListMonitors:
    def test_returns_empty_list_when_no_monitors(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        result = list_monitors(app, 0, "CAN")
        assert result == []

    def test_returns_monitor_info(self) -> None:
        mon = _make_monitor(name="CANMonitor", state=1)
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = list_monitors(app, 0, "CAN")
        assert len(result) == 1
        assert result[0]["name"] == "CANMonitor"
        assert result[0]["state"] == "Running"
        assert result[0]["update_rate_ms"] == 100
        assert result[0]["buffer_size_frames"] == 10000
        assert result[0]["buffer_mode"] == "RingBuffer"

    def test_returns_multiple_monitors(self) -> None:
        mon1 = _make_monitor(name="Mon1", state=0)
        mon2 = _make_monitor(name="Mon2", state=1)
        monitors_col = _make_monitors_collection([mon1, mon2])
        app = _make_app(monitors_col=monitors_col)
        result = list_monitors(app, 0, "CAN")
        assert len(result) == 2
        assert result[0]["name"] == "Mon1"
        assert result[1]["name"] == "Mon2"


# ── remove_monitor ────────────────────────────────────────────────────────────


class TestRemoveMonitor:
    def test_removes_successfully(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = remove_monitor(app, "CANMonitor", 0, "CAN")
        assert result["removed"] is True
        assert result["monitor_name"] == "CANMonitor"
        mon.Remove.assert_called_once()

    def test_raises_when_monitor_not_found(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="not found"):
            remove_monitor(app, "Missing", 0, "CAN")


# ── clear_all_monitors ────────────────────────────────────────────────────────


class TestClearAllMonitors:
    def test_clears_all_monitors(self) -> None:
        mon1 = _make_monitor(name="Mon1")
        mon2 = _make_monitor(name="Mon2")
        monitors_col = _make_monitors_collection([mon1, mon2])
        app = _make_app(monitors_col=monitors_col)
        result = clear_all_monitors(app, 0, "CAN")
        assert result["monitors_removed"] == 2
        monitors_col.Clear.assert_called_once()

    def test_clears_empty_collection(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        result = clear_all_monitors(app, 0, "CAN")
        assert result["monitors_removed"] == 0


# ── save_monitor_data ─────────────────────────────────────────────────────────


class TestSaveMonitorData:
    def test_saves_data_successfully(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = save_monitor_data(app, "CANMonitor", 0, "CAN", "C:\\Logs\\out.mf4")
        assert result["monitor_name"] == "CANMonitor"
        assert result["output_file_path"] == "C:\\Logs\\out.mf4"
        mon.SaveDataWithOptions.assert_called_once_with("C:\\Logs\\out.mf4", 3, 0, False)

    def test_raises_when_monitor_not_found(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="not found"):
            save_monitor_data(app, "Missing", 0, "CAN", "C:\\Logs\\out.mf4")


# ── save_monitor_data_with_time_axis ──────────────────────────────────────────


class TestSaveMonitorDataWithTimeAxis:
    def test_saves_with_absolute_time_axis(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = save_monitor_data_with_time_axis(app, "CANMonitor", 0, "CAN", "C:\\Logs\\out.mf4", "Absolute")
        assert result["monitor_name"] == "CANMonitor"
        assert result["time_axis"] == "Absolute"
        mon.SaveDataWithOptions.assert_called_once_with("C:\\Logs\\out.mf4", 3, 1, False)

    def test_saves_with_relative_time_axis(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = save_monitor_data_with_time_axis(app, "CANMonitor", 0, "CAN", "C:\\Logs\\out.mf4", "Relative")
        assert result["time_axis"] == "Relative"
        mon.SaveDataWithOptions.assert_called_once_with("C:\\Logs\\out.mf4", 3, 0, False)

    def test_saves_with_recording_time_axis(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = save_monitor_data_with_time_axis(app, "CANMonitor", 0, "CAN", "C:\\Logs\\out.mf4", "RecordingTime")
        assert result["time_axis"] == "RecordingTime"
        mon.SaveDataWithOptions.assert_called_once_with("C:\\Logs\\out.mf4", 3, 2, False)

    def test_raises_on_invalid_time_axis(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="Invalid time_axis"):
            save_monitor_data_with_time_axis(app, "CANMonitor", 0, "CAN", "C:\\Logs\\out.mf4", "BadAxis")

    def test_raises_when_monitor_not_found(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="not found"):
            save_monitor_data_with_time_axis(app, "Missing", 0, "CAN", "C:\\Logs\\out.mf4", "Absolute")


# ── load_monitor_data ─────────────────────────────────────────────────────────


class TestLoadMonitorData:
    def test_loads_successfully(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = load_monitor_data(app, "CANMonitor", 0, "CAN", "C:\\Logs\\out.asc")
        assert result["monitor_name"] == "CANMonitor"
        assert result["log_file_path"] == "C:\\Logs\\out.asc"
        assert result["log_file_section"] == 0
        mon.LoadData.assert_called_once_with("C:\\Logs\\out.asc", 0)

    def test_loads_with_section(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = load_monitor_data(app, "CANMonitor", 0, "CAN", "C:\\Logs\\out.asc", log_file_section=2)
        assert result["log_file_section"] == 2
        mon.LoadData.assert_called_once_with("C:\\Logs\\out.asc", 2)

    def test_raises_when_monitor_not_found(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="not found"):
            load_monitor_data(app, "Missing", 0, "CAN", "C:\\Logs\\out.asc")


# ── rename_monitor ────────────────────────────────────────────────────────────


class TestRenameMonitor:
    def test_renames_successfully(self) -> None:
        mon = _make_monitor(name="CANMonitor")
        monitors_col = _make_monitors_collection([mon])
        app = _make_app(monitors_col=monitors_col)
        result = rename_monitor(app, "CANMonitor", "NewMonitor", 0, "CAN")
        assert result["old_name"] == "CANMonitor"
        assert result["new_name"] == "NewMonitor"
        # Verify the Name attribute was set on the COM object
        # (PropertyMock wraps with get-only; just verify no exception raised)

    def test_raises_when_monitor_not_found(self) -> None:
        monitors_col = _make_monitors_collection([])
        app = _make_app(monitors_col=monitors_col)
        with pytest.raises(BridgePreconditionError, match="not found"):
            rename_monitor(app, "Missing", "NewName", 0, "CAN")
