"""Agentic product tests — Application Lifecycle (all agents).

A single parametrized test drives every scenario against every configured
agent.  The pytest report looks like:

    test_application_lifecycle[copilot-start_and_report_version]   PASSED
    test_application_lifecycle[copilot-query_visibility_readonly]   PASSED
    ...
    test_application_lifecycle[llm-start_and_report_version]        PASSED  ← if LLM configured
    ...

Which agents appear is controlled entirely by environment / credentials (see
``tests/product/agentic/conftest.py``):

  Copilot  — COPILOT_GITHUB_TOKEN  or  ``copilot login`` (one-time)
  LLM      — GITHUB_TOKEN  (GitHub Models / Azure OpenAI / Groq / Ollama)

Scenario definitions live in ``tests/product/scenarios/application_lifecycle.py``
and are shared by all agents.  Adding a new scenario automatically exercises
it against every configured agent.

Assertion levels
----------------
  Level 1 — Agent completes without exception or timeout.
  Level 2 — Tool coverage: every tool in ``scenario.expected_tools`` was called.
  Level 3 — Tool success: the last result of every expected tool contains no
             ``error_code`` field.  The MCP tool result IS the ground truth —
             a success envelope means the action happened.  No independent COM
             reader is needed.  This scales to any number of tools.

Run
---
    # All agents, all scenarios
    .\\scripts\\run_product_tests.ps1 -Suite agentic

    # Single scenario, all agents
    uv run pytest tests/product/agentic/ -m llm_product -k start_and_report_version -v

    # HTML report
    uv run pytest tests/product/agentic/ -m llm_product --html=reports/agentic.html
"""

from __future__ import annotations

import pytest

from tests.product.agents.copilot_agent import CopilotAgentRunner
from tests.product.agents.llm_agent import AgentResult, LLMAgentRunner
from tests.product.scenarios.application_lifecycle import (
    APPLICATION_LIFECYCLE_SCENARIOS,
    LLMScenario,
)

AnyRunner = CopilotAgentRunner | LLMAgentRunner

pytestmark = pytest.mark.llm_product


@pytest.mark.parametrize(
    "scenario",
    APPLICATION_LIFECYCLE_SCENARIOS,
    ids=lambda s: s.name,
)
async def test_application_lifecycle(
    scenario: LLMScenario,
    agent_runner: AnyRunner,
    max_iterations: int,
) -> None:
    """Run one lifecycle scenario with the active agent and assert all three levels.

    Parameters
    ----------
    scenario:
        One of the shared ``LLMScenario`` definitions — identical for all agents.
    agent_runner:
        Injected by ``pytest_generate_tests`` in conftest.  Will be either a
        ``CopilotAgentRunner`` (param="copilot") or ``LLMAgentRunner`` (param="llm").
    max_iterations:
        Global cap on tool calls (from ``LLM_MAX_ITERATIONS`` env var).
    """
    # ── Level 1: agent runs to completion ────────────────────────────────────
    result: AgentResult = await agent_runner.run(
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
            f"Agent        : {type(agent_runner).__name__}\n"
            f"Prompt       : {scenario.prompt}\n"
            f"Agent output : {result.final_message[:200]}"
        )

    # ── Level 3: tool success ─────────────────────────────────────────────────
    # The MCP tool result is the ground truth.  A success result has no
    # ``error_code`` field.  This works for every tool without any per-tool
    # verification code.
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
                f"Agent    : {type(agent_runner).__name__}"
            )

