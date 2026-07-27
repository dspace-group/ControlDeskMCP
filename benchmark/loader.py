"""MCP server introspection — loads tool schemas without starting the server.

The loader imports the ControlDesk FastMCP instance and the registry module
(which triggers every @mcp.tool decorator), then calls list_tools() to get
the full tool catalogue in-process.

No COM connection is made — the STA thread and ControlDesk client are only
started inside the server lifespan, which does NOT run here.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any


async def load_tools() -> tuple[str, list[Any]]:
    """Return (server_name, tools) by introspecting the ControlDesk FastMCP instance.

    Safe to call even when ControlDesk is not running: the tool *functions*
    are registered (decorators executed) but never *called*.
    """
    _ensure_project_on_path()

    from controldesk_mcp.server.app import mcp  # noqa: PLC0415
    import controldesk_mcp.server.registry  # noqa: F401, PLC0415 — registers all @mcp.tool

    tools = await mcp.list_tools()
    return mcp.name, tools


def load_tools_sync() -> tuple[str, list[Any]]:
    """Synchronous wrapper around :func:`load_tools`."""
    return asyncio.run(load_tools())


def _ensure_project_on_path() -> None:
    """Add the repository root to sys.path so 'controldesk_mcp' can be imported."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
