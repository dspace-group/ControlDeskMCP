"""Agentic product tests — Project & Experiment Management (all agents).

A single parametrized test drives every scenario against every configured
agent.  The pytest report looks like:

    test_project_experiment[copilot-list_project_roots]               PASSED
    test_project_experiment[copilot-add_root_and_check_list]          PASSED
    test_project_experiment[copilot-create_project_and_get_info]      PASSED
    test_project_experiment[copilot-project_exists_check]             PASSED
    test_project_experiment[copilot-create_experiment_flow]           PASSED

Which agents appear is controlled entirely by environment / credentials (see
``tests/product/agentic/conftest.py``):

  Copilot  — COPILOT_GITHUB_TOKEN  or  ``copilot login`` (one-time)
  LLM      — GITHUB_TOKEN  (GitHub Models / Azure OpenAI / Groq / Ollama)

Scenario definitions live in ``tests/product/scenarios/project_experiment.py``
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
    .\\scripts\\run_product_tests.ps1 -Suite agentic

    # Single scenario, all agents
    uv run pytest tests/product/agentic/test_project_experiment.py \\
        -m llm_product -k list_project_roots -v

    # HTML report
    uv run pytest tests/product/agentic/test_project_experiment.py \\
        -m llm_product --html=reports/agentic.html
"""

from __future__ import annotations

import pytest

from tests.product.agents.copilot_agent import CopilotAgentRunner
from tests.product.agents.llm_agent import AgentResult, LLMAgentRunner
from tests.product.scenarios.project_experiment import (
    PROJECT_EXPERIMENT_SCENARIOS,
    LLMScenario,
)

AnyRunner = CopilotAgentRunner | LLMAgentRunner

pytestmark = pytest.mark.llm_product


@pytest.mark.parametrize(
    "scenario",
    PROJECT_EXPERIMENT_SCENARIOS,
    ids=lambda s: s.name,
)
async def test_project_experiment(
    scenario: LLMScenario,
    project_agent_runner: AnyRunner,
    max_iterations: int,
) -> None:
    """Run one project/experiment scenario with the active agent and assert all three levels.

    Parameters
    ----------
    scenario:
        One of the shared ``LLMScenario`` definitions from project_experiment.py.
    project_agent_runner:
        Injected by ``pytest_generate_tests`` in conftest.  Will be either a
        ``CopilotAgentRunner`` (param="copilot") or ``LLMAgentRunner`` (param="llm").
    max_iterations:
        Global cap on tool calls (from ``LLM_MAX_ITERATIONS`` env var).
    """
    # ── Level 1: agent runs to completion ────────────────────────────────────
    result: AgentResult = await project_agent_runner.run(
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
            f"Agent        : {type(project_agent_runner).__name__}\n"
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
                f"Agent    : {type(project_agent_runner).__name__}"
            )

