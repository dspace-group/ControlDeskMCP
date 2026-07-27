"""Unit tests for controldesk_mcp.services.application_service.

Tests mock com_bridge.dispatch and related bridge functions.
Service layer is tested in isolation from both the MCP tool layer and real COM.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeConnectionError, BridgeTimeoutError
from controldesk_mcp.models.application import (
    AppGetLogsInput,
    AppQuitInput,
    AppSetWindowVisibleInput,
    AppStartOrAttachInput,
)
from controldesk_mcp.models.base import DryRunPreviewResult
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.project import ProjectGetInfoResult

# ── Shared helpers ────────────────────────────────────────────────────────────


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


# ── start_or_attach ───────────────────────────────────────────────────────────


class TestStartOrAttach:
    @pytest.mark.asyncio
    async def test_returns_attached_result_on_existing_instance(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with (
            patch("controldesk_mcp.services.application_service.get_settings") as mock_cfg,
            patch(
                "controldesk_mcp.com_bridge.ensure_connected",
                new_callable=AsyncMock,
                return_value=False,
            ),
            patch("controldesk_mcp.com_bridge.get_connected_version", return_value="2026-A"),
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, "2026-A"],
            ),
        ):
            mock_cfg.return_value.controldesk_version = ""
            mock_cfg.return_value.com_launch_timeout_ms = 30_000
            from controldesk_mcp.services.application_service import start_or_attach

            result = await start_or_attach(AppStartOrAttachInput(make_visible=False))

        assert result["action"] == "attached"
        assert result["is_new_instance"] is False

    @pytest.mark.asyncio
    async def test_returns_error_envelope_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with (
            patch("controldesk_mcp.services.application_service.get_settings") as mock_cfg,
            patch(
                "controldesk_mcp.com_bridge.ensure_connected",
                new_callable=AsyncMock,
                side_effect=BridgeConnectionError("not connected"),
            ),
        ):
            mock_cfg.return_value.controldesk_version = ""
            mock_cfg.return_value.com_launch_timeout_ms = 30_000
            from controldesk_mcp.services.application_service import start_or_attach

            result = await start_or_attach(AppStartOrAttachInput(make_visible=False))

        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_returns_new_instance_on_launch(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with (
            patch("controldesk_mcp.services.application_service.get_settings") as mock_cfg,
            patch("controldesk_mcp.com_bridge.ensure_connected", new_callable=AsyncMock, return_value=True),
            patch("controldesk_mcp.com_bridge.get_connected_version", return_value=None),
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, "2026-A"],
            ),
        ):
            mock_cfg.return_value.controldesk_version = ""
            mock_cfg.return_value.com_launch_timeout_ms = 30_000
            from controldesk_mcp.services.application_service import start_or_attach

            result = await start_or_attach(AppStartOrAttachInput(make_visible=False))

        assert result["action"] == "launched"
        assert result["is_new_instance"] is True


class TestDryRunStartOrAttach:
    @pytest.mark.asyncio
    async def test_reports_forced_switch_with_unsaved_project(self) -> None:
        info = ProjectGetInfoResult(
            name="MyProject",
            path="C:\\Projects\\MyProject",
            is_modified=True,
            experiment_count=1,
            timestamp_utc="2024-01-01T00:00:00Z",
        )

        with (
            patch("controldesk_mcp.services.application_service.get_settings") as mock_cfg,
            patch("controldesk_mcp.com_bridge.is_version_installed", return_value=True),
            patch("controldesk_mcp.com_bridge.get_connected_version", return_value="2026-A"),
            patch(
                "controldesk_mcp.services.project_service.project_get_info",
                new_callable=AsyncMock,
                return_value=info,
            ),
        ):
            mock_cfg.return_value.controldesk_version = ""
            from controldesk_mcp.services.application_service import dry_run_start_or_attach

            result = await dry_run_start_or_attach(
                AppStartOrAttachInput(
                    controldesk_version="2024-A",
                    force_version_switch=True,
                    dry_run=True,
                )
            )

        assert isinstance(result, DryRunPreviewResult)
        assert result["would_execute"] is True
        assert result["current_state"]["version_switch_required"] is True
        assert result["current_state"]["is_modified"] is True
        assert "discarded" in result["message"]

    @pytest.mark.asyncio
    async def test_reports_forced_switch_without_open_project_info(self) -> None:
        with (
            patch("controldesk_mcp.services.application_service.get_settings") as mock_cfg,
            patch("controldesk_mcp.com_bridge.is_version_installed", return_value=True),
            patch("controldesk_mcp.com_bridge.get_connected_version", return_value="2026-A"),
            patch(
                "controldesk_mcp.services.project_service.project_get_info",
                new_callable=AsyncMock,
                return_value=ErrorEnvelope(
                    error_code="E001",
                    category="UNKNOWN",
                    message="no project",
                    retryable=False,
                ),
            ),
        ):
            mock_cfg.return_value.controldesk_version = ""
            from controldesk_mcp.services.application_service import dry_run_start_or_attach

            result = await dry_run_start_or_attach(
                AppStartOrAttachInput(
                    controldesk_version="2024-A",
                    force_version_switch=True,
                    dry_run=True,
                )
            )

        assert result["current_state"]["project_open"] is False
        assert "would need to be quit" in result["message"]

    @pytest.mark.asyncio
    async def test_reports_no_switch_when_nothing_running(self) -> None:
        with (
            patch("controldesk_mcp.services.application_service.get_settings") as mock_cfg,
            patch("controldesk_mcp.com_bridge.get_connected_version", return_value=None),
        ):
            mock_cfg.return_value.controldesk_version = ""
            from controldesk_mcp.services.application_service import dry_run_start_or_attach

            result = await dry_run_start_or_attach(AppStartOrAttachInput(dry_run=True))

        assert result["would_execute"] is True
        assert result["current_state"]["version_switch_required"] is False
        assert "without quitting anything" in result["message"]


# ── set_window_visible ────────────────────────────────────────────────────────


class TestSetWindowVisible:
    @pytest.mark.asyncio
    async def test_returns_visible_true(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, None],
        ):
            from controldesk_mcp.services.application_service import set_window_visible

            result = await set_window_visible(AppSetWindowVisibleInput(visible=True))

        assert result["is_now_visible"] is True

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_timeout(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeTimeoutError("timed out"),
        ):
            from controldesk_mcp.services.application_service import set_window_visible

            result = await set_window_visible(AppSetWindowVisibleInput(visible=True))

        assert "error_code" in result


# ── quit_application ──────────────────────────────────────────────────────────


class TestQuitApplication:
    @pytest.mark.asyncio
    async def test_returns_quit_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, None],
        ):
            from controldesk_mcp.services.application_service import quit_application

            result = await quit_application(AppQuitInput())

        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("disconnected"),
        ):
            from controldesk_mcp.services.application_service import quit_application

            result = await quit_application(AppQuitInput())

        assert "error_code" in result


# ── dry_run_quit_application ────────────────────────────────────────


class TestDryRunQuitApplication:
    @pytest.mark.asyncio
    async def test_reports_would_lose_changes_when_unsaved_and_not_saving(self) -> None:
        info = ProjectGetInfoResult(
            name="MyProject",
            path="C:\\Projects\\MyProject",
            is_modified=True,
            experiment_count=1,
            timestamp_utc="2024-01-01T00:00:00Z",
        )

        with patch(
            "controldesk_mcp.services.project_service.project_get_info",
            new_callable=AsyncMock,
            return_value=info,
        ):
            from controldesk_mcp.services.application_service import dry_run_quit_application

            result = await dry_run_quit_application(AppQuitInput(save_all_projects=False, dry_run=True))

        assert result["would_execute"] is True
        assert result["current_state"]["is_modified"] is True
        assert "discarded" in result["message"]

    @pytest.mark.asyncio
    async def test_reports_clean_quit_when_no_unsaved_changes(self) -> None:
        info = ProjectGetInfoResult(
            name="MyProject",
            path="C:\\Projects\\MyProject",
            is_modified=False,
            experiment_count=1,
            timestamp_utc="2024-01-01T00:00:00Z",
        )

        with patch(
            "controldesk_mcp.services.project_service.project_get_info",
            new_callable=AsyncMock,
            return_value=info,
        ):
            from controldesk_mcp.services.application_service import dry_run_quit_application

            result = await dry_run_quit_application(AppQuitInput(dry_run=True))

        assert result["current_state"]["is_modified"] is False

    @pytest.mark.asyncio
    async def test_reports_no_project_open(self) -> None:
        with patch(
            "controldesk_mcp.services.project_service.project_get_info",
            new_callable=AsyncMock,
            return_value=ErrorEnvelope(error_code="E001", category="UNKNOWN", message="no project", retryable=False),
        ):
            from controldesk_mcp.services.application_service import dry_run_quit_application

            result = await dry_run_quit_application(AppQuitInput(dry_run=True))

        assert result["current_state"]["project_open"] is False


# ── get_window_visibility ─────────────────────────────────────────────────────


class TestGetWindowVisibility:
    @pytest.mark.asyncio
    async def test_returns_visibility_state(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, True],
        ):
            from controldesk_mcp.services.application_service import get_window_visibility

            result = await get_window_visibility()

        assert result["is_visible"] is True


# ── get_logs ─────────────────────────────────────────────────────────────────


class TestGetLogs:
    @pytest.mark.asyncio
    async def test_returns_files_sorted_newest_first_and_limited(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "Log"
        log_dir.mkdir(parents=True)

        older = log_dir / "ControlDesk.20240101.log"
        older.write_text("older", encoding="utf-8")
        newer = log_dir / "ControlDesk.20240102.log"
        newer.write_text("newer", encoding="utf-8")

        os.utime(older, (1_700_000_000, 1_700_000_000))
        os.utime(newer, (1_800_000_000, 1_800_000_000))

        with patch(
            "controldesk_mcp.services.application_service._discover_candidate_log_folders",
            return_value=[log_dir],
        ):
            from controldesk_mcp.services.application_service import get_logs

            result = await get_logs(AppGetLogsInput(limit=1, newest_first=True))

        assert result["status"] == "ok"
        assert result["total_found"] == 1
        assert result["files"][0]["name"] == "ControlDesk.20240102.log"

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_logs_found(self, tmp_path: Path) -> None:
        log_dir = tmp_path / "Log"
        log_dir.mkdir(parents=True)

        with patch(
            "controldesk_mcp.services.application_service._discover_candidate_log_folders",
            return_value=[log_dir],
        ):
            from controldesk_mcp.services.application_service import get_logs

            result = await get_logs(AppGetLogsInput())

        assert result["status"] == "ok"
        assert result["total_found"] == 0
        assert result["files"] == []

    @pytest.mark.asyncio
    async def test_uses_log_folder_override(self, tmp_path: Path) -> None:
        override_dir = tmp_path / "override" / "Log"
        override_dir.mkdir(parents=True)
        log_file = override_dir / "ControlDesk.20240702.log"
        log_file.write_text("log", encoding="utf-8")

        with patch(
            "controldesk_mcp.services.application_service._discover_candidate_log_folders",
            return_value=[],
        ):
            from controldesk_mcp.services.application_service import get_logs

            result = await get_logs(AppGetLogsInput(log_folder_override=str(override_dir)))

        assert result["status"] == "ok"
        assert result["total_found"] == 1
        assert result["files"][0]["path"].endswith("ControlDesk.20240702.log")
