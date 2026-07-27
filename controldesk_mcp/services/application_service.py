"""Service facade for ControlDesk application lifecycle operations.

Owns: orchestration of multi-step app startup, window management, and teardown.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError, BridgeNotInstalledError
from controldesk_mcp.config.settings import get_settings
from controldesk_mcp.models.application import (
    AppGetLogsInput,
    AppGetLogsResult,
    AppGetWindowStateResult,
    AppGetWindowVisibilityResult,
    AppLogFileEntry,
    AppQuitInput,
    AppQuitResult,
    AppSetFullscreenInput,
    AppSetFullscreenResult,
    AppSetWindowPositionInput,
    AppSetWindowPositionResult,
    AppSetWindowStateInput,
    AppSetWindowStateResult,
    AppSetWindowVisibleInput,
    AppSetWindowVisibleResult,
    AppStartOrAttachInput,
    AppStartOrAttachResult,
    AppVersionConfirmationRequired,
)
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _to_utc_timestamp(epoch_seconds: float) -> str:
    return (
        datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _discover_candidate_log_folders() -> list[Path]:
    """Return candidate ControlDesk log folders under LOCALAPPDATA.

    ControlDesk stores logs under a user settings path + "Log". The exact user
    settings path can vary by installation/profile, so this function uses a
    bounded search under LOCALAPPDATA\\dSPACE and prioritizes common paths.
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return []

    root = Path(local_app_data)
    dspace_root = root / "dSPACE"
    seen: set[str] = set()
    results: list[Path] = []

    def _add(path: Path) -> None:
        key = str(path)
        if key not in seen:
            seen.add(key)
            results.append(path)

    # Common direct locations.
    _add(dspace_root / "ControlDesk" / "Log")
    _add(dspace_root / "ControlDeskNG" / "Log")

    # Bounded recursive search only under dSPACE to avoid scanning full AppData.
    if dspace_root.exists():
        for log_dir in dspace_root.rglob("Log"):
            if not log_dir.is_dir():
                continue
            if any("controldesk" in part.lower() for part in log_dir.parts):
                _add(log_dir)

    return results


def _collect_log_files(log_folders: list[Path]) -> tuple[list[Path], list[dict[str, object]]]:
    """Collect ControlDesk*.log files from existing folders."""
    existing_folders: list[Path] = []
    rows: list[dict[str, object]] = []

    for folder in log_folders:
        if not folder.exists() or not folder.is_dir():
            continue
        existing_folders.append(folder)
        for file_path in folder.glob("ControlDesk*.log"):
            if not file_path.is_file():
                continue
            stat = file_path.stat()
            rows.append(
                {
                    "path": file_path,
                    "name": file_path.name,
                    "size_bytes": int(stat.st_size),
                    "mtime": float(stat.st_mtime),
                }
            )

    return existing_folders, rows


