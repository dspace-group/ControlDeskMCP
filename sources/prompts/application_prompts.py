"""MCP prompts for ControlDesk application lifecycle and window management.

Prompts registered:
  manage_application_window — arrange the ControlDesk window for automated sessions

All 8 application-domain tools are covered:
  Lifecycle:         start_controldesk, stop_controldesk
  Window management: app_get_window_state, app_get_window_visibility,
                     app_set_window_visible, app_set_window_state,
                     app_set_window_position, app_set_fullscreen

Note: the cross-domain session startup prompt ``start_automation_session``
(which also invokes ``start_controldesk``) lives in ``session_prompts.py``.

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from sources.server.app import mcp

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
                f"1. Call `app_get_window_visibility` to check if ControlDesk is currently "
                f"   visible on screen.\n"
                f"2. If not visible: call `app_set_window_visible` with visible=True to "
                f"   bring it to the foreground.\n"
                f"3. Call `app_get_window_state` to inspect the current state "
                f"   (normal, minimized, maximized).\n"
                f"4. "
                + (
                    "Call `app_set_fullscreen` with enabled=True to maximize "
                    "ControlDesk to full screen."
                    if fullscreen
                    else f"Call `app_set_window_state` with state='{window_state}' to "
                    f"adjust the window. {state_hint}"
                )
                + "\n"
                "5. If exact placement is required: call `app_set_window_position` with "
                "   x, y, width, and height to position ControlDesk precisely.\n"
                "6. Call `app_get_window_state` again to confirm the final state.\n"
                "7. To close ControlDesk when done: call `stop_controldesk`.\n"
                "8. Report: window visibility, state, and position after configuration."
            ),
        }
    ]
