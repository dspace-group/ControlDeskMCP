"""MCP prompts for ControlDesk layout management workflows.

Prompts registered:
  manage_layout_workflow — list, create/open, configure, and export/import layouts

All layout-domain tools are covered:
  layout_list, layout_manage, layout_discover, layout_io_manage

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from sources.server.app import mcp

# ── Prompt — Manage Layout Workflow ───────────────────────────────────────────


@mcp.prompt(
    name="manage_layout_workflow",
    description=(
        "Guided workflow for managing ControlDesk layouts: "
        "enumerate layouts, create, open, configure, save, close, activate, "
        "and perform I/O operations (export/import layouts and connection files). "
        "Accepts an optional layout name to target a specific layout."
    ),
)
def manage_layout_workflow(
    layout_name: str = "",
) -> list[dict]:
    """Generate a layout management workflow prompt."""
    name_arg = f"name='{layout_name}'" if layout_name else "name='<your_layout>'"

    return [
        {
            "role": "user",
            "content": (
                f"Manage ControlDesk layouts.\n\n"
                f"**Parameters:**\n"
                f"- Layout name: {layout_name or '(not specified — list all first)'}\n\n"
                f"**Prerequisite:** `start_controldesk` must have been called and an "
                f"experiment must be open.\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `layout_list` to see all layouts in the active experiment "
                f"   (name, file path, open/active state, editing mode).\n"
                f"2. To create a new layout: call `layout_manage` with "
                f"   `action='create', {name_arg}`.\n"
                f"3. To open an existing layout: call `layout_manage` with "
                f"   `action='open', {name_arg}`.\n"
                f"4. To make a layout active (bring to foreground): call `layout_manage` with "
                f"   `action='activate', {name_arg}`.\n"
                f"5. To set the editing mode (Design / Runtime / Hybrid): call `layout_manage` "
                f"   with `action='configure', {name_arg}, editing_mode='Runtime'`.\n"
                f"6. To get full metadata of a layout: call `layout_manage` with "
                f"   `action='get_info', {name_arg}`.\n"
                f"7. To save a layout: call `layout_manage` with `action='save', {name_arg}`.\n"
                f"8. To close a layout: call `layout_manage` with "
                f"   `action='close', {name_arg}, save_before_close=True`.\n"
                f"9. For export/import operations (layouts and connection files): "
                f"   first call `layout_discover` to activate the `layout_io_manage` tool, "
                f"   then:\n"
                f"   - Export active layout: `layout_io_manage(action='export', "
                f"     export_path='C:/exports/my_layout.lax')`\n"
                f"   - Import layout: `layout_io_manage(action='import', "
                f"     import_path='C:/exports/my_layout.lax')`\n"
                f"   - Export connection file: `layout_io_manage("
                f"     action='export_connection_file', "
                f"     connection_file_path='C:/exports/connections.cdx')`\n"
                f"   - Import connection file: `layout_io_manage("
                f"     action='import_connection_file', "
                f"     connection_file_path='C:/exports/connections.cdx')`\n"
                f"10. Report: final layout state (name, is_open, is_active, editing_mode)."
            ),
        }
    ]
