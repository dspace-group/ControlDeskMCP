"""COM wrappers for ControlDesk ECU Diagnostics (Diagnostic2) platform interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry points:
  app.ActiveExperiment.Platforms.Item(platform_name)
    └─ .GeneralSettings.DisplayStatusInformation       (bool — suppress UI dialogs)
    └─ .ActiveDiagnosticsDatabase                      (IXaECUDiagnosticsDatabase)
         ├─ .Name                                       (read/write — rename)
         ├─ .OptimizeDatabaseEnabled                   (bool)
         ├─ .Update()
         ├─ .DatabaseFiles                             (IXaECUDiagnosticsDatabaseFiles)
         │    ├─ .AddFilesFromDirectory(path)
         │    ├─ .Add(filepath)
         │    └─ .Count / .Item(i)
         └─ .VehicleSelection
              ├─ .Vehicles.Count
              ├─ .Vehicles.Item(index_or_shortname)
              │    ├─ .ShortName / .LongName / .Description / .IsSelected
              │    └─ .Select()
              └─ .selectedVehicle.logicalLinkSelection
                   ├─ .LogicalLinks.Count
                   ├─ .LogicalLinks.Item(index_or_shortname)
                   │    ├─ .ShortName / .LongName / .DisplayName / .Description / .IsSelected
                   │    ├─ .Select()
                   │    ├─ .Protocol  (ECUDiagnosticsProtocol enum int)
                   │    ├─ .PhysicalConnection  (ECUDiagnosticsPhysicalConnection enum int)
                   │    └─ .InterfaceSelection
                   │         └─ .Vendors.Item(name)
                   │              └─ .AvailableInterfaces.Item(name)
                   │                   └─ .Channels.Item(index).Select()
                   ├─ .CreateVariableDescriptionForSelectedLogicalLinks (bool)
                   └─ .Update()
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgePreconditionError


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# ── Protocol / PhysicalConnection integer maps ────────────────────────────────
# Source: ControlDesk COM Enums — ECUDiagnosticsProtocol / ECUDiagnosticsPhysicalConnection
# Note: Verify exact integer values against dspace.com.Enums at runtime.
# Values derived from demo script enum usage patterns.

_PROTOCOL_INT_CANDIDATES: dict[str, tuple[int, ...]] = {
    # Additional fallback values keep compatibility with potential variants.
    "ISO_14229_UDS": (2, 0),
    "KWP2000": (1,),
    # ISO 14230 (K-Line) is commonly represented by the same enum value as KWP2000.
    "ISO_14230": (1, 3),
}

_PHYSICAL_CONNECTION_INT: dict[str, int] = {
    "CAN": 0,
    "LIN": 1,
    "Ethernet": 2,
    "FlexRay": 3,
    "K_Line": 4,
    "DoIP": 5,
}

# Diagnostic2 platform type integer (from _PLATFORM_TYPE_INT in platform_com.py)
_DIAGNOSTIC2_TYPE_INT = 27


# ── Internal helpers ──────────────────────────────────────────────────────────


def _get_platform(app: Any, platform_name: str) -> Any:
    """Return the IXaExperimentPlatform COM object for *platform_name*."""
    try:
        return app.ActiveExperiment.Platforms.Item(platform_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Platform '{platform_name}' not found in the active experiment.",
            error_code="BRIDGE_DIAG_PLATFORM_NOT_FOUND",
            recovery_hint="Call platform_list to enumerate valid platform names.",
        ) from exc


def _require_diagnostic_platform(app: Any, platform_name: str) -> Any:
    """Return the Diagnostic2 platform object, raising if wrong type.

    1. Looks up the platform by name.
    2. Verifies that int(plat.Type) == 27 (Diagnostic2).
    3. Raises BridgePreconditionError with BRIDGE_DIAG_WRONG_TYPE if the type
       does not match.
    """
    plat = _get_platform(app, platform_name)
    try:
        plat_type = int(plat.Type)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="Type") from exc
    if plat_type != _DIAGNOSTIC2_TYPE_INT:
        raise BridgePreconditionError(
            f"Platform '{platform_name}' is not a Diagnostic2 platform (type={plat_type}). "
            "Use platform_manage(action='add', platform_type='Diagnostic2') to create one.",
            error_code="BRIDGE_DIAG_WRONG_TYPE",
            recovery_hint="Add a Diagnostic2 platform or supply the correct platform name.",
        )
    return plat


def _get_active_db(plat: Any, platform_name: str) -> Any:
    """Return ActiveDiagnosticsDatabase, raising if not accessible."""
    try:
        db = plat.ActiveDiagnosticsDatabase
        if db is None:
            raise ValueError("ActiveDiagnosticsDatabase is None")
        return db
    except Exception as exc:
        raise BridgePreconditionError(
            f"Platform '{platform_name}' has no active diagnostics database. "
            "Call ecu_diagnostics_setup with action='add_odx_directory' to load one.",
            error_code="BRIDGE_DIAG_NO_DATABASE",
            recovery_hint="Load an ODX database directory before accessing vehicle/link settings.",
        ) from exc


def _get_logical_link_selection(plat: Any, platform_name: str) -> Any:
    """Return the LogicalLinkSelection object.

    Tries the top-level path first, then falls back to the vehicle-scoped path.
    """
    # Prefer top-level path
    try:
        lls = plat.LogicalLinkSelection
        if lls is not None:
            return lls
    except Exception:  # noqa: BLE001
        pass

    # Fallback: vehicle-scoped path
    try:
        db = _get_active_db(plat, platform_name)
        lls = db.VehicleSelection.selectedVehicle.logicalLinkSelection
        if lls is None:
            raise ValueError("logicalLinkSelection is None")
        return lls
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise BridgePreconditionError(
            f"Could not access LogicalLinkSelection on platform '{platform_name}'. "
            "Ensure a vehicle has been selected before accessing logical links.",
            error_code="BRIDGE_DIAG_NO_DATABASE",
            recovery_hint="Select a vehicle first using ecu_diagnostics_link_setup with action='select_vehicle'.",
        ) from exc


# ── add_odx_files_from_directory ──────────────────────────────────────────────


def add_odx_files_from_directory(
    app: Any,
    platform_name: str,
    directory_path: str,
    db_name: str = "",
    optimize: bool = False,
) -> dict[str, Any]:
    """Add all ODX files from *directory_path* to the active diagnostics database.

    Also suppresses UI dialogs via GeneralSettings.DisplayStatusInformation = False
    (required for automation to prevent blocking dialogs).

    Returns a dict with keys: platform_name, directory_path, db_name, optimized, timestamp.
    """
    plat = _require_diagnostic_platform(app, platform_name)

    # Suppress blocking UI dialogs during automation.
    try:
        plat.GeneralSettings.DisplayStatusInformation = False
    except Exception:  # noqa: BLE001
        pass  # Best-effort; continue if not supported

    try:
        db = _get_active_db(plat, platform_name)
        db.DatabaseFiles.AddFilesFromDirectory(directory_path)
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsDatabaseFiles", method="AddFilesFromDirectory"
        ) from exc

    if db_name:
        try:
            db.Name = db_name
        except Exception as exc:
            raise map_com_error(
                exc, interface="IXaECUDiagnosticsDatabase", method="Name"
            ) from exc

    try:
        db.OptimizeDatabaseEnabled = optimize
        db.Update()
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsDatabase", method="Update"
        ) from exc

    # Count files after loading
    try:
        files_added = int(db.DatabaseFiles.Count)
    except Exception:  # noqa: BLE001
        files_added = -1

    return {
        "platform_name": platform_name,
        "directory_path": directory_path,
        "db_name": db_name or "",
        "files_added": files_added,
        "optimized": optimize,
        "timestamp": _utc_now(),
    }


# ── add_odx_file ──────────────────────────────────────────────────────────────


def add_odx_file(app: Any, platform_name: str, file_path: str) -> dict[str, Any]:
    """Add a single ODX file to the active diagnostics database.

    Returns a dict with keys: platform_name, file_path, timestamp.
    """
    plat = _require_diagnostic_platform(app, platform_name)

    try:
        db = _get_active_db(plat, platform_name)
        db.DatabaseFiles.Add(file_path)
        db.Update()
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsDatabaseFiles", method="Add"
        ) from exc

    return {
        "platform_name": platform_name,
        "file_path": file_path,
        "timestamp": _utc_now(),
    }


# ── list_odx_files ────────────────────────────────────────────────────────────


def list_odx_files(app: Any, platform_name: str) -> dict[str, Any]:
    """Return a list of file paths currently loaded in the active diagnostics database.

    Returns a dict with keys: platform_name, files (list[str]), count.
    """
    plat = _require_diagnostic_platform(app, platform_name)
    db = _get_active_db(plat, platform_name)

    try:
        db_files = db.DatabaseFiles
        count = int(db_files.Count)
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsDatabaseFiles", method="Count"
        ) from exc

    files: list[str] = []
    for i in range(count):
        try:
            item = db_files.Item(i)
            # DatabaseFiles.Item may return a string or a COM object with a Path property
            try:
                files.append(str(item.Path))
            except Exception:  # noqa: BLE001
                files.append(str(item))
        except Exception as exc:
            raise map_com_error(
                exc, interface="IXaECUDiagnosticsDatabaseFiles", method="Item"
            ) from exc

    return {
        "platform_name": platform_name,
        "files": files,
        "count": count,
    }


# ── list_vehicles ─────────────────────────────────────────────────────────────


def list_vehicles(app: Any, platform_name: str) -> dict[str, Any]:
    """Return all vehicles from VehicleSelection.Vehicles.

    Returns a dict with keys: platform_name, vehicles (list[dict]), count.
    Each vehicle dict has: short_name, long_name, description, is_selected.
    """
    plat = _require_diagnostic_platform(app, platform_name)
    db = _get_active_db(plat, platform_name)

    try:
        vehicles_col = db.VehicleSelection.Vehicles
        count = int(vehicles_col.Count)
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsVehicleSelection", method="Vehicles.Count"
        ) from exc

    vehicles: list[dict] = []
    for i in range(count):
        try:
            v = vehicles_col.Item(i)
        except Exception as exc:
            raise map_com_error(
                exc, interface="IXaECUDiagnosticsVehicles", method="Item"
            ) from exc

        def _safe(attr: str, default: str = "") -> str:
            try:
                return str(getattr(v, attr))
            except Exception:  # noqa: BLE001
                return default

        def _safe_bool(attr: str) -> bool:
            try:
                return bool(getattr(v, attr))
            except Exception:  # noqa: BLE001
                return False

        vehicles.append(
            {
                "short_name": _safe("ShortName"),
                "long_name": _safe("LongName"),
                "description": _safe("Description"),
                "is_selected": _safe_bool("IsSelected"),
            }
        )

    return {
        "platform_name": platform_name,
        "vehicles": vehicles,
        "count": count,
    }


# ── select_vehicle ────────────────────────────────────────────────────────────


def select_vehicle(app: Any, platform_name: str, vehicle_name: str) -> dict[str, Any]:
    """Select a vehicle by short name and call Update() to persist the selection.

    Returns a dict with keys: platform_name, vehicle_name, timestamp.
    """
    plat = _require_diagnostic_platform(app, platform_name)
    db = _get_active_db(plat, platform_name)

    try:
        vehicle = db.VehicleSelection.Vehicles.Item(vehicle_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Vehicle '{vehicle_name}' not found on platform '{platform_name}'.",
            error_code="BRIDGE_DIAG_VEHICLE_NOT_FOUND",
            recovery_hint=(
                "Call ecu_diagnostics_link_setup with action='list_vehicles' to see "
                "available vehicle short names."
            ),
        ) from exc

    try:
        vehicle.Select()
        db.Update()
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsVehicle", method="Select"
        ) from exc

    return {
        "platform_name": platform_name,
        "vehicle_name": vehicle_name,
        "timestamp": _utc_now(),
    }


# ── list_logical_links ────────────────────────────────────────────────────────


def list_logical_links(app: Any, platform_name: str) -> dict[str, Any]:
    """Return all logical links from LogicalLinkSelection.LogicalLinks.

    Returns a dict with keys: platform_name, logical_links (list[dict]), count.
    Each link dict has: short_name, long_name, display_name, description, is_selected.
    """
    plat = _require_diagnostic_platform(app, platform_name)
    lls = _get_logical_link_selection(plat, platform_name)

    try:
        links_col = lls.LogicalLinks
        count = int(links_col.Count)
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsLogicalLinkSelection", method="LogicalLinks.Count"
        ) from exc

    links: list[dict] = []
    for i in range(count):
        try:
            lnk = links_col.Item(i)
        except Exception as exc:
            raise map_com_error(
                exc, interface="IXaECUDiagnosticsLogicalLinks", method="Item"
            ) from exc

        def _safe(attr: str, default: str = "") -> str:
            try:
                return str(getattr(lnk, attr))
            except Exception:  # noqa: BLE001
                return default

        def _safe_bool(attr: str) -> bool:
            try:
                return bool(getattr(lnk, attr))
            except Exception:  # noqa: BLE001
                return False

        links.append(
            {
                "short_name": _safe("ShortName"),
                "long_name": _safe("LongName"),
                "display_name": _safe("DisplayName"),
                "description": _safe("Description"),
                "is_selected": _safe_bool("IsSelected"),
            }
        )

    return {
        "platform_name": platform_name,
        "logical_links": links,
        "count": count,
    }


# ── select_logical_link ───────────────────────────────────────────────────────


def select_logical_link(app: Any, platform_name: str, link_name: str) -> dict[str, Any]:
    """Select a logical link by short name and call Update().

    Returns a dict with keys: platform_name, link_name, timestamp.
    """
    plat = _require_diagnostic_platform(app, platform_name)
    lls = _get_logical_link_selection(plat, platform_name)

    try:
        lnk = lls.LogicalLinks.Item(link_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Logical link '{link_name}' not found on platform '{platform_name}'.",
            error_code="BRIDGE_DIAG_LINK_NOT_FOUND",
            recovery_hint=(
                "Call ecu_diagnostics_link_setup with action='list_logical_links' to see "
                "available logical link short names."
            ),
        ) from exc

    try:
        lnk.Select()
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsLogicalLink", method="Select"
        ) from exc

    try:
        lls.Update()
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsLogicalLinkSelection", method="Update"
        ) from exc

    return {
        "platform_name": platform_name,
        "link_name": link_name,
        "timestamp": _utc_now(),
    }


# ── configure_logical_link ────────────────────────────────────────────────────


def configure_logical_link(
    app: Any,
    platform_name: str,
    link_name: str,
    protocol: str,
    physical_connection: str,
) -> dict[str, Any]:
    """Set protocol and physical connection on a logical link and call Update().

    *protocol* must be a key in ``_PROTOCOL_INT_CANDIDATES``.
    *physical_connection* must be a key in ``_PHYSICAL_CONNECTION_INT``.

    Returns a dict with keys: platform_name, link_name, protocol, physical_connection, timestamp.
    """
    protocol_candidates = _PROTOCOL_INT_CANDIDATES.get(protocol)
    if protocol_candidates is None:
        raise BridgePreconditionError(
            f"Unknown protocol '{protocol}'. Valid values: {list(_PROTOCOL_INT_CANDIDATES.keys())}",
            error_code="BRIDGE_DIAG_INVALID_PROTOCOL",
            recovery_hint=f"Use one of: {list(_PROTOCOL_INT_CANDIDATES.keys())}",
        )

    phys_int = _PHYSICAL_CONNECTION_INT.get(physical_connection)
    if phys_int is None:
        raise BridgePreconditionError(
            f"Unknown physical connection '{physical_connection}'. "
            f"Valid values: {list(_PHYSICAL_CONNECTION_INT.keys())}",
            error_code="BRIDGE_DIAG_INVALID_PHYSICAL_CONNECTION",
            recovery_hint=f"Use one of: {list(_PHYSICAL_CONNECTION_INT.keys())}",
        )

    plat = _require_diagnostic_platform(app, platform_name)
    lls = _get_logical_link_selection(plat, platform_name)

    try:
        lnk = lls.LogicalLinks.Item(link_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Logical link '{link_name}' not found on platform '{platform_name}'.",
            error_code="BRIDGE_DIAG_LINK_NOT_FOUND",
            recovery_hint=(
                "Call ecu_diagnostics_link_setup with action='list_logical_links' to "
                "see available logical link short names."
            ),
        ) from exc

    # Ensure the target link is selected before mutating configuration.
    try:
        lnk.Select()
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsLogicalLink", method="Select"
        ) from exc

    last_protocol_error: Exception | None = None
    for protocol_int in protocol_candidates:
        try:
            lnk.Protocol = protocol_int
            last_protocol_error = None
            break
        except Exception as exc:  # noqa: BLE001
            last_protocol_error = exc

    if last_protocol_error is not None:
        raise map_com_error(
            last_protocol_error,
            interface="IXaECUDiagnosticsLogicalLink",
            method="Protocol",
        ) from last_protocol_error

    try:
        lnk.PhysicalConnection = phys_int
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsLogicalLink", method="PhysicalConnection"
        ) from exc

    try:
        lls.Update()
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsLogicalLinkSelection", method="Update"
        ) from exc

    return {
        "platform_name": platform_name,
        "link_name": link_name,
        "protocol": protocol,
        "physical_connection": physical_connection,
        "timestamp": _utc_now(),
    }


# ── list_interfaces ───────────────────────────────────────────────────────────


def list_interfaces(app: Any, platform_name: str, link_name: str) -> dict[str, Any]:
    """List available CAN/interface vendors and their interfaces for a logical link.

    Returns a dict with keys: platform_name, link_name, vendors (list[dict]).
    Each vendor dict has: vendor_name, interfaces (list[str]).
    """
    plat = _require_diagnostic_platform(app, platform_name)
    lls = _get_logical_link_selection(plat, platform_name)

    try:
        lnk = lls.LogicalLinks.Item(link_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Logical link '{link_name}' not found on platform '{platform_name}'.",
            error_code="BRIDGE_DIAG_LINK_NOT_FOUND",
            recovery_hint=(
                "Call ecu_diagnostics_link_setup with action='list_logical_links' first."
            ),
        ) from exc

    try:
        interface_sel = lnk.InterfaceSelection
        vendors_col = interface_sel.Vendors
        vendor_count = int(vendors_col.Count)
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsInterfaceSelection", method="Vendors.Count"
        ) from exc

    vendors: list[dict] = []
    for vi in range(vendor_count):
        try:
            vendor = vendors_col.Item(vi)
        except Exception as exc:
            raise map_com_error(
                exc, interface="IXaECUDiagnosticsVendors", method="Item"
            ) from exc

        try:
            vendor_name = str(vendor.Name)
        except Exception:  # noqa: BLE001
            vendor_name = str(vi)

        interfaces: list[str] = []
        try:
            avail = vendor.AvailableInterfaces
            iface_count = int(avail.Count)
            for ii in range(iface_count):
                try:
                    iface = avail.Item(ii)
                    interfaces.append(str(iface.Name))
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            pass

        vendors.append({"vendor_name": vendor_name, "interfaces": interfaces})

    return {
        "platform_name": platform_name,
        "link_name": link_name,
        "vendors": vendors,
    }


# ── select_interface_channel ──────────────────────────────────────────────────


def select_interface_channel(
    app: Any,
    platform_name: str,
    link_name: str,
    vendor_name: str,
    interface_name: str,
    channel_index: int = 0,
) -> dict[str, Any]:
    """Select a vendor / interface / channel for a logical link and call Update().

    Also sets CreateVariableDescriptionForSelectedLogicalLinks = False to avoid
    unnecessary variable description generation during automation.

    Returns a dict with keys:
      platform_name, link_name, vendor_name, interface_name, channel_index, timestamp.
    """
    plat = _require_diagnostic_platform(app, platform_name)
    lls = _get_logical_link_selection(plat, platform_name)

    try:
        lnk = lls.LogicalLinks.Item(link_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Logical link '{link_name}' not found on platform '{platform_name}'.",
            error_code="BRIDGE_DIAG_LINK_NOT_FOUND",
            recovery_hint=(
                "Call ecu_diagnostics_link_setup with action='list_logical_links' first."
            ),
        ) from exc

    try:
        interface_sel = lnk.InterfaceSelection
        vendor = interface_sel.Vendors.Item(vendor_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Vendor '{vendor_name}' not found for link '{link_name}' on "
            f"platform '{platform_name}'.",
            error_code="BRIDGE_DIAG_INTERFACE_NOT_FOUND",
            recovery_hint=(
                "Call ecu_diagnostics_link_setup with action='list_interfaces' to see "
                "available vendors and interfaces."
            ),
        ) from exc

    try:
        iface = vendor.AvailableInterfaces.Item(interface_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Interface '{interface_name}' not found for vendor '{vendor_name}' on "
            f"link '{link_name}'.",
            error_code="BRIDGE_DIAG_INTERFACE_NOT_FOUND",
            recovery_hint=(
                "Call ecu_diagnostics_link_setup with action='list_interfaces' to see "
                "available interfaces for this vendor."
            ),
        ) from exc

    try:
        iface.Channels.Item(channel_index).Select()
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsChannel", method="Select"
        ) from exc

    # Suppress variable description generation during automation
    try:
        lls.CreateVariableDescriptionForSelectedLogicalLinks = False
    except Exception:  # noqa: BLE001
        pass  # Best-effort

    try:
        lls.Update()
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaECUDiagnosticsLogicalLinkSelection", method="Update"
        ) from exc

    return {
        "platform_name": platform_name,
        "link_name": link_name,
        "vendor_name": vendor_name,
        "interface_name": interface_name,
        "channel_index": channel_index,
        "timestamp": _utc_now(),
    }
