"""MCP prompts for ControlDesk instrument management workflows.

Prompts registered:
  manage_instrument_workflow — list, add, configure, connect signals, and arrange instruments

All instrument-domain tools are covered:
  instrument_list, instrument_manage, instrument_discover, instrument_signal_manage

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from sources.server.app import mcp

# ── Prompt — Manage Instrument Workflow ───────────────────────────────────────


@mcp.prompt(
    name="manage_instrument_workflow",
    description=(
        "Guided workflow for managing instruments on a ControlDesk layout: "
        "enumerate instruments and types, add, configure, move, arrange, "
        "and connect/disconnect signals. "
        "Accepts optional layout and instrument name parameters."
    ),
)
def manage_instrument_workflow(
    layout_name: str = "",
    instrument_name: str = "",
) -> list[dict]:
    """Generate an instrument management workflow prompt."""
    layout_hint = (
        f"Ensure layout '{layout_name}' is active first."
        if layout_name
        else "Ensure a layout is active first (use layout_manage(action='activate'))."
    )
    instr_arg = (
        f"instrument_name='{instrument_name}'"
        if instrument_name
        else "instrument_name='<your_instrument>'"
    )

    return [
        {
            "role": "user",
            "content": (
                f"Manage instruments on a ControlDesk layout.\n\n"
                f"**Parameters:**\n"
                f"- Layout name: {layout_name or '(not specified)'}\n"
                f"- Instrument name: {instrument_name or '(not specified — list all first)'}\n\n"
                f"**Prerequisite:** `start_controldesk` must have been called. "
                f"{layout_hint}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `instrument_list` to see all instruments on the active layout "
                f"   (name, type, position, size, main_variable).\n"
                f"2. To discover available instrument types before adding: call "
                f"   `instrument_list(list_types=True)` — returns type strings, "
                f"   category, and signal connection mode.\n"
                f"3. To add a new instrument: call `instrument_manage` with "
                f"   `action='add', instrument_type='Time Plotter', "
                f"   instrument_name='MyPlotter', x=10, y=10, width=400, height=300`.\n"
                f"4. To get detailed info (including signal connections): call "
                f"   `instrument_manage` with `action='get_info', {instr_arg}`.\n"
                f"5. To reposition or resize: call `instrument_manage` with "
                f"   `action='move', {instr_arg}, x=50, y=50, width=500, height=350`.\n"
                f"6. To set caption, colors, or border: call `instrument_manage` with "
                f"   `action='configure', {instr_arg}, caption='Speed', "
                f"   back_color='#FFFFFF', fore_color='#000000', show_border=True`.\n"
                f"7. To align or group multiple instruments: call `instrument_manage` with "
                f"   `action='arrange', instrument_names=['Inst1', 'Inst2'], "
                f"   arrange_action='align_top'`. "
                f"   Valid arrange_action values: align_top, align_bottom, align_left, "
                f"   align_right, center_horizontally, center_vertically, "
                f"   space_evenly_horizontal, space_evenly_vertical, group, ungroup.\n"
                f"8. To connect a variable/signal to an instrument: "
                f"   first call `instrument_discover` to activate `instrument_signal_manage`, "
                f"   then call `instrument_signal_manage(action='connect', {instr_arg}, "
                f"   variable_path='XCP(5ms)://Engine_Speed', signal_color='#0000FF', "
                f"   axis_index=0)`. "
                f"   Connection mode is resolved automatically by instrument type:\n"
                f"   - Simple controls (Knob, Slider, etc.): sets MainVariable directly.\n"
                f"   - Time/XY Plotter: adds a signal to a Y-axis.\n"
                f"   - variable Array: adds a row.\n"
                f"   - Table Editor: uses SubInstrument.\n"
                f"9. To disconnect a signal: call `instrument_signal_manage("
                f"   action='disconnect', {instr_arg}, "
                f"   variable_path='XCP(5ms)://Engine_Speed')`.\n"
                f"   Omit variable_path to clear all connections.\n"
                f"10. To remove an instrument: call `instrument_manage` with "
                f"    `action='remove', {instr_arg}`.\n"
                f"11. Report: final instrument state (name, type, position, signal connections)."
            ),
        }
    ]
