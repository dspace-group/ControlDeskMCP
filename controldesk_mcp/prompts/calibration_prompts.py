"""MCP prompts for ControlDesk calibration workflows.

Prompts registered:
  run_calibration_workflow   — activate working page, adjust parameters, apply or cancel
  proposed_calibration_flow  — guided propose → review → apply/reject cycle
  manage_calibration_data_sets — switch between working and reference data-set pages

Calibration tools used across these prompts:
    Lifecycle:    controldesk_calibration_start, controldesk_calibration_stop,
                                controldesk_calibration_discover, controldesk_calibration_query
    Page tools:   controldesk_calibration_page_manage,
                                controldesk_variable_discover, controldesk_variable_data_set_manage
    Proposals:    controldesk_proposed_calibration_manage

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from controldesk_mcp.server.app import mcp

# ── Prompt — Run Calibration Workflow ─────────────────────────────────────────


@mcp.prompt(
    name="run_calibration_workflow",
    description=(
        "Step-by-step guide for running a ControlDesk online calibration session: "
        "start calibration, switch pages, refresh parameters, and stop. "
        "Accepts an optional platform name to scope the workflow."
    ),
)
def run_calibration_workflow(
    platform_name: str = "",
) -> list[dict]:
    """Generate an online calibration workflow prompt."""
    platform_arg = f", platform_name='{platform_name}'" if platform_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Run a ControlDesk online calibration session.\n\n"
                f"**Parameters:**\n"
                f"- Platform: {platform_name or '(use active/default platform)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_platform_query` with action='get_connection_state'"
                f"{platform_arg}. If not connected, call `controldesk_platform_connect`{platform_arg} first.\n"
                f"2. Call `controldesk_calibration_start`{platform_arg} to enable online calibration mode.\n"
                f"3. Call `controldesk_calibration_discover` to activate calibration page tools.\n"
                f"4. Call `controldesk_calibration_page_manage` with action='copy_reference_to_working'"
                f"{platform_arg} when a reference-page copy is required.\n"
                f"5. Use `controldesk_variable_write` with the matching write_type to adjust parameters.\n"
                f"6. Verify changes using `controldesk_variable_read` with the matching read_type.\n"
                f"7. To persist changes, call `controldesk_calibration_page_manage` with "
                f"   action='copy_working_to_reference'{platform_arg}.\n"
                f"8. Call `controldesk_calibration_stop`{platform_arg} to end the calibration session.\n"
                f"9. Report: parameters modified, final values, and calibration state."
            ),
        }
    ]


# ── Prompt — Proposed Calibration Flow ───────────────────────────────────────


@mcp.prompt(
    name="proposed_calibration_flow",
    description=(
        "Guided workflow for the ControlDesk Proposed Calibration feature: "
        "start the proposal session, let the model suggest changes, then apply or cancel. "
        "Use when coordinating AI-suggested parameter updates with human review."
    ),
)
def proposed_calibration_flow(
    platform_name: str = "",
) -> list[dict]:
    """Generate a proposed calibration workflow prompt."""
    platform_arg = f", platform_name='{platform_name}'" if platform_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Run a Proposed Calibration session in ControlDesk.\n\n"
                f"**Parameters:**\n"
                f"- Platform: {platform_name or '(use active/default platform)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Confirm the platform is connected: call `controldesk_platform_query` with action='get_connection_state'"
                f"{platform_arg}.\n"
                f"2. Call `controldesk_calibration_start`{platform_arg} to enable online calibration.\n"
                f"3. Call `controldesk_calibration_discover` to activate proposed-calibration tools.\n"
                f"4. Call `controldesk_proposed_calibration_manage` with action='start' to open a proposal "
                f"   session — parameter changes will be staged, not applied immediately.\n"
                f"5. Write proposed values with `controldesk_variable_write`.\n"
                f"6. Present the proposed changes to the user for review.\n"
                f"7. If approved, call `controldesk_proposed_calibration_manage` with action='apply'; "
                f"otherwise use action='cancel'.\n"
                f"8. Call `controldesk_proposed_calibration_manage` with action='stop'.\n"
                f"9. Call `controldesk_calibration_stop`{platform_arg} to end the calibration session.\n"
                f"10. Report: proposed changes, approval decision, and final parameter values."
            ),
        }
    ]


# ── Prompt — Manage Calibration Data Sets ────────────────────────────────────


@mcp.prompt(
    name="manage_calibration_data_sets",
    description=(
        "Guided workflow for switching between working and reference data-set pages "
        "in ControlDesk calibration. "
        "Data sets hold ECU parameter values; the working page is editable while "
        "the reference page holds the last committed baseline."
    ),
)
def manage_calibration_data_sets(
    platform_name: str = "",
) -> list[dict]:
    """Generate a calibration data-set management workflow prompt."""
    platform_arg = f", platform_name='{platform_name}'" if platform_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Manage ControlDesk calibration data-set pages.\n\n"
                f"**Parameters:**\n"
                f"- Platform: {platform_name or '(use active/default platform)'}\n\n"
                f"**Page types:**\n"
                f"- **Working page**: RAM copy — editable, changes are temporary.\n"
                f"- **Reference page**: Flash/ROM baseline — persisted values.\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_calibration_start`{platform_arg} if calibration is not active.\n"
                f"2. Call `controldesk_variable_discover` to activate data-set page tools.\n"
                f"3. To activate the editable working page, call `controldesk_variable_data_set_manage` "
                f"with action='activate_working_page'.\n"
                f"4. Make the required parameter changes via `controldesk_variable_write`.\n"
                f"5. To activate the reference page, call `controldesk_variable_data_set_manage` "
                f"with action='activate_reference_page'.\n"
                f"6. Report: current page state, parameters changed, and final values."
            ),
        }
    ]
