"""Server configuration — read from environment variables or .env file."""

from __future__ import annotations

import os
import re
import warnings
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field, field_validator

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover - import-time guard
    warnings.warn(
        "pydantic-settings is not installed; falling back to environment-only settings. Install with: uv sync",
        RuntimeWarning,
        stacklevel=2,
    )

    SettingsConfigDict = dict

    class BaseSettings(BaseModel):
        """Minimal fallback for pydantic-settings BaseSettings.

        Reads values from environment variables using upper-case field names.
        Example: field "com_timeout_ms" maps to env var "COM_TIMEOUT_MS".
        """

        def __init__(self, **data):
            merged = {}
            for field_name in self.__class__.model_fields:
                env_name = field_name.upper()
                if env_name in os.environ and field_name not in data:
                    merged[field_name] = os.environ[env_name]
            merged.update(data)
            super().__init__(**merged)


class Settings(BaseSettings):
    """Typed, env-var-backed configuration. .env loaded automatically if present."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # unknown env vars do not raise an error
    )

    # ── Transport ─────────────────────────────────────────────────────────────

    mcp_transport: Literal["stdio", "streamable-http"] = Field(
        default="stdio",
        description="MCP transport to use: 'stdio' for local/VS Code, 'streamable-http' for remote/network access.",
    )
    mcp_host: str = Field(
        default="127.0.0.1",
        description="Bind host for the HTTP transport. Ignored for stdio.",
    )
    mcp_port: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="TCP port for the HTTP transport. Ignored for stdio.",
    )

    # ── Logging ───────────────────────────────────────────────────────────────

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Python logging level for all server-side (stderr) output.",
    )
    mcp_debug: bool = Field(
        default=False,
        description="When True, enables verbose protocol tracing. Equivalent to log_level=DEBUG for MCP internals.",
    )

    # ── COM bridge ────────────────────────────────────────────────────────────
    # NOTE: ProgID is *internal* — never expose it here.
    # Users configure the human-readable version like "2026-A"; the bridge
    # resolves the full ProgID from the Windows Registry automatically.

    controldesk_version: str = Field(
        default="",
        description=(
            "ControlDesk version to connect to, e.g. '2026-A' or '2025-B'. "
            "Empty means auto-detect the latest installed version. "
            "Set CONTROLDESK_VERSION env var or .env file."
        ),
    )
    com_timeout_ms: int = Field(
        default=120_000,
        ge=500,
        le=120_000,
        description="Wall-clock timeout (ms) for any single COM method call. "
        "Calls that exceed this budget raise BridgeTimeoutError.",
    )
    com_launch_timeout_ms: int = Field(
        default=30_000,
        ge=5_000,
        le=120_000,
        description="Max ms to wait for ControlDesk to finish initializing after launch. "
        "ControlDesk may take 10-30s to fully start before its COM objects are ready.",
    )
    com_hardware_timeout_ms: int = Field(
        default=30_000,
        ge=5_000,
        le=120_000,
        description="Wall-clock timeout (ms) for hardware registration COM calls "
        "(register_hardware_platform). These operations probe network/USB hardware "
        "and typically take much longer than regular COM calls.",
    )
    com_reconnect_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of reconnection attempts after RPC_E_DISCONNECTED before the circuit opens.",
    )

    # ── Server identity ───────────────────────────────────────────────────────

    server_version: str = Field(
        default="0.1.0",
        description="Semantic version reported in the MCP initialize response.",
    )

    # ── Tool TTL / lazy eviction ──────────────────────────────────────────────

    tool_ttl_enabled: bool = Field(
        default=True,
        description=(
            "Enable lazy TTL eviction of inactive ADD_ON tool domains. "
            "When True, domains idle longer than tool_ttl_seconds are removed from the "
            "tool list on the next SEARCH (discover) call, freeing LLM context. "
            "Stateful domains (bus_logging, bus_monitor, bus_replay, measurement, recorder) "
            "are never auto-evicted regardless of this setting."
        ),
    )
    tool_ttl_seconds: float = Field(
        default=120.0,
        ge=30.0,
        description=(
            "Inactivity threshold in seconds before an ADD_ON domain is evicted. "
            "A domain is considered active as long as any of its tools was called within "
            "this window. Default: 120 (2 minutes)."
        ),
    )

    # ── Variable resolution hardening ────────────────────────────────────────

    variable_resolution_cache_ttl_seconds: float = Field(
        default=300.0,
        ge=0.0,
        description=("TTL for variable path resolver in-memory cache entries. Set to 0 to disable resolver caching."),
    )
    variable_resolution_debug_telemetry: bool = Field(
        default=False,
        description=("When True, include verbose resolver telemetry fields in responses and attempt diagnostics."),
    )

    # ── Validators ────────────────────────────────────────────────────────────

    @field_validator("mcp_host")
    @classmethod
    def _host_not_empty(cls, value: str) -> str:
        if not value.strip():
            msg = "mcp_host must not be empty"
            raise ValueError(msg)
        return value

    @field_validator("controldesk_version")
    @classmethod
    def _version_format(cls, value: str) -> str:
        """Accept '' (auto-detect) or 'YYYY-L' pattern, e.g. '2026-A'."""
        if value and not re.fullmatch(r"\d{4}-[A-Za-z]", value):
            msg = (
                f"controldesk_version '{value}' is invalid. "
                "Use 'YYYY-L' format, e.g. '2026-A', or leave empty to auto-detect."
            )
            raise ValueError(msg)
        return value.upper() if value else value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings instance.

    In tests, call get_settings.cache_clear() after changing env vars.
    """
    return Settings()
