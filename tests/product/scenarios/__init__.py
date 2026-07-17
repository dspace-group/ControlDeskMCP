"""Manual product tests — platform management tools (direct tool calls).

Each test calls the tool function directly with a Pydantic input model,
parses the JSON response envelope, and asserts the response fields.

No LLM involvement.  Requires a live ControlDesk instance with an active
experiment containing at least one platform (started by the session fixture
in tests/product/conftest.py).

Run:
    .\\scripts\\run_product_tests.ps1 -Suite manual

Test organisation
-----------------
- Tests that only READ state (list, get_info, get_connection_state) are safe
  to run on any experiment.
- Tests that MUTATE state (add, remove, connect, configure) require an
  experiment with the expected platform already present, or are structured to
  clean up after themselves.
- Hardware-specific tests (register_hardware, add_registered) are skipped
  unless the relevant environment is available.
"""

from __future__ import annotations

import json

import pytest

import sources.tools.platform.management as _platform_module  # noqa: F401 — triggers @mcp.tool registration
from sources.models.platform import (
    PlatformClearRegisteredInput,
    PlatformGetConnectionStateInput,
    PlatformGetInfoInput,
    PlatformListInterfacesInput,
    PlatformRemoveInput,
    PlatformType,
)
from sources.tools.platform.management import (
    platform_clear_registered,
    platform_get_connection_state,
    platform_get_info,
    platform_list,
    platform_list_interfaces,
    platform_remove,
)

pytestmark = pytest.mark.product

# Settle time not required for platform tools (no window state transitions).

# Name of the XCPonCAN platform expected to exist in the active experiment.
# Override via pytest marker or environment if needed.
_XCP_PLATFORM_NAME = "XCP"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ok(raw: str) -> dict:
    """Parse tool JSON and assert it is not an error envelope."""
    data = json.loads(raw)
    assert "error_code" not in data, f"Tool returned error envelope: {data}"
    return data


def _error(raw: str) -> dict:
    """Parse tool JSON and assert it IS an error envelope."""
    data = json.loads(raw)
    assert "error_code" in data, f"Expected error envelope but got: {data}"
    return data


# ── platform_list ─────────────────────────────────────────────────────────────


class TestPlatformList:
    async def test_returns_list_with_count(self) -> None:
        """platform_list returns a non-error response with 'platforms' and 'count'."""
        raw = await platform_list()
        data = _ok(raw)
        assert "platforms" in data
        assert "count" in data
        assert isinstance(data["platforms"], list)
        assert data["count"] == len(data["platforms"])

    async def test_each_platform_has_required_fields(self) -> None:
        """Every platform entry has the minimum required fields."""
        raw = await platform_list()
        data = _ok(raw)
        for plat in data["platforms"]:
            assert "name" in plat, f"Missing 'name' in platform entry: {plat}"
            assert "type" in plat, f"Missing 'type' in platform entry: {plat}"
            assert (
                "connection_state" in plat
            ), f"Missing 'connection_state' in platform entry: {plat}"
            assert (
                "measurement_state" in plat
            ), f"Missing 'measurement_state' in platform entry: {plat}"
            assert (
                "variable_description_count" in plat
            ), f"Missing 'variable_description_count' in: {plat}"

    async def test_platform_types_are_known_values(self) -> None:
        """All returned platform types match valid PlatformType enum values."""
        known_types = {e.value for e in PlatformType}
        raw = await platform_list()
        data = _ok(raw)
        for plat in data["platforms"]:
            plat_type = plat["type"]
            assert plat_type in known_types, (
                f"Platform '{plat['name']}' has unknown type '{plat_type}'. "
                f"Known types: {sorted(known_types)}"
            )


# ── platform_get_info ─────────────────────────────────────────────────────────


class TestPlatformGetInfo:
    async def test_get_info_for_existing_platform(self) -> None:
        """platform_get_info returns metadata for the first platform in the experiment."""
        list_raw = await platform_list()
        list_data = _ok(list_raw)
        if not list_data["platforms"]:
            pytest.skip("No platforms in the active experiment.")
        first_name = list_data["platforms"][0]["name"]

        raw = await platform_get_info(PlatformGetInfoInput(platform_name=first_name))
        data = _ok(raw)
        assert data["name"] == first_name
        assert "type" in data
        assert "connection_state" in data
        assert "measurement_state" in data

    async def test_get_info_for_missing_platform_returns_error(self) -> None:
        """platform_get_info returns an error envelope for an unknown platform name."""
        raw = await platform_get_info(PlatformGetInfoInput(platform_name="_nonexistent_platform_"))
        _error(raw)


