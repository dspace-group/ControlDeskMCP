"""Unit tests for sources.com_bridge.error_handling.preconditions."""

from __future__ import annotations

import struct
from unittest.mock import patch

import pytest

from sources.com_bridge.error_handling.preconditions import (
    check_64bit_process,
    check_calibration_started,
    check_experiment_active,
    check_measurement_not_active,
    check_platform_connected,
)
from sources.com_bridge.errors import BridgePreconditionError


class TestCheckExperimentActive:
    def test_raises_when_not_active(self) -> None:
        with pytest.raises(BridgePreconditionError) as exc_info:
            check_experiment_active(False)
        assert exc_info.value.error_code == "BRIDGE_NO_EXPERIMENT"
        assert exc_info.value.retryable is False

    def test_does_not_raise_when_active(self) -> None:
        check_experiment_active(True)  # must not raise

    def test_recovery_hint_references_tool(self) -> None:
        with pytest.raises(BridgePreconditionError) as exc_info:
            check_experiment_active(False)
        assert "experiment_load_and_activate" in exc_info.value.recovery_hint


class TestCheckPlatformConnected:
    def test_raises_when_disconnected(self) -> None:
        with pytest.raises(BridgePreconditionError) as exc_info:
            check_platform_connected(False)
        assert exc_info.value.error_code == "BRIDGE_PLATFORM_DISCONNECTED"
        assert exc_info.value.retryable is False

    def test_does_not_raise_when_connected(self) -> None:
        check_platform_connected(True)  # must not raise

    def test_recovery_hint_references_tool(self) -> None:
        with pytest.raises(BridgePreconditionError) as exc_info:
            check_platform_connected(False)
        assert "platform_connect" in exc_info.value.recovery_hint


class TestCheckMeasurementNotActive:
    def test_raises_when_running(self) -> None:
        with pytest.raises(BridgePreconditionError) as exc_info:
            check_measurement_not_active(True)
        assert exc_info.value.error_code == "BRIDGE_MEASUREMENT_ACTIVE"
        assert exc_info.value.retryable is False

    def test_does_not_raise_when_not_running(self) -> None:
        check_measurement_not_active(False)  # must not raise

    def test_recovery_hint_instructs_to_stop(self) -> None:
        with pytest.raises(BridgePreconditionError) as exc_info:
            check_measurement_not_active(True)
        assert "Stop" in exc_info.value.recovery_hint or "stop" in exc_info.value.recovery_hint


class TestCheckCalibrationStarted:
    def test_raises_when_not_started(self) -> None:
        with pytest.raises(BridgePreconditionError) as exc_info:
            check_calibration_started(False)
        assert exc_info.value.error_code == "BRIDGE_CALIBRATION_NOT_STARTED"
        assert exc_info.value.retryable is False

    def test_does_not_raise_when_started(self) -> None:
        check_calibration_started(True)  # must not raise

    def test_recovery_hint_references_tool(self) -> None:
        with pytest.raises(BridgePreconditionError) as exc_info:
            check_calibration_started(False)
        assert "calibration_start" in exc_info.value.recovery_hint


class TestCheck64BitProcess:
    def test_raises_when_32bit_process(self) -> None:
        # Patch calcsize to simulate a 32-bit pointer (4 bytes)
        with (
            patch("sources.com_bridge.error_handling.preconditions.struct") as mock_struct,
            patch("sources.com_bridge.error_handling.preconditions.sys") as mock_sys,
        ):
            mock_struct.calcsize.return_value = 4
            mock_sys.maxsize = 2**31 - 1
            with pytest.raises(BridgePreconditionError) as exc_info:
                check_64bit_process()
        assert exc_info.value.error_code == "BRIDGE_WRONG_BITNESS"
        assert exc_info.value.retryable is False

    def test_does_not_raise_on_64bit_process(self) -> None:
        # Verify the check passes on the actual test runner (which must be 64-bit)
        assert struct.calcsize("P") == 8, "Tests must run on a 64-bit Python"
        check_64bit_process()  # must not raise

    def test_recovery_hint_references_64bit(self) -> None:
        with (
            patch("sources.com_bridge.error_handling.preconditions.struct") as mock_struct,
            patch("sources.com_bridge.error_handling.preconditions.sys") as mock_sys,
        ):
            mock_struct.calcsize.return_value = 4
            mock_sys.maxsize = 2**31 - 1
            with pytest.raises(BridgePreconditionError) as exc_info:
                check_64bit_process()
        assert "64-bit" in exc_info.value.recovery_hint
