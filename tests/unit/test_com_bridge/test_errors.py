"""Unit tests for controldesk_mcp.com_bridge.errors."""

from __future__ import annotations

import pytest

from controldesk_mcp.com_bridge.errors import (
    BridgeCircuitOpenError,
    BridgeConnectionError,
    BridgeError,
    BridgeNotInstalledError,
    BridgeOperationError,
    BridgePreconditionError,
    BridgeTimeoutError,
    BridgeUiBlockedError,
    BridgeVersionError,
)


class TestBridgeError:
    def test_defaults(self) -> None:
        err = BridgeError("boom")
        assert str(err) == "boom"
        assert err.error_code == "BRIDGE_ERROR"
        assert err.retryable is False
        assert err.recovery_hint == ""
        assert err.hresult is None
        assert err.correlation_id == ""

    def test_custom_fields(self) -> None:
        err = BridgeError("x", error_code="X", retryable=True, recovery_hint="hint", hresult=0x80)
        assert err.error_code == "X"
        assert err.retryable is True
        assert err.recovery_hint == "hint"
        assert err.hresult == 0x80

    def test_correlation_id_attribute_present_on_all_subclasses(self) -> None:
        for cls in (
            BridgeConnectionError,
            BridgeTimeoutError,
            BridgeNotInstalledError,
            BridgeVersionError,
            BridgeOperationError,
            BridgePreconditionError,
            BridgeCircuitOpenError,
            BridgeUiBlockedError,
        ):
            exc = cls("test")
            assert hasattr(exc, "correlation_id"), f"{cls.__name__} missing correlation_id"
            assert exc.correlation_id == ""  # default is empty

    def test_is_exception(self) -> None:
        with pytest.raises(BridgeError):
            raise BridgeError("raised")


class TestBridgeConnectionError:
    def test_defaults(self) -> None:
        err = BridgeConnectionError("disc")
        assert err.error_code == "COM_DISCONNECTED"
        assert err.retryable is True
        assert "ControlDesk" in err.recovery_hint

    def test_override_retryable(self) -> None:
        err = BridgeConnectionError("disc", retryable=False)
        assert err.retryable is False

    def test_is_bridge_error(self) -> None:
        assert isinstance(BridgeConnectionError("x"), BridgeError)


class TestBridgeTimeoutError:
    def test_defaults(self) -> None:
        err = BridgeTimeoutError("slow")
        assert err.error_code == "COM_TIMEOUT"
        assert err.retryable is True

    def test_is_bridge_error(self) -> None:
        assert isinstance(BridgeTimeoutError("x"), BridgeError)


class TestBridgeNotInstalledError:
    def test_defaults(self) -> None:
        err = BridgeNotInstalledError("missing")
        assert err.error_code == "BRIDGE_NOT_INSTALLED"
        assert err.retryable is False
        assert "CONTROLDESK_VERSION" in err.recovery_hint

    def test_is_bridge_error(self) -> None:
        assert isinstance(BridgeNotInstalledError("x"), BridgeError)


class TestBridgeVersionError:
    def test_defaults(self) -> None:
        err = BridgeVersionError("mismatch")
        assert err.error_code == "COM_VERSION_MISMATCH"
        assert err.retryable is False

    def test_is_bridge_error(self) -> None:
        assert isinstance(BridgeVersionError("x"), BridgeError)


class TestBridgeOperationError:
    def test_defaults(self) -> None:
        err = BridgeOperationError("op failed")
        assert err.error_code == "BRIDGE_OPERATION_ERROR"
        assert err.retryable is False

    def test_hresult_stored(self) -> None:
        err = BridgeOperationError("op", hresult=0x8001010E)
        assert err.hresult == 0x8001010E

    def test_is_bridge_error(self) -> None:
        assert isinstance(BridgeOperationError("x"), BridgeError)


class TestBridgeUiBlockedError:
    def test_defaults(self) -> None:
        err = BridgeUiBlockedError("dialog")
        assert err.error_code == "COM_UI_BLOCKING"
        assert err.retryable is True
        hint = err.recovery_hint
        assert "dialog" in hint.lower() or "DisplayStatusInformation" in hint

    def test_is_bridge_error(self) -> None:
        assert isinstance(BridgeUiBlockedError("x"), BridgeError)

    def test_custom_error_code(self) -> None:
        err = BridgeUiBlockedError("x", error_code="CUSTOM")
        assert err.error_code == "CUSTOM"


class TestBridgePreconditionError:
    def test_defaults(self) -> None:
        err = BridgePreconditionError("no experiment")
        assert err.error_code == "BRIDGE_PRECONDITION"
        assert err.retryable is False
        assert err.hresult is None

    def test_custom_error_code(self) -> None:
        err = BridgePreconditionError("msg", error_code="BRIDGE_NO_EXPERIMENT")
        assert err.error_code == "BRIDGE_NO_EXPERIMENT"

    def test_is_bridge_error(self) -> None:
        assert isinstance(BridgePreconditionError("x"), BridgeError)

    def test_recovery_hint_passthrough(self) -> None:
        err = BridgePreconditionError("x", recovery_hint="Call experiment_load_and_activate.")
        assert err.recovery_hint == "Call experiment_load_and_activate."


class TestBridgeCircuitOpenError:
    def test_defaults(self) -> None:
        err = BridgeCircuitOpenError("circuit open")
        assert err.error_code == "CIRCUIT_OPEN"
        assert err.retryable is True
        assert "30" in err.recovery_hint or "start_controldesk" in err.recovery_hint

    def test_is_bridge_error(self) -> None:
        assert isinstance(BridgeCircuitOpenError("x"), BridgeError)

    def test_custom_cooldown_in_hint(self) -> None:
        err = BridgeCircuitOpenError("x", recovery_hint="Wait 60 s and retry.")
        assert "60" in err.recovery_hint
