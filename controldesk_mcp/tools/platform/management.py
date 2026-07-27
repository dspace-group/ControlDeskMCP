"""MCP tools for ControlDesk platform management.

Tools implemented (domain: platform management):

  MAIN (always loaded):
    platform_connect    — Establish the ECU communication link
    platform_disconnect — Release the ECU communication link
    platform_manage     — All platform configuration/query operations (14 actions)

  ADD_ON lazy (access via platform_discover):
    GROUP: ADMIN
      platform_admin_manage — Admin operations: remove, rename, set_enabled

    GROUP: HARDWARE
      platform_hardware_manage — Hardware registry operations: register_hardware,
                                  clear_registered, list_registered_hardware,
                                  get_registered_info, refresh_configuration,
                                  refresh_interface_connections

  META / Discovery:
    platform_discover — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.platform_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.platform import (
    PlatformAddInput,
    PlatformAddRegisteredInput,
    PlatformAddRegisteredResult,
    PlatformAddResult,
    PlatformAddVariableDescriptionInput,
    PlatformAddVariableDescriptionResult,
    PlatformAdminManageAction,
    PlatformAdminManageInput,
    PlatformClearRegisteredAborted,
    PlatformClearRegisteredInput,
    PlatformClearRegisteredResult,
    PlatformConfigureCalibrationBehaviorInput,
    PlatformConfigureCalibrationBehaviorResult,
    PlatformConfigureInput,
    PlatformConfigureResult,
    PlatformConfigureTransportInput,
    PlatformConfigureTransportResult,
    PlatformConnectInput,
    PlatformConnectResult,
    PlatformDisconnectInput,
    PlatformDisconnectResult,
    PlatformDiscoverResult,
    PlatformGetConnectionStateInput,
    PlatformGetConnectionStateResult,
    PlatformGetInfoInput,
    PlatformGetInfoResult,
    PlatformGetRegisteredInfoResult,
    PlatformHardwareManageAction,
    PlatformHardwareManageInput,
    PlatformListHardwareTypesResult,
    PlatformListInterfacesInput,
    PlatformListInterfacesResult,
    PlatformListRegisteredHardwareResult,
    PlatformListResult,
    PlatformListTypesResult,
    PlatformManageAction,
    PlatformManageInput,
    PlatformQueryAction,
    PlatformQueryInput,
    PlatformRefreshConfigurationInput,
    PlatformRefreshConfigurationResult,
    PlatformRefreshInterfaceConnectionsInput,
    PlatformRefreshInterfaceConnectionsResult,
    PlatformRegisterHardwareInput,
    PlatformRegisterHardwareResult,
    PlatformRemoveInput,
    PlatformRemoveResult,
    PlatformRenameInput,
    PlatformRenameResult,
    PlatformSelectInterfaceManualInput,
    PlatformSelectInterfaceManualResult,
    PlatformSetApiVersionInput,
    PlatformSetApiVersionResult,
    PlatformSetEnabledInput,
    PlatformSetEnabledResult,
    ToolActionEntry,
)
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import platform_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — platform_connect ─────────────────────────────────────────────────


@mcp.tool(
    name="platform_connect",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Establishes the physical or virtual communication link between ControlDesk and "
        "a specific ECU/platform in the active experiment. This is the final setup step "
        "before online calibration can begin. "
        "Prerequisites by platform type: "
        "CAN platforms (XCPonCAN, CCP): platform_manage(action='select_interface_manual') or "
        "platform_manage(action='configure', can_interface=...) MUST be called first. "
        "CANMonitoring/LINMonitoring/FlexRayMonitoring: AutomaticAssignment=True by default "
        "(physical CAN only); for virtual CAN call platform_manage(action='configure', "
        "can_interface='Virtual') BEFORE connecting. "
        "Hardware platforms (SCALEXIO, DS1202, DS1203, DS1403, MABX): variable description must "
        "be loaded and hardware powered; "
        "VEOS: process must be running (default IP 127.0.0.1) and variable description loaded; "
        "XCPonEthernet: configure adapter via platform_manage(action='configure_transport') first. "
        "After connect, call platform_manage(action='get_connection_state') to verify."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.PLATFORM, ToolGroup.CONNECTIVITY),
)
async def platform_connect(params: PlatformConnectInput) -> PlatformConnectResult | ErrorEnvelope:
    return await platform_service.connect_platform(params)


# ── Tool 2 — platform_disconnect ──────────────────────────────────────────────


@mcp.tool(
    name="platform_disconnect",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Releases the communication link between ControlDesk and a specific ECU/platform. "
        "Must be called after calibration_stop — disconnecting while calibration is running "
        "will cause data loss. "
        "Disconnecting an already-disconnected platform is a safe no-op (idempotent)."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.PLATFORM, ToolGroup.CONNECTIVITY),
)
async def platform_disconnect(
    params: PlatformDisconnectInput,
) -> PlatformDisconnectResult | ErrorEnvelope:
    return await platform_service.disconnect_platform(params)


# ── Tool 3 — platform_manage ──────────────────────────────────────────────────


@mcp.tool(
    name="platform_manage",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages all platform configuration operations (mutating only). "
        "Set 'action' to specify what to do: "
        "'add' — add a new platform (requires platform_type; replay risk: repeating 'add' "
        "with the same platform_type is not guaranteed safe and can create a duplicate platform "
        "entry or fail, so check platform_query(action='list') first); "
        "'activate_registered' — attach registered hardware to experiment (requires unique_name); "
        "'configure' — set CAN interface or hardware assignment (requires platform_name + fields); "
        "'configure_calibration_behavior' — set startup page behavior "
        "(requires platform_name + calibration_behavior + initial_page); "
        "'configure_transport' — CAN baud rate or Ethernet adapter settings (requires platform_name); "
        "'set_api_version' — set automation API version (requires version); "
        "'select_interface_manual' — select CAN vendor/interface/channel "
        "(requires platform_name + vendor_name + interface_name + channel_index); "
        "'add_variable_description' — load A2L/SDF/DBC/LDF variable description "
        "(requires platform_name + file_path). "
        "Use platform_discover to query platforms, list types, and list interfaces (platform_query). "
        "For admin operations (remove, rename, set_enabled) use platform_admin_manage. "
        "For hardware registry operations use platform_hardware_manage."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.PLATFORM, ToolGroup.CONFIGURATION),
)
async def platform_manage(
    params: PlatformManageInput,
) -> (
    PlatformAddResult
    | PlatformAddRegisteredResult
    | PlatformConfigureResult
    | PlatformConfigureCalibrationBehaviorResult
    | PlatformConfigureTransportResult
    | PlatformSetApiVersionResult
    | PlatformSelectInterfaceManualResult
    | PlatformAddVariableDescriptionResult
    | ErrorEnvelope
):
    action = params.action

    if action == PlatformManageAction.add:
        if params.platform_type is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_type is required for add.",
                recovery_hint="Set platform_type to the type of platform to add.",
            )
        return await platform_service.add_platform(PlatformAddInput(platform_type=params.platform_type))

    if action == PlatformManageAction.activate_registered:
        if params.unique_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="unique_name is required for activate_registered.",
                recovery_hint="Set unique_name returned by platform_hardware_manage register_hardware.",
            )
        return await platform_service.add_registered_platform(
            PlatformAddRegisteredInput(unique_name=params.unique_name)
        )

    if action == PlatformManageAction.configure:
        if params.platform_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name is required for configure.",
                recovery_hint="Set platform_name to the name of the platform to configure.",
            )
        return await platform_service.configure_platform(
            PlatformConfigureInput(
                platform_name=params.platform_name,
                can_interface=params.can_interface,
                ip_address=params.ip_address,
                mac_address=params.mac_address,
                board_name=params.board_name,
                assignment_mode=params.assignment_mode,
                calibration_behavior=params.calibration_behavior,
            )
        )

    if action == PlatformManageAction.configure_calibration_behavior:
        if params.platform_name is None or params.calibration_behavior is None or params.initial_page is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message=(
                    "platform_name, calibration_behavior, and initial_page are required "
                    "for configure_calibration_behavior."
                ),
                recovery_hint="Set all three required fields.",
            )
        from controldesk_mcp.models.platform import OnlineCalibrationBehavior

        return await platform_service.configure_calibration_behavior(
            PlatformConfigureCalibrationBehaviorInput(
                platform_name=params.platform_name,
                calibration_behavior=OnlineCalibrationBehavior(params.calibration_behavior),
                initial_page=params.initial_page,
            )
        )

    if action == PlatformManageAction.configure_transport:
        if params.platform_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name is required for configure_transport.",
                recovery_hint="Set platform_name to the name of the platform to configure.",
            )
        return await platform_service.configure_transport(
            PlatformConfigureTransportInput(
                platform_name=params.platform_name,
                baud_rate=params.baud_rate,
                ethernet_protocol=params.ethernet_protocol,
                automatic_adapter=params.automatic_adapter,
                adapter_name=params.adapter_name,
            )
        )

    if action == PlatformManageAction.set_api_version:
        if params.version is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="version is required for set_api_version.",
                recovery_hint="Set version to 'APIVersion1' or 'APIVersion2'.",
            )
        return await platform_service.set_api_version(PlatformSetApiVersionInput(version=params.version))

    if action == PlatformManageAction.select_interface_manual:
        if (
            params.platform_name is None
            or params.vendor_name is None
            or params.interface_name is None
            or params.channel_index is None
        ):
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message=(
                    "platform_name, vendor_name, interface_name, and channel_index "
                    "are required for select_interface_manual."
                ),
                recovery_hint="Set all four required fields.",
            )
        return await platform_service.select_interface_manual(
            PlatformSelectInterfaceManualInput(
                platform_name=params.platform_name,
                vendor_name=params.vendor_name,
                interface_name=params.interface_name,
                channel_index=params.channel_index,
            )
        )

    if action == PlatformManageAction.add_variable_description:
        if params.platform_name is None or params.file_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name and file_path are required for add_variable_description.",
                recovery_hint="Set platform_name and file_path to the variable description file.",
            )
        return await platform_service.add_variable_description(
            PlatformAddVariableDescriptionInput(platform_name=params.platform_name, file_path=params.file_path)
        )

    return ErrorEnvelope(
        error_code="INVALID_ACTION",
        category="INPUT_VALIDATION",
        message=f"Unknown action '{params.action}' for platform_manage.",
        recovery_hint=(
            "Valid mutating actions: add, activate_registered, configure, "
            "configure_calibration_behavior, configure_transport, set_api_version, "
            "select_interface_manual, add_variable_description."
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via platform_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: PLATFORM_QUERY ───────────────────────────────────────────────────────────
# ── Tool 4 — platform_query ─────────────────────────────────────────────────────


@mcp.tool(
    name="platform_query",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Read-only queries for platforms (readOnlyHint=true). "
        "Set 'action' to specify what to do: "
        "'list' — enumerate all platforms in the active experiment (paginated); "
        "'get_info' — detailed metadata for a named platform (requires platform_name); "
        "'get_connection_state' — query connection state (requires platform_name); "
        "'list_interfaces' — list CAN vendors and channels (requires platform_name); "
        "'list_types' — catalog of all supported platform type names; "
        "'list_hardware_types' — catalog of hardware types and registration requirements. "
        "Use platform_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.PLATFORM, ToolGroup.CONFIGURATION),
)
async def platform_query(
    params: PlatformQueryInput,
) -> (
    PlatformListResult
    | PlatformGetInfoResult
    | PlatformGetConnectionStateResult
    | PlatformListInterfacesResult
    | PlatformListTypesResult
    | PlatformListHardwareTypesResult
    | ErrorEnvelope
):
    action = params.action

    if action == PlatformQueryAction.list:
        result = await platform_service.list_platforms()
        if isinstance(result, ErrorEnvelope):
            return result
        return PlatformListResult(**paginate(result.model_dump(), params.offset, params.limit, "platforms"))

    if action == PlatformQueryAction.get_info:
        if params.platform_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name is required for get_info.",
                recovery_hint="Set platform_name to the name of the platform to query.",
            )
        return await platform_service.get_platform_info(PlatformGetInfoInput(platform_name=params.platform_name))

    if action == PlatformQueryAction.get_connection_state:
        if params.platform_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name is required for get_connection_state.",
                recovery_hint="Set platform_name to the name of the platform to query.",
            )
        return await platform_service.get_connection_state(
            PlatformGetConnectionStateInput(platform_name=params.platform_name)
        )

    if action == PlatformQueryAction.list_interfaces:
        if params.platform_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name is required for list_interfaces.",
                recovery_hint="Set platform_name to enumerate its available interfaces.",
            )
        return await platform_service.list_interfaces(PlatformListInterfacesInput(platform_name=params.platform_name))

    if action == PlatformQueryAction.list_types:
        return await platform_service.list_platform_types()

    # list_hardware_types
    return await platform_service.list_hardware_types()


# ── GROUP: ADMIN ─────────────────────────────────────────────────────────────────
# ── Tool 5 — platform_admin_manage ───────────────────────────────────────────────


@mcp.tool(
    name="platform_admin_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Performs administrative operations on platforms in the active experiment. "
        "Set 'action' to specify what to do: "
        "'remove' — remove a platform from the experiment (requires platform_name; "
        "platform must be disconnected first); "
        "'rename' — rename a platform (requires platform_name + new_name; "
        "new name must be unique within the experiment); "
        "'set_enabled' — enable or disable a platform (requires platform_name + enabled; "
        "does not disconnect a currently connected platform). "
        "For lifecycle operations (connect, disconnect) use platform_connect/platform_disconnect. "
        "For configuration use platform_manage."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.PLATFORM, ToolGroup.CONFIGURATION),
)
async def platform_admin_manage(
    params: PlatformAdminManageInput,
) -> PlatformRemoveResult | PlatformRenameResult | PlatformSetEnabledResult | ErrorEnvelope:
    if params.action == PlatformAdminManageAction.remove:
        if params.platform_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name is required for remove.",
                recovery_hint="Set platform_name to the name of the platform to remove.",
            )
        return await platform_service.remove_platform(PlatformRemoveInput(platform_name=params.platform_name))

    if params.action == PlatformAdminManageAction.rename:
        if params.platform_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_name is required for rename.",
                recovery_hint="Set platform_name to the current name of the platform.",
            )
        if params.new_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="new_name is required for rename.",
                recovery_hint="Set new_name to the desired new name for the platform.",
            )
        return await platform_service.rename_platform(
            PlatformRenameInput(platform_name=params.platform_name, new_name=params.new_name)
        )

    # set_enabled
    if params.platform_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="platform_name is required for set_enabled.",
            recovery_hint="Set platform_name to the name of the platform.",
        )
    if params.enabled is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="enabled is required for set_enabled.",
            recovery_hint="Set enabled=true to enable or enabled=false to disable the platform.",
        )
    return await platform_service.set_platform_enabled(
        PlatformSetEnabledInput(platform_name=params.platform_name, enabled=params.enabled)
    )


# ── GROUP: HARDWARE ───────────────────────────────────────────────────────────
# ── Tool 5 — platform_hardware_manage ────────────────────────────────────────


@mcp.tool(
    name="platform_hardware_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages hardware platform registry operations. "
        "Set 'action' to specify what to do: "
        "'register_hardware' — register IP-addressable hardware (requires platform_type + ip_address); "
        "'clear_registered' — remove ALL registered platforms (requires confirm=true; destructive); "
        "'list_registered_hardware' — enumerate registered platforms (paginated); "
        "'get_registered_info' — metadata for a registered platform by index (requires index); "
        "'refresh_configuration' — re-read platform configuration from hardware; "
        "'refresh_interface_connections' — re-enumerate hardware interface connections "
        "(force_driver_reset=true by default). "
        "IP-addressable types: SCALEXIO, DS1202, DS1203, DS1403, MABX, remote VEOS."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.PLATFORM, ToolGroup.HARDWARE),
)
async def platform_hardware_manage(
    params: PlatformHardwareManageInput,
) -> (
    PlatformRegisterHardwareResult
    | PlatformClearRegisteredResult
    | PlatformClearRegisteredAborted
    | PlatformListRegisteredHardwareResult
    | PlatformGetRegisteredInfoResult
    | PlatformRefreshConfigurationResult
    | PlatformRefreshInterfaceConnectionsResult
    | ErrorEnvelope
):
    action = params.action

    if action == PlatformHardwareManageAction.register_hardware:
        if params.platform_type is None or params.ip_address is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="platform_type and ip_address are required for register_hardware.",
                recovery_hint="Set platform_type (e.g., 'SCALEXIO') and ip_address.",
            )
        return await platform_service.register_hardware_platform(
            PlatformRegisterHardwareInput(platform_type=params.platform_type, ip_address=params.ip_address)
        )

    if action == PlatformHardwareManageAction.clear_registered:
        if params.confirm is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="confirm is required for clear_registered.",
                recovery_hint="Set confirm=true to proceed or confirm=false to get a warning.",
            )
        return await platform_service.clear_registered_platforms(
            PlatformClearRegisteredInput(confirm=params.confirm, force_driver_reset=params.force_driver_reset)
        )

    if action == PlatformHardwareManageAction.list_registered_hardware:
        result = await platform_service.list_registered_hardware()
        if isinstance(result, ErrorEnvelope):
            return result
        return PlatformListRegisteredHardwareResult(
            **paginate(result.model_dump(), params.offset, params.limit, "registered_platforms")
        )

    if action == PlatformHardwareManageAction.get_registered_info:
        if params.index is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="index is required for get_registered_info.",
                recovery_hint="Set index to the zero-based registry index.",
            )
        return await platform_service.get_registered_info(params.index)

    if action == PlatformHardwareManageAction.refresh_configuration:
        return await platform_service.refresh_platform_configuration(PlatformRefreshConfigurationInput())

    # refresh_interface_connections
    return await platform_service.refresh_interface_connections(
        PlatformRefreshInterfaceConnectionsInput(force_driver_reset=params.force_driver_reset)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 5 — platform_discover ────────────────────────────────────────────────


@mcp.tool(
    name="platform_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available platform operations "
        "that are not loaded by default. Call this tool first when you need to perform "
        "admin operations on platforms (remove, rename, set_enabled) or hardware registry "
        "operations (register, clear, refresh). "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.PLATFORM, ToolGroup.CONFIGURATION),
)
async def platform_discover(ctx: Context) -> PlatformDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.PLATFORM, ctx)
    return PlatformDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="platform_query",
                purpose=(
                    "Read-only queries: list platforms, get info, get connection state, "
                    "list interfaces, list types, list hardware types."
                ),
                actions=[
                    "list",
                    "get_info",
                    "get_connection_state",
                    "list_interfaces",
                    "list_types",
                    "list_hardware_types",
                ],
                required_params_per_action={
                    "list": [],
                    "get_info": ["platform_name"],
                    "get_connection_state": ["platform_name"],
                    "list_interfaces": ["platform_name"],
                    "list_types": [],
                    "list_hardware_types": [],
                },
            ),
            ToolActionEntry(
                tool_name="platform_admin_manage",
                purpose=("Perform administrative operations on platforms: remove, rename, set_enabled."),
                actions=["remove", "rename", "set_enabled"],
                required_params_per_action={
                    "remove": ["platform_name"],
                    "rename": ["platform_name", "new_name"],
                    "set_enabled": ["platform_name", "enabled"],
                },
            ),
            ToolActionEntry(
                tool_name="platform_hardware_manage",
                purpose=(
                    "Manage hardware platform registry: register, clear, list, inspect, and refresh hardware platforms."
                ),
                actions=[
                    "register_hardware",
                    "clear_registered",
                    "list_registered_hardware",
                    "get_registered_info",
                    "refresh_configuration",
                    "refresh_interface_connections",
                ],
                required_params_per_action={
                    "register_hardware": ["platform_type", "ip_address"],
                    "clear_registered": ["confirm"],
                    "list_registered_hardware": [],
                    "get_registered_info": ["index"],
                    "refresh_configuration": [],
                    "refresh_interface_connections": [],
                },
            ),
        ]
    )
