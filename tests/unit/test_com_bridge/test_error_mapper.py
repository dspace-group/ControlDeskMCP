"""Unit tests for controldesk_mcp.com_bridge.error_handling.hresult."""

from __future__ import annotations

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import (
    BridgeConnectionError,
    BridgeOperationError,
    BridgeUiBlockedError,
    BridgeVersionError,
)


class _FakeComError(Exception):
    """Minimal stand-in for pywintypes.com_error."""

    def __init__(
        self,
        hresult: int,
        description: str = "error",
        error_info: tuple | None = None,
    ) -> None:
        signed = hresult if hresult < 0x80000000 else hresult - 0x100000000
        # Mimic pywintypes.com_error args layout: (hresult, str, error_info_tuple)
        if error_info is not None:
            super().__init__(signed, description, error_info)
        else:
            super().__init__(signed, description)


# ── Known HRESULT exact lookups ───────────────────────────────────────────────


class TestKnownHresults:
    def test_rpc_e_disconnected_maps_to_connection_error(self) -> None:
        result = map_com_error(_FakeComError(0x80010108))
        assert isinstance(result, BridgeConnectionError)
        assert result.hresult == 0x80010108
        assert result.retryable is True
        assert result.error_code == "COM_DISCONNECTED"

    def test_rpc_e_call_rejected_maps_to_blocked_by_ui(self) -> None:
        result = map_com_error(_FakeComError(0x80010001))
        assert isinstance(result, BridgeUiBlockedError)
        assert result.error_code == "COM_UI_BLOCKING"
        assert result.retryable is True

    def test_rpc_e_wrongthread_not_retryable(self) -> None:
        result = map_com_error(_FakeComError(0x8001010E))
        assert isinstance(result, BridgeOperationError)
        assert result.retryable is False
        assert result.error_code == "COM_WRONG_THREAD"

    def test_co_e_server_stopping_maps_to_connection_error(self) -> None:
        result = map_com_error(_FakeComError(0x80004007))
        assert isinstance(result, BridgeConnectionError)
        assert result.error_code == "COM_SERVER_STOPPING"
        assert result.retryable is True

    def test_disp_e_membernotfound_maps_to_version_mismatch(self) -> None:
        result = map_com_error(_FakeComError(0x80020003))
        assert isinstance(result, BridgeVersionError)
        assert result.error_code == "COM_VERSION_MISMATCH"
        assert result.retryable is False

    def test_disp_e_unknownname_maps_to_version_mismatch(self) -> None:
        result = map_com_error(_FakeComError(0x80020006))
        assert isinstance(result, BridgeVersionError)
        assert result.error_code == "COM_VERSION_MISMATCH"

    def test_disp_e_exception_maps_to_operation_error(self) -> None:
        result = map_com_error(_FakeComError(0x80020009))
        assert isinstance(result, BridgeOperationError)
        assert result.error_code == "BRIDGE_OPERATION_FAILED"
        assert result.retryable is False

    def test_e_fail_maps_to_operation_error(self) -> None:
        result = map_com_error(_FakeComError(0x80004005))
        assert isinstance(result, BridgeOperationError)
        assert result.error_code == "BRIDGE_OPERATION_FAILED"

    def test_e_invalidarg_maps_to_invalid_argument(self) -> None:
        result = map_com_error(_FakeComError(0x80070057))
        assert isinstance(result, BridgeOperationError)
        assert result.error_code == "BRIDGE_INVALID_ARGUMENT"

    def test_e_accessdenied_maps_to_access_denied(self) -> None:
        result = map_com_error(_FakeComError(0x80070005))
        assert isinstance(result, BridgeOperationError)
        assert result.error_code == "BRIDGE_ACCESS_DENIED"
        assert result.retryable is False

    def test_e_outofmemory_is_retryable(self) -> None:
        result = map_com_error(_FakeComError(0x8007000E))
        assert isinstance(result, BridgeOperationError)
        assert result.error_code == "BRIDGE_OUT_OF_MEMORY"
        assert result.retryable is True

    def test_class_e_notlicensed(self) -> None:
        result = map_com_error(_FakeComError(0x80040112))
        assert isinstance(result, BridgeOperationError)
        assert result.error_code == "BRIDGE_NOT_LICENSED"

    def test_server_unavailable_is_retryable(self) -> None:
        result = map_com_error(_FakeComError(0x800706BA))
        assert isinstance(result, BridgeConnectionError)
        assert result.retryable is True


