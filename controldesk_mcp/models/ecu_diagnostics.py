"""Pydantic input and response models for the ECU Diagnostics domain.

Domain: ControlDesk ECU Diagnostics (Diagnostic2 platform) — ODX database setup,
        vehicle selection, logical link configuration, and interface selection.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from controldesk_mcp.models.base import DictModelMixin

# ── Enums ───────────────────────────────────────────────────────────────────────


class ECUDiagnosticsProtocol(str, Enum):
    """Supported ECU diagnostics protocols.

    Integer COM values (ECUDiagnosticsProtocol):
            ISO_14229_UDS → 2
            KWP2000       → 1
            ISO_14230     → 1 (K-Line variant)

        Note: Some ControlDesk installations can expose variant-specific protocol
        values. The COM bridge applies runtime-safe fallbacks where needed.
    """

    ISO_14229_UDS = "ISO_14229_UDS"
    KWP2000 = "KWP2000"
    ISO_14230 = "ISO_14230"


class ECUDiagnosticsPhysicalConnection(str, Enum):
    """Physical connection types for ECU diagnostics logical links.

    Integer COM values (ECUDiagnosticsPhysicalConnection):
      CAN       → 0
      LIN       → 1
      Ethernet  → 2
      FlexRay   → 3
      K_Line    → 4
      DoIP      → 5
    """

    CAN = "CAN"
    LIN = "LIN"
    Ethernet = "Ethernet"
    FlexRay = "FlexRay"
    K_Line = "K_Line"
    DoIP = "DoIP"


class DiagSetupAction(str, Enum):
    """Actions for controldesk_ecu_diagnostics_setup tool."""

    add_odx_directory = "add_odx_directory"
    list_odx_files = "list_odx_files"


class DiagLinkSetupAction(str, Enum):
    """Actions for controldesk_ecu_diagnostics_link_setup tool."""

    list_vehicles = "list_vehicles"
    select_vehicle = "select_vehicle"
    list_logical_links = "list_logical_links"
    select_logical_link = "select_logical_link"
    configure_logical_link = "configure_logical_link"
    list_interfaces = "list_interfaces"
    select_interface = "select_interface"


class DiagDbManageAction(str, Enum):
    """Actions for controldesk_ecu_diagnostics_db_manage ADD-ON tool."""

    add_file = "add_file"
    list_files = "list_files"


class DiagVehicleManageAction(str, Enum):
    """Actions for controldesk_ecu_diagnostics_vehicle_manage ADD-ON tool."""

    list_vehicles = "list_vehicles"
    select_vehicle = "select_vehicle"


class DiagLinkManageAction(str, Enum):
    """Actions for controldesk_ecu_diagnostics_link_manage ADD-ON tool."""

    list_links = "list_links"
    select_link = "select_link"
    configure_link = "configure_link"
    list_interfaces = "list_interfaces"
    select_interface = "select_interface"


# ── Sub-models ─────────────────────────────────────────────────────────────────


class VehicleInfo(DictModelMixin, BaseModel):
    """Information about a single vehicle in the VehicleSelection."""

    short_name: str = Field(description="Short (identifier) name of the vehicle.")
    long_name: str = Field(default="", description="Long (human-readable) name of the vehicle.")
    description: str = Field(default="", description="Description of the vehicle.")
    is_selected: bool = Field(default=False, description="Whether this vehicle is currently selected.")


class LogicalLinkInfo(DictModelMixin, BaseModel):
    """Information about a single logical link."""

    short_name: str = Field(description="Short (identifier) name of the logical link.")
    long_name: str = Field(default="", description="Long name of the logical link.")
    display_name: str = Field(default="", description="Display name of the logical link.")
    description: str = Field(default="", description="Description of the logical link.")
    is_selected: bool = Field(default=False, description="Whether this link is currently selected.")


class VendorInfo(DictModelMixin, BaseModel):
    """Interface vendor with its list of available interface names."""

    vendor_name: str = Field(description="Name of the interface vendor (e.g. 'dSPACE').")
    interfaces: list[str] = Field(
        default_factory=list,
        description="List of available interface names for this vendor.",
    )


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the discover catalogue."""

    tool_name: str = Field(description="MCP tool name.")
    purpose: str = Field(description="Brief description of what the tool does.")
    actions: list[str] = Field(default_factory=list, description="Supported action values.")
    required_params_per_action: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Required parameters for each action.",
    )
    group: str = Field(default="", description="Tool group name.")


