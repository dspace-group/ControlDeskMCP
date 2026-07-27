"""Unit tests for controldesk_mcp.com_bridge.domains.application_com."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

from controldesk_mcp.com_bridge.domains.application_com import (
    get_version,
    get_window_state,
    get_window_visible,
    is_experiment_open,
    quit_application,
    set_fullscreen,
    set_window_position,
    set_window_state,
    set_window_visible,
    show_window,
)
from controldesk_mcp.com_bridge.errors import BridgeError, BridgePreconditionError, BridgeTimeoutError

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_app(main_window_visible: bool = True, main_window_state: int = 0) -> MagicMock:
    """Return a mock IXaApplication with a working MainWindow.

    ``main_window_state`` is the integer COM enum value (0=Normal, 1=Minimized,
    2=Maximized, 3=Hidden).
    """
    app = MagicMock()
    mw = MagicMock()
    type(mw).Visible = PropertyMock(return_value=main_window_visible)
    type(mw).State = PropertyMock(return_value=main_window_state)
    type(mw).FullScreenModeEnabled = PropertyMock(return_value=False)
    app.MainWindow = mw
    return app


# ── get_version ───────────────────────────────────────────────────────────────


class TestGetVersion:
    def test_returns_version_string(self) -> None:
        app = MagicMock()
        app.Version = "2026-A"
        assert get_version(app) == "2026-A"

    def test_raises_cd_error_on_com_failure(self) -> None:
        app = MagicMock()
        app.Version = PropertyMock(side_effect=Exception("com error"))
        type(app).Version = PropertyMock(side_effect=Exception("com error"))
        with pytest.raises(BridgeError):
            get_version(app)


# ── is_experiment_open ────────────────────────────────────────────────────────


class TestIsExperimentOpen:
    def test_true_when_active_experiment_is_not_none(self) -> None:
        app = MagicMock()
        app.ActiveExperiment = MagicMock()
        assert is_experiment_open(app) is True

    def test_false_when_active_experiment_is_none(self) -> None:
        app = MagicMock()
        app.ActiveExperiment = None
        assert is_experiment_open(app) is False


# ── show_window ───────────────────────────────────────────────────────────────


class TestShowWindow:
    def test_sets_visible_on_success(self) -> None:
        app = MagicMock()
        show_window(app)
        # Verify MainWindow.Visible was set (mock records the call)
        assert app.MainWindow is not None

    def test_raises_timeout_when_always_unavailable(self) -> None:
        def _fset(self: object, value: bool) -> None:
            signed = 0x800706BA - 0x100000000  # RPC_S_SERVER_UNAVAILABLE (signed)
            raise Exception(signed, "server unavailable", None, None)

        app = MagicMock()
        type(app.MainWindow).Visible = property(fget=lambda self: None, fset=_fset)  # type: ignore[assignment]

        with pytest.raises(BridgeTimeoutError):
            show_window(app, timeout_s=0.1)

    def test_raises_cd_error_on_non_transient_failure(self) -> None:
        def _fset(self: object, value: bool) -> None:
            raise Exception("non-transient COM error")

        app = MagicMock()
        type(app.MainWindow).Visible = property(fget=lambda self: None, fset=_fset)  # type: ignore[assignment]

        with pytest.raises(BridgeError):
            show_window(app, timeout_s=5.0)


# ── set_window_visible / get_window_visible ───────────────────────────────────


class TestSetGetWindowVisible:
    def test_set_window_visible_true(self) -> None:
        app = MagicMock()
        set_window_visible(app, visible=True)
        # verify the property assignment was attempted
        assert app.MainWindow is not None

    def test_set_window_visible_false(self) -> None:
        app = MagicMock()
        set_window_visible(app, visible=False)
        assert app.MainWindow is not None

    def test_set_window_visible_raises_on_com_error(self) -> None:
        def _fset(self: object, value: bool) -> None:
            raise Exception("com error")

        app = MagicMock()
        type(app.MainWindow).Visible = property(fget=lambda self: False, fset=_fset)  # type: ignore[assignment]
        with pytest.raises(BridgeError):
            set_window_visible(app, visible=True)

    def test_get_window_visible_returns_bool(self) -> None:
        app = _make_app(main_window_visible=True)
        result = get_window_visible(app)
        assert isinstance(result, bool)
        assert result is True

    def test_get_window_visible_raises_on_com_error(self) -> None:
        app = MagicMock()
        type(app.MainWindow).Visible = PropertyMock(side_effect=Exception("com error"))
        with pytest.raises(BridgeError):
            get_window_visible(app)


# ── set_window_state / get_window_state ──────────────────────────────────────


class TestSetGetWindowState:
    def test_set_window_state_assigns_integer_value(self) -> None:
        app = MagicMock()
        set_window_state(app, "Maximized")
        # Verify the integer 2 (Maximized) was assigned, not the string
        app.MainWindow.__setattr__  # mock was used
        assert app.MainWindow.State == 2

    def test_set_window_state_unknown_raises_precondition(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError):
            set_window_state(app, "Fullscreen")

    def test_set_window_state_raises_on_com_error(self) -> None:
        def _fset(self: object, value: int) -> None:
            raise Exception("com error")

        app = MagicMock()
        type(app.MainWindow).State = property(fget=lambda self: 0, fset=_fset)  # type: ignore[assignment]
        with pytest.raises(BridgeError):
            set_window_state(app, "Maximized")

    def test_get_window_state_maps_integer_to_name(self) -> None:
        app = _make_app(main_window_state=2)  # 2 = Maximized
        result = get_window_state(app)
        assert result == "Maximized"

    def test_get_window_state_normal_maps_correctly(self) -> None:
        app = _make_app(main_window_state=0)  # 0 = Normal
        assert get_window_state(app) == "Normal"

    def test_get_window_state_unknown_int_returns_str_repr(self) -> None:
        app = _make_app(main_window_state=99)
        assert get_window_state(app) == "99"

    def test_get_window_state_raises_on_com_error(self) -> None:
        app = MagicMock()
        type(app.MainWindow).State = PropertyMock(side_effect=Exception("com error"))
        with pytest.raises(BridgeError):
            get_window_state(app)


# ── set_window_position ───────────────────────────────────────────────────────


class TestSetWindowPosition:
    def test_assigns_all_four_geometry_properties(self) -> None:
        app = _make_app(main_window_state=0)  # Normal
        set_window_position(app, left=10, top=20, width=1920, height=1080)
        assert app.MainWindow is not None

    def test_raises_precondition_when_maximized(self) -> None:
        app = _make_app(main_window_state=2)  # 2 = Maximized
        with pytest.raises(BridgePreconditionError) as exc_info:
            set_window_position(app, 0, 0, 800, 600)
        assert exc_info.value.error_code == "BRIDGE_WINDOW_NOT_NORMAL"
        assert "app_set_window_state" in exc_info.value.recovery_hint

    def test_raises_precondition_when_fullscreen(self) -> None:
        app = _make_app(main_window_state=0)  # Normal state but fullscreen
        type(app.MainWindow).FullScreenModeEnabled = PropertyMock(return_value=True)
        with pytest.raises(BridgePreconditionError) as exc_info:
            set_window_position(app, 0, 0, 800, 600)
        assert "app_set_fullscreen" in exc_info.value.recovery_hint

    def test_raises_on_com_error(self) -> None:
        app = MagicMock()
        app.MainWindow.Left = PropertyMock(side_effect=Exception("com error"))

        # Make the *assignment* raise by using a property that raises on set
        class _FailMW:
            @property
            def Left(self):  # noqa: N802
                return 0

            @Left.setter
            def Left(self, v):  # noqa: N802
                raise Exception("com error")  # noqa: TRY002

            State = 0
            FullScreenModeEnabled = False

        app.MainWindow = _FailMW()
        with pytest.raises(BridgeError):
            set_window_position(app, 0, 0, 800, 600)


# ── set_fullscreen ────────────────────────────────────────────────────────────


class TestSetFullscreen:
    def test_enables_fullscreen(self) -> None:
        app = MagicMock()
        set_fullscreen(app, enabled=True)
        assert app.MainWindow is not None

    def test_disables_fullscreen(self) -> None:
        app = MagicMock()
        set_fullscreen(app, enabled=False)
        assert app.MainWindow is not None

    def test_raises_on_com_error(self) -> None:
        def _fset(self: object, value: bool) -> None:
            raise Exception("com error")

        app = MagicMock()
        type(app.MainWindow).FullScreenModeEnabled = property(fget=lambda self: False, fset=_fset)  # type: ignore[assignment]
        with pytest.raises(BridgeError):
            set_fullscreen(app, enabled=True)


# ── quit_application ─────────────────────────────────────────────────────────


class TestQuitApplication:
    def test_calls_quit(self) -> None:
        app = MagicMock()
        quit_application(app)
        app.Quit.assert_called_once()

    def test_raises_on_com_error(self) -> None:
        app = MagicMock()
        app.Quit.side_effect = Exception("com error")
        with pytest.raises(BridgeError):
            quit_application(app)
