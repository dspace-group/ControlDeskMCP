"""Unit tests for sources.com_bridge.connection."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from sources.com_bridge.connection import ComConnection, ConnectionState
from sources.com_bridge.errors import BridgeConnectionError, BridgeError


class TestComConnection:
    def _make(self, max_retries: int = 3) -> ComConnection:
        return ComConnection(max_retries=max_retries)

    # ── connect ────────────────────────────────────────────────────────────────

    def test_connect_sets_state_connected(self) -> None:
        conn = self._make()
        mock_app = MagicMock()
        with patch.object(conn, "_dispatch", return_value=(mock_app, True)):
            with patch("sources.com_bridge.connection.resolve_prog_id", return_value="CD.App"):
                launched = conn.connect("")  # empty = auto-detect
        assert conn.state is ConnectionState.CONNECTED
        assert conn._prog_id == "CD.App"
        assert conn._app is mock_app
        assert launched is True

    def test_connect_raises_cd_error_on_dispatch_failure(self) -> None:
        conn = self._make()
        with patch.object(conn, "_dispatch", side_effect=BridgeConnectionError("fail")):
            with patch("sources.com_bridge.connection.resolve_prog_id", return_value="CD.App"):
                with pytest.raises(BridgeConnectionError):
                    conn.connect("")

    # ── disconnect ─────────────────────────────────────────────────────────────

    def test_disconnect_sets_state_disconnected(self) -> None:
        conn = self._make()
        conn._state = ConnectionState.CONNECTED
        conn._app = MagicMock()
        conn.disconnect()
        assert conn.state is ConnectionState.DISCONNECTED
        assert conn._app is None

    # ── get_app ────────────────────────────────────────────────────────────────

    def test_get_app_raises_when_disconnected(self) -> None:
        conn = self._make()
        with pytest.raises(BridgeConnectionError):
            conn.get_app()

    def test_get_app_returns_app_when_connected(self) -> None:
        conn = self._make()
        conn._state = ConnectionState.CONNECTED
        conn._app = MagicMock()
        assert conn.get_app() is conn._app

    # ── health ─────────────────────────────────────────────────────────────────

    def test_health_reports_connected_true(self) -> None:
        conn = self._make()
        conn._state = ConnectionState.CONNECTED
        conn._prog_id = "CD.App.2026-A"
        h = conn.health()
        assert h["connected"] is True
        assert h["prog_id"] == "CD.App.2026-A"

    def test_health_reports_connected_false_when_disconnected(self) -> None:
        conn = self._make()
        h = conn.health()
        assert h["connected"] is False

    # ── get_connected_version ──────────────────────────────────────────────────

    def test_get_connected_version_returns_version_token(self) -> None:
        conn = self._make()
        conn._prog_id = "ControlDeskNG.Application.2026-A"
        assert conn.get_connected_version() == "2026-A"

    def test_get_connected_version_uppercase_normalised(self) -> None:
        conn = self._make()
        conn._prog_id = "ControlDeskNG.Application.2025-b"
        assert conn.get_connected_version() == "2025-B"

    def test_get_connected_version_empty_when_no_prog_id(self) -> None:
        conn = self._make()
        # _prog_id is "" by default (never connected)
        assert conn.get_connected_version() == ""

    def test_get_connected_version_empty_for_unversioned_prog_id(self) -> None:
        conn = self._make()
        conn._prog_id = "SomeOther.Application"
        assert conn.get_connected_version() == ""

    # ── reconnect ─────────────────────────────────────────────────────────────

    def test_reconnect_succeeds(self) -> None:
        conn = self._make()
        conn._prog_id = "CD.App"
        conn._state = ConnectionState.CONNECTED
        mock_app = MagicMock()
        with patch.object(conn, "_dispatch", return_value=(mock_app, True)):
            conn.reconnect()
        assert conn.state is ConnectionState.CONNECTED

    def test_reconnect_raises_after_max_retries(self) -> None:
        conn = self._make(max_retries=2)
        conn._prog_id = "CD.App"
        with patch.object(conn, "_dispatch", side_effect=BridgeConnectionError("fail")):
            with pytest.raises(BridgeConnectionError):
                conn.reconnect()
        assert conn.state is ConnectionState.FAILED


# ── domains.application_com ───────────────────────────────────────────────────


class TestApplicationCom:
    def test_get_version_returns_string(self) -> None:
        from sources.com_bridge.domains.application_com import get_version

        app = MagicMock()
        app.Version = "2026-A"
        assert get_version(app) == "2026-A"

    def test_get_version_raises_cd_error_on_failure(self) -> None:
        from sources.com_bridge.domains.application_com import get_version

        app = MagicMock()
        type(app).Version = property(  # type: ignore[assignment]
            fget=lambda self: (_ for _ in ()).throw(Exception("COM error"))
        )
        with pytest.raises(BridgeError):
            get_version(app)

    def test_is_experiment_open_true(self) -> None:
        from sources.com_bridge.domains.application_com import is_experiment_open

        app = MagicMock()
        app.ActiveExperiment = MagicMock()
        assert is_experiment_open(app) is True

    def test_is_experiment_open_false_when_none(self) -> None:
        from sources.com_bridge.domains.application_com import is_experiment_open

        app = MagicMock()
        app.ActiveExperiment = None
        assert is_experiment_open(app) is False

    def test_show_window_sets_visible(self) -> None:
        from sources.com_bridge.domains.application_com import show_window

        app = MagicMock()
        show_window(app)
        assert app.MainWindow.Visible is True

    def test_show_window_retries_on_server_unavailable(self) -> None:
        """Should poll and succeed once the COM server becomes ready."""
        from sources.com_bridge.domains.application_com import show_window

        call_count = 0

        def _fset(self: object, value: bool) -> None:
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # fail twice then succeed
                signed = 0x800706BA - 0x100000000  # RPC_S_SERVER_UNAVAILABLE signed
                raise Exception(signed, "The RPC server is unavailable.", None, None)

        app = MagicMock()
        type(app.MainWindow).Visible = property(fget=lambda self: None, fset=_fset)  # type: ignore[assignment]
        show_window(app, timeout_s=5.0)
        assert call_count == 3

    def test_show_window_raises_timeout_when_always_unavailable(self) -> None:
        from sources.com_bridge.domains.application_com import show_window
        from sources.com_bridge.errors import BridgeTimeoutError

        def _fset(self: object, value: bool) -> None:
            signed = 0x800706BA - 0x100000000
            raise Exception(signed, "The RPC server is unavailable.", None, None)

        app = MagicMock()
        type(app.MainWindow).Visible = property(fget=lambda self: None, fset=_fset)  # type: ignore[assignment]
        with pytest.raises(BridgeTimeoutError):
            show_window(app, timeout_s=0.2)  # very short timeout

    def test_show_window_raises_cd_error_on_non_transient_failure(self) -> None:
        """Errors that are not startup-race HRESULTs must not be retried."""
        from sources.com_bridge.domains.application_com import show_window

        def _fset(self: object, value: bool) -> None:
            raise Exception("some other error")

        app = MagicMock()
        type(app.MainWindow).Visible = property(fget=lambda self: None, fset=_fset)  # type: ignore[assignment]
        err = pytest.raises(BridgeError, show_window, app)
        assert "IXaMainWindow" in str(err.value)
