"""Unit tests for sources.models.envelope_builder."""

from __future__ import annotations

import json

from sources.com_bridge.errors import (
    BridgeCircuitOpenError,
    BridgeConnectionError,
    BridgeOperationError,
    BridgePreconditionError,
    BridgeTimeoutError,
    BridgeUiBlockedError,
    BridgeVersionError,
)
from sources.models.envelope_builder import build_envelope, tool_error_result
from sources.models.errors import ErrorEnvelope

# ── build_envelope ────────────────────────────────────────────────────────────


class TestBuildEnvelope:
    def test_returns_error_envelope_instance(self) -> None:
        exc = BridgeConnectionError("disc")
        envelope = build_envelope(exc)
        assert isinstance(envelope, ErrorEnvelope)

    def test_connection_error_maps_to_connection_category(self) -> None:
        envelope = build_envelope(BridgeConnectionError("disc"))
        assert envelope.category == "CONNECTION"

    def test_blocked_by_ui_maps_to_ui_blocking_category(self) -> None:
        envelope = build_envelope(BridgeUiBlockedError("dialog"))
        assert envelope.category == "UI_BLOCKING"

    def test_circuit_open_maps_to_circuit_category(self) -> None:
        envelope = build_envelope(BridgeCircuitOpenError("open"))
        assert envelope.category == "CIRCUIT"

    def test_precondition_maps_to_precondition_category(self) -> None:
        envelope = build_envelope(BridgePreconditionError("no experiment"))
        assert envelope.category == "PRECONDITION"

    def test_timeout_maps_to_timeout_category(self) -> None:
        envelope = build_envelope(BridgeTimeoutError("slow"))
        assert envelope.category == "TIMEOUT"

    def test_version_mismatch_maps_to_version_mismatch_category(self) -> None:
        envelope = build_envelope(BridgeVersionError("mismatch"))
        assert envelope.category == "VERSION_MISMATCH"

    def test_operation_error_maps_to_operation_category(self) -> None:
        envelope = build_envelope(BridgeOperationError("op failed"))
        assert envelope.category == "OPERATION"

    def test_bridge_unknown_error_code_maps_to_unknown_category(self) -> None:
        exc = BridgeOperationError("x", error_code="BRIDGE_UNKNOWN")
        envelope = build_envelope(exc)
        assert envelope.category == "UNKNOWN"

    def test_bridge_access_denied_maps_to_system_category(self) -> None:
        exc = BridgeOperationError("denied", error_code="BRIDGE_ACCESS_DENIED")
        envelope = build_envelope(exc)
        assert envelope.category == "SYSTEM"

    def test_bridge_out_of_memory_maps_to_system_category(self) -> None:
        exc = BridgeOperationError("oom", error_code="BRIDGE_OUT_OF_MEMORY")
        envelope = build_envelope(exc)
        assert envelope.category == "SYSTEM"

    def test_bridge_not_licensed_maps_to_system_category(self) -> None:
        exc = BridgeOperationError("no license", error_code="BRIDGE_NOT_LICENSED")
        envelope = build_envelope(exc)
        assert envelope.category == "SYSTEM"

    def test_error_code_from_exception(self) -> None:
        exc = BridgeConnectionError("x", error_code="COM_DISCONNECTED")
        envelope = build_envelope(exc)
        assert envelope.error_code == "COM_DISCONNECTED"

    def test_message_from_exception(self) -> None:
        exc = BridgeConnectionError("original message")
        envelope = build_envelope(exc)
        assert "original message" in envelope.message

    def test_retryable_from_exception(self) -> None:
        assert build_envelope(BridgeConnectionError("x")).retryable is True
        assert build_envelope(BridgeOperationError("x")).retryable is False

    def test_recovery_hint_from_exception(self) -> None:
        exc = BridgeConnectionError("x", recovery_hint="Call start_controldesk.")
        envelope = build_envelope(exc)
        assert envelope.recovery_hint == "Call start_controldesk."

    def test_hresult_in_detail_when_present(self) -> None:
        exc = BridgeConnectionError("x", hresult=0x80010108)
        envelope = build_envelope(exc)
        assert "80010108" in envelope.detail.upper()

    def test_detail_empty_when_no_hresult(self) -> None:
        exc = BridgePreconditionError("x")
        envelope = build_envelope(exc)
        assert envelope.detail == ""

    def test_correlation_id_passthrough(self) -> None:
        exc = BridgeConnectionError("x")
        envelope = build_envelope(exc, correlation_id="abc-123")
        assert envelope.correlation_id == "abc-123"

    def test_com_interface_and_method_passthrough(self) -> None:
        exc = BridgeConnectionError("x")
        envelope = build_envelope(exc, com_interface="IXaApp", com_method="Connect")
        assert envelope.com_interface == "IXaApp"
        assert envelope.com_method == "Connect"

    def test_defaults_when_no_optional_args(self) -> None:
        exc = BridgeConnectionError("x")
        envelope = build_envelope(exc)
        assert envelope.correlation_id == ""  # exc has no corr_id set either
        assert envelope.com_interface is None
        assert envelope.com_method is None

    def test_correlation_id_read_from_exception_attribute(self) -> None:
        """build_envelope falls back to exc.correlation_id when no explicit kwarg."""
        exc = BridgeConnectionError("x")
        exc.correlation_id = "from-exc-attr-uuid"
        envelope = build_envelope(exc)
        assert envelope.correlation_id == "from-exc-attr-uuid"

    def test_explicit_correlation_id_takes_precedence_over_exception_attr(self) -> None:
        exc = BridgeConnectionError("x")
        exc.correlation_id = "from-exc"
        envelope = build_envelope(exc, correlation_id="explicit")
        assert envelope.correlation_id == "explicit"


