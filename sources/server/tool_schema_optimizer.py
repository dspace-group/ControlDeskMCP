"""Suppress outputSchema from the MCP wire format for all registered tools.

outputSchema accounts for 66 % of the server's total token budget (118,547 / 179,455
tokens at baseline). LLMs do not need it to call tools — they rely solely on
inputSchema and descriptions. Stripping it drops context-window usage from 89.7 %
to ~30 % of Claude's 200k window.

Mechanism: Tool.output_schema is a cached_property on the FastMCP Tool class (not a
Pydantic model field). Writing to tool.__dict__["output_schema"] injects the cached
value before the property descriptor runs, suppressing schema generation without
modifying the FastMCP framework.
"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)


def strip_output_schemas(mcp_instance: FastMCP) -> int:
    """Set output_schema to None for every registered tool.

    Must be called after all @mcp.tool decorators have executed (i.e. after all
    tool modules are imported in registry.py).

    Returns the number of tools processed.
    """
    tools: dict = mcp_instance._tool_manager._tools
    for tool in tools.values():
        tool.__dict__["output_schema"] = None
    count = len(tools)
    logger.debug("Stripped outputSchema from %d tools", count)
    return count
