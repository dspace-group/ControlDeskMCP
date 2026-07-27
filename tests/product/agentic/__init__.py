"""Shared fixtures for product tests (direct + LLM-driven).

Session lifecycle
-----------------
1. ``_controldesk_session`` (autouse, session scope):
   Starts the COM bridge STA thread, calls start_controldesk to ensure
   ControlDesk is running, and shuts down cleanly after all tests.

2. ``app_lifecycle_registry`` (session scope):
   ToolRegistry with the 8 lifecycle tools — consumed by agentic runners.
"""

from __future__ import annotations

import pathlib

import pytest

# ── Load .env early — before collection so env vars are visible to
#    pytest_generate_tests (which runs before any fixture executes). ──────────
try:
    from dotenv import load_dotenv as _load_dotenv

    _env_file = pathlib.Path(__file__).parent.parent.parent / ".env"
    if _env_file.is_file():
        _load_dotenv(_env_file, override=False)  # override=False: real env vars win
except ImportError:
    pass  # python-dotenv not installed — rely on system env vars

import controldesk_mcp.com_bridge as com_bridge
from controldesk_mcp.models.application import AppStartOrAttachInput
from controldesk_mcp.server.app import mcp
from controldesk_mcp.tools.application import (
    lifecycle as _lifecycle_module,  # noqa: F401 — triggers @mcp.tool registration
)
from controldesk_mcp.tools.project import (
    management as _project_module,  # noqa: F401 — triggers @mcp.tool registration
)
from controldesk_mcp.tools.tool_window import (
    management as _tool_window_module,  # noqa: F401 — triggers @mcp.tool registration
)
from tests.product.agents.llm_agent import ToolRegistry
from tests.product.helpers.session import get_controldesk_version

# ── Names of the 8 application lifecycle tools confirmed in the source ────────
_APP_LIFECYCLE_TOOLS: set[str] = {
    "start_controldesk",
    "app_set_window_visible",
    "app_get_window_visibility",
    "app_set_window_state",
    "app_get_window_state",
    "stop_controldesk",
    "app_set_window_position",
    "app_set_fullscreen",
}

# ── Names of the 23 project & experiment management tools ────────────────────
_PROJECT_EXPERIMENT_TOOLS: set[str] = {
    "project_root_add",
    "project_root_activate",
    "project_root_list",
    "project_root_remove",
    "project_create",
    "project_open",
    "project_save",
    "project_close",
    "project_remove",
    "project_backup",
    "project_open_from_backup",
    "project_exists",
    "project_get_info",
    "experiment_create",
    "experiment_activate",
    "experiment_list",
    "experiment_remove",
    "experiment_get_info",
    "experiment_export",
    "experiment_import",
    "experiment_rename",
    "experiment_save_as",
    "project_configure_settings",
}

# ── Names of the 6 tool window management tools ───────────────────────────────
_TOOL_WINDOW_TOOLS: set[str] = {
    "tool_window_list",
    "tool_window_show",
    "tool_window_close",
    "tool_window_get_state",
    "tool_window_set_dock_state",
    "tool_window_check_exists",
}


# ── Session: start / stop ControlDesk ─────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
async def _controldesk_session():
    """Start the STA thread, attach to ControlDesk, tear down after all tests."""
    await com_bridge.startup()

    # Attach to (or launch) ControlDesk so all subsequent tools can connect
    params = AppStartOrAttachInput(
        controldesk_version=get_controldesk_version(),
        make_visible=True,
    )
    await _lifecycle_module.start_controldesk(params)

    yield

    await com_bridge.shutdown()


# ── Tool registry: application lifecycle ─────────────────────────────────────


@pytest.fixture(scope="session")
def app_lifecycle_registry() -> ToolRegistry:
    """ToolRegistry containing only the 8 confirmed application lifecycle tools."""
    registry = ToolRegistry()
    registry.add_from_mcp(mcp, include=_APP_LIFECYCLE_TOOLS)
    return registry


# ── Tool registry: project & experiment management ────────────────────────────


@pytest.fixture(scope="session")
def project_experiment_registry() -> ToolRegistry:
    """ToolRegistry containing lifecycle + all 23 project/experiment tools."""
    registry = ToolRegistry()
    registry.add_from_mcp(mcp, include=_APP_LIFECYCLE_TOOLS | _PROJECT_EXPERIMENT_TOOLS)
    return registry


# ── Tool registry: tool window management ─────────────────────────────────────


@pytest.fixture(scope="session")
def tool_window_registry() -> ToolRegistry:
    """ToolRegistry containing lifecycle + all 6 tool window management tools."""
    registry = ToolRegistry()
    registry.add_from_mcp(mcp, include=_APP_LIFECYCLE_TOOLS | _TOOL_WINDOW_TOOLS)
    return registry
