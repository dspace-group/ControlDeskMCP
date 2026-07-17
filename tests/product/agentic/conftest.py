"""Agentic product test fixtures.

Agent matrix
-------------
Tests are parametrized over all *available* agents automatically — no manual
selection needed.

+----------+-----------------------------------------------+------------------+
| Agent ID | Implementation                                | Required         |
+----------+-----------------------------------------------+------------------+
| copilot  | github-copilot-sdk (CopilotAgentRunner)       | COPILOT_GITHUB_  |
|          | Bundled copilot.exe — no separate install.    | TOKEN  or        |
|          |                                               | `copilot login`  |
+----------+-----------------------------------------------+------------------+
| llm      | OpenAI-compatible HTTP (LLMAgentRunner)       | GITHUB_TOKEN     |
|          | GitHub Models / Azure OpenAI / Groq / Ollama  | (GitHub Models)  |
+----------+-----------------------------------------------+------------------+

If an agent's required credentials are absent the agent is removed from the
parameter list and its tests are never collected (no SKIP noise).

Configuration (via .env / env vars)
------------------------------------
  Copilot:
    COPILOT_GITHUB_TOKEN   — fine-grained PAT with "Copilot Requests" permission
                             (OR run `copilot login` once — no token needed then)
    COPILOT_MODEL          — model name (default: gpt-4.1)
    COPILOT_CLI_PATH       — override bundled CLI path (usually leave empty)

  OpenAI-compatible:
    GITHUB_TOKEN           — API key / PAT for the LLM endpoint
    GITHUB_MODELS_BASE_URL — OpenAI-compatible base URL
    GITHUB_MODELS_MODEL    — model name (default: gpt-4.1)

  Both:
    LLM_MAX_ITERATIONS     — max tool calls per scenario (default: 15)
"""

from __future__ import annotations

import os

import pytest

from tests.product.agents.copilot_agent import CopilotAgentRunner
from tests.product.agents.llm_agent import LLMAgentRunner, ToolRegistry
from tests.product.helpers.session import (
    get_base_url,
    get_copilot_cli_path,
    get_copilot_github_token,
    get_copilot_model,
    get_max_iterations,
    get_model,
)

# ── Agent availability check (module-level, evaluated at collection time) ─────


def _copilot_available() -> bool:
    """True if Copilot credentials are present (token or stored login)."""
    token = get_copilot_github_token()
    if token:
        return True
    # Check for stored login credentials in ~/.copilot/
    config_dir = os.path.join(os.path.expanduser("~"), ".copilot")
    hosts_file = os.path.join(config_dir, "hosts.json")
    return os.path.isfile(hosts_file)


def _llm_available() -> bool:
    """True if a GitHub Models / OpenAI-compatible token is present."""
    return bool(os.environ.get("GITHUB_TOKEN"))


def _available_agents() -> list[str]:
    """Return agent IDs whose prerequisites are satisfied."""
    agents: list[str] = []
    if _copilot_available():
        agents.append("copilot")
    if _llm_available():
        agents.append("llm")
    return agents


