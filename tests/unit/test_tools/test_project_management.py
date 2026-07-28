"""Unit tests for controldesk_mcp.tools.project.management (consolidated manage-tools).

Mocks at the service layer — no COM bridge involved.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.project import (
    ExperimentActivateResult,
    ExperimentCreateResult,
    ExperimentExportResult,
    ExperimentGetInfoResult,
    ExperimentImportResult,
    ExperimentIoManageAction,
    ExperimentIoManageInput,
    ExperimentListResult,
    ExperimentManageAction,
    ExperimentManageInput,
    ExperimentRemoveResult,
    ExperimentRenameResult,
    ExperimentSaveAsResult,
    ProjectBackupManageAction,
    ProjectBackupManageInput,
    ProjectBackupResult,
    ProjectCloseResult,
    ProjectConfigureSettingsResult,
    ProjectCreateResult,
    ProjectDiscoverResult,
    ProjectExistsResult,
    ProjectGetInfoResult,
    ProjectListRecentInput,
    ProjectListRecentResult,
    ProjectListResult,
    ProjectManageAction,
    ProjectManageInput,
    ProjectOpenFromBackupResult,
    ProjectOpenInput,
    ProjectOpenResult,
    ProjectRemoveResult,
    ProjectRootActivateResult,
    ProjectRootAddResult,
    ProjectRootListResult,
    ProjectRootManageAction,
    ProjectRootManageInput,
    ProjectRootRemoveResult,
    ProjectSaveResult,
)

_TS = "2024-01-01T00:00:00Z"

_ERROR = ErrorEnvelope(
    error_code="COM_DISCONNECTED",
    category="CONNECTION",
    message="Bridge not connected",
)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.tools.project.management.project_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── project_list_recent (MAIN) ────────────────────────────────────────────────


class TestProjectListRecent:
    @pytest.mark.asyncio
    async def test_returns_projects_sorted_by_mtime(self) -> None:
        mock_result = ProjectListRecentResult(
            projects=[
                {
                    "root_path": "C:\\Root",
                    "name": "NewProj",
                    "last_modified_utc": "2024-01-02T00:00:00Z",
                },
                {
                    "root_path": "C:\\Root",
                    "name": "OldProj",
                    "last_modified_utc": "2024-01-01T00:00:00Z",
                },
            ],
            count=2,
            timestamp_utc=_TS,
        )
        with _patch_svc("project_list_recent", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_list_recent

            result = await project_list_recent(ProjectListRecentInput(limit=10))

        assert result["status"] == "ok"
        assert result["total_count"] == 2
        assert result["projects"][0]["name"] == "NewProj"

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("project_list_recent", return_value=_ERROR):
            from controldesk_mcp.tools.project.management import project_list_recent

            result = await project_list_recent(ProjectListRecentInput())

        assert isinstance(result, ErrorEnvelope)


# ── project_open (MAIN) ───────────────────────────────────────────────────────


class TestProjectOpen:
    @pytest.mark.asyncio
    async def test_returns_ok_on_success(self) -> None:
        mock_result = ProjectOpenResult(name="TestProject", open=True, experiment_count=3, timestamp_utc=_TS)
        with _patch_svc("project_open", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_open

            result = await project_open(ProjectOpenInput(name="TestProject"))

        assert isinstance(result, ProjectOpenResult)
        assert result["open"] is True
        assert result["experiment_count"] == 3

    @pytest.mark.asyncio
    async def test_returns_error_on_service_error(self) -> None:
        with _patch_svc("project_open", return_value=_ERROR):
            from controldesk_mcp.tools.project.management import project_open

            result = await project_open(ProjectOpenInput(name="Missing"))

        assert isinstance(result, ErrorEnvelope)


# ── project_root_manage (ADD_ON lazy) ────────────────────────────────────────


class TestProjectRootManage:
    @pytest.mark.asyncio
    async def test_add_returns_ok(self) -> None:
        mock_result = ProjectRootAddResult(path="C:\\Root", added=True, timestamp_utc=_TS)
        with _patch_svc("project_root_add", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_root_manage

            result = await project_root_manage(
                ProjectRootManageInput(action=ProjectRootManageAction.add, path="C:\\Root")
            )

        assert isinstance(result, ProjectRootAddResult)
        assert result["added"] is True

    @pytest.mark.asyncio
    async def test_add_missing_path_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import project_root_manage

        result = await project_root_manage(ProjectRootManageInput(action=ProjectRootManageAction.add, path=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_activate_returns_ok(self) -> None:
        mock_result = ProjectRootActivateResult(activated=True, path="C:\\Root", timestamp_utc=_TS)
        with _patch_svc("project_root_activate", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_root_manage

            result = await project_root_manage(
                ProjectRootManageInput(action=ProjectRootManageAction.activate, path="C:\\Root")
            )

        assert isinstance(result, ProjectRootActivateResult)
        assert result["activated"] is True

    @pytest.mark.asyncio
    async def test_activate_missing_path_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import project_root_manage

        result = await project_root_manage(ProjectRootManageInput(action=ProjectRootManageAction.activate, path=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_returns_roots(self) -> None:
        mock_result = ProjectRootListResult(
            roots=[{"path": "C:\\Root", "project_count": 2}], count=1, timestamp_utc=_TS
        )
        with _patch_svc("project_root_list", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_root_manage

            result = await project_root_manage(ProjectRootManageInput(action=ProjectRootManageAction.list))

        assert result["status"] == "ok"
        assert result["total_count"] == 1

    @pytest.mark.asyncio
    async def test_list_service_error_propagates(self) -> None:
        with _patch_svc("project_root_list", return_value=_ERROR):
            from controldesk_mcp.tools.project.management import project_root_manage

            result = await project_root_manage(ProjectRootManageInput(action=ProjectRootManageAction.list))

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_remove_returns_ok(self) -> None:
        mock_result = ProjectRootRemoveResult(removed=True, path="C:\\Root", timestamp_utc=_TS)
        with _patch_svc("project_root_remove", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_root_manage

            result = await project_root_manage(
                ProjectRootManageInput(action=ProjectRootManageAction.remove, path="C:\\Root")
            )

        assert isinstance(result, ProjectRootRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_path_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import project_root_manage

        result = await project_root_manage(ProjectRootManageInput(action=ProjectRootManageAction.remove, path=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── project_manage (ADD_ON lazy) ──────────────────────────────────────────────


class TestProjectManage:
    @pytest.mark.asyncio
    async def test_create_returns_ok(self) -> None:
        mock_result = ProjectCreateResult(name="Proj", path="C:\\Root\\Proj", created=True, timestamp_utc=_TS)
        with _patch_svc("project_create", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.create, name="Proj"))

        assert isinstance(result, ProjectCreateResult)
        assert result["created"] is True

    @pytest.mark.asyncio
    async def test_create_missing_name_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import project_manage

        result = await project_manage(ProjectManageInput(action=ProjectManageAction.create, name=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_save_returns_ok(self) -> None:
        mock_result = ProjectSaveResult(saved=True, timestamp_utc=_TS)
        with _patch_svc("project_save", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.save))

        assert isinstance(result, ProjectSaveResult)
        assert result["saved"] is True

    @pytest.mark.asyncio
    async def test_save_service_error_propagates(self) -> None:
        with _patch_svc("project_save", return_value=_ERROR):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.save))

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_close_returns_ok(self) -> None:
        mock_result = ProjectCloseResult(closed=True, timestamp_utc=_TS)
        with _patch_svc("project_close", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.close, save=True))

        assert isinstance(result, ProjectCloseResult)
        assert result["closed"] is True

    @pytest.mark.asyncio
    async def test_remove_returns_ok(self) -> None:
        mock_result = ProjectRemoveResult(removed=True, timestamp_utc=_TS)
        with _patch_svc("project_remove", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.remove, name="Proj"))

        assert isinstance(result, ProjectRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_name_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import project_manage

        result = await project_manage(ProjectManageInput(action=ProjectManageAction.remove, name=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_exists_true(self) -> None:
        mock_result = ProjectExistsResult(name="Proj", exists=True, timestamp_utc=_TS)
        with _patch_svc("project_exists", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.exists, name="Proj"))

        assert isinstance(result, ProjectExistsResult)
        assert result["exists"] is True

    @pytest.mark.asyncio
    async def test_exists_false(self) -> None:
        mock_result = ProjectExistsResult(name="Ghost", exists=False, timestamp_utc=_TS)
        with _patch_svc("project_exists", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.exists, name="Ghost"))

        assert result["exists"] is False

    @pytest.mark.asyncio
    async def test_exists_missing_name_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import project_manage

        result = await project_manage(ProjectManageInput(action=ProjectManageAction.exists, name=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_get_info_returns_metadata(self) -> None:
        mock_result = ProjectGetInfoResult(
            name="Proj",
            path="C:\\Root\\Proj",
            is_modified=False,
            experiment_count=2,
            timestamp_utc=_TS,
        )
        with _patch_svc("project_get_info", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.get_info))

        assert isinstance(result, ProjectGetInfoResult)
        assert result["experiment_count"] == 2

    @pytest.mark.asyncio
    async def test_configure_returns_ok(self) -> None:
        mock_result = ProjectConfigureSettingsResult(configured=True, timestamp_utc=_TS)
        with _patch_svc("project_configure_settings", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.configure, auto_save=True))

        assert isinstance(result, ProjectConfigureSettingsResult)
        assert result["configured"] is True

    @pytest.mark.asyncio
    async def test_list_returns_projects(self) -> None:
        mock_result = ProjectListResult(projects=[{"name": "ProjA"}, {"name": "ProjB"}], count=2, timestamp_utc=_TS)
        with _patch_svc("project_list", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.list))

        assert result["status"] == "ok"
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_list_service_error_propagates(self) -> None:
        with _patch_svc("project_list", return_value=_ERROR):
            from controldesk_mcp.tools.project.management import project_manage

            result = await project_manage(ProjectManageInput(action=ProjectManageAction.list))

        assert isinstance(result, ErrorEnvelope)


# ── project_backup_manage (ADD_ON lazy) ───────────────────────────────────────


class TestProjectBackupManage:
    @pytest.mark.asyncio
    async def test_backup_returns_ok(self) -> None:
        mock_result = ProjectBackupResult(backup_path="C:\\Backups\\proj.zip", success=True, timestamp_utc=_TS)
        with _patch_svc("project_backup", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_backup_manage

            result = await project_backup_manage(
                ProjectBackupManageInput(
                    action=ProjectBackupManageAction.backup,
                    backup_path="C:\\Backups\\proj.zip",
                )
            )

        assert isinstance(result, ProjectBackupResult)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_backup_missing_path_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import project_backup_manage

        result = await project_backup_manage(
            ProjectBackupManageInput(action=ProjectBackupManageAction.backup, backup_path=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_restore_returns_ok(self) -> None:
        mock_result = ProjectOpenFromBackupResult(name="RestoredProj", restored=True, timestamp_utc=_TS)
        with _patch_svc("project_open_from_backup", return_value=mock_result):
            from controldesk_mcp.tools.project.management import project_backup_manage

            result = await project_backup_manage(
                ProjectBackupManageInput(
                    action=ProjectBackupManageAction.restore,
                    backup_path="C:\\Backups\\proj.zip",
                )
            )

        assert isinstance(result, ProjectOpenFromBackupResult)
        assert result["restored"] is True

    @pytest.mark.asyncio
    async def test_restore_missing_path_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import project_backup_manage

        result = await project_backup_manage(
            ProjectBackupManageInput(action=ProjectBackupManageAction.restore, backup_path=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── experiment_manage (ADD_ON lazy) ──────────────────────────────────────────


class TestExperimentManage:
    @pytest.mark.asyncio
    async def test_create_returns_ok(self) -> None:
        mock_result = ExperimentCreateResult(name="Exp1", created=True, is_active=True, timestamp_utc=_TS)
        with _patch_svc("experiment_create", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_manage

            result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.create, name="Exp1"))

        assert isinstance(result, ExperimentCreateResult)
        assert result["created"] is True
        assert result["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_missing_name_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import experiment_manage

        result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.create, name=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_activate_returns_ok(self) -> None:
        mock_result = ExperimentActivateResult(activated=True, name="Exp1", timestamp_utc=_TS)
        with _patch_svc("experiment_activate", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_manage

            result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.activate, name="Exp1"))

        assert isinstance(result, ExperimentActivateResult)
        assert result["activated"] is True

    @pytest.mark.asyncio
    async def test_activate_missing_name_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import experiment_manage

        result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.activate, name=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_activate_service_error_propagates(self) -> None:
        with _patch_svc("experiment_activate", return_value=_ERROR):
            from controldesk_mcp.tools.project.management import experiment_manage

            result = await experiment_manage(
                ExperimentManageInput(action=ExperimentManageAction.activate, name="Missing")
            )

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_list_returns_experiments(self) -> None:
        mock_result = ExperimentListResult(experiments=[{"name": "Exp1"}, {"name": "Exp2"}], count=2, timestamp_utc=_TS)
        with _patch_svc("experiment_list", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_manage

            result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.list))

        assert result["status"] == "ok"
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_list_service_error_propagates(self) -> None:
        with _patch_svc("experiment_list", return_value=_ERROR):
            from controldesk_mcp.tools.project.management import experiment_manage

            result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.list))

        assert isinstance(result, ErrorEnvelope)

    @pytest.mark.asyncio
    async def test_remove_returns_ok(self) -> None:
        mock_result = ExperimentRemoveResult(removed=True, timestamp_utc=_TS)
        with _patch_svc("experiment_remove", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_manage

            result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.remove, name="Exp1"))

        assert isinstance(result, ExperimentRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_remove_missing_name_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import experiment_manage

        result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.remove, name=None))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_get_info_returns_metadata(self) -> None:
        mock_result = ExperimentGetInfoResult(name="Exp1", platform_count=2, timestamp_utc=_TS)
        with _patch_svc("experiment_get_info", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_manage

            result = await experiment_manage(ExperimentManageInput(action=ExperimentManageAction.get_info))

        assert isinstance(result, ExperimentGetInfoResult)
        assert result["platform_count"] == 2


# ── experiment_io_manage (ADD_ON lazy) ────────────────────────────────────────


class TestExperimentIoManage:
    @pytest.mark.asyncio
    async def test_export_returns_ok(self) -> None:
        mock_result = ExperimentExportResult(export_path="C:\\Exports\\exp.dsa", success=True, timestamp_utc=_TS)
        with _patch_svc("experiment_export", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_io_manage

            result = await experiment_io_manage(
                ExperimentIoManageInput(
                    action=ExperimentIoManageAction.export,
                    export_path="C:\\Exports\\exp.dsa",
                )
            )

        assert isinstance(result, ExperimentExportResult)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_export_missing_path_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import experiment_io_manage

        result = await experiment_io_manage(
            ExperimentIoManageInput(action=ExperimentIoManageAction.export, export_path=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_import_returns_ok(self) -> None:
        mock_result = ExperimentImportResult(name="ImportedExp", imported=True, timestamp_utc=_TS)
        with _patch_svc("experiment_import", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_io_manage

            result = await experiment_io_manage(
                ExperimentIoManageInput(
                    action=ExperimentIoManageAction.import_,
                    import_path="C:\\Exports\\exp.dsa",
                )
            )

        assert isinstance(result, ExperimentImportResult)
        assert result["imported"] is True

    @pytest.mark.asyncio
    async def test_import_missing_path_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import experiment_io_manage

        result = await experiment_io_manage(
            ExperimentIoManageInput(action=ExperimentIoManageAction.import_, import_path=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_rename_returns_ok(self) -> None:
        mock_result = ExperimentRenameResult(new_name="NewName", renamed=True, timestamp_utc=_TS)
        with _patch_svc("experiment_rename", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_io_manage

            result = await experiment_io_manage(
                ExperimentIoManageInput(action=ExperimentIoManageAction.rename, new_name="NewName")
            )

        assert isinstance(result, ExperimentRenameResult)
        assert result["renamed"] is True
        assert result["new_name"] == "NewName"

    @pytest.mark.asyncio
    async def test_rename_missing_name_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import experiment_io_manage

        result = await experiment_io_manage(
            ExperimentIoManageInput(action=ExperimentIoManageAction.rename, new_name=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_save_as_returns_ok(self) -> None:
        mock_result = ExperimentSaveAsResult(new_name="Exp_Copy", saved=True, timestamp_utc=_TS)
        with _patch_svc("experiment_save_as", return_value=mock_result):
            from controldesk_mcp.tools.project.management import experiment_io_manage

            result = await experiment_io_manage(
                ExperimentIoManageInput(action=ExperimentIoManageAction.save_as, new_name="Exp_Copy")
            )

        assert isinstance(result, ExperimentSaveAsResult)
        assert result["saved"] is True
        assert result["new_name"] == "Exp_Copy"

    @pytest.mark.asyncio
    async def test_save_as_missing_name_returns_missing_param(self) -> None:
        from controldesk_mcp.tools.project.management import experiment_io_manage

        result = await experiment_io_manage(
            ExperimentIoManageInput(action=ExperimentIoManageAction.save_as, new_name=None)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── project_discover (META / SEARCH) ─────────────────────────────────────────


class TestProjectDiscover:
    @pytest.mark.asyncio
    async def test_returns_catalogue_with_all_tools(self) -> None:
        from controldesk_mcp.tools.project.management import project_discover

        result = await project_discover(AsyncMock())

        assert isinstance(result, ProjectDiscoverResult)
        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "controldesk_project_root_manage" in tool_names
        assert "controldesk_project_manage" in tool_names
        assert "controldesk_project_backup_manage" in tool_names
        assert "controldesk_project_experiment_manage" in tool_names
        assert "controldesk_project_experiment_io_manage" in tool_names

    @pytest.mark.asyncio
    async def test_required_params_populated(self) -> None:
        from controldesk_mcp.tools.project.management import project_discover

        result = await project_discover(AsyncMock())

        root_entry = next(t for t in result["tools"] if t["tool_name"] == "controldesk_project_root_manage")
        assert root_entry["required_params_per_action"]["add"] == ["path"]
        assert root_entry["required_params_per_action"]["list"] == []
