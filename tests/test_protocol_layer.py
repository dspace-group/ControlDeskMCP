"""Tests for Layer 1 input validation — Pydantic model enforcement."""

import pytest
from pydantic import ValidationError


class TestErrorEnvelope:
    """ErrorEnvelope construction and Markdown rendering."""

    def _minimal(self) -> "ErrorEnvelope":  # noqa: F821
        from controldesk_mcp.models.errors import ErrorEnvelope

        return ErrorEnvelope(
            error_code="COM_DISCONNECTED",
            category="CONNECTION",
            message="ControlDesk process is not reachable.",
            retryable=True,
        )

    def test_minimal_envelope_valid(self) -> None:
        env = self._minimal()
        assert env.error_code == "COM_DISCONNECTED"
        assert env.retryable is True

    def test_to_markdown_contains_error_code(self) -> None:
        md = self._minimal().to_markdown()
        assert "COM_DISCONNECTED" in md

    def test_to_markdown_contains_category(self) -> None:
        md = self._minimal().to_markdown()
        assert "CONNECTION" in md

    def test_to_markdown_contains_retryable(self) -> None:
        md = self._minimal().to_markdown()
        assert "Yes" in md  # retryable=True

    def test_to_markdown_hresult_formatted_as_hex(self) -> None:
        from controldesk_mcp.models.errors import ErrorEnvelope

        env = ErrorEnvelope(
            error_code="COM_DISCONNECTED",
            category="CONNECTION",
            message="Disconnected.",
            retryable=True,
            hresult=0x80010108,
        )
        md = env.to_markdown()
        assert "0x80010108" in md

    def test_to_markdown_omits_empty_optional_sections(self) -> None:
        md = self._minimal().to_markdown()
        # detail, hresult, com_interface, recovery_hint, correlation_id all empty
        assert "Detail" not in md
        assert "HRESULT" not in md
        assert "COM:" not in md

    def test_invalid_category_raises(self) -> None:
        from controldesk_mcp.models.errors import ErrorEnvelope

        with pytest.raises(ValidationError):
            ErrorEnvelope(
                error_code="X",
                category="INVALID_CATEGORY",  # type: ignore[arg-type]
                message="msg",
                retryable=False,
            )
