"""Unit tests for controldesk_mcp.com_bridge.domains.platform_com."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

from controldesk_mcp.com_bridge.domains.platform_com import (
    add_platform,
    add_registered_platform,
    add_variable_description,
    clear_registered_platforms,
    configure_calibration_behavior,
    configure_platform,
    configure_transport,
    connect_platform,
    disconnect_platform,
    get_connection_state,
    get_platform_info,
    get_registered_info,
    list_interfaces,
    list_platform_types,
    list_platforms,
    list_registered_hardware,
    refresh_interface_connections,
    refresh_platform_configuration,
    register_hardware_platform,
    remove_platform,
    rename_platform,
    select_interface_manual,
    set_api_version,
    set_platform_enabled,
)
from controldesk_mcp.com_bridge.errors import BridgeError, BridgePreconditionError

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_platform(
    name: str = "XCP",
    plat_type: str = "XCPonCAN",
    connection_state: str = "Disconnected",
    measurement_state: str = "Stopped",
    vd_count: int = 0,
) -> MagicMock:
    """Return a mock IXaExperimentPlatform.

    plat_type is the *name* string (e.g. "XCPonCAN").  The mock's .Type property
    returns the corresponding integer value (as COM would), so the code under test
    can call int(plat.Type) and look it up in _PLATFORM_TYPE_NAME.
    """
    from controldesk_mcp.com_bridge.domains.platform_com import _PLATFORM_TYPE_INT

    plat = MagicMock()
    type(plat).Name = PropertyMock(return_value=name)
    type_int = _PLATFORM_TYPE_INT.get(plat_type, 0)
    type(plat).Type = PropertyMock(return_value=type_int)
    type(plat).ConnectionState = PropertyMock(return_value=connection_state)
    type(plat).MeasurementState = PropertyMock(return_value=measurement_state)
    plat.VariableDescriptions = MagicMock()
    type(plat.VariableDescriptions).Count = PropertyMock(return_value=vd_count)
    return plat


def _make_app(platforms: list[MagicMock] | None = None) -> MagicMock:
    """Return a mock IXaApplication with an active experiment."""
    app = MagicMock()
    exp = MagicMock()
    plats_col = MagicMock()
    plats_list = platforms or []
    type(plats_col).Count = PropertyMock(return_value=len(plats_list))

    def _item(key):
        if isinstance(key, int):
            return plats_list[key]
        for p in plats_list:
            if str(p.Name) == str(key):
                return p
        raise Exception(f"Platform '{key}' not found")

    plats_col.Item.side_effect = _item
    exp.Platforms = plats_col
    app.ActiveExperiment = exp
    return app


def _make_no_experiment_app() -> MagicMock:
    """Return a mock IXaApplication with no active experiment."""
    app = MagicMock()
    app.ActiveExperiment = None
    return app


# ── list_platforms ────────────────────────────────────────────────────────────


class TestListPlatforms:
    def test_returns_empty_list_when_no_platforms(self) -> None:
        app = _make_app(platforms=[])
        result = list_platforms(app)
        assert result == []

    def test_returns_platform_info(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN", vd_count=1)
        app = _make_app(platforms=[plat])
        result = list_platforms(app)
        assert len(result) == 1
        assert result[0]["name"] == "XCP"
        assert result[0]["type"] == "XCPonCAN"
        assert result[0]["connection_state"] == "Disconnected"
        assert result[0]["variable_description_count"] == 1

    def test_raises_precondition_when_no_experiment(self) -> None:
        app = _make_no_experiment_app()
        with pytest.raises(BridgePreconditionError):
            list_platforms(app)

    def test_returns_multiple_platforms(self) -> None:
        p1 = _make_platform(name="XCP", plat_type="XCPonCAN")
        p2 = _make_platform(name="SCALEXIO_1", plat_type="SCALEXIO")
        app = _make_app(platforms=[p1, p2])
        result = list_platforms(app)
        assert len(result) == 2
        names = [r["name"] for r in result]
        assert "XCP" in names
        assert "SCALEXIO_1" in names

    def test_variable_descriptions_count_failure_returns_zero(self) -> None:
        """VariableDescriptions.Count throws on bus device types — must not crash list."""
        plat = _make_platform(name="CAN_1", plat_type="CANMonitoring")
        type(plat.VariableDescriptions).Count = PropertyMock(
            side_effect=Exception("Value does not fall within the expected range.")
        )
        app = _make_app(platforms=[plat])
        result = list_platforms(app)
        assert len(result) == 1
        assert result[0]["name"] == "CAN_1"
        assert result[0]["variable_description_count"] == 0

    def test_measurement_state_failure_returns_unknown(self) -> None:
        """MeasurementState may not exist on all platform types — must not crash list."""
        plat = _make_platform(name="Diag", plat_type="Diagnostic2")
        type(plat).MeasurementState = PropertyMock(side_effect=Exception("Property not supported"))
        app = _make_app(platforms=[plat])
        result = list_platforms(app)
        assert len(result) == 1
        assert result[0]["measurement_state"] == "Unknown"

    def test_mixed_types_all_listed(self) -> None:
        """Mixed XCP + bus device platforms all appear in the result."""
        xcp = _make_platform(name="XCP", plat_type="XCPonCAN", vd_count=1)
        can_mon = _make_platform(name="CAN_2", plat_type="CANMonitoring")
        type(can_mon.VariableDescriptions).Count = PropertyMock(side_effect=Exception("Not supported"))
        app = _make_app(platforms=[xcp, can_mon])
        result = list_platforms(app)
        assert len(result) == 2
        assert result[0]["variable_description_count"] == 1
        assert result[1]["variable_description_count"] == 0


# ── get_platform_info ─────────────────────────────────────────────────────────


class TestGetPlatformInfo:
    def test_returns_basic_info(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN", connection_state="Connected")
        app = _make_app(platforms=[plat])
        result = get_platform_info(app, "XCP")
        assert result["name"] == "XCP"
        assert result["type"] == "XCPonCAN"
        assert result["connection_state"] == "Connected"

    def test_raises_precondition_when_platform_not_found(self) -> None:
        app = _make_app(platforms=[])
        with pytest.raises(BridgePreconditionError):
            get_platform_info(app, "NonExistent")

    def test_raises_precondition_when_no_experiment(self) -> None:
        app = _make_no_experiment_app()
        with pytest.raises(BridgePreconditionError):
            get_platform_info(app, "XCP")


# ── add_platform ──────────────────────────────────────────────────────────────


class TestAddPlatform:
    def test_returns_added_true_on_success(self) -> None:
        app = _make_app()
        new_plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app.ActiveExperiment.Platforms.Add.return_value = new_plat
        result = add_platform(app, "XCPonCAN")
        assert result["added"] is True
        assert result["platform_name"] == "XCP"
        assert result["platform_type"] == "XCPonCAN"

    def test_bus_device_sets_automatic_assignment_on_add(self) -> None:
        """Adding a bus device type must set AutomaticAssignment=True immediately.

        Without this, platform_connect fails: 'Could not find any suitable CAN channel.'
        """
        app = _make_app()
        new_plat = _make_platform(name="CAN_1", plat_type="CANMonitoring")
        app.ActiveExperiment.Platforms.Add.return_value = new_plat
        result = add_platform(app, "CANMonitoring")
        assert result["added"] is True
        assert result["auto_assignment"] == "Automatic"
        # Verify the property was set to True on the COM object
        assert new_plat.InterfaceSelection.AutomaticAssignment is True

    def test_bus_device_auto_assignment_set_for_lin_monitoring(self) -> None:
        app = _make_app()
        new_plat = _make_platform(name="LIN_1", plat_type="LINMonitoring")
        app.ActiveExperiment.Platforms.Add.return_value = new_plat
        result = add_platform(app, "LINMonitoring")
        assert result["added"] is True
        assert result["auto_assignment"] == "Automatic"

    def test_non_bus_device_does_not_set_automatic_assignment(self) -> None:
        """XCPonCAN platforms must not get AutomaticAssignment set at add time."""
        app = _make_app()
        new_plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app.ActiveExperiment.Platforms.Add.return_value = new_plat
        result = add_platform(app, "XCPonCAN")
        assert result["added"] is True
        assert "auto_assignment" not in result

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = _make_app()
        app.ActiveExperiment.Platforms.Add.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            add_platform(app, "XCPonCAN")

    def test_raises_precondition_when_no_experiment(self) -> None:
        app = _make_no_experiment_app()
        with pytest.raises(BridgePreconditionError):
            add_platform(app, "XCPonCAN")


# ── add_registered_platform ───────────────────────────────────────────────────


class TestAddRegisteredPlatform:
    def test_returns_added_true_on_success(self) -> None:
        app = _make_app()
        result = add_registered_platform(app, "SCALEXIO_192.168.140.110")
        assert result["added"] is True
        assert result["unique_name"] == "SCALEXIO_192.168.140.110"

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = _make_app()
        app.ActiveExperiment.Platforms.AddExistingPlatform.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            add_registered_platform(app, "SCALEXIO_192.168.140.110")


# ── remove_platform ───────────────────────────────────────────────────────────


class TestRemovePlatform:
    def test_returns_removed_true_on_success(self) -> None:
        plat = _make_platform(name="XCP")
        app = _make_app(platforms=[plat])
        result = remove_platform(app, "XCP")
        assert result["removed"] is True
        assert result["platform_name"] == "XCP"
        # Correct COM call is Platforms.Remove(name), NOT plat.Remove()
        app.ActiveExperiment.Platforms.Remove.assert_called_once_with("XCP")

    def test_raises_bridge_error_on_com_failure(self) -> None:
        plat = _make_platform(name="XCP")
        app = _make_app(platforms=[plat])
        app.ActiveExperiment.Platforms.Remove.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            remove_platform(app, "XCP")

    def test_raises_precondition_when_platform_not_found(self) -> None:
        app = _make_app(platforms=[])
        with pytest.raises(BridgePreconditionError):
            remove_platform(app, "NonExistent")


# ── register_hardware_platform ────────────────────────────────────────────────


class TestRegisterHardwarePlatform:
    def test_raises_precondition_for_xcp_type(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError):
            register_hardware_platform(app, "XCPonCAN", "192.168.140.110")

    def test_raises_precondition_for_xcp_ethernet_type(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError):
            register_hardware_platform(app, "XCPonEthernet", "192.168.140.110")

    def test_raises_precondition_for_bus_device_type(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError):
            register_hardware_platform(app, "CANMonitoring", "192.168.140.110")

    def test_raises_precondition_for_ethernet_monitoring_type(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError):
            register_hardware_platform(app, "EthernetMonitoring", "192.168.140.110")

    def test_raises_precondition_for_diagnostic2_type(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError):
            register_hardware_platform(app, "Diagnostic2", "192.168.140.110")

    def test_raises_precondition_for_ds1104_type(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError):
            register_hardware_platform(app, "DS1104", "192.168.140.110")

    def test_scalexio_registration_success(self) -> None:
        app = MagicMock()
        reg_info = MagicMock()
        sub = MagicMock()
        reg_info.RegistrationInfos.Add.return_value = sub
        app.PlatformManagement.CreatePlatformRegistrationInfo.return_value = reg_info
        registered_platform = MagicMock()
        registered_platform.UniqueName = "SCALEXIO_192.168.140.110"
        registered_platform.DisplayName = "SCALEXIO at 192.168.140.110"
        app.PlatformManagement.RegisterPlatform.return_value = registered_platform
        result = register_hardware_platform(app, "SCALEXIO", "192.168.140.110")
        assert result["registered"] is True
        assert result["unique_name"] == "SCALEXIO_192.168.140.110"
        assert result["display_name"] == "SCALEXIO at 192.168.140.110"
        assert result["ip_address"] == "192.168.140.110"
        app.PlatformManagement.RegisterPlatform.assert_called_once_with(reg_info)

    def test_mabx_registration_uses_net_client(self) -> None:
        app = MagicMock()
        reg_info = MagicMock()
        registered_platform = MagicMock()
        registered_platform.UniqueName = "MABX_192.168.140.200"
        registered_platform.DisplayName = "MABX at 192.168.140.200"
        app.PlatformManagement.CreatePlatformRegistrationInfo.return_value = reg_info
        app.PlatformManagement.RegisterPlatform.return_value = registered_platform
        result = register_hardware_platform(app, "MABX", "192.168.140.200")
        assert result["registered"] is True
        assert reg_info.NetClient == "192.168.140.200"
        assert result["unique_name"] == "MABX_192.168.140.200"
        assert result["display_name"] == "MABX at 192.168.140.200"

    def test_veos_registration_uses_net_client(self) -> None:
        """VEOS uses NetClient registration path, same as MABX."""
        app = MagicMock()
        reg_info = MagicMock()
        registered_platform = MagicMock()
        registered_platform.UniqueName = "VEOS_192.168.140.150"
        registered_platform.DisplayName = "VEOS at 192.168.140.150"
        app.PlatformManagement.CreatePlatformRegistrationInfo.return_value = reg_info
        app.PlatformManagement.RegisterPlatform.return_value = registered_platform
        result = register_hardware_platform(app, "VEOS", "192.168.140.150")
        assert result["registered"] is True
        assert reg_info.NetClient == "192.168.140.150"
        assert result["unique_name"] == "VEOS_192.168.140.150"
        assert result["display_name"] == "VEOS at 192.168.140.150"

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = MagicMock()
        app.PlatformManagement.CreatePlatformRegistrationInfo.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            register_hardware_platform(app, "SCALEXIO", "192.168.140.110")

    def test_scalexio_sets_api_version_to_2_if_lower(self) -> None:
        """SCALEXIO requires APIVersion 2. Test that we upgrade from 1 to 2."""
        app = MagicMock()
        app.PlatformManagement.PlatformAutomationAPIVersion = 1  # Start at version 1
        reg_info = MagicMock()
        sub = MagicMock()
        reg_info.RegistrationInfos.Add.return_value = sub
        app.PlatformManagement.CreatePlatformRegistrationInfo.return_value = reg_info

        register_hardware_platform(app, "SCALEXIO", "192.168.140.110")

        # Verify that APIVersion was set to 2
        assert app.PlatformManagement.PlatformAutomationAPIVersion == 2

    def test_mabx_sets_api_version_to_2_if_lower(self) -> None:
        """MABX also requires APIVersion 2. Test that we upgrade if needed."""
        app = MagicMock()
        app.PlatformManagement.PlatformAutomationAPIVersion = 1
        reg_info = MagicMock()
        app.PlatformManagement.CreatePlatformRegistrationInfo.return_value = reg_info

        register_hardware_platform(app, "MABX", "192.168.140.200")

        # Verify that APIVersion was set to 2
        assert app.PlatformManagement.PlatformAutomationAPIVersion == 2

    def test_veos_sets_api_version_to_2_if_lower(self) -> None:
        """VEOS also requires APIVersion 2. Test that we upgrade if needed."""
        app = MagicMock()
        app.PlatformManagement.PlatformAutomationAPIVersion = 1
        reg_info = MagicMock()
        registered_platform = MagicMock()
        registered_platform.UniqueName = "VEOS_192.168.140.150"
        registered_platform.DisplayName = "VEOS at 192.168.140.150"
        app.PlatformManagement.CreatePlatformRegistrationInfo.return_value = reg_info
        app.PlatformManagement.RegisterPlatform.return_value = registered_platform

        register_hardware_platform(app, "VEOS", "192.168.140.150")

        # Verify that APIVersion was set to 2
        assert app.PlatformManagement.PlatformAutomationAPIVersion == 2

    def test_raises_precondition_for_invalid_hardware_type(self) -> None:
        """Verify invalid hardware types fail with BridgePreconditionError before COM."""
        app = MagicMock()
        # This should fail immediately, without calling CreatePlatformRegistrationInfo
        with pytest.raises(BridgePreconditionError) as exc_info:
            register_hardware_platform(app, "InvalidHardwareType", "192.168.140.110")

        assert "hardware" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()
        # Verify no COM call was made
        app.PlatformManagement.CreatePlatformRegistrationInfo.assert_not_called()

    def test_raises_precondition_for_xcp_platform_with_helpful_message(self) -> None:
        """Verify XCP platforms are rejected with clear guidance."""
        app = MagicMock()
        with pytest.raises(BridgePreconditionError) as exc_info:
            register_hardware_platform(app, "XCPonCAN", "192.168.140.110")

        error_msg = str(exc_info.value).lower()
        assert "device type" in error_msg or "platform_add" in error_msg


# ── clear_registered_platforms ────────────────────────────────────────────────


class TestClearRegisteredPlatforms:
    def test_calls_clear_system(self) -> None:
        app = MagicMock()
        clear_registered_platforms(app)
        app.PlatformManagement.ClearSystem.assert_called_once_with(False)

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = MagicMock()
        app.PlatformManagement.ClearSystem.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            clear_registered_platforms(app)


# ── add_variable_description ─────────────────────────────────────────────────


class TestAddVariableDescription:
    # ── Bus Device types ───────────────────────────────────────────────────────

    def test_can_monitoring_dbc_calls_add(self) -> None:
        plat = _make_platform(name="CAN_1", plat_type="CANMonitoring")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "CAN_1", "C:\\BusConfig\\mycan.dbc")
        assert result["added"] is True
        assert result["file_path"] == "C:\\BusConfig\\mycan.dbc"
        assert result["variable_description_name"] == "mycan"
        plat.VariableDescriptions.Add.assert_called_once_with("C:\\BusConfig\\mycan.dbc")

    def test_can_monitoring_arxml_calls_add(self) -> None:
        plat = _make_platform(name="CAN_1", plat_type="CANMonitoring")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "CAN_1", "C:\\BusConfig\\can.arxml")
        assert result["added"] is True
        plat.VariableDescriptions.Add.assert_called_once_with("C:\\BusConfig\\can.arxml")

    def test_ethernet_monitoring_arxml_calls_add(self) -> None:
        plat = _make_platform(name="ETH_1", plat_type="EthernetMonitoring")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "ETH_1", "C:\\BusConfig\\eth.arxml")
        assert result["added"] is True
        plat.VariableDescriptions.Add.assert_called_once_with("C:\\BusConfig\\eth.arxml")

    def test_lin_monitoring_ldf_calls_add(self) -> None:
        plat = _make_platform(name="LIN_1", plat_type="LINMonitoring")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "LIN_1", "C:\\BusConfig\\mylin.ldf")
        assert result["added"] is True
        plat.VariableDescriptions.Add.assert_called_once_with("C:\\BusConfig\\mylin.ldf")

    def test_flexray_monitoring_fibex_calls_add(self) -> None:
        plat = _make_platform(name="FR_1", plat_type="FlexRayMonitoring")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "FR_1", "C:\\BusConfig\\fr.fibex")
        assert result["added"] is True
        plat.VariableDescriptions.Add.assert_called_once_with("C:\\BusConfig\\fr.fibex")

    # ── XCP / calibration types ────────────────────────────────────────────────

    def test_xcp_a2l_with_companion_mot_calls_add_with_image(self, tmp_path) -> None:
        a2l = tmp_path / "ecu.a2l"
        mot = tmp_path / "ecu.mot"
        a2l.touch()
        mot.touch()
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "XCP", str(a2l))
        assert result["added"] is True
        assert result["companion_mot_path"] == str(mot)
        plat.VariableDescriptions.AddWithImage.assert_called_once_with(str(a2l), str(mot))

    def test_xcp_a2l_without_mot_calls_add(self, tmp_path) -> None:
        a2l = tmp_path / "ecu.a2l"
        a2l.touch()
        plat = _make_platform(name="XCP", plat_type="XCPonEthernet")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "XCP", str(a2l))
        assert result["added"] is True
        assert result["companion_mot_path"] is None
        plat.VariableDescriptions.Add.assert_called_once_with(str(a2l))

    def test_ccp_a2l_with_companion_mot_calls_add_with_image(self, tmp_path) -> None:
        a2l = tmp_path / "ecu.a2l"
        mot = tmp_path / "ecu.mot"
        a2l.touch()
        mot.touch()
        plat = _make_platform(name="CCP_1", plat_type="CCP")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "CCP_1", str(a2l))
        assert result["added"] is True
        plat.VariableDescriptions.AddWithImage.assert_called_once_with(str(a2l), str(mot))

    # ── Hardware types ─────────────────────────────────────────────────────────

    def test_hardware_sdf_calls_add(self) -> None:
        plat = _make_platform(name="SCALEXIO_1", plat_type="SCALEXIO")
        app = _make_app(platforms=[plat])
        result = add_variable_description(app, "SCALEXIO_1", "C:\\ECU\\scalexio.sdf")
        assert result["added"] is True
        assert result["file_path"] == "C:\\ECU\\scalexio.sdf"
        assert result["variable_description_name"] == "scalexio"
        plat.VariableDescriptions.Add.assert_called_once_with("C:\\ECU\\scalexio.sdf")

    # ── Blocked types ──────────────────────────────────────────────────────────

    def test_diagnostic2_raises_precondition(self) -> None:
        plat = _make_platform(name="Diag_1", plat_type="Diagnostic2")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            add_variable_description(app, "Diag_1", "C:\\ecu.a2l")

    def test_gnss_raises_precondition(self) -> None:
        plat = _make_platform(name="GNSS_1", plat_type="GNSS")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            add_variable_description(app, "GNSS_1", "C:\\ecu.arxml")

    # ── Cross-validation: wrong extension for platform type ────────────────────

    def test_a2l_on_can_monitoring_raises_precondition(self) -> None:
        plat = _make_platform(name="CAN_1", plat_type="CANMonitoring")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            add_variable_description(app, "CAN_1", "C:\\ecu.a2l")

    def test_dbc_on_xcp_raises_precondition(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            add_variable_description(app, "XCP", "C:\\bus.dbc")

    def test_sdf_on_can_monitoring_raises_precondition(self) -> None:
        plat = _make_platform(name="CAN_1", plat_type="CANMonitoring")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            add_variable_description(app, "CAN_1", "C:\\ecu.sdf")

    def test_unknown_extension_raises_precondition(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            add_variable_description(app, "XCP", "C:\\ecu.xyz")


# ── configure_calibration_behavior ───────────────────────────────────────────


class TestConfigureCalibrationBehavior:
    def test_sets_behavior_and_page(self) -> None:
        plat = _make_platform(name="XCP")
        app = _make_app(platforms=[plat])
        result = configure_calibration_behavior(app, "XCP", "UploadConnectedVariables", "WorkingPage")
        assert result["configured"] is True
        assert result["calibration_behavior"] == "UploadConnectedVariables"
        assert result["initial_page"] == "WorkingPage"

    def test_raises_bridge_error_on_com_failure(self) -> None:
        plat = _make_platform(name="XCP")
        plat.GeneralSettings = MagicMock()
        type(plat.GeneralSettings).StartOnlineCalibrationBehavior = PropertyMock(side_effect=Exception("COM error"))
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgeError):
            configure_calibration_behavior(app, "XCP", "Upload", "ReferencePage")


# ── set_api_version ───────────────────────────────────────────────────────────


class TestSetApiVersion:
    def test_sets_version_on_platform_management(self) -> None:
        app = MagicMock()
        result = set_api_version(app, "APIVersion2")
        assert result["version_string"] == "APIVersion2"
        assert result["version_integer"] == 2
        assert result["configured"] is True

    def test_api_version_1(self) -> None:
        app = MagicMock()
        result = set_api_version(app, "APIVersion1")
        assert result["version_string"] == "APIVersion1"
        assert result["version_integer"] == 1
        assert result["configured"] is True

    def test_raises_precondition_for_invalid_version(self) -> None:
        app = MagicMock()
        with pytest.raises(BridgePreconditionError):
            set_api_version(app, "APIVersion3")

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = MagicMock()
        type(app.PlatformManagement).PlatformAutomationAPIVersion = PropertyMock(side_effect=Exception("COM error"))
        with pytest.raises(BridgeError):
            set_api_version(app, "APIVersion2")


# ── configure_transport ───────────────────────────────────────────────────────


class TestConfigureTransport:
    def test_can_baud_rate(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])
        result = configure_transport(app, "XCP", 500000, None, None, None)
        assert result["configured"] is True
        assert result["baud_rate"] == 500000

    def test_can_monitoring_baud_rate(self) -> None:
        plat = _make_platform(name="CAN_1", plat_type="CANMonitoring")
        app = _make_app(platforms=[plat])
        result = configure_transport(app, "CAN_1", 500000, None, None, None)
        assert result["configured"] is True
        assert result["baud_rate"] == 500000

    def test_ethernet_automatic_adapter(self) -> None:
        plat = _make_platform(name="XCPonEth", plat_type="XCPonEthernet")
        app = _make_app(platforms=[plat])
        result = configure_transport(app, "XCPonEth", None, "TCP", True, None)
        assert result["configured"] is True
        assert result["automatic_adapter"] is True
        assert result["adapter_name"] is None

    def test_ethernet_adapter_discovery(self) -> None:
        plat = _make_platform(name="XCPonEth", plat_type="XCPonEthernet")
        # Mock network adapters
        adapter1 = MagicMock()
        type(adapter1).Description = PropertyMock(return_value="Intel Ethernet")
        adapter2 = MagicMock()
        type(adapter2).Description = PropertyMock(return_value="dSPACE Adapter")
        adapters_col = MagicMock()
        type(adapters_col).Count = PropertyMock(return_value=2)
        adapters_col.Item.side_effect = lambda i: [adapter1, adapter2][i - 1]
        plat.NetworkAdapterSelection.NetworkAdapters = adapters_col
        app = _make_app(platforms=[plat])
        result = configure_transport(app, "XCPonEth", None, None, False, None)
        assert result["configured"] is False
        assert "available_adapters" in result
        assert len(result["available_adapters"]) == 2

    def test_ethernet_with_adapter_name(self) -> None:
        plat = _make_platform(name="XCPonEth", plat_type="XCPonEthernet")
        app = _make_app(platforms=[plat])
        result = configure_transport(app, "XCPonEth", None, None, False, "Intel Ethernet")
        assert result["configured"] is True
        assert result["adapter_name"] == "Intel Ethernet"


# ── list_interfaces ───────────────────────────────────────────────────────────


class TestListInterfaces:
    def test_raises_precondition_for_non_can_platform(self) -> None:
        plat = _make_platform(name="SCALEXIO_1", plat_type="SCALEXIO")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            list_interfaces(app, "SCALEXIO_1")

    def test_raises_precondition_for_diagnostic2(self) -> None:
        plat = _make_platform(name="Diag_1", plat_type="Diagnostic2")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            list_interfaces(app, "Diag_1")

    def test_raises_precondition_for_ethernet_monitoring(self) -> None:
        plat = _make_platform(name="ETH_1", plat_type="EthernetMonitoring")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError):
            list_interfaces(app, "ETH_1")

    def _make_interface_tree(self, plat: MagicMock) -> None:
        """Wire up a mock vendor/interface/channel tree on plat."""
        channels_col = MagicMock()
        type(channels_col).Count = PropertyMock(return_value=1)
        iface = MagicMock()
        type(iface).Name = PropertyMock(return_value="Virtual")
        iface.Channels = channels_col
        ifaces_col = MagicMock()
        type(ifaces_col).Count = PropertyMock(return_value=1)
        ifaces_col.Item.return_value = iface
        vendor = MagicMock()
        type(vendor).Name = PropertyMock(return_value="dSPACE")
        vendor.AvailableInterfaces = ifaces_col
        vendors_col = MagicMock()
        type(vendors_col).Count = PropertyMock(return_value=1)
        vendors_col.Item.return_value = vendor
        plat.InterfaceSelection.Vendors = vendors_col

    def test_returns_vendors_and_interfaces_for_xcp_on_can(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        self._make_interface_tree(plat)
        app = _make_app(platforms=[plat])
        result = list_interfaces(app, "XCP")
        assert result["platform_name"] == "XCP"
        assert len(result["interfaces"]) == 1
        assert result["interfaces"][0]["vendor_name"] == "dSPACE"
        assert result["interfaces"][0]["interfaces"][0]["interface_name"] == "Virtual"
        assert result["interfaces"][0]["interfaces"][0]["channel_count"] == 1

    def test_returns_vendors_and_interfaces_for_can_monitoring(self) -> None:
        # CANMonitoring enumerates vendors just like XCPonCAN — Virtual/Automatic selection
        plat = _make_platform(name="CAN_1", plat_type="CANMonitoring")
        self._make_interface_tree(plat)
        app = _make_app(platforms=[plat])
        result = list_interfaces(app, "CAN_1")
        assert result["platform_name"] == "CAN_1"
        assert len(result["interfaces"]) == 1
        assert result["interfaces"][0]["vendor_name"] == "dSPACE"
        assert result["interfaces"][0]["interfaces"][0]["interface_name"] == "Virtual"
        assert result["interfaces"][0]["interfaces"][0]["channel_count"] == 1

    def test_returns_vendors_and_interfaces_for_lin_monitoring(self) -> None:
        # LINMonitoring enumerates vendors just like XCPonCAN — Virtual/Automatic selection
        plat = _make_platform(name="LIN_1", plat_type="LINMonitoring")
        self._make_interface_tree(plat)
        app = _make_app(platforms=[plat])
        result = list_interfaces(app, "LIN_1")
        assert result["platform_name"] == "LIN_1"
        assert len(result["interfaces"]) == 1
        assert result["interfaces"][0]["vendor_name"] == "dSPACE"


# ── select_interface_manual ───────────────────────────────────────────────────


class TestSelectInterfaceManual:
    def test_selects_channel_and_returns_result(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        channel = MagicMock()
        (
            plat.InterfaceSelection.Vendors.Item("dSPACE")
            .AvailableInterfaces.Item("Virtual")
            .Channels.Item.return_value
        ) = channel
        app = _make_app(platforms=[plat])
        result = select_interface_manual(app, "XCP", "dSPACE", "Virtual", 0)
        assert result["selected"] is True
        assert result["vendor"] == "dSPACE"
        assert result["interface"] == "Virtual"
        assert result["channel_index"] == 0

    def test_raises_bridge_error_on_com_failure(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        plat.InterfaceSelection.Vendors.Item.side_effect = Exception("Vendor not found")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgeError):
            select_interface_manual(app, "XCP", "BadVendor", "Virtual", 0)


# ── connect_platform ──────────────────────────────────────────────────────────


class TestConnectPlatform:
    def test_returns_connected_true(self) -> None:
        plat = _make_platform(name="XCP", connection_state="Connected")
        app = _make_app(platforms=[plat])
        result = connect_platform(app, "XCP")
        assert result["connected"] is True
        assert result["platform_name"] == "XCP"
        plat.Connect.assert_called_once()

    def test_raises_bridge_error_on_com_failure(self) -> None:
        plat = _make_platform(name="XCP")
        plat.Connect.side_effect = Exception("COM error")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgeError):
            connect_platform(app, "XCP")

    def test_raises_precondition_when_platform_not_found(self) -> None:
        app = _make_app(platforms=[])
        with pytest.raises(BridgePreconditionError):
            connect_platform(app, "NonExistent")


# ── disconnect_platform ───────────────────────────────────────────────────────


class TestDisconnectPlatform:
    def test_returns_disconnected_true(self) -> None:
        plat = _make_platform(name="XCP", connection_state="Disconnected")
        app = _make_app(platforms=[plat])
        result = disconnect_platform(app, "XCP")
        assert result["disconnected"] is True
        assert result["platform_name"] == "XCP"
        plat.Disconnect.assert_called_once()

    def test_raises_bridge_error_on_com_failure(self) -> None:
        plat = _make_platform(name="XCP")
        plat.Disconnect.side_effect = Exception("COM error")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgeError):
            disconnect_platform(app, "XCP")


# ── get_connection_state ──────────────────────────────────────────────────────


class TestGetConnectionState:
    def test_returns_connected_state(self) -> None:
        plat = _make_platform(name="XCP", connection_state="Connected")
        app = _make_app(platforms=[plat])
        result = get_connection_state(app, "XCP")
        assert result["connection_state"] == "Connected"
        assert result["is_connected"] is True
        assert result["platform_name"] == "XCP"

    def test_returns_disconnected_state(self) -> None:
        plat = _make_platform(name="XCP", connection_state="Disconnected")
        app = _make_app(platforms=[plat])
        result = get_connection_state(app, "XCP")
        assert result["connection_state"] == "Disconnected"
        assert result["is_connected"] is False

    def test_raises_precondition_when_platform_not_found(self) -> None:
        app = _make_app(platforms=[])
        with pytest.raises(BridgePreconditionError):
            get_connection_state(app, "NonExistent")


# ── list_platform_types ───────────────────────────────────────────────────────


class TestListPlatformTypes:
    def test_returns_categories(self) -> None:
        result = list_platform_types()
        assert "categories" in result
        assert len(result["categories"]) == 5

    def test_categories_have_required_fields(self) -> None:
        result = list_platform_types()
        for cat in result["categories"]:
            assert "category" in cat
            assert "types" in cat
            assert isinstance(cat["types"], list)

    def test_xcp_on_can_in_measurement_category(self) -> None:
        result = list_platform_types()
        measurement_cat = next(c for c in result["categories"] if c["category"] == "Measurement & Calibration")
        names = [t["name"] for t in measurement_cat["types"]]
        assert "XCPonCAN" in names

    def test_scalexio_in_hardware_category(self) -> None:
        result = list_platform_types()
        hardware_cat = next(c for c in result["categories"] if c["category"] == "Hardware")
        names = [t["name"] for t in hardware_cat["types"]]
        assert "SCALEXIO" in names

    def test_integer_values_present(self) -> None:
        result = list_platform_types()
        for cat in result["categories"]:
            for t in cat["types"]:
                assert "integer_value" in t
                assert isinstance(t["integer_value"], int)

    def test_no_com_call_required(self) -> None:
        # list_platform_types is pure static data — must not raise even without a mock app
        result = list_platform_types()
        assert result is not None

    def test_add_platform_raises_for_unknown_type(self) -> None:
        app = _make_app()
        with pytest.raises(BridgePreconditionError, match="Unknown platform type"):
            add_platform(app, "NotARealPlatform")

    def test_add_platform_passes_integer_to_com(self) -> None:
        app = _make_app()
        new_plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app.ActiveExperiment.Platforms.Add.return_value = new_plat
        add_platform(app, "XCPonCAN")
        # COM must receive the integer 4 (XCPonCAN), not the string
        app.ActiveExperiment.Platforms.Add.assert_called_once_with(4)

    def test_list_platforms_returns_type_name_not_integer(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN", vd_count=0)
        app = _make_app(platforms=[plat])
        result = list_platforms(app)
        # Type should be the human-readable name, not the raw integer "4"
        assert result[0]["type"] == "XCPonCAN"


# ── configure_calibration_behavior (fixed integer enums) ─────────────────────


class TestConfigureCalibrationBehaviorEnums:
    def test_valid_behavior_and_page_pass_integers_to_com(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])
        behavior = "UploadConnectedVariables"
        result = configure_calibration_behavior(app, "XCP", behavior, "WorkingPage")
        assert result["configured"] is True
        # COM must receive integer 5 (UploadConnectedVariables) and 1 (WorkingPage)
        assert plat.GeneralSettings.StartOnlineCalibrationBehavior == 5
        assert plat.GeneralSettings.InitialPage == 1

    def test_invalid_behavior_raises_precondition(self) -> None:
        app = _make_app()
        with pytest.raises(BridgePreconditionError, match="Unknown calibration_behavior"):
            configure_calibration_behavior(app, "XCP", "NotABehavior", "WorkingPage")

    def test_invalid_initial_page_raises_precondition(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgePreconditionError, match="Unknown initial_page"):
            configure_calibration_behavior(app, "XCP", "UploadConnectedVariables", "BadPage")


# ── configure_platform ────────────────────────────────────────────────────────


class TestConfigurePlatform:
    # ── CAN interface selection ────────────────────────────────────────────────

    def test_virtual_interface_selection(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        virtual_iface = MagicMock()
        type(virtual_iface).Name = PropertyMock(return_value="Virtual")
        available = MagicMock()
        available.Count = 1
        available.Item.return_value = virtual_iface
        plat.InterfaceSelection.Vendors.Item.return_value.AvailableInterfaces = available
        app = _make_app(platforms=[plat])

        result = configure_platform(
            app,
            "XCP",
            can_interface="Virtual",
            ip_address=None,
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior=None,
        )
        assert result["configured"] is True
        assert result["can_interface"] == "Virtual"
        virtual_iface.Channels.Item(0).Select.assert_called()

    def test_automatic_can_interface(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])

        result = configure_platform(
            app,
            "XCP",
            can_interface="Automatic",
            ip_address=None,
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior=None,
        )
        assert result["configured"] is True
        assert result["can_interface"] == "Automatic"
        plat.InterfaceSelection.AutomaticAssignment = True

    def test_unknown_can_interface_raises_precondition(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        available = MagicMock()
        available.Count = 1
        iface = MagicMock()
        type(iface).Name = PropertyMock(return_value="DS4302")
        available.Item.return_value = iface
        plat.InterfaceSelection.Vendors.Item.return_value.AvailableInterfaces = available
        app = _make_app(platforms=[plat])

        with pytest.raises(BridgePreconditionError, match="not found"):
            configure_platform(
                app,
                "XCP",
                can_interface="NonExistent",
                ip_address=None,
                mac_address=None,
                board_name=None,
                assignment_mode=None,
                calibration_behavior=None,
            )

    # ── SMART assignment (SCALEXIO) ────────────────────────────────────────────

    def test_scalexio_ip_address_assignment(self) -> None:
        plat = _make_platform(name="SCALEXIO_1", plat_type="SCALEXIO")
        assignment_obj = MagicMock()
        assignment_obj.IPAddress = ""
        assignment_obj.BoardName = ""
        plat.Assignment.Assignments.Count = 1
        plat.Assignment.Assignments.Item.return_value = assignment_obj
        app = _make_app(platforms=[plat])

        result = configure_platform(
            app,
            "SCALEXIO_1",
            can_interface=None,
            ip_address="192.168.140.110",
            mac_address=None,
            board_name=None,
            assignment_mode="AnyEqual",
            calibration_behavior=None,
        )
        assert result["configured"] is True
        assert result["ip_address"] == "192.168.140.110"
        assert result["assignment_mode"] == "AnyEqual"
        plat.Assignment.Mode == 1  # AnyEqual = 1

    def test_scalexio_creates_assignment_if_none(self) -> None:
        plat = _make_platform(name="SCALEXIO_1", plat_type="SCALEXIO")
        new_assignment = MagicMock()
        new_assignment.IPAddress = ""
        new_assignment.BoardName = ""
        plat.Assignment.Assignments.Count = 0
        plat.Assignment.Assignments.CreateNewAssignment.return_value = new_assignment
        app = _make_app(platforms=[plat])

        result = configure_platform(
            app,
            "SCALEXIO_1",
            can_interface=None,
            ip_address="192.168.140.110",
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior=None,
        )
        assert result["configured"] is True
        plat.Assignment.Assignments.CreateNewAssignment.assert_called_once()

    # ── VEOS ──────────────────────────────────────────────────────────────────

    def test_veos_sets_net_client(self) -> None:
        plat = _make_platform(name="VEOS_1", plat_type="VEOS")
        app = _make_app(platforms=[plat])

        result = configure_platform(
            app,
            "VEOS_1",
            can_interface=None,
            ip_address="127.0.0.1",
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior=None,
        )
        assert result["configured"] is True
        assert result["ip_address"] == "127.0.0.1"
        assert plat.Assignment.NetClient == "127.0.0.1"

    def test_veos_defaults_to_localhost_when_no_ip(self) -> None:
        plat = _make_platform(name="VEOS_1", plat_type="VEOS")
        app = _make_app(platforms=[plat])

        result = configure_platform(
            app,
            "VEOS_1",
            can_interface=None,
            ip_address=None,
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior=None,
        )
        assert result["configured"] is True
        assert result["ip_address"] == "127.0.0.1"

    # ── Calibration behavior ───────────────────────────────────────────────────

    def test_calibration_behavior_set_as_integer(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        available = MagicMock()
        available.Count = 0
        plat.InterfaceSelection.Vendors.Item.return_value.AvailableInterfaces = available
        app = _make_app(platforms=[plat])

        configure_platform(
            app,
            "XCP",
            can_interface=None,
            ip_address=None,
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior="UploadConnectedVariables",
        )
        # COM must receive integer 5
        assert plat.GeneralSettings.StartOnlineCalibrationBehavior == 5

    def test_invalid_calibration_behavior_raises_precondition(self) -> None:
        app = _make_app()
        with pytest.raises(BridgePreconditionError, match="Unknown calibration_behavior"):
            configure_platform(
                app,
                "XCP",
                can_interface=None,
                ip_address=None,
                mac_address=None,
                board_name=None,
                assignment_mode=None,
                calibration_behavior="Invalid",
            )

    def test_invalid_assignment_mode_raises_precondition(self) -> None:
        app = _make_app()
        with pytest.raises(BridgePreconditionError, match="Unknown assignment_mode"):
            configure_platform(
                app,
                "XCP",
                can_interface=None,
                ip_address=None,
                mac_address=None,
                board_name=None,
                assignment_mode="BadMode",
                calibration_behavior=None,
            )

    def test_raises_precondition_when_no_experiment(self) -> None:
        app = _make_no_experiment_app()
        with pytest.raises(BridgePreconditionError):
            configure_platform(
                app,
                "XCP",
                can_interface=None,
                ip_address=None,
                mac_address=None,
                board_name=None,
                assignment_mode=None,
                calibration_behavior=None,
            )


# ── rename_platform ───────────────────────────────────────────────────────────


class TestRenamePlatform:
    def test_calls_platforms_rename(self) -> None:
        app = _make_app()
        result = rename_platform(app, "XCP", "XCP_CalDemo")
        assert result["renamed"] is True
        assert result["old_name"] == "XCP"
        assert result["new_name"] == "XCP_CalDemo"
        app.ActiveExperiment.Platforms.Rename.assert_called_once_with("XCP", "XCP_CalDemo")

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = _make_app()
        app.ActiveExperiment.Platforms.Rename.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            rename_platform(app, "XCP", "XCP_New")

    def test_raises_precondition_when_no_experiment(self) -> None:
        app = _make_no_experiment_app()
        with pytest.raises(BridgePreconditionError):
            rename_platform(app, "XCP", "XCP_New")


# ── _connection_state_str / _measurement_state_str ───────────────────────────


class TestStateStringHelpers:
    def test_connection_state_connected(self) -> None:
        from controldesk_mcp.com_bridge.domains.platform_com import _connection_state_str

        assert _connection_state_str(0) == "Connected"

    def test_connection_state_disconnected(self) -> None:
        from controldesk_mcp.com_bridge.domains.platform_com import _connection_state_str

        assert _connection_state_str(1) == "Disconnected"

    def test_connection_state_unknown_int_returns_raw(self) -> None:
        from controldesk_mcp.com_bridge.domains.platform_com import _connection_state_str

        assert _connection_state_str(99) == "99"

    def test_connection_state_string_fallback(self) -> None:
        # Real COM returns integers, but tests may use strings — fallback must work.
        from controldesk_mcp.com_bridge.domains.platform_com import _connection_state_str

        assert _connection_state_str("Disconnected") == "Disconnected"

    def test_measurement_state_stopped(self) -> None:
        from controldesk_mcp.com_bridge.domains.platform_com import _measurement_state_str

        assert _measurement_state_str(0) == "Stopped"

    def test_measurement_state_running(self) -> None:
        from controldesk_mcp.com_bridge.domains.platform_com import _measurement_state_str

        assert _measurement_state_str(1) == "Running"

    def test_measurement_state_string_fallback(self) -> None:
        from controldesk_mcp.com_bridge.domains.platform_com import _measurement_state_str

        assert _measurement_state_str("Stopped") == "Stopped"


# ── list_platforms / get_platform_info — integer state conversion ─────────────


class TestStateConversionInListPlatforms:
    def test_connection_state_integer_converted_to_string(self) -> None:
        """COM returns integer 0 for Connected — must appear as 'Connected' in output."""
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        # Override mock to return integer as COM would
        type(plat).ConnectionState = PropertyMock(return_value=0)
        type(plat).MeasurementState = PropertyMock(return_value=0)
        app = _make_app(platforms=[plat])
        result = list_platforms(app)
        assert result[0]["connection_state"] == "Connected"
        assert result[0]["measurement_state"] == "Stopped"

    def test_measurement_state_running_integer(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        type(plat).ConnectionState = PropertyMock(return_value=0)
        type(plat).MeasurementState = PropertyMock(return_value=1)
        app = _make_app(platforms=[plat])
        result = list_platforms(app)
        assert result[0]["measurement_state"] == "Running"


# ── configure_platform — bus device auto-assignment ───────────────────────────


class TestConfigurePlatformBusDeviceAutoAssignment:
    def test_can_monitoring_with_no_can_interface_does_not_change_assignment(self) -> None:
        # When can_interface=None, CANMonitoring retains whatever assignment was set by platform_add
        plat = _make_platform(name="CAN_2", plat_type="CANMonitoring")
        app = _make_app(platforms=[plat])
        result = configure_platform(
            app,
            "CAN_2",
            can_interface=None,
            ip_address=None,
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior=None,
        )
        assert result["configured"] is True
        # can_interface not in result when not explicitly set
        assert "can_interface" not in result
        plat.InterfaceSelection.AutomaticAssignment.assert_not_called()

    def test_can_monitoring_with_automatic_can_interface_sets_assignment(self) -> None:
        plat = _make_platform(name="CAN_2", plat_type="CANMonitoring")
        app = _make_app(platforms=[plat])
        result = configure_platform(
            app,
            "CAN_2",
            can_interface="Automatic",
            ip_address=None,
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior=None,
        )
        assert result["configured"] is True
        assert result["can_interface"] == "Automatic"
        assert plat.InterfaceSelection.AutomaticAssignment is True

    def test_lin_monitoring_with_automatic_can_interface_sets_assignment(self) -> None:
        plat = _make_platform(name="LIN_1", plat_type="LINMonitoring")
        app = _make_app(platforms=[plat])
        result = configure_platform(
            app,
            "LIN_1",
            can_interface="Automatic",
            ip_address=None,
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior=None,
        )
        assert result["can_interface"] == "Automatic"
        assert plat.InterfaceSelection.AutomaticAssignment is True

    def test_bus_device_ignores_calibration_behavior(self) -> None:
        """Bus device types must NOT call StartOnlineCalibrationBehavior — it raises COM error."""
        plat = _make_platform(name="CAN_2", plat_type="CANMonitoring")
        app = _make_app(platforms=[plat])
        result = configure_platform(
            app,
            "CAN_2",
            can_interface=None,
            ip_address=None,
            mac_address=None,
            board_name=None,
            assignment_mode=None,
            calibration_behavior="UploadConnectedVariables",
        )
        # calibration_behavior must NOT appear in result for bus device types
        assert "calibration_behavior" not in result


# ── list_interfaces — bus device returns automatic note ──────────────────────


class TestListInterfacesBusDevice:
    def _make_interface_tree(self, plat: MagicMock) -> None:
        channels_col = MagicMock()
        type(channels_col).Count = PropertyMock(return_value=2)
        iface = MagicMock()
        type(iface).Name = PropertyMock(return_value="Virtual")
        iface.Channels = channels_col
        ifaces_col = MagicMock()
        type(ifaces_col).Count = PropertyMock(return_value=1)
        ifaces_col.Item.return_value = iface
        vendor = MagicMock()
        type(vendor).Name = PropertyMock(return_value="dSPACE")
        vendor.AvailableInterfaces = ifaces_col
        vendors_col = MagicMock()
        type(vendors_col).Count = PropertyMock(return_value=1)
        vendors_col.Item.return_value = vendor
        plat.InterfaceSelection.Vendors = vendors_col

    def test_can_monitoring_enumerates_vendors(self) -> None:
        # CANMonitoring now enumerates vendors (Virtual/physical); no longer returns empty list
        plat = _make_platform(name="CAN_2", plat_type="CANMonitoring")
        self._make_interface_tree(plat)
        app = _make_app(platforms=[plat])
        result = list_interfaces(app, "CAN_2")
        assert result["platform_name"] == "CAN_2"
        assert len(result["interfaces"]) == 1
        assert result["interfaces"][0]["vendor_name"] == "dSPACE"

    def test_lin_monitoring_enumerates_vendors(self) -> None:
        # LINMonitoring now enumerates vendors like XCPonCAN
        plat = _make_platform(name="LIN_1", plat_type="LINMonitoring")
        self._make_interface_tree(plat)
        app = _make_app(platforms=[plat])
        result = list_interfaces(app, "LIN_1")
        assert len(result["interfaces"]) == 1
        assert result["interfaces"][0]["vendor_name"] == "dSPACE"


class TestListRegisteredHardware:
    def _make_recent(self, platforms: list) -> MagicMock:
        """Helper to build a mock IPmRecentPlatformConfiguration collection."""
        recent = MagicMock()
        recent.Count = len(platforms)
        recent.Item = MagicMock(side_effect=lambda i: platforms[i])
        return recent

    def test_list_registered_hardware_empty(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        pm.RecentPlatformConfiguration = self._make_recent([])
        result = list_registered_hardware(app)
        assert result["count"] == 0
        assert result["registered_platforms"] == []

    def test_list_registered_hardware_single_platform(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        plat = MagicMock()
        plat.UniqueName = "hw_1_unique"
        plat.Name = "hw_1"
        plat.Type = 15  # SCALEXIO type integer
        plat.ConnectionState = 0  # Connected
        pm.RecentPlatformConfiguration = self._make_recent([plat])
        result = list_registered_hardware(app)
        assert result["count"] == 1
        assert len(result["registered_platforms"]) == 1
        assert result["registered_platforms"][0]["unique_name"] == "hw_1_unique"
        assert result["registered_platforms"][0]["name"] == "hw_1"
        assert result["registered_platforms"][0]["index"] == 0
        assert result["registered_platforms"][0]["connection_state"] == "Connected"

    def test_list_registered_hardware_with_optional_properties(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        plat = MagicMock()
        plat.UniqueName = "hw_2_unique"
        plat.Name = "hw_2"
        plat.Type = 15  # SCALEXIO
        plat.ConnectionState = 0
        plat.IPAddress = "192.168.1.100"
        plat.BoardName = "SCALEXIO_1"
        pm.RecentPlatformConfiguration = self._make_recent([plat])
        result = list_registered_hardware(app)
        assert result["registered_platforms"][0]["ip_address"] == "192.168.1.100"
        assert result["registered_platforms"][0]["board_name"] == "SCALEXIO_1"

    def test_list_registered_hardware_gracefully_skips_broken_platform(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        good_plat = MagicMock()
        good_plat.UniqueName = "good_unique"
        good_plat.Name = "good"
        good_plat.Type = 15
        good_plat.ConnectionState = 0
        bad_plat = MagicMock()
        # Simulate a platform whose UniqueName fails (causes outer except to skip entry)
        type(bad_plat).UniqueName = PropertyMock(side_effect=Exception("COM error"))
        pm.RecentPlatformConfiguration = self._make_recent([good_plat, bad_plat])
        result = list_registered_hardware(app)
        # Should only include the good platform
        assert result["count"] == 1
        assert result["registered_platforms"][0]["name"] == "good"

    def test_list_registered_hardware_multiple_platforms(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        plat1 = MagicMock()
        plat1.UniqueName = "hw_a_unique"
        plat1.Name = "hw_a"
        plat1.Type = 15
        plat1.ConnectionState = 0
        plat2 = MagicMock()
        plat2.UniqueName = "hw_b_unique"
        plat2.Name = "hw_b"
        plat2.Type = 16  # DS1202
        plat2.ConnectionState = 1  # Disconnected
        pm.RecentPlatformConfiguration = self._make_recent([plat1, plat2])
        result = list_registered_hardware(app)
        assert result["count"] == 2
        assert result["registered_platforms"][0]["name"] == "hw_a"
        assert result["registered_platforms"][1]["name"] == "hw_b"
        assert result["registered_platforms"][1]["connection_state"] == "Disconnected"


# ── get_registered_info ───────────────────────────────────────────────────────


class TestGetRegisteredInfo:
    def test_get_registered_info_success(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        plat = MagicMock()
        plat.UniqueName = "hw_1_unique"
        plat.Name = "hw_1"
        plat.Type = 15  # SCALEXIO
        plat.ConnectionState = 0
        plat.IPAddress = "192.168.1.100"
        plat.BoardName = "SCALEXIO_Board"
        recent = MagicMock()
        recent.Item = MagicMock(return_value=plat)
        pm.RecentPlatformConfiguration = recent
        result = get_registered_info(app, 0)
        assert result["index"] == 0
        assert result["unique_name"] == "hw_1_unique"
        assert result["name"] == "hw_1"
        assert result["ip_address"] == "192.168.1.100"
        assert result["board_name"] == "SCALEXIO_Board"
        assert result["connection_state"] == "Connected"

    def test_get_registered_info_index_out_of_range(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        recent = MagicMock()
        recent.Item = MagicMock(side_effect=IndexError("out of range"))
        pm.RecentPlatformConfiguration = recent
        with pytest.raises(BridgePreconditionError) as exc_info:
            get_registered_info(app, 99)
        assert "not found" in str(exc_info.value)
        assert "platform_list_registered_hardware" in str(exc_info.value)

    def test_get_registered_info_handles_missing_properties(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        plat = MagicMock(spec=["UniqueName", "Name", "Type", "ConnectionState"])
        plat.UniqueName = "hw_2_unique"
        plat.Name = "hw_2"
        plat.Type = 17  # DS1203
        plat.ConnectionState = 0
        # plat does NOT have IPAddress, BoardName, SerialNumber — should gracefully skip
        recent = MagicMock()
        recent.Item = MagicMock(return_value=plat)
        pm.RecentPlatformConfiguration = recent
        result = get_registered_info(app, 0)
        assert result["unique_name"] == "hw_2_unique"
        assert result["name"] == "hw_2"
        # Optional properties should not be present
        assert "ip_address" not in result
        assert "board_name" not in result

    def test_get_registered_info_veos_platform(self) -> None:
        app = MagicMock()
        pm = MagicMock()
        app.PlatformManagement = pm
        plat = MagicMock(spec=["UniqueName", "Name", "Type", "ConnectionState"])
        plat.UniqueName = "veos_sim_unique"
        plat.Name = "veos_sim"
        plat.Type = 26  # VEOS
        plat.ConnectionState = 0
        recent = MagicMock()
        recent.Item = MagicMock(return_value=plat)
        pm.RecentPlatformConfiguration = recent
        result = get_registered_info(app, 0)
        assert result["unique_name"] == "veos_sim_unique"
        assert result["type"] == "VEOS"
        assert "ip_address" not in result  # VEOS has no IP address


# ── clear_registered_platforms (with force_driver_reset param) ────────────────


class TestClearRegisteredPlatformsWithForceReset:
    def test_clear_with_force_false_calls_clearsystem_false(self) -> None:
        app = MagicMock()
        clear_registered_platforms(app, force_driver_reset=False)
        app.PlatformManagement.ClearSystem.assert_called_once_with(False)

    def test_clear_with_force_true_calls_clearsystem_true(self) -> None:
        app = MagicMock()
        clear_registered_platforms(app, force_driver_reset=True)
        app.PlatformManagement.ClearSystem.assert_called_once_with(True)

    def test_clear_default_is_force_false(self) -> None:
        app = MagicMock()
        clear_registered_platforms(app)
        app.PlatformManagement.ClearSystem.assert_called_once_with(False)

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = MagicMock()
        app.PlatformManagement.ClearSystem.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            clear_registered_platforms(app)


# ── refresh_platform_configuration ───────────────────────────────────────────


class TestRefreshPlatformConfiguration:
    def test_calls_refresh_and_returns_result(self) -> None:
        app = MagicMock()
        result = refresh_platform_configuration(app)
        app.PlatformManagement.RefreshPlatformConfiguration.assert_called_once_with()
        assert result["refreshed"] is True
        assert result["operation"] == "RefreshPlatformConfiguration"

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = MagicMock()
        app.PlatformManagement.RefreshPlatformConfiguration.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            refresh_platform_configuration(app)


# ── refresh_interface_connections ─────────────────────────────────────────────


class TestRefreshInterfaceConnections:
    def test_calls_refresh_with_force_true(self) -> None:
        app = MagicMock()
        result = refresh_interface_connections(app, force_driver_reset=True)
        app.PlatformManagement.RefreshInterfaceConnections.assert_called_once_with(True)
        assert result["refreshed"] is True
        assert result["force_driver_reset"] is True
        assert result["operation"] == "RefreshInterfaceConnections"

    def test_calls_refresh_with_force_false(self) -> None:
        app = MagicMock()
        result = refresh_interface_connections(app, force_driver_reset=False)
        app.PlatformManagement.RefreshInterfaceConnections.assert_called_once_with(False)
        assert result["force_driver_reset"] is False

    def test_default_force_is_true(self) -> None:
        app = MagicMock()
        refresh_interface_connections(app)
        app.PlatformManagement.RefreshInterfaceConnections.assert_called_once_with(True)

    def test_raises_bridge_error_on_com_failure(self) -> None:
        app = MagicMock()
        app.PlatformManagement.RefreshInterfaceConnections.side_effect = Exception("COM error")
        with pytest.raises(BridgeError):
            refresh_interface_connections(app)


# ── set_platform_enabled ──────────────────────────────────────────────────────


class TestSetPlatformEnabled:
    def test_enable_platform(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])
        result = set_platform_enabled(app, "XCP", True)
        assert result["configured"] is True
        assert result["platform_name"] == "XCP"
        assert result["enabled"] is True
        assert plat.GeneralSettings.EnablePlatform is True

    def test_disable_platform(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        app = _make_app(platforms=[plat])
        result = set_platform_enabled(app, "XCP", False)
        assert result["configured"] is True
        assert result["enabled"] is False
        assert plat.GeneralSettings.EnablePlatform is False

    def test_raises_precondition_when_platform_not_found(self) -> None:
        app = _make_app(platforms=[])
        with pytest.raises(BridgePreconditionError):
            set_platform_enabled(app, "NonExistent", True)

    def test_raises_bridge_error_on_com_failure(self) -> None:
        plat = _make_platform(name="XCP", plat_type="XCPonCAN")
        plat.GeneralSettings = MagicMock()
        type(plat.GeneralSettings).EnablePlatform = PropertyMock(side_effect=Exception("COM error"))
        app = _make_app(platforms=[plat])
        with pytest.raises(BridgeError):
            set_platform_enabled(app, "XCP", True)

    def test_raises_precondition_when_no_experiment(self) -> None:
        app = _make_no_experiment_app()
        with pytest.raises(BridgePreconditionError):
            set_platform_enabled(app, "XCP", True)
