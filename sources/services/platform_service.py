"""Service facade for ControlDesk platform management operations.

Owns: orchestration of platform registration, configuration, and connection lifecycle.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sources import com_bridge
from sources.com_bridge.errors import BridgeError, BridgeOperationError
from sources.config.settings import get_settings
from sources.models.envelope_builder import build_envelope
from sources.models.errors import ErrorEnvelope
from sources.models.platform import (
    PlatformAddInput,
    PlatformAddRegisteredInput,
    PlatformAddRegisteredResult,
    PlatformAddResult,
    PlatformAddVariableDescriptionInput,
    PlatformAddVariableDescriptionResult,
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
    PlatformGetConnectionStateInput,
    PlatformGetConnectionStateResult,
    PlatformGetInfoInput,
    PlatformGetInfoResult,
    PlatformGetRegisteredInfoResult,
    PlatformListHardwareTypesResult,
    PlatformListInterfacesInput,
    PlatformListInterfacesResult,
    PlatformListRegisteredHardwareResult,
    PlatformListResult,
    PlatformListTypesResult,
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
)
from sources.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _get_app_lambda():
    return lambda: com_bridge.get_connection().get_app()


async def list_platforms() -> PlatformListResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        platforms = await com_bridge.dispatch(com_bridge.domains.platform_com.list_platforms, app)
        return PlatformListResult(platforms=platforms, count=len(platforms))
    except BridgeError as exc:
        _log.warning("platform_list failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_list unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def get_platform_info(params: PlatformGetInfoInput) -> PlatformGetInfoResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        info = await com_bridge.dispatch(
            com_bridge.domains.platform_com.get_platform_info, app, params.platform_name
        )
        return PlatformGetInfoResult(**info)
    except BridgeError as exc:
        _log.warning("platform_get_info failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_get_info unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def add_platform(params: PlatformAddInput) -> PlatformAddResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.add_platform, app, params.platform_type.value
        )
        return PlatformAddResult(**result)
    except BridgeError as exc:
        _log.warning("platform_add failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_add unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def add_registered_platform(
    params: PlatformAddRegisteredInput,
) -> PlatformAddRegisteredResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.add_registered_platform, app, params.unique_name
        )
        return PlatformAddRegisteredResult(**result)
    except BridgeError as exc:
        _log.warning("platform_add_registered failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_add_registered unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def remove_platform(params: PlatformRemoveInput) -> PlatformRemoveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.remove_platform, app, params.platform_name
        )
        return PlatformRemoveResult(**result)
    except BridgeError as exc:
        _log.warning("platform_remove failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_remove unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def register_hardware_platform(
    params: PlatformRegisterHardwareInput,
) -> PlatformRegisterHardwareResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.register_hardware_platform,
            app,
            params.platform_type.value,
            params.ip_address,
            timeout_ms=get_settings().com_hardware_timeout_ms,
        )
        return PlatformRegisterHardwareResult(**result)
    except BridgeError as exc:
        _log.warning("platform_register_hardware failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_register_hardware unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def clear_registered_platforms(
    params: PlatformClearRegisteredInput,
) -> PlatformClearRegisteredAborted | PlatformClearRegisteredResult | ErrorEnvelope:
    if not params.confirm:
        return PlatformClearRegisteredAborted()
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        await com_bridge.dispatch(
            com_bridge.domains.platform_com.clear_registered_platforms,
            app,
            params.force_driver_reset,
        )
        return PlatformClearRegisteredResult(
            cleared=True,
            force_driver_reset=params.force_driver_reset,
            message="All registered platforms have been removed from PlatformManagement.",
        )
    except BridgeError as exc:
        _log.warning("platform_clear_registered failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_clear_registered unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def refresh_platform_configuration(  # noqa: ARG001
    params: PlatformRefreshConfigurationInput,
) -> PlatformRefreshConfigurationResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.refresh_platform_configuration, app
        )
        return PlatformRefreshConfigurationResult(**result)
    except BridgeError as exc:
        _log.warning("platform_refresh_configuration failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_refresh_configuration unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def refresh_interface_connections(
    params: PlatformRefreshInterfaceConnectionsInput,
) -> PlatformRefreshInterfaceConnectionsResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.refresh_interface_connections,
            app,
            params.force_driver_reset,
        )
        return PlatformRefreshInterfaceConnectionsResult(**result)
    except BridgeError as exc:
        _log.warning("platform_refresh_interface_connections failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_refresh_interface_connections unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def set_platform_enabled(
    params: PlatformSetEnabledInput,
) -> PlatformSetEnabledResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.set_platform_enabled,
            app,
            params.platform_name,
            params.enabled,
        )
        return PlatformSetEnabledResult(**result)
    except BridgeError as exc:
        _log.warning("platform_set_enabled failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_set_enabled unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def add_variable_description(
    params: PlatformAddVariableDescriptionInput,
) -> PlatformAddVariableDescriptionResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.add_variable_description,
            app,
            params.platform_name,
            params.file_path,
        )
        return PlatformAddVariableDescriptionResult(**result)
    except BridgeError as exc:
        _log.warning("platform_add_variable_description failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_add_variable_description unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def configure_calibration_behavior(
    params: PlatformConfigureCalibrationBehaviorInput,
) -> PlatformConfigureCalibrationBehaviorResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.configure_calibration_behavior,
            app,
            params.platform_name,
            params.calibration_behavior.value,
            params.initial_page.value,
        )
        return PlatformConfigureCalibrationBehaviorResult(**result)
    except BridgeError as exc:
        _log.warning("platform_configure_calibration_behavior failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_configure_calibration_behavior unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def set_api_version(
    params: PlatformSetApiVersionInput,
) -> PlatformSetApiVersionResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.set_api_version, app, params.version.value
        )
        return PlatformSetApiVersionResult(**result)
    except BridgeError as exc:
        _log.warning("platform_set_api_version failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_set_api_version unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def configure_transport(
    params: PlatformConfigureTransportInput,
) -> PlatformConfigureTransportResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.configure_transport,
            app,
            params.platform_name,
            params.baud_rate,
            params.ethernet_protocol.value if params.ethernet_protocol else None,
            params.automatic_adapter,
            params.adapter_name,
        )
        return PlatformConfigureTransportResult(**result)
    except BridgeError as exc:
        _log.warning("platform_configure_transport failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_configure_transport unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def list_interfaces(
    params: PlatformListInterfacesInput,
) -> PlatformListInterfacesResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.list_interfaces, app, params.platform_name
        )
        return PlatformListInterfacesResult(**result)
    except BridgeError as exc:
        _log.warning("platform_list_interfaces failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_list_interfaces unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def select_interface_manual(
    params: PlatformSelectInterfaceManualInput,
) -> PlatformSelectInterfaceManualResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.select_interface_manual,
            app,
            params.platform_name,
            params.vendor_name,
            params.interface_name,
            params.channel_index,
        )
        return PlatformSelectInterfaceManualResult(**result)
    except BridgeError as exc:
        _log.warning("platform_select_interface_manual failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_select_interface_manual unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def connect_platform(params: PlatformConnectInput) -> PlatformConnectResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.connect_platform, app, params.platform_name
        )
        result.setdefault("timestamp_utc", _now_utc())
        return PlatformConnectResult(**result)
    except BridgeError as exc:
        _log.warning("platform_connect failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_connect unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def disconnect_platform(
    params: PlatformDisconnectInput,
) -> PlatformDisconnectResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.disconnect_platform, app, params.platform_name
        )
        result.setdefault("timestamp_utc", _now_utc())
        return PlatformDisconnectResult(**result)
    except BridgeError as exc:
        _log.warning("platform_disconnect failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_disconnect unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def get_connection_state(
    params: PlatformGetConnectionStateInput,
) -> PlatformGetConnectionStateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.get_connection_state, app, params.platform_name
        )
        result.setdefault("timestamp_utc", _now_utc())
        return PlatformGetConnectionStateResult(**result)
    except BridgeError as exc:
        _log.warning("platform_get_connection_state failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_get_connection_state unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def list_platform_types() -> PlatformListTypesResult | ErrorEnvelope:
    try:
        result = com_bridge.domains.platform_com.list_platform_types()
        return PlatformListTypesResult(**result)
    except Exception as exc:
        _log.exception("platform_list_types unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def configure_platform(
    params: PlatformConfigureInput,
) -> PlatformConfigureResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.configure_platform,
            app,
            params.platform_name,
            params.can_interface,
            params.ip_address,
            params.mac_address,
            params.board_name,
            params.assignment_mode,
            params.calibration_behavior,
        )
        return PlatformConfigureResult(**result)
    except BridgeError as exc:
        _log.warning("platform_configure failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_configure unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def rename_platform(params: PlatformRenameInput) -> PlatformRenameResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.rename_platform,
            app,
            params.platform_name,
            params.new_name,
        )
        result.setdefault("timestamp_utc", _now_utc())
        return PlatformRenameResult(**result)
    except BridgeError as exc:
        _log.warning("platform_rename failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_rename unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def list_hardware_types() -> PlatformListHardwareTypesResult:
    """List all hardware platform types grouped by registration method.

    No COM call required — returns static catalog of hardware types.

    Returns JSON with two categories:
    - ip_addressable: Platforms registered via platform_register_hardware (IP or config-file)
    - direct_add: Platforms added via platform_add without any registration
    """
    return PlatformListHardwareTypesResult(
        hardware_types=[],
        total_count=8,
        **{
            "hardware_platforms": {
                "ip_addressable": [
                    {
                        "type": "SCALEXIO",
                        "description": "dSPACE SCALEXIO real-time processor",
                        "registration_method": (
                            "IP-based (platform_register_hardware + platform_activate_registered)"
                        ),
                        "typical_use": "Real-time hardware-in-the-loop testing",
                    },
                    {
                        "type": "DS1202",
                        "description": "dSPACE MicroLabBox data acquisition unit",
                        "registration_method": (
                            "IP-based (platform_register_hardware + platform_activate_registered)"
                        ),
                        "typical_use": "Hardware data logging and measurement",
                    },
                    {
                        "type": "DS1203",
                        "description": "dSPACE MicroLabBox II multi-processor system",
                        "registration_method": (
                            "IP-based (platform_register_hardware + platform_activate_registered)"
                        ),
                        "typical_use": "Multi-processor real-time systems",
                    },
                    {
                        "type": "DS1403",
                        "description": "dSPACE MicroAutoBox III (DS1403) multi-function platform",
                        "registration_method": (
                            "IP-based (platform_register_hardware + platform_activate_registered)"
                        ),
                        "typical_use": "Automated testing and calibration",
                    },
                    {
                        "type": "MABX",
                        "description": "dSPACE MicroAutoBox II (original) automation platform",
                        "registration_method": (
                            "IP-based (platform_register_hardware + platform_activate_registered)"
                        ),
                        "typical_use": "Network-connected automation and testing",
                    },
                    {
                        "type": "VEOS",
                        "description": (
                            "Virtual ECU OS (remote VEOS). "
                            "For local VEOS (same host), use platform_add directly."
                        ),
                        "registration_method": (
                            "IP-based for remote VEOS "
                            "(platform_register_hardware + platform_activate_registered)"
                        ),
                        "typical_use": "Remote virtual ECU simulation and testing",
                    },
                    {
                        "type": "XILAPIMAPort",
                        "description": "ASAM XIL API MAPort simulation platform",
                        "registration_method": (
                            "Config-file-based via ControlDesk Register Platform dialog "
                            "(not supported via platform_register_hardware tool)"
                        ),
                        "typical_use": "Third-party simulation tool integration via XIL API",
                    },
                ],
                "direct_add": [
                    {
                        "type": "DS1104",
                        "description": "dSPACE DS1104 R&D Controller Board (legacy)",
                        "registration_method": "Direct add (platform_add, no registration)",
                        "typical_use": "Local real-time control systems",
                    },
                    {
                        "type": "VEOS",
                        "description": (
                            "Virtual ECU OS (local VEOS, same host as ControlDesk). "
                            "For remote VEOS (different host), use platform_register_hardware."
                        ),
                        "registration_method": "Direct add (platform_add, no registration)",
                        "typical_use": "Local virtual ECU simulation and offline testing",
                    },
                ],
            },
            "total_hardware_types": 8,
            "note": (
                "VEOS supports two paths: "
                "local VEOS uses platform_add directly; "
                "remote VEOS uses platform_register_hardware(ip_address) "
                "+ platform_activate_registered. "
                "XILAPIMAPort registration must be done via the ControlDesk UI (config-file-based)."
            ),
        },
    )


async def list_registered_hardware() -> PlatformListRegisteredHardwareResult | ErrorEnvelope:
    """List all registered hardware platforms from PlatformManagement.Platforms.

    No active experiment required — reads from the platform registry.
    """
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.list_registered_hardware,
            app,
        )
        return PlatformListRegisteredHardwareResult(**result)
    except BridgeError as exc:
        _log.warning("platform_list_registered_hardware failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_list_registered_hardware unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )


async def get_registered_info(index: int) -> PlatformGetRegisteredInfoResult | ErrorEnvelope:
    """Get full metadata for a registered platform by index.

    No active experiment required — reads from the platform registry.
    """
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.platform_com.get_registered_info,
            app,
            index,
        )
        return PlatformGetRegisteredInfoResult(**result)
    except BridgeError as exc:
        _log.warning("platform_get_registered_info failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("platform_get_registered_info unexpected error")
        return build_envelope(
            BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN")
        )