# ── ODX Database input / result models ─────────────────────────────────────────


class DiagAddOdxDirectoryInput(BaseModel):
    """Input for add_odx_directory action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform (e.g. 'ECU Diagnostics').",
        examples=["ECU Diagnostics"],
    )
    directory_path: str = Field(
        description=(
            "Absolute path to the folder containing ODX database files "
            "(e.g. 'C:\\\\DiagDemo\\\\ECUDiagnostics_v2.0.2')."
        ),
        examples=["C:\\DiagDemo\\ECUDiagnostics_v2.0.2"],
    )
    db_name: str = Field(
        default="",
        description="Optional custom name for the ODX database. Ignored if empty.",
        examples=["MyDatabase"],
    )
    optimize: bool = Field(
        default=False,
        description=(
            "Set to True to optimize the database for faster loading. Optimization takes additional time at import."
        ),
        examples=[False, True],
    )


class DiagAddOdxDirectoryResult(DictModelMixin, BaseModel):
    """Result of add_odx_directory."""

    platform_name: str
    directory_path: str
    db_name: str
    files_added: int
    optimized: bool
    timestamp: str


class DiagAddOdxFileInput(BaseModel):
    """Input for add_file action (ADD-ON db_manage tool)."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    file_path: str = Field(
        description="Absolute path to a single ODX file to add.",
        examples=["C:\\DiagDemo\\MyECU.odx"],
    )


class DiagAddOdxFileResult(DictModelMixin, BaseModel):
    """Result of add_odx_file."""

    platform_name: str
    file_path: str
    timestamp: str


class DiagListOdxFilesInput(BaseModel):
    """Input for list_odx_files / list_files action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )


class DiagListOdxFilesResult(DictModelMixin, BaseModel):
    """Result of list_odx_files."""

    platform_name: str
    files: list[str]
    count: int


# ── Vehicle input / result models ───────────────────────────────────────────────


class DiagListVehiclesInput(BaseModel):
    """Input for list_vehicles action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )


class DiagListVehiclesResult(DictModelMixin, BaseModel):
    """Result of list_vehicles."""

    platform_name: str
    vehicles: list[VehicleInfo]
    count: int


class DiagSelectVehicleInput(BaseModel):
    """Input for select_vehicle action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    vehicle_name: str = Field(
        description=("Short name of the vehicle to select (as returned by list_vehicles, e.g. 'VI_DemoCar')."),
        examples=["VI_DemoCar"],
    )


class DiagSelectVehicleResult(DictModelMixin, BaseModel):
    """Result of select_vehicle."""

    platform_name: str
    vehicle_name: str
    timestamp: str


# ── Logical link input / result models ─────────────────────────────────────────


class DiagListLogicalLinksInput(BaseModel):
    """Input for list_logical_links action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )


class DiagListLogicalLinksResult(DictModelMixin, BaseModel):
    """Result of list_logical_links."""

    platform_name: str
    logical_links: list[LogicalLinkInfo]
    count: int


class DiagSelectLogicalLinkInput(BaseModel):
    """Input for select_logical_link action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    link_name: str = Field(
        description=(
            "Short name of the logical link to select (as returned by list_logical_links, e.g. 'LL_DemoECU')."
        ),
        examples=["LL_DemoECU"],
    )


class DiagSelectLogicalLinkResult(DictModelMixin, BaseModel):
    """Result of select_logical_link."""

    platform_name: str
    link_name: str
    timestamp: str


class DiagConfigureLogicalLinkInput(BaseModel):
    """Input for configure_logical_link / configure_link action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    link_name: str = Field(
        description="Short name of the logical link to configure.",
        examples=["LL_DemoECU"],
    )
    protocol: ECUDiagnosticsProtocol = Field(
        description="Diagnostics protocol to use (e.g. 'ISO_14229_UDS').",
        examples=["ISO_14229_UDS"],
    )
    physical_connection: ECUDiagnosticsPhysicalConnection = Field(
        description="Physical bus connection type (e.g. 'CAN').",
        examples=["CAN"],
    )


