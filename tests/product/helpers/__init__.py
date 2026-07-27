"""LLM agentic loop driver for product tests.

Drives a GitHub Models LLM (GPT-4.1 or any OpenAI-compatible model) through a
multi-turn conversation where it autonomously selects MCP tools until the goal
is achieved.

Architecture
------------
1. ``ToolRegistry`` — domain-agnostic registry that maps tool names to their
   FastMCP ``Tool`` objects.  Each domain (application, project, measurement…)
   builds its own registry by passing the ``mcp`` instance.  Schemas are pulled
   directly from the live FastMCP registration — not hardcoded.

2. ``LLMAgentRunner`` — receives a ``ToolRegistry`` and a prompt, then drives
   the agentic loop until ``finish_reason == "stop"`` or ``max_iterations``.

Multi-tool call handling
------------------------
The LLM may emit multiple ``tool_calls`` in a single response (parallel intent).
Because ControlDesk's COM bridge is STA-bound, tool calls are executed
SEQUENTIALLY even when the LLM intended them to run in parallel.  ALL results
are collected and returned to the LLM in one batch before the next turn — this
is required by the OpenAI protocol.

Schema flattening
-----------------
FastMCP wraps every tool's Pydantic input model in a top-level ``params``
property:  ``{"properties": {"params": {"$ref": "..."}}, "$defs": {...}}``.
``ToolRegistry`` flattens this before exposing the schema to the LLM so the
LLM calls tools with direct field names (e.g. ``{"visible": true}``).
``tool.run()`` receives the original wrapped form (``{"params": {...}}``) so
FastMCP's Pydantic coercion continues to work.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openai import OpenAI, RateLimitError
from openai.types.chat import ChatCompletionMessageParam

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

_log = logging.getLogger(__name__)

# ── Default system prompt ─────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are a ControlDesk automation agent. "
    "Use the provided MCP tools to fulfil the user's goal exactly as stated. "
    "Always call start_controldesk first if no ControlDesk session is established. "
    "Do NOT call stop_controldesk unless the user explicitly asks you to quit ControlDesk. "
    "Report the final outcome once all requested actions are complete."
)


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class ToolCallRecord:
    """One tool call made by the LLM during the agentic loop."""

    name: str
    arguments: dict[str, Any]
    result: str  # Raw JSON string returned by the MCP tool
    tool_call_id: str
    turn: int  # Which LLM turn triggered this call (0-based)


@dataclass
class AgentResult:
    """Complete result from one LLM agent run."""

    final_message: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    iterations: int = 0
    finish_reason: str = "stop"

    def tools_called(self) -> list[str]:
        """Return tool names in call order (duplicates preserved)."""
        return [tc.name for tc in self.tool_calls]

    def was_tool_called(self, name: str) -> bool:
        return any(tc.name == name for tc in self.tool_calls)

    def last_result_for(self, name: str) -> dict[str, Any] | None:
        """Return the parsed JSON result of the last call to ``name``, or None."""
        for tc in reversed(self.tool_calls):
            if tc.name == name:
                try:
                    return json.loads(tc.result)
                except json.JSONDecodeError:
                    return None
        return None


class AgentTimeoutError(RuntimeError):
    """Raised when the agentic loop exceeds ``max_iterations``."""


# ── Tool registry ─────────────────────────────────────────────────────────────


class ToolRegistry:
    """Domain-agnostic registry of MCP tools for LLM agent execution.

    Built from a FastMCP instance — reads the live tool registration so schemas
    always match production.  Extend for new domains by calling ``add_from_mcp``
    with an optional ``include`` filter.

    Example (application lifecycle):
        registry = ToolRegistry()
        registry.add_from_mcp(mcp, include={
            "start_controldesk", "app_set_window_visible", ...
        })
    """

    def __init__(self) -> None:
        # name → FastMCP Tool object
        self._tools: dict[str, Any] = {}
        # name → bool: does this tool wrap its input in a "params" property?
        self._has_params_wrapper: dict[str, bool] = {}

    def add_from_mcp(self, mcp: "FastMCP", include: set[str] | None = None) -> None:
        """Register tools from a FastMCP instance.

        Parameters
        ----------
        mcp:
            The live FastMCP instance (``controldesk_mcp.server.app.mcp``).
        include:
            If provided, only these tool names are registered.  If None, all
            tools in the instance are registered.
        """
        for name, tool in mcp._tool_manager._tools.items():
            if include is not None and name not in include:
                continue
            self._tools[name] = tool
            # Detect the params-wrapper pattern FastMCP uses for Pydantic models
            props = tool.parameters.get("properties", {})
            self._has_params_wrapper[name] = "params" in props

    def get_openai_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-format function schemas for all registered tools.

        FastMCP's ``params`` wrapper is flattened so the LLM sees direct field
        names (e.g. ``{"visible": true}``) rather than ``{"params": {...}}``.
        """
        schemas: list[dict[str, Any]] = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or "",
                        "parameters": self._flatten_schema(tool.parameters),
                    },
                }
            )
        return schemas

    @staticmethod
    def _flatten_schema(raw: dict[str, Any]) -> dict[str, Any]:
        """Unwrap the FastMCP ``params`` wrapper from the JSON Schema."""
        props = raw.get("properties", {})
        defs = raw.get("$defs", {})

        if "params" not in props:
            return {"type": "object", "properties": {}}

        ref = props["params"].get("$ref", "")
        if not ref:
            return {"type": "object", "properties": {}}

        ref_name = ref.split("/")[-1]  # e.g. "AppStartOrAttachInput"
        inner = dict(defs.get(ref_name, {}))

        remaining_defs = {k: v for k, v in defs.items() if k != ref_name}
        if remaining_defs:
            inner["$defs"] = remaining_defs

        return inner

    async def call(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a registered tool by name with the LLM-supplied flat arguments."""
        if name not in self._tools:
            return json.dumps({"error_code": "TOOL_NOT_FOUND", "tool": name, "retryable": False})

        tool = self._tools[name]

        if self._has_params_wrapper[name]:
            call_args: dict[str, Any] = {"params": arguments}
        else:
            call_args = arguments  # no-input tools

        raw = await tool.run(call_args)

        if isinstance(raw, str):
            return raw
        if isinstance(raw, (dict, list)):
            return json.dumps(raw)
        return str(raw)

    def registered_names(self) -> list[str]:
        return list(self._tools.keys())


# ── LLM agent runner ──────────────────────────────────────────────────────────


class LLMAgentRunner:
    """Drives an LLM through a multi-turn conversation with registered MCP tools."""

    def __init__(
        self,
        registry: ToolRegistry,
        model: str,
        base_url: str,
        api_key: str,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self._registry = registry
        self._model = model
        self._system_prompt = system_prompt
        self._llm = OpenAI(base_url=base_url, api_key=api_key)

    async def run(
        self,
        prompt: str,
        max_iterations: int = 15,
    ) -> AgentResult:
        """Run the agentic loop for a single natural-language prompt."""
        tool_schemas = self._registry.get_openai_schemas()
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": prompt},
        ]
        audit: list[ToolCallRecord] = []

        _log.info("")
        _log.info("┌─ LLM AGENT (%s) ─────────────────────────────────────────", self._model)
        _log.info("│ PROMPT: %s", prompt)
        _log.info("│")

        for turn in range(max_iterations):
            try:
                response = self._llm.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    tools=tool_schemas,  # type: ignore[arg-type]
                    tool_choice="auto",
                )
            except RateLimitError as exc:
                raise AgentTimeoutError(
                    f"GitHub Models rate limit hit at turn {turn}: {exc}"
                ) from exc

            choice = response.choices[0]
            assistant_msg = choice.message
            messages.append(assistant_msg.model_dump(exclude_none=True))

            if choice.finish_reason == "stop":
                _log.info("│ RESPONSE: %s", (assistant_msg.content or "")[:300])
                _log.info("└──────────────────────────────────────────────────────────")
                return AgentResult(
                    final_message=assistant_msg.content or "",
                    tool_calls=audit,
                    iterations=turn + 1,
                    finish_reason="stop",
                )

            if choice.finish_reason == "tool_calls" and assistant_msg.tool_calls:
                tool_results: list[ChatCompletionMessageParam] = []

                for tc in assistant_msg.tool_calls:
                    try:
                        raw_args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        raw_args = {}

                    _log.info("│ → TOOL CALL : %s(%s)", tc.function.name, _fmt_args(raw_args))
                    result_str = await self._registry.call(tc.function.name, raw_args)
                    _log.info("│ ← TOOL RESULT: %s", result_str[:200])

                    audit.append(
                        ToolCallRecord(
                            name=tc.function.name,
                            arguments=raw_args,
                            result=result_str,
                            tool_call_id=tc.id,
                            turn=turn,
                        )
                    )
                    tool_results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result_str,
                        }
                    )

                messages.extend(tool_results)

        raise AgentTimeoutError(
            f"Agent did not finish within {max_iterations} iterations. "
            f"Last tools called: {[tc.name for tc in audit[-5:]]}"
        )


# ── Formatting helpers ────────────────────────────────────────────────────────


def _fmt_args(args: dict[str, Any]) -> str:
    """Compact single-line representation of tool arguments."""
    parts = []
    for k, v in args.items():
        parts.append(f"{k}={v!r}" if not isinstance(v, dict) else f"{k}={{...}}")
    return ", ".join(parts) if parts else ""
