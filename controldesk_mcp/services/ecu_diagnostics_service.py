"""Service facade for ControlDesk ECU Diagnostics (Diagnostic2) platform operations.

Owns: orchestration of ODX database setup, vehicle selection, logical-link
      configuration, and interface selection for Diagnostic2 platforms.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError
from controldesk_mcp.models.ecu_diagnostics import (
    DiagAddOdxDirectoryInput,
    DiagAddOdxDirectoryResult,
    DiagAddOdxFileInput,
    DiagAddOdxFileResult,
    DiagConfigureLogicalLinkInput,
    DiagConfigureLogicalLinkResult,
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
    LogicalLinkInfo,
    VehicleInfo,
    VendorInfo,
)
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


# ── ODX database operations ───────────────────────────────────────────────────


async def add_odx_from_directory(
    params: DiagAddOdxDirectoryInput,
) -> DiagAddOdxDirectoryResult | ErrorEnvelope:
    """Add all ODX files from a directory to the active diagnostics database."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.add_odx_files_from_directory,
            app,
            params.platform_name,
            params.directory_path,
            params.db_name or "",
            params.optimize,
        )
        return DiagAddOdxDirectoryResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def add_odx_file(
    params: DiagAddOdxFileInput,
) -> DiagAddOdxFileResult | ErrorEnvelope:
    """Add a single ODX file to the active diagnostics database."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.add_odx_file,
            app,
            params.platform_name,
            params.file_path,
        )
        return DiagAddOdxFileResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def list_odx_files(
    params: DiagListOdxFilesInput,
) -> DiagListOdxFilesResult | ErrorEnvelope:
    """List file paths currently loaded in the active diagnostics database."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.list_odx_files,
            app,
            params.platform_name,
        )
        return DiagListOdxFilesResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


# ── Vehicle operations ────────────────────────────────────────────────────────


async def list_vehicles(
    params: DiagListVehiclesInput,
) -> DiagListVehiclesResult | ErrorEnvelope:
    """List all vehicles from VehicleSelection.Vehicles."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.list_vehicles,
            app,
            params.platform_name,
        )
        vehicles = [VehicleInfo(**v) for v in result["vehicles"]]
        return DiagListVehiclesResult(
            platform_name=result["platform_name"],
            vehicles=vehicles,
            count=result["count"],
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def select_vehicle(
    params: DiagSelectVehicleInput,
) -> DiagSelectVehicleResult | ErrorEnvelope:
    """Select a vehicle by short name."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.select_vehicle,
            app,
            params.platform_name,
            params.vehicle_name,
        )
        return DiagSelectVehicleResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


# ── Logical link operations ───────────────────────────────────────────────────


async def list_logical_links(
    params: DiagListLogicalLinksInput,
) -> DiagListLogicalLinksResult | ErrorEnvelope:
    """List all logical links from LogicalLinkSelection.LogicalLinks."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.list_logical_links,
            app,
            params.platform_name,
        )
        links = [LogicalLinkInfo(**lnk) for lnk in result["logical_links"]]
        return DiagListLogicalLinksResult(
            platform_name=result["platform_name"],
            logical_links=links,
            count=result["count"],
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def select_logical_link(
    params: DiagSelectLogicalLinkInput,
) -> DiagSelectLogicalLinkResult | ErrorEnvelope:
    """Select a logical link by short name."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.select_logical_link,
            app,
            params.platform_name,
            params.link_name,
        )
        return DiagSelectLogicalLinkResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


async def configure_logical_link(
    params: DiagConfigureLogicalLinkInput,
) -> DiagConfigureLogicalLinkResult | ErrorEnvelope:
    """Set protocol and physical connection on a logical link."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.configure_logical_link,
            app,
            params.platform_name,
            params.link_name,
            params.protocol.value,
            params.physical_connection.value,
        )
        return DiagConfigureLogicalLinkResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)


# ── Interface operations ──────────────────────────────────────────────────────


async def list_interfaces(
    params: DiagListInterfacesInput,
) -> DiagListInterfacesResult | ErrorEnvelope:
    """List available vendors and interfaces for a logical link."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.list_interfaces,
            app,
            params.platform_name,
            params.link_name,
        )
        vendors = [VendorInfo(**v) for v in result["vendors"]]
        return DiagListInterfacesResult(
            platform_name=result["platform_name"],
            link_name=result["link_name"],
            vendors=vendors,
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def select_interface_channel(
    params: DiagSelectInterfaceInput,
) -> DiagSelectInterfaceResult | ErrorEnvelope:
    """Select a vendor / interface / channel for a logical link."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.ecu_diagnostics_com.select_interface_channel,
            app,
            params.platform_name,
            params.link_name,
            params.vendor_name,
            params.interface_name,
            params.channel_index,
        )
        return DiagSelectInterfaceResult(**result)
    except BridgeError as exc:
        return build_envelope(exc)
