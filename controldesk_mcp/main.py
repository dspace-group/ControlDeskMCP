"""Entry point for the ControlDesk MCP server.

Transport is selected from the ``MCP_TRANSPORT`` environment variable
(default: ``stdio``). See ``controldesk_mcp.config.settings`` for all options.

Inspection flags (no ControlDesk connection required):
    --version         Print the server version and exit.
    --list-tools      Print all registered tool names and exit.
    --list-resources  Print all registered resource URIs (static and templates) and exit.
    --list-prompts    Print all registered prompt names and exit.
"""

from __future__ import annotations

import argparse
import sys

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.server.app import mcp
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="controldesk-mcp",
        description="dSPACE ControlDesk MCP Server",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the server version and exit.",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Print all registered tool names and exit (no ControlDesk connection required).",
    )
    parser.add_argument(
        "--list-resources",
        action="store_true",
        help="Print all registered resource URIs (static and templates) and exit.",
    )
    parser.add_argument(
        "--list-prompts",
        action="store_true",
        help="Print all registered prompt names and exit.",
    )
    return parser.parse_args()


def _run_inspection(args: argparse.Namespace) -> None:
    """Print the requested MCP inventory and exit. No server is started."""
    import controldesk_mcp.server.registry  # noqa: F401 — side-effect: registers all tools

    if args.version:
        try:
            from importlib.metadata import version

            ver = version("controldesk-mcp-server")
        except Exception:
            ver = get_settings().server_version
        print(f"controldesk-mcp {ver}")  # noqa: T201

    if args.list_tools:
        tools = sorted(t.name for t in mcp._tool_manager.list_tools())
        print(f"Tools ({len(tools)}):")  # noqa: T201
        for name in tools:
            print(f"  {name}")  # noqa: T201

    if args.list_resources:
        static = sorted(str(r.uri) for r in mcp._resource_manager.list_resources())
        templates = sorted(t.uri_template for t in mcp._resource_manager.list_templates())
        print(f"Resources ({len(static)} static, {len(templates)} templates):")  # noqa: T201
        for uri in static:
            print(f"  {uri}")  # noqa: T201
        for uri in templates:
            print(f"  {uri}  [template]")  # noqa: T201

    if args.list_prompts:
        prompts = sorted(p.name for p in mcp._prompt_manager.list_prompts())
        print(f"Prompts ({len(prompts)}):")  # noqa: T201
        for name in prompts:
            print(f"  {name}")  # noqa: T201


def main() -> None:
    """Start the MCP server with transport from settings."""
    args = _parse_args()

    if args.version or args.list_tools or args.list_resources or args.list_prompts:
        _run_inspection(args)
        sys.exit(0)

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
        mcp.settings.host = cfg.mcp_host
        mcp.settings.port = cfg.mcp_port
        if cfg.mcp_host not in ("127.0.0.1", "localhost", "::1"):
            mcp.settings.transport_security.enable_dns_rebinding_protection = False
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
