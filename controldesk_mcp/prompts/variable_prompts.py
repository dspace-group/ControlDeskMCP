"""MCP prompts for ControlDesk variable read/write workflows.

Prompts registered:
  read_write_variables       — find, inspect, read, optionally write, and verify variables
  discover_variables         — search, list, and inspect variables and groups
  manage_variable_descriptions — load, activate, and remove variable description files

All 18 variable-domain tools are covered across these prompts:
  Discovery:              variable_find, variable_get_info, variable_list_all,
                          variable_list_array_elements, variable_list_group_variables
  Read:                   variable_read_scalar, variable_read_array_element,
                          variable_read_curve, variable_read_map, variable_read_string
  Write:                  variable_write_scalar, variable_write_array_element,
                          variable_write_curve, variable_write_map, variable_write_string
  Variable descriptions:  variable_description_activate, variable_description_list,
                          variable_description_remove

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
        else "   Call `variable_find` with a search pattern to locate the variable, "
        "or use `variable_list_all` to browse all available variables."
    )
    write_step = (
        f"4. Write value `{write_value}` using the appropriate write tool "
        f"   (`variable_write_scalar`, `variable_write_array_element`, "
        f"   `variable_write_curve`, `variable_write_map`, or `variable_write_string`), "
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
                f"2. Call `variable_get_info` to inspect the variable's type, unit, min, max, "
                f"   and current value. Report this information.\n"
                f"3. Call the correct read tool based on the variable type:\n"
                f"   - Scalar: `variable_read_scalar`\n"
                f"   - Array element: `variable_read_array_element`\n"
                f"   - Curve (1D map): `variable_read_curve`\n"
                f"   - Map (2D): `variable_read_map`\n"
                f"   - String: `variable_read_string`\n"
                f"{write_step}\n"
                f"5. Summarise: variable path, type, current value, and write result "
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
        f"   Call `variable_find` with pattern='{search_pattern}' to locate matching " f"variables."
        if search_pattern
        else "   Call `variable_list_all` to get the complete list of available variables. "
        "Optionally use `variable_find` with a pattern to narrow the search."
    )
    group_step = (
        f"3. Call `variable_list_group_variables` for group '{group_path}' to list all "
        f"   variables within that group."
        if group_path
        else "3. Call `variable_list_group_variables` on a group path to enumerate its "
        "   members (useful for structured/hierarchical variable trees)."
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
                f"1. {search_step}\n"
                f"2. For any variable of interest, call `variable_get_info` to retrieve "
                f"   its type, dimensions, unit, min, max, and current value.\n"
                f"{group_step}\n"
                f"4. For array variables: call `variable_list_array_elements` to see all "
                f"   indexed elements (e.g., array[0], array[1], ...).\n"
                f"5. Report: list of variables found, their types, and any group structure "
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
                f"1. Call `variable_description_list` to see all currently loaded "
                f"   variable description files and their activation state.\n"
                f"2. If a specific file should be active: call "
                f"   `variable_description_activate`{file_arg}{platform_arg} to load and "
                f"   activate the description file.\n"
                f"   Alternatively, use `platform_add_variable_description` to associate "
                f"   a description with a platform at registration time.\n"
                f"3. Verify by calling `variable_list_all` — variables from the activated "
                f"   description should appear.\n"
                f"4. To remove a description that is no longer needed: call "
                f"   `variable_description_remove`.\n"
                f"5. Report: loaded description files, activation state, and variable count."
            ),
        }
    ]