# ── Facility-based fallback ────────────────────────────────────────────────────


class TestFacilityFallback:
    def test_facility_rpc_unknown_hresult_maps_to_connection_error(self) -> None:
        # HRESULT with FACILITY_RPC (facility=1) but unknown exact code
        # FACILITY_RPC: bits [16..26] = 0x0001 → base = 0x80010000
        unknown_rpc = 0x800100FF
        result = map_com_error(_FakeComError(unknown_rpc))
        assert isinstance(result, BridgeConnectionError)
        assert result.retryable is True
        assert result.error_code == "COM_DISCONNECTED"

    def test_facility_dispatch_unknown_hresult_maps_to_version_mismatch(self) -> None:
        # FACILITY_DISPATCH (facility=2): 0x80020000 base
        unknown_dispatch = 0x800200FF
        result = map_com_error(_FakeComError(unknown_dispatch))
        assert isinstance(result, BridgeVersionError)
        assert result.error_code == "COM_VERSION_MISMATCH"


# ── Unknown / generic exceptions ──────────────────────────────────────────────


class TestUnknownExceptions:
    def test_unknown_hresult_maps_to_cd_unknown(self) -> None:
        result = map_com_error(_FakeComError(0xDEADBEEF))
        assert isinstance(result, BridgeOperationError)
        assert result.error_code == "BRIDGE_UNKNOWN"
        assert result.hresult == 0xDEADBEEF

    def test_non_com_exception_maps_to_cd_unknown(self) -> None:
        result = map_com_error(ValueError("plain error"))
        assert isinstance(result, BridgeOperationError)
        assert result.hresult is None
        assert result.error_code == "BRIDGE_UNKNOWN"


# ── IErrorInfo description extraction ─────────────────────────────────────────


class TestIErrorInfoExtraction:
    def test_ierrorinfo_description_used_over_short_message(self) -> None:
        # Simulate DISP_E_EXCEPTION with IErrorInfo description in args[2][2]
        error_info = (None, None, "ControlDesk: Variable not found", None, None)
        exc = _FakeComError(0x80020009, "Exception occurred", error_info=error_info)
        result = map_com_error(exc)
        assert "Variable not found" in str(result)

    def test_falls_back_when_no_error_info(self) -> None:
        exc = _FakeComError(0x80020009, "Exception occurred")
        result = map_com_error(exc)
        # Should not crash; message comes from the args
        assert isinstance(result, BridgeOperationError)


# ── Context parameters ────────────────────────────────────────────────────────


class TestContextParameters:
    def test_interface_and_method_appear_in_message(self) -> None:
        result = map_com_error(
            _FakeComError(0x80010108),
            interface="IXaApplication",
            method="Connect",
        )
        assert "IXaApplication" in str(result)
        assert "Connect" in str(result)

    def test_correlation_id_stored_as_attribute(self) -> None:
        """correlation_id is stored on the exception attribute, not embedded in the message."""
        corr_id = "test-corr-id-123"
        result = map_com_error(
            _FakeComError(0x80010108),
            correlation_id=corr_id,
        )
        assert result.correlation_id == corr_id
        # Must NOT appear in the message string — keep messages clean
        assert corr_id not in str(result)

    def test_no_correlation_id_gives_empty_attribute(self) -> None:
        result = map_com_error(_FakeComError(0x80010108))
        assert result.correlation_id == ""
        assert "[corr=" not in str(result)

    def test_correlation_id_set_on_all_return_paths(self) -> None:
        """All 4 return paths in map_com_error set correlation_id on the result."""
        corr_id = "path-test-uuid"

        # Path 1: exact HRESULT lookup
        r1 = map_com_error(_FakeComError(0x80010108), correlation_id=corr_id)
        assert r1.correlation_id == corr_id

        # Path 2: FACILITY_RPC fallback
        r2 = map_com_error(_FakeComError(0x800100FF), correlation_id=corr_id)
        assert r2.correlation_id == corr_id

        # Path 3: FACILITY_DISPATCH fallback
        r3 = map_com_error(_FakeComError(0x800200FF), correlation_id=corr_id)
        assert r3.correlation_id == corr_id

        # Path 4: unknown / non-COM exception
        r4 = map_com_error(ValueError("plain"), correlation_id=corr_id)
        assert r4.correlation_id == corr_id
