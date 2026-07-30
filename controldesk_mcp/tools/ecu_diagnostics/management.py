"""MCP tools for ControlDesk ECU Diagnostics (Diagnostic2) platform.

Tools implemented (domain: ecu_diagnostics):

  MAIN (always loaded, ≤ 3):
    controldesk_ecu_diagnostics_setup      — ODX database setup actions:
                                             add_odx_directory, list_odx_files
    controldesk_ecu_diagnostics_link_setup — Vehicle + logical-link + interface setup:
                                             list_vehicles, select_vehicle,
                                             list_logical_links, select_logical_link,
                                             configure_logical_link, list_interfaces,
                                             select_interface
    controldesk_ecu_diagnostics_discover   — Returns catalogue of lazy add-on tools

  ADD_ON lazy (access via controldesk_ecu_diagnostics_discover):
    GROUP: DATABASE_MANAGEMENT
      controldesk_ecu_diagnostics_db_manage      — add_file, list_files

    GROUP: VEHICLE_MANAGEMENT
      controldesk_ecu_diagnostics_vehicle_manage — list_vehicles, select_vehicle

    GROUP: LINK_MANAGEMENT
      controldesk_ecu_diagnostics_link_manage    — list_links, select_link,
                                                   configure_link, list_interfaces,
                                                   select_interface

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.ecu_diagnostics_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.ecu_diagnostics import (
    DiagAddOdxDirectoryInput,
    DiagAddOdxDirectoryResult,
    DiagAddOdxFileInput,
    DiagAddOdxFileResult,
    DiagConfigureLogicalLinkInput,
    DiagConfigureLogicalLinkResult,
    DiagDbManageAction,
    DiagDbManageInput,
    DiagDiscoverResult,
    DiagLinkManageAction,
    DiagLinkManageInput,
    DiagLinkSetupAction,
    DiagLinkSetupInput,
    DiagListInterfacesInput,
    DiagListInterfacesResult,
    DiagListLogicalLinksInput,
    DiagListLogicalLinksResult,
    DiagListOdxFilesInput,
    DiagListOdxFilesResult,
    DiagListVehiclesInput,
    DiagListVehiclesResult,
    DiagSelectInterfaceInput,
    DiagSelectInterfaceResult,
    DiagSelectLogicalLinkInput,
    DiagSelectLogicalLinkResult,
    DiagSelectVehicleInput,
    DiagSelectVehicleResult,
    DiagSetupAction,
    DiagSetupInput,
    DiagVehicleManageAction,
    DiagVehicleManageInput,
    ToolActionEntry,
)
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import ecu_diagnostics_service

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — controldesk_ecu_diagnostics_setup ────────────────────────────────


@mcp.tool(
    name="controldesk_ecu_diagnostics_setup",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Configures the ODX diagnostic database for a Diagnostic2 platform. "
        "Set 'action' to specify what to do: "
        "'add_odx_directory' — add all ODX files from a directory to "
        "ActiveDiagnosticsDatabase (requires platform_name, directory_path; "
        "optional db_name, optimize). Also suppresses blocking UI dialogs "
        "via GeneralSettings.DisplayStatusInformation = False. "
        "'list_odx_files' — list currently loaded ODX file paths (requires platform_name). "
        "Prerequisite: platform_manage(action='add', platform_type='Diagnostic2') must have "
        "been called first to create the platform."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.ECU_DIAGNOSTICS, ToolGroup.DATABASE_MANAGEMENT),
)
async def ecu_diagnostics_setup(
    params: DiagSetupInput,
) -> (
    DiagAddOdxDirectoryResult
    | DiagListOdxFilesResult
    | ErrorEnvelope
):
    if params.action == DiagSetupAction.add_odx_directory:
        if not params.directory_path:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="directory_path is required for action='add_odx_directory'.",
                recovery_hint="Set directory_path to the absolute path of the ODX folder.",
            )
        return await ecu_diagnostics_service.add_odx_from_directory(
            DiagAddOdxDirectoryInput(
                platform_name=params.platform_name,
                directory_path=params.directory_path,
                db_name=params.db_name or "",
                optimize=params.optimize,
            )
        )
    # list_odx_files
    return await ecu_diagnostics_service.list_odx_files(
        DiagListOdxFilesInput(platform_name=params.platform_name)
    )


# ── Tool 2 — controldesk_ecu_diagnostics_link_setup ──────────────────────────


@mcp.tool(
    name="controldesk_ecu_diagnostics_link_setup",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Manages vehicle selection, logical-link setup, and interface configuration "
        "for a Diagnostic2 platform. "
        "Set 'action' to specify what to do: "
        "'list_vehicles' — enumerate all vehicles from VehicleSelection.Vehicles "
        "(requires platform_name); "
        "'select_vehicle' — select a vehicle by short name (requires platform_name, "
        "vehicle_name); "
        "'list_logical_links' — enumerate all logical links (requires platform_name); "
        "'select_logical_link' — select a logical link by short name (requires "
        "platform_name, link_name); "
        "'configure_logical_link' — set protocol and physical connection on a link "
        "(requires platform_name, link_name, protocol, physical_connection); "
        "'list_interfaces' — list available vendors and interfaces for a link "
        "(requires platform_name, link_name); "
        "'select_interface' — select vendor/interface/channel (requires platform_name, "
        "link_name, vendor_name, interface_name; optional channel_index). "
        "Prerequisite: an ODX database must be loaded via ecu_diagnostics_setup first."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.ECU_DIAGNOSTICS, ToolGroup.LINK_MANAGEMENT),
)
async def ecu_diagnostics_link_setup(
    params: DiagLinkSetupInput,
) -> (
    DiagListVehiclesResult
    | DiagSelectVehicleResult
    | DiagListLogicalLinksResult
    | DiagSelectLogicalLinkResult
    | DiagConfigureLogicalLinkResult
    | DiagListInterfacesResult
    | DiagSelectInterfaceResult
    | ErrorEnvelope
):
    if params.action == DiagLinkSetupAction.list_vehicles:
        return await ecu_diagnostics_service.list_vehicles(
            DiagListVehiclesInput(platform_name=params.platform_name)
        )

    if params.action == DiagLinkSetupAction.select_vehicle:
        if not params.vehicle_name:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="vehicle_name is required for action='select_vehicle'.",
                recovery_hint="Set vehicle_name to a short name from list_vehicles.",
            )
        return await ecu_diagnostics_service.select_vehicle(
            DiagSelectVehicleInput(
                platform_name=params.platform_name,
                vehicle_name=params.vehicle_name,
            )
        )

    if params.action == DiagLinkSetupAction.list_logical_links:
        return await ecu_diagnostics_service.list_logical_links(
            DiagListLogicalLinksInput(platform_name=params.platform_name)
        )

    if params.action == DiagLinkSetupAction.select_logical_link:
        if not params.link_name:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="link_name is required for action='select_logical_link'.",
                recovery_hint="Set link_name to a short name from list_logical_links.",
            )
        return await ecu_diagnostics_service.select_logical_link(
            DiagSelectLogicalLinkInput(
                platform_name=params.platform_name,
                link_name=params.link_name,
            )
        )

    if params.action == DiagLinkSetupAction.configure_logical_link:
        if not params.link_name or params.protocol is None or params.physical_connection is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message=(
                    "link_name, protocol, and physical_connection are required for "
                    "action='configure_logical_link'."
                ),
                recovery_hint=(
                    "Provide link_name (from list_logical_links), protocol "
                    "(ISO_14229_UDS/KWP2000/ISO_14230), and physical_connection "
                    "(CAN/LIN/Ethernet/FlexRay/K_Line/DoIP)."
                ),
            )
        return await ecu_diagnostics_service.configure_logical_link(
            DiagConfigureLogicalLinkInput(
                platform_name=params.platform_name,
                link_name=params.link_name,
                protocol=params.protocol,
                physical_connection=params.physical_connection,
            )
        )

    if params.action == DiagLinkSetupAction.list_interfaces:
        if not params.link_name:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="link_name is required for action='list_interfaces'.",
                recovery_hint="Set link_name to a short name from list_logical_links.",
            )
        return await ecu_diagnostics_service.list_interfaces(
            DiagListInterfacesInput(
                platform_name=params.platform_name,
                link_name=params.link_name,
            )
        )

    # select_interface
    if not params.link_name or not params.vendor_name or not params.interface_name:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message=(
                "link_name, vendor_name, and interface_name are required for "
                "action='select_interface'."
            ),
            recovery_hint=(
                "Call list_interfaces first to discover available vendors and interfaces."
            ),
        )
    return await ecu_diagnostics_service.select_interface_channel(
        DiagSelectInterfaceInput(
            platform_name=params.platform_name,
            link_name=params.link_name,
            vendor_name=params.vendor_name,
            interface_name=params.interface_name,
            channel_index=params.channel_index,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; access via controldesk_ecu_diagnostics_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: DATABASE_MANAGEMENT ────────────────────────────────────────────────
# ── Tool 4 — controldesk_ecu_diagnostics_db_manage ───────────────────────────


@mcp.tool(
    name="controldesk_ecu_diagnostics_db_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages individual ODX database file operations. "
        "Set 'action' to specify what to do: "
        "'add_file' — add a single ODX file to ActiveDiagnosticsDatabase "
        "(requires platform_name, file_path); "
        "'list_files' — list currently loaded ODX file paths (requires platform_name). "
        "Use ecu_diagnostics_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.ECU_DIAGNOSTICS, ToolGroup.DATABASE_MANAGEMENT),
)
async def ecu_diagnostics_db_manage(
    params: DiagDbManageInput,
) -> DiagAddOdxFileResult | DiagListOdxFilesResult | ErrorEnvelope:
    if params.action == DiagDbManageAction.add_file:
        if not params.file_path:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="file_path is required for action='add_file'.",
                recovery_hint="Set file_path to the absolute path of the ODX file to add.",
            )
        return await ecu_diagnostics_service.add_odx_file(
            DiagAddOdxFileInput(
                platform_name=params.platform_name,
                file_path=params.file_path,
            )
        )
    # list_files
    return await ecu_diagnostics_service.list_odx_files(
        DiagListOdxFilesInput(platform_name=params.platform_name)
    )


# ── GROUP: VEHICLE_MANAGEMENT ─────────────────────────────────────────────────
# ── Tool 5 — controldesk_ecu_diagnostics_vehicle_manage ──────────────────────


@mcp.tool(
    name="controldesk_ecu_diagnostics_vehicle_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages vehicle selection on a Diagnostic2 platform. "
        "Set 'action' to specify what to do: "
        "'list_vehicles' — enumerate all vehicles from VehicleSelection.Vehicles "
        "(requires platform_name); "
        "'select_vehicle' — select a vehicle by short name (requires platform_name, "
        "vehicle_name). "
        "Use ecu_diagnostics_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.ECU_DIAGNOSTICS, ToolGroup.VEHICLE_MANAGEMENT),
)
async def ecu_diagnostics_vehicle_manage(
    params: DiagVehicleManageInput,
) -> DiagListVehiclesResult | DiagSelectVehicleResult | ErrorEnvelope:
    if params.action == DiagVehicleManageAction.list_vehicles:
        return await ecu_diagnostics_service.list_vehicles(
            DiagListVehiclesInput(platform_name=params.platform_name)
        )
    # select_vehicle
    if not params.vehicle_name:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="vehicle_name is required for action='select_vehicle'.",
            recovery_hint="Set vehicle_name to a short name from list_vehicles.",
        )
    return await ecu_diagnostics_service.select_vehicle(
        DiagSelectVehicleInput(
            platform_name=params.platform_name,
            vehicle_name=params.vehicle_name,
        )
    )


# ── GROUP: LINK_MANAGEMENT ────────────────────────────────────────────────────
# ── Tool 6 — controldesk_ecu_diagnostics_link_manage ─────────────────────────


@mcp.tool(
    name="controldesk_ecu_diagnostics_link_manage",
    tool_category=MCPToolCategory.ADD_ON,
    lazy_loading=True,
    description=(
        "Manages logical-link selection and interface configuration on a Diagnostic2 platform. "
        "Set 'action' to specify what to do: "
        "'list_links' — enumerate all logical links (requires platform_name); "
        "'select_link' — select a logical link by short name (requires platform_name, link_name); "
        "'configure_link' — set protocol and physical connection (requires platform_name, "
        "link_name, protocol, physical_connection); "
        "'list_interfaces' — list vendors and interfaces for a link (requires platform_name, link_name); "
        "'select_interface' — select vendor/interface/channel (requires platform_name, "
        "link_name, vendor_name, interface_name; optional channel_index). "
        "Use ecu_diagnostics_discover to activate this tool."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.ECU_DIAGNOSTICS, ToolGroup.LINK_MANAGEMENT),
)
async def ecu_diagnostics_link_manage(
    params: DiagLinkManageInput,
) -> (
    DiagListLogicalLinksResult
    | DiagSelectLogicalLinkResult
    | DiagConfigureLogicalLinkResult
    | DiagListInterfacesResult
    | DiagSelectInterfaceResult
    | ErrorEnvelope
):
    if params.action == DiagLinkManageAction.list_links:
        return await ecu_diagnostics_service.list_logical_links(
            DiagListLogicalLinksInput(platform_name=params.platform_name)
        )

    if params.action == DiagLinkManageAction.select_link:
        if not params.link_name:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="link_name is required for action='select_link'.",
                recovery_hint="Set link_name to a short name from list_links.",
            )
        return await ecu_diagnostics_service.select_logical_link(
            DiagSelectLogicalLinkInput(
                platform_name=params.platform_name,
                link_name=params.link_name,
            )
        )

    if params.action == DiagLinkManageAction.configure_link:
        if not params.link_name or params.protocol is None or params.physical_connection is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message=(
                    "link_name, protocol, and physical_connection are required for "
                    "action='configure_link'."
                ),
                recovery_hint=(
                    "Provide link_name (from list_links), protocol, and physical_connection."
                ),
            )
        return await ecu_diagnostics_service.configure_logical_link(
            DiagConfigureLogicalLinkInput(
                platform_name=params.platform_name,
                link_name=params.link_name,
                protocol=params.protocol,
                physical_connection=params.physical_connection,
            )
        )

    if params.action == DiagLinkManageAction.list_interfaces:
        if not params.link_name:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="link_name is required for action='list_interfaces'.",
                recovery_hint="Set link_name to a short name from list_links.",
            )
        return await ecu_diagnostics_service.list_interfaces(
            DiagListInterfacesInput(
                platform_name=params.platform_name,
                link_name=params.link_name,
            )
        )

    # select_interface
    if not params.link_name or not params.vendor_name or not params.interface_name:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message=(
                "link_name, vendor_name, and interface_name are required for "
                "action='select_interface'."
            ),
            recovery_hint=(
                "Call list_interfaces first to discover available vendors and interfaces."
            ),
        )
    return await ecu_diagnostics_service.select_interface_channel(
        DiagSelectInterfaceInput(
            platform_name=params.platform_name,
            link_name=params.link_name,
            vendor_name=params.vendor_name,
            interface_name=params.interface_name,
            channel_index=params.channel_index,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery — returns catalogue of lazy ADD_ON tools
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 3 — controldesk_ecu_diagnostics_discover ────────────────────────────


@mcp.tool(
    name="controldesk_ecu_diagnostics_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all available ECU Diagnostics operations "
        "that are not loaded by default. Call this tool first when you need to "
        "manage ODX database files individually, manage vehicle selection, or "
        "manage logical-link and interface settings via dedicated tools. "
        "The catalogue lists each tool, its purpose, and the actions it supports."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.ECU_DIAGNOSTICS, ToolGroup.DATABASE_MANAGEMENT),
)
async def ecu_diagnostics_discover(ctx: Context) -> DiagDiscoverResult:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.ECU_DIAGNOSTICS, ctx)
    return DiagDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="controldesk_ecu_diagnostics_db_manage",
                purpose=(
                    "Add individual ODX files to or list files in the active "
                    "diagnostics database."
                ),
                actions=["add_file", "list_files"],
                required_params_per_action={
                    "add_file": ["platform_name", "file_path"],
                    "list_files": ["platform_name"],
                },
                group="database_management",
            ),
            ToolActionEntry(
                tool_name="controldesk_ecu_diagnostics_vehicle_manage",
                purpose="List all vehicles or select a vehicle for the diagnostics session.",
                actions=["list_vehicles", "select_vehicle"],
                required_params_per_action={
                    "list_vehicles": ["platform_name"],
                    "select_vehicle": ["platform_name", "vehicle_name"],
                },
                group="vehicle_management",
            ),
            ToolActionEntry(
                tool_name="controldesk_ecu_diagnostics_link_manage",
                purpose=(
                    "Manage logical links: list, select, configure protocol/connection, "
                    "list vendors/interfaces, select interface channel."
                ),
                actions=[
                    "list_links",
                    "select_link",
                    "configure_link",
                    "list_interfaces",
                    "select_interface",
                ],
                required_params_per_action={
                    "list_links": ["platform_name"],
                    "select_link": ["platform_name", "link_name"],
                    "configure_link": [
                        "platform_name",
                        "link_name",
                        "protocol",
                        "physical_connection",
                    ],
                    "list_interfaces": ["platform_name", "link_name"],
                    "select_interface": [
                        "platform_name",
                        "link_name",
                        "vendor_name",
                        "interface_name",
                    ],
                },
                group="link_management",
            ),
        ],
        hint=(
            "Call these tools after running ecu_diagnostics_discover to set up the "
            "Diagnostic2 platform before connecting. Typical order: "
            "ecu_diagnostics_setup (add_odx_directory) → "
            "ecu_diagnostics_link_setup (list_vehicles → select_vehicle → "
            "list_logical_links → configure_logical_link → list_interfaces → "
            "select_interface) → platform_connect."
        ),
    )