# ── platform_get_connection_state ─────────────────────────────────────────────


class TestPlatformGetConnectionState:
    async def test_returns_connection_state_for_existing_platform(self) -> None:
        """platform_get_connection_state returns a known state string."""
        list_raw = await platform_list()
        list_data = _ok(list_raw)
        if not list_data["platforms"]:
            pytest.skip("No platforms in the active experiment.")
        first_name = list_data["platforms"][0]["name"]

        raw = await platform_get_connection_state(
            PlatformGetConnectionStateInput(platform_name=first_name)
        )
        data = _ok(raw)
        assert data["connection_state"] in {
            "Connected",
            "Disconnected",
            "Connecting",
            "Disconnecting",
        }
        assert isinstance(data["is_connected"], bool)
        assert data["platform_name"] == first_name

    async def test_returns_error_for_missing_platform(self) -> None:
        raw = await platform_get_connection_state(
            PlatformGetConnectionStateInput(platform_name="_nonexistent_platform_")
        )
        _error(raw)


# ── platform_list_interfaces ──────────────────────────────────────────────────


class TestPlatformListInterfaces:
    async def test_returns_vendors_for_xcp_platform(self) -> None:
        """platform_list_interfaces returns vendor/interface/channel data for XCPonCAN."""
        # Find a CAN-capable platform in the experiment
        list_raw = await platform_list()
        list_data = _ok(list_raw)
        can_types = {"XCPonCAN", "CANMonitoring", "LINMonitoring", "FlexRayMonitoring", "CCP"}
        can_platform = next((p for p in list_data["platforms"] if p["type"] in can_types), None)
        if can_platform is None:
            pytest.skip("No CAN-bus platform in the active experiment.")

        raw = await platform_list_interfaces(
            PlatformListInterfacesInput(platform_name=can_platform["name"])
        )
        data = _ok(raw)
        assert "vendors" in data
        assert isinstance(data["vendors"], list)
        if data["vendors"]:
            vendor = data["vendors"][0]
            assert "vendor_name" in vendor
            assert "interfaces" in vendor
            if vendor["interfaces"]:
                iface = vendor["interfaces"][0]
                assert "interface_name" in iface
                assert "channel_count" in iface

    async def test_returns_error_for_hardware_platform(self) -> None:
        """platform_list_interfaces returns error for hardware (SCALEXIO) platform."""
        list_raw = await platform_list()
        list_data = _ok(list_raw)
        hw_types = {"SCALEXIO", "DS1202", "DS1203", "DS1403", "MABX", "VEOS"}
        hw_platform = next((p for p in list_data["platforms"] if p["type"] in hw_types), None)
        if hw_platform is None:
            pytest.skip("No hardware platform in the active experiment.")

        raw = await platform_list_interfaces(
            PlatformListInterfacesInput(platform_name=hw_platform["name"])
        )
        _error(raw)

    async def test_returns_error_for_ethernet_monitoring(self) -> None:
        """platform_list_interfaces returns error for EthernetMonitoring (not CAN-bus)."""
        list_raw = await platform_list()
        list_data = _ok(list_raw)
        eth_platform = next(
            (p for p in list_data["platforms"] if p["type"] == "EthernetMonitoring"), None
        )
        if eth_platform is None:
            pytest.skip("No EthernetMonitoring platform in the active experiment.")

        raw = await platform_list_interfaces(
            PlatformListInterfacesInput(platform_name=eth_platform["name"])
        )
        _error(raw)


# ── platform_clear_registered (safety guard only) ─────────────────────────────


class TestPlatformClearRegisteredGuard:
    async def test_confirm_false_is_safe_no_op(self) -> None:
        """platform_clear_registered with confirm=False returns"""
        """cleared=False without modifying state."""
        raw = await platform_clear_registered(PlatformClearRegisteredInput(confirm=False))
        data = _ok(raw)
        assert data["cleared"] is False
        assert "message" in data


# ── platform_remove (error path only — don't mutate live experiment) ──────────


class TestPlatformRemoveErrorPath:
    async def test_returns_error_for_missing_platform(self) -> None:
        """platform_remove returns an error envelope when the platform does not exist."""

        raw = await platform_remove(PlatformRemoveInput(platform_name="_nonexistent_platform_"))
        _error(raw)
