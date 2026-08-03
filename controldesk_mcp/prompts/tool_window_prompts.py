"""MCP prompts for ControlDesk tool-window management workflows.

Prompts registered:
  manage_tool_windows — list, show, dock, and close ControlDesk tool windows

Tool-window tools used: controldesk_tool_window_list, controldesk_tool_window_show,
    controldesk_tool_window_manage, controldesk_tool_window_query, controldesk_tool_window_discover

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from controldesk_mcp.server.app import mcp

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
                f"1. Call `controldesk_tool_window_list` to see all registered tool windows and their "
                f"   current visibility and dock state.\n"
                f"2. Call `controldesk_tool_window_discover` to activate query and management tools.\n"
                f"3. To check whether a specific window exists: call "
                f"   `controldesk_tool_window_query` with action='check_exists'{name_arg}.\n"
                f"4. To show a window: call `controldesk_tool_window_show`{name_arg}. "
                f"   This makes the window visible if it was hidden.\n"
                f"5. To inspect state: call `controldesk_tool_window_query` with action='get_state'{name_arg}.\n"
                f"6. To change docking: call `controldesk_tool_window_manage` with "
                f"   action='set_dock_state'{name_arg} and "
                f"   the desired dock location (left, right, bottom, floating, etc.).\n"
                f"7. To close a window: call `controldesk_tool_window_manage` with action='close'{name_arg}.\n"
                f"8. Report: window name, final dock state, and visibility."
            ),
        }
    ]
