"""Unit tests for sources.com_bridge (public __init__ API)."""

from __future__ import annotations

import concurrent.futures
from unittest.mock import MagicMock, patch

import pytest

import sources.com_bridge as bridge
from sources.com_bridge import dispatch, ensure_connected, get_connection, shutdown, startup
from sources.com_bridge.connection import ConnectionState
from sources.com_bridge.errors import BridgeTimeoutError


@pytest.fixture(autouse=True)
def _reset_bridge():
    """Reset the module-level singletons before and after each test."""
    bridge._connection = None
    import sources.com_bridge.sta_thread as _sta

    _sta._sta_thread = None
    yield
    bridge._connection = None
    _sta._sta_thread = None


class TestGetConnection:
    def test_raises_when_not_started(self) -> None:
        with pytest.raises(RuntimeError, match="startup"):
            get_connection()

    def test_returns_connection_after_startup(self) -> None:
        bridge._connection = MagicMock()
        assert get_connection() is bridge._connection


class TestStartupShutdown:
    @pytest.mark.asyncio
    async def test_startup_only_starts_sta_thread(self) -> None:
        """startup must NOT call connect — keeps lifespan fast."""
        with patch("sources.com_bridge.sta_thread.startup") as mock_sta_start:
            await startup()
        mock_sta_start.assert_called_once()
        # Connection object created but in DISCONNECTED state — no COM call yet.
        assert bridge._connection is not None
        assert bridge._connection.state is ConnectionState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_ensure_connected_connects_when_disconnected(self) -> None:
        """After startup the connection is DISCONNECTED; ensure_connected must connect."""
        future: concurrent.futures.Future[bool] = concurrent.futures.Future()
        future.set_result(True)

        with (
            patch("sources.com_bridge.sta_thread.startup"),
            patch("sources.com_bridge.sta_thread.get_sta_thread") as mock_get_sta,
        ):
            mock_sta_thread = MagicMock()
            mock_sta_thread.submit.return_value = future
            mock_get_sta.return_value = mock_sta_thread

            await startup()
            newly = await ensure_connected()

        assert newly is True

    @pytest.mark.asyncio
    async def test_ensure_connected_returns_false_when_already_connected(self) -> None:
        conn = MagicMock()
        conn.state = ConnectionState.CONNECTED
        bridge._connection = conn
        newly = await ensure_connected()
        assert newly is False

    @pytest.mark.asyncio
    async def test_shutdown_clears_connection(self) -> None:
        bridge._connection = MagicMock()
        future: concurrent.futures.Future[None] = concurrent.futures.Future()
        future.set_result(None)

        with patch("sources.com_bridge.sta_thread.get_sta_thread") as mock_get_sta:
            mock_sta_thread = MagicMock()
            mock_sta_thread.submit.return_value = future
            mock_get_sta.return_value = mock_sta_thread
            with patch("sources.com_bridge.sta_thread.shutdown"):
                await shutdown()

        assert bridge._connection is None

    @pytest.mark.asyncio
    async def test_shutdown_is_safe_when_not_started(self) -> None:
        with patch("sources.com_bridge.sta_thread.shutdown"):
            await shutdown()  # must not raise


class TestDispatch:
    @pytest.mark.asyncio
    async def test_dispatch_returns_function_result(self) -> None:
        fn = lambda x: x * 2  # noqa: E731
        future: concurrent.futures.Future[int] = concurrent.futures.Future()
        future.set_result(84)

        with patch("sources.com_bridge.sta_thread.get_sta_thread") as mock_get_sta:
            mock_sta = MagicMock()
            mock_sta.submit.return_value = future
            mock_get_sta.return_value = mock_sta
            result = await dispatch(fn, 42)

        assert result == 84

    @pytest.mark.asyncio
    async def test_dispatch_raises_timeout(self) -> None:
        future: concurrent.futures.Future[None] = concurrent.futures.Future()
        # Never set a result → will time out

        with patch("sources.com_bridge.sta_thread.get_sta_thread") as mock_get_sta:
            mock_sta = MagicMock()
            mock_sta.submit.return_value = future
            mock_get_sta.return_value = mock_sta

            with pytest.raises(BridgeTimeoutError):
                await dispatch(lambda: None, timeout_ms=1)


class TestDomainsImport:
    def test_application_com_accessible_via_domains(self) -> None:
        """domains.application_com must be importable — catches the missing __init__ import."""
        from sources.com_bridge import domains

        assert hasattr(
            domains, "application_com"
        ), "domains.application_com is not exported from com_bridge/domains/__init__.py"

    def test_application_com_has_expected_callables(self) -> None:
        from sources.com_bridge.domains import application_com

        for name in ("get_version", "show_window", "quit_application", "set_window_state"):
            assert callable(
                getattr(application_com, name, None)
            ), f"application_com.{name} is missing or not callable"
