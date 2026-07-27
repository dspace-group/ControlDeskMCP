"""Unit tests for controldesk_mcp.models.base — DictModelMixin and ToolResult."""

import pytest

from controldesk_mcp.models.base import DryRunPreviewResult, ToolResult
from controldesk_mcp.models.errors import ErrorEnvelope


class TestDictModelMixin:
    """DictModelMixin tested via ToolResult (it's a mixin — not instantiated standalone)."""

    def test_getitem_success(self):
        r = ToolResult(status="ok", value=42)
        assert r["status"] == "ok"
        assert r["value"] == 42

    def test_getitem_missing_raises_key_error(self):
        r = ToolResult(status="ok")
        with pytest.raises(KeyError):
            _ = r["missing"]

    def test_contains_present(self):
        r = ToolResult(status="ok")
        assert "status" in r

    def test_contains_absent(self):
        r = ToolResult(status="ok")
        assert "missing" not in r


class TestToolResult:
    def test_empty_instantiation(self):
        r = ToolResult()
        assert r is not None

    def test_arbitrary_fields_extra_allow(self):
        """extra='allow' means any keyword arg is accepted."""
        r = ToolResult(foo="bar", count=3, nested={"a": 1})
        assert r.foo == "bar"
        assert r.count == 3
        assert r.nested == {"a": 1}

    def test_dict_style_access_on_extra_field(self):
        r = ToolResult(magic=True)
        assert r["magic"] is True

    def test_model_schema_generated(self):
        schema = ToolResult.model_json_schema()
        assert schema["type"] == "object"

    def test_is_pydantic_model(self):
        from pydantic import BaseModel

        assert issubclass(ToolResult, BaseModel)


class TestErrorEnvelopeWithMarkdownStrip:
    """Verify the markdown-strip pattern used in all tool wrappers."""

    def test_markdown_key_excluded(self):
        raw = {
            "error_code": "CD_0001",
            "category": "UNKNOWN",
            "message": "Something failed",
            "detail": "details here",
            "markdown": "## Error\nSomething failed",
        }
        env = ErrorEnvelope(**{k: v for k, v in raw.items() if k != "markdown"})
        assert env.error_code == "CD_0001"
        assert env.message == "Something failed"
        assert not hasattr(env, "markdown")

    def test_error_envelope_dict_access(self):
        env = ErrorEnvelope(
            error_code="CD_0002",
            category="CONNECTION",
            message="Test error",
        )
        assert env["error_code"] == "CD_0002"
        assert env["message"] == "Test error"

    def test_error_envelope_contains(self):
        env = ErrorEnvelope(
            error_code="CD_0003",
            category="OPERATION",
            message="msg",
        )
        assert "error_code" in env
        assert "missing" not in env


class TestDryRunPreviewResult:
    def test_defaults_dry_run_true(self):
        preview = DryRunPreviewResult(
            tool="bus_logger_create",
            action="create",
            target="CANRecorder",
            would_execute=True,
            message="No logger named 'CANRecorder' exists — create would succeed.",
        )
        assert preview.dry_run is True
        assert preview.current_state == {}

    def test_dict_style_access(self):
        preview = DryRunPreviewResult(
            tool="calibration_start",
            action="start",
            target="online_calibration",
            would_execute=False,
            current_state={"calibration_state": "Started"},
            message="Online calibration is already running.",
        )
        assert preview["would_execute"] is False
        assert preview["current_state"]["calibration_state"] == "Started"

    def test_is_pydantic_model(self):
        from pydantic import BaseModel

        assert issubclass(DryRunPreviewResult, BaseModel)
