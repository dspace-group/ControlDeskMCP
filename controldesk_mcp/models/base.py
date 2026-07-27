"""Base classes shared across all model files."""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict


class DictModelMixin:
    """Makes Pydantic models subscriptable and dict-like for backward compatibility."""

    def __getitem__(self, key: str):
        try:
            val = getattr(self, key)
        except AttributeError:
            raise KeyError(key)
        return val

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default=None):
        try:
            return getattr(self, key)
        except AttributeError:
            return default


class ToolResult(DictModelMixin, BaseModel):
    """Generic result container that accepts arbitrary fields."""

    model_config = ConfigDict(extra="allow")


def make_tool_result(data) -> ToolResult:
    """Convert a service return value (model, dict, or JSON string) to ToolResult."""
    if isinstance(data, str):
        data = json.loads(data)
    elif hasattr(data, "model_dump"):
        data = data.model_dump()
    return ToolResult(**data)


class DryRunPreviewResult(DictModelMixin, BaseModel):
    """Generic preview response for any tool invoked with ``dry_run=True``.

    Returned instead of performing the mutating action. Reports what the tool
    would do — based on a read-only precondition check — without invoking the
    underlying mutating COM operation, so calling with ``dry_run=True`` is
    always safe and has no side effects.
    """

    model_config = ConfigDict(extra="allow")
    dry_run: bool = True
    tool: str
    action: str
    target: str
    would_execute: bool
    current_state: dict = {}
    message: str
