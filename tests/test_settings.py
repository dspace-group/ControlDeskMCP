"""Tests for the settings module (Layer 1 — Transport & Protocol)."""

import os

import pytest
from pydantic import ValidationError


class TestSettingsDefaults:
    """Verify default values when no environment variables are set."""

    def setup_method(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        get_settings.cache_clear()

    def test_default_transport_is_stdio(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        assert get_settings().mcp_transport == "stdio"

    def test_default_log_level_is_info(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        assert get_settings().log_level == "INFO"

    def test_default_com_timeout_is_120000(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        assert get_settings().com_timeout_ms == 120_000

    def test_default_launch_timeout_is_30000(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        assert get_settings().com_launch_timeout_ms == 30_000

    def test_default_controldesk_version_is_empty(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        assert get_settings().controldesk_version == ""

    def test_default_port_is_8000(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        assert get_settings().mcp_port == 8000


class TestSettingsFromEnvironment:
    """Verify environment variable overrides."""

    def setup_method(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        get_settings.cache_clear()

    def teardown_method(self) -> None:
        from controldesk_mcp.config.settings import get_settings

        get_settings.cache_clear()
        for key in ("MCP_TRANSPORT", "LOG_LEVEL", "COM_TIMEOUT_MS", "MCP_PORT"):
            os.environ.pop(key, None)

    def test_transport_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from controldesk_mcp.config.settings import Settings

        s = Settings(mcp_transport="streamable-http")
        assert s.mcp_transport == "streamable-http"

    def test_log_level_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from controldesk_mcp.config.settings import Settings

        s = Settings(log_level="DEBUG")
        assert s.log_level == "DEBUG"

    def test_invalid_transport_raises(self) -> None:
        from controldesk_mcp.config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(mcp_transport="invalid-transport")  # type: ignore[arg-type]

    def test_invalid_log_level_raises(self) -> None:
        from controldesk_mcp.config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(log_level="VERBOSE")  # type: ignore[arg-type]

    def test_port_below_range_raises(self) -> None:
        from controldesk_mcp.config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(mcp_port=0)

    def test_port_above_range_raises(self) -> None:
        from controldesk_mcp.config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(mcp_port=99999)

    def test_empty_version_is_valid(self) -> None:
        """Empty version is valid; auto-detects at connection time."""
        from controldesk_mcp.config.settings import Settings

        s = Settings(controldesk_version="")
        assert s.controldesk_version == ""

    def test_valid_version_format_accepted(self) -> None:
        from controldesk_mcp.config.settings import Settings

        s = Settings(controldesk_version="2026-A")
        assert s.controldesk_version == "2026-A"

    def test_invalid_version_format_raises(self) -> None:
        from pydantic import ValidationError

        from controldesk_mcp.config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(controldesk_version="ControlDeskNG.Application.2026-A")

    def test_com_timeout_below_minimum_raises(self) -> None:
        from controldesk_mcp.config.settings import Settings

        with pytest.raises(ValidationError):
            Settings(com_timeout_ms=100)
