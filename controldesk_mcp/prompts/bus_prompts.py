"""MCP prompts for ControlDesk bus logging, monitoring, replay, and filtering workflows.

Prompts registered:
  configure_bus_logging  — create a logger, configure filters, start/stop logging
  run_bus_monitor        — create a monitor, start capturing, save data
  replay_bus_data        — create a replay session and play back recorded bus data
  manage_bus_filters     — create, configure, start, and stop message filters

Bus-domain tools used across these prompts:
    Logger:  controldesk_bus_logger_create, controldesk_bus_logger_configure,
                     controldesk_bus_logger_manage, controldesk_bus_logger_query,
                     controldesk_bus_logging_discover
    Monitor: controldesk_bus_monitor_create, controldesk_bus_monitor_configure,
                     controldesk_bus_monitor_manage, controldesk_bus_monitor_discover,
                     controldesk_bus_monitor_save
    Replay:  controldesk_bus_replay_create, controldesk_bus_replay_configure,
                     controldesk_bus_replay_manage, controldesk_bus_replay_discover

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from controldesk_mcp.server.app import mcp

# ── Prompt — Configure Bus Logging ────────────────────────────────────────────


@mcp.prompt(
    name="configure_bus_logging",
    description=(
        "Step-by-step guide for setting up ControlDesk bus logging: "
        "create a logger, configure it, activate, start capturing, and stop. "
        "Covers logger lifecycle including clear-all and remove operations. "
        "Accepts optional logger name and database path for context."
    ),
)
def configure_bus_logging(
    logger_name: str = "",
    database_path: str = "",
) -> list[dict]:
    """Generate a bus logging setup and capture workflow prompt."""
    name_arg = f", name='{logger_name}'" if logger_name else ""
    db_arg = f", database_path='{database_path}'" if database_path else ""

    return [
        {
            "role": "user",
            "content": (
                f"Configure and run a ControlDesk bus logging session.\n\n"
                f"**Parameters:**\n"
                f"- Logger name: {logger_name or '(auto-generated)'}\n"
                f"- Database path: {database_path or '(not specified)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_bus_logger_query` with action='list' to check existing loggers.\n"
                f"2. Call `controldesk_bus_logger_create`{name_arg} to create a new logger.\n"
                f"3. Call `controldesk_bus_logger_configure`{db_arg} to set the database and options.\n"
                f"4. Call `controldesk_bus_logging_discover` to activate logger administration and filter tools.\n"
                f"5. Call `controldesk_bus_logger_admin_manage` with action='set_activated'.\n"
                f"6. Call `controldesk_bus_logger_manage` with action='start' to begin bus data capture.\n"
                f"7. When done, call `controldesk_bus_logger_manage` with action='stop'.\n"
                f"8. Call `controldesk_bus_logger_query` with action='get_state' to confirm the logger stopped.\n"
                f"9. Report: logger name, database path, capture duration, and final state."
            ),
        }
    ]


# ── Prompt — Run Bus Monitor ──────────────────────────────────────────────────


@mcp.prompt(
    name="run_bus_monitor",
    description=(
        "Guided workflow for creating a ControlDesk bus monitor, starting live capture, "
        "and saving the captured data to a file. "
        "Covers monitor lifecycle including clear-all and remove operations. "
        "Accepts optional monitor name and output file path."
    ),
)
def run_bus_monitor(
    monitor_name: str = "",
    output_path: str = "",
) -> list[dict]:
    """Generate a bus monitor capture and save workflow prompt."""
    name_arg = f", name='{monitor_name}'" if monitor_name else ""
    path_arg = f", file_path='{output_path}'" if output_path else ""

    return [
        {
            "role": "user",
            "content": (
                f"Capture bus traffic using the ControlDesk Bus Monitor.\n\n"
                f"**Parameters:**\n"
                f"- Monitor name: {monitor_name or '(auto-generated)'}\n"
                f"- Output path: {output_path or '(auto-generated)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_bus_monitor_discover` to activate monitor query and save tools.\n"
                f"2. Call `controldesk_bus_monitor_query` with action='list' to check existing monitors.\n"
                f"3. Call `controldesk_bus_monitor_create`{name_arg} to create a new monitor.\n"
                f"4. Call `controldesk_bus_monitor_configure` to set capture options.\n"
                f"5. Call `controldesk_bus_monitor_manage` with action='start' to begin capture.\n"
                f"6. When enough data has been captured, call `controldesk_bus_monitor_manage` with action='stop'.\n"
                f"7. Call `controldesk_bus_monitor_save`{path_arg} to write the captured data to a file.\n"
                f"8. Call `controldesk_bus_monitor_query` with action='get_state' to confirm the save.\n"
                f"9. Report: monitor name, output file path, number of frames captured."
            ),
        }
    ]


# ── Prompt — Replay Bus Data ──────────────────────────────────────────────────


@mcp.prompt(
    name="replay_bus_data",
    description=(
        "Guided workflow for replaying previously recorded bus data in ControlDesk: "
        "create a replay session, configure the source file, and play back. "
        "Covers replay lifecycle including clear-all and remove operations. "
        "Accepts optional replay name and source file path."
    ),
)
def replay_bus_data(
    replay_name: str = "",
    source_path: str = "",
) -> list[dict]:
    """Generate a bus replay workflow prompt."""
    name_arg = f", name='{replay_name}'" if replay_name else ""
    path_arg = f", file_path='{source_path}'" if source_path else ""

    return [
        {
            "role": "user",
            "content": (
                f"Replay recorded bus data in ControlDesk.\n\n"
                f"**Parameters:**\n"
                f"- Replay name: {replay_name or '(auto-generated)'}\n"
                f"- Source file: {source_path or '(not specified — must configure)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_bus_replay_discover` to activate replay query and administration tools.\n"
                f"2. Call `controldesk_bus_replay_query` with action='list' to check existing replay sessions.\n"
                f"3. Call `controldesk_bus_replay_create`{name_arg} to create a new replay.\n"
                f"4. Call `controldesk_bus_replay_configure`{path_arg} to set the source file and "
                f"   replay options.\n"
                f"5. Call `controldesk_bus_replay_admin_manage` with action='set_activated' to arm the replay.\n"
                f"6. Call `controldesk_bus_replay_manage` with action='start' to begin playback.\n"
                f"7. When playback is complete, call `controldesk_bus_replay_manage` with action='stop'.\n"
                f"8. Call `controldesk_bus_replay_query` with action='get_state' to confirm completion.\n"
                f"9. Report: replay name, source file, playback duration, and final state."
            ),
        }
    ]


# ── Prompt — Manage Bus Filters ───────────────────────────────────────────────


@mcp.prompt(
    name="manage_bus_filters",
    description=(
        "Guided workflow for creating and managing ControlDesk bus message filters: "
        "create a filter, configure which frames to include/exclude, start filtering, "
        "and clean up. "
        "Filters are used in combination with bus loggers to selectively capture frames."
    ),
)
def manage_bus_filters(
    filter_name: str = "",
) -> list[dict]:
    """Generate a bus filter management workflow prompt."""
    name_arg = f", name='{filter_name}'" if filter_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Create and manage a ControlDesk bus message filter.\n\n"
                f"**Parameters:**\n"
                f"- Filter name: {filter_name or '(auto-generated)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `controldesk_bus_logging_discover` to activate filter tools.\n"
                f"2. Call `controldesk_bus_filter_manage` with action='list' to see existing filters.\n"
                f"3. Call `controldesk_bus_filter_create`{name_arg} to create a new filter.\n"
                f"4. Call `controldesk_bus_filter_configure` to set which message IDs, CAN channels, "
                f"   or frame types to include or exclude.\n"
                f"5. Call `controldesk_bus_filter_manage` with action='start' to activate the filter.\n"
                f"6. When filtering is complete, call `controldesk_bus_filter_manage` with action='stop'.\n"
                f"7. When no longer needed, call `controldesk_bus_filter_manage` with action='remove'.\n"
                f"8. Report: filter name, configured frame IDs, and capture statistics."
            ),
        }
    ]
