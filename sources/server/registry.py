"""Registry — imports trigger @mcp.tool, @mcp.resource, and @mcp.prompt decorators.

This module is the single place where new tool, resource, and prompt modules must be added.
Importing this module is sufficient to register every item; no further wiring is needed.

Rules:
  - Add one import per tool module when following the 5-layer tool addition sequence.
  - Add one import per resource module to sources/resources/.
  - Add one import per prompt module to sources/prompts/.
  - Tools MUST be imported before resources so that domain_resources can read the
    full tool list when building its catalog at module-load time.

Governance — when adding new tools or domains:
  - Resources: add domain prefix to _DOMAIN_PREFIXES in domain_resources.py.
  - Prompts: add a new <domain>_prompts.py and import it here under # ── Prompts.
  - Tests: add tests/unit/test_prompts/test_<domain>_prompts.py.
"""

from __future__ import annotations

# ── Prompts ───────────────────────────────────────────────────────────────────
import sources.prompts.application_prompts  # noqa: E402, F401
import sources.prompts.bus_prompts  # noqa: E402, F401
import sources.prompts.calibration_prompts  # noqa: E402, F401
import sources.prompts.instrument_prompts  # noqa: E402, F401
import sources.prompts.layout_prompts  # noqa: E402, F401
import sources.prompts.measurement_prompts  # noqa: E402, F401
import sources.prompts.project_prompts  # noqa: E402, F401
import sources.prompts.recorder_prompts  # noqa: E402, F401
import sources.prompts.session_prompts  # noqa: E402, F401
import sources.prompts.tool_window_prompts  # noqa: E402, F401
import sources.prompts.variable_prompts  # noqa: E402, F401

# ── Resources ─────────────────────────────────────────────────────────────────
# Resources imported after tools so domain/group catalogs reflect all tools.
import sources.resources.domain_resources  # noqa: E402, F401
import sources.resources.server_resources  # noqa: E402, F401

# ── Tools ─────────────────────────────────────────────────────────────────────
# Tools MUST be registered before Resources so the domain catalog is complete.
import sources.tools.application.lifecycle  # noqa: F401
import sources.tools.bus_logging.management  # noqa: F401
import sources.tools.bus_monitor.monitoring  # noqa: F401
import sources.tools.bus_replay.management  # noqa: F401
import sources.tools.calibration.management  # noqa: F401
import sources.tools.instrument.management  # noqa: F401
import sources.tools.layout.management  # noqa: F401
import sources.tools.measurement.management  # noqa: F401
import sources.tools.platform.management  # noqa: F401
import sources.tools.project.management  # noqa: F401
import sources.tools.recorder.management  # noqa: F401
import sources.tools.tool_window.management  # noqa: F401
import sources.tools.variable_management.management  # noqa: F401
from sources.server.app import mcp as _mcp  # noqa: E402

# ── Token optimisation ────────────────────────────────────────────────────────
# outputSchema accounts for 66 % of the MCP wire-format token budget. Strip it
# after all tools are registered so LLM context usage drops from ~90 % → ~30 %.
from sources.server.tool_schema_optimizer import strip_output_schemas  # noqa: E402

strip_output_schemas(_mcp)
