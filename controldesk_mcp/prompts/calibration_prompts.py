"""MCP prompts for ControlDesk calibration workflows.

Prompts registered:
  run_calibration_workflow   — activate working page, adjust parameters, apply or cancel
  proposed_calibration_flow  — guided propose → review → apply/reject cycle
  manage_calibration_data_sets — switch between working and reference data-set pages

All 11 calibration-domain tools are covered across these prompts:
  Online calibration:    calibration_start, calibration_stop, calibration_refresh_parameters
  Page management:       calibration_activate_working_page, calibration_activate_reference_page,
                         data_set_activate_working_page, data_set_activate_reference_page
  Proposed calibration:  proposed_calibration_start, proposed_calibration_stop,
                         proposed_calibration_apply, proposed_calibration_cancel

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
                f"1. Confirm the platform is connected: call `platform_get_connection_state`"
                f"{platform_arg}. If not connected, call `platform_connect`{platform_arg} first.\n"
                f"2. Call `calibration_start`{platform_arg} to enable online calibration mode.\n"
                f"3. Call `calibration_activate_working_page`{platform_arg} to switch to the "
                f"   working (RAM) copy of parameters — changes here are temporary.\n"
                f"   For data-set parameters use `data_set_activate_working_page` instead.\n"
                f"4. Call `calibration_refresh_parameters`{platform_arg} to sync the latest "
                f"   ECU parameter values into ControlDesk.\n"
                f"5. Adjust any required parameters using `variable_write_scalar` or "
                f"   `variable_write_curve` / `variable_write_map` as appropriate.\n"
                f"6. Verify changes by reading back each modified parameter.\n"
                f"7. To persist changes: call `calibration_activate_reference_page`"
                f"{platform_arg} to commit the working page to the reference page.\n"
                f"   For data-set parameters: `data_set_activate_reference_page`.\n"
                f"8. Call `calibration_stop`{platform_arg} to end the calibration session.\n"
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
                f"1. Confirm the platform is connected: call `platform_get_connection_state`"
                f"{platform_arg}.\n"
                f"2. Call `calibration_start`{platform_arg} to enable online calibration.\n"
                f"3. Call `proposed_calibration_start`{platform_arg} to open a proposal "
                f"   session — parameter changes will be staged, not applied immediately.\n"
                f"4. Write the proposed parameter values using `variable_write_scalar`, "
                f"   `variable_write_curve`, or `variable_write_map`.\n"
                f"5. Present the proposed changes to the user for review.\n"
                f"6. If the user approves: call `proposed_calibration_apply`{platform_arg}.\n"
                f"   If the user rejects: call `proposed_calibration_cancel`{platform_arg}.\n"
                f"7. Call `proposed_calibration_stop`{platform_arg} to close the session.\n"
                f"8. Call `calibration_stop`{platform_arg} to end the calibration session.\n"
                f"9. Report: proposed changes, approval decision, and final parameter values."
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
                f"1. Call `calibration_start`{platform_arg} if calibration is not active.\n"
                f"2. To switch to the editable working page:\n"
                f"   - Standard parameters: `calibration_activate_working_page`"
                f"{platform_arg}\n"
                f"   - Data-set parameters: `data_set_activate_working_page`"
                f"{platform_arg}\n"
                f"3. Make the required parameter changes via variable write tools.\n"
                f"4. To commit the working page changes back to the reference:\n"
                f"   - Standard parameters: `calibration_activate_reference_page`"
                f"{platform_arg}\n"
                f"   - Data-set parameters: `data_set_activate_reference_page`"
                f"{platform_arg}\n"
                f"5. Call `calibration_refresh_parameters`{platform_arg} to re-sync "
                f"   after page switches.\n"
                f"6. Report: current page state, parameters changed, and final values."
            ),
        }
    ]
