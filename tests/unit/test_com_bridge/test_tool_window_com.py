"""Unit tests for controldesk_mcp.com_bridge.domains.tool_window_com."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from controldesk_mcp.com_bridge.domains import tool_window_com
from controldesk_mcp.com_bridge.errors import BridgePreconditionError

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_window(
    caption: str = "Variables",
    state: int = 3,  # 3 = Docked
    visible: bool = True,
) -> MagicMock:
    win = MagicMock()
    win.Caption = caption
    win.State = state
    win.Visible = visible
    return win


def _make_windows(*windows: MagicMock, contains: bool = True) -> MagicMock:
    col = MagicMock()
    col.Count = len(windows)
    # Item(int) — 1-based index during enumeration
    col.Item.side_effect = lambda idx: (
        windows[int(idx) - 1]
        if isinstance(idx, int)
        else next(
            (w for w in windows if w.Caption == idx), (_ for _ in ()).throw(Exception("not found"))
        )
    )
    col.Contains.return_value = contains
    return col


def _make_app(*windows: MagicMock, contains: bool = True) -> MagicMock:
    app = MagicMock()
    app.MainWindow.Windows = _make_windows(*windows, contains=contains)
    return app


# ── _parse_state ──────────────────────────────────────────────────────────────


class TestParseState:
    def test_parses_int_to_string(self) -> None:
        assert tool_window_com._parse_state(3) == "Docked"
        assert tool_window_com._parse_state(7) == "DockedAsDocument"
        assert tool_window_com._parse_state(4) == "AutoHidden"
        assert tool_window_com._parse_state(5) == "Floating"
        assert tool_window_com._parse_state(6) == "Closed"

    def test_parses_known_string(self) -> None:
        assert tool_window_com._parse_state("Docked") == "Docked"
        assert tool_window_com._parse_state("Floating") == "Floating"

    def test_parses_int_string(self) -> None:
        assert tool_window_com._parse_state("3") == "Docked"
        assert tool_window_com._parse_state("6") == "Closed"

    def test_returns_raw_for_unknown(self) -> None:
        assert tool_window_com._parse_state(99) == "99"
        assert tool_window_com._parse_state("unknown") == "unknown"


# ── list_windows ──────────────────────────────────────────────────────────────


class TestListWindows:
    def test_returns_all_windows(self) -> None:
        app = _make_app(
            _make_window("Project", state=3, visible=True),
            _make_window("Variables", state=4, visible=True),
            _make_window("Messages", state=6, visible=False),
        )
        result = tool_window_com.list_windows(app)
        assert len(result) == 3
        assert result[0]["name"] == "Project"
        assert result[0]["dock_state"] == "Docked"
        assert result[0]["is_visible"] is True
        assert result[1]["name"] == "Variables"
        assert result[1]["dock_state"] == "AutoHidden"
        assert result[2]["name"] == "Messages"
        assert result[2]["dock_state"] == "Closed"
        assert result[2]["is_visible"] is False

    def test_returns_empty_list_when_no_windows(self) -> None:
        app = _make_app()
        result = tool_window_com.list_windows(app)
        assert result == []

    def test_skips_window_that_raises_during_enumeration(self) -> None:
        """Windows that raise on property access are silently skipped."""
        from unittest.mock import PropertyMock

        good_win = _make_window("Project", state=0, visible=True)
        bad_win = MagicMock()
        # Make Caption raise for the bad window
        type(bad_win).Caption = PropertyMock(side_effect=Exception("COM error"))
        col = MagicMock()
        col.Count = 2
        col.Item.side_effect = lambda idx: good_win if idx == 1 else bad_win
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.list_windows(app)

        # The good window is returned; the bad one is silently skipped
        assert len(result) == 1
        assert result[0]["name"] == "Project"

    def test_raises_on_windows_collection_error(self) -> None:
        from unittest.mock import PropertyMock

        app = MagicMock()
        type(app.MainWindow).Windows = PropertyMock(side_effect=Exception("COM error"))
        with pytest.raises(Exception):
            tool_window_com.list_windows(app)


# ── show_window ───────────────────────────────────────────────────────────────


class TestShowWindow:
    def test_calls_show_and_returns_state(self) -> None:
        win = _make_window("Variables", state=3, visible=True)
        col = MagicMock()
        col.Item.return_value = win
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.show_window(app, "Variables")

        win.Show.assert_called_once()
        assert result["caption"] == "Variables"
        assert result["dock_state"] == "Docked"
        assert result["is_now_visible"] is True

    def test_raises_precondition_error_when_item_not_found(self) -> None:
        col = MagicMock()
        col.Item.side_effect = Exception("not found")
        app = MagicMock()
        app.MainWindow.Windows = col

        with pytest.raises(BridgePreconditionError, match="does not exist"):
            tool_window_com.show_window(app, "NonExistentWindow")


# ── close_window ──────────────────────────────────────────────────────────────


class TestCloseWindow:
    def test_calls_close_with_save_layout_true(self) -> None:
        win = _make_window("Messages", state=6, visible=False)
        col = MagicMock()
        col.Item.return_value = win
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.close_window(app, "Messages", save_layout=True)

        win.Close.assert_called_once_with(True)
        assert result["caption"] == "Messages"
        assert result["layout_saved"] is True
        assert result["is_now_visible"] is False

    def test_calls_close_with_save_layout_false(self) -> None:
        win = _make_window("Messages", state=6, visible=False)
        col = MagicMock()
        col.Item.return_value = win
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.close_window(app, "Messages", save_layout=False)

        win.Close.assert_called_once_with(False)
        assert result["layout_saved"] is False

    def test_raises_precondition_error_when_item_not_found(self) -> None:
        col = MagicMock()
        col.Item.side_effect = Exception("not found")
        app = MagicMock()
        app.MainWindow.Windows = col

        with pytest.raises(BridgePreconditionError, match="does not exist"):
            tool_window_com.close_window(app, "NonExistent")


# ── get_window_state ──────────────────────────────────────────────────────────


class TestGetWindowState:
    def test_returns_state_and_visibility(self) -> None:
        win = _make_window("Measurement Configuration", state=7, visible=True)
        col = MagicMock()
        col.Item.return_value = win
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.get_window_state(app, "Measurement Configuration")

        assert result["caption"] == "Measurement Configuration"
        assert result["dock_state"] == "DockedAsDocument"
        assert result["is_visible"] is True

    def test_returns_closed_state_with_not_visible(self) -> None:
        win = _make_window("Properties", state=6, visible=False)
        col = MagicMock()
        col.Item.return_value = win
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.get_window_state(app, "Properties")

        assert result["dock_state"] == "Closed"
        assert result["is_visible"] is False

    def test_raises_precondition_error_when_item_not_found(self) -> None:
        col = MagicMock()
        col.Item.side_effect = Exception("not found")
        app = MagicMock()
        app.MainWindow.Windows = col

        with pytest.raises(BridgePreconditionError, match="does not exist"):
            tool_window_com.get_window_state(app, "NonExistent")


# ── set_window_dock_state ─────────────────────────────────────────────────────


class TestSetWindowDockState:
    def test_sets_state_to_integer_and_reads_back(self) -> None:
        win = _make_window("Variables", state=4, visible=True)
        col = MagicMock()
        col.Item.return_value = win
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.set_window_dock_state(app, "Variables", "AutoHidden")

        # State was written as integer 4 (AutoHidden)
        assert win.State == 4
        assert result["caption"] == "Variables"
        assert result["dock_state"] == "AutoHidden"
        assert result["is_visible"] is True

    def test_sets_floating_state(self) -> None:
        win = _make_window("Variables", state=5, visible=True)
        col = MagicMock()
        col.Item.return_value = win
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.set_window_dock_state(app, "Variables", "Floating")

        assert win.State == 5
        assert result["dock_state"] == "Floating"

    def test_raises_precondition_error_for_invalid_state(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError, match="Unknown dock state"):
            tool_window_com.set_window_dock_state(app, "Variables", "Invalid")

    def test_raises_precondition_error_when_item_not_found(self) -> None:
        col = MagicMock()
        col.Item.side_effect = Exception("not found")
        app = MagicMock()
        app.MainWindow.Windows = col

        with pytest.raises(BridgePreconditionError, match="does not exist"):
            tool_window_com.set_window_dock_state(app, "NonExistent", "Docked")


# ── check_window_exists ───────────────────────────────────────────────────────


class TestCheckWindowExists:
    def test_returns_true_when_window_exists(self) -> None:
        col = MagicMock()
        col.Contains.return_value = True
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.check_window_exists(app, "BusNavigator")

        col.Contains.assert_called_once_with("BusNavigator")
        assert result is True

    def test_returns_false_when_window_not_found(self) -> None:
        col = MagicMock()
        col.Contains.return_value = False
        app = MagicMock()
        app.MainWindow.Windows = col

        result = tool_window_com.check_window_exists(app, "EESPort Configurations")

        assert result is False

    def test_raises_on_com_error(self) -> None:
        col = MagicMock()
        col.Contains.side_effect = Exception("COM error")
        app = MagicMock()
        app.MainWindow.Windows = col

        with pytest.raises(Exception):
            tool_window_com.check_window_exists(app, "Variables")
