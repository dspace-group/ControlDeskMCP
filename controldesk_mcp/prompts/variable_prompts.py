"""MCP prompts for ControlDesk variable read/write workflows.

Prompts registered:
  read_write_variables       — find, inspect, read, optionally write, and verify variables
  discover_variables         — search, list, and inspect variables and groups
  manage_variable_descriptions — load, activate, and remove variable description files

Variable tools used across these prompts:
    Core:       controldesk_variable_find, controldesk_variable_read,
                            controldesk_variable_write
    Lazy tools: controldesk_variable_discover, controldesk_variable_list,
                            controldesk_variable_description_manage

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from controldesk_mcp.server.app import mcp

# ── Prompt — Read / Write Variables ──────────────────────────────────────────


@mcp.prompt(
    name="read_write_variables",
    description=(
        "Guided workflow for reading and writing ControlDesk variables: find, inspect, "
        "read, optionally write, and verify. "
        "Covers scalars, arrays, curves, maps, and strings. "
        "Useful for testing calibration values, signal manipulation, and variable access."
    ),
)
def read_write_variables(
    variable_path: str = "",
    write_value: str = "",
) -> list[dict]:
    """Generate a variable read/write testing workflow prompt."""
    find_step = (
        f"   The target variable path is `{variable_path}` — skip the search step."
        if variable_path
        else "   Call `controldesk_variable_find` with a search pattern to locate the variable."
    )
    write_step = (
        f"4. Write value `{write_value}` with `controldesk_variable_write` using the matching write_type, "
        f"   then read back immediately to verify the change was applied."
        if write_value
        else "4. No write value specified — perform a read-only inspection."
    )

    return [
        {
            "role": "user",
            "content": (
                f"Perform a variable read/write test in ControlDesk.\n\n"
                f"**Parameters:**\n"
                f"- Variable path: {variable_path or '(search required)'}\n"
                f"- Write value: {write_value or '(read-only)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. {find_step}\n"
                f"2. If no direct path is provided, follow resolver-first order: "
                f"instrument hint -> bounded `controldesk_variable_find` name attempts -> "
                f"`controldesk_variable_list(action='list_all')` fallback -> ranked candidate selection.\n"
                f"3. Do not ask the operator for a fully qualified path before resolver attempts finish; "
                f"if ambiguous, present the top 3-5 candidates and ask the operator to pick one.\n"
                f"4. Ignore `<COMObject <unknown>>` placeholders as a path source and preserve returned "
                f"connection paths verbatim.\n"
                f"5. Call `controldesk_variable_read` with the matching read_type to inspect the value.\n"
                f"6. Use the same variable path with `controldesk_variable_write` only when a write is required, "
                f"and enforce write safety checks (`is_writable`, init-only lock state) before writing.\n"
                f"{write_step}\n"
                f"7. Summarise: variable path, type, current value, and write result "
                f"(if applicable)."
            ),
        }
    ]


# ── Prompt — Discover Variables ───────────────────────────────────────────────


@mcp.prompt(
    name="discover_variables",
    description=(
        "Guided workflow for discovering and inspecting ControlDesk variables: "
        "search by pattern, list all variables, browse group contents, and "
        "inspect array elements. "
        "Use this to explore what variables are available before reading or writing."
    ),
)
def discover_variables(
    search_pattern: str = "",
    group_path: str = "",
) -> list[dict]:
    """Generate a variable discovery workflow prompt."""
    search_step = (
        f"   Call `controldesk_variable_find` with pattern='{search_pattern}' to locate matching variables."
        if search_pattern
        else "   Call `controldesk_variable_find` with a pattern to narrow the search."
    )
    group_step = (
        f"3. Call `controldesk_variable_list` with action='list_group_variables' for group '{group_path}'."
        if group_path
        else "3. Call `controldesk_variable_list` with action='list_all' to enumerate available variables."
    )

    return [
        {
            "role": "user",
            "content": (
                f"Explore and discover ControlDesk variables.\n\n"
                f"**Parameters:**\n"
                f"- Search pattern: {search_pattern or '(list all)'}\n"
                f"- Group path: {group_path or '(not specified)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_variable_discover` to activate variable-list tools.\n"
                f"2. {search_step}\n"
                f"3. If name lookup is weak, continue with `controldesk_variable_list(action='list_all')` "
                f"fallback before requesting manual full paths.\n"
                f"4. For any variable of interest, call `controldesk_variable_read` with the matching read_type.\n"
                f"{group_step}\n"
                f"5. For arrays, call `controldesk_variable_list` with action='list_array_elements'.\n"
                f"6. Report: list of variables found, their types, and any group structure "
                f"   discovered."
            ),
        }
    ]


# ── Prompt — Manage Variable Descriptions ────────────────────────────────────


@mcp.prompt(
    name="manage_variable_descriptions",
    description=(
        "Guided workflow for managing ControlDesk variable description files (A2L/DCM): "
        "list loaded descriptions, activate a specific file, and remove unused ones. "
        "Variable descriptions must be loaded before variables become accessible."
    ),
)
def manage_variable_descriptions(
    description_file: str = "",
    platform_name: str = "",
) -> list[dict]:
    """Generate a variable description management workflow prompt."""
    file_arg = f", file_path='{description_file}'" if description_file else ""
    platform_arg = f", platform_name='{platform_name}'" if platform_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Manage ControlDesk variable description files.\n\n"
                f"**Parameters:**\n"
                f"- Description file: {description_file or '(not specified)'}\n"
                f"- Platform: {platform_name or '(use active platform)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_variable_discover` to activate description-management tools.\n"
                f"2. Call `controldesk_variable_description_manage` with action='list'{platform_arg}.\n"
                f"3. If a description should be active, call `controldesk_variable_description_manage` "
                f"   with action='activate'{file_arg}{platform_arg}.\n"
                f"4. To remove one, call `controldesk_variable_description_manage` with action='remove'.\n"
                f"5. Report: loaded description files, activation state, and variable count."
            ),
        }
    ]
