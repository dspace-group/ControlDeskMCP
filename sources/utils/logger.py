"""Stderr-only structured JSON logger. stdout is reserved for MCP JSON-RPC transport.

On stdio transport, INFO/DEBUG are silent (no stderr noise). Set LOG_LEVEL=DEBUG to enable them.
WARNING+ always write to stderr.
"""

from __future__ import annotations

import logging
import sys
from typing import ClassVar


class _StderrOnlyHandler(logging.StreamHandler):
    """StreamHandler hard-wired to stderr. Filters INFO/DEBUG on stdio (avoid MCP host noise)."""

    def __init__(self) -> None:
        super().__init__(stream=sys.stderr)
        # On stdio transport, only WARNING+ messages go to stderr.
        # INFO/DEBUG are silent unless explicitly enabled via LOG_LEVEL=DEBUG.
        self.addFilter(logging.Filter())
        self.setLevel(logging.WARNING)


_LOG_FORMAT = (
    '{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
)
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

# Module-level registry so each named logger is configured exactly once.
_configured: ClassVar[set[str]] = set()  # type: ignore


def get_logger(name: str) -> logging.Logger:
    """Return a named logger writing structured JSON to stderr. Safe to call multiple times."""
    logger = logging.getLogger(name)

    if name not in _configured:
        handler = _StderrOnlyHandler()
        handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(handler)
        logger.propagate = False  # do not forward to root logger (which may use stdout)
        _configured.add(name)
        # Default: only WARNING+ on stderr. configure_root_level() may lower this for DEBUG.
        logger.setLevel(logging.DEBUG)

    return logger


def configure_root_level(level: str) -> None:
    """Apply *level* to every logger managed by this module. Called once at startup.

    INFO/DEBUG messages are suppressed on stderr by the handler filter.
    To enable them, set LOG_LEVEL=DEBUG to lower the handler threshold.
    """
    numeric = getattr(logging, level.upper(), logging.INFO)
    for name in _configured:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # logger passes all to handler
        # Handler filter: only WARNING+ unless DEBUG is requested
        for h in logger.handlers:
            if isinstance(h, _StderrOnlyHandler):
                h.setLevel(numeric if numeric <= logging.DEBUG else logging.WARNING)
