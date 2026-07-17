"""LLM product test scenarios for the application lifecycle domain.

Each ``LLMScenario`` defines:
- A natural-language prompt sent to the LLM agent
- Which tools MUST appear in the audit trail (``expected_tools``)
- Whether the tool results must be free of errors (``assert_tool_success``)

Tools used here are the 8 confirmed tools from sources/tools/application/lifecycle.py:
  start_controldesk, app_set_window_visible, app_get_window_visibility,
  app_set_window_state, app_get_window_state, app_set_window_position,
  app_set_fullscreen, stop_controldesk

NOTE: No scenario prompts the agent to call stop_controldesk — doing so would break
subsequent tests in the same session.  stop_controldesk remains in the tool registry
so the LLM knows it exists, but test prompts are designed to avoid triggering it.

Design
------
Product tests validate three things only:

  Level 1 — the agent completed without exception or timeout.
  Level 2 — every tool in ``expected_tools`` was called at least once.
  Level 3 — the last call to each expected tool returned a success result
             (no ``error_code`` field in the JSON response).

This approach scales to any number of tools without per-tool verification
code.  The MCP tool result IS the ground truth — a success envelope means the
action happened.  No independent COM reader is needed for the default case.
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
        contain an ``error_code`` field (Level 3).  Set False only for
        read-only query scenarios where you care about coverage but not
        success/failure.
    max_iterations:
        Cap on agent tool-call iterations for this scenario.
    """

    name: str
    prompt: str
    expected_tools: list[str]
    assert_tool_success: bool = True
    max_iterations: int = 15


# ── Scenario definitions ──────────────────────────────────────────────────────

APPLICATION_LIFECYCLE_SCENARIOS: list[LLMScenario] = [
    LLMScenario(
        name="start_and_report_version",
        prompt=(
            "Start ControlDesk (or attach to an already-running instance) "
            "and tell me the installed version."
        ),
        expected_tools=["start_controldesk"],
    ),
    LLMScenario(
        name="make_window_visible",
        prompt=(
            "Start ControlDesk. Make the main window visible by calling "
            "app_set_window_visible, then report whether it is visible."
        ),
        expected_tools=["start_controldesk", "app_set_window_visible"],
    ),
    LLMScenario(
        name="maximize_window",
        prompt=(
            "Start ControlDesk, make the window visible, then maximize it "
            "using app_set_window_state. Confirm the final window state."
        ),
        expected_tools=["start_controldesk", "app_set_window_state"],
    ),
    LLMScenario(
        name="restore_window_to_normal",
        prompt=(
            "Start ControlDesk and set the main window state to Normal "
            "using app_set_window_state. Then query and report the current "
            "window state using app_get_window_state."
        ),
        expected_tools=["start_controldesk", "app_set_window_state", "app_get_window_state"],
    ),
    LLMScenario(
        name="query_visibility_readonly",
        prompt=(
            "Start ControlDesk and check whether the main window is currently "
            "visible using app_get_window_visibility. Do not change the "
            "visibility — just report it."
        ),
        expected_tools=["start_controldesk", "app_get_window_visibility"],
    ),
    LLMScenario(
        name="set_window_position",
        prompt=(
            "Start ControlDesk. Ensure the window is in Normal state using "
            "app_set_window_state, then position the main window at "
            "left=100, top=50, width=1280, height=720 using app_set_window_position."
        ),
        expected_tools=["start_controldesk", "app_set_window_position"],
    ),
    LLMScenario(
        name="fullscreen_toggle",
        prompt=(
            "Start ControlDesk. Enable full-screen mode using app_set_fullscreen, "
            "then disable it. Report whether full-screen is currently active."
        ),
        expected_tools=["start_controldesk", "app_set_fullscreen"],
    ),
    LLMScenario(
        name="multi_tool_parallel_intent",
        prompt=(
            "Start ControlDesk. Call app_set_window_visible to make the window "
            "visible AND call app_set_window_state to set it to Normal. "
            "Call both tools even if you think the state is already correct. "
            "Report the final visibility and state."
        ),
        expected_tools=[
            "start_controldesk",
            "app_set_window_visible",
            "app_set_window_state",
        ],
    ),
]
