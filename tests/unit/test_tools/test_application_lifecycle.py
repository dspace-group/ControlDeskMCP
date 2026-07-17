"""Unit tests for sources.tools.application.lifecycle (consolidated tools)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sources.com_bridge as bridge
from sources.com_bridge.domains import application_com
from sources.com_bridge.errors import BridgeConnectionError
from sources.models.application import (
    AppGetLogsInput,
    AppStartOrAttachInput,
    AppWindowManageAction,
    AppWindowManageInput,
    MainWindowState,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_bridge():
    """Reset the com_bridge singleton before and after each test."""
    bridge._connection = None
    import sources.com_bridge.sta_thread as _sta

    _sta._sta_thread = None
    yield
    bridge._connection = None
    _sta._sta_thread = None


def _make_connected_bridge(
    version: str = "2026-A",
    prog_id: str = "ControlDeskNG.Application.2026-A",
) -> MagicMock:
    """Return a mock ComConnection in CONNECTED state."""
    from sources.com_bridge.connection import ConnectionState

    conn = MagicMock()
    conn.state = ConnectionState.CONNECTED
    conn.get_app.return_value = MagicMock()
    conn.health.return_value = {"connected": True, "state": "CONNECTED", "prog_id": prog_id}
    bridge._connection = conn
    return conn


def _default_cfg(**overrides):
    cfg = MagicMock()
    cfg.controldesk_version = overrides.get("controldesk_version", "")
    cfg.com_launch_timeout_ms = overrides.get("com_launch_timeout_ms", 30_000)
    return cfg


# ── start_controldesk ────────────────────────────────────────────────────────


class TestAppStartOrAttach:
    @pytest.mark.asyncio
    async def test_returns_attached_true_when_already_connected(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch(
                "sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=False
            ),
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None, "2026-A"],
            ),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(AppStartOrAttachInput())

        assert result["status"] == "ok"
        assert result["action"] == "attached"
        assert result["is_new_instance"] is False
        assert result["controldesk_version"] == "2026-A"
        assert result["window_visible"] is True
        assert result["launched_at_utc"] is None
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_is_new_instance_true_when_launched(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=True),
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None, "2026-A"],
            ),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(AppStartOrAttachInput())

        assert result["is_new_instance"] is True
        assert result["launched_at_utc"] is not None

    @pytest.mark.asyncio
    async def test_make_visible_false_skips_show_window(self) -> None:
        conn = _make_connected_bridge()
        dispatched_fns: list = []

        async def _capture(fn, *args, **kwargs):
            dispatched_fns.append(fn)
            if fn == application_com.get_version:
                return "2026-A"
            return None

        with (
            patch(
                "sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=False
            ),
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch("sources.com_bridge.dispatch", side_effect=_capture),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(AppStartOrAttachInput(make_visible=False))

        assert result["window_visible"] is False
        assert application_com.show_window not in dispatched_fns

    @pytest.mark.asyncio
    async def test_initial_window_state_maximized_calls_set_state(self) -> None:
        conn = _make_connected_bridge()
        dispatched_fns: list = []

        async def _capture(fn, *args, **kwargs):
            dispatched_fns.append(fn)
            if fn == application_com.get_version:
                return "2026-A"
            return None

        with (
            patch(
                "sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=False
            ),
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch("sources.com_bridge.dispatch", side_effect=_capture),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(
                AppStartOrAttachInput(initial_window_state=MainWindowState.Maximized)
            )

        assert result["window_state"] == "Maximized"
        assert application_com.set_window_state in dispatched_fns

    @pytest.mark.asyncio
    async def test_controldesk_version_from_params_overrides_config(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch(
                "sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=False
            ) as mock_ensure,
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None, "2025-B"],
            ),
            patch(
                "sources.services.application_service.get_settings",
                return_value=_default_cfg(controldesk_version="2026-A"),
            ),
            patch("sources.com_bridge.is_version_installed", return_value=True),
            patch("sources.com_bridge.get_connected_version", return_value=""),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            await start_controldesk(AppStartOrAttachInput(controldesk_version="2025-B"))

        mock_ensure.assert_awaited_once_with("2025-B")

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_cd_error(self) -> None:
        with patch(
            "sources.com_bridge.ensure_connected",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("not running"),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(AppStartOrAttachInput())

        assert result["error_code"] == "COM_DISCONNECTED"
        assert result["retryable"] is True

    @pytest.mark.asyncio
    async def test_show_window_is_dispatched_when_make_visible_true(self) -> None:
        conn = _make_connected_bridge()
        dispatched_fns: list = []

        async def _capture(fn, *args, **kwargs):
            dispatched_fns.append(fn)
            if fn == application_com.get_version:
                return "2026-A"
            return None

        with (
            patch(
                "sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=False
            ),
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch("sources.com_bridge.dispatch", side_effect=_capture),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            await start_controldesk(AppStartOrAttachInput(make_visible=True))

        assert application_com.show_window in dispatched_fns

    @pytest.mark.asyncio
    async def test_version_not_installed_returns_error(self) -> None:
        """Requested version not in registry → CD_NOT_INSTALLED error envelope."""
        from sources.com_bridge.errors import BridgeNotInstalledError

        with (
            patch(
                "sources.com_bridge.normalize_user_version",
                side_effect=BridgeNotInstalledError("not installed"),
            ),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(AppStartOrAttachInput(controldesk_version="2024-A"))

        assert result["error_code"] == "BRIDGE_NOT_INSTALLED"

    @pytest.mark.asyncio
    async def test_year_only_version_normalised_and_launched(self) -> None:
        """'2026' is normalised to '2026-A' and the tool proceeds normally."""
        conn = _make_connected_bridge(version="2026-A")

        with (
            patch(
                "sources.com_bridge.normalize_user_version",
                return_value="2026-A",
            ),
            patch("sources.com_bridge.is_version_installed", return_value=True),
            patch("sources.com_bridge.get_connected_version", return_value=""),
            patch(
                "sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=True
            ) as mock_ensure,
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None, "2026-A"],
            ),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(AppStartOrAttachInput(controldesk_version="2026"))

        mock_ensure.assert_awaited_once_with("2026-A")
        assert result["status"] == "ok"
        assert result["controldesk_version"] == "2026-A"

    @pytest.mark.asyncio
    async def test_version_mismatch_returns_confirmation_required(self) -> None:
        """Different version already running without force flag → confirmation_required."""
        with (
            patch("sources.com_bridge.is_version_installed", return_value=True),
            patch("sources.com_bridge.get_connected_version", return_value="2026-A"),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(AppStartOrAttachInput(controldesk_version="2024-A"))

        assert result["status"] == "confirmation_required"
        assert result["running_version"] == "2026-A"
        assert result["requested_version"] == "2024-A"
        assert "force_version_switch" in result["message"]

    @pytest.mark.asyncio
    async def test_force_version_switch_quits_and_reconnects(self) -> None:
        """force_version_switch=True quits old instance and connects to new version."""
        conn = _make_connected_bridge(version="2026-A")
        dispatched_fns: list = []

        async def _capture(fn, *args, **kwargs):
            dispatched_fns.append(fn)
            if fn == application_com.get_version:
                return "2024-A"
            return MagicMock()

        with (
            patch("sources.com_bridge.is_version_installed", return_value=True),
            patch("sources.com_bridge.get_connected_version", return_value="2026-A"),
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch("sources.com_bridge.dispatch", side_effect=_capture),
            patch(
                "sources.com_bridge.disconnect_for_switch", new_callable=AsyncMock
            ) as mock_disconnect,
            patch(
                "sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=True
            ) as mock_ensure,
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(
                AppStartOrAttachInput(controldesk_version="2024-A", force_version_switch=True)
            )

        assert application_com.quit_application in dispatched_fns
        mock_disconnect.assert_awaited_once()
        mock_ensure.assert_awaited_once_with("2024-A")
        assert result["status"] == "ok"
        assert result["is_new_instance"] is True
        assert result["launched_at_utc"] is not None

    @pytest.mark.asyncio
    async def test_dry_run_delegates_to_preview_without_starting(self) -> None:
        from sources.models.base import DryRunPreviewResult

        preview = DryRunPreviewResult(
            tool="start_controldesk",
            action="start_or_attach",
            target="2024-A",
            would_execute=True,
            current_state={
                "requested_version": "2024-A",
                "running_version": "2026-A",
                "version_switch_required": True,
                "project_open": True,
                "project_name": "MyProject",
                "is_modified": True,
            },
            message=(
                "ControlDesk 2026-A is running and would need to be quit before switching to 2024-A. "
                "Project 'MyProject' has unsaved changes that would be discarded by the forced switch."
            ),
        )

        with (
            patch(
                "sources.services.application_service.dry_run_start_or_attach",
                new_callable=AsyncMock,
                return_value=preview,
            ) as mock_dry_run,
            patch(
                "sources.services.application_service.start_or_attach",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_start,
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(
                AppStartOrAttachInput(
                    controldesk_version="2024-A",
                    force_version_switch=True,
                    dry_run=True,
                )
            )

        assert isinstance(result, DryRunPreviewResult)
        assert result["tool"] == "start_controldesk"
        assert result["current_state"]["version_switch_required"] is True
        mock_dry_run.assert_awaited_once()
        mock_start.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_no_conflict_when_same_version_running(self) -> None:
        """Same version already connected → normal attach, no conflict path."""
        conn = _make_connected_bridge(version="2024-A")

        with (
            patch("sources.com_bridge.is_version_installed", return_value=True),
            patch("sources.com_bridge.get_connected_version", return_value="2024-A"),
            patch(
                "sources.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=False
            ),
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None, "2024-A"],
            ),
            patch("sources.services.application_service.get_settings", return_value=_default_cfg()),
        ):
            from sources.tools.application.lifecycle import start_controldesk

            result = await start_controldesk(AppStartOrAttachInput(controldesk_version="2024-A"))

        assert result["status"] == "ok"
        assert result["action"] == "attached"


# ── app_window_manage: set_visible ────────────────────────────────────────────


class TestAppSetWindowVisible:
    @pytest.mark.asyncio
    async def test_returns_visibility_set_true(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None],
            ),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.set_visible, visible=True)
            )

        assert result["visibility_set"] is True
        assert result["is_now_visible"] is True
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_cd_error(self) -> None:
        with patch(
            "sources.com_bridge.get_connection",
            side_effect=BridgeConnectionError("not connected"),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.set_visible, visible=True)
            )

        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_missing_visible_returns_error(self) -> None:
        from sources.tools.application.lifecycle import app_window_manage

        result = await app_window_manage(
            AppWindowManageInput(action=AppWindowManageAction.set_visible)
        )
        assert result["error_code"] == "MISSING_PARAM"


# ── app_window_manage: get_visibility ─────────────────────────────────────────


class TestAppGetWindowVisibility:
    @pytest.mark.asyncio
    async def test_returns_is_visible(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, True],
            ),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.get_visibility)
            )

        assert result["is_visible"] is True
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_cd_error(self) -> None:
        with patch(
            "sources.com_bridge.get_connection",
            side_effect=BridgeConnectionError("not connected"),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.get_visibility)
            )

        assert "error_code" in result


# ── app_window_manage: set_state ──────────────────────────────────────────────


class TestAppSetWindowState:
    @pytest.mark.asyncio
    async def test_returns_state_set(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None],
            ),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(
                    action=AppWindowManageAction.set_state,
                    window_state=MainWindowState.Maximized,
                )
            )

        assert result["state_set"] is True
        assert result["window_state"] == "Maximized"
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_cd_error(self) -> None:
        with patch(
            "sources.com_bridge.get_connection",
            side_effect=BridgeConnectionError("not connected"),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(
                    action=AppWindowManageAction.set_state,
                    window_state=MainWindowState.Normal,
                )
            )

        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_missing_window_state_returns_error(self) -> None:
        from sources.tools.application.lifecycle import app_window_manage

        result = await app_window_manage(
            AppWindowManageInput(action=AppWindowManageAction.set_state)
        )
        assert result["error_code"] == "MISSING_PARAM"


# ── app_window_manage: get_state ──────────────────────────────────────────────


class TestAppGetWindowState:
    @pytest.mark.asyncio
    async def test_returns_state_and_visibility(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, "Maximized", True],
            ),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.get_state)
            )

        assert result["window_state"] == "Maximized"
        assert result["is_visible"] is True
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_cd_error(self) -> None:
        with patch(
            "sources.com_bridge.get_connection",
            side_effect=BridgeConnectionError("not connected"),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.get_state)
            )

        assert "error_code" in result


# ── stop_controldesk ──────────────────────────────────────────────────────────────────


class TestAppQuit:
    @pytest.mark.asyncio
    async def test_returns_quit_true_on_success(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None],
            ),
        ):
            from sources.models.application import AppQuitInput
            from sources.tools.application.lifecycle import stop_controldesk

            result = await stop_controldesk(AppQuitInput())

        assert result["quit"] is True
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_envelope_when_not_connected(self) -> None:
        with patch(
            "sources.com_bridge.get_connection",
            side_effect=BridgeConnectionError("not connected"),
        ):
            from sources.models.application import AppQuitInput
            from sources.tools.application.lifecycle import stop_controldesk

            result = await stop_controldesk(AppQuitInput())

        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_dry_run_delegates_to_preview_without_quitting(self) -> None:
        from sources.models.application import AppQuitInput
        from sources.models.base import DryRunPreviewResult

        preview = DryRunPreviewResult(
            tool="stop_controldesk",
            action="quit",
            target="MyProject",
            would_execute=True,
            current_state={"project_name": "MyProject", "is_modified": False},
            message="Project 'MyProject' has no unsaved changes — ControlDesk would quit cleanly.",
        )
        with (
            patch(
                "sources.services.application_service.dry_run_quit_application",
                new_callable=AsyncMock,
                return_value=preview,
            ) as mock_dry_run,
            patch(
                "sources.services.application_service.quit_application",
                new_callable=AsyncMock,
                return_value=None,
            ) as mock_quit,
        ):
            from sources.tools.application.lifecycle import stop_controldesk

            result = await stop_controldesk(AppQuitInput(dry_run=True))

        assert isinstance(result, DryRunPreviewResult)
        assert result["would_execute"] is True
        mock_dry_run.assert_awaited_once()
        mock_quit.assert_not_awaited()


# ── app_get_logs ─────────────────────────────────────────────────────────────


class TestAppGetLogs:
    @pytest.mark.asyncio
    async def test_returns_log_entries_on_success(self) -> None:
        with patch(
            "sources.services.application_service.get_logs",
            new=AsyncMock(
                return_value={
                    "status": "ok",
                    "file_pattern": "ControlDesk*.log",
                    "searched_folders": ["C:\\Users\\u\\AppData\\Local\\dSPACE\\ControlDesk\\Log"],
                    "resolved_log_folders": [
                        "C:\\Users\\u\\AppData\\Local\\dSPACE\\ControlDesk\\Log"
                    ],
                    "files": [
                        {
                            "path": "C:\\Users\\u\\AppData\\Local\\dSPACE\\ControlDesk\\Log\\ControlDesk.20260702.log",
                            "name": "ControlDesk.20260702.log",
                            "size_bytes": 1234,
                            "last_write_time_utc": "2026-07-02T10:00:00.000Z",
                        }
                    ],
                    "total_found": 1,
                    "timestamp_utc": "2026-07-02T10:00:01.000Z",
                }
            ),
        ):
            from sources.tools.application.lifecycle import app_get_logs

            result = await app_get_logs(AppGetLogsInput())

        assert result["status"] == "ok"
        assert result["total_found"] == 1
        assert result["files"][0]["name"] == "ControlDesk.20260702.log"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with patch(
            "sources.services.application_service.get_logs",
            new=AsyncMock(
                return_value={
                    "error_code": "LOG_ENUMERATION_FAILED",
                    "category": "OPERATION",
                    "message": "Failed to enumerate ControlDesk log files",
                    "retryable": False,
                    "recovery_hint": "Verify log folder permissions.",
                }
            ),
        ):
            from sources.tools.application.lifecycle import app_get_logs

            result = await app_get_logs(AppGetLogsInput())

        assert result["error_code"] == "LOG_ENUMERATION_FAILED"


# ── app_window_manage: set_position ──────────────────────────────────────────


class TestAppSetWindowPosition:
    @pytest.mark.asyncio
    async def test_returns_positioned_with_geometry(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None],
            ),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(
                    action=AppWindowManageAction.set_position,
                    left=0,
                    top=0,
                    width=1920,
                    height=1080,
                )
            )

        assert result["positioned"] is True
        assert result["left"] == 0
        assert result["top"] == 0
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_cd_error(self) -> None:
        with patch(
            "sources.com_bridge.get_connection",
            side_effect=BridgeConnectionError("not connected"),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(
                    action=AppWindowManageAction.set_position,
                    left=0,
                    top=0,
                    width=800,
                    height=600,
                )
            )

        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_missing_height_returns_error(self) -> None:
        from sources.tools.application.lifecycle import app_window_manage

        result = await app_window_manage(
            AppWindowManageInput(
                action=AppWindowManageAction.set_position, left=0, top=0, width=800
            )
        )
        assert result["error_code"] == "MISSING_PARAM"


# ── app_window_manage: set_fullscreen ─────────────────────────────────────────


class TestAppSetFullscreen:
    @pytest.mark.asyncio
    async def test_enable_fullscreen_returns_correct_shape(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None],
            ),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.set_fullscreen, enabled=True)
            )

        assert result["fullscreen_set"] is True
        assert result["fullscreen_enabled"] is True
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_disable_fullscreen(self) -> None:
        conn = _make_connected_bridge()

        with (
            patch("sources.com_bridge.get_connection", return_value=conn),
            patch(
                "sources.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[conn.get_app.return_value, None],
            ),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.set_fullscreen, enabled=False)
            )

        assert result["fullscreen_enabled"] is False

    @pytest.mark.asyncio
    async def test_returns_error_on_cd_error(self) -> None:
        with patch(
            "sources.com_bridge.get_connection",
            side_effect=BridgeConnectionError("not connected"),
        ):
            from sources.tools.application.lifecycle import app_window_manage

            result = await app_window_manage(
                AppWindowManageInput(action=AppWindowManageAction.set_fullscreen, enabled=True)
            )

        assert "error_code" in result