# ── tool_error_result ─────────────────────────────────────────────────────────


class TestToolErrorResult:
    def test_returns_valid_json_string(self) -> None:
        exc = BridgeConnectionError("disc")
        result = tool_error_result(exc)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)

    def test_json_contains_error_code(self) -> None:
        exc = BridgeConnectionError("disc", error_code="COM_DISCONNECTED")
        parsed = json.loads(tool_error_result(exc))
        assert parsed["error_code"] == "COM_DISCONNECTED"

    def test_json_contains_markdown_key(self) -> None:
        exc = BridgeConnectionError("disc")
        parsed = json.loads(tool_error_result(exc))
        assert "markdown" in parsed
        assert "## ControlDesk MCP Error" in parsed["markdown"]

    def test_json_contains_retryable(self) -> None:
        parsed = json.loads(tool_error_result(BridgeConnectionError("x")))
        assert parsed["retryable"] is True
        parsed2 = json.loads(tool_error_result(BridgeOperationError("x")))
        assert parsed2["retryable"] is False

    def test_correlation_id_in_json(self) -> None:
        exc = BridgeConnectionError("disc")
        parsed = json.loads(tool_error_result(exc, correlation_id="corr-abc"))
        assert parsed["correlation_id"] == "corr-abc"

    def test_correlation_id_from_exc_attr_appears_in_json(self) -> None:
        """tool_error_result picks up correlation_id from exc.correlation_id (the normal path)."""
        exc = BridgeConnectionError("disc")
        exc.correlation_id = "auto-uuid-from-guard"
        parsed = json.loads(tool_error_result(exc))
        assert parsed["correlation_id"] == "auto-uuid-from-guard"

    def test_com_interface_and_method_in_json(self) -> None:
        exc = BridgeConnectionError("disc")
        parsed = json.loads(tool_error_result(exc, com_interface="IXaApp", com_method="Connect"))
        assert parsed["com_interface"] == "IXaApp"
        assert parsed["com_method"] == "Connect"
