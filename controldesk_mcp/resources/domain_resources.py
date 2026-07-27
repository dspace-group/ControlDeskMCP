"""MCP resources exposing per-domain and per-group tool catalogs via URI templates.

Resources registered:
  controldesk://server/domains              — list of all top-level tool domains
  controldesk://server/tool-groups          — full domain→group→[tool] hierarchy
  controldesk://tools/{domain}              — URI template; tools for a single domain
  controldesk://tools/{domain}/{group}      — URI template; tools for a domain sub-group

URI template resources let the MCP Inspector and LLM clients query a specific domain
or sub-group without downloading the entire tool catalog.  No COM connection is required.

Domain / group taxonomy (set via meta={"domain": X, "group": Y} in each @mcp.tool decorator):
  application   (lifecycle, window_management)
  bus_logging   (logger_management, filter_management)
  bus_monitor   (monitor_management)
  bus_replay    (replay_management)
  calibration   (online_calibration, proposed_calibration, page_management, data_logging)
  measurement   (recording, signal_management, raster_management, data_export,
                 bookmarks, triggers, data_logging)
  platform      (connectivity, configuration, hardware, variable_descriptions)
  project       (project_management, project_roots, experiment_management)
  recorder      (recorder_management)
  tool_window   (window_management)
  variable      (discovery, read, write, variable_descriptions)

Layer: MCP Resource adapter — owns @mcp.resource annotations only.
No COM calls; all data is read from the in-process tool manager.
"""

from __future__ import annotations

import json

from controldesk_mcp.server.app import mcp


def _get_domain_group_catalog() -> dict[str, dict[str, list[str]]]:
    """Build domain→group→[tool_names] catalog from tool meta tags."""
    catalog: dict[str, dict[str, list[str]]] = {}
    for tool in mcp._tool_manager.list_tools():
        meta = tool.meta or {}
        domain = meta.get("domain")
        group = meta.get("group")
        if domain and group:
            catalog.setdefault(domain, {}).setdefault(group, []).append(tool.name)
    for domain in catalog:
        for group in catalog[domain]:
            catalog[domain][group].sort()
    return catalog


# ── Domain → tool-name prefix mapping ────────────────────────────────────────
# Used for fast prefix-based filtering before meta tags are applied.
# Note: experiment is now a distinct queryable domain (group under project).

_DOMAIN_PREFIXES: dict[str, list[str]] = {
    "application": ["app_", "start_controldesk", "stop_controldesk"],
    "bus_logging": ["bus_logger_", "bus_filter_"],
    "bus_monitor": ["bus_monitor_"],
    "bus_replay": ["bus_replay_"],
    "calibration": ["calibration_", "proposed_calibration_", "data_set_"],
    "experiment": ["experiment_"],
    "instrument": ["instrument_"],
    "layout": ["layout_"],
    "measurement": ["measurement_", "data_logger_", "trigger_"],
    "platform": ["platform_"],
    "project": ["project_"],
    "recorder": ["recorder_main_"],
    "tool_window": ["tool_window_"],
    "variable": ["variable_"],
}

# Sorted list of known domain names for discovery
_KNOWN_DOMAINS: list[str] = sorted(_DOMAIN_PREFIXES.keys())


def _tools_for_domain(domain: str) -> list[dict]:
    """Return tool dicts for a given domain, or [] if domain is unknown."""
    prefixes = _DOMAIN_PREFIXES.get(domain, [])
    if not prefixes:
        return []
    all_tools = mcp._tool_manager.list_tools()
    matched = [
        {"name": t.name, "description": t.description or ""}
        for t in all_tools
        if any(t.name.startswith(p) for p in prefixes)
    ]
    matched.sort(key=lambda t: t["name"])
    return matched


# ── Resource 1 — Domain list ──────────────────────────────────────────────────


