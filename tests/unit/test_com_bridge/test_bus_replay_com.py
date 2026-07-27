"""Unit tests for controldesk_mcp.com_bridge.domains.bus_replay_com."""

from __future__ import annotations

from unittest.mock import MagicMock

from controldesk_mcp.com_bridge.domains.bus_replay_com import (
    clear_cache,
    create_replay,
    get_replay_state,
    list_replays,
    remove_replay,
    rename_replay,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_replay(
    name: str = "CAN Replay",
    state: int = 0,
    activated: bool = False,
) -> MagicMock:
    """Return a mock IBnReplay."""
    rep = MagicMock()
    rep.Name = name
    rep.State = state
    rep.Activated = activated
    cfg = MagicMock()
    cfg.LogFileFullPath = f"C:\\Logs\\{name}.asc"
    cfg.ReplayMode = 0
    cfg.NumberOfPasses = 1
    cfg.Duration = 0.0
    cfg.RollingMode = False
    rep.Configuration = cfg
    return rep


def _make_replays_collection(replays: list[MagicMock] | None = None) -> MagicMock:
    """Return a mock IBnReplays collection."""
    col = MagicMock()
    items = replays or []
    col.Count = len(items)

    def _item(idx):
        # Support both integer (list) and string (name) lookups
        if isinstance(idx, int):
            return items[idx]
        for r in items:
            if r.Name == idx:
                return r
        raise KeyError(f"Replay '{idx}' not found")

    col.Item.side_effect = _item

    def _add(name):
        new_rep = _make_replay(name=name)
        return new_rep

    col.Add.side_effect = _add
    return col


def _make_app(
    replays: list[MagicMock] | None = None,
    bus_type: str = "CAN",
) -> MagicMock:
    """Return a mock app with BusNavigator hierarchy."""
    app = MagicMock()
    bus_nav = MagicMock()

    system = MagicMock()
    bus_platform = MagicMock()

    bus_system = MagicMock()

    pba = MagicMock()
    pba.Replays = _make_replays_collection(replays)

    pba_col = MagicMock()
    pba_col.Item.side_effect = lambda idx: pba
    bus_system.PhysicalBusAccesses = pba_col

    # Support all bus types
    bus_platform.CANBusSystem = bus_system
    bus_platform.LINBusSystem = bus_system
    bus_platform.FlexRayBusSystem = bus_system
    bus_platform.EthernetBusSystem = bus_system

    bp_col = MagicMock()
    bp_col.Item.side_effect = lambda idx: bus_platform
    system.BusPlatforms = bp_col

    sys_col = MagicMock()
    sys_col.Item.side_effect = lambda idx: system
    bus_nav.Systems = sys_col

    app.BusNavigator = bus_nav
    return app


# ── create_replay ─────────────────────────────────────────────────────────────


class TestCreateReplay:
    def setup_method(self) -> None:
        clear_cache()

    def test_creates_replay_successfully(self) -> None:
        app = _make_app()
        result = create_replay(app, "TestReplay", 0, "CAN")
        assert result["replay_name"] == "TestReplay"
        assert result["system_index"] == 0
        assert result["bus_type"] == "CAN"
        assert result["created"] is True


# ── get_replay_state ──────────────────────────────────────────────────────────


class TestGetReplayState:
    def setup_method(self) -> None:
        clear_cache()

    def test_returns_stopped_state(self) -> None:
        rep = _make_replay(name="CAN Replay", state=0)
        app = _make_app(replays=[rep])
        result = get_replay_state(app, "CAN Replay", 0, "CAN")
        assert result["state"] == "Stopped"
        assert result["is_running"] is False

    def test_returns_running_state(self) -> None:
        rep = _make_replay(name="CAN Replay", state=1)
        app = _make_app(replays=[rep])
        result = get_replay_state(app, "CAN Replay", 0, "CAN")
        assert result["state"] == "Running"
        assert result["is_running"] is True


# ── list_replays ──────────────────────────────────────────────────────────────


class TestListReplays:
    def setup_method(self) -> None:
        clear_cache()

    def test_returns_empty_list(self) -> None:
        app = _make_app(replays=[])
        result = list_replays(app, 0, "CAN")
        assert result["replays"] == []
        assert result["total_count"] == 0

    def test_returns_replay_info(self) -> None:
        rep = _make_replay(name="CAN Replay", state=0)
        app = _make_app(replays=[rep])
        result = list_replays(app, 0, "CAN")
        assert len(result["replays"]) == 1
        assert result["replays"][0]["name"] == "CAN Replay"
        assert result["replays"][0]["state"] == "Stopped"

    def test_returns_multiple_replays(self) -> None:
        rep1 = _make_replay(name="Rep1", state=0)
        rep2 = _make_replay(name="Rep2", state=1)
        app = _make_app(replays=[rep1, rep2])
        result = list_replays(app, 0, "CAN")
        assert result["total_count"] == 2
        assert result["replays"][0]["name"] == "Rep1"
        assert result["replays"][1]["name"] == "Rep2"


# ── remove_replay ─────────────────────────────────────────────────────────────


class TestRemoveReplay:
    def setup_method(self) -> None:
        clear_cache()

    def test_removes_successfully(self) -> None:
        rep = _make_replay(name="CAN Replay")
        app = _make_app(replays=[rep])
        result = remove_replay(app, "CAN Replay", 0, "CAN")
        assert result["removed"] is True
        assert result["replay_name"] == "CAN Replay"


# ── rename_replay ─────────────────────────────────────────────────────────────


class TestRenameReplay:
    def setup_method(self) -> None:
        clear_cache()

    def test_renames_successfully(self) -> None:
        rep = _make_replay(name="CAN Replay")
        app = _make_app(replays=[rep])
        result = rename_replay(app, "CAN Replay", "NewReplay", 0, "CAN")
        assert result["old_name"] == "CAN Replay"
        assert result["new_name"] == "NewReplay"
        assert rep.Name == "NewReplay"

    def test_renames_from_cache(self) -> None:
        """Test rename works when the replay is already in cache."""
        from controldesk_mcp.com_bridge.domains.bus_replay_com import _replay_cache

        rep = _make_replay(name="CAN Replay")
        _replay_cache[(0, "CAN", "CAN Replay")] = rep
        app = _make_app(replays=[])
        result = rename_replay(app, "CAN Replay", "CachedNewReplay", 0, "CAN")
        assert result["old_name"] == "CAN Replay"
        assert result["new_name"] == "CachedNewReplay"
        # Old key evicted, new key present
        assert (0, "CAN", "CAN Replay") not in _replay_cache
        assert (0, "CAN", "CachedNewReplay") in _replay_cache
