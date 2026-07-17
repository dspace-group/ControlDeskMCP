"""Entry point for the ControlDesk MCP server.

Transport is selected from the ``MCP_TRANSPORT`` environment variable
(default: ``stdio``).  See ``sources/config/settings.py`` for all options.
"""

from __future__ import annotations

from sources.config.settings import get_settings
from sources.server.app import mcp
from sources.utils.logger import get_logger

_log = get_logger(__name__)


def main() -> None:
    """Start the MCP server with transport from settings."""
    cfg = get_settings()
    _log.debug("Starting with transport=%s", cfg.mcp_transport)

    if cfg.mcp_transport == "streamable-http":
        if cfg.mcp_host != "127.0.0.1":
            _log.warning(
                "[SECURITY] MCP transport is streamable-http on non-localhost host '%s'. "
                "No authentication is configured. Restrict access via firewall or add "
                "API key middleware.",
                cfg.mcp_host,
            )
        # FastMCP 1.27.x reads host/port from mcp.settings — run() does not accept kwargs.
        mcp.settings.host = cfg.mcp_host
        mcp.settings.port = cfg.mcp_port
        if cfg.mcp_host not in ("127.0.0.1", "localhost", "::1"):
            # Disable DNS-rebinding protection so requests with the machine's IP
            # in the Host header are accepted by remote clients.
            mcp.settings.transport_security.enable_dns_rebinding_protection = False
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
