"""COM bridge exception hierarchy.

All exceptions raised inside the com_bridge package are subclasses of BridgeError.
"""

from __future__ import annotations


class BridgeError(Exception):
    """Base class for all COM bridge errors."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "BRIDGE_ERROR",
        retryable: bool = False,
        recovery_hint: str = "",
        hresult: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.retryable = retryable
        self.recovery_hint = recovery_hint
        self.hresult = hresult
        self.correlation_id: str = ""


class BridgeConnectionError(BridgeError):
    """ControlDesk is not running or the COM connection is lost."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "COM_DISCONNECTED",
        retryable: bool = True,
        recovery_hint: str = "Ensure ControlDesk is running, then retry.",
        hresult: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )


class BridgeTimeoutError(BridgeError):
    """A COM method call exceeded the configured timeout."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "COM_TIMEOUT",
        retryable: bool = True,
        recovery_hint: str = "Retry after a short delay.",
        hresult: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )


class BridgeNotInstalledError(BridgeError):
    """No ControlDesk installation was found in the Windows Registry."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "BRIDGE_NOT_INSTALLED",
        retryable: bool = False,
        recovery_hint: str = ("Install ControlDesk or set the CONTROLDESK_VERSION environment variable."),
        hresult: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )


class BridgeVersionError(BridgeError):
    """The running ControlDesk version does not match the resolved ProgID."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "COM_VERSION_MISMATCH",
        retryable: bool = False,
        recovery_hint: str = ("Verify the ControlDesk version or clear CONTROLDESK_VERSION to auto-detect."),
        hresult: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )


class BridgeOperationError(BridgeError):
    """A COM operation failed for a domain-specific reason."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "BRIDGE_OPERATION_ERROR",
        retryable: bool = False,
        recovery_hint: str = "",
        hresult: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )


class BridgeUiBlockedError(BridgeError):
    """COM call rejected because ControlDesk is showing a modal dialog (STA busy)."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "COM_UI_BLOCKING",
        retryable: bool = True,
        recovery_hint: str = (
            "Dismiss the open ControlDesk dialog, or set "
            "Platform.DisplayStatusInformation = False before long operations."
        ),
        hresult: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )


class BridgePreconditionError(BridgeError):
    """A required domain-state precondition was not met before the COM call."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "BRIDGE_PRECONDITION",
        retryable: bool = False,
        recovery_hint: str = "",
        hresult: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )


class BridgeCircuitOpenError(BridgeError):
    """Circuit breaker is OPEN — the operation has exceeded the failure threshold."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "CIRCUIT_OPEN",
        retryable: bool = True,
        recovery_hint: str = ("Wait 30 s and retry, or call controldesk_app_start_or_attach to reset the connection."),
        hresult: int | None = None,
    ) -> None:
        super().__init__(
            message,
            error_code=error_code,
            retryable=retryable,
            recovery_hint=recovery_hint,
            hresult=hresult,
        )
