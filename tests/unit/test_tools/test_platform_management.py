"""Unit tests for controldesk_mcp.tools.platform.management (all tools).

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.platform import (
    AutomationAPIVersion,
    EthernetProtocol,
    InitialPageType,
    PlatformAddRegisteredResult,
    PlatformAddResult,
    PlatformAddVariableDescriptionResult,
    PlatformAdminManageAction,
    PlatformAdminManageInput,
    PlatformClearRegisteredAborted,
    PlatformClearRegisteredResult,
    PlatformConfigureCalibrationBehaviorResult,
    PlatformConfigureTransportResult,
    PlatformConnectInput,
    PlatformConnectResult,
    PlatformDisconnectInput,
    PlatformDisconnectResult,
    PlatformDiscoverResult,
    PlatformGetConnectionStateResult,
    PlatformGetInfoResult,
    PlatformGetRegisteredInfoResult,
    PlatformHardwareManageAction,
    PlatformHardwareManageInput,
    PlatformListInterfacesResult,
    PlatformListRegisteredHardwareResult,
    PlatformListResult,
    PlatformManageAction,
    PlatformManageInput,
    PlatformQueryAction,
    PlatformQueryInput,
    PlatformRefreshConfigurationResult,
    PlatformRefreshInterfaceConnectionsResult,
    PlatformRegisterHardwareResult,
    PlatformRemoveResult,
    PlatformRenameResult,
    PlatformSelectInterfaceManualResult,
    PlatformSetApiVersionResult,
    PlatformSetEnabledResult,
    PlatformType,
)

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.platform_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── platform_manage: list ─────────────────────────────────────────────────────


class TestPlatformManageList:
    @pytest.mark.asyncio
    async def test_returns_platform_list_on_success(self) -> None:
        expected = PlatformListResult(
            platforms=[
                {
                    "name": "XCP",
                    "type": "XCPonCAN",
                    "connection_state": "Disconnected",
                    "measurement_state": "Stopped",
                    "variable_description_count": 0,
                }
            ]
        )
        with _patch_svc("list_platforms", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(PlatformQueryInput(action=PlatformQueryAction.list))

        assert isinstance(result, PlatformListResult)
        assert result["total_count"] == 1
        assert result["platforms"][0]["name"] == "XCP"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_platforms(self) -> None:
        expected = PlatformListResult(platforms=[])
        with _patch_svc("list_platforms", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(PlatformQueryInput(action=PlatformQueryAction.list))

        assert isinstance(result, PlatformListResult)
        assert result["total_count"] == 0
        assert result["platforms"] == []

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_service_error(self) -> None:
        with _patch_svc("list_platforms", return_value=_ERROR):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(PlatformQueryInput(action=PlatformQueryAction.list))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


# ── platform_manage: get_info ─────────────────────────────────────────────────


class TestPlatformManageGetInfo:
    @pytest.mark.asyncio
    async def test_returns_platform_info_on_success(self) -> None:
        expected = PlatformGetInfoResult(
            name="XCP",
            type="XCPonCAN",
            connection_state="Disconnected",
            measurement_state="Stopped",
            variable_description_count=1,
        )
        with _patch_svc("get_platform_info", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(action=PlatformQueryAction.get_info, platform_name="XCP")
            )

        assert isinstance(result, PlatformGetInfoResult)
        assert result["name"] == "XCP"
        assert result["type"] == "XCPonCAN"
        assert result["measurement_state"] == "Stopped"

    @pytest.mark.asyncio
    async def test_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_query

        result = await platform_query(
            PlatformQueryInput(action=PlatformQueryAction.get_info, platform_name=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("get_platform_info", return_value=_ERROR):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(action=PlatformQueryAction.get_info, platform_name="XCP")
            )

        assert isinstance(result, ErrorEnvelope)
        assert "error_code" in result


# ── platform_manage: add ──────────────────────────────────────────────────────


class TestPlatformManageAdd:
    @pytest.mark.asyncio
    async def test_returns_added_true_on_success(self) -> None:
        expected = PlatformAddResult(added=True, platform_name="XCP", platform_type="XCPonCAN")
        with _patch_svc("add_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.add, platform_type=PlatformType.XCPonCAN
                )
            )

        assert isinstance(result, PlatformAddResult)
        assert result["added"] is True
        assert result["platform_type"] == "XCPonCAN"

    @pytest.mark.asyncio
    async def test_can_monitoring_type_succeeds(self) -> None:
        expected = PlatformAddResult(
            added=True, platform_name="CAN_1", platform_type="CANMonitoring"
        )
        with _patch_svc("add_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.add, platform_type=PlatformType.CANMonitoring
                )
            )

        assert isinstance(result, PlatformAddResult)
        assert result["added"] is True
        assert result["platform_type"] == "CANMonitoring"

    @pytest.mark.asyncio
    async def test_diagnostic2_type_succeeds(self) -> None:
        expected = PlatformAddResult(
            added=True, platform_name="Diag_1", platform_type="Diagnostic2"
        )
        with _patch_svc("add_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.add, platform_type=PlatformType.Diagnostic2
                )
            )

        assert isinstance(result, PlatformAddResult)
        assert result["added"] is True

    @pytest.mark.asyncio
    async def test_missing_platform_type_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(action=PlatformManageAction.add, platform_type=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("add_platform", return_value=_ERROR):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.add, platform_type=PlatformType.XCPonCAN
                )
            )

        assert isinstance(result, ErrorEnvelope)
        assert "error_code" in result


# ── platform_manage: activate_registered ─────────────────────────────────────


class TestPlatformManageActivateRegistered:
    @pytest.mark.asyncio
    async def test_returns_added_true_on_success(self) -> None:
        expected = PlatformAddRegisteredResult(added=True, unique_name="SCALEXIO_192.168.140.110")
        with _patch_svc("add_registered_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.activate_registered,
                    unique_name="SCALEXIO_192.168.140.110",
                )
            )

        assert isinstance(result, PlatformAddRegisteredResult)
        assert result["added"] is True
        assert result["unique_name"] == "SCALEXIO_192.168.140.110"

    @pytest.mark.asyncio
    async def test_missing_unique_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(action=PlatformManageAction.activate_registered, unique_name=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_admin_manage ─────────────────────────────────────────────────────


class TestPlatformAdminManage:
    @pytest.mark.asyncio
    async def test_remove_returns_removed_true_on_success(self) -> None:
        expected = PlatformRemoveResult(platform_name="XCP", removed=True)
        with _patch_svc("remove_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_admin_manage

            result = await platform_admin_manage(
                PlatformAdminManageInput(
                    action=PlatformAdminManageAction.remove, platform_name="XCP"
                )
            )

        assert isinstance(result, PlatformRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_admin_manage

        result = await platform_admin_manage(
            PlatformAdminManageInput(action=PlatformAdminManageAction.remove, platform_name=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename_returns_renamed_true_on_success(self) -> None:
        expected = PlatformRenameResult(
            renamed=True, platform_name="XCP", new_name="XCP_CalDemo", timestamp_utc=_TS
        )
        with _patch_svc("rename_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_admin_manage

            result = await platform_admin_manage(
                PlatformAdminManageInput(
                    action=PlatformAdminManageAction.rename,
                    platform_name="XCP",
                    new_name="XCP_CalDemo",
                )
            )

        assert isinstance(result, PlatformRenameResult)
        assert result["renamed"] is True
        assert result["platform_name"] == "XCP"
        assert result["new_name"] == "XCP_CalDemo"

    @pytest.mark.asyncio
    async def test_rename_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_admin_manage

        result = await platform_admin_manage(
            PlatformAdminManageInput(
                action=PlatformAdminManageAction.rename,
                platform_name=None,
                new_name="XCP_CalDemo",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename_missing_new_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_admin_manage

        result = await platform_admin_manage(
            PlatformAdminManageInput(
                action=PlatformAdminManageAction.rename,
                platform_name="XCP",
                new_name=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_set_enabled_true_on_success(self) -> None:
        expected = PlatformSetEnabledResult(configured=True, platform_name="XCP", enabled=True)
        with _patch_svc("set_platform_enabled", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_admin_manage

            result = await platform_admin_manage(
                PlatformAdminManageInput(
                    action=PlatformAdminManageAction.set_enabled,
                    platform_name="XCP",
                    enabled=True,
                )
            )

        assert isinstance(result, PlatformSetEnabledResult)
        assert result["enabled"] is True

    @pytest.mark.asyncio
    async def test_set_enabled_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_admin_manage

        result = await platform_admin_manage(
            PlatformAdminManageInput(
                action=PlatformAdminManageAction.set_enabled,
                platform_name=None,
                enabled=True,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_set_enabled_missing_enabled_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_admin_manage

        result = await platform_admin_manage(
            PlatformAdminManageInput(
                action=PlatformAdminManageAction.set_enabled,
                platform_name="XCP",
                enabled=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_manage: add_variable_description ─────────────────────────────────


class TestPlatformManageAddVariableDescription:
    @pytest.mark.asyncio
    async def test_returns_added_true_on_success(self) -> None:
        expected = PlatformAddVariableDescriptionResult(
            added=True,
            platform_name="XCP",
            variable_description_name="ecu",
            file_path="C:\\ecu.a2l",
        )
        with _patch_svc("add_variable_description", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.add_variable_description,
                    platform_name="XCP",
                    file_path="C:\\ecu.a2l",
                )
            )

        assert isinstance(result, PlatformAddVariableDescriptionResult)
        assert result["added"] is True
        assert result["variable_description_name"] == "ecu"

    @pytest.mark.asyncio
    async def test_missing_file_path_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(
                action=PlatformManageAction.add_variable_description,
                platform_name="XCP",
                file_path=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_manage: configure_calibration_behavior ──────────────────────────


class TestPlatformManageConfigureCalibrationBehavior:
    @pytest.mark.asyncio
    async def test_returns_configured_true_on_success(self) -> None:
        expected = PlatformConfigureCalibrationBehaviorResult(
            configured=True,
            platform_name="XCP",
            calibration_behavior="UploadConnectedVariables",
            initial_page="WorkingPage",
        )
        with _patch_svc("configure_calibration_behavior", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.configure_calibration_behavior,
                    platform_name="XCP",
                    calibration_behavior="UploadConnectedVariables",
                    initial_page=InitialPageType.WorkingPage,
                )
            )

        assert isinstance(result, PlatformConfigureCalibrationBehaviorResult)
        assert result["configured"] is True
        assert result["calibration_behavior"] == "UploadConnectedVariables"

    @pytest.mark.asyncio
    async def test_missing_params_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(
                action=PlatformManageAction.configure_calibration_behavior,
                platform_name="XCP",
                calibration_behavior=None,
                initial_page=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_manage: set_api_version ─────────────────────────────────────────


class TestPlatformManageSetApiVersion:
    @pytest.mark.asyncio
    async def test_returns_configured_true_on_success(self) -> None:
        expected = PlatformSetApiVersionResult(
            version_string="APIVersion2", version_integer=2, configured=True
        )
        with _patch_svc("set_api_version", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.set_api_version,
                    version=AutomationAPIVersion.APIVersion2,
                )
            )

        assert isinstance(result, PlatformSetApiVersionResult)
        assert result["configured"] is True
        assert result["version_string"] == "APIVersion2"
        assert result["version_integer"] == 2

    @pytest.mark.asyncio
    async def test_missing_version_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(action=PlatformManageAction.set_api_version, version=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_manage: configure_transport ─────────────────────────────────────


class TestPlatformManageConfigureTransport:
    @pytest.mark.asyncio
    async def test_can_baud_rate_returns_configured(self) -> None:
        expected = PlatformConfigureTransportResult(
            configured=True, platform_name="XCP", baud_rate=500000
        )
        with _patch_svc("configure_transport", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.configure_transport,
                    platform_name="XCP",
                    baud_rate=500000,
                )
            )

        assert isinstance(result, PlatformConfigureTransportResult)
        assert result["configured"] is True
        assert result["baud_rate"] == 500000

    @pytest.mark.asyncio
    async def test_ethernet_automatic_adapter_returns_configured(self) -> None:
        expected = PlatformConfigureTransportResult(
            configured=True,
            platform_name="XCPonEth",
            ethernet_protocol="TCP",
            automatic_adapter=True,
        )
        with _patch_svc("configure_transport", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.configure_transport,
                    platform_name="XCPonEth",
                    ethernet_protocol=EthernetProtocol.TCP,
                    automatic_adapter=True,
                )
            )

        assert isinstance(result, PlatformConfigureTransportResult)
        assert result["configured"] is True
        assert result["automatic_adapter"] is True

    @pytest.mark.asyncio
    async def test_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(action=PlatformManageAction.configure_transport, platform_name=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_manage: list_interfaces ─────────────────────────────────────────


class TestPlatformManageListInterfaces:
    @pytest.mark.asyncio
    async def test_returns_interfaces_on_success(self) -> None:
        expected = PlatformListInterfacesResult(
            interfaces=[
                {
                    "vendor_name": "dSPACE",
                    "interface_name": "Virtual",
                    "channel_count": 1,
                }
            ],
            total_count=1,
        )
        with _patch_svc("list_interfaces", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(action=PlatformQueryAction.list_interfaces, platform_name="XCP")
            )

        assert isinstance(result, PlatformListInterfacesResult)
        assert result["total_count"] == 1
        assert len(result["interfaces"]) == 1
        assert result["interfaces"][0]["vendor_name"] == "dSPACE"

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("list_interfaces", return_value=_ERROR):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(action=PlatformQueryAction.list_interfaces, platform_name="XCP")
            )

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_query

        result = await platform_query(
            PlatformQueryInput(action=PlatformQueryAction.list_interfaces, platform_name=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_manage: select_interface_manual ─────────────────────────────────


class TestPlatformManageSelectInterfaceManual:
    @pytest.mark.asyncio
    async def test_returns_selected_true_on_success(self) -> None:
        expected = PlatformSelectInterfaceManualResult(
            selected=True,
            platform_name="XCP",
            interface_name="Virtual",
        )
        with _patch_svc("select_interface_manual", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.select_interface_manual,
                    platform_name="XCP",
                    vendor_name="dSPACE",
                    interface_name="Virtual",
                    channel_index=0,
                )
            )

        assert isinstance(result, PlatformSelectInterfaceManualResult)
        assert result["selected"] is True
        assert result["interface_name"] == "Virtual"

    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(
                action=PlatformManageAction.select_interface_manual,
                platform_name="XCP",
                vendor_name=None,
                interface_name=None,
                channel_index=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_manage: get_connection_state ────────────────────────────────────


class TestPlatformManageGetConnectionState:
    @pytest.mark.asyncio
    async def test_returns_connected_state(self) -> None:
        expected = PlatformGetConnectionStateResult(
            platform_name="XCP",
            connection_state="Connected",
            is_connected=True,
            timestamp_utc=_TS,
        )
        with _patch_svc("get_connection_state", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(
                    action=PlatformQueryAction.get_connection_state, platform_name="XCP"
                )
            )

        assert isinstance(result, PlatformGetConnectionStateResult)
        assert result["is_connected"] is True
        assert result["connection_state"] == "Connected"

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("get_connection_state", return_value=_ERROR):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(
                    action=PlatformQueryAction.get_connection_state, platform_name="XCP"
                )
            )

        assert isinstance(result, ErrorEnvelope)
        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_query

        result = await platform_query(
            PlatformQueryInput(action=PlatformQueryAction.get_connection_state, platform_name=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── platform_connect ──────────────────────────────────────────────────────────


class TestPlatformConnect:
    @pytest.mark.asyncio
    async def test_returns_connected_true_on_success(self) -> None:
        expected = PlatformConnectResult(
            connected=True,
            platform_name="XCP",
            connection_state="Connected",
            timestamp_utc=_TS,
        )
        with _patch_svc("connect_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_connect

            result = await platform_connect(PlatformConnectInput(platform_name="XCP"))

        assert isinstance(result, PlatformConnectResult)
        assert result["connected"] is True
        assert result["connection_state"] == "Connected"

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("connect_platform", return_value=_ERROR):
            from controldesk_mcp.tools.platform.management import platform_connect

            result = await platform_connect(PlatformConnectInput(platform_name="XCP"))

        assert isinstance(result, ErrorEnvelope)
        assert "error_code" in result


# ── platform_disconnect ───────────────────────────────────────────────────────


class TestPlatformDisconnect:
    @pytest.mark.asyncio
    async def test_returns_disconnected_true_on_success(self) -> None:
        expected = PlatformDisconnectResult(
            disconnected=True,
            platform_name="XCP",
            connection_state="Disconnected",
            timestamp_utc=_TS,
        )
        with _patch_svc("disconnect_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_disconnect

            result = await platform_disconnect(PlatformDisconnectInput(platform_name="XCP"))

        assert isinstance(result, PlatformDisconnectResult)
        assert result["disconnected"] is True
        assert result["connection_state"] == "Disconnected"


# ── platform_hardware_manage ──────────────────────────────────────────────────


class TestPlatformHardwareManage:
    @pytest.mark.asyncio
    async def test_register_hardware_returns_registered_true(self) -> None:
        expected = PlatformRegisterHardwareResult(
            registered=True,
            unique_name="SCALEXIO_192.168.140.110",
            display_name="SCALEXIO (192.168.140.110)",
            platform_type="SCALEXIO",
            ip_address="192.168.140.110",
        )
        with _patch_svc("register_hardware_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.register_hardware,
                    platform_type=PlatformType.SCALEXIO,
                    ip_address="192.168.140.110",
                )
            )

        assert isinstance(result, PlatformRegisterHardwareResult)
        assert result["registered"] is True
        assert result["unique_name"] == "SCALEXIO_192.168.140.110"

    @pytest.mark.asyncio
    async def test_register_hardware_missing_type_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_hardware_manage

        result = await platform_hardware_manage(
            PlatformHardwareManageInput(
                action=PlatformHardwareManageAction.register_hardware,
                platform_type=None,
                ip_address="192.168.140.110",
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_register_hardware_missing_ip_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_hardware_manage

        result = await platform_hardware_manage(
            PlatformHardwareManageInput(
                action=PlatformHardwareManageAction.register_hardware,
                platform_type=PlatformType.MABX,
                ip_address=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_clear_registered_confirm_false_aborted(self) -> None:
        expected = PlatformClearRegisteredAborted()
        with _patch_svc("clear_registered_platforms", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.clear_registered,
                    confirm=False,
                )
            )

        assert isinstance(result, PlatformClearRegisteredAborted)
        assert result["cleared"] is False

    @pytest.mark.asyncio
    async def test_clear_registered_confirm_true_clears(self) -> None:
        expected = PlatformClearRegisteredResult(
            cleared=True, force_driver_reset=False, message="All registered platforms cleared."
        )
        with _patch_svc("clear_registered_platforms", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.clear_registered,
                    confirm=True,
                )
            )

        assert isinstance(result, PlatformClearRegisteredResult)
        assert result["cleared"] is True

    @pytest.mark.asyncio
    async def test_clear_registered_missing_confirm_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_hardware_manage

        result = await platform_hardware_manage(
            PlatformHardwareManageInput(
                action=PlatformHardwareManageAction.clear_registered,
                confirm=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_registered_hardware_returns_result(self) -> None:
        expected = PlatformListRegisteredHardwareResult(
            registered_platforms=[{"unique_name": "SCALEXIO_192.168.140.110", "index": 0}],
            count=1,
        )
        with _patch_svc("list_registered_hardware", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.list_registered_hardware
                )
            )

        assert isinstance(result, PlatformListRegisteredHardwareResult)
        assert len(result["registered_platforms"]) == 1

    @pytest.mark.asyncio
    async def test_get_registered_info_returns_result(self) -> None:
        expected = PlatformGetRegisteredInfoResult(index=0, unique_name="SCALEXIO_192.168.140.110")
        with _patch_svc("get_registered_info", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.get_registered_info,
                    index=0,
                )
            )

        assert isinstance(result, PlatformGetRegisteredInfoResult)
        assert result["index"] == 0
        assert result["unique_name"] == "SCALEXIO_192.168.140.110"

    @pytest.mark.asyncio
    async def test_get_registered_info_missing_index_returns_error(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_hardware_manage

        result = await platform_hardware_manage(
            PlatformHardwareManageInput(
                action=PlatformHardwareManageAction.get_registered_info,
                index=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_refresh_configuration_returns_result(self) -> None:
        expected = PlatformRefreshConfigurationResult(
            refreshed=True, operation="refresh_configuration"
        )
        with _patch_svc("refresh_platform_configuration", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.refresh_configuration
                )
            )

        assert isinstance(result, PlatformRefreshConfigurationResult)
        assert result["refreshed"] is True

    @pytest.mark.asyncio
    async def test_refresh_interface_connections_returns_result(self) -> None:
        expected = PlatformRefreshInterfaceConnectionsResult(
            refreshed=True,
            operation="refresh_interface_connections",
            force_driver_reset=True,
        )
        with _patch_svc("refresh_interface_connections", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.refresh_interface_connections
                )
            )

        assert isinstance(result, PlatformRefreshInterfaceConnectionsResult)
        assert result["refreshed"] is True
        assert result["force_driver_reset"] is True


# ── platform_discover ─────────────────────────────────────────────────────────


class TestPlatformDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_discover

        result = await platform_discover(AsyncMock())

        assert isinstance(result, PlatformDiscoverResult)
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_discover_has_two_tools(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_discover

        result = await platform_discover(AsyncMock())

        assert len(result["tools"]) == 3

    @pytest.mark.asyncio
    async def test_discover_has_admin_manage_tool(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_discover

        result = await platform_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "platform_admin_manage" in tool_names

    @pytest.mark.asyncio
    async def test_discover_admin_manage_actions(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_discover

        result = await platform_discover(AsyncMock())

        admin_tool = next(t for t in result["tools"] if t["tool_name"] == "platform_admin_manage")
        assert "remove" in admin_tool["actions"]
        assert "rename" in admin_tool["actions"]
        assert "set_enabled" in admin_tool["actions"]

    @pytest.mark.asyncio
    async def test_discover_has_hardware_manage_tool(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_discover

        result = await platform_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "platform_hardware_manage" in tool_names

    @pytest.mark.asyncio
    async def test_discover_hardware_manage_actions(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_discover

        result = await platform_discover(AsyncMock())

        hw_tool = next(t for t in result["tools"] if t["tool_name"] == "platform_hardware_manage")
        assert "register_hardware" in hw_tool["actions"]
        assert "clear_registered" in hw_tool["actions"]
        assert "list_registered_hardware" in hw_tool["actions"]
        assert "get_registered_info" in hw_tool["actions"]
        assert "refresh_configuration" in hw_tool["actions"]
        assert "refresh_interface_connections" in hw_tool["actions"]


# ── Input model tests ─────────────────────────────────────────────────────────


class TestPlatformInputModels:
    def test_manage_input_defaults(self) -> None:
        params = PlatformQueryInput(action=PlatformQueryAction.list)
        assert params.offset == 0
        assert params.limit == 200

    def test_hardware_manage_input_defaults(self) -> None:
        params = PlatformHardwareManageInput(
            action=PlatformHardwareManageAction.list_registered_hardware
        )
        assert params.offset == 0
        assert params.limit == 200
        assert params.force_driver_reset is True
