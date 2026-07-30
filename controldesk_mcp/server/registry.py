"""Registry — imports trigger @mcp.tool, @mcp.resource, and @mcp.prompt decorators.

This module is the single place where new tool, resource, and prompt modules must be added.
Importing this module is sufficient to register every item; no further wiring is needed.

Rules:
  - Add one import per tool module when following the 5-layer tool addition sequence.
  - Add one import per resource module to controldesk_mcp/resources/.
  - Add one import per prompt module to controldesk_mcp/prompts/.
  - Tools MUST be imported before resources so that domain_resources can read the
    full tool list when building its catalog at module-load time.

Governance — when adding new tools or domains:
  - Resources: add domain prefix to _DOMAIN_PREFIXES in domain_resources.py.
  - Prompts: add a new <domain>_prompts.py and import it here under # ── Prompts.
  - Tests: add tests/unit/test_prompts/test_<domain>_prompts.py.
"""

from __future__ import annotations

# ── Prompts ───────────────────────────────────────────────────────────────────
import controldesk_mcp.prompts.application_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.bus_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.calibration_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.ecu_diagnostics_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.instrument_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.layout_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.measurement_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.project_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.recorder_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.session_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.tool_window_prompts  # noqa: E402, F401
import controldesk_mcp.prompts.variable_prompts  # noqa: E402, F401

# ── Resources ─────────────────────────────────────────────────────────────────
# Resources imported after tools so domain/group catalogs reflect all tools.
import controldesk_mcp.resources.domain_resources  # noqa: E402, F401
import controldesk_mcp.resources.server_resources  # noqa: E402, F401

# ── Tools ─────────────────────────────────────────────────────────────────────
# Tools MUST be registered before Resources so the domain catalog is complete.
import controldesk_mcp.tools.application.lifecycle  # noqa: F401
import controldesk_mcp.tools.bus_logging.management  # noqa: F401
import controldesk_mcp.tools.bus_monitor.monitoring  # noqa: F401
import controldesk_mcp.tools.bus_replay.management  # noqa: F401
import controldesk_mcp.tools.calibration.management  # noqa: F401
import controldesk_mcp.tools.ecu_diagnostics.management  # noqa: F401
import controldesk_mcp.tools.instrument.management  # noqa: F401
import controldesk_mcp.tools.layout.management  # noqa: F401
import controldesk_mcp.tools.measurement.management  # noqa: F401
import controldesk_mcp.tools.platform.management  # noqa: F401
import controldesk_mcp.tools.project.management  # noqa: F401
import controldesk_mcp.tools.recorder.management  # noqa: F401
import controldesk_mcp.tools.tool_window.management  # noqa: F401
import controldesk_mcp.tools.variable_management.management  # noqa: F401
from controldesk_mcp.server.app import mcp as _mcp  # noqa: E402

# ── Token optimisation ────────────────────────────────────────────────────────
# outputSchema accounts for 66 % of the MCP wire-format token budget. Strip it
# after all tools are registered so LLM context usage drops from ~90 % → ~30 %.
from controldesk_mcp.server.tool_schema_optimizer import strip_output_schemas  # noqa: E402

strip_output_schemas(_mcp)