@mcp.resource(
    uri="controldesk://server/domains",
    name="DomainList",
    title="Tool Domain List",
    description=(
        "List of all tool domains available on this server. "
        "Use a domain name with the resource template "
        "`controldesk://tools/{domain}` to get tools for a specific domain. "
        "Always available — no ControlDesk connection required."
    ),
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_domain_list() -> str:
    """Return a JSON list of known tool domains."""
    return json.dumps(
        {
            "domains": _KNOWN_DOMAINS,
            "count": len(_KNOWN_DOMAINS),
            "uri_template": "controldesk://tools/{domain}",
        }
    )


# ── Resource Template — Per-domain tool catalog ───────────────────────────────


@mcp.resource(
    uri="controldesk://tools/{domain}",
    name="DomainToolCatalog",
    title="Domain Tool Catalog",
    description=(
        "Tool catalog for a single domain. "
        "Replace {domain} with one of the names from controldesk://server/domains "
        "(e.g., controldesk://tools/measurement). "
        "Returns all tools whose names match the domain prefix, with descriptions. "
        "Always available — no ControlDesk connection required."
    ),
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_domain_tools(domain: str) -> str:
    """Return tool catalog for a single domain as JSON.

    The ``domain`` parameter is extracted from the URI template by FastMCP.
    Unknown domain names return an empty tool list with an error hint.
    """
    tools = _tools_for_domain(domain)
    result: dict = {
        "domain": domain,
        "count": len(tools),
        "tools": tools,
    }
    if not tools:
        result["hint"] = (
            f"Domain '{domain}' is unknown or has no registered tools. "
            f"Known domains: {_KNOWN_DOMAINS}"
        )
    return json.dumps(result)


# ── Resource 3 — Tool-group hierarchy ────────────────────────────────────────


@mcp.resource(
    uri="controldesk://server/tool-groups",
    name="ToolGroupHierarchy",
    title="Tool Group Hierarchy",
    description=(
        "Full domain → group → [tool names] hierarchy for all registered tools. "
        "Each tool carries domain and group metadata (set via meta field). "
        "Use this to understand how tools are organized into logical sub-groups "
        "within each domain. Always available — no ControlDesk connection required."
    ),
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_tool_group_hierarchy() -> str:
    """Return the full domain→group→[tool] catalog as JSON."""
    catalog = _get_domain_group_catalog()
    # Enrich with per-group tool count
    enriched: dict = {}
    total = 0
    for domain, groups in catalog.items():
        enriched[domain] = {}
        for group, names in groups.items():
            enriched[domain][group] = {"tools": names, "count": len(names)}
            total += len(names)
    return json.dumps(
        {
            "total_tools": total,
            "domains": enriched,
            "hint": (
                "Use controldesk://tools/{domain}/{group} to fetch tools for a "
                "specific sub-group (e.g., controldesk://tools/project/experiment_management)."
            ),
        }
    )


# ── Resource Template — Per-group tool catalog ────────────────────────────────


@mcp.resource(
    uri="controldesk://tools/{domain}/{group}",
    name="GroupToolCatalog",
    title="Group Tool Catalog",
    description=(
        "Tool catalog for a single domain sub-group. "
        "Replace {domain} and {group} with values from controldesk://server/tool-groups. "
        "Example: controldesk://tools/project/experiment_management "
        "returns all experiment_* tools. "
        "Always available — no ControlDesk connection required."
    ),
    mime_type="application/json",
    annotations={"readOnlyHint": True, "idempotentHint": True},
)
def get_group_tools(domain: str, group: str) -> str:
    """Return tools for a specific domain/group combination as JSON."""
    all_tools = mcp._tool_manager.list_tools()
    matched = [
        {"name": t.name, "description": t.description or ""}
        for t in all_tools
        if (t.meta or {}).get("domain") == domain and (t.meta or {}).get("group") == group
    ]
    matched.sort(key=lambda t: t["name"])
    result: dict = {
        "domain": domain,
        "group": group,
        "count": len(matched),
        "tools": matched,
    }
    if not matched:
        catalog = _get_domain_group_catalog()
        available_groups = list(catalog.get(domain, {}).keys())
        result["hint"] = (
            f"No tools found for domain='{domain}' group='{group}'. "
            f"Available groups in '{domain}': {available_groups}. "
            f"Known domains: {sorted(catalog.keys())}"
        )
    return json.dumps(result)
