"""Unit tests for controldesk_mcp.resources.domain_resources.

Tests cover:
  get_domain_list()         — returns all known domains including 'experiment'
  get_domain_tools()        — returns filtered tool list for a domain, or empty with hint
  get_tool_group_hierarchy()— returns domain→group→[tools] catalog
  get_group_tools()         — returns tools for a domain/group combination
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_tool(name: str, description: str = "", meta: dict | None = None) -> MagicMock:
    t = MagicMock()
    t.name = name
    t.description = description
    t.meta = meta
    return t


_SAMPLE_TOOLS = [
    _make_tool("controldesk_app_start_or_attach", "Start or attach ControlDesk", {"domain": "application", "group": "lifecycle"}),
    _make_tool("controldesk_app_stop", "Quit ControlDesk", {"domain": "application", "group": "lifecycle"}),
    _make_tool("controldesk_measurement_start", "Start measurement", {"domain": "measurement", "group": "recording"}),
    _make_tool("controldesk_measurement_stop", "Stop measurement", {"domain": "measurement", "group": "recording"}),
    _make_tool("controldesk_measurement_raster_manage", "Manage rasters", {"domain": "measurement", "group": "raster_management"}),
    _make_tool("controldesk_platform_connect", "Connect a platform", {"domain": "platform", "group": "connectivity"}),
    _make_tool("controldesk_platform_query", "Query platforms", {"domain": "platform", "group": "configuration"}),
    _make_tool("controldesk_variable_read", "Read a variable", {"domain": "variable", "group": "read"}),
    _make_tool("controldesk_bus_logger_manage", "Manage bus logger", {"domain": "bus_logging", "group": "logger_management"}),
    _make_tool("controldesk_bus_filter_create", "Create bus filter", {"domain": "bus_logging", "group": "filter_management"}),
    _make_tool("controldesk_bus_replay_manage", "Manage bus replay", {"domain": "bus_replay", "group": "replay_management"}),
    _make_tool("controldesk_project_experiment_manage", "Manage experiment", {"domain": "project", "group": "experiment_management"}),
    _make_tool("controldesk_project_manage", "Manage project", {"domain": "project", "group": "project_management"}),
    _make_tool("health", "Health check"),
]

_TAGGED_TOOLS = [
    _make_tool(
        "controldesk_project_experiment_manage",
        "Create experiment",
        meta={"domain": "project", "group": "experiment_management"},
    ),
    _make_tool(
        "controldesk_project_root_manage",
        "Manage project roots",
        meta={"domain": "project", "group": "project_roots"},
    ),
    _make_tool(
        "controldesk_measurement_start",
        "Start measurement",
        meta={"domain": "measurement", "group": "recording"},
    ),
    _make_tool("health", "Health", meta={"domain": "server", "group": "bootstrap"}),
]


# ── get_domain_list ───────────────────────────────────────────────────────────


class TestGetDomainList:
    def test_returns_json_string(self) -> None:
        from controldesk_mcp.resources.domain_resources import get_domain_list

        result = get_domain_list()
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_contains_known_domains(self) -> None:
        from controldesk_mcp.resources.domain_resources import get_domain_list

        data = json.loads(get_domain_list())
        domains = data["domains"]
        for expected in (
            "application",
            "measurement",
            "platform",
            "variable",
            "calibration",
            "bus_logging",
            "bus_monitor",
            "bus_replay",
            "project",
            "recorder",
            "tool_window",
        ):
            assert expected in domains

    def test_experiment_is_own_domain(self) -> None:
        from controldesk_mcp.resources.domain_resources import get_domain_list

        data = json.loads(get_domain_list())
        assert "experiment" in data["domains"]

    def test_domain_count_matches_list(self) -> None:
        from controldesk_mcp.resources.domain_resources import get_domain_list

        data = json.loads(get_domain_list())
        assert data["count"] == len(data["domains"])

    def test_includes_uri_template(self) -> None:
        from controldesk_mcp.resources.domain_resources import get_domain_list

        data = json.loads(get_domain_list())
        assert "uri_template" in data
        assert "{domain}" in data["uri_template"]

    def test_domains_are_sorted(self) -> None:
        from controldesk_mcp.resources.domain_resources import get_domain_list

        data = json.loads(get_domain_list())
        assert data["domains"] == sorted(data["domains"])


# ── get_domain_tools ──────────────────────────────────────────────────────────


class TestGetDomainTools:
    def _call(self, domain: str) -> dict:
        with patch(
            "controldesk_mcp.resources.domain_resources.mcp._tool_manager.list_tools",
            return_value=_SAMPLE_TOOLS,
        ):
            from controldesk_mcp.resources.domain_resources import get_domain_tools

            return json.loads(get_domain_tools(domain))

    def test_application_domain_returns_app_tools(self) -> None:
        data = self._call("application")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_app_start_or_attach" in names
        assert "controldesk_app_stop" in names

    def test_application_domain_excludes_other_tools(self) -> None:
        data = self._call("application")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_measurement_start" not in names
        assert "controldesk_platform_connect" not in names

    def test_measurement_domain_returns_measurement_tools(self) -> None:
        data = self._call("measurement")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_measurement_start" in names
        assert "controldesk_measurement_stop" in names
        assert "controldesk_measurement_raster_manage" in names

    def test_platform_domain_returns_platform_tools(self) -> None:
        data = self._call("platform")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_platform_connect" in names
        assert "controldesk_platform_query" in names

    def test_unknown_domain_returns_empty_list(self) -> None:
        data = self._call("nonexistent_domain")
        assert data["count"] == 0
        assert data["tools"] == []
        assert "hint" in data

    def test_unknown_domain_hint_lists_known_domains(self) -> None:
        data = self._call("nonexistent_domain")
        assert "nonexistent_domain" in data["hint"]

    def test_tools_sorted_alphabetically(self) -> None:
        data = self._call("application")
        names = [t["name"] for t in data["tools"]]
        assert names == sorted(names)

    def test_count_matches_tool_list_length(self) -> None:
        data = self._call("measurement")
        assert data["count"] == len(data["tools"])

    def test_bus_logging_includes_filter_tools(self) -> None:
        data = self._call("bus_logging")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_bus_filter_create" in names
        assert "controldesk_bus_logger_manage" in names

    def test_bus_logging_includes_discovery_tools_by_metadata(self) -> None:
        tools = [
            _make_tool(
                "controldesk_bus_logging_discover",
                "Discover bus logging tools",
                {"domain": "bus_logging", "group": "logger_management"},
            )
        ]
        with patch("controldesk_mcp.resources.domain_resources.mcp._tool_manager.list_tools", return_value=tools):
            from controldesk_mcp.resources.domain_resources import get_domain_tools

            data = json.loads(get_domain_tools("bus_logging"))

        assert data["tools"][0]["name"] == "controldesk_bus_logging_discover"

    def test_bus_replay_does_not_include_filter_tools(self) -> None:
        data = self._call("bus_replay")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_bus_filter_create" not in names
        assert "controldesk_bus_replay_manage" in names

    def test_experiment_domain_returns_experiment_tools(self) -> None:
        data = self._call("experiment")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_project_experiment_manage" in names

    def test_project_domain_excludes_experiment_tools(self) -> None:
        data = self._call("project")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_project_manage" in names
        assert "controldesk_project_experiment_manage" not in names


# ── get_tool_group_hierarchy ──────────────────────────────────────────────────


class TestGetToolGroupHierarchy:
    def _call(self) -> dict:
        with patch(
            "controldesk_mcp.resources.domain_resources.mcp._tool_manager.list_tools",
            return_value=_TAGGED_TOOLS,
        ):
            from controldesk_mcp.resources.domain_resources import get_tool_group_hierarchy

            return json.loads(get_tool_group_hierarchy())

    def test_returns_json_with_domains_key(self) -> None:
        data = self._call()
        assert "domains" in data

    def test_includes_total_tools_count(self) -> None:
        data = self._call()
        assert "total_tools" in data
        assert data["total_tools"] == len(_TAGGED_TOOLS)

    def test_project_domain_has_experiment_management_group(self) -> None:
        data = self._call()
        assert "project" in data["domains"]
        assert "experiment_management" in data["domains"]["project"]

    def test_experiment_management_group_contains_experiment_create(self) -> None:
        data = self._call()
        tools = data["domains"]["project"]["experiment_management"]["tools"]
        assert "controldesk_project_experiment_manage" in tools

    def test_project_roots_group_present(self) -> None:
        data = self._call()
        assert "project_roots" in data["domains"]["project"]

    def test_includes_hint_about_uri_template(self) -> None:
        data = self._call()
        assert "hint" in data
        assert "{domain}" in data["hint"]


# ── get_group_tools ───────────────────────────────────────────────────────────


class TestGetGroupTools:
    def _call(self, domain: str, group: str) -> dict:
        with patch(
            "controldesk_mcp.resources.domain_resources.mcp._tool_manager.list_tools",
            return_value=_TAGGED_TOOLS,
        ):
            from controldesk_mcp.resources.domain_resources import get_group_tools

            return json.loads(get_group_tools(domain, group))

    def test_experiment_management_group_returns_correct_tools(self) -> None:
        data = self._call("project", "experiment_management")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_project_experiment_manage" in names

    def test_project_roots_group_returns_correct_tools(self) -> None:
        data = self._call("project", "project_roots")
        names = [t["name"] for t in data["tools"]]
        assert "controldesk_project_root_manage" in names

    def test_unknown_group_returns_empty_with_hint(self) -> None:
        data = self._call("project", "nonexistent_group")
        assert data["count"] == 0
        assert "hint" in data

    def test_unknown_domain_returns_empty_with_hint(self) -> None:
        data = self._call("nonexistent_domain", "some_group")
        assert data["count"] == 0
        assert "hint" in data

    def test_count_matches_tool_list(self) -> None:
        data = self._call("project", "experiment_management")
        assert data["count"] == len(data["tools"])

    def test_tools_sorted_alphabetically(self) -> None:
        data = self._call("project", "experiment_management")
        names = [t["name"] for t in data["tools"]]
        assert names == sorted(names)