class DiagConfigureLogicalLinkResult(DictModelMixin, BaseModel):
    """Result of configure_logical_link."""

    platform_name: str
    link_name: str
    protocol: str
    physical_connection: str
    timestamp: str


# ── Interface selection input / result models ───────────────────────────────────


class DiagListInterfacesInput(BaseModel):
    """Input for list_interfaces action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    link_name: str = Field(
        description="Short name of the logical link whose interfaces to list.",
        examples=["LL_DemoECU"],
    )


class DiagListInterfacesResult(DictModelMixin, BaseModel):
    """Result of list_interfaces."""

    platform_name: str
    link_name: str
    vendors: list[VendorInfo]


class DiagSelectInterfaceInput(BaseModel):
    """Input for select_interface action."""

    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    link_name: str = Field(
        description="Short name of the logical link.",
        examples=["LL_DemoECU"],
    )
    vendor_name: str = Field(
        description="Name of the interface vendor (e.g. 'dSPACE').",
        examples=["dSPACE"],
    )
    interface_name: str = Field(
        description="Name of the interface (e.g. 'Virtual', 'DS2211').",
        examples=["Virtual"],
    )
    channel_index: int = Field(
        default=0,
        description="Zero-based index of the channel to select (e.g. 0).",
        examples=[0],
    )


class DiagSelectInterfaceResult(DictModelMixin, BaseModel):
    """Result of select_interface_channel."""

    platform_name: str
    link_name: str
    vendor_name: str
    interface_name: str
    channel_index: int
    timestamp: str


# ── Consolidated action inputs (MAIN tools) ────────────────────────────────────


class DiagSetupInput(BaseModel):
    """Consolidated input for controldesk_ecu_diagnostics_setup (MAIN tool).

    The *action* field determines which fields are required:
      add_odx_directory → platform_name, directory_path; optional db_name, optimize
      list_odx_files    → platform_name
    """

    action: DiagSetupAction = Field(
        description=(
            "Setup action to perform: "
            "'add_odx_directory' — add all ODX files from a directory to the active database; "
            "'list_odx_files' — list currently loaded ODX file paths."
        )
    )
    platform_name: str = Field(
        description=("Name of the Diagnostic2 platform (e.g. 'ECU Diagnostics', as returned by platform_manage add)."),
        examples=["ECU Diagnostics"],
    )
    directory_path: Optional[str] = Field(
        default=None,
        description="Required for action='add_odx_directory'. Absolute path to the ODX folder.",
        examples=["C:\\DiagDemo\\ECUDiagnostics_v2.0.2"],
    )
    db_name: Optional[str] = Field(
        default=None,
        description="Optional for action='add_odx_directory'. Custom name for the database.",
        examples=["MyDatabase"],
    )
    optimize: bool = Field(
        default=False,
        description="Optional for action='add_odx_directory'. Optimize database for faster loading.",
        examples=[False],
    )


class DiagLinkSetupInput(BaseModel):
    """Consolidated input for controldesk_ecu_diagnostics_link_setup (MAIN tool).

    The *action* field determines which additional fields are required:
      list_vehicles        → platform_name
      select_vehicle       → platform_name, vehicle_name
      list_logical_links   → platform_name
      select_logical_link  → platform_name, link_name
      configure_logical_link → platform_name, link_name, protocol, physical_connection
      list_interfaces      → platform_name, link_name
      select_interface     → platform_name, link_name, vendor_name, interface_name, channel_index
    """

    action: DiagLinkSetupAction = Field(
        description=(
            "Link setup action: 'list_vehicles', 'select_vehicle', "
            "'list_logical_links', 'select_logical_link', "
            "'configure_logical_link', 'list_interfaces', 'select_interface'."
        )
    )
    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    vehicle_name: Optional[str] = Field(
        default=None,
        description="Required for action='select_vehicle'. Vehicle short name.",
        examples=["VI_DemoCar"],
    )
    link_name: Optional[str] = Field(
        default=None,
        description=("Required for select_logical_link, configure_logical_link, list_interfaces, select_interface."),
        examples=["LL_DemoECU"],
    )
    protocol: Optional[ECUDiagnosticsProtocol] = Field(
        default=None,
        description="Required for action='configure_logical_link'. Protocol to use.",
        examples=["ISO_14229_UDS"],
    )
    physical_connection: Optional[ECUDiagnosticsPhysicalConnection] = Field(
        default=None,
        description="Required for action='configure_logical_link'. Physical bus type.",
        examples=["CAN"],
    )
    vendor_name: Optional[str] = Field(
        default=None,
        description="Required for action='select_interface'. Interface vendor name.",
        examples=["dSPACE"],
    )
    interface_name: Optional[str] = Field(
        default=None,
        description="Required for action='select_interface'. Interface name.",
        examples=["Virtual"],
    )
    channel_index: int = Field(
        default=0,
        description="For action='select_interface'. Zero-based channel index.",
        examples=[0],
    )


class DiagDbManageInput(BaseModel):
    """Input for controldesk_ecu_diagnostics_db_manage ADD-ON tool."""

    action: DiagDbManageAction = Field(
        description="'add_file' — add a single ODX file; 'list_files' — list loaded files."
    )
    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    file_path: Optional[str] = Field(
        default=None,
        description="Required for action='add_file'. Absolute path to a single ODX file.",
        examples=["C:\\DiagDemo\\MyECU.odx"],
    )


class DiagVehicleManageInput(BaseModel):
    """Input for controldesk_ecu_diagnostics_vehicle_manage ADD-ON tool."""

    action: DiagVehicleManageAction = Field(
        description="'list_vehicles' — list all vehicles; 'select_vehicle' — select one."
    )
    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    vehicle_name: Optional[str] = Field(
        default=None,
        description="Required for action='select_vehicle'. Vehicle short name.",
        examples=["VI_DemoCar"],
    )


class DiagLinkManageInput(BaseModel):
    """Input for controldesk_ecu_diagnostics_link_manage ADD-ON tool."""

    action: DiagLinkManageAction = Field(
        description=("'list_links', 'select_link', 'configure_link', 'list_interfaces', or 'select_interface'.")
    )
    platform_name: str = Field(
        description="Name of the Diagnostic2 platform.",
        examples=["ECU Diagnostics"],
    )
    link_name: Optional[str] = Field(
        default=None,
        description="Required for select_link, configure_link, list_interfaces, select_interface.",
        examples=["LL_DemoECU"],
    )
    protocol: Optional[ECUDiagnosticsProtocol] = Field(
        default=None,
        description="Required for action='configure_link'.",
        examples=["ISO_14229_UDS"],
    )
    physical_connection: Optional[ECUDiagnosticsPhysicalConnection] = Field(
        default=None,
        description="Required for action='configure_link'.",
        examples=["CAN"],
    )
    vendor_name: Optional[str] = Field(
        default=None,
        description="Required for action='select_interface'.",
        examples=["dSPACE"],
    )
    interface_name: Optional[str] = Field(
        default=None,
        description="Required for action='select_interface'.",
        examples=["Virtual"],
    )
    channel_index: int = Field(
        default=0,
        description="For action='select_interface'. Zero-based channel index.",
        examples=[0],
    )


# ── Discover result ────────────────────────────────────────────────────────────


class DiagDiscoverResult(DictModelMixin, BaseModel):
    """Catalogue of lazy add-on tools returned by controldesk_ecu_diagnostics_discover."""

    tools: list[ToolActionEntry] = Field(
        description="List of available add-on tool entries.",
    )
    hint: str = Field(
        default="",
        description="Usage hint for the catalogue.",
    )
