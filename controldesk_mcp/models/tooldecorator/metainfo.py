from __future__ import annotations

from enum import Enum


class ToolDomain(str, Enum):
    """Allowed domains for MCP tool meta tags."""

    APPLICATION = "application"
    BUS_LOGGING = "bus_logging"
    BUS_MONITOR = "bus_monitor"
    BUS_REPLAY = "bus_replay"
    CALIBRATION = "calibration"
    ECU_DIAGNOSTICS = "ecu_diagnostics"
    INSTRUMENT = "instrument"
    LAYOUT = "layout"
    MEASUREMENT = "measurement"
    PLATFORM = "platform"
    PROJECT = "project"
    RECORDER = "recorder"
    TOOL_WINDOW = "tool_window"
    VARIABLE = "variable"


class ToolGroup(str, Enum):
    """Allowed groups for MCP tool meta tags."""

    # application
    LIFECYCLE = "lifecycle"
    WINDOW_MANAGEMENT = "window_management"
    # bus_logging
    LOGGER_MANAGEMENT = "logger_management"
    FILTER_MANAGEMENT = "filter_management"
    # bus_monitor
    MONITOR_MANAGEMENT = "monitor_management"
    # bus_replay
    REPLAY_MANAGEMENT = "replay_management"
    # calibration
    ONLINE_CALIBRATION = "online_calibration"
    PAGE_MANAGEMENT = "page_management"
    PROPOSED_CALIBRATION = "proposed_calibration"
    # measurement
    SIGNAL_MANAGEMENT = "signal_management"
    RECORDING = "recording"
    DATA_EXPORT = "data_export"
    BOOKMARKS = "bookmarks"
    RASTER_MANAGEMENT = "raster_management"
    TRIGGERS = "triggers"
    DATA_LOGGING = "data_logging"
    # platform
    CONNECTIVITY = "connectivity"
    VARIABLE_DESCRIPTIONS = "variable_descriptions"
    HARDWARE = "hardware"
    DISCOVERY = "discovery"
    CONFIGURATION = "configuration"
    # instrument
    INSTRUMENT_MANAGEMENT = "instrument_management"
    INSTRUMENT_SIGNAL = "instrument_signal"
    # layout
    LAYOUT_MANAGEMENT = "layout_management"
    LAYOUT_IO = "layout_io"
    # project
    PROJECT_ROOTS = "project_roots"
    EXPERIMENT_MANAGEMENT = "experiment_management"
    PROJECT_MANAGEMENT = "project_management"
    # recorder
    RECORDER_MANAGEMENT = "recorder_management"
    # variable
    READ = "read"
    WRITE = "write"
    # ecu_diagnostics
    DATABASE_MANAGEMENT = "database_management"
    VEHICLE_MANAGEMENT = "vehicle_management"
    LINK_MANAGEMENT = "link_management"


class MetaInfo(dict):
    """Typed meta container for MCP ``@mcp.tool(meta=...)`` parameter.

    Inherits from ``dict`` so it passes directly to FastMCP without conversion.

    Example::

        meta=MetaInfo(ToolDomain.APPLICATION, ToolGroup.LIFECYCLE)
    """

    domain: ToolDomain
    group: ToolGroup

    def __init__(self, domain: ToolDomain, group: ToolGroup) -> None:
        self.domain = domain
        self.group = group
        super().__init__(domain=domain.value, group=group.value)


class AnnotationInfo(dict):
    """Typed annotation container for MCP ``@mcp.tool(annotations=...)`` parameter.

    Inherits from ``dict`` so it passes directly to FastMCP without conversion.
    Named parameters replace error-prone raw key strings.

    Args:
        read_only:   ``True`` when the tool does not modify any system state.
        destructive: ``True`` when the tool may cause hard-to-reverse side effects.
        idempotent:  ``True`` when calling the tool multiple times has the same effect.
        open_world:  ``True`` when the tool may interact with services beyond ControlDesk.
        title:       Optional human-readable display title for inspector UIs.

    Example::

        annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True)
    """

    def __init__(
        self,
        *,
        read_only: bool = True,
        destructive: bool = False,
        idempotent: bool = True,
        open_world: bool = False,
        title: str | None = None,
    ) -> None:
        data: dict[str, object] = {
            "readOnlyHint": read_only,
            "destructiveHint": destructive,
            "idempotentHint": idempotent,
            "openWorldHint": open_world,
        }
        if title is not None:
            data["title"] = title
        super().__init__(**data)
