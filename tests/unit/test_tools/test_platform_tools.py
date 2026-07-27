"""Unit tests for platform MCP tools.

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.platform import (
    AutomationAPIVersion,
    InitialPageType,
    PlatformAddRegisteredResult,
    PlatformAddVariableDescriptionResult,
    PlatformAdminManageAction,
    PlatformAdminManageInput,
    PlatformClearRegisteredAborted,
    PlatformClearRegisteredResult,
    PlatformConfigureCalibrationBehaviorResult,
    PlatformConfigureResult,
    PlatformConfigureTransportResult,
    PlatformConnectResult,
    PlatformDisconnectResult,
    PlatformDiscoverResult,
    PlatformGetConnectionStateResult,
    PlatformGetInfoResult,
    PlatformGetRegisteredInfoResult,
    PlatformHardwareManageAction,
    PlatformHardwareManageInput,
    PlatformListHardwareTypesResult,
    PlatformListInterfacesResult,
    PlatformListRegisteredHardwareResult,
    PlatformListResult,
    PlatformListTypesResult,
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


class TestPlatformConnect:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = PlatformConnectResult(
            connected=True, platform_name="XCP", connection_state="Connected", timestamp_utc=_TS
        )
        with _patch_svc("connect_platform", return_value=expected):
            from controldesk_mcp.models.platform import PlatformConnectInput
            from controldesk_mcp.tools.platform.management import platform_connect

            result = await platform_connect(PlatformConnectInput(platform_name="XCP"))

        assert isinstance(result, PlatformConnectResult)
        assert result["connected"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("connect_platform", return_value=_ERROR):
            from controldesk_mcp.models.platform import PlatformConnectInput
            from controldesk_mcp.tools.platform.management import platform_connect

            result = await platform_connect(PlatformConnectInput(platform_name="XCP"))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


class TestPlatformDisconnect:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = PlatformDisconnectResult(
            disconnected=True,
            platform_name="XCP",
            connection_state="Disconnected",
            timestamp_utc=_TS,
        )
        with _patch_svc("disconnect_platform", return_value=expected):
            from controldesk_mcp.models.platform import PlatformDisconnectInput
            from controldesk_mcp.tools.platform.management import platform_disconnect

            result = await platform_disconnect(PlatformDisconnectInput(platform_name="XCP"))

        assert isinstance(result, PlatformDisconnectResult)
        assert result["disconnected"] is True


class TestPlatformManage:
    @pytest.mark.asyncio
    async def test_list(self) -> None:
        svc_result = PlatformListResult(platforms=[])
        with _patch_svc("list_platforms", return_value=svc_result):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(PlatformQueryInput(action=PlatformQueryAction.list))

        assert isinstance(result, PlatformListResult)

    @pytest.mark.asyncio
    async def test_list_returns_error(self) -> None:
        with _patch_svc("list_platforms", return_value=_ERROR):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(PlatformQueryInput(action=PlatformQueryAction.list))

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_get_info(self) -> None:
        expected = PlatformGetInfoResult(
            name="XCP",
            type="XCPonCAN",
            connection_state="Connected",
            measurement_state="NotMeasuring",
            variable_description_count=1,
        )
        with _patch_svc("get_platform_info", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(action=PlatformQueryAction.get_info, platform_name="XCP")
            )

        assert isinstance(result, PlatformGetInfoResult)
        assert result["name"] == "XCP"

    @pytest.mark.asyncio
    async def test_get_info_missing_platform_name(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_query

        result = await platform_query(PlatformQueryInput(action=PlatformQueryAction.get_info))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_get_connection_state(self) -> None:
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

    @pytest.mark.asyncio
    async def test_get_connection_state_missing_platform_name(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_query

        result = await platform_query(
            PlatformQueryInput(action=PlatformQueryAction.get_connection_state)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_add(self) -> None:
        from controldesk_mcp.models.platform import PlatformAddResult

        expected = PlatformAddResult(added=True, platform_name="XCP_1", platform_type="XCPonCAN")
        with _patch_svc("add_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.add, platform_type=PlatformType.XCPonCAN
                )
            )

        assert isinstance(result, PlatformAddResult)
        assert result["added"] is True

    @pytest.mark.asyncio
    async def test_add_missing_platform_type(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(PlatformManageInput(action=PlatformManageAction.add))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_activate_registered(self) -> None:
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

    @pytest.mark.asyncio
    async def test_activate_registered_missing_unique_name(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(action=PlatformManageAction.activate_registered)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_configure(self) -> None:
        expected = PlatformConfigureResult(configured=True, platform_name="XCP")
        with _patch_svc("configure_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.configure,
                    platform_name="XCP",
                    can_interface="Virtual",
                )
            )

        assert isinstance(result, PlatformConfigureResult)
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_configure_missing_platform_name(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(PlatformManageInput(action=PlatformManageAction.configure))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_configure_calibration_behavior(self) -> None:
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

    @pytest.mark.asyncio
    async def test_configure_calibration_behavior_missing_params(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(
                action=PlatformManageAction.configure_calibration_behavior, platform_name="XCP"
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_configure_transport(self) -> None:
        expected = PlatformConfigureTransportResult(configured=True, platform_name="XCP")
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

    @pytest.mark.asyncio
    async def test_configure_transport_missing_platform_name(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(action=PlatformManageAction.configure_transport)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_set_api_version(self) -> None:
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

    @pytest.mark.asyncio
    async def test_set_api_version_missing_version(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(action=PlatformManageAction.set_api_version)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_select_interface_manual(self) -> None:
        expected = PlatformSelectInterfaceManualResult(
            selected=True, platform_name="XCP", interface_name="Virtual"
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

    @pytest.mark.asyncio
    async def test_select_interface_manual_missing_params(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(
                action=PlatformManageAction.select_interface_manual, platform_name="XCP"
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_add_variable_description(self) -> None:
        expected = PlatformAddVariableDescriptionResult(
            added=True,
            platform_name="XCP",
            variable_description_name="myecu",
            file_path="C:\\ECU\\myecu.a2l",
        )
        with _patch_svc("add_variable_description", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_manage

            result = await platform_manage(
                PlatformManageInput(
                    action=PlatformManageAction.add_variable_description,
                    platform_name="XCP",
                    file_path="C:\\ECU\\myecu.a2l",
                )
            )

        assert isinstance(result, PlatformAddVariableDescriptionResult)
        assert result["added"] is True

    @pytest.mark.asyncio
    async def test_add_variable_description_missing_params(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_manage

        result = await platform_manage(
            PlatformManageInput(
                action=PlatformManageAction.add_variable_description, platform_name="XCP"
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_interfaces(self) -> None:
        expected = PlatformListInterfacesResult(interfaces=[], total_count=0)
        with _patch_svc("list_interfaces", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(action=PlatformQueryAction.list_interfaces, platform_name="XCP")
            )

        assert isinstance(result, PlatformListInterfacesResult)

    @pytest.mark.asyncio
    async def test_list_interfaces_missing_platform_name(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_query

        result = await platform_query(
            PlatformQueryInput(action=PlatformQueryAction.list_interfaces)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_types(self) -> None:
        expected = PlatformListTypesResult(
            categories=[
                {"category": "Hardware", "types": [{"name": "SCALEXIO", "integer_value": 1}]}
            ],
            usage_note="Use platform_add for direct-add types.",
        )
        with _patch_svc("list_platform_types", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(PlatformQueryInput(action=PlatformQueryAction.list_types))

        assert isinstance(result, PlatformListTypesResult)
        assert len(result["categories"]) == 1

    @pytest.mark.asyncio
    async def test_list_hardware_types(self) -> None:
        expected = PlatformListHardwareTypesResult(hardware_types=[], total_count=0)
        with _patch_svc("list_hardware_types", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_query

            result = await platform_query(
                PlatformQueryInput(action=PlatformQueryAction.list_hardware_types)
            )

        assert isinstance(result, PlatformListHardwareTypesResult)


class TestPlatformHardwareManage:
    @pytest.mark.asyncio
    async def test_register_hardware(self) -> None:
        expected = PlatformRegisterHardwareResult(
            registered=True,
            unique_name="SCALEXIO_192.168.140.110",
            display_name="SCALEXIO",
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

    @pytest.mark.asyncio
    async def test_register_hardware_missing_params(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_hardware_manage

        result = await platform_hardware_manage(
            PlatformHardwareManageInput(
                action=PlatformHardwareManageAction.register_hardware,
                platform_type=PlatformType.SCALEXIO,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_clear_registered(self) -> None:
        expected = PlatformClearRegisteredResult(
            cleared=True, force_driver_reset=False, message="All cleared"
        )
        with _patch_svc("clear_registered_platforms", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.clear_registered, confirm=True
                )
            )

        assert isinstance(result, PlatformClearRegisteredResult)
        assert result["cleared"] is True

    @pytest.mark.asyncio
    async def test_clear_registered_aborted(self) -> None:
        expected = PlatformClearRegisteredAborted()
        with _patch_svc("clear_registered_platforms", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.clear_registered, confirm=False
                )
            )

        assert isinstance(result, PlatformClearRegisteredAborted)
        assert result["cleared"] is False

    @pytest.mark.asyncio
    async def test_clear_registered_missing_confirm(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_hardware_manage

        result = await platform_hardware_manage(
            PlatformHardwareManageInput(action=PlatformHardwareManageAction.clear_registered)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_registered_hardware(self) -> None:
        svc_result = PlatformListRegisteredHardwareResult(registered_platforms=[], count=0)
        with _patch_svc("list_registered_hardware", return_value=svc_result):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.list_registered_hardware
                )
            )

        assert isinstance(result, PlatformListRegisteredHardwareResult)

    @pytest.mark.asyncio
    async def test_list_registered_hardware_returns_error(self) -> None:
        with _patch_svc("list_registered_hardware", return_value=_ERROR):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.list_registered_hardware
                )
            )

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_get_registered_info(self) -> None:
        expected = PlatformGetRegisteredInfoResult(index=0, unique_name="SCALEXIO_192.168.140.110")
        with _patch_svc("get_registered_info", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_hardware_manage

            result = await platform_hardware_manage(
                PlatformHardwareManageInput(
                    action=PlatformHardwareManageAction.get_registered_info, index=0
                )
            )

        assert isinstance(result, PlatformGetRegisteredInfoResult)
        assert result["index"] == 0

    @pytest.mark.asyncio
    async def test_get_registered_info_missing_index(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_hardware_manage

        result = await platform_hardware_manage(
            PlatformHardwareManageInput(action=PlatformHardwareManageAction.get_registered_info)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_refresh_configuration(self) -> None:
        expected = PlatformRefreshConfigurationResult(
            refreshed=True, operation="RefreshPlatformConfiguration"
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
    async def test_refresh_interface_connections(self) -> None:
        expected = PlatformRefreshInterfaceConnectionsResult(
            refreshed=True, operation="RefreshInterfaceConnections", force_driver_reset=True
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


class TestPlatformAdminManage:
    @pytest.mark.asyncio
    async def test_remove(self) -> None:
        expected = PlatformRemoveResult(removed=True, platform_name="XCP")
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
    async def test_remove_missing_platform_name(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_admin_manage

        result = await platform_admin_manage(
            PlatformAdminManageInput(action=PlatformAdminManageAction.remove)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename(self) -> None:
        expected = PlatformRenameResult(
            renamed=True, platform_name="XCP", new_name="XCP_Renamed", timestamp_utc=_TS
        )
        with _patch_svc("rename_platform", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_admin_manage

            result = await platform_admin_manage(
                PlatformAdminManageInput(
                    action=PlatformAdminManageAction.rename,
                    platform_name="XCP",
                    new_name="XCP_Renamed",
                )
            )

        assert isinstance(result, PlatformRenameResult)
        assert result["renamed"] is True

    @pytest.mark.asyncio
    async def test_rename_missing_params(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_admin_manage

        result = await platform_admin_manage(
            PlatformAdminManageInput(action=PlatformAdminManageAction.rename, platform_name="XCP")
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_set_enabled(self) -> None:
        expected = PlatformSetEnabledResult(configured=True, platform_name="XCP", enabled=False)
        with _patch_svc("set_platform_enabled", return_value=expected):
            from controldesk_mcp.tools.platform.management import platform_admin_manage

            result = await platform_admin_manage(
                PlatformAdminManageInput(
                    action=PlatformAdminManageAction.set_enabled,
                    platform_name="XCP",
                    enabled=False,
                )
            )

        assert isinstance(result, PlatformSetEnabledResult)
        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_set_enabled_missing_params(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_admin_manage

        result = await platform_admin_manage(
            PlatformAdminManageInput(
                action=PlatformAdminManageAction.set_enabled, platform_name="XCP"
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


class TestPlatformDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_discover

        result = await platform_discover(AsyncMock())

        assert isinstance(result, PlatformDiscoverResult)
        assert result["status"] == "ok"
        assert len(result["tools"]) == 3

    @pytest.mark.asyncio
    async def test_hardware_manage_has_all_actions(self) -> None:
        from controldesk_mcp.tools.platform.management import platform_discover

        result = await platform_discover(AsyncMock())

        hw_tool = next(t for t in result["tools"] if t["tool_name"] == "platform_hardware_manage")
        actions = hw_tool["actions"]
        assert "register_hardware" in actions
        assert "clear_registered" in actions
        assert "list_registered_hardware" in actions
        assert "get_registered_info" in actions
        assert "refresh_configuration" in actions
        assert "refresh_interface_connections" in actions


class TestPlatformInputModels:
    def test_manage_input_instantiates(self) -> None:
        assert PlatformQueryInput(action=PlatformQueryAction.list) is not None
        assert (
            PlatformHardwareManageInput(action=PlatformHardwareManageAction.refresh_configuration)
            is not None
        )
