"""MCP prompts for ControlDesk recorder (main recorder) workflows.

Prompts registered:
  run_recorder_main_workflow — configure the main recorder, add signals, start/stop

Recorder tools used: controldesk_recorder_main_start, controldesk_recorder_main_stop,
    controldesk_recorder_main_manage, controldesk_recorder_query,
    controldesk_recorder_signal_manage, controldesk_recorder_config_manage,
    controldesk_recorder_discover

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from controldesk_mcp.server.app import mcp

# ── Prompt — Run Recorder Main Workflow ───────────────────────────────────────


@mcp.prompt(
    name="run_recorder_main_workflow",
    description=(
        "End-to-end workflow for using the ControlDesk main recorder: "
        "configure the recorder, add signals to record, start, pause/resume, "
        "and stop recording. "
        "The main recorder is the primary data-capture component for signal recording "
        "in ControlDesk. "
        "Accepts optional signal path and output file."
    ),
)
def run_recorder_main_workflow(
    signal_path: str = "",
    output_file: str = "",
) -> list[dict]:
    """Generate a main recorder workflow prompt."""
    signal_arg = f", signal_path='{signal_path}'" if signal_path else ""
    file_arg = f", output_file='{output_file}'" if output_file else ""

    return [
        {
            "role": "user",
            "content": (
                f"Configure and run the ControlDesk main recorder.\n\n"
                f"**Parameters:**\n"
                f"- Signal: {signal_path or '(to be selected)'}\n"
                f"- Output file: {output_file or '(auto-generated)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_recorder_discover` to activate recorder query and management tools.\n"
                f"2. Call `controldesk_recorder_query` with action='get_state' to check the current recorder state. "
                f"   If already recording, call `controldesk_recorder_main_stop` first.\n"
                f"3. Call `controldesk_recorder_config_manage` with action='configure'{file_arg} to set the output file, "
                f"   trigger mode, and recording options.\n"
                f"4. Call `controldesk_recorder_signal_manage` with action='list' to see configured "
                f"   configured for recording.\n"
                f"5. Add the required signals:\n"
                f"   - Call `controldesk_recorder_signal_manage` with action='add'{signal_arg} for each signal to "
                f"     capture.\n"
                f"   - To remove unwanted signals, use action='remove'.\n"
                f"6. Call `controldesk_recorder_main_start` to begin recording.\n"
                f"7. During recording, call `controldesk_recorder_main_manage` with action='pause' or action='resume'.\n"
                f"8. When done, call `controldesk_recorder_main_stop` to finish the recording and "
                f"   flush data to the output file.\n"
                f"9. Call `controldesk_recorder_query` with action='get_state' to confirm it stopped.\n"
                f"10. Report: signals recorded, output file path, and recording duration."
            ),
        }
    ]
