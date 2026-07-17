"""Models package."""

from sources.models.application import (
    AppGetLogsInput,
    AppQuitInput,
    AppSetFullscreenInput,
    AppSetWindowPositionInput,
    AppSetWindowStateInput,
    AppSetWindowVisibleInput,
    AppStartOrAttachInput,
    MainWindowState,
)
from sources.models.errors import ErrorEnvelope

__all__ = [
    "ErrorEnvelope",
    "MainWindowState",
    "AppStartOrAttachInput",
    "AppGetLogsInput",
    "AppSetWindowVisibleInput",
    "AppSetWindowStateInput",
    "AppQuitInput",
    "AppSetWindowPositionInput",
    "AppSetFullscreenInput",
]
