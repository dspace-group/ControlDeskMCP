"""FastMCP instance, lifespan, and bootstrap tools."""

from __future__ import annotations

import logging
import platform
import struct
import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.server.server import MCPServer
from controldesk_mcp.utils.logger import configure_root_level, get_logger

_log = get_logger(__name__)


# ── Suppress FastMCP internal logging ──────────────────────────────────────────
# FastMCP emits INFO-level logs for every protocol message.
# Suppress them to keep stderr clean on the stdio transport.
logging.getLogger("mcp.server").setLevel(logging.WARNING)
logging.getLogger("mcp.server.fastmcp").setLevel(logging.WARNING)


# ── Startup validation ────────────────────────────────────────────────────────


def _validate_runtime() -> None:
    """Raise RuntimeError if Python <3.11 or 32-bit on Windows."""
    # 1. Python version
    if sys.version_info < (3, 11):
        msg = f"Python 3.11+ required; running {sys.version}. Upgrade the Python interpreter."
        raise RuntimeError(msg)

    # 2. Process bitness — COM automation objects are 64-bit only on Windows
    if platform.system() == "Windows" and struct.calcsize("P") != 8:
        msg = (
            "A 64-bit Python interpreter is required on Windows. "
            "The COM ControlDesk automation interface does not support 32-bit clients."
        )
        raise RuntimeError(msg)


# ── Lifespan ──────────────────────────────────────────────────────────────────


@asynccontextmanager
async def _lifespan(server: FastMCP) -> Any:  # type: ignore[type-arg]
    """Configure logging, validate runtime, and bracket COM bridge lifecycle."""
    cfg = get_settings()
    configure_root_level(cfg.log_level)

    _log.debug(
        "ControlDesk MCP Server starting (transport=%s, log_level=%s)",
        cfg.mcp_transport,
        cfg.log_level,
    )

    _validate_runtime()
    _log.debug("Runtime validation passed (Python %s, 64-bit OK)", sys.version.split()[0])

    # Start only the STA thread — COM connection is deferred to the first tool call.
    # This keeps the lifespan fast so the MCP `initialize` handshake completes immediately.
    from controldesk_mcp import com_bridge  # noqa: PLC0415

    await com_bridge.startup()
    _log.info("STA thread started; COM connection deferred until first tool call")

    try:
        yield {}
    finally:
        _log.debug("ControlDesk MCP Server shutting down")
        await com_bridge.shutdown()


# ── FastMCP instance ──────────────────────────────────────────────────────────

_cfg = get_settings()

mcp = MCPServer(
    name="ControlDesk MCP Server",
    instructions=(
        "Provides tools to automate dSPACE ControlDesk via COM. "
        "Read the resource `controldesk://server/info` to confirm the server version. "
        "All tools return JSON strings. "
        "On failure, tools return an error envelope with `error_code`, "
        "`retryable`, and `recovery_hint` fields."
    ),
    lifespan=_lifespan,
    log_level=_cfg.log_level,
)


# ── Domain tool registration ──────────────────────────────────────────────────
# Importing registry triggers all @mcp.tool decorators, registering every domain tool.
# To add a new domain, add its import to controldesk_mcp/server/registry.py only.

import controldesk_mcp.server.registry  # noqa: E402, F401
