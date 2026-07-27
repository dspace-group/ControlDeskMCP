"""Domain-state precondition checks run before any COM call.

These are explicit, non-COM checks that verify the required server state is in
place before dispatching to ControlDesk.  They are not COM errors — wrapping
them in HRESULT classification would lose context.

Error codes produced:
    BRIDGE_NO_EXPERIMENT           — no active experiment loaded
    BRIDGE_PLATFORM_DISCONNECTED   — platform not connected
    BRIDGE_MEASUREMENT_ACTIVE      — measurement already running
    BRIDGE_CALIBRATION_NOT_STARTED — calibration session not active
    BRIDGE_WRONG_BITNESS           — Python process is 32-bit

Each function raises :class:`BridgePreconditionError` on failure and returns
``None`` on success, so callers can chain checks without boilerplate.
"""

from __future__ import annotations

import struct
import sys

from controldesk_mcp.com_bridge.errors import BridgePreconditionError


def check_experiment_active(is_active: bool) -> None:
    """Raise if no experiment is loaded and activated.

    Args:
        is_active: ``True`` when ``Application.ActiveExperiment`` is not ``None``.

    Raises:
        BridgePreconditionError: error_code ``BRIDGE_NO_EXPERIMENT``
    """
    if not is_active:
        raise BridgePreconditionError(
            "No active experiment. Load and activate an experiment first.",
            error_code="BRIDGE_NO_EXPERIMENT",
            recovery_hint="Call experiment_load_and_activate.",
        )


def check_platform_connected(is_connected: bool) -> None:
    """Raise if the platform is not connected.

    Args:
        is_connected: ``True`` when the platform is online.

    Raises:
        BridgePreconditionError: error_code ``BRIDGE_PLATFORM_DISCONNECTED``
    """
    if not is_connected:
        raise BridgePreconditionError(
            "Platform is not connected. Connect the platform before performing this operation.",
            error_code="BRIDGE_PLATFORM_DISCONNECTED",
            recovery_hint="Call platform_connect.",
        )


def check_measurement_not_active(is_running: bool) -> None:
    """Raise if a measurement is already running.

    Args:
        is_running: ``True`` when a measurement session is currently active.

    Raises:
        BridgePreconditionError: error_code ``BRIDGE_MEASUREMENT_ACTIVE``
    """
    if is_running:
        raise BridgePreconditionError(
            "A measurement is already running. Stop the current measurement first.",
            error_code="BRIDGE_MEASUREMENT_ACTIVE",
            recovery_hint="Stop measurement first.",
        )


def check_calibration_started(is_started: bool) -> None:
    """Raise if a calibration session is not active.

    Args:
        is_started: ``True`` when a calibration session is active.

    Raises:
        BridgePreconditionError: error_code ``BRIDGE_CALIBRATION_NOT_STARTED``
    """
    if not is_started:
        raise BridgePreconditionError(
            "Calibration session is not active. Start calibration before performing this operation.",
            error_code="BRIDGE_CALIBRATION_NOT_STARTED",
            recovery_hint="Call calibration_start.",
        )


def check_64bit_process() -> None:
    """Raise if the current Python process is 32-bit.

    ControlDesk COM automation requires a 64-bit Python process.

    Raises:
        BridgePreconditionError: error_code ``BRIDGE_WRONG_BITNESS``
    """
    if struct.calcsize("P") != 8 or sys.maxsize <= 2**32:
        raise BridgePreconditionError(
            "The MCP server is running as a 32-bit Python process. "
            "ControlDesk COM automation requires a 64-bit Python interpreter.",
            error_code="BRIDGE_WRONG_BITNESS",
            recovery_hint="Use a 64-bit Python installation.",
        )
