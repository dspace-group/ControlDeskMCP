"""ErrorEnvelope — structured error payload for all failed tool calls."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from sources.models.base import DictModelMixin


class ErrorEnvelope(DictModelMixin, BaseModel):
    """Structured error payload for failed tool calls. Rendered as Markdown for the LLM."""

    error_code: str = Field(
        description="Machine-readable error code, e.g. 'COM_DISCONNECTED'.",
        examples=["COM_DISCONNECTED", "CD_PRECONDITION", "CD_BAD_INPUT"],
    )
    category: Literal[
        "CONNECTION",
        "UI_BLOCKING",
        "CIRCUIT",
        "PRECONDITION",
        "OPERATION",
        "VERSION_MISMATCH",
        "TIMEOUT",
        "INPUT_VALIDATION",
        "SYSTEM",
        "UNKNOWN",
    ] = Field(
        description="High-level error category used for routing and display.",
    )
    message: str = Field(
        description="Human-readable English sentence describing what went wrong.",
    )
    detail: str = Field(
        default="",
        description="Technical detail such as the raw HRESULT value or "
        "IErrorInfo description string.",
    )
    hresult: int | None = Field(
        default=None,
        description="Raw unsigned HRESULT integer (e.g. 0x80010108). "
        "None when the error is not COM-originated.",
    )
    com_interface: str | None = Field(
        default=None,
        description="COM interface name where the error occurred, "
        "e.g. 'IXaMeasurementConfiguration'.",
    )
    com_method: str | None = Field(
        default=None,
        description="COM method name where the error occurred, e.g. 'Start'.",
    )
    retryable: bool = Field(
        default=False,
        description="True when the LLM may retry the same tool call after a "
        "short delay without human intervention.",
    )
    recovery_hint: str = Field(
        default="",
        description="Actionable guidance for the LLM or user, e.g. "
        "'Call start_controldesk to re-establish the COM connection.'",
    )
    correlation_id: str = Field(
        default="",
        description="UUID linking this MCP error to a dSPACE ILoLog entry "
        "for correlated audit trails.",
    )

    def to_markdown(self) -> str:
        """Render as a Markdown error card."""
        lines = [
            "## ControlDesk MCP Error",
            "",
            f"**Code:** `{self.error_code}`  ",
            f"**Category:** {self.category}  ",
            f"**Retryable:** {'Yes' if self.retryable else 'No'}  ",
            "",
            f"**Message:** {self.message}",
        ]
        if self.detail:
            lines += ["", f"**Detail:** `{self.detail}`"]
        if self.hresult is not None:
            lines += [f"**HRESULT:** `0x{self.hresult:08X}`"]
        if self.com_interface or self.com_method:
            iface = self.com_interface or "?"
            method = self.com_method or "?"
            lines += [f"**COM:** `{iface}.{method}`"]
        if self.recovery_hint:
            lines += ["", f"**Recovery:** {self.recovery_hint}"]
        if self.correlation_id:
            lines += ["", f"**Correlation ID:** `{self.correlation_id}`"]
        return "\n".join(lines)
