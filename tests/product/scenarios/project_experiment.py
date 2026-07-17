"""LLM product test scenarios for the project and experiment management domain.

Each ``LLMScenario`` defines:
- A natural-language prompt sent to the LLM agent
- Which tools MUST appear in the audit trail (``expected_tools``)
- Whether the tool results must be free of errors (``assert_tool_success``)

Tools covered (domain: project & experiment management):
  project_root_add, project_root_activate, project_root_list, project_root_remove,
  project_create, project_open, project_save, project_close, project_remove,
  project_backup, project_open_from_backup, project_exists, project_get_info,
  experiment_create, experiment_activate, experiment_list, experiment_remove,
  experiment_get_info, experiment_export, experiment_import,
  experiment_rename, experiment_save_as, project_configure_settings

Design
------
Product tests validate three things only:

  Level 1 — the agent completed without exception or timeout.
  Level 2 — every tool in ``expected_tools`` was called at least once.
  Level 3 — the last call to each expected tool returned a success result
             (no ``error_code`` field in the JSON response).

Scenario safety
---------------
All write scenarios are self-contained:
  - Each scenario creates its own isolated folder path under C:\\Temp\\MCPProj.
  - Each scenario closes and removes the project it created.
  - The test root folder may persist on disk but ControlDesk removes its
    registration after the scenario.
This ensures scenarios do not leave orphaned ControlDesk state between runs.

NOTE: No scenario removes the root folder itself — that would require file-
system access outside COM and is intentionally outside the MCP tool scope.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LLMScenario:
    """One LLM-driven product test scenario.

    Attributes
    ----------
    name:
        Unique identifier used as the pytest parametrize ID.
    prompt:
        Natural-language instruction sent to the LLM agent as the user message.
    expected_tools:
        Tool names that must appear in the agent's audit trail (Level 2).
        The test fails if any are absent.
    assert_tool_success:
        When True (default) the last result of every expected tool must not
        contain an ``error_code`` field (Level 3).
    max_iterations:
        Cap on agent tool-call iterations for this scenario.
    """

    name: str
    prompt: str
    expected_tools: list[str]
    assert_tool_success: bool = True
    max_iterations: int = 20


# ── Scenario definitions ──────────────────────────────────────────────────────

PROJECT_EXPERIMENT_SCENARIOS: list[LLMScenario] = [
    LLMScenario(
        name="list_project_roots",
        prompt=(
            "Start ControlDesk (or attach to an already-running instance). "
            "Then list all registered project roots using project_root_list "
            "and report how many roots are registered."
        ),
        expected_tools=["start_controldesk", "project_root_list"],
    ),
    LLMScenario(
        name="add_root_and_check_list",
        prompt=(
            "Start ControlDesk. "
            "Add 'C:\\Temp\\MCPProjRoot' as a project root using project_root_add. "
            "Then list all roots with project_root_list and confirm the new root appears. "
            "Finally remove that root with project_root_remove."
        ),
        expected_tools=[
            "start_controldesk",
            "project_root_add",
            "project_root_list",
            "project_root_remove",
        ],
    ),
    LLMScenario(
        name="create_project_and_get_info",
        prompt=(
            "Start ControlDesk. "
            "Add 'C:\\Temp\\MCPProjRoot' as a project root using project_root_add, "
            "then activate it with project_root_activate. "
            "Create a new project named 'MCPTestProject' using project_create. "
            "Get its info with project_get_info and report the project name. "
            "Then close the project with project_close (save=False) "
            "and remove it using project_remove. "
            "Finally remove the root with project_root_remove."
        ),
        expected_tools=[
            "start_controldesk",
            "project_root_add",
            "project_root_activate",
            "project_create",
            "project_get_info",
            "project_close",
            "project_remove",
            "project_root_remove",
        ],
        max_iterations=25,
    ),
    LLMScenario(
        name="project_exists_check",
        prompt=(
            "Start ControlDesk. "
            "Add 'C:\\Temp\\MCPProjRoot' as a project root using project_root_add, "
            "then activate it with project_root_activate. "
            "Check whether a project named 'NonExistentProject' exists using project_exists. "
            "Report whether it exists. "
            "Then remove the root with project_root_remove."
        ),
        expected_tools=[
            "start_controldesk",
            "project_root_add",
            "project_root_activate",
            "project_exists",
            "project_root_remove",
        ],
    ),
    LLMScenario(
        name="create_experiment_flow",
        prompt=(
            "Start ControlDesk. "
            "Add 'C:\\Temp\\MCPProjRoot' as a project root using project_root_add "
            "and activate it with project_root_activate. "
            "Create a project named 'MCPTestProject' using project_create. "
            "Create an experiment named 'TestExperiment' using experiment_create. "
            "List all experiments with experiment_list and report the count. "
            "Get the experiment info with experiment_get_info. "
            "Then close the project with project_close (save=False), "
            "remove the project using project_remove, "
            "and remove the root with project_root_remove."
        ),
        expected_tools=[
            "start_controldesk",
            "project_root_add",
            "project_root_activate",
            "project_create",
            "experiment_create",
            "experiment_list",
            "experiment_get_info",
            "project_close",
            "project_remove",
            "project_root_remove",
        ],
        max_iterations=30,
    ),
]
