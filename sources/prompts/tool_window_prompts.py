"""MCP prompts for ControlDesk tool-window management workflows.

Prompts registered:
  manage_tool_windows — list, show, dock, and close ControlDesk tool windows

All 6 tool_window-domain tools are covered:
  tool_window_list, tool_window_check_exists, tool_window_show, tool_window_close,
  tool_window_set_dock_state, tool_window_get_state

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from sources.server.app import mcp

# ── Prompt — Manage Tool Windows ──────────────────────────────────────────────


@mcp.prompt(
    name="manage_tool_windows",
    description=(
        "Guided workflow for managing ControlDesk tool windows: "
        "list available windows, show or hide a specific window, "
        "configure its docking position, and close when done. "
        "Useful for arranging the ControlDesk UI before running automated tests. "
        "Accepts an optional window name to target a specific tool window."
    ),
)
def manage_tool_windows(
    window_name: str = "",
) -> list[dict]:
    """Generate a tool window management workflow prompt."""
    name_arg = f", name='{window_name}'" if window_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Manage ControlDesk tool windows.\n\n"
                f"**Parameters:**\n"
                f"- Window name: {window_name or '(not specified — list all first)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `tool_window_list` to see all registered tool windows and their "
                f"   current visibility and dock state.\n"
                f"2. To check whether a specific window exists: call "
                f"   `tool_window_check_exists`{name_arg}.\n"
                f"3. To show a window: call `tool_window_show`{name_arg}. "
                f"   This makes the window visible if it was hidden.\n"
                f"4. To inspect the current state of a window: call "
                f"   `tool_window_get_state`{name_arg} (returns visibility, size, position).\n"
                f"5. To change docking: call `tool_window_set_dock_state`{name_arg} with "
                f"   the desired dock location (left, right, bottom, floating, etc.).\n"
                f"6. To close a window when done: call `tool_window_close`{name_arg}.\n"
                f"7. Report: window name, final dock state, and visibility."
            ),
        }
    ]
