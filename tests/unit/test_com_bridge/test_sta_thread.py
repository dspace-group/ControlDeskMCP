"""Unit tests for sources.com_bridge.sta_thread."""

from __future__ import annotations

import concurrent.futures
from unittest.mock import MagicMock, patch

import pytest

from sources.com_bridge import sta_thread as _module
from sources.com_bridge.sta_thread import STAThread, get_sta_thread, shutdown, startup

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_sta(mock_pythoncom: MagicMock | None = None) -> STAThread:
    """Return a STAThread with pythoncom stubbed out."""
    sta = STAThread()
    _patch_pythoncom(sta, mock_pythoncom or MagicMock())
    return sta


def _patch_pythoncom(sta: STAThread, mock_pc: MagicMock) -> None:
    sta._co_initialize = lambda: mock_pc  # type: ignore[method-assign]
    sta._co_uninitialize = lambda _: None  # type: ignore[method-assign]
    sta._pump = lambda _: None  # type: ignore[method-assign]


# ── STAThread ──────────────────────────────────────────────────────────────────


class TestSTAThread:
    def test_submit_executes_function_on_thread(self) -> None:
        sta = _make_sta()
        sta.start()
        try:
            future = sta.submit(lambda: 42)
            assert future.result(timeout=2) == 42
        finally:
            sta.stop()

    def test_submit_propagates_exception(self) -> None:
        sta = _make_sta()
        sta.start()
        try:
            future = sta.submit(lambda: (_ for _ in ()).throw(ValueError("boom")))
            with pytest.raises(ValueError, match="boom"):
                future.result(timeout=2)
        finally:
            sta.stop()

    def test_multiple_submits_execute_in_order(self) -> None:
        results: list[int] = []
        sta = _make_sta()
        sta.start()
        try:
            futures = [sta.submit(results.append, i) for i in range(5)]
            for f in futures:
                f.result(timeout=2)
        finally:
            sta.stop()
        assert results == [0, 1, 2, 3, 4]

    def test_stop_is_idempotent_after_thread_exits(self) -> None:
        sta = _make_sta()
        sta.start()
        sta.stop()
        sta.stop()  # second call must not raise

    def test_submit_returns_future(self) -> None:
        sta = _make_sta()
        sta.start()
        try:
            f = sta.submit(lambda: None)
            assert isinstance(f, concurrent.futures.Future)
            f.result(timeout=2)
        finally:
            sta.stop()


# ── Module-level singleton (startup / shutdown / get_sta_thread) ───────────────


class TestModuleSingleton:
    def setup_method(self) -> None:
        _module._sta_thread = None

    def teardown_method(self) -> None:
        _module._sta_thread = None

    def test_get_sta_thread_raises_before_startup(self) -> None:
        with pytest.raises(RuntimeError, match="startup"):
            get_sta_thread()

    def test_startup_creates_singleton(self) -> None:
        with patch.object(STAThread, "start"):
            startup()
        assert _module._sta_thread is not None

    def test_startup_is_idempotent(self) -> None:
        with patch.object(STAThread, "start"):
            startup()
            first = _module._sta_thread
            startup()
            assert _module._sta_thread is first

    def test_shutdown_clears_singleton(self) -> None:
        with patch.object(STAThread, "start"), patch.object(STAThread, "stop"):
            startup()
            shutdown()
        assert _module._sta_thread is None

    def test_shutdown_is_idempotent_when_not_started(self) -> None:
        shutdown()  # must not raise

    def test_get_sta_thread_returns_instance_after_startup(self) -> None:
        with patch.object(STAThread, "start"):
            startup()
        assert get_sta_thread() is _module._sta_thread


# ── Resilience: cancelled futures must not crash the STA thread ────────────────


class TestSTAThreadResilienceOnCancelledFuture:
    """Verify the STA thread survives when a future is cancelled before the
    COM call completes (the asyncio timeout scenario)."""

    def test_cancelled_future_does_not_kill_thread(self) -> None:
        """Cancel a future externally; the STA thread must still process the next task."""
        sta = _make_sta()
        sta.start()
        try:
            # Submit a task and immediately cancel its future.
            future = sta.submit(lambda: 99)
            future.cancel()  # may or may not beat the thread to set_result

            # The thread must still be alive and able to execute another task.
            next_future = sta.submit(lambda: "alive")
            assert next_future.result(timeout=2) == "alive"
            assert sta._thread.is_alive()
        finally:
            sta.stop()

    def test_cancelled_future_with_raising_fn_does_not_kill_thread(self) -> None:
        """Cancel a future, then the COM function raises — thread must survive."""
        import threading
        import time

        # Block until the cancel has been issued, then raise.
        cancel_event = threading.Event()

        def slow_raising_fn() -> None:
            cancel_event.wait(timeout=2)
            raise RuntimeError("COM exploded")

        sta = _make_sta()
        sta.start()
        try:
            future = sta.submit(slow_raising_fn)
            future.cancel()
            cancel_event.set()  # unblock the fn so it raises on the STA thread

            time.sleep(0.2)  # give the STA thread time to process the exception

            # Thread must be alive and process further work.
            next_future = sta.submit(lambda: "still alive")
            assert next_future.result(timeout=2) == "still alive"
            assert sta._thread.is_alive()
        finally:
            sta.stop()
