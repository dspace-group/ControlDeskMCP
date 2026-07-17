"""GitHub Copilot SDK agentic runner for product tests.

Drives a GitHub Copilot CLI session to fulfil a natural-language prompt by
calling registered MCP tools.  No API key or external LLM endpoint is required
— authentication is handled by the Copilot CLI using the user's existing
Copilot Business subscription.

Configuration (via .env / env vars)
------------------------------------
    COPILOT_CLI_PATH   — absolute path to the copilot CLI binary.
                         Leave unset (or empty) to use the native executable
                         bundled with the ``github-copilot-sdk`` package.
    COPILOT_MODEL      — model name passed to create_session().
                         Default: gpt-4.1
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from copilot import CopilotClient, SubprocessConfig
from copilot.session import (
    AssistantMessageData,
    PermissionHandler,
    PostToolUseHookInput,
    PostToolUseHookOutput,
    PreToolUseHookInput,
    PreToolUseHookOutput,
    SessionEvent,
    SessionHooks,
    SessionIdleData,
)
from copilot.tools import Tool, ToolInvocation, ToolResult

from tests.product.agents.llm_agent import (
    AgentResult,
    AgentTimeoutError,
    ToolCallRecord,
    ToolRegistry,
    _fmt_args,
)

_log = logging.getLogger(__name__)

_STRIP_ENV_VARS = frozenset({"GITHUB_TOKEN", "GH_TOKEN"})


def _clean_env() -> dict[str, str]:
    """Return os.environ with GitHub Models / Azure PATs stripped out.

    The Copilot CLI checks COPILOT_GITHUB_TOKEN → GH_TOKEN → GITHUB_TOKEN in
    that order.  Our ``GITHUB_TOKEN`` is a GitHub Models PAT that does *not*
    have the "Copilot Requests" permission — forwarding it causes auth errors.
    """
    return {k: v for k, v in os.environ.items() if k not in _STRIP_ENV_VARS}


_SYSTEM_PROMPT = (
    "You are a ControlDesk automation agent. "
    "Use ONLY the provided custom tools to fulfil the user's goal. "
    "Always call start_controldesk first if no ControlDesk session is established. "
    "Do NOT call stop_controldesk unless the user explicitly asks you to quit ControlDesk. "
    "Do NOT use shell commands, file read/write tools, or any other built-in tools. "
    "Report the final outcome once all requested actions are complete."
)

_TOOL_TIMEOUT_S: float = 30.0
_SESSION_IDLE_TIMEOUT_S: float = 300.0


class CopilotAgentRunner:
    """Run a Copilot-SDK agentic session against registered MCP tools."""

    def __init__(
        self,
        registry: ToolRegistry,
        model: str = "gpt-4.1",
        cli_path: str | None = None,
        github_token: str | None = None,
    ) -> None:
        self._registry = registry
        self._model = model
        self._cli_path = cli_path or os.environ.get("COPILOT_CLI_PATH") or None
        self._copilot_token = github_token or os.environ.get("COPILOT_GITHUB_TOKEN") or None

    async def run(self, prompt: str, max_iterations: int = 15) -> AgentResult:
        """Send *prompt* to the Copilot agent and wait for completion."""
        tool_calls: list[ToolCallRecord] = []
        final_message: str = ""
        done_event = asyncio.Event()

        config = SubprocessConfig(
            cli_path=self._cli_path,
            github_token=self._copilot_token,
            env=_clean_env(),
        )
        copilot_tools = self._build_copilot_tools(tool_calls)

        async def _on_pre_tool_use(inp: PreToolUseHookInput) -> PreToolUseHookOutput:
            return PreToolUseHookOutput(permissionDecision="allow")

        async def _on_post_tool_use(inp: PostToolUseHookInput) -> PostToolUseHookOutput:
            return PostToolUseHookOutput()

        hooks = SessionHooks(
            on_pre_tool_use=_on_pre_tool_use,
            on_post_tool_use=_on_post_tool_use,
        )

        def _on_event(event: SessionEvent) -> None:
            nonlocal final_message
            data = event.data
            if isinstance(data, AssistantMessageData):
                content = getattr(data, "content", "") or ""
                final_message = content
                if content:
                    _log.info("│ RESPONSE: %s", content[:300])
            elif isinstance(data, SessionIdleData):
                _log.info("└──────────────────────────────────────────────────────────")
                done_event.set()

        _log.info("")
        _log.info("┌─ COPILOT AGENT (%s) ──────────────────────────────────────", self._model)
        _log.info("│ PROMPT: %s", prompt)
        _log.info("│")

        async with CopilotClient(config) as client:
            session = await client.create_session(
                on_permission_request=PermissionHandler.approve_all,
                model=self._model,
                tools=copilot_tools,
                system_message={"text": _SYSTEM_PROMPT},
                hooks=hooks,
                on_event=_on_event,
            )
            async with session:
                await session.send(prompt)

                try:
                    await asyncio.wait_for(
                        done_event.wait(),
                        timeout=_SESSION_IDLE_TIMEOUT_S,
                    )
                except asyncio.TimeoutError as exc:
                    raise AgentTimeoutError(
                        f"Copilot session did not complete within "
                        f"{_SESSION_IDLE_TIMEOUT_S:.0f}s for prompt: {prompt[:80]!r}"
                    ) from exc

        n_calls = len(tool_calls)
        if n_calls > max_iterations:
            raise AgentTimeoutError(
                f"Copilot agent made {n_calls} tool calls, exceeding "
                f"max_iterations={max_iterations}."
            )

        return AgentResult(
            final_message=final_message,
            tool_calls=tool_calls,
            iterations=n_calls,
            finish_reason="stop",
        )

    def _build_copilot_tools(self, audit: list[ToolCallRecord]) -> list[Tool]:
        """Convert each registry entry to a Copilot SDK ``Tool`` object."""
        tools: list[Tool] = []
        registry = self._registry

        for name in registry.registered_names():
            mcp_tool = registry._tools[name]
            flat_schema = ToolRegistry._flatten_schema(mcp_tool.parameters)

            async def _handler(
                invocation: ToolInvocation,
                _name: str = name,
            ) -> ToolResult:
                args = invocation.arguments or {}
                _log.info("│ → TOOL CALL : %s(%s)", _name, _fmt_args(args))

                try:
                    result_str = await asyncio.wait_for(
                        registry.call(_name, args),
                        timeout=_TOOL_TIMEOUT_S,
                    )
                except asyncio.TimeoutError:
                    result_str = json.dumps(
                        {
                            "error_code": "TOOL_TIMEOUT",
                            "tool": _name,
                            "message": f"Tool timed out after {_TOOL_TIMEOUT_S:.0f}s",
                        }
                    )

                _log.info("│ ← TOOL RESULT: %s", result_str[:200])

                audit.append(
                    ToolCallRecord(
                        name=_name,
                        arguments=args,
                        result=result_str,
                        tool_call_id=str(len(audit)),
                        turn=len(audit),
                    )
                )
                return ToolResult(
                    text_result_for_llm=result_str,
                    result_type="success",
                )

            tools.append(
                Tool(
                    name=name,
                    description=mcp_tool.description or "",
                    parameters=flat_schema,
                    handler=_handler,
                    skip_permission=True,
                )
            )

        return tools
