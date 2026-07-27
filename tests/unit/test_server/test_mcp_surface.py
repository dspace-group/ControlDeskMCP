"""MCP surface snapshot test — asserts the exact registered tools, resources, and prompts.

This test catches undocumented inventory drift: any tool, resource, or prompt that is
added or removed will cause it to fail, enforcing that docs and CI stay in sync.

Run without a live ControlDesk installation; no COM connection is made.
"""

from __future__ import annotations

import pytest

# ── Expected inventory (generated from the live server; update intentionally) ──

EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        "app_discover",
        "app_get_logs",
        "bus_logger_configure",
        "bus_logger_create",
        "bus_logger_manage",
        "bus_logging_discover",
        "bus_monitor_configure",
        "bus_monitor_create",
        "bus_monitor_discover",
        "bus_monitor_manage",
        "bus_replay_configure",
        "bus_replay_create",
        "bus_replay_discover",
        "bus_replay_manage",
        "calibration_discover",
        "calibration_manage",
        "calibration_start",
        "calibration_stop",
        "instrument_discover",
        "instrument_list",
        "instrument_manage",
        "instrument_query",
        "layout_discover",
        "layout_list",
        "layout_manage",
        "layout_query",
        "measurement_discover",
        "measurement_manage",
        "measurement_start",
        "measurement_stop",
        "platform_connect",
        "platform_disconnect",
        "platform_discover",
        "platform_manage",
        "project_discover",
        "project_list_recent",
        "project_open",
        "recorder_discover",
        "recorder_main_manage",
        "recorder_main_start",
        "recorder_main_stop",
        "start_controldesk",
        "stop_controldesk",
        "tool_window_discover",
        "tool_window_list",
        "tool_window_manage",
        "tool_window_show",
        "variable_discover",
        "variable_find",
        "variable_read",
        "variable_write",
    }
)

EXPECTED_RESOURCE_URIS: frozenset[str] = frozenset(
    {
        "controldesk://server/connection-status",
        "controldesk://server/domains",
        "controldesk://server/info",
        "controldesk://server/tool-catalog",
        "controldesk://server/tool-groups",
    }
)

EXPECTED_RESOURCE_TEMPLATES: frozenset[str] = frozenset(
    {
        "controldesk://tools/{domain}",
        "controldesk://tools/{domain}/{group}",
    }
)

EXPECTED_PROMPTS: frozenset[str] = frozenset(
    {
        "add_measurement_bookmark",
        "configure_bus_logging",
        "configure_measurement_triggers",
        "diagnose_connection",
        "discover_variables",
        "export_experiment",
        "manage_application_window",
        "manage_bus_filters",
        "manage_calibration_data_sets",
        "manage_data_loggers",
        "manage_experiments",
        "manage_instrument_workflow",
        "manage_layout_workflow",
        "manage_project_roots",
        "manage_project_workflow",
        "manage_tool_windows",
        "manage_variable_descriptions",
        "proposed_calibration_flow",
        "read_write_variables",
        "replay_bus_data",
        "run_bus_monitor",
        "run_calibration_workflow",
        "run_measurement_workflow",
        "run_recorder_main_workflow",
        "start_automation_session",
    }
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def registered_mcp():
    """Import and return the fully populated MCPServer instance.

    Importing the registry triggers all @mcp.tool, @mcp.resource, and
    @mcp.prompt decorators without starting the server or opening a COM
    connection.
    """
    import controldesk_mcp.server.registry  # noqa: F401 — side-effect import
    from controldesk_mcp.server.app import mcp

    return mcp


# ── Tool surface ──────────────────────────────────────────────────────────────


class TestToolSurface:
    def test_exact_tool_count(self, registered_mcp) -> None:
        tools = {t.name for t in registered_mcp._tool_manager.list_tools()}
        assert len(tools) == len(EXPECTED_TOOLS), (
            f"Tool count mismatch: got {len(tools)}, expected {len(EXPECTED_TOOLS)}.\n"
            f"  Added:   {sorted(tools - EXPECTED_TOOLS)}\n"
            f"  Removed: {sorted(EXPECTED_TOOLS - tools)}"
        )

    def test_exact_tool_names(self, registered_mcp) -> None:
        tools = {t.name for t in registered_mcp._tool_manager.list_tools()}
        added = tools - EXPECTED_TOOLS
        removed = EXPECTED_TOOLS - tools
        assert not added and not removed, (
            f"Tool inventory drift detected.\n"
            f"  Added (not in snapshot):   {sorted(added)}\n"
            f"  Removed (missing from MCP): {sorted(removed)}"
        )


# ── Resource surface ──────────────────────────────────────────────────────────


class TestResourceSurface:
    def test_exact_static_resource_uris(self, registered_mcp) -> None:
        uris = {str(r.uri) for r in registered_mcp._resource_manager.list_resources()}
        added = uris - EXPECTED_RESOURCE_URIS
        removed = EXPECTED_RESOURCE_URIS - uris
        assert not added and not removed, (
            f"Static resource drift detected.\n  Added:   {sorted(added)}\n  Removed: {sorted(removed)}"
        )

    def test_exact_resource_templates(self, registered_mcp) -> None:
        templates = {t.uri_template for t in registered_mcp._resource_manager.list_templates()}
        added = templates - EXPECTED_RESOURCE_TEMPLATES
        removed = EXPECTED_RESOURCE_TEMPLATES - templates
        assert not added and not removed, (
            f"Resource template drift detected.\n  Added:   {sorted(added)}\n  Removed: {sorted(removed)}"
        )


# ── Prompt surface ────────────────────────────────────────────────────────────


class TestPromptSurface:
    def test_exact_prompt_count(self, registered_mcp) -> None:
        prompts = {p.name for p in registered_mcp._prompt_manager.list_prompts()}
        assert len(prompts) == len(EXPECTED_PROMPTS), (
            f"Prompt count mismatch: got {len(prompts)}, expected {len(EXPECTED_PROMPTS)}.\n"
            f"  Added:   {sorted(prompts - EXPECTED_PROMPTS)}\n"
            f"  Removed: {sorted(EXPECTED_PROMPTS - prompts)}"
        )

    def test_exact_prompt_names(self, registered_mcp) -> None:
        prompts = {p.name for p in registered_mcp._prompt_manager.list_prompts()}
        added = prompts - EXPECTED_PROMPTS
        removed = EXPECTED_PROMPTS - prompts
        assert not added and not removed, (
            f"Prompt inventory drift detected.\n"
            f"  Added (not in snapshot):     {sorted(added)}\n"
            f"  Removed (missing from MCP): {sorted(removed)}"
        )
