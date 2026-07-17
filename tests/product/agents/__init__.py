"""Agentic product tests — Tool Window Management (all agents).

A single parametrized test drives every scenario against every configured
agent.  The pytest report looks like:

    test_tool_window[copilot-list_all_tool_windows]         PASSED
    test_tool_window[copilot-check_project_window_exists]   PASSED
    test_tool_window[copilot-show_and_get_state]            PASSED
    test_tool_window[copilot-show_close_panel]              PASSED
    test_tool_window[copilot-set_dock_state_auto_hidden]    PASSED

Which agents appear is controlled entirely by environment / credentials (see
``tests/product/agentic/conftest.py``):

  Copilot  — COPILOT_GITHUB_TOKEN  or  ``copilot login`` (one-time)
  LLM      — GITHUB_TOKEN  (GitHub Models / Azure OpenAI / Groq / Ollama)

Scenario definitions live in ``tests/product/scenarios/tool_window.py``
and are shared by all agents.

Assertion levels
----------------
  Level 1 — Agent completes without exception or timeout.
  Level 2 — Tool coverage: every tool in ``scenario.expected_tools`` was called.
  Level 3 — Tool success: the last result of every expected tool contains no
             ``error_code`` field.

Run
---
    # All agents, all scenarios
    uv run pytest tests/product/agentic/test_tool_window.py -m llm_product -v

    # Single scenario, all agents
    uv run pytest tests/product/agentic/test_tool_window.py \\
        -m llm_product -k list_all_tool_windows -v

    # HTML report
    uv run pytest tests/product/agentic/test_tool_window.py \\
        -m llm_product --html=reports/tool_window.html
"""

from __future__ import annotations

import pytest

from tests.product.agents.copilot_agent import CopilotAgentRunner
from tests.product.agents.llm_agent import AgentResult, LLMAgentRunner
from tests.product.scenarios.tool_window import (
    TOOL_WINDOW_SCENARIOS,
    LLMScenario,
)

AnyRunner = CopilotAgentRunner | LLMAgentRunner

pytestmark = pytest.mark.llm_product


@pytest.mark.parametrize(
    "scenario",
    TOOL_WINDOW_SCENARIOS,
    ids=lambda s: s.name,
)
async def test_tool_window(
    scenario: LLMScenario,
    tool_window_runner: AnyRunner,
    max_iterations: int,
) -> None:
    """Run one tool window scenario with the active agent and assert all three levels.

    Parameters
    ----------
    scenario:
        One of the shared ``LLMScenario`` definitions from tool_window.py.
    tool_window_runner:
        Injected by ``pytest_generate_tests`` in conftest.  Will be either a
        ``CopilotAgentRunner`` (param="copilot") or ``LLMAgentRunner`` (param="llm").
    max_iterations:
        Global cap on tool calls (from ``LLM_MAX_ITERATIONS`` env var).
    """
    # ── Level 1: agent runs to completion ────────────────────────────────────
    result: AgentResult = await tool_window_runner.run(
        prompt=scenario.prompt,
        max_iterations=scenario.max_iterations or max_iterations,
    )

    called = result.tools_called()

    # ── Level 2: tool coverage ────────────────────────────────────────────────
    for expected_tool in scenario.expected_tools:
        assert expected_tool in called, (
            f"Expected tool '{expected_tool}' was never called.\n"
            f"Tools called : {called}\n"
            f"Scenario     : {scenario.name}\n"
            f"Agent        : {type(tool_window_runner).__name__}\n"
            f"Prompt       : {scenario.prompt}\n"
            f"Agent output : {result.final_message[:200]}"
        )

    # ── Level 3: tool success ─────────────────────────────────────────────────
    if scenario.assert_tool_success:
        for tool_name in scenario.expected_tools:
            tool_result = result.last_result_for(tool_name)
            assert tool_result is not None, (
                f"Tool '{tool_name}' was called but its result was not captured.\n"
                f"Scenario : {scenario.name}"
            )
            assert "error_code" not in tool_result, (
                f"Tool '{tool_name}' returned an error.\n"
                f"Result   : {tool_result}\n"
                f"Scenario : {scenario.name}\n"
                f"Agent    : {type(tool_window_runner).__name__}"
            )

