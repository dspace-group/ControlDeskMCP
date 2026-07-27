"""Unit tests for controldesk_mcp.com_bridge.domains.bus_logging_com."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from controldesk_mcp.com_bridge.domains.bus_logging_com import (
    clear_all_loggers,
    configure_filter,
    configure_logger,
    create_filter,
    create_logger,
    get_logger_state,
    list_filters,
    list_loggers,
    remove_filter,
    remove_logger,
    rename_logger,
    set_logger_activated,
    start_filter,
    start_logger,
    stop_filter,
    stop_logger,
)
from controldesk_mcp.com_bridge.errors import BridgePreconditionError

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_app(
    loggers: list[MagicMock] | None = None,
    filters: list[MagicMock] | None = None,
) -> MagicMock:
    """Return a mock app with BusNavigator hierarchy."""
    app = MagicMock()
    pba = MagicMock()

    # Loggers collection
    lgrs = MagicMock()
    lgr_list = loggers or []
    lgrs.Count = len(lgr_list)
    lgrs.Item = lambda i: lgr_list[i]
    lgrs.Add.return_value = MagicMock()
    pba.Loggers = lgrs

    # Filters collection
    flts = MagicMock()
    flt_list = filters or []
    flts.Count = len(flt_list)
    flts.Item = lambda i: flt_list[i]
    flts.Add.return_value = MagicMock()
    pba.Filters = flts

    # BusNavigator hierarchy
    bus_system = MagicMock()
    bus_system.PhysicalBusAccesses.Item.return_value = pba
    platform = MagicMock()
    platform.CANBusSystem = bus_system
    platform.LINBusSystem = bus_system
    platform.FlexRayBusSystem = bus_system
    platform.EthernetBusSystem = bus_system
    system = MagicMock()
    system.BusPlatforms.Item.return_value = platform
    app.BusNavigator.Systems.Item.return_value = system

    return app


def _make_logger(name: str, state: int = 0, activated: bool = False) -> MagicMock:
    """Return a mock IBnLogger."""
    lgr = MagicMock()
    lgr.Name = name
    lgr.State = state
    lgr.Activated = activated
    cfg = MagicMock()
    cfg.LogFileFullPath = f"C:\\Logs\\{name}.asc"
    lgr.Configuration = cfg
    return lgr


def _make_filter(name: str, loggers: list | None = None, replays: list | None = None) -> MagicMock:
    """Return a mock IBnFilter container."""
    flt = MagicMock()
    flt.Name = name
    lgr_list = loggers or []
    rep_list = replays or []
    flt.Loggers.Count = len(lgr_list)
    flt.Loggers.Item = lambda i: lgr_list[i]
    flt.Monitors.Count = 0
    flt.Replays.Count = len(rep_list)
    flt.Replays.Item = lambda i: rep_list[i]
    return flt


# ── create_logger ─────────────────────────────────────────────────────────────


class TestCreateLogger:
    def test_returns_created_dict(self) -> None:
        app = _make_app()
        result = create_logger(app, "CANRecorder", 0, "CAN")
        assert result["created"] is True
        assert result["logger_name"] == "CANRecorder"
        assert result["bus_type"] == "CAN"
        assert result["state"] == "Stopped"

    def test_raises_on_invalid_bus_type(self) -> None:
        app = _make_app()
        with pytest.raises(BridgePreconditionError, match="Unknown bus_type"):
            create_logger(app, "L1", 0, "INVALID")


# ── configure_logger ─────────────────────────────────────────────────────────


class TestConfigureLogger:
    def test_returns_configured_dict(self) -> None:
        lgr = _make_logger("L1")
        app = _make_app(loggers=[lgr])
        result = configure_logger(
            app, "L1", 0, "CAN", "C:\\Logs\\out.asc", max_duration_seconds=30.0
        )
        assert result["configured"] is True
        assert result["logger_name"] == "L1"
        assert result["log_file_full_path"] == "C:\\Logs\\out.asc"

    def test_sets_file_rolling_properties(self) -> None:
        lgr = _make_logger("L1")
        app = _make_app(loggers=[lgr])
        result = configure_logger(
            app,
            "L1",
            0,
            "CAN",
            "C:\\Logs\\out.asc",
            file_rolling_enabled=True,
            file_rolling_type="Size",
            file_rolling_interval_seconds=100.0,
        )
        assert result["configured"] is True
        assert result["file_rolling_enabled"] is True


# ── start_logger ──────────────────────────────────────────────────────────────


class TestStartLogger:
    def test_returns_started_dict(self) -> None:
        lgr = _make_logger("L1")
        app = _make_app(loggers=[lgr])
        result = start_logger(app, "L1", 0, "CAN")
        assert result["started"] is True
        assert result["state"] == "Running"
        assert result["activated"] is True

    def test_raises_when_logger_not_found(self) -> None:
        app = _make_app(loggers=[])
        with pytest.raises(BridgePreconditionError, match="not found"):
            start_logger(app, "NonExistent", 0, "CAN")


# ── stop_logger ───────────────────────────────────────────────────────────────


class TestStopLogger:
    def test_returns_stopped_dict(self) -> None:
        lgr = _make_logger("L1", state=1, activated=True)
        app = _make_app(loggers=[lgr])
        result = stop_logger(app, "L1", 0, "CAN")
        assert result["stopped"] is True
        assert result["state"] == "Stopped"


# ── get_logger_state ──────────────────────────────────────────────────────────


class TestGetLoggerState:
    def test_returns_running_state(self) -> None:
        lgr = _make_logger("L1", state=1, activated=True)
        app = _make_app(loggers=[lgr])
        result = get_logger_state(app, "L1", 0, "CAN")
        assert result["state"] == "Running"
        assert result["is_running"] is True
        assert result["activated"] is True

    def test_returns_stopped_state(self) -> None:
        lgr = _make_logger("L1", state=0, activated=False)
        app = _make_app(loggers=[lgr])
        result = get_logger_state(app, "L1", 0, "CAN")
        assert result["state"] == "Stopped"
        assert result["is_running"] is False


# ── list_loggers ──────────────────────────────────────────────────────────────


class TestListLoggers:
    def test_returns_all_loggers(self) -> None:
        lgr1 = _make_logger("L1", state=1, activated=True)
        lgr2 = _make_logger("L2", state=0, activated=False)
        app = _make_app(loggers=[lgr1, lgr2])
        result = list_loggers(app, 0, "CAN")
        assert result["total_count"] == 2
        assert result["loggers"][0]["name"] == "L1"
        assert result["loggers"][0]["state"] == "Running"
        assert result["loggers"][1]["name"] == "L2"
        assert result["loggers"][1]["state"] == "Stopped"

    def test_returns_empty_when_no_loggers(self) -> None:
        app = _make_app(loggers=[])
        result = list_loggers(app, 0, "CAN")
        assert result["total_count"] == 0
        assert result["loggers"] == []


# ── remove_logger ─────────────────────────────────────────────────────────────


class TestRemoveLogger:
    def test_returns_removed_dict(self) -> None:
        lgr = _make_logger("L1")
        app = _make_app(loggers=[lgr])
        result = remove_logger(app, "L1", 0, "CAN")
        assert result["removed"] is True
        assert result["logger_name"] == "L1"

    def test_raises_when_not_found(self) -> None:
        app = _make_app(loggers=[])
        with pytest.raises(BridgePreconditionError, match="not found"):
            remove_logger(app, "NonExistent", 0, "CAN")


# ── clear_all_loggers ────────────────────────────────────────────────────────


class TestClearAllLoggers:
    def test_returns_cleared_dict(self) -> None:
        lgr1 = _make_logger("L1")
        lgr2 = _make_logger("L2")
        app = _make_app(loggers=[lgr1, lgr2])
        result = clear_all_loggers(app, 0, "CAN")
        assert result["cleared"] is True
        assert result["loggers_removed"] == 2


# ── set_logger_activated ──────────────────────────────────────────────────────


class TestSetLoggerActivated:
    def test_returns_activated_dict(self) -> None:
        lgr = _make_logger("L1", activated=False)
        app = _make_app(loggers=[lgr])
        result = set_logger_activated(app, "L1", 0, "CAN", True)
        assert result["activated"] is True
        assert result["previous_activated"] is False


# ── create_filter ─────────────────────────────────────────────────────────────


class TestCreateFilter:
    def test_returns_created_dict(self) -> None:
        app = _make_app()
        result = create_filter(app, "CANFilter", 0, "CAN")
        assert result["created"] is True
        assert result["filter_name"] == "CANFilter"


# ── configure_filter ──────────────────────────────────────────────────────────


class TestConfigureFilter:
    def test_returns_sub_collection_metadata(self) -> None:
        flt = _make_filter("F1")
        app = _make_app(filters=[flt])
        result = configure_filter(app, "F1", 0, "CAN")
        assert result["filter_name"] == "F1"
        assert "loggers_count" in result
        assert "monitors_count" in result
        assert "replays_count" in result
        assert "note" in result


# ── start_filter ──────────────────────────────────────────────────────────────


class TestStartFilter:
    def test_returns_started_dict(self) -> None:
        flt = _make_filter("F1")
        app = _make_app(filters=[flt])
        result = start_filter(app, "F1", 0, "CAN")
        assert result["started"] is True
        assert "started_loggers" in result
        assert "started_replays" in result

    def test_starts_sub_loggers(self) -> None:
        lgr = _make_logger("SL1")
        flt = _make_filter("F1", loggers=[lgr])
        app = _make_app(filters=[flt])
        result = start_filter(app, "F1", 0, "CAN")
        assert "SL1" in result["started_loggers"]


# ── stop_filter ───────────────────────────────────────────────────────────────


class TestStopFilter:
    def test_returns_stopped_dict(self) -> None:
        flt = _make_filter("F1")
        app = _make_app(filters=[flt])
        result = stop_filter(app, "F1", 0, "CAN")
        assert result["stopped"] is True
        assert "stopped_loggers" in result
        assert "stopped_replays" in result


# ── list_filters ──────────────────────────────────────────────────────────────


class TestListFilters:
    def test_returns_all_filters(self) -> None:
        flt1 = _make_filter("F1")
        flt2 = _make_filter("F2")
        app = _make_app(filters=[flt1, flt2])
        result = list_filters(app, 0, "CAN")
        assert result["total_filters"] == 2
        assert result["filters"][0]["name"] == "F1"
        assert result["filters"][1]["name"] == "F2"


# ── remove_filter ─────────────────────────────────────────────────────────────


class TestRemoveFilter:
    def test_returns_removed_dict(self) -> None:
        flt = _make_filter("F1")
        app = _make_app(filters=[flt])
        result = remove_filter(app, "F1", 0, "CAN")
        assert result["removed"] is True

    def test_raises_when_not_found(self) -> None:
        app = _make_app(filters=[])
        with pytest.raises(BridgePreconditionError, match="not found"):
            remove_filter(app, "NonExistent", 0, "CAN")


# ── rename_logger ─────────────────────────────────────────────────────────────


class TestRenameLogger:
    def test_renames_successfully(self) -> None:
        lgr = _make_logger("CAN Logger")
        app = _make_app(loggers=[lgr])
        result = rename_logger(app, "CAN Logger", "NewLogger", 0, "CAN")
        assert result["old_name"] == "CAN Logger"
        assert result["new_name"] == "NewLogger"
        assert lgr.Name == "NewLogger"

    def test_raises_when_not_found(self) -> None:
        app = _make_app(loggers=[])
        with pytest.raises(BridgePreconditionError, match="not found"):
            rename_logger(app, "NonExistent", "NewName", 0, "CAN")
