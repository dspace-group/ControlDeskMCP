"""COM wrappers for ControlDesk platform management interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry points:
  - app.ActiveExperiment.Platforms   (IXaExperimentPlatforms)
  - app.PlatformManagement            (IPmPlatformManagement)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgePreconditionError


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


# Bus Device types — added via Platforms.Add(); no IP registration
# CANMonitoring/LINMonitoring/EthernetMonitoring/FlexRayMonitoring support
# VariableDescriptions.Add() with .dbc, .ldf, .arxml, .fibex files.
# GNSS does not support variable descriptions.
_BUS_DEVICE_TYPES = frozenset(["CANMonitoring", "EthernetMonitoring", "LINMonitoring", "FlexRayMonitoring", "GNSS"])
# Bus monitoring types that accept bus configuration files via VariableDescriptions.Add()
# Source: BNV_Migration/generate.py lines 241-244; LayoutAndInstrumentHandling.py lines 1368-1369
_BUS_CONFIG_TYPES = frozenset(["CANMonitoring", "EthernetMonitoring", "LINMonitoring", "FlexRayMonitoring"])
# Types with no variable description support at all
_NO_VARIABLE_DESCRIPTION_TYPES = frozenset(["Diagnostic2", "GNSS"])
# Diagnostics — added via Platforms.Add(); ODX-based workflow; no A2L/SDF
_DIAGNOSTICS_TYPES = frozenset(["Diagnostic2"])
# Measurement & Calibration — added via Platforms.Add(); A2L+MOT variable descriptions
_XCP_PLATFORM_TYPES = frozenset(["XCPonCAN", "XCPonEthernet", "CCP", "GSI2"])
# Hardware platforms — require RegisterPlatform + AddExistingPlatform; SDF variable descriptions
# XILAPIMAPort uses config-file-based registration (not IP) via the Register Platform dialog.
_HARDWARE_PLATFORM_TYPES = frozenset(
    ["SCALEXIO", "DS1202", "DS1203", "DS1403", "MABX", "DS1104", "VEOS", "XILAPIMAPort"]
)
# Sub-set: all non-hardware types (must never be passed to platform_register_hardware)
_DIRECT_ADD_TYPES = _BUS_DEVICE_TYPES | _DIAGNOSTICS_TYPES | _XCP_PLATFORM_TYPES
# Platforms that use RegistrationInfos.Add() + sub.IPAddress
_SUBNET_REG_TYPES = frozenset(["SCALEXIO", "DS1202", "DS1203", "DS1403"])
# Platforms that use reg_info.NetClient directly
_NETCLIENT_REG_TYPES = frozenset(["MABX", "VEOS"])
# Types that support CAN-bus interface selection (InterfaceSelection.Vendors)
_MONITORING_INTERFACE_TYPES = frozenset(["XCPonCAN", "CANMonitoring", "LINMonitoring", "FlexRayMonitoring", "CCP"])
# CAN-baud-rate-configurable types
_CAN_BAUD_TYPES = frozenset(["XCPonCAN", "CANMonitoring", "LINMonitoring", "CCP"])
# Hardware types that use SMART assignment (Assignment.Assignments collection)
_SMART_ASSIGNMENT_TYPES = frozenset(["SCALEXIO", "DS1202", "DS1203", "DS1403"])
# Types that use legacy Assignment.NetClient / Assignment.ConnectionType (MABX)
_NETCLIENT_ASSIGNMENT_TYPES = frozenset(["MABX"])
# Types that use Assignment.NetClient directly (VEOS)
_VEOS_ASSIGNMENT_TYPES = frozenset(["VEOS"])
# Types that use Assignment.Mode + SerialNumber/BoardName (DS1104 family)
_DS1104_ASSIGNMENT_TYPES = frozenset(["DS1104", "DS1005", "DS1006", "DS1007"])
# All hardware types that have Assignment settings
_ASSIGNMENT_TYPES = (
    _SMART_ASSIGNMENT_TYPES | _NETCLIENT_ASSIGNMENT_TYPES | _VEOS_ASSIGNMENT_TYPES | _DS1104_ASSIGNMENT_TYPES
)
# Platforms that require APIVersion 2 for registration
# Source: SQSCalDeskToolautomationHelper.py _VerifyPlatformAgainstAPIVersion()
# SCALEXIO and related platforms must have APIVersion=2 set before RegisterPlatform
_REQUIRES_API_VERSION_2: frozenset[str] = frozenset(["SCALEXIO", "DS1202", "DS1203", "DS1403", "MABX", "VEOS"])
# Platform types that expose GeneralSettings.StartOnlineCalibrationBehavior.
# Bus Device types (CANMonitoring etc.) and Diagnostic2 do NOT have this property.
_CALIBRATION_BEHAVIOR_TYPES = _XCP_PLATFORM_TYPES | _HARDWARE_PLATFORM_TYPES

# ── Enum string→integer mappings ─────────────────────────────────────────────
# Source: SQSCalDeskToolautomationHelper.py / CalDeskAutomationEnums.py
# These COM properties require integers — NOT strings.

# Source: ControlDesk Automation PDF p.1899 — OnlineCalibrationBehavior <<Enumeration>>
# Keys MUST match OnlineCalibrationBehavior enum values in controldesk_mcp/models/platform.py
_ONLINE_CALIBRATION_BEHAVIOR: dict[str, int] = {
    "PromptUser": 0,
    "UploadWorkingPageDownloadReferencePage": 1,
    "DownloadWorkingPageUploadReferencePage": 2,
    "DownloadWorkingPageDownloadReferencePage": 3,
    "UploadWorkingPageUploadReferencePage": 4,
    "UploadConnectedVariables": 5,
    "IgnoreDifferences": 6,
    "Upload": 7,
    "Download": 8,
    "DownloadConnectedVariables": 9,
}

# Platform automation API versions
# Source: ControlDesk SQSCalDeskToolautomationHelper.py GetPlatformAutomationAPIVersion()
# COM property accepts integer values only, NOT strings.
_API_VERSION: dict[str, int] = {
    "APIVersion1": 1,
    "APIVersion2": 2,
}

# Source: ControlDesk Automation PDF p.1465-1466 — InitialPageType <<Enumeration>>
# Keys MUST match InitialPageType enum values in controldesk_mcp/models/platform.py
_INITIAL_PAGE: dict[str, int] = {
    "ECUDefined": 0,
    "WorkingPage": 1,
    "ReferencePage": 2,
    "ToolDefined": 3,
}

_ASSIGNMENT_MODE: dict[str, int] = {
    "FirstAvailable": 0,
    "AnyEqual": 1,
    "Identical": 2,
}

# ConnectionState / MeasurementState: COM integer → display string
# Source: CalDeskAutomationEnums.ConnectionState / MeasurementState
_CONNECTION_STATE_NAME: dict[int, str] = {0: "Connected", 1: "Disconnected"}
_MEASUREMENT_STATE_NAME: dict[int, str] = {0: "Stopped", 1: "Running"}

# ── PlatformType integer enum mapping ─────────────────────────────────────────
# Source: dSPACE CalDeskAutomationEnums.py / ATCalDeskSupport.py
# IXaExperimentPlatforms.Add() and CreatePlatformRegistrationInfo() require
# the integer value — NOT the string name.
# Source: ControlDesk Automation PDF p.1981 — PlatformType <<Enumeration>>
# IXaExperimentPlatforms.Add() and CreatePlatformRegistrationInfo() require integers.
_PLATFORM_TYPE_INT: dict[str, int] = {
    "MABX": 0,  # MicroAutoBox II (original)
    "DS1005": 3,  # Legacy
    "XCPonCAN": 4,
    "CCP": 6,
    "CANMonitoring": 10,
    "DS1104": 16,
    "DS1006": 17,  # Legacy
    "LINMonitoring": 19,
    "XCPonEthernet": 20,
    "SCALEXIO": 22,
    "FlexRayMonitoring": 24,
    "GSI2": 25,
    "VEOS": 26,
    "Diagnostic2": 27,
    "DS1007": 29,  # Legacy
    "DS1202": 30,  # MicroLabBox
    "XILAPIMAPort": 31,
    "EthernetMonitoring": 32,
    "DS1403": 33,  # MicroAutoBox III
    "GNSS": 34,  # GPS Device
    "DS1203": 35,  # MicroLabBox II
}
# Reverse lookup: COM integer → display name (for list/get_info responses)
_PLATFORM_TYPE_NAME: dict[int, str] = {v: k for k, v in _PLATFORM_TYPE_INT.items()}


# ── State string helpers ──────────────────────────────────────────────────────


def _connection_state_str(raw: Any) -> str:
    """Convert COM ConnectionState integer to a human-readable string."""
    try:
        return _CONNECTION_STATE_NAME.get(int(raw), str(raw))
    except (TypeError, ValueError):
        return str(raw)


def _measurement_state_str(raw: Any) -> str:
    """Convert COM MeasurementState integer to a human-readable string."""
    try:
        return _MEASUREMENT_STATE_NAME.get(int(raw), str(raw))
    except (TypeError, ValueError):
        return str(raw)


# ── IXaExperimentPlatforms helpers ────────────────────────────────────────────


def _get_platform(app: Any, platform_name: str) -> Any:
    """Return the IXaExperimentPlatform COM object for *platform_name*.

    Raises :class:`BridgePreconditionError` if the platform is not found.
    """
    try:
        return app.ActiveExperiment.Platforms.Item(platform_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Platform '{platform_name}' not found in the active experiment. "
            "Call platform_list to enumerate valid names.",
            error_code="BRIDGE_PLATFORM_NOT_FOUND",
            recovery_hint="Use platform_list to get the current platform names.",
        ) from exc


def _require_active_experiment(app: Any) -> None:
    """Raise BridgePreconditionError if no experiment is open."""
    try:
        exp = app.ActiveExperiment
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="ActiveExperiment") from exc
    if exp is None:
        raise BridgePreconditionError(
            "No active experiment open. Call experiment_activate first.",
            error_code="BRIDGE_NO_EXPERIMENT",
            recovery_hint="Load and activate an experiment before calling platform tools.",
        )


def _verify_platform_against_api_version(app: Any, platform_type: str) -> None:
    """Ensure APIVersion is set to 2 if the platform requires it.

    For SCALEXIO, DS1202, DS1203, DS1403, MABX, and VEOS, the PlatformManagement
    APIVersion MUST be 2 before calling RegisterPlatform. This function automatically
    upgrades the version if needed.

    Source: SQSCalDeskToolautomationHelper.py _VerifyPlatformAgainstAPIVersion()
    """
    if platform_type in _REQUIRES_API_VERSION_2:
        try:
            current_version = app.PlatformManagement.PlatformAutomationAPIVersion
            if int(current_version) < 2:
                app.PlatformManagement.PlatformAutomationAPIVersion = 2
        except Exception:  # noqa: BLE001
            # Best effort — if we can't read or set the version, continue anyway
            # and let RegisterPlatform fail if the version is truly incompatible
            pass


# ── platform_list ─────────────────────────────────────────────────────────────


def list_platforms(app: Any) -> list[dict[str, Any]]:
    """Return a list of platform info dicts for all platforms in the active experiment."""
    _require_active_experiment(app)
    try:
        platforms = app.ActiveExperiment.Platforms
        count = int(platforms.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatforms", method="Count") from exc

    result = []
    for i in range(0, count):
        # Obtain the platform COM object — hard failure if the collection index is invalid.
        try:
            plat = platforms.Item(i)
        except Exception as exc:
            raise map_com_error(exc, interface="IXaExperimentPlatforms", method="Item") from exc

        # Core identity properties — hard failure; every platform must expose these.
        try:
            name = str(plat.Name)
            plat_type = _PLATFORM_TYPE_NAME.get(int(plat.Type), str(plat.Type))
            connection_state = _connection_state_str(plat.ConnectionState)
        except Exception as exc:
            raise map_com_error(exc, interface="IXaExperimentPlatform", method="Name") from exc

        # MeasurementState may not be exposed by all platform types (e.g. Diagnostic2).
        try:
            measurement_state = _measurement_state_str(plat.MeasurementState)
        except Exception:  # noqa: BLE001
            measurement_state = "Unknown"

        # VariableDescriptions is not supported on bus device types (CANMonitoring etc.).
        # Accessing .Count throws DISP_E_EXCEPTION on these platform types.
        try:
            vd_count = int(plat.VariableDescriptions.Count)
        except Exception:  # noqa: BLE001
            vd_count = 0

        result.append(
            {
                "name": name,
                "type": plat_type,
                "connection_state": connection_state,
                "measurement_state": measurement_state,
                "variable_description_count": vd_count,
            }
        )
    return result


# ── platform_get_info ─────────────────────────────────────────────────────────


def get_platform_info(app: Any, platform_name: str) -> dict[str, Any]:
    """Return detailed metadata for the named platform."""
    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    try:
        info: dict[str, Any] = {
            "name": str(plat.Name),
            "type": _PLATFORM_TYPE_NAME.get(int(plat.Type), str(plat.Type)),
            "connection_state": _connection_state_str(plat.ConnectionState),
            "measurement_state": _measurement_state_str(plat.MeasurementState),
            "variable_description_count": int(plat.VariableDescriptions.Count),
        }
        # CAN-specific
        try:
            info["baud_rate"] = int(plat.CANSettings.BaudRate)
        except Exception:  # noqa: BLE001
            pass
        # XCP-specific
        try:
            info["xcp_checksum_algorithm"] = str(plat.XCPSettings.ChecksumCalculation.Algorithm)
        except Exception:  # noqa: BLE001
            pass
        try:
            info["xcp_byte_order"] = str(plat.XCPSettings.Advanced.ServiceByteOrder)
        except Exception:  # noqa: BLE001
            pass
        # Available channels
        try:
            info["available_channel_count"] = int(plat.InterfaceSelection.AvailableChannels.Count)
        except Exception:  # noqa: BLE001
            pass
        # Calibration behavior
        try:
            info["calibration_behavior"] = str(plat.GeneralSettings.StartOnlineCalibrationBehavior)
        except Exception:  # noqa: BLE001
            pass
        return info
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="properties") from exc


# ── platform_add ──────────────────────────────────────────────────────────────


def add_platform(app: Any, platform_type: str) -> dict[str, Any]:
    """Add a new platform of *platform_type* to the active experiment."""
    _require_active_experiment(app)
    if platform_type not in _PLATFORM_TYPE_INT:
        raise BridgePreconditionError(
            f"Unknown platform type '{platform_type}'. Valid types: {sorted(_PLATFORM_TYPE_INT.keys())}",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Call platform_list_types to see all supported platform types.",
        )
    try:
        plat = app.ActiveExperiment.Platforms.Add(_PLATFORM_TYPE_INT[platform_type])
        name = str(plat.Name)
    except Exception as exc:
        raise map_com_error(
            exc,
            interface="IXaExperimentPlatforms",
            method="Add",
        ) from exc

    result: dict[str, Any] = {
        "added": True,
        "platform_name": name,
        "platform_type": platform_type,
    }

    # Bus device types (CANMonitoring, LINMonitoring, FlexRayMonitoring, EthernetMonitoring)
    # must have automatic interface assignment set immediately after add.
    # Without this, connect_platform fails: "Could not find any suitable CAN channel."
    if platform_type in _BUS_DEVICE_TYPES:
        try:
            plat.InterfaceSelection.AutomaticAssignment = True
            result["auto_assignment"] = "Automatic"
        except Exception:  # noqa: BLE001
            # Best effort — platform was added; call platform_configure if this failed.
            pass

    return result


# ── platform_add_registered ───────────────────────────────────────────────────


def add_registered_platform(app: Any, unique_name: str) -> dict[str, Any]:
    """Attach a registered hardware platform to the active experiment."""
    _require_active_experiment(app)
    try:
        app.ActiveExperiment.Platforms.AddExistingPlatform(unique_name)
        return {"added": True, "unique_name": unique_name}
    except Exception as exc:
        raise map_com_error(
            exc,
            interface="IXaExperimentPlatforms",
            method="AddExistingPlatform",
        ) from exc


# ── platform_remove ───────────────────────────────────────────────────────────


def remove_platform(app: Any, platform_name: str) -> dict[str, Any]:
    """Remove a named platform from the active experiment.

    Uses IXaExperimentPlatforms.Remove(name) — confirmed from SQSCalDeskToolautomationHelper.py.
    """
    _require_active_experiment(app)
    # Verify the platform exists before attempting removal
    _get_platform(app, platform_name)
    try:
        app.ActiveExperiment.Platforms.Remove(platform_name)
        return {"platform_name": platform_name, "removed": True}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatforms", method="Remove") from exc


# ── platform_register_hardware ────────────────────────────────────────────────


def register_hardware_platform(app: Any, platform_type: str, ip_address: str) -> dict[str, Any]:
    """Register a physical hardware platform with PlatformManagement by IP address.

    Supports IP-addressable hardware: SCALEXIO, DS1202, DS1203, DS1403, MABX, VEOS.
    For these platforms, the PlatformAutomationAPIVersion is automatically set to 2 if needed.

    Invalid types:
    - Bus Device types (CANMonitoring, LINMonitoring, etc.) → use platform_add instead
    - XCP types (XCPonCAN, XCPonEthernet, CCP, GSI2) → use platform_add instead
    - Diagnostic2 → use platform_add instead
    - DS1104 → use platform_add instead (no IP-based registration support)

    Pre-validation errors (before any COM call):
    - BridgePreconditionError if platform_type is not IP-addressable hardware
    """
    # Explicit check: platform_type must be IP-addressable hardware (not software-only)
    valid_hardware_types = _SUBNET_REG_TYPES | _NETCLIENT_REG_TYPES
    if platform_type not in valid_hardware_types:
        if platform_type in _DIRECT_ADD_TYPES:
            raise BridgePreconditionError(
                f"'{platform_type}' is a Device type — use platform_add instead. "
                "platform_register_hardware is only for IP-addressable hardware: "
                "SCALEXIO, DS1202, DS1203, DS1403, MABX, VEOS.",
                error_code="BRIDGE_INVALID_ARGUMENT",
                recovery_hint=(
                    "Use platform_add for Bus, XCP, or Diagnostics. Call platform_list_types for available types."
                ),
            )
        elif platform_type == "DS1104":
            raise BridgePreconditionError(
                f"'{platform_type}' does not support IP-based registration. Use platform_add instead.",
                error_code="BRIDGE_INVALID_ARGUMENT",
                recovery_hint="Use platform_add for DS1104.",
            )
        elif platform_type in _HARDWARE_PLATFORM_TYPES:
            # Shouldn't reach here (logic error in _HARDWARE_PLATFORM_TYPES definition)
            raise BridgePreconditionError(
                f"Internal error: '{platform_type}' is hardware but not IP-addressable.",
                error_code="BRIDGE_INTERNAL_ERROR",
            )
        else:
            # Unknown type entirely
            raise BridgePreconditionError(
                f"Unknown platform type '{platform_type}'. "
                f"Valid IP-addressable hardware: {sorted(valid_hardware_types)}",
                error_code="BRIDGE_INVALID_ARGUMENT",
                recovery_hint="Call platform_list_hardware_types() to discover all hardware.",
            )

    # Verify and upgrade APIVersion if needed for this platform type
    _verify_platform_against_api_version(app, platform_type)

    try:
        pm = app.PlatformManagement
        reg_info = pm.CreatePlatformRegistrationInfo(_PLATFORM_TYPE_INT[platform_type])
        if platform_type in _NETCLIENT_REG_TYPES:
            reg_info.NetClient = ip_address
        else:
            # SCALEXIO / DS1202 / DS1203 / DS1403
            sub = reg_info.RegistrationInfos.Add()
            sub.IPAddress = ip_address
        registered_platform = pm.RegisterPlatform(reg_info)
        unique_name = str(registered_platform.UniqueName)
        return {
            "registered": True,
            "unique_name": unique_name,
            "display_name": str(registered_platform.DisplayName),
            "platform_type": platform_type,
            "ip_address": ip_address,
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IPmPlatformManagement", method="RegisterPlatform") from exc


# ── platform_list_registered_hardware ─────────────────────────────────────────


def list_registered_hardware(app: Any) -> dict[str, Any]:
    """List all recent hardware platforms from PlatformManagement.RecentPlatformConfiguration.

    Iterates the IPmRecentPlatformConfiguration collection (backed by RecentHardware.xml)
    to enumerate all hardware platforms that have ever been registered with this
    ControlDesk instance — including those not currently active in the session.

    Differs from PlatformManagement.Platforms which only contains platforms registered
    in the current session; RecentPlatformConfiguration persists across ControlDesk restarts.

    Source: ControlDesk Automation API — IPmRecentPlatformConfiguration <<Collection>> (p. 2127)
            PlatformConfiguration.py:
                Application.PlatformManagement.RecentPlatformConfiguration[0].UniqueName
    """
    try:
        pm = app.PlatformManagement
        recent = pm.RecentPlatformConfiguration
        count = int(recent.Count)
        registered = []
        for i in range(count):
            try:
                plat = recent.Item(i)
                entry: dict[str, Any] = {
                    "index": i,
                    "unique_name": str(plat.UniqueName),
                }
                # Optional properties — present on most hardware types but not guaranteed
                # on all entries in RecentPlatformConfiguration. Use try/except instead
                # of hasattr() which can hang on COM objects.
                try:
                    entry["name"] = str(plat.Name)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    entry["type"] = _PLATFORM_TYPE_NAME.get(int(plat.Type), str(plat.Type))
                except Exception:  # noqa: BLE001
                    pass
                try:
                    entry["connection_state"] = _connection_state_str(plat.ConnectionState)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    entry["ip_address"] = str(plat.IPAddress)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    entry["board_name"] = str(plat.BoardName)
                except Exception:  # noqa: BLE001
                    pass
                try:
                    entry["serial_number"] = str(plat.SerialNumber)
                except Exception:  # noqa: BLE001
                    pass
                registered.append(entry)
            except Exception:  # noqa: BLE001
                # Best effort: Count succeeded, but reading this particular
                # entry's properties failed. Skip it.
                continue
        return {
            "registered_platforms": registered,
            "count": len(registered),
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IPmPlatformManagement", method="RecentPlatformConfiguration") from exc


# ── platform_get_registered_info ──────────────────────────────────────────────


def get_registered_info(app: Any, index: int) -> dict[str, Any]:
    """Get full metadata for a recent hardware platform by index.

    Access the PlatformManagement.RecentPlatformConfiguration collection by index
    to retrieve a hardware platform's complete information from the persistent
    recent-hardware registry (RecentHardware.xml).

    Args:
        app: COM Application object
        index: Zero-based index into PlatformManagement.RecentPlatformConfiguration

    Returns:
        Dictionary with full platform metadata

    Source: ControlDesk Automation API — IPmRecentPlatformConfiguration.Item() (p. 2127)
    """
    try:
        pm = app.PlatformManagement
        recent = pm.RecentPlatformConfiguration
        try:
            plat = recent.Item(index)
        except (IndexError, ValueError) as exc:
            raise BridgePreconditionError(
                f"Registered platform index {index} not found. "
                "Use platform_list_registered_hardware() to discover available platforms.",
                error_code="BRIDGE_INVALID_ARGUMENT",
                recovery_hint="Call platform_list_registered_hardware() to list platforms.",
            ) from exc

        result: dict[str, Any] = {"index": index, "unique_name": str(plat.UniqueName)}
        # Optional properties — present on most hardware types but not guaranteed
        # on all entries in RecentPlatformConfiguration. Use try/except instead
        # of hasattr() which can hang on COM objects.
        try:
            result["name"] = str(plat.Name)
        except Exception:  # noqa: BLE001
            pass
        try:
            result["type"] = _PLATFORM_TYPE_NAME.get(int(plat.Type), str(plat.Type))
        except Exception:  # noqa: BLE001
            pass
        try:
            result["connection_state"] = _connection_state_str(plat.ConnectionState)
        except Exception:  # noqa: BLE001
            pass
        for prop_name in ["IPAddress", "BoardName", "SerialNumber", "PlugState"]:
            try:
                result[_snake_case(prop_name)] = getattr(plat, prop_name)
            except Exception:  # noqa: BLE001
                pass  # Skip properties that fail to read
        return result
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IPmPlatformManagement", method="RecentPlatformConfiguration") from exc


def _snake_case(camel_case: str) -> str:
    """Convert CamelCase to snake_case for property names."""
    import re

    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", camel_case)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


# ── platform_clear_registered ─────────────────────────────────────────────────


def clear_registered_platforms(app: Any, force_driver_reset: bool = False) -> None:
    """Remove all registered platforms from PlatformManagement.

    Args:
        app: COM Application object.
        force_driver_reset: When True, forces a hardware driver reset in addition
            to clearing registered platforms (ClearSystem(True)). Use True to
            recover from a hung/stale state. Default False is the safe clear.
    """
    try:
        app.PlatformManagement.ClearSystem(force_driver_reset)
    except Exception as exc:
        raise map_com_error(exc, interface="IPmPlatformManagement", method="ClearSystem") from exc


# ── platform_refresh_configuration ────────────────────────────────────────────


def refresh_platform_configuration(app: Any) -> dict[str, Any]:
    """Trigger ControlDesk to re-read the platform configuration from hardware.

    Calls IPmPlatformManagement.RefreshPlatformConfiguration().
    Useful after hardware changes, cable swaps, or when platform configuration
    appears stale without a full restart.

    Source: SQSCalDeskToolautomationHelper.py RefreshPlatformConfiguration()
    """
    try:
        app.PlatformManagement.RefreshPlatformConfiguration()
        return {"refreshed": True, "operation": "RefreshPlatformConfiguration"}
    except Exception as exc:
        raise map_com_error(exc, interface="IPmPlatformManagement", method="RefreshPlatformConfiguration") from exc


# ── platform_refresh_interface_connections ────────────────────────────────────


def refresh_interface_connections(app: Any, force_driver_reset: bool = True) -> dict[str, Any]:
    """Re-enumerate all hardware interface connections.

    Calls IPmPlatformManagement.RefreshInterfaceConnections(force_driver_reset).
    Used to recover from a failed connect attempt, after a hardware unplug/replug,
    or after ClearSystem to restore a clean interface state.

    Args:
        app: COM Application object.
        force_driver_reset: When True (default), resets hardware interface drivers
            before re-enumerating. Use False for a lighter refresh.

    Source: TTD_FreeMABX.py, TC_0001_Reset_Common_Settings.py:
        cdng.PlatformManagement.RefreshInterfaceConnections(True)  # ForceDriverReset
    """
    try:
        app.PlatformManagement.RefreshInterfaceConnections(force_driver_reset)
        return {
            "refreshed": True,
            "operation": "RefreshInterfaceConnections",
            "force_driver_reset": force_driver_reset,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IPmPlatformManagement", method="RefreshInterfaceConnections") from exc


# ── platform_set_enabled ──────────────────────────────────────────────────────


def set_platform_enabled(app: Any, platform_name: str, enabled: bool) -> dict[str, Any]:
    """Enable or disable a platform via GeneralSettings.EnablePlatform.

    Calls IXaExperimentPlatform.GeneralSettings.EnablePlatform = enabled.
    A disabled platform is skipped during experiment start and will not connect.
    Does NOT disconnect a currently connected platform — call platform_disconnect first.

    Source: SQSCalDeskToolautomationHelper.py SetPlatformEnabled():
        Platform.GeneralSettings.EnablePlatform = State
    """
    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    try:
        plat.GeneralSettings.EnablePlatform = enabled
        return {
            "configured": True,
            "platform_name": platform_name,
            "enabled": enabled,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="GeneralSettings.EnablePlatform") from exc


# ── platform_add_variable_description ────────────────────────────────────────


def add_variable_description(
    app: Any,
    platform_name: str,
    file_path: str,
) -> dict[str, Any]:
    """Load a variable description into the named platform.

    The file extension determines which COM call is made:
    - .a2l → XCPonCAN, XCPonEthernet, CCP, GSI2
              Companion .mot auto-discovered in the same folder.
              If found: VariableDescriptions.AddWithImage(a2l, mot)
              If not:   VariableDescriptions.Add(a2l)
    - .sdf  → SCALEXIO, DS1202, DS1203, DS1403, MABX, VEOS
              VariableDescriptions.Add(sdf)
    - .dbc, .ldf, .fibex, .arxml → Bus Device platforms
              VariableDescriptions.Add(path)
    - GNSS, Diagnostic2 → no variable description support (raises BridgePreconditionError).
    """
    import os

    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    plat_type = _PLATFORM_TYPE_NAME.get(int(plat.Type), str(plat.Type))

    if plat_type in _NO_VARIABLE_DESCRIPTION_TYPES:
        raise BridgePreconditionError(
            f"Platform '{platform_name}' is of type '{plat_type}', which does not "
            "support variable descriptions. "
            "Diagnostic2 uses ODX databases; GNSS has no variable description concept.",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint=(
                "Variable descriptions are supported for: "
                "Bus Device platforms (CANMonitoring, LINMonitoring, EthernetMonitoring, "
                "FlexRayMonitoring — provide .dbc/.ldf/.arxml/.fibex), "
                "Measurement & Calibration platforms (XCPonCAN, XCPonEthernet, CCP, GSI2 "
                "— provide .a2l; companion .mot is auto-discovered), and "
                "hardware platforms (SCALEXIO, DS1202, DS1203, DS1403, MABX, VEOS — provide .sdf)."
            ),
        )

    ext = os.path.splitext(file_path)[1].lower()
    name = os.path.splitext(os.path.basename(file_path))[0]

    # Extension → allowed platform types
    ext_allowed: dict[str, frozenset[str]] = {
        ".a2l": _XCP_PLATFORM_TYPES,
        ".sdf": _HARDWARE_PLATFORM_TYPES,
        ".dbc": frozenset(["CANMonitoring"]),
        ".ldf": frozenset(["LINMonitoring"]),
        ".fibex": frozenset(["FlexRayMonitoring"]),
        ".arxml": _BUS_CONFIG_TYPES,
    }

    allowed = ext_allowed.get(ext)
    if allowed is None:
        raise BridgePreconditionError(
            f"Unsupported file extension '{ext}'. "
            "Supported extensions: .a2l (XCP/CCP/GSI2), .sdf (hardware), "
            ".dbc (CANMonitoring), .ldf (LINMonitoring), "
            ".fibex (FlexRayMonitoring), .arxml (AUTOSAR bus config).",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Provide a file with a supported extension.",
        )

    if plat_type not in allowed:
        if plat_type in _XCP_PLATFORM_TYPES:
            type_hint = ".a2l (companion .mot auto-discovered)"
        elif plat_type in _HARDWARE_PLATFORM_TYPES:
            type_hint = ".sdf"
        elif plat_type in _BUS_CONFIG_TYPES:
            type_hint = ".dbc (CAN) / .ldf (LIN) / .fibex (FlexRay) / .arxml (AUTOSAR)"
        else:
            type_hint = "a supported file type"
        raise BridgePreconditionError(
            f"File extension '{ext}' is not valid for platform type '{plat_type}'. "
            f"For '{plat_type}', use: {type_hint}.",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint=f"For '{plat_type}', use: {type_hint}.",
        )

    try:
        if ext == ".a2l":
            # Auto-discover companion .mot in the same directory
            mot_path = os.path.splitext(file_path)[0] + ".mot"
            if os.path.isfile(mot_path):
                plat.VariableDescriptions.AddWithImage(file_path, mot_path)
                return {
                    "added": True,
                    "platform_name": platform_name,
                    "variable_description_name": name,
                    "file_path": file_path,
                    "companion_mot_path": mot_path,
                }
            else:
                plat.VariableDescriptions.Add(file_path)
                return {
                    "added": True,
                    "platform_name": platform_name,
                    "variable_description_name": name,
                    "file_path": file_path,
                    "companion_mot_path": None,
                }
        else:
            plat.VariableDescriptions.Add(file_path)
            return {
                "added": True,
                "platform_name": platform_name,
                "variable_description_name": name,
                "file_path": file_path,
            }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        method = "AddWithImage" if ext == ".a2l" else "Add"
        raise map_com_error(exc, interface="IXaVariableDescriptions", method=method) from exc


# ── platform_configure_calibration_behavior ───────────────────────────────────


def configure_calibration_behavior(
    app: Any,
    platform_name: str,
    calibration_behavior: str,
    initial_page: str,
) -> dict[str, Any]:
    """Set calibration startup behavior and initial page for the named platform."""
    _require_active_experiment(app)
    if calibration_behavior not in _ONLINE_CALIBRATION_BEHAVIOR:
        raise BridgePreconditionError(
            f"Unknown calibration_behavior '{calibration_behavior}'. "
            f"Valid values: {sorted(_ONLINE_CALIBRATION_BEHAVIOR.keys())}",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Use one of the listed calibration_behavior values.",
        )
    if initial_page not in _INITIAL_PAGE:
        raise BridgePreconditionError(
            f"Unknown initial_page '{initial_page}'. Valid values: {sorted(_INITIAL_PAGE.keys())}",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Use one of the listed initial_page values.",
        )
    plat = _get_platform(app, platform_name)
    try:
        plat.GeneralSettings.StartOnlineCalibrationBehavior = _ONLINE_CALIBRATION_BEHAVIOR[calibration_behavior]
        plat.GeneralSettings.InitialPage = _INITIAL_PAGE[initial_page]
        return {
            "configured": True,
            "platform_name": platform_name,
            "calibration_behavior": calibration_behavior,
            "initial_page": initial_page,
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="GeneralSettings") from exc


# ── platform_set_api_version ──────────────────────────────────────────────────


def set_api_version(app: Any, version: str) -> dict[str, Any]:
    """Set the platform automation API version on PlatformManagement.

    API Version 2 is required before adding XCPonEthernet platforms or
    certain hardware types (SCALEXIO, DS1202, DS1203, DS1403, etc.).

    Args:
        version: Either "APIVersion1" (default) or "APIVersion2".
                 COM expects an integer (1 or 2), not a string.

    Returns:
        A dict with the version as an integer and configuration status.
    """
    if version not in _API_VERSION:
        raise BridgePreconditionError(
            f"Unknown API version '{version}'. Valid values: {sorted(_API_VERSION.keys())}",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Use 'APIVersion1' or 'APIVersion2'.",
        )
    try:
        # Convert string to integer for COM
        version_int = _API_VERSION[version]
        app.PlatformManagement.PlatformAutomationAPIVersion = version_int
        return {"version_string": version, "version_integer": version_int, "configured": True}
    except Exception as exc:
        raise map_com_error(
            exc,
            interface="IPmPlatformManagement",
            method="PlatformAutomationAPIVersion",
        ) from exc


# ── platform_configure_transport ─────────────────────────────────────────────


def configure_transport(
    app: Any,
    platform_name: str,
    baud_rate: int | None,
    ethernet_protocol: str | None,
    automatic_adapter: bool | None,
    adapter_name: str | None,
) -> dict[str, Any]:
    """Configure transport-level settings for the named platform."""
    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    plat_type = _PLATFORM_TYPE_NAME.get(int(plat.Type), str(plat.Type))

    result: dict[str, Any] = {"platform_name": platform_name}

    if plat_type in _CAN_BAUD_TYPES and baud_rate is not None:
        try:
            plat.CANSettings.BaudRate = baud_rate
            result["configured"] = True
            result["baud_rate"] = baud_rate
            return result
        except Exception as exc:
            raise map_com_error(exc, interface="IPmCANSettings", method="BaudRate") from exc

    if plat_type == "XCPonEthernet":
        if ethernet_protocol is not None:
            try:
                plat.EthernetSettings.EthernetProtocol = ethernet_protocol
                result["ethernet_protocol"] = ethernet_protocol
            except Exception as exc:
                raise map_com_error(exc, interface="IPmEthernetSettings", method="EthernetProtocol") from exc

        if automatic_adapter is True:
            try:
                plat.NetworkAdapterSelection.AutomaticAssignment = True
                result["configured"] = True
                result["automatic_adapter"] = True
                result["adapter_name"] = None
                return result
            except Exception as exc:
                raise map_com_error(
                    exc,
                    interface="IPmNetworkAdapterSelection",
                    method="AutomaticAssignment",
                ) from exc

        if automatic_adapter is False:
            if adapter_name is None:
                # Discovery mode: return available adapters
                try:
                    adapters_com = plat.NetworkAdapterSelection.NetworkAdapters
                    adapters = [str(adapters_com.Item(i).Description) for i in range(1, int(adapters_com.Count) + 1)]
                    return {
                        "configured": False,
                        "platform_name": platform_name,
                        "available_adapters": adapters,
                        "message": (
                            "adapter_name is required when automatic_adapter=False. "
                            "Re-call with one of the available_adapters values."
                        ),
                    }
                except Exception as exc:
                    raise map_com_error(
                        exc,
                        interface="IPmNetworkAdapterSelection",
                        method="NetworkAdapters",
                    ) from exc
            else:
                try:
                    plat.NetworkAdapterSelection.AutomaticAssignment = False
                    plat.NetworkAdapterSelection.SelectedAdapterDescription = adapter_name
                    result["configured"] = True
                    result["automatic_adapter"] = False
                    result["adapter_name"] = adapter_name
                    return result
                except Exception as exc:
                    raise map_com_error(
                        exc,
                        interface="IPmNetworkAdapterSelection",
                        method="SelectedAdapterDescription",
                    ) from exc

        result["configured"] = True
        return result

    # No applicable params
    result["configured"] = True
    return result


# ── platform_list_interfaces ──────────────────────────────────────────────────


def list_interfaces(app: Any, platform_name: str) -> dict[str, Any]:
    """Enumerate vendors, interfaces, and channel counts for a CAN platform."""
    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    plat_type = _PLATFORM_TYPE_NAME.get(int(plat.Type), str(plat.Type))
    if plat_type not in _MONITORING_INTERFACE_TYPES:
        raise BridgePreconditionError(
            f"Platform '{platform_name}' is of type '{plat_type}'. "
            "platform_list_interfaces applies to CAN-bus platforms only: "
            "XCPonCAN, CANMonitoring, LINMonitoring, FlexRayMonitoring, CCP.",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Verify the platform type with platform_get_info.",
        )
    # NOTE: CANMonitoring / LINMonitoring / FlexRayMonitoring ARE in _MONITORING_INTERFACE_TYPES
    # and support InterfaceSelection.Vendors — they fall through to the enumeration below.
    # EthernetMonitoring / GNSS are NOT in _MONITORING_INTERFACE_TYPES and are caught by the
    # guard above (raises BridgePreconditionError).
    try:
        vendors_com = plat.InterfaceSelection.Vendors
        vendors_count = int(vendors_com.Count)
        vendors = []
        for vi in range(0, vendors_count):
            vendor = vendors_com.Item(vi)
            vendor_name = str(vendor.Name)
            ifaces_com = vendor.AvailableInterfaces
            ifaces_count = int(ifaces_com.Count)
            interfaces = []
            for ii in range(0, ifaces_count):
                iface = ifaces_com.Item(ii)
                interfaces.append(
                    {
                        "interface_name": str(iface.Name),
                        "channel_count": int(iface.Channels.Count),
                    }
                )
            vendors.append({"vendor_name": vendor_name, "interfaces": interfaces})
        return {
            "platform_name": platform_name,
            "interfaces": vendors,
            "total_count": len(vendors),
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaInterfaceSelection", method="Vendors") from exc


# ── platform_select_interface_manual ─────────────────────────────────────────


def select_interface_manual(
    app: Any,
    platform_name: str,
    vendor_name: str,
    interface_name: str,
    channel_index: int,
) -> dict[str, Any]:
    """Select vendor, interface, and channel for a CAN platform."""
    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    try:
        channel = (
            plat.InterfaceSelection.Vendors.Item(vendor_name)
            .AvailableInterfaces.Item(interface_name)
            .Channels.Item(channel_index)
        )
        channel.Select()
        return {
            "platform_name": platform_name,
            "vendor": vendor_name,
            "interface": interface_name,
            "channel_index": channel_index,
            "selected": True,
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaInterfaceSelection", method="Channels.Select") from exc


# ── platform_connect ──────────────────────────────────────────────────────────


def connect_platform(app: Any, platform_name: str) -> dict[str, Any]:
    """Establish the communication link for the named platform."""
    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    try:
        plat.Connect()
        connection_state = _connection_state_str(plat.ConnectionState)
        return {
            "connected": True,
            "platform_name": platform_name,
            "connection_state": connection_state,
            "timestamp_utc": _utc_now(),
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="Connect") from exc


# ── platform_disconnect ───────────────────────────────────────────────────────


def disconnect_platform(app: Any, platform_name: str) -> dict[str, Any]:
    """Release the communication link for the named platform."""
    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    try:
        plat.Disconnect()
        connection_state = _connection_state_str(plat.ConnectionState)
        return {
            "disconnected": True,
            "platform_name": platform_name,
            "connection_state": connection_state,
            "timestamp_utc": _utc_now(),
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="Disconnect") from exc


# ── platform_get_connection_state ─────────────────────────────────────────────


def get_connection_state(app: Any, platform_name: str) -> dict[str, Any]:
    """Return the current connection state of the named platform."""
    _require_active_experiment(app)
    plat = _get_platform(app, platform_name)
    try:
        state = _connection_state_str(plat.ConnectionState)
        return {
            "platform_name": platform_name,
            "connection_state": state,
            "is_connected": state == "Connected",
            "timestamp_utc": _utc_now(),
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="ConnectionState") from exc


# ── platform_configure ───────────────────────────────────────────────────────


def configure_platform(
    app: Any,
    platform_name: str,
    can_interface: str | None,
    ip_address: str | None,
    mac_address: str | None,
    board_name: str | None,
    assignment_mode: str | None,
    calibration_behavior: str | None,
) -> dict[str, Any]:
    """Configure assignment / interface-selection settings for the named platform.

    Behaviour is type-driven:

    XCPonCAN / CCP / CANMonitoring / LINMonitoring / FlexRayMonitoring
        ``can_interface="Virtual"``  → selects the first dSPACE Virtual channel
        ``can_interface="Automatic"`` → enables AutomaticAssignment
        ``can_interface=<name>``      → selects the named interface channel 0

    SCALEXIO / DS1202 (MLBX) / DS1203 (MLBXII) / DS1403 (MABXIII)
        Uses SMART assignment (Assignment.Assignments collection).
        ``ip_address``    → IPAddress of the hardware unit (clears board_name first)
        ``mac_address``   → MACAddress, only valid with assignment_mode="Identical"
        ``board_name``    → BoardName (clears ip_address first)
        ``assignment_mode`` → "FirstAvailable" | "AnyEqual" | "Identical"

    MABX
        ``ip_address``  → sets Assignment.NetClient (Net connection)
        (no ip_address) → uses Bus connection

    VEOS
        ``ip_address``  → sets Assignment.NetClient (defaults to 127.0.0.1)

    DS1104 / DS1005 / DS1006 / DS1007
        ``assignment_mode`` → "FirstAvailable" | "AnyEqual" | "Identical"
        ``mac_address``     → SerialNumber, only valid with assignment_mode="Identical"
        ``board_name``      → BoardName

    All platform types
        ``calibration_behavior`` → sets GeneralSettings.StartOnlineCalibrationBehavior
    """
    _require_active_experiment(app)
    if calibration_behavior is not None and calibration_behavior not in _ONLINE_CALIBRATION_BEHAVIOR:
        raise BridgePreconditionError(
            f"Unknown calibration_behavior '{calibration_behavior}'. "
            f"Valid values: {sorted(_ONLINE_CALIBRATION_BEHAVIOR.keys())}",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Use one of the listed calibration_behavior values.",
        )
    if assignment_mode is not None and assignment_mode not in _ASSIGNMENT_MODE:
        raise BridgePreconditionError(
            f"Unknown assignment_mode '{assignment_mode}'. Valid values: {sorted(_ASSIGNMENT_MODE.keys())}",
            error_code="BRIDGE_INVALID_ARGUMENT",
            recovery_hint="Use 'FirstAvailable', 'AnyEqual', or 'Identical'.",
        )

    plat = _get_platform(app, platform_name)
    plat_type = _PLATFORM_TYPE_NAME.get(int(plat.Type), str(plat.Type))
    result: dict[str, Any] = {"platform_name": platform_name, "platform_type": plat_type}

    try:
        # ── CAN-interface selection (XCPonCAN / CCP / CANMonitoring / LINMonitoring / FlexRay)
        # NOTE: _BUS_DEVICE_TYPES ∩ _MONITORING_INTERFACE_TYPES = {CANMonitoring, LINMonitoring,
        # FlexRayMonitoring}.  These types support InterfaceSelection.Vendors and must reach
        # this branch.  EthernetMonitoring uses configure_transport; GNSS has no interface
        # selection — neither hits this path.
        if can_interface is not None and plat_type in _MONITORING_INTERFACE_TYPES:
            if can_interface == "Automatic":
                plat.InterfaceSelection.AutomaticAssignment = True
                result["can_interface"] = "Automatic"
            else:
                # Select by name from dSPACE vendor list
                available = plat.InterfaceSelection.Vendors.Item("dSPACE").AvailableInterfaces
                count = int(available.Count)
                matched = False
                for idx in range(count):
                    iface = available.Item(idx)
                    if str(iface.Name) == can_interface:
                        iface.Channels.Item(0).Select()
                        matched = True
                        result["can_interface"] = can_interface
                        break
                if not matched:
                    raise BridgePreconditionError(
                        f"CAN interface '{can_interface}' not found on platform '{platform_name}'. "
                        "Call platform_list_interfaces to see available interfaces.",
                        error_code="BRIDGE_INVALID_ARGUMENT",
                        recovery_hint=("Use platform_list_interfaces to discover valid interface names."),
                    )

        # ── SMART assignment (SCALEXIO / DS1202 / DS1203 / DS1403) ────────────
        elif plat_type in _SMART_ASSIGNMENT_TYPES:
            if assignment_mode is not None:
                plat.Assignment.Mode = _ASSIGNMENT_MODE[assignment_mode]
                result["assignment_mode"] = assignment_mode

            # Get or create the single assignment entry
            assignments = plat.Assignment.Assignments
            if int(assignments.Count) == 0:
                current_assignment = assignments.CreateNewAssignment()
            else:
                current_assignment = assignments.Item(0)

            if mac_address is not None:
                # MACAddress is valid for Identical mode only
                current_assignment.MACAddress = mac_address
                result["mac_address"] = mac_address

            if board_name is not None:
                # BoardName and IPAddress are mutually exclusive — clear IPAddress first
                if str(current_assignment.IPAddress) != "":
                    current_assignment.IPAddress = ""
                current_assignment.BoardName = board_name
                result["board_name"] = board_name

            if ip_address is not None:
                # IPAddress and BoardName are mutually exclusive — clear BoardName first
                if str(current_assignment.BoardName) != "":
                    current_assignment.BoardName = ""
                current_assignment.IPAddress = ip_address
                result["ip_address"] = ip_address

        # ── MABX (legacy NetClient assignment) ────────────────────────────────
        elif plat_type in _NETCLIENT_ASSIGNMENT_TYPES:
            if ip_address is not None:
                plat.Assignment.ConnectionType = 1  # Net connection
                plat.Assignment.NetClient = ip_address
                result["connection_type"] = "Net"
                result["ip_address"] = ip_address
            else:
                plat.Assignment.ConnectionType = 0  # Bus connection
                result["connection_type"] = "Bus"

            if assignment_mode is not None:
                plat.Assignment.Mode = _ASSIGNMENT_MODE[assignment_mode]
                result["assignment_mode"] = assignment_mode

        # ── VEOS ──────────────────────────────────────────────────────────────
        elif plat_type in _VEOS_ASSIGNMENT_TYPES:
            effective_ip = ip_address or "127.0.0.1"
            plat.Assignment.NetClient = effective_ip
            result["ip_address"] = effective_ip

        # ── DS1104 / DS1005 / DS1006 / DS1007 (simple assignment) ─────────────
        elif plat_type in _DS1104_ASSIGNMENT_TYPES:
            if assignment_mode is not None:
                plat.Assignment.Mode = _ASSIGNMENT_MODE[assignment_mode]
                result["assignment_mode"] = assignment_mode
                # SerialNumber (passed as mac_address field) is for Identical mode
                if assignment_mode == "Identical" and mac_address is not None:
                    plat.Assignment.SerialNumber = mac_address
                    result["serial_number"] = mac_address

            if board_name is not None:
                plat.Assignment.BoardName = board_name
                result["board_name"] = board_name

        # ── Calibration behavior (XCP + Hardware types only) ──────────────────
        # Bus Device types and Diagnostic2 do not expose StartOnlineCalibrationBehavior.
        if calibration_behavior is not None and plat_type in _CALIBRATION_BEHAVIOR_TYPES:
            plat.GeneralSettings.StartOnlineCalibrationBehavior = _ONLINE_CALIBRATION_BEHAVIOR[calibration_behavior]
            result["calibration_behavior"] = calibration_behavior

        result["configured"] = True
        return result

    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="configure_platform") from exc


# ── platform_rename ───────────────────────────────────────────────────────────


def rename_platform(app: Any, platform_name: str, new_name: str) -> dict[str, Any]:
    """Rename a platform in the active experiment.

    Calls IXaExperimentPlatforms.Rename(old_name, new_name).
    """
    _require_active_experiment(app)
    try:
        app.ActiveExperiment.Platforms.Rename(platform_name, new_name)
        return {
            "renamed": True,
            "old_name": platform_name,
            "new_name": new_name,
            "timestamp_utc": _utc_now(),
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatforms", method="Rename") from exc


# ── platform_list_types ───────────────────────────────────────────────────────


def list_platform_types() -> dict[str, Any]:
    """Return the static catalog of all supported platform types, grouped by category.

    No COM call is made — this is pure static data derived from the
    PlatformType <<Enumeration>> in the ControlDesk Automation API (PDF p.1981).
    """
    return {
        "categories": [
            {
                "category": "Bus Device",
                "description": (
                    "Bus-level monitoring platforms. Added via platform_add. "
                    "No variable descriptions or IP registration required."
                ),
                "types": [
                    {"name": "CANMonitoring", "integer_value": 10},
                    {"name": "LINMonitoring", "integer_value": 19},
                    {"name": "FlexRayMonitoring", "integer_value": 24},
                    {"name": "EthernetMonitoring", "integer_value": 32},
                ],
            },
            {
                "category": "GPS Device",
                "description": (
                    "GNSS GPS receiver device. Added via platform_add. "
                    "Requires serial port configuration via platform_configure_gnss. "
                    "No variable descriptions required."
                ),
                "types": [
                    {"name": "GNSS", "integer_value": 34},
                ],
            },
            {
                "category": "Diagnostics",
                "description": (
                    "ECU Diagnostics platform. Added via platform_add. "
                    "Uses ODX databases — no A2L/SDF variable descriptions."
                ),
                "types": [
                    {"name": "Diagnostic2", "integer_value": 27},
                ],
            },
            {
                "category": "Measurement & Calibration",
                "description": (
                    "XCP/CCP-based measurement and calibration platforms. "
                    "Added via platform_add. "
                    "Physical ECU: provide both a2l_path and mot_path. "
                    "XCPonEthernet with SIL/VEOS inheritance: a2l_path only."
                ),
                "types": [
                    {"name": "XCPonCAN", "integer_value": 4},
                    {"name": "XCPonEthernet", "integer_value": 20},
                    {"name": "CCP", "integer_value": 6},
                    {"name": "GSI2", "integer_value": 25},
                ],
            },
            {
                "category": "Hardware",
                "description": (
                    "Physical and virtual hardware platforms. "
                    "IP-addressable types (SCALEXIO, DS1202, DS1203, DS1403, MABX): "
                    "register via platform_register_hardware, "
                    "then activate via platform_activate_registered. "
                    "VEOS: local VEOS uses platform_add directly; "
                    "remote VEOS uses register + activate. "
                    "XILAPIMAPort: register via Register Platform dialog (config-file-based). "
                    "DS1104: use platform_add directly (no IP registration). "
                    "All hardware types require sdf_path for variable descriptions."
                ),
                "types": [
                    {"name": "SCALEXIO", "integer_value": 22},
                    {"name": "DS1202", "integer_value": 30, "alias": "MicroLabBox"},
                    {"name": "DS1203", "integer_value": 35, "alias": "MicroLabBox II"},
                    {"name": "DS1403", "integer_value": 33, "alias": "MicroAutoBox III"},
                    {"name": "MABX", "integer_value": 0, "alias": "MicroAutoBox II"},
                    {"name": "VEOS", "integer_value": 26},
                    {"name": "XILAPIMAPort", "integer_value": 31},
                    {"name": "DS1104", "integer_value": 16},
                    {"name": "DS1005", "integer_value": 3, "alias": "Legacy"},
                    {"name": "DS1006", "integer_value": 17, "alias": "Legacy"},
                    {"name": "DS1007", "integer_value": 29, "alias": "Legacy"},
                ],
            },
        ],
        "usage_note": (
            "Pass the 'name' string to platform_add or platform_register_hardware. "
            "The MCP server converts it to the required integer enum internally. "
            "Source: ControlDesk Automation API PlatformType enumeration (2026-A)."
        ),
    }
