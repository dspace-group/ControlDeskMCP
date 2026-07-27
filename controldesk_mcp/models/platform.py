"""Pydantic input and response models for the platform management domain.

Domain: ControlDesk platform management (platform_list, platform_add, platform_connect, etc.).

Convention: one models module per domain under controldesk_mcp/models/<domain>.py.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from controldesk_mcp.models.base import DictModelMixin

# ── Enums ─────────────────────────────────────────────────────────────────────


class PlatformCategory(str, Enum):
    """Top-level category as shown in the ControlDesk 'Add Platform' dialog."""

    Device = "Device"
    Platform = "Platform"


class DeviceSubcategory(str, Enum):
    """Sub-category under the Device branch of the ControlDesk platform tree."""

    BusDevice = "BusDevice"
    Diagnostics = "Diagnostics"
    MeasurementAndCalibration = "MeasurementAndCalibration"


class PlatformType(str, Enum):
    """Supported ControlDesk platform types.

    Values match the COM ``PlatformType`` enumeration exactly.
    Source: ControlDesk Automation API PDF p.1981 (2026-A).

    Category mapping (ControlDesk UI "Add Platform" dialog)
    --------------------------------------------------------
    Device > Bus Devices:
        CANMonitoring, EthernetMonitoring, LINMonitoring, FlexRayMonitoring

    Device > GPS Device:
        GNSS

    Device > Diagnostics:
        Diagnostic2

    Device > Measurement & Calibration:
        XCPonCAN, XCPonEthernet, CCP, GSI2

    Platforms (hardware, require registration or direct add):
        SCALEXIO, DS1202, DS1203, DS1403, MABX, DS1104, VEOS, XILAPIMAPort
    """

    # ── Bus Devices ───────────────────────────────────────────────────────
    CANMonitoring = "CANMonitoring"
    EthernetMonitoring = "EthernetMonitoring"
    LINMonitoring = "LINMonitoring"
    FlexRayMonitoring = "FlexRayMonitoring"

    # ── GPS Device ────────────────────────────────────────────────────────
    GNSS = "GNSS"

    # ── Diagnostics ───────────────────────────────────────────────────────
    Diagnostic2 = "Diagnostic2"

    # ── Measurement & Calibration ─────────────────────────────────────────
    XCPonCAN = "XCPonCAN"
    XCPonEthernet = "XCPonEthernet"
    CCP = "CCP"
    GSI2 = "GSI2"

    # ── Hardware platforms ────────────────────────────────────────────────
    SCALEXIO = "SCALEXIO"
    DS1202 = "DS1202"  # MicroLabBox
    DS1203 = "DS1203"  # MicroLabBox II
    DS1403 = "DS1403"  # MicroAutoBox III
    MABX = "MABX"  # MicroAutoBox II (original)
    DS1104 = "DS1104"  # R&D Controller Board (direct-add)
    VEOS = "VEOS"  # Virtual ECU OS
    XILAPIMAPort = "XILAPIMAPort"  # ASAM XIL API MAPort


class ConnectionState(str, Enum):
    """ECU platform connection states."""

    Connected = "Connected"
    Disconnected = "Disconnected"
    Connecting = "Connecting"
    Disconnecting = "Disconnecting"


class OnlineCalibrationBehavior(str, Enum):
    """Startup online-calibration behavior options.

    Values match the COM ``OnlineCalibrationBehavior`` enumeration exactly.
    Source: ControlDesk Automation API PDF p.1899 (2026-A).
    """

    PromptUser = "PromptUser"
    """Always prompt user if differences are detected (value 0)."""
    UploadWorkingPageDownloadReferencePage = "UploadWorkingPageDownloadReferencePage"
    """Upload working page and download reference page if differences detected (value 1)."""
    DownloadWorkingPageUploadReferencePage = "DownloadWorkingPageUploadReferencePage"
    """Download working page and upload reference page if differences detected (value 2)."""
    DownloadWorkingPageDownloadReferencePage = "DownloadWorkingPageDownloadReferencePage"
    """Download working page and reference page if differences detected (value 3)."""
    UploadWorkingPageUploadReferencePage = "UploadWorkingPageUploadReferencePage"
    """Upload working page and reference page if differences detected (value 4)."""
    UploadConnectedVariables = "UploadConnectedVariables"
    """Upload connected variables only (value 5)."""
    IgnoreDifferences = "IgnoreDifferences"
    """Skip balancing; calibrate even if pages differ (value 6)."""
    Upload = "Upload"
    """Upload all variables or memory segments (value 7)."""
    Download = "Download"
    """Download all variables or memory segments (value 8)."""
    DownloadConnectedVariables = "DownloadConnectedVariables"
    """Download connected variables only (value 9)."""


class InitialPageType(str, Enum):
    """Initial memory page type for calibration.

    Values match the COM ``InitialPageType`` enumeration exactly.
    Source: ControlDesk Automation API PDF p.1465-1466 (2026-A).
    """

    ECUDefined = "ECUDefined"
    """Active page on the hardware becomes the active page in ControlDesk (value 0)."""
    WorkingPage = "WorkingPage"
    """Force working page as active page (value 1)."""
    ReferencePage = "ReferencePage"
    """Force reference page as active page (value 2)."""
    ToolDefined = "ToolDefined"
    """Page last active before calibration start or unplug becomes the active page (value 3)."""


class EthernetProtocol(str, Enum):
    """Ethernet transport protocol for XCPonEthernet platforms."""

    UDP = "UDP"
    TCP = "TCP"


class AutomationAPIVersion(str, Enum):
    """Platform automation API version."""

    APIVersion1 = "APIVersion1"
    APIVersion2 = "APIVersion2"


# ── Input models ──────────────────────────────────────────────────────────────


class PlatformListInput(BaseModel):
    """Input for platform_list."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class PlatformListRegisteredHardwareInput(BaseModel):
    """Input for platform_list_registered_hardware."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class PlatformGetInfoInput(BaseModel):
    """Input for platform_get_info."""

    platform_name: str = Field(
        description="Name of the platform to query (e.g., 'XCP', 'SCALEXIO_1'). "
        "Use platform_list to enumerate valid names.",
        examples=["XCP", "SCALEXIO_1"],
    )


class PlatformAddInput(BaseModel):
    """Input for platform_add."""

    platform_type: PlatformType = Field(
        description=(
            "Type of platform to add to the active experiment. "
            "Device types (added directly via platform_add): "
            "CANMonitoring, EthernetMonitoring, LINMonitoring, FlexRayMonitoring "
            "(Bus Devices); "
            "GNSS (GPS Device); "
            "Diagnostic2 (Diagnostics); "
            "XCPonCAN, XCPonEthernet, CCP, GSI2 (Measurement & Calibration). "
            "Also use platform_add for: DS1104 (direct-add hardware) and local VEOS "
            "(Virtual ECU OS running on the same host as ControlDesk). "
            "For IP-addressable hardware (SCALEXIO, DS1202, DS1203, DS1403, MABX), "
            "use platform_register_hardware + platform_activate_registered instead. "
            "For remote VEOS (VEOS on a different host), also use register + activate. "
            "APIVersion2 prerequisite: call platform_set_api_version('APIVersion2') before adding "
            "XCPonEthernet platforms."
        ),
        examples=["XCPonCAN", "CANMonitoring", "Diagnostic2", "VEOS"],
    )


class PlatformAddRegisteredInput(BaseModel):
    """Input for platform_add_registered."""

    unique_name: str = Field(
        description="The unique platform name returned by platform_register_hardware "
        "(e.g., 'SCALEXIO_192.168.140.110'). Do not construct this manually.",
        examples=["SCALEXIO_192.168.140.110", "MABX_192.168.140.200"],
    )


class PlatformRemoveInput(BaseModel):
    """Input for platform_remove."""

    platform_name: str = Field(
        description="Name of the platform to remove (e.g., 'XCP'). "
        "Use platform_list to verify the name. Platform must be disconnected first.",
        examples=["XCP", "SCALEXIO_1"],
    )


class PlatformRegisterHardwareInput(BaseModel):
    """Input for platform_register_hardware."""

    platform_type: PlatformType = Field(
        description=(
            "Hardware type to register. "
            "IP-addressable types (use ip_address): SCALEXIO, DS1202, DS1203, DS1403, MABX. "
            "VEOS: for remote VEOS (running on a different host) provide ip_address; "
            "for local VEOS use platform_add directly instead. "
            "XILAPIMAPort: registration requires a config file path via the "
            "ControlDesk Register Platform dialog — use the ControlDesk UI for this type. "
            "Device types (CANMonitoring, EthernetMonitoring, LINMonitoring, "
            "FlexRayMonitoring, GNSS, Diagnostic2, XCPonCAN, XCPonEthernet, CCP, GSI2) "
            "and DS1104 are added via platform_add — do NOT use platform_register_hardware."
        ),
        examples=["SCALEXIO", "MABX", "DS1202", "VEOS"],
    )
    ip_address: str = Field(
        description=(
            "IPv4 address of the hardware platform in dotted-decimal notation "
            "(e.g., '192.168.140.110'). "
            "Required for: SCALEXIO, DS1202, DS1203, DS1403, MABX, and remote VEOS. "
            "Do not use hostnames or IPv6."
        ),
        examples=["192.168.140.110", "192.168.140.200", "127.0.0.1"],
    )


class PlatformClearRegisteredInput(BaseModel):
    """Input for platform_clear_registered."""

    confirm: bool = Field(
        description=(
            "Must be true to proceed. Acts as a safety guard against accidental invocation. "
            "If false, returns immediately with a warning without making any changes."
        ),
        examples=[True, False],
    )
    force_driver_reset: bool = Field(
        default=False,
        description=(
            "When true, forces a driver reset in addition to clearing registered platforms. "
            "Use true when recovering from a hung or stale hardware state "
            "(e.g., after a crash or failed connection). "
            "Equivalent to ClearSystem(True) in the COM API. "
            "Default is false (safe/non-destructive clear)."
        ),
        examples=[False, True],
    )


class PlatformRefreshConfigurationInput(BaseModel):
    """Input for platform_refresh_configuration."""

    # No parameters — the COM method takes no arguments.
    # Model exists for consistency with the tool framework.
    pass


class PlatformRefreshInterfaceConnectionsInput(BaseModel):
    """Input for platform_refresh_interface_connections."""

    force_driver_reset: bool = Field(
        default=True,
        description=(
            "When true, forces a driver reset as part of the interface refresh. "
            "This resets the hardware interface drivers and re-enumerates all connections. "
            "Use true (the default) to fully recover after a hardware unplug/replug or "
            "after a failed connect attempt. "
            "Use false for a lighter refresh that re-enumerates without resetting drivers."
        ),
        examples=[True, False],
    )


class PlatformSetEnabledInput(BaseModel):
    """Input for platform_set_enabled."""

    platform_name: str = Field(
        description=("Name of the platform to enable or disable. Use platform_list to enumerate valid platform names."),
        examples=["XCP", "SCALEXIO_1"],
    )
    enabled: bool = Field(
        description=(
            "True to enable the platform (default active state); "
            "false to disable the platform. "
            "A disabled platform will not be connected or participate in calibration "
            "on the next experiment start. "
            "Does not disconnect a currently connected platform — "
            "call platform_disconnect first if the platform is connected."
        ),
        examples=[True, False],
    )


class PlatformAddVariableDescriptionInput(BaseModel):
    """Input for platform_add_variable_description."""

    platform_name: str = Field(
        description="Name of the platform to load the variable description into.",
        examples=["XCP", "XCPonEth"],
    )
    file_path: str = Field(
        description=(
            "Absolute path to the variable description file. "
            "The file extension determines the type and COM call used: "
            ".a2l → XCP/CCP/GSI2 calibration database "
            "(a companion .mot is auto-discovered in the same folder; if found, "
            "VariableDescriptions.AddWithImage is called, otherwise .Add); "
            ".sdf → hardware platforms (SCALEXIO, DS1202, DS1203, DS1403, MABX, VEOS); "
            ".dbc → CANMonitoring bus configuration; "
            ".ldf → LINMonitoring bus configuration; "
            ".fibex → FlexRayMonitoring bus configuration; "
            ".arxml → AUTOSAR bus configuration (CANMonitoring, LINMonitoring, "
            "EthernetMonitoring, FlexRayMonitoring)."
        ),
        examples=[
            "C:\\ECU\\myecu.a2l",
            "C:\\ECU\\scalexio_demo.sdf",
            "C:\\BusConfig\\mycan.dbc",
            "C:\\BusConfig\\ethernet.arxml",
        ],
    )


class PlatformConfigureCalibrationBehaviorInput(BaseModel):
    """Input for platform_configure_calibration_behavior."""

    platform_name: str = Field(
        description="Name of the platform to configure.",
        examples=["XCP", "XCPonEth"],
    )
    calibration_behavior: OnlineCalibrationBehavior = Field(
        description=(
            "Startup online-calibration behavior. "
            "PromptUser: always prompt (0). "
            "UploadWorkingPageDownloadReferencePage: upload WP, download RP (1). "
            "DownloadWorkingPageUploadReferencePage: download WP, upload RP (2). "
            "DownloadWorkingPageDownloadReferencePage: download WP and RP (3). "
            "UploadWorkingPageUploadReferencePage: upload WP and RP (4). "
            "UploadConnectedVariables: upload connected variables only (5). "
            "IgnoreDifferences: skip balancing, calibrate with differences (6). "
            "Upload: upload all variables or memory segments (7). "
            "Download: download all variables or memory segments (8). "
            "DownloadConnectedVariables: download connected variables only (9)."
        ),
        examples=["UploadConnectedVariables", "DownloadWorkingPageUploadReferencePage"],
    )
    initial_page: InitialPageType = Field(
        description=(
            "Initial memory page after calibration start or automatic reconnect. "
            "ECUDefined: page currently active on hardware (0). "
            "WorkingPage: force working page (1). "
            "ReferencePage: force reference page (2). "
            "ToolDefined: page last active before calibration start/unplug (3)."
        ),
        examples=["WorkingPage", "ECUDefined"],
    )


class PlatformSetApiVersionInput(BaseModel):
    """Input for platform_set_api_version."""

    version: AutomationAPIVersion = Field(
        description="APIVersion1 (default, all platforms except XCPonEthernet) or "
        "APIVersion2 (required for XCPonEthernet). "
        "Must be called before platform_add(type='XCPonEthernet').",
        examples=["APIVersion2", "APIVersion1"],
    )


class PlatformConfigureTransportInput(BaseModel):
    """Input for platform_configure_transport."""

    platform_name: str = Field(
        description="Name of the platform to configure (e.g., 'XCP', 'XCPonEth').",
        examples=["XCP", "XCPonEth"],
    )
    baud_rate: Optional[int] = Field(
        default=None,
        description="CAN baud rate in bits/s (e.g., 100000, 500000, 1000000). "
        "Applies to XCPonCAN only. Must match ECU firmware CAN baud rate.",
        examples=[500000, 100000, 1000000],
    )
    ethernet_protocol: Optional[EthernetProtocol] = Field(
        default=None,
        description="Ethernet transport protocol: 'TCP' or 'UDP'. Applies to XCPonEthernet only.",
        examples=["TCP", "UDP"],
    )
    automatic_adapter: Optional[bool] = Field(
        default=None,
        description="Ethernet adapter assignment mode. True = auto-select (recommended); "
        "False = manual selection via adapter_name. Applies to XCPonEthernet only.",
        examples=[True, False],
    )
    adapter_name: Optional[str] = Field(
        default=None,
        description="Network adapter description string. Required when automatic_adapter=False. "
        "Applies to XCPonEthernet only.",
        examples=["Intel(R) Ethernet Connection I217-LM"],
    )


class PlatformListInterfacesInput(BaseModel):
    """Input for platform_list_interfaces."""

    platform_name: str = Field(
        description=(
            "Name of the platform to query for available hardware interfaces. "
            "Applies to platforms with CAN-bus interface selection: "
            "XCPonCAN, CANMonitoring, LINMonitoring, FlexRayMonitoring, CCP. "
            "EthernetMonitoring: uses IPmEthernetInterfaceSelection (separate COM interface). "
            "For EthernetMonitoring, use platform_configure_transport instead."
        ),
        examples=["XCP", "CAN_1"],
    )


class PlatformSelectInterfaceManualInput(BaseModel):
    """Input for platform_select_interface_manual."""

    platform_name: str = Field(
        description=(
            "Name of the platform to configure (e.g., 'XCP', 'CAN_1'). "
            "Applies to CAN-bus platforms: "
            "XCPonCAN, CANMonitoring, LINMonitoring, FlexRayMonitoring, CCP. "
            "EthernetMonitoring uses a separate interface selection path "
            "— use platform_configure_transport."
        ),
        examples=["XCP", "CAN_1"],
    )
    vendor_name: str = Field(
        description="Vendor name (e.g., 'dSPACE', 'Peak', 'Vector'). Must match a value from platform_list_interfaces.",
        examples=["dSPACE", "Peak"],
    )
    interface_name: str = Field(
        description="Interface name (e.g., 'Virtual', 'DS2211', 'PCAN-USB'). "
        "Must match a value from platform_list_interfaces.",
        examples=["Virtual", "DS2211"],
    )
    channel_index: int = Field(
        description="Zero-based channel index (0 to channel_count-1).",
        examples=[0, 1],
    )


class PlatformConnectInput(BaseModel):
    """Input for platform_connect."""

    platform_name: str = Field(
        description="Name of the platform to connect (e.g., 'XCP', 'SCALEXIO_1'). "
        "Platform must be in Disconnected state. "
        "For CAN platforms, platform_select_interface_manual must have been called first.",
        examples=["XCP", "SCALEXIO_1"],
    )


class PlatformDisconnectInput(BaseModel):
    """Input for platform_disconnect."""

    platform_name: str = Field(
        description="Name of the platform to disconnect (e.g., 'XCP', 'SCALEXIO_1'). "
        "Always call calibration_stop before disconnecting.",
        examples=["XCP", "SCALEXIO_1"],
    )


class PlatformGetConnectionStateInput(BaseModel):
    """Input for platform_get_connection_state."""

    platform_name: str = Field(
        description="Name of the platform to query (e.g., 'XCP', 'SCALEXIO_1'). "
        "Use platform_list to enumerate valid names.",
        examples=["XCP", "SCALEXIO_1"],
    )


class PlatformConfigureInput(BaseModel):
    """Input for platform_configure.

    All fields except ``platform_name`` are optional — supply only the ones
    relevant to the platform type.  The server selects the correct COM path
    based on the platform's actual type.

    CAN-interface platforms (XCPonCAN, CCP, CANMonitoring, LINMonitoring, FlexRayMonitoring)
        Use ``can_interface``.

    Hardware platforms with SMART assignment (SCALEXIO, DS1202/MLBX, DS1203/MLBXII, DS1403/MABXIII)
        Use ``ip_address`` and/or ``mac_address`` and/or ``board_name`` together with
        ``assignment_mode``.

    MABX
        Use ``ip_address`` for Net connection; omit for Bus connection.

    VEOS
        Use ``ip_address`` (defaults to 127.0.0.1 if omitted).

    DS1104 / DS1005 / DS1006 / DS1007
        Use ``assignment_mode`` + optionally ``board_name``.
        For Identical mode pass the serial number as ``mac_address``.

    All platform types
        Use ``calibration_behavior`` to set the online-calibration startup action.
    """

    platform_name: str = Field(
        description="Name of the platform to configure. Use platform_list to enumerate names.",
        examples=["XCP", "SCALEXIO_1", "MABX_1"],
    )
    can_interface: Optional[str] = Field(
        default=None,
        description=(
            "CAN interface to select. Pass 'Virtual' to use the dSPACE Virtual interface, "
            "'Automatic' to enable automatic assignment, or an exact interface name "
            "(e.g. 'DS4302') to select it. "
            "Applies to: XCPonCAN, CCP, CANMonitoring, LINMonitoring, FlexRayMonitoring. "
            "Use platform_list_interfaces to discover valid names."
        ),
        examples=["Virtual", "Automatic", "DS4302"],
    )
    ip_address: Optional[str] = Field(
        default=None,
        description=(
            "IP address of the hardware unit. "
            "For SMART-assignment platforms (SCALEXIO, DS1202, DS1203, DS1403): "
            "sets Assignment.Assignments[0].IPAddress (mutually exclusive with board_name). "
            "For MABX: sets Assignment.NetClient and switches to Net connection. "
            "For VEOS: sets Assignment.NetClient (default 127.0.0.1)."
        ),
        examples=["192.168.140.110", "127.0.0.1"],
    )
    mac_address: Optional[str] = Field(
        default=None,
        description=(
            "MAC address for SMART-assignment platforms "
            "(SCALEXIO, DS1202, DS1203, DS1403) when assignment_mode='Identical'. "
            "For DS1104 family: treated as the hardware serial number."
        ),
        examples=["00:1A:2B:3C:4D:5E"],
    )
    board_name: Optional[str] = Field(
        default=None,
        description=(
            "Board name to filter the hardware unit. "
            "For SMART-assignment platforms: sets Assignment.Assignments[0].BoardName "
            "(mutually exclusive with ip_address). "
            "For DS1104 family: sets Assignment.BoardName."
        ),
        examples=["ds1202", "ds1104"],
    )
    assignment_mode: Optional[str] = Field(
        default=None,
        description=(
            "Assignment mode for hardware platforms. "
            "'FirstAvailable' — connect to the first available unit. "
            "'AnyEqual' — connect to any unit matching board_name or ip_address. "
            "'Identical' — connect to the exact unit identified by mac_address/serial_number. "
            "Applies to: SCALEXIO, DS1202, DS1203, DS1403, MABX, DS1104 family."
        ),
        examples=["AnyEqual", "FirstAvailable", "Identical"],
    )
    calibration_behavior: Optional[str] = Field(
        default=None,
        description=(
            "Online calibration startup behavior. Applies to all platform types. "
            "Valid values: 'PromptUser', 'UploadWP_DownloadRP', 'DownloadWP_UploadRP', "
            "'DownloadWP_DownloadRP', 'UploadWP_UploadRP', 'UploadConnectedVariables', "
            "'IgnoreDifferences', 'Upload', 'Download', 'DownloadConnectedVariables'."
        ),
        examples=["UploadConnectedVariables", "PromptUser"],
    )


class PlatformRenameInput(BaseModel):
    """Input for platform_rename."""

    platform_name: str = Field(
        description="Current name of the platform to rename. Use platform_list to enumerate valid names.",
        examples=["XCP", "SCALEXIO_1"],
    )
    new_name: str = Field(
        description="New name to assign to the platform. Must be unique within the experiment.",
        examples=["XCP_CalDemo", "SCALEXIO_Main"],
    )


# ── Result models (Category B — COM bridge returns raw dicts) ─────────────────


class PlatformListResult(DictModelMixin, BaseModel):
    """Special case: COM bridge returns a raw list; wrap it here."""

    model_config = {"extra": "allow"}
    platforms: list[dict] = []


class PlatformGetInfoResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    name: str
    type: str
    connection_state: str
    measurement_state: str
    variable_description_count: int


class PlatformAddResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    added: bool
    platform_name: str
    platform_type: str


class PlatformAddRegisteredResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    added: bool
    unique_name: str


class PlatformRemoveResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    platform_name: str
    removed: bool


class PlatformRegisterHardwareResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    registered: bool
    unique_name: str
    display_name: str
    platform_type: str
    ip_address: str


class PlatformListRegisteredHardwareResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    registered_platforms: list[dict] = []
    count: int


class PlatformGetRegisteredInfoResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    index: int
    unique_name: str


class PlatformClearRegisteredResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    cleared: bool
    force_driver_reset: bool
    message: str


class PlatformClearRegisteredAborted(DictModelMixin, BaseModel):
    cleared: Literal[False] = False
    message: str = "Operation aborted. Set 'confirm' to true to proceed with clearing all registered platforms."


class PlatformRefreshConfigurationResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    refreshed: bool
    operation: str


class PlatformRefreshInterfaceConnectionsResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    refreshed: bool
    operation: str
    force_driver_reset: bool


class PlatformSetEnabledResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    platform_name: str
    enabled: bool


class PlatformAddVariableDescriptionResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    added: bool
    platform_name: str
    variable_description_name: str
    file_path: str


class PlatformConfigureCalibrationBehaviorResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    platform_name: str
    calibration_behavior: str
    initial_page: str


class PlatformSetApiVersionResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    version_string: str
    version_integer: int
    configured: bool


class PlatformConfigureTransportResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    platform_name: str


class PlatformListInterfacesResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    interfaces: list[dict] = []
    total_count: int


class PlatformSelectInterfaceManualResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    selected: bool
    platform_name: str
    interface_name: str


class PlatformConnectResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    connected: bool
    platform_name: str
    connection_state: str
    timestamp_utc: str


class PlatformDisconnectResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    disconnected: bool
    platform_name: str
    connection_state: str
    timestamp_utc: str


class PlatformGetConnectionStateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    platform_name: str
    connection_state: str
    is_connected: bool
    timestamp_utc: str


class PlatformConfigureResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    configured: bool
    platform_name: str


class PlatformRenameResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    renamed: bool
    platform_name: str
    new_name: str
    timestamp_utc: str


class PlatformListTypesResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    categories: list[dict] = []
    usage_note: str = ""


class PlatformListHardwareTypesResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    hardware_types: list[dict] = []
    total_count: int


# ── Consolidated action enums ─────────────────────────────────────────────────


class PlatformQueryAction(str, Enum):
    """Read-only query actions for platform_query tool."""

    list = "list"
    get_info = "get_info"
    get_connection_state = "get_connection_state"
    list_interfaces = "list_interfaces"
    list_types = "list_types"
    list_hardware_types = "list_hardware_types"


class PlatformManageAction(str, Enum):
    """Mutating actions for platform_manage tool (state-changing only)."""

    add = "add"
    activate_registered = "activate_registered"
    configure = "configure"
    configure_calibration_behavior = "configure_calibration_behavior"
    configure_transport = "configure_transport"
    set_api_version = "set_api_version"
    select_interface_manual = "select_interface_manual"
    add_variable_description = "add_variable_description"


class PlatformAdminManageAction(str, Enum):
    remove = "remove"
    rename = "rename"
    set_enabled = "set_enabled"


class PlatformHardwareManageAction(str, Enum):
    register_hardware = "register_hardware"
    clear_registered = "clear_registered"
    list_registered_hardware = "list_registered_hardware"
    get_registered_info = "get_registered_info"
    refresh_configuration = "refresh_configuration"
    refresh_interface_connections = "refresh_interface_connections"


# ── Consolidated input models ─────────────────────────────────────────────────


class PlatformQueryInput(BaseModel):
    """Input for platform_query (read-only actions)."""

    action: PlatformQueryAction
    platform_name: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=200, ge=1, le=1000)


class PlatformManageInput(BaseModel):
    """Consolidated input for platform_manage (mutating actions only)."""

    action: PlatformManageAction
    platform_name: Optional[str] = None
    platform_type: Optional[PlatformType] = None
    unique_name: Optional[str] = None
    can_interface: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    board_name: Optional[str] = None
    assignment_mode: Optional[str] = None
    calibration_behavior: Optional[str] = None
    initial_page: Optional[InitialPageType] = None
    ethernet_protocol: Optional[EthernetProtocol] = None
    automatic_adapter: Optional[bool] = None
    adapter_name: Optional[str] = None
    baud_rate: Optional[int] = None
    version: Optional[AutomationAPIVersion] = None
    vendor_name: Optional[str] = None
    interface_name: Optional[str] = None
    channel_index: Optional[int] = None
    file_path: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=200, ge=1, le=1000)


class PlatformHardwareManageInput(BaseModel):
    """Consolidated input for platform_hardware_manage."""

    action: PlatformHardwareManageAction
    platform_type: Optional[PlatformType] = None
    ip_address: Optional[str] = None
    confirm: Optional[bool] = None
    force_driver_reset: bool = True
    index: Optional[int] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=200, ge=1, le=1000)


class PlatformAdminManageInput(BaseModel):
    """Consolidated input for platform_admin_manage."""

    action: PlatformAdminManageAction
    platform_name: Optional[str] = Field(
        default=None,
        description=("Name of the platform. Required for: remove, rename, set_enabled."),
        examples=["XCP", "SCALEXIO_1"],
    )
    new_name: Optional[str] = Field(
        default=None,
        description="Required for action='rename'. New unique name for the platform.",
        examples=["XCP_CalDemo"],
    )
    enabled: Optional[bool] = Field(
        default=None,
        description="Required for action='set_enabled'. True to enable; False to disable.",
        examples=[True, False],
    )


# ── Discovery models ──────────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    tool_name: str
    purpose: str
    actions: list[str] = []
    required_params_per_action: dict[str, list[str]] = {}


class PlatformDiscoverResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry] = []