# ── Dynamic parametrization ───────────────────────────────────────────────────


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Parametrize ``agent_runner``, ``project_agent_runner``, and ``tool_window_runner``
    over all available agents.

    Called by pytest during collection.  Tests are only generated for agents
    whose credentials are present — absent agents produce no rows at all (not
    even SKIPs), keeping the report clean.
    """
    for fixture_name in ("agent_runner", "project_agent_runner", "tool_window_runner"):
        if fixture_name not in metafunc.fixturenames:
            continue

        agents = _available_agents()
        if not agents:
            # No agents configured — force a single row that will xfail with a
            # clear message rather than silently collecting zero tests.
            metafunc.parametrize(
                fixture_name,
                ["_no_agent_"],
                indirect=True,
                ids=["no_agent_configured"],
            )
        else:
            metafunc.parametrize(fixture_name, agents, indirect=True, ids=agents)


# ── Runner fixtures ───────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def agent_runner(
    request: pytest.FixtureRequest,
    copilot_runner: CopilotAgentRunner,
    llm_runner: LLMAgentRunner,
) -> CopilotAgentRunner | LLMAgentRunner:
    """Return the runner for the current agent parameter.

    The ``request.param`` value is one of the IDs from ``_available_agents()``.
    An unknown value (e.g. ``_no_agent_``) causes the test to xfail with an
    informative message.
    """
    param = request.param
    if param == "copilot":
        return copilot_runner
    if param == "llm":
        return llm_runner
    pytest.xfail(
        "No agentic runner is configured.\n"
        "  Copilot: set COPILOT_GITHUB_TOKEN or run `copilot login`.\n"
        "  LLM:     set GITHUB_TOKEN (GitHub Models PAT)."
    )


@pytest.fixture(scope="session")
def copilot_runner(app_lifecycle_registry: ToolRegistry) -> CopilotAgentRunner:
    """CopilotAgentRunner — uses the SDK-bundled copilot.exe."""
    return CopilotAgentRunner(
        registry=app_lifecycle_registry,
        model=get_copilot_model(),
        cli_path=get_copilot_cli_path() or None,
        github_token=get_copilot_github_token() or None,
    )


@pytest.fixture(scope="session")
def llm_runner(app_lifecycle_registry: ToolRegistry) -> LLMAgentRunner:
    """LLMAgentRunner — GitHub Models / Azure OpenAI / Groq / Ollama."""
    return LLMAgentRunner(
        registry=app_lifecycle_registry,
        model=get_model(),
        base_url=get_base_url(),
        api_key=os.environ.get("GITHUB_TOKEN", ""),
    )


# ── Shared ────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def max_iterations() -> int:
    """Max agentic loop turns per scenario (from LLM_MAX_ITERATIONS env var)."""
    return get_max_iterations()


# ── Project experiment runner fixtures ────────────────────────────────────────


@pytest.fixture(scope="session")
def project_agent_runner(
    request: pytest.FixtureRequest,
    project_copilot_runner: CopilotAgentRunner,
    project_llm_runner: LLMAgentRunner,
) -> CopilotAgentRunner | LLMAgentRunner:
    """Return the project-domain runner for the current agent parameter."""
    param = request.param
    if param == "copilot":
        return project_copilot_runner
    if param == "llm":
        return project_llm_runner
    pytest.xfail(
        "No agentic runner is configured.\n"
        "  Copilot: set COPILOT_GITHUB_TOKEN or run `copilot login`.\n"
        "  LLM:     set GITHUB_TOKEN (GitHub Models PAT)."
    )


@pytest.fixture(scope="session")
def project_copilot_runner(project_experiment_registry: ToolRegistry) -> CopilotAgentRunner:
    """CopilotAgentRunner with project & experiment tools."""
    return CopilotAgentRunner(
        registry=project_experiment_registry,
        model=get_copilot_model(),
        cli_path=get_copilot_cli_path() or None,
        github_token=get_copilot_github_token() or None,
    )


@pytest.fixture(scope="session")
def project_llm_runner(project_experiment_registry: ToolRegistry) -> LLMAgentRunner:
    """LLMAgentRunner with project & experiment tools."""
    return LLMAgentRunner(
        registry=project_experiment_registry,
        model=get_model(),
        base_url=get_base_url(),
        api_key=os.environ.get("GITHUB_TOKEN", ""),
    )


# ── Tool window runner fixtures ───────────────────────────────────────────────


@pytest.fixture(scope="session")
def tool_window_runner(
    request: pytest.FixtureRequest,
    tool_window_copilot_runner: CopilotAgentRunner,
    tool_window_llm_runner: LLMAgentRunner,
) -> CopilotAgentRunner | LLMAgentRunner:
    """Return the tool-window-domain runner for the current agent parameter."""
    param = request.param
    if param == "copilot":
        return tool_window_copilot_runner
    if param == "llm":
        return tool_window_llm_runner
    pytest.xfail(
        "No agentic runner is configured.\n"
        "  Copilot: set COPILOT_GITHUB_TOKEN or run `copilot login`.\n"
        "  LLM:     set GITHUB_TOKEN (GitHub Models PAT)."
    )


@pytest.fixture(scope="session")
def tool_window_copilot_runner(tool_window_registry: ToolRegistry) -> CopilotAgentRunner:
    """CopilotAgentRunner with lifecycle + tool window tools."""
    return CopilotAgentRunner(
        registry=tool_window_registry,
        model=get_copilot_model(),
        cli_path=get_copilot_cli_path() or None,
        github_token=get_copilot_github_token() or None,
    )


@pytest.fixture(scope="session")
def tool_window_llm_runner(tool_window_registry: ToolRegistry) -> LLMAgentRunner:
    """LLMAgentRunner with lifecycle + tool window tools."""
    return LLMAgentRunner(
        registry=tool_window_registry,
        model=get_model(),
        base_url=get_base_url(),
        api_key=os.environ.get("GITHUB_TOKEN", ""),
    )
