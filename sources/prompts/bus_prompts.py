"""MCP prompts for ControlDesk bus logging, monitoring, replay, and filtering workflows.

Prompts registered:
  configure_bus_logging  — create a logger, configure filters, start/stop logging
  run_bus_monitor        — create a monitor, start capturing, save data
  replay_bus_data        — create a replay session and play back recorded bus data
  manage_bus_filters     — create, configure, start, and stop message filters

All 28 bus-domain tools are covered across these prompts:
  Logger management:  bus_logger_create, bus_logger_configure, bus_logger_set_activated,
                      bus_logger_start, bus_logger_stop, bus_logger_get_state,
                      bus_logger_list, bus_logger_remove, bus_logger_clear_all
  Filter management:  bus_filter_create, bus_filter_configure, bus_filter_start,
                      bus_filter_stop, bus_filter_list, bus_filter_remove
  Monitor management: bus_monitor_create, bus_monitor_configure, bus_monitor_start,
                      bus_monitor_stop, bus_monitor_save_data,
                      bus_monitor_save_data_with_time_axis, bus_monitor_get_state,
                      bus_monitor_list, bus_monitor_remove, bus_monitor_clear_all
  Replay management:  bus_replay_create, bus_replay_configure, bus_replay_set_activated,
                      bus_replay_start, bus_replay_stop, bus_replay_get_state,
                      bus_replay_list, bus_replay_remove, bus_replay_clear_all

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from sources.server.app import mcp

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
                f"1. Call `bus_logger_list` to check for existing loggers.\n"
                f"   To remove all loggers at once: `bus_logger_clear_all`.\n"
                f"2. Call `bus_logger_create`{name_arg} to create a new logger.\n"
                f"3. Call `bus_logger_configure`{db_arg} to set the database and options.\n"
                f"   Optionally call `manage_bus_filters` (see that prompt) to add message "
                f"   filters that restrict which frames are captured.\n"
                f"4. Call `bus_logger_set_activated` to enable the logger.\n"
                f"5. Call `bus_logger_start` to begin bus data capture.\n"
                f"6. When done, call `bus_logger_stop`.\n"
                f"7. Call `bus_logger_get_state` to confirm the logger stopped cleanly.\n"
                f"8. When the logger is no longer needed: call `bus_logger_remove`.\n"
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
                f"1. Call `bus_monitor_list` to check for existing monitors.\n"
                f"   To remove all monitors at once: `bus_monitor_clear_all`.\n"
                f"2. Call `bus_monitor_create`{name_arg} to create a new monitor.\n"
                f"3. Call `bus_monitor_configure` to set capture options.\n"
                f"4. Call `bus_monitor_start` to begin live bus data capture.\n"
                f"5. When enough data has been captured, call `bus_monitor_stop`.\n"
                f"6. Call `bus_monitor_save_data`{path_arg} to write the captured data "
                f"   to a file, or `bus_monitor_save_data_with_time_axis` for time-stamped "
                f"   output.\n"
                f"7. Call `bus_monitor_get_state` to confirm the save completed.\n"
                f"8. When the monitor is no longer needed: call `bus_monitor_remove`.\n"
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
                f"1. Call `bus_replay_list` to check for existing replay sessions.\n"
                f"   To remove all replay sessions at once: `bus_replay_clear_all`.\n"
                f"2. Call `bus_replay_create`{name_arg} to create a new replay.\n"
                f"3. Call `bus_replay_configure`{path_arg} to set the source file and "
                f"   replay options.\n"
                f"4. Call `bus_replay_set_activated` to arm the replay.\n"
                f"5. Call `bus_replay_start` to begin playback.\n"
                f"6. When playback is complete, call `bus_replay_stop`.\n"
                f"7. Call `bus_replay_get_state` to confirm the session ended cleanly.\n"
                f"8. When the replay is no longer needed: call `bus_replay_remove`.\n"
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
                f"1. Call `bus_filter_list` to see existing filters.\n"
                f"2. Call `bus_filter_create`{name_arg} to create a new filter.\n"
                f"3. Call `bus_filter_configure` to set which message IDs, CAN channels, "
                f"   or frame types to include or exclude.\n"
                f"4. Associate the filter with a logger (see `configure_bus_logging` prompt) "
                f"   before starting.\n"
                f"5. Call `bus_filter_start` to activate the filter.\n"
                f"6. When filtering is complete, call `bus_filter_stop`.\n"
                f"7. When the filter is no longer needed: call `bus_filter_remove`.\n"
                f"8. Report: filter name, configured frame IDs, and capture statistics."
            ),
        }
    ]
