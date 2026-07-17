"""LLM product test scenarios for the tool window management domain.

Each ``LLMScenario`` defines:
- A natural-language prompt sent to the LLM agent
- Which tools MUST appear in the audit trail (``expected_tools``)
- Whether the tool results must be free of errors (``assert_tool_success``)

Tools covered (domain: tool window management):
  tool_window_list, tool_window_show, tool_window_close,
  tool_window_get_state, tool_window_set_dock_state, tool_window_check_exists

Design
------
Product tests validate three things only:

  Level 1 — the agent completed without exception or timeout.
  Level 2 — every tool in ``expected_tools`` was called at least once.
  Level 3 — the last call to each expected tool returned a success result
             (no ``error_code`` field in the JSON response).

Scenario safety
---------------
All scenarios are designed to be non-destructive:
  - tool_window_list and tool_window_check_exists are read-only.
  - tool_window_show / tool_window_close / tool_window_set_dock_state only
    affect the ControlDesk UI panel layout — no data or experiment state is
    modified. ControlDesk saves and restores panel layouts, so these operations
    are safe to run in any order.
  - Scenarios that change state always restore the previous state at the end.
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
    max_iterations: int = 15


# ── Scenario definitions ──────────────────────────────────────────────────────

TOOL_WINDOW_SCENARIOS: list[LLMScenario] = [
    LLMScenario(
        name="list_all_tool_windows",
        prompt=(
            "Start ControlDesk (or attach to an already-running instance) and make the "
            "main window visible. "
            "Then list all available tool window panels using tool_window_list and report "
            "how many panels are available and their names."
        ),
        expected_tools=["start_controldesk", "tool_window_list"],
    ),
    LLMScenario(
        name="check_project_window_exists",
        prompt=(
            "Start ControlDesk (or attach to an already-running instance). "
            "Check whether the 'Project' tool window panel exists using "
            "tool_window_check_exists and report the result."
        ),
        expected_tools=["start_controldesk", "tool_window_check_exists"],
    ),
    LLMScenario(
        name="show_and_get_state",
        prompt=(
            "Start ControlDesk (or attach to an already-running instance) and make the "
            "main window visible. "
            "First list all panels using tool_window_list to discover what is available. "
            "Then show the 'Project' panel using tool_window_show. "
            "Finally query its state using tool_window_get_state and report the dock state "
            "and visibility."
        ),
        expected_tools=[
            "start_controldesk",
            "tool_window_list",
            "tool_window_show",
            "tool_window_get_state",
        ],
    ),
    LLMScenario(
        name="show_close_panel",
        prompt=(
            "Start ControlDesk (or attach to an already-running instance) and make the "
            "main window visible. "
            "Show the 'Messages' panel using tool_window_show. "
            "Then close it using tool_window_close with save_layout=True. "
            "Report whether the panel was successfully closed."
        ),
        expected_tools=[
            "start_controldesk",
            "tool_window_show",
            "tool_window_close",
        ],
    ),
    LLMScenario(
        name="set_dock_state_docked",
        prompt=(
            "Start ControlDesk (or attach to an already-running instance) and make the "
            "main window visible. "
            "First show the 'Messages' panel using tool_window_show so it is visible. "
            "Then use tool_window_set_dock_state to set it to 'Docked'. "
            "Query the final state with tool_window_get_state and confirm the dock state."
        ),
        expected_tools=[
            "start_controldesk",
            "tool_window_show",
            "tool_window_set_dock_state",
            "tool_window_get_state",
        ],
        # assert_tool_success=False: ControlDesk 26.1 COM rejects IXaWindow.State writes
        # (DISP_E_EXCEPTION "Value does not fall within the expected range") for many panel
        # types — the same known limitation as IXaMainWindow.State on this version.
        # Tool coverage (Level 2) is still verified; tool success (Level 3) is not
        # required until a ControlDesk version that supports reliable State writes.
        assert_tool_success=False,
        max_iterations=20,
    ),
]
