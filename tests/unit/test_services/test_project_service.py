"""Unit tests for controldesk_mcp.services.project_service.

Tests mock com_bridge.dispatch; no real COM is invoked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import controldesk_mcp.com_bridge as bridge
from controldesk_mcp.com_bridge.errors import BridgeConnectionError, BridgePreconditionError
from controldesk_mcp.models.project import (
    ProjectOpenInput,
    ProjectRootAddInput,
)

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


# ── project_root_add ──────────────────────────────────────────────────────────


class TestProjectRootAdd:
    @pytest.mark.asyncio
    async def test_returns_add_result_on_success(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"path": "C:\\Root", "added": True}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.project_service import project_root_add

            result = await project_root_add(ProjectRootAddInput(path="C:\\Root"))

        assert result["path"] == "C:\\Root"
        assert result["added"] is True
        assert "timestamp_utc" in result

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("disconnected"),
        ):
            from controldesk_mcp.services.project_service import project_root_add

            result = await project_root_add(ProjectRootAddInput(path="C:\\Root"))

        assert "error_code" in result


# ── project_root_list ─────────────────────────────────────────────────────────


class TestProjectRootList:
    @pytest.mark.asyncio
    async def test_returns_roots_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = [{"path": "C:\\Root1"}]

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.project_service import project_root_list

            result = await project_root_list()

        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgePreconditionError("no project"),
        ):
            from controldesk_mcp.services.project_service import project_root_list

            result = await project_root_list()

        assert "error_code" in result


# ── project_open ──────────────────────────────────────────────────────────────


class TestProjectOpen:
    @pytest.mark.asyncio
    async def test_returns_open_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = {"name": "TestProj", "open": True, "experiment_count": 2}

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=[app_mock, com_result],
        ):
            from controldesk_mcp.services.project_service import project_open

            result = await project_open(ProjectOpenInput(name="TestProj"))

        assert result["name"] == "TestProj"
        assert result["open"] is True


# ── project_list ────────────────────────────────────────────────────────────


class TestProjectList:
    @pytest.mark.asyncio
    async def test_returns_projects_across_all_roots(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = [
            {
                "root_path": "C:\\Root1",
                "name": "Proj1",
                "full_path": "C:\\Root1\\Proj1\\Proj1.cdxs",
            },
            {
                "root_path": "C:\\Root2",
                "name": "Proj2",
                "full_path": "C:\\Root2\\Proj2\\Proj2.cdxs",
            },
        ]

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, com_result],
            ),
            patch("os.scandir", return_value=[]),
        ):
            from controldesk_mcp.services.project_service import project_list

            result = await project_list()

        assert result["count"] == 2
        assert result["projects"][0]["name"] == "Proj1"
        assert result["projects"][1]["root_path"] == "C:\\Root2"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_projects(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, []],
            ),
            patch("os.scandir", return_value=[]),
        ):
            from controldesk_mcp.services.project_service import project_list

            result = await project_list()

        assert result["count"] == 0
        assert result["projects"] == []

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("not running"),
        ):
            from controldesk_mcp.services.project_service import project_list

            result = await project_list()

        assert "error_code" in result

    @pytest.mark.asyncio
    async def test_experiments_included_in_project_list(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = [
            {
                "root_path": "C:\\Root",
                "name": "Proj",
                "full_path": "C:\\Root\\Proj\\Proj.CDP",
            }
        ]

        mock_cde_file = MagicMock()
        mock_cde_file.is_file.return_value = True
        mock_cde_file.name = "Exp1.CDE"

        mock_exp_dir = MagicMock()
        mock_exp_dir.is_dir.return_value = True
        mock_exp_dir.name = "Exp1"
        mock_exp_dir.path = "C:\\Root\\Proj\\Exp1"

        def _scandir(path: str):
            if "Proj" in path and "Exp1" not in path:
                return [mock_exp_dir]
            return [mock_cde_file]

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, com_result],
            ),
            patch("os.scandir", side_effect=_scandir),
        ):
            from controldesk_mcp.services.project_service import project_list

            result = await project_list()

        assert result["projects"][0]["experiments"] == ["Exp1"]


# ── project_list_recent ───────────────────────────────────────────────────────


class TestProjectListRecent:
    @pytest.mark.asyncio
    async def test_returns_projects_sorted_by_mtime(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = [
            {"root_path": "C:\\Root", "name": "Old", "full_path": "C:\\Root\\Old\\Old.cdxs"},
            {"root_path": "C:\\Root", "name": "New", "full_path": "C:\\Root\\New\\New.cdxs"},
        ]

        # Old = mtime 1000, New = mtime 2000 → New should appear first
        def fake_getmtime(path: str) -> float:
            return 2000.0 if "New" in path else 1000.0

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, com_result],
            ),
            patch("os.path.getmtime", side_effect=fake_getmtime),
            patch("os.scandir", return_value=[]),
        ):
            from controldesk_mcp.models.project import ProjectListRecentInput
            from controldesk_mcp.services.project_service import project_list_recent

            result = await project_list_recent(ProjectListRecentInput(limit=10))

        assert result["status"] == "ok"
        assert result["count"] == 2
        assert result["projects"][0]["name"] == "New"
        assert result["projects"][1]["name"] == "Old"

    @pytest.mark.asyncio
    async def test_limit_truncates_result(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = [
            {"root_path": "C:\\Root", "name": f"P{i}", "full_path": f"C:\\Root\\P{i}\\P{i}.cdxs"}
            for i in range(5)
        ]

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, com_result],
            ),
            patch("os.path.getmtime", side_effect=OSError),
            patch("os.scandir", return_value=[]),
        ):
            from controldesk_mcp.models.project import ProjectListRecentInput
            from controldesk_mcp.services.project_service import project_list_recent

            result = await project_list_recent(ProjectListRecentInput(limit=2))

        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_experiments_discovered_from_disk(self) -> None:
        conn = _make_connected_bridge()
        app_mock = conn.get_app.return_value
        com_result = [
            {
                "root_path": "C:\\Root",
                "name": "Proj",
                "full_path": "C:\\Root\\Proj\\Proj.cdxs",
            }
        ]

        # Simulate an experiment subdirectory containing a .CDE file
        mock_cde_file = MagicMock()
        mock_cde_file.is_file.return_value = True
        mock_cde_file.name = "Exp1.CDE"

        mock_exp_dir = MagicMock()
        mock_exp_dir.is_dir.return_value = True
        mock_exp_dir.name = "Exp1"
        mock_exp_dir.path = "C:\\Root\\Proj\\Exp1"

        def _scandir(path: str):
            if "Proj" in path and "Exp1" not in path:
                return [mock_exp_dir]
            return [mock_cde_file]

        with (
            patch(
                "controldesk_mcp.com_bridge.dispatch",
                new_callable=AsyncMock,
                side_effect=[app_mock, com_result],
            ),
            patch("os.path.getmtime", return_value=1000.0),
            patch("os.scandir", side_effect=_scandir),
        ):
            from controldesk_mcp.models.project import ProjectListRecentInput
            from controldesk_mcp.services.project_service import project_list_recent

            result = await project_list_recent(ProjectListRecentInput())

        assert result["projects"][0]["experiments"] == ["Exp1"]

    @pytest.mark.asyncio
    async def test_returns_error_on_bridge_error(self) -> None:
        _make_connected_bridge()

        with patch(
            "controldesk_mcp.com_bridge.dispatch",
            new_callable=AsyncMock,
            side_effect=BridgeConnectionError("not running"),
        ):
            from controldesk_mcp.models.project import ProjectListRecentInput
            from controldesk_mcp.services.project_service import project_list_recent

            result = await project_list_recent(ProjectListRecentInput())

        assert "error_code" in result
