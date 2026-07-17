"""MCP prompts for ControlDesk recorder (main recorder) workflows.

Prompts registered:
  run_recorder_main_workflow — configure the main recorder, add signals, start/stop

All 9 recorder-domain tools are covered:
  recorder_main_configure, recorder_main_add_signal, recorder_main_remove_signal,
  recorder_main_list_signals, recorder_main_start, recorder_main_stop,
  recorder_main_pause, recorder_main_resume, recorder_main_get_state

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from sources.server.app import mcp

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
                f"1. Call `recorder_main_get_state` to check the current recorder state. "
                f"   If already recording, call `recorder_main_stop` first.\n"
                f"2. Call `recorder_main_configure`{file_arg} to set the output file, "
                f"   trigger mode, and recording options.\n"
                f"3. Call `recorder_main_list_signals` to see what signals are currently "
                f"   configured for recording.\n"
                f"4. Add the required signals:\n"
                f"   - Call `recorder_main_add_signal`{signal_arg} for each signal to "
                f"     capture.\n"
                f"   - To remove unwanted signals: `recorder_main_remove_signal`.\n"
                f"5. Call `recorder_main_start` to begin recording.\n"
                f"6. During recording, call `recorder_main_pause` to temporarily suspend "
                f"   capture (data is held in buffer), then `recorder_main_resume` to "
                f"   continue.\n"
                f"7. When done, call `recorder_main_stop` to finish the recording and "
                f"   flush data to the output file.\n"
                f"8. Call `recorder_main_get_state` to confirm the recorder stopped cleanly.\n"
                f"9. Report: signals recorded, output file path, and recording duration."
            ),
        }
    ]
