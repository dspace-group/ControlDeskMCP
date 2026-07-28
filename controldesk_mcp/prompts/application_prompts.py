"""MCP prompts for ControlDesk application lifecycle and window management.

Prompts registered:
  manage_application_window — arrange the ControlDesk window for automated sessions

Application-domain tools covered:
  Lifecycle:         controldesk_app_start_or_attach, controldesk_app_stop
    Window management: controldesk_app_window_manage

Note: the cross-domain session startup prompt ``start_automation_session``
(which also invokes ``controldesk_app_start_or_attach``) lives in ``session_prompts.py``.

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from controldesk_mcp.server.app import mcp

# ── Prompt — Manage Application Window ───────────────────────────────────────


@mcp.prompt(
    name="manage_application_window",
    description=(
        "Guided workflow for controlling the ControlDesk application window: "
        "check visibility, show/hide, resize, reposition, and set fullscreen. "
        "Use before running automated workflows to ensure ControlDesk is visible "
        "and correctly positioned on screen. "
        "Accepts optional position and state parameters."
    ),
)
def manage_application_window(
    window_state: str = "normal",
    fullscreen: bool = False,
) -> list[dict]:
    """Generate an application window management workflow prompt."""
    state_hint = f"Set the window state to '{window_state}'." if window_state != "normal" else ""

    return [
        {
            "role": "user",
            "content": (
                f"Configure the ControlDesk application window.\n\n"
                f"**Parameters:**\n"
                f"- Window state: {window_state}\n"
                f"- Fullscreen: {fullscreen}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_app_window_manage` with action='get_visibility' to check if "
                f"   ControlDesk is visible on screen.\n"
                f"2. If not visible: call `controldesk_app_window_manage` with action='set_visible' "
                f"   and visible=True to bring it to the foreground.\n"
                f"3. Call `controldesk_app_window_manage` with action='get_state' to inspect the "
                f"   current state (normal, minimized, maximized).\n"
                f"4. "
                + (
                    "Call `controldesk_app_window_manage` with action='set_fullscreen' and enabled=True."
                    if fullscreen
                    else (
                        "Call `controldesk_app_window_manage` with action='set_state' and "
                        f"window_state='{window_state}' to adjust the window. {state_hint}"
                    )
                )
                + "\n"
                "5. If exact placement is required: call `controldesk_app_window_manage` with "
                "   action='set_position', left, top, width, and height.\n"
                "6. Call `controldesk_app_window_manage` with action='get_state' again to confirm the final state.\n"
                "7. To close ControlDesk when done: call `controldesk_app_stop`.\n"
                "8. Report: window visibility, state, and position after configuration."
            ),
        }
    ]