async def start_or_attach(
    params: AppStartOrAttachInput,
) -> AppVersionConfirmationRequired | AppStartOrAttachResult | ErrorEnvelope:
    """Launch or attach to a ControlDesk instance."""
    cfg = get_settings()
    version = params.controldesk_version or cfg.controldesk_version
    try:
        if version:
            version = com_bridge.normalize_user_version(version)

        if version:
            if not com_bridge.is_version_installed(version):
                raise BridgeNotInstalledError(
                    f"ControlDesk version '{version}' is not installed on this machine. "
                    "Install the requested version or omit controldesk_version to "
                    "auto-detect the latest installed version.",
                    recovery_hint=(
                        f"Install ControlDesk {version}, or leave controldesk_version "
                        "empty to use the latest available version."
                    ),
                )

            running_version = com_bridge.get_connected_version()
            if running_version and running_version.upper() != version.upper():
                if not params.force_version_switch:
                    return AppVersionConfirmationRequired(
                        running_version=running_version,
                        requested_version=version,
                        message=(
                            f"ControlDesk {running_version} is currently running. "
                            f"To switch to version {version}, ControlDesk "
                            f"{running_version} must be closed first. "
                            "Set force_version_switch=True to confirm the switch."
                        ),
                        timestamp_utc=_now_utc(),
                    )

                _log.info("Version switch confirmed: %s → %s", running_version, version)
                conn = com_bridge.get_connection()
                app = await com_bridge.dispatch(conn.get_app)
                await com_bridge.dispatch(com_bridge.domains.application_com.quit_application, app)
                await com_bridge.disconnect_for_switch()

        is_new = await com_bridge.ensure_connected(version)
        launched_at: str | None = _now_utc() if is_new else None
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)

        if params.make_visible:
            launch_timeout_s = cfg.com_launch_timeout_ms / 1000.0
            await com_bridge.dispatch(
                com_bridge.domains.application_com.show_window,
                app,
                launch_timeout_s,
                timeout_ms=cfg.com_launch_timeout_ms + 5_000,
            )
            if params.initial_window_state.value != "Normal":
                await com_bridge.dispatch(
                    com_bridge.domains.application_com.set_window_state,
                    app,
                    params.initial_window_state.value,
                )

        cd_version = await com_bridge.dispatch(com_bridge.domains.application_com.get_version, app)
        return AppStartOrAttachResult(
            action="launched" if is_new else "attached",
            is_new_instance=is_new,
            controldesk_version=cd_version,
            window_visible=params.make_visible,
            window_state=params.initial_window_state.value,
            launched_at_utc=launched_at,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def dry_run_start_or_attach(
    params: AppStartOrAttachInput,
) -> DryRunPreviewResult | ErrorEnvelope:
    """Preview start_controldesk without changing the running instance."""
    from controldesk_mcp.services import project_service

    cfg = get_settings()
    version = params.controldesk_version or cfg.controldesk_version

    try:
        if version:
            version = com_bridge.normalize_user_version(version)

        if version and not com_bridge.is_version_installed(version):
            raise BridgeNotInstalledError(
                f"ControlDesk version '{version}' is not installed on this machine. "
                "Install the requested version or omit controldesk_version to "
                "auto-detect the latest installed version.",
                recovery_hint=(
                    f"Install ControlDesk {version}, or leave controldesk_version "
                    "empty to use the latest available version."
                ),
            )

        running_version = com_bridge.get_connected_version()
        version_switch_required = bool(
            version and running_version and running_version.upper() != version.upper()
        )

        current_state: dict[str, object] = {
            "requested_version": version or "",
            "running_version": running_version or "",
            "version_switch_required": version_switch_required,
            "force_version_switch": params.force_version_switch,
            "make_visible": params.make_visible,
            "initial_window_state": params.initial_window_state.value,
        }

        if not version_switch_required:
            message = (
                f"No version switch is required — start_controldesk would connect to ControlDesk {running_version}."
                if running_version
                else (
                    "No ControlDesk instance is currently running — start_controldesk would launch or attach "
                    "without quitting anything."
                )
            )
            return DryRunPreviewResult(
                tool="start_controldesk",
                action="start_or_attach",
                target=version or running_version or "ControlDesk",
                would_execute=True,
                current_state=current_state,
                message=message,
            )

        info_result = await project_service.project_get_info()
        if isinstance(info_result, ErrorEnvelope):
            current_state["project_open"] = False
            message = (
                f"ControlDesk {running_version} is running and would need to be quit before switching to {version}. "
                "No open project information is available, so no unsaved project changes were detected in the preview."
            )
        else:
            current_state.update(
                {
                    "project_open": True,
                    "project_name": info_result.name,
                    "is_modified": info_result.is_modified,
                }
            )
            message = (
                f"ControlDesk {running_version} is running and would need to be quit before switching to {version}. "
                + (
                    f"Project '{info_result.name}' has unsaved changes that would be discarded by the forced switch."
                    if info_result.is_modified
                    else f"Project '{info_result.name}' has no unsaved changes."
                )
            )

        return DryRunPreviewResult(
            tool="start_controldesk",
            action="start_or_attach",
            target=version,
            would_execute=params.force_version_switch,
            current_state=current_state,
            message=message,
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def set_window_visible(
    params: AppSetWindowVisibleInput,
) -> AppSetWindowVisibleResult | ErrorEnvelope:
    """Show or hide the ControlDesk main window."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        await com_bridge.dispatch(
            com_bridge.domains.application_com.set_window_visible, app, params.visible
        )
        return AppSetWindowVisibleResult(
            is_now_visible=params.visible,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def get_window_visibility() -> AppGetWindowVisibilityResult | ErrorEnvelope:
    """Query main window visibility state."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        visible = await com_bridge.dispatch(
            com_bridge.domains.application_com.get_window_visible, app
        )
        return AppGetWindowVisibilityResult(
            is_visible=visible,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def set_window_state(
    params: AppSetWindowStateInput,
) -> AppSetWindowStateResult | ErrorEnvelope:
    """Set window display state (Normal / Maximized / Minimized / Hidden)."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        await com_bridge.dispatch(
            com_bridge.domains.application_com.set_window_state, app, params.window_state.value
        )
        return AppSetWindowStateResult(
            window_state=params.window_state.value,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def get_window_state() -> AppGetWindowStateResult | ErrorEnvelope:
    """Query current window display state and visibility."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        state = await com_bridge.dispatch(com_bridge.domains.application_com.get_window_state, app)
        visible = await com_bridge.dispatch(
            com_bridge.domains.application_com.get_window_visible, app
        )
        return AppGetWindowStateResult(
            window_state=state,
            is_visible=visible,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def quit_application(params: AppQuitInput) -> AppQuitResult | ErrorEnvelope:  # noqa: ARG001
    """Gracefully shut down ControlDesk."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        await com_bridge.dispatch(com_bridge.domains.application_com.quit_application, app)
        _log.info("ControlDesk quit command sent successfully")
        return AppQuitResult(timestamp_utc=_now_utc())
    except BridgeError as exc:
        return build_envelope(exc)


async def dry_run_quit_application(
    params: AppQuitInput,
) -> DryRunPreviewResult | ErrorEnvelope:
    """Preview stop_controldesk without quitting anything.

    Checks whether the active project has unsaved changes (a safe, read-only
    COM call) and reports the impact of save_all_projects, without sending
    the quit command.
    """
    from controldesk_mcp.services import project_service

    info_result = await project_service.project_get_info()
    if isinstance(info_result, ErrorEnvelope):
        # No project open (or not connected) — quitting has nothing to save/discard.
        return DryRunPreviewResult(
            tool="stop_controldesk",
            action="quit",
            target="ControlDesk",
            would_execute=True,
            current_state={"project_open": False},
            message="No project is currently open — ControlDesk would quit with nothing to save.",
        )
    is_modified = info_result.is_modified
    would_lose_changes = is_modified and not params.save_all_projects
    return DryRunPreviewResult(
        tool="stop_controldesk",
        action="quit",
        target=info_result.name,
        would_execute=True,
        current_state={"project_name": info_result.name, "is_modified": is_modified},
        message=(
            f"Project '{info_result.name}' has unsaved changes and save_all_projects=False "
            "— those changes would be discarded on quit."
            if would_lose_changes
            else f"Project '{info_result.name}' "
            + (
                "has unsaved changes and would be saved before quitting."
                if is_modified
                else "has no unsaved changes — ControlDesk would quit cleanly."
            )
        ),
    )


async def set_window_position(
    params: AppSetWindowPositionInput,
) -> AppSetWindowPositionResult | ErrorEnvelope:
    """Set window position and size in pixels."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        await com_bridge.dispatch(
            com_bridge.domains.application_com.set_window_position,
            app,
            params.left,
            params.top,
            params.width,
            params.height,
        )
        return AppSetWindowPositionResult(
            left=params.left,
            top=params.top,
            width=params.width,
            height=params.height,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def set_fullscreen(params: AppSetFullscreenInput) -> AppSetFullscreenResult | ErrorEnvelope:
    """Enable or disable full-screen mode."""
    try:
        conn = com_bridge.get_connection()
        app = await com_bridge.dispatch(conn.get_app)
        await com_bridge.dispatch(
            com_bridge.domains.application_com.set_fullscreen, app, params.enabled
        )
        return AppSetFullscreenResult(
            fullscreen_enabled=params.enabled,
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        return build_envelope(exc)


async def get_logs(params: AppGetLogsInput) -> AppGetLogsResult | ErrorEnvelope:
    """Return available ControlDesk application log file paths.

    This function intentionally does not depend on COM so diagnostics remain
    available even when ControlDesk is not running or has crashed.
    """
    try:
        candidate_folders: list[Path] = []
        if params.log_folder_override:
            candidate_folders.append(Path(params.log_folder_override))

        candidate_folders.extend(_discover_candidate_log_folders())
        existing_folders, rows = _collect_log_files(candidate_folders)

        rows.sort(key=lambda item: item["mtime"], reverse=params.newest_first)
        rows = rows[: params.limit]

        files = [
            AppLogFileEntry(
                path=str(item["path"]),
                name=str(item["name"]),
                size_bytes=int(item["size_bytes"]),
                last_write_time_utc=_to_utc_timestamp(float(item["mtime"])),
            )
            for item in rows
        ]

        return AppGetLogsResult(
            file_pattern="ControlDesk*.log",
            searched_folders=[str(path) for path in candidate_folders],
            resolved_log_folders=[str(path) for path in existing_folders],
            files=files,
            total_found=len(files),
            timestamp_utc=_now_utc(),
        )
    except OSError as exc:
        _log.exception("Failed to enumerate ControlDesk log files")
        return ErrorEnvelope(
            error_code="LOG_ENUMERATION_FAILED",
            category="OPERATION",
            message=f"Failed to enumerate ControlDesk log files: {exc}",
            retryable=False,
            recovery_hint=(
                "Verify that the configured log folder exists and is readable, "
                "or pass log_folder_override to app_get_logs."
            ),
        )
