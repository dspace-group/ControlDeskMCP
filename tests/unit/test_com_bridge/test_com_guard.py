"""Unit tests for controldesk_mcp.com_bridge.com_guard."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from controldesk_mcp.com_bridge.error_handling.circuit_breaker import CircuitBreaker
from controldesk_mcp.com_bridge.error_handling.guard import com_guard, guarded_dispatch
from controldesk_mcp.com_bridge.errors import (
    BridgeCircuitOpenError,
    BridgeConnectionError,
    BridgeOperationError,
    BridgeTimeoutError,
)

# ── com_guard (single-call context manager) ───────────────────────────────────


class TestComGuard:
    @pytest.mark.asyncio
    async def test_success_path_does_not_raise(self) -> None:
        corr_id = "test-corr-id"
        async with com_guard("test_op", corr_id=corr_id):
            pass  # no exception → success

    @pytest.mark.asyncio
    async def test_timeout_raises_cd_timeout_error(self) -> None:
        corr_id = "test-corr-id"
        with pytest.raises(BridgeTimeoutError) as exc_info:
            async with com_guard("test_op", corr_id=corr_id, timeout_ms=1):
                await asyncio.sleep(10)  # will be interrupted by timeout
        assert exc_info.value.error_code == "COM_TIMEOUT"
        assert exc_info.value.retryable is True
        assert "test_op" in str(exc_info.value)
        assert exc_info.value.correlation_id == corr_id

    @pytest.mark.asyncio
    async def test_com_error_is_classified(self) -> None:
        class _FakeComError(Exception):
            def __init__(self):
                super().__init__(-2147417848, "disconnected")  # 0x80010108 signed

        corr_id = "test-corr-id"
        with pytest.raises(BridgeConnectionError):
            async with com_guard("test_op", corr_id=corr_id):
                raise _FakeComError()

    @pytest.mark.asyncio
    async def test_already_typed_cd_error_is_re_raised(self) -> None:
        corr_id = "test-corr-id"
        original = BridgeOperationError("already typed")
        with pytest.raises(BridgeOperationError) as exc_info:
            async with com_guard("test_op", corr_id=corr_id):
                raise original
        assert exc_info.value is original
        assert exc_info.value.correlation_id == corr_id


# ── guarded_dispatch ──────────────────────────────────────────────────────────


class TestGuardedDispatch:
    @pytest.mark.asyncio
    async def test_returns_result_on_success(self) -> None:
        with patch("controldesk_mcp.com_bridge.dispatch", new_callable=AsyncMock, return_value=42):
            result = await guarded_dispatch(MagicMock(), operation="test_op")
        assert result == 42

    @pytest.mark.asyncio
    async def test_raises_cd_error_on_failure(self) -> None:
        exc = BridgeOperationError("op failed", error_code="BRIDGE_OPERATION_ERROR")
        with patch("controldesk_mcp.com_bridge.dispatch", new_callable=AsyncMock, side_effect=exc):
            with pytest.raises(BridgeOperationError):
                await guarded_dispatch(MagicMock(), operation="test_op")

    @pytest.mark.asyncio
    async def test_retries_on_retryable_error(self) -> None:
        retryable_exc = BridgeConnectionError("disc")
        call_count = 0

        async def _flaky(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise retryable_exc
            return "ok"

        with (
            patch("controldesk_mcp.com_bridge.dispatch", new_callable=AsyncMock, side_effect=_flaky),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            result = await guarded_dispatch(MagicMock(), operation="test_op", max_attempts=3)
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_does_not_retry_non_retryable_error(self) -> None:
        non_retryable = BridgeOperationError("op failed")
        call_count = 0

        async def _fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise non_retryable

        with patch("controldesk_mcp.com_bridge.dispatch", new_callable=AsyncMock, side_effect=_fail):
            with pytest.raises(BridgeOperationError):
                await guarded_dispatch(MagicMock(), operation="test_op", max_attempts=3)
        assert call_count == 1  # no retry for non-retryable

    @pytest.mark.asyncio
    async def test_raises_after_max_attempts_exhausted(self) -> None:
        retryable_exc = BridgeConnectionError("always fails")
        call_count = 0

        async def _always_fail(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise retryable_exc

        with (
            patch("controldesk_mcp.com_bridge.dispatch", new_callable=AsyncMock, side_effect=_always_fail),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(BridgeConnectionError):
                await guarded_dispatch(MagicMock(), operation="test_op", max_attempts=3)
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks_call_when_open(self) -> None:
        mock_breaker = MagicMock(spec=CircuitBreaker)
        mock_breaker.assert_call_allowed.side_effect = BridgeCircuitOpenError("Circuit OPEN for 'start_controldesk'.")

        with patch(
            "controldesk_mcp.com_bridge.error_handling.guard.get_breaker",
            return_value=mock_breaker,
        ):
            with pytest.raises(BridgeCircuitOpenError):
                await guarded_dispatch(
                    MagicMock(),
                    operation="start_controldesk",
                )

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_success(self) -> None:
        mock_breaker = MagicMock(spec=CircuitBreaker)
        mock_breaker.assert_call_allowed.return_value = None

        with (
            patch("controldesk_mcp.com_bridge.error_handling.guard.get_breaker", return_value=mock_breaker),
            patch("controldesk_mcp.com_bridge.dispatch", new_callable=AsyncMock, return_value="ok"),
        ):
            await guarded_dispatch(MagicMock(), operation="start_controldesk")

        mock_breaker.record_success.assert_called_once()

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failure(self) -> None:
        mock_breaker = MagicMock(spec=CircuitBreaker)
        mock_breaker.assert_call_allowed.return_value = None
        exc = BridgeOperationError("fail")

        with (
            patch("controldesk_mcp.com_bridge.error_handling.guard.get_breaker", return_value=mock_breaker),
            patch("controldesk_mcp.com_bridge.dispatch", new_callable=AsyncMock, side_effect=exc),
        ):
            with pytest.raises(BridgeOperationError):
                await guarded_dispatch(MagicMock(), operation="start_controldesk")

        mock_breaker.record_failure.assert_called()
