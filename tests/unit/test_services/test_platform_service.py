"""Unit tests for controldesk_mcp.services.platform_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeConnectionError, BridgeOperationError
from controldesk_mcp.models.platform import PlatformAddInput, PlatformGetInfoInput, PlatformType

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_bridge():
    bridge._connection = None
    import controldesk_mcp.com_bridge.sta_thread as _sta

    _sta._sta_thread = None
    yield
    bridge._connection = None
    _sta._sta_thread = None


def _make_connected_bridge() -> MagicMock:
    from controldesk_mcp.com_bridge.connection import ConnectionState

    conn = MagicMock()
    conn.state = ConnectionState.CONNECTED
    conn.get_app.return_value = MagicMock()
    bridge._connection = conn
    return conn


# ── list_platforms ────────────────────────────────────────────────────────────


class TestListPlatforms:
    @pytest.mark.asyncio
    async def test_returns_platforms_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, [{"name": "MyCAN"}]],
        ):
            from controldesk_mcp.services.platform_service import list_platforms

            result = await list_platforms()

        assert result["count"] == 1
        assert result["platforms"][0]["name"] == "MyCAN"

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("disconnected"),
        ):
            from controldesk_mcp.services.platform_service import list_platforms

            result = await list_platforms()

        assert "error_code" in result


# ── get_platform_info ─────────────────────────────────────────────────────────


class TestGetPlatformInfo:
    @pytest.mark.asyncio
    async def test_returns_info_dict(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        info = {
            "name": "MyCAN",
            "platform_type": "CANMonitoring",
            "type": "CANMonitoring",
            "connected": False,
            "connection_state": "Disconnected",
            "measurement_state": "NotMeasuring",
            "variable_description_count": 0,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, info],
        ):
            from controldesk_mcp.services.platform_service import get_platform_info

            result = await get_platform_info(PlatformGetInfoInput(platform_name="MyCAN"))

        assert result["name"] == "MyCAN"

    @pytest.mark.asyncio
    async def test_returns_error_on_operation_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("not found", error_code="BRIDGE_OPERATION"),
        ):
            from controldesk_mcp.services.platform_service import get_platform_info

            result = await get_platform_info(PlatformGetInfoInput(platform_name="Unknown"))

        assert "error_code" in result


# ── add_platform ──────────────────────────────────────────────────────────────


class TestAddPlatform:
    @pytest.mark.asyncio
    async def test_returns_add_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        add_result = {
            "name": "CANMonitoring_0",
            "platform_type": "CANMonitoring",
            "added": True,
            "platform_name": "CANMonitoring_0",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, add_result],
        ):
            from controldesk_mcp.services.platform_service import add_platform

            result = await add_platform(PlatformAddInput(platform_type=PlatformType.CANMonitoring))

        assert result["platform_type"] == "CANMonitoring"


# ── list_hardware_types ───────────────────────────────────────────────────────


class TestListHardwareTypes:
    @pytest.mark.asyncio
    async def test_returns_hardware_types_catalog(self) -> None:
        """Verify list_hardware_types returns static catalog with proper structure."""
        from controldesk_mcp.services.platform_service import list_hardware_types

        result = await list_hardware_types()

        # Verify structure
        assert "hardware_platforms" in result
        assert "ip_addressable" in result["hardware_platforms"]
        assert "direct_add" in result["hardware_platforms"]
        assert "total_hardware_types" in result
        assert result["total_hardware_types"] == 8

    @pytest.mark.asyncio
    async def test_ip_addressable_types_listed(self) -> None:
        """Verify IP-addressable types are in the catalog."""
        from controldesk_mcp.services.platform_service import list_hardware_types

        result = await list_hardware_types()
        ip_types = result["hardware_platforms"]["ip_addressable"]
        type_names = [t["type"] for t in ip_types]

        assert "SCALEXIO" in type_names
        assert "DS1202" in type_names
        assert "DS1203" in type_names
        assert "DS1403" in type_names
        assert "MABX" in type_names
        assert "VEOS" in type_names
        assert "XILAPIMAPort" in type_names

    @pytest.mark.asyncio
    async def test_direct_add_types_listed(self) -> None:
        """Verify direct-add types are in the catalog."""
        from controldesk_mcp.services.platform_service import list_hardware_types

        result = await list_hardware_types()
        direct_types = result["hardware_platforms"]["direct_add"]
        type_names = [t["type"] for t in direct_types]

        assert "DS1104" in type_names

    @pytest.mark.asyncio
    async def test_each_hardware_type_has_description(self) -> None:
        """Verify each hardware type entry has required fields."""
        from controldesk_mcp.services.platform_service import list_hardware_types

        result = await list_hardware_types()
        all_types = (
            result["hardware_platforms"]["ip_addressable"]
            + result["hardware_platforms"]["direct_add"]
        )

        for hw_type in all_types:
            assert "type" in hw_type
            assert "description" in hw_type
            assert "registration_method" in hw_type
            assert "typical_use" in hw_type
            assert isinstance(hw_type["type"], str)
            assert len(hw_type["description"]) > 0
            assert len(hw_type["registration_method"]) > 0
            assert len(hw_type["typical_use"]) > 0


class TestListRegisteredHardware:
    @pytest.mark.asyncio
    async def test_list_registered_hardware_success(self) -> None:
        """Verify list_registered_hardware returns registered platforms list."""
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        registered_data = {
            "registered_platforms": [
                {
                    "index": 0,
                    "name": "hw_1",
                    "unique_name": "hw_1_unique",
                    "type": "SCALEXIO",
                    "connection_state": "Connected",
                    "ip_address": "192.168.1.100",
                }
            ],
            "count": 1,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, registered_data],
        ):
            from controldesk_mcp.services.platform_service import list_registered_hardware

            result = await list_registered_hardware()

        assert result["count"] == 1
        assert result["registered_platforms"][0]["name"] == "hw_1"
        assert result["registered_platforms"][0]["ip_address"] == "192.168.1.100"

    @pytest.mark.asyncio
    async def test_list_registered_hardware_empty(self) -> None:
        """Verify list_registered_hardware returns empty list when no platforms registered."""
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[
                app_mock,
                {
                    "registered_platforms": [],
                    "count": 0,
                },
            ],
        ):
            from controldesk_mcp.services.platform_service import list_registered_hardware

            result = await list_registered_hardware()

        assert result["count"] == 0
        assert result["registered_platforms"] == []

    @pytest.mark.asyncio
    async def test_list_registered_hardware_bridge_error(self) -> None:
        """Verify list_registered_hardware handles BridgeError gracefully."""
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("COM connection failed", error_code="BRIDGE_ERROR"),
        ):
            from controldesk_mcp.services.platform_service import list_registered_hardware

            result = await list_registered_hardware()

        # Should return error envelope
        assert "error_code" in result
        assert result["error_code"] == "BRIDGE_ERROR"


class TestGetRegisteredInfo:
    @pytest.mark.asyncio
    async def test_get_registered_info_success(self) -> None:
        """Verify get_registered_info returns platform metadata by index."""
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        platform_data = {
            "index": 0,
            "name": "scalexio_1",
            "unique_name": "scalexio_1_unique",
            "type": "SCALEXIO",
            "connection_state": "Connected",
            "ip_address": "192.168.1.100",
            "board_name": "SCALEXIO_Board",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, platform_data],
        ):
            from controldesk_mcp.services.platform_service import get_registered_info

            result = await get_registered_info(0)

        assert result["name"] == "scalexio_1"
        assert result["ip_address"] == "192.168.1.100"
        assert result["board_name"] == "SCALEXIO_Board"

    @pytest.mark.asyncio
    async def test_get_registered_info_index_out_of_range(self) -> None:
        """Verify get_registered_info handles index out of range gracefully."""
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError(
                "Index not found", error_code="BRIDGE_INVALID_ARGUMENT"
            ),
        ):
            from controldesk_mcp.services.platform_service import get_registered_info

            result = await get_registered_info(99)

        # Should return error envelope
        assert "error_code" in result
        assert result["error_code"] == "BRIDGE_INVALID_ARGUMENT"

    @pytest.mark.asyncio
    async def test_get_registered_info_veos_platform(self) -> None:
        """Verify get_registered_info works for VEOS software platform."""
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        platform_data = {
            "index": 1,
            "name": "veos_sim",
            "unique_name": "veos_sim_unique",
            "type": "VEOS",
            "connection_state": "Disconnected",
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, platform_data],
        ):
            from controldesk_mcp.services.platform_service import get_registered_info

            result = await get_registered_info(1)

        assert result["name"] == "veos_sim"
        assert result["type"] == "VEOS"
        assert "ip_address" not in result  # VEOS has no IP address


# ── clear_registered_platforms (with force_driver_reset) ─────────────────────


class TestClearRegisteredPlatformsService:
    @pytest.mark.asyncio
    async def test_clear_with_confirm_and_force_false(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, None],
        ):
            from controldesk_mcp.models.platform import PlatformClearRegisteredInput
            from controldesk_mcp.services.platform_service import clear_registered_platforms

            params = PlatformClearRegisteredInput(confirm=True, force_driver_reset=False)
            result = await clear_registered_platforms(params)

        assert result["cleared"] is True
        assert result["force_driver_reset"] is False

    @pytest.mark.asyncio
    async def test_clear_with_confirm_and_force_true(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, None],
        ):
            from controldesk_mcp.models.platform import PlatformClearRegisteredInput
            from controldesk_mcp.services.platform_service import clear_registered_platforms

            params = PlatformClearRegisteredInput(confirm=True, force_driver_reset=True)
            result = await clear_registered_platforms(params)

        assert result["cleared"] is True
        assert result["force_driver_reset"] is True

    @pytest.mark.asyncio
    async def test_clear_aborted_when_confirm_false(self) -> None:
        _make_connected_bridge()

        with patch("controldesk_mcp.com_bridge.dispatch", new_callable=AsyncMock):
            from controldesk_mcp.models.platform import PlatformClearRegisteredInput
            from controldesk_mcp.services.platform_service import clear_registered_platforms

            params = PlatformClearRegisteredInput(confirm=False)
            result = await clear_registered_platforms(params)

        assert result["cleared"] is False


# ── refresh_platform_configuration ───────────────────────────────────────────


class TestRefreshPlatformConfigurationService:
    @pytest.mark.asyncio
    async def test_returns_refreshed_true(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        refresh_result = {"refreshed": True, "operation": "RefreshPlatformConfiguration"}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, refresh_result],
        ):
            from controldesk_mcp.models.platform import PlatformRefreshConfigurationInput
            from controldesk_mcp.services.platform_service import refresh_platform_configuration

            params = PlatformRefreshConfigurationInput()
            result = await refresh_platform_configuration(params)

        assert result["refreshed"] is True
        assert result["operation"] == "RefreshPlatformConfiguration"

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_failure(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("COM error"),
        ):
            from controldesk_mcp.models.platform import PlatformRefreshConfigurationInput
            from controldesk_mcp.services.platform_service import refresh_platform_configuration

            params = PlatformRefreshConfigurationInput()
            result = await refresh_platform_configuration(params)

        assert "error_code" in result


# ── refresh_interface_connections ─────────────────────────────────────────────


class TestRefreshInterfaceConnectionsService:
    @pytest.mark.asyncio
    async def test_returns_refreshed_true_with_force(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        refresh_result = {
            "refreshed": True,
            "operation": "RefreshInterfaceConnections",
            "force_driver_reset": True,
        }

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, refresh_result],
        ):
            from controldesk_mcp.models.platform import PlatformRefreshInterfaceConnectionsInput
            from controldesk_mcp.services.platform_service import refresh_interface_connections

            params = PlatformRefreshInterfaceConnectionsInput(force_driver_reset=True)
            result = await refresh_interface_connections(params)

        assert result["refreshed"] is True
        assert result["force_driver_reset"] is True

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_failure(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("COM error"),
        ):
            from controldesk_mcp.models.platform import PlatformRefreshInterfaceConnectionsInput
            from controldesk_mcp.services.platform_service import refresh_interface_connections

            params = PlatformRefreshInterfaceConnectionsInput()
            result = await refresh_interface_connections(params)

        assert "error_code" in result


# ── set_platform_enabled ──────────────────────────────────────────────────────


class TestSetPlatformEnabledService:
    @pytest.mark.asyncio
    async def test_enable_platform_returns_configured_true(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        enabled_result = {"configured": True, "platform_name": "XCP", "enabled": True}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, enabled_result],
        ):
            from controldesk_mcp.models.platform import PlatformSetEnabledInput
            from controldesk_mcp.services.platform_service import set_platform_enabled

            params = PlatformSetEnabledInput(platform_name="XCP", enabled=True)
            result = await set_platform_enabled(params)

        assert result["configured"] is True
        assert result["enabled"] is True
        assert result["platform_name"] == "XCP"

    @pytest.mark.asyncio
    async def test_disable_platform_returns_configured_true(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        disabled_result = {"configured": True, "platform_name": "XCP", "enabled": False}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, disabled_result],
        ):
            from controldesk_mcp.models.platform import PlatformSetEnabledInput
            from controldesk_mcp.services.platform_service import set_platform_enabled

            params = PlatformSetEnabledInput(platform_name="XCP", enabled=False)
            result = await set_platform_enabled(params)

        assert result["enabled"] is False

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_failure(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeOperationError("COM error"),
        ):
            from controldesk_mcp.models.platform import PlatformSetEnabledInput
            from controldesk_mcp.services.platform_service import set_platform_enabled

            params = PlatformSetEnabledInput(platform_name="XCP", enabled=True)
            result = await set_platform_enabled(params)

        assert "error_code" in result
