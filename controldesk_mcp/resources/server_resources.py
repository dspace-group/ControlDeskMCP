"""MCP resources exposing server metadata for the MCP Inspector and LLM context.

Resources registered (all read-only; none require a live ControlDesk connection):
  controldesk://server/info              — version, transport, and COM settings
  controldesk://server/tool-catalog      — full list of registered tools with descriptions
  controldesk://server/connection-status — live COM bridge state (reads in-memory state only)

Layer: MCP Resource adapter — owns @mcp.resource annotations only.
All config access goes through controldesk_mcp.config.settings.
All bridge state queries go through the controldesk_mcp.com_bridge public API.
"""

from __future__ import annotations

import json

import controldesk_mcp.com_bridge as com_bridge
from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.server.app import mcp

# ── Resource 1 — Server Info ──────────────────────────────────────────────────


@mcp.resource(
    uri="controldesk://server/info",
    name="ServerInfo",
    title="Server Info",
    description=(
        "Server version, transport configuration, and COM timeout settings. "
        "Always available — no ControlDesk connection required. "
        "Use this to verify which server instance is running and its configuration."
    ),
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_server_info() -> str:
    """Return server configuration as a JSON string."""
    cfg = get_settings()
    return json.dumps(
        {
            "server_version": cfg.server_version,
            "transport": cfg.mcp_transport,
            "host": cfg.mcp_host,
            "port": cfg.mcp_port,
            "controldesk_version_target": cfg.controldesk_version or "auto-detect",
            "com_timeout_ms": cfg.com_timeout_ms,
            "com_launch_timeout_ms": cfg.com_launch_timeout_ms,
            "com_reconnect_attempts": cfg.com_reconnect_attempts,
        }
    )


# ── Resource 2 — Tool Catalog ─────────────────────────────────────────────────


@mcp.resource(
    uri="controldesk://server/tool-catalog",
    name="ToolCatalog",
    title="Tool Catalog",
    description=(
        "Full catalog of all registered MCP tools sorted alphabetically, "
        "with each tool's name and description. "
        "Always available — no ControlDesk connection required. "
        "Use this to discover available automation capabilities before calling tools."
    ),
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_tool_catalog() -> str:
    """Return all registered tool names and descriptions as JSON.

    Uses mcp._tool_manager.list_tools() — a synchronous method on the internal
    ToolManager — because FastMCP provides no public non-protocol API for this.
    The tool list is stable after startup so this is safe to call at any time.
    """
    tools = [{"name": t.name, "description": t.description or ""} for t in mcp._tool_manager.list_tools()]
    tools.sort(key=lambda t: t["name"])
    return json.dumps({"count": len(tools), "tools": tools})


# ── Resource 3 — Connection Status ───────────────────────────────────────────


@mcp.resource(
    uri="controldesk://server/connection-status",
    name="ConnectionStatus",
    title="Connection Status",
    description=(
        "Current COM bridge connection state: whether a ControlDesk instance is attached, "
        "its version, and the connection health. "
        "Reads in-memory bridge state only — makes no COM calls. "
        "Refresh after calling controldesk_app_start_or_attach or controldesk_app_stop."
    ),
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": False},
)
def get_connection_status() -> str:
    """Return the current COM bridge state as JSON."""
    try:
        conn = com_bridge.get_connection()
        return json.dumps(conn.health())
    except RuntimeError:
        return json.dumps(
            {
                "connected": False,
                "state": "NOT_STARTED",
                "message": ("COM bridge not started. Call controldesk_app_start_or_attach to launch or attach to ControlDesk."),
            }
        )
