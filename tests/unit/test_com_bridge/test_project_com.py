"""Unit tests for controldesk_mcp.com_bridge.domains.project_com."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from controldesk_mcp.com_bridge.domains import project_com
from controldesk_mcp.com_bridge.errors import BridgePreconditionError

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_app(
    *,
    active_project=None,
    active_experiment=None,
    active_root=None,
) -> MagicMock:
    """Return a mock IXaApplication object."""
    app = MagicMock()
    app.ActiveProject = active_project
    app.ActiveExperiment = active_experiment
    app.ActiveProjectRoot = active_root
    return app


def _make_project(name: str = "TestProject", path: str = "C:\\Root\\TestProject") -> MagicMock:
    proj = MagicMock()
    proj.Name = name
    proj.DirectoryName = path
    proj.IsModified = False
    proj.Experiments.Count = 0
    return proj


def _make_experiment(name: str = "Experiment1") -> MagicMock:
    exp = MagicMock()
    exp.Name = name
    exp.Platforms.Count = 2
    return exp


def _make_root(path: str = "C:\\Root") -> MagicMock:
    root = MagicMock()
    root.PathName = path
    root.Projects.Count = 1
    return root


# ── _require_active_project ───────────────────────────────────────────────────


class TestRequireActiveProject:
    def test_raises_when_no_active_project(self) -> None:
        app = _make_app(active_project=None)
        with pytest.raises(BridgePreconditionError, match="No active project"):
            project_com._require_active_project(app)

    def test_returns_project_when_active(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        result = project_com._require_active_project(app)
        assert result is proj


# ── _require_active_root ──────────────────────────────────────────────────────


class TestRequireActiveRoot:
    def test_raises_when_no_active_root(self) -> None:
        app = _make_app(active_root=None)
        with pytest.raises(BridgePreconditionError, match="No active project root"):
            project_com._require_active_root(app)

    def test_returns_root_when_active(self) -> None:
        root = _make_root()
        app = _make_app(active_root=root)
        result = project_com._require_active_root(app)
        assert result is root


# ── _require_active_experiment ────────────────────────────────────────────────


class TestRequireActiveExperiment:
    def test_raises_when_no_active_experiment(self) -> None:
        app = _make_app(active_experiment=None)
        with pytest.raises(BridgePreconditionError, match="No active experiment"):
            project_com._require_active_experiment(app)

    def test_returns_experiment_when_active(self) -> None:
        exp = _make_experiment()
        app = _make_app(active_experiment=exp)
        result = project_com._require_active_experiment(app)
        assert result is exp


# ── project_root_add ──────────────────────────────────────────────────────────


class TestProjectRootAdd:
    def test_returns_added_true_on_success(self) -> None:
        app = MagicMock()
        result = project_com.project_root_add(app, "C:\\Root")
        app.ProjectRoots.Add.assert_called_once_with("C:\\Root")
        assert result == {"path": "C:\\Root", "added": True}

    def test_raises_on_com_error(self) -> None:
        app = MagicMock()
        app.ProjectRoots.Add.side_effect = Exception("COM error")
        with pytest.raises(Exception):
            project_com.project_root_add(app, "C:\\Root")


# ── project_root_activate ─────────────────────────────────────────────────────


class TestProjectRootActivate:
    def test_activates_root_on_success(self) -> None:
        root = MagicMock()
        app = MagicMock()
        app.ProjectRoots.Item.return_value = root
        result = project_com.project_root_activate(app, "C:\\Root")
        root.Activate.assert_called_once()
        assert result == {"activated": True, "path": "C:\\Root"}

    def test_raises_precondition_when_root_not_found(self) -> None:
        app = MagicMock()
        app.ProjectRoots.Item.side_effect = Exception("not found")
        with pytest.raises(BridgePreconditionError, match="not registered"):
            project_com.project_root_activate(app, "C:\\Root")


# ── project_root_list ─────────────────────────────────────────────────────────


class TestProjectRootList:
    def test_returns_list_of_roots(self) -> None:
        root1 = MagicMock()
        root1.PathName = "C:\\Root1"
        root1.Projects.Count = 2

        app = MagicMock()
        app.ProjectRoots.Count = 1
        app.ProjectRoots.Item.return_value = root1

        result = project_com.project_root_list(app)
        assert len(result) == 1
        assert result[0]["path"] == "C:\\Root1"
        assert result[0]["project_count"] == 2
        app.ProjectRoots.Item.assert_called_with(0)

    def test_returns_empty_when_no_roots(self) -> None:
        app = MagicMock()
        app.ProjectRoots.Count = 0
        result = project_com.project_root_list(app)
        assert result == []


# ── project_root_remove ───────────────────────────────────────────────────────


class TestProjectRootRemove:
    def test_removes_root_on_success(self) -> None:
        root = MagicMock()
        app = MagicMock()
        app.ProjectRoots.Item.return_value = root
        result = project_com.project_root_remove(app, "C:\\Root")
        root.Remove.assert_called_once()
        assert result == {"removed": True, "path": "C:\\Root"}

    def test_raises_precondition_when_root_not_found(self) -> None:
        app = MagicMock()
        app.ProjectRoots.Item.side_effect = Exception("not found")
        with pytest.raises(BridgePreconditionError, match="not found"):
            project_com.project_root_remove(app, "C:\\Root")


# ── project_create ────────────────────────────────────────────────────────────


class TestProjectCreate:
    def test_creates_project_and_returns_info(self) -> None:
        proj = _make_project("NewProject", "C:\\Root\\NewProject")
        root = _make_root()
        app = _make_app(active_root=root)
        app.ActiveProjectRoot.Projects.Add.return_value = proj

        result = project_com.project_create(app, "NewProject")
        assert result["name"] == "NewProject"
        assert result["created"] is True

    def test_raises_when_no_active_root(self) -> None:
        app = _make_app(active_root=None)
        with pytest.raises(BridgePreconditionError):
            project_com.project_create(app, "NewProject")


# ── project_open ──────────────────────────────────────────────────────────────


class TestProjectOpen:
    def test_opens_project_on_success(self) -> None:
        proj = MagicMock()
        root = _make_root()
        app = _make_app(active_root=root, active_project=_make_project("TestProject"))
        app.ActiveProjectRoot.Projects.Item.return_value = proj
        app.ActiveProject.Experiments.Count = 3

        result = project_com.project_open(app, "TestProject")
        proj.Open.assert_called_once()
        assert result["name"] == "TestProject"
        assert result["open"] is True
        assert result["experiment_count"] == 3

    def test_raises_when_project_not_found(self) -> None:
        root = _make_root()
        app = _make_app(active_root=root)
        app.ActiveProjectRoot.Projects.Item.side_effect = Exception("not found")
        with pytest.raises(BridgePreconditionError, match="not found"):
            project_com.project_open(app, "NonExistent")


# ── project_save ──────────────────────────────────────────────────────────────


class TestProjectSave:
    def test_saves_active_project(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        result = project_com.project_save(app)
        app.ActiveProject.Save.assert_called_once()
        assert result == {"saved": True}

    def test_raises_when_no_active_project(self) -> None:
        app = _make_app(active_project=None)
        with pytest.raises(BridgePreconditionError):
            project_com.project_save(app)


# ── project_close ─────────────────────────────────────────────────────────────


class TestProjectClose:
    def test_closes_with_save(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        result = project_com.project_close(app, save=True)
        app.ActiveProject.Close.assert_called_once_with(True)
        assert result == {"closed": True}

    def test_closes_without_save(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        project_com.project_close(app, save=False)
        app.ActiveProject.Close.assert_called_once_with(False)

    def test_raises_when_no_active_project(self) -> None:
        app = _make_app(active_project=None)
        with pytest.raises(BridgePreconditionError):
            project_com.project_close(app, save=True)


# ── project_remove ────────────────────────────────────────────────────────────


class TestProjectRemove:
    def test_removes_project(self) -> None:
        proj = MagicMock()
        root = _make_root()
        app = _make_app(active_root=root)
        app.ActiveProjectRoot.Projects.Item.return_value = proj
        result = project_com.project_remove(app, "TestProject", delete_from_disk=False)
        proj.Remove.assert_called_once_with(False)
        assert result == {"removed": True}

    def test_raises_when_project_not_found(self) -> None:
        root = _make_root()
        app = _make_app(active_root=root)
        app.ActiveProjectRoot.Projects.Item.side_effect = Exception("not found")
        with pytest.raises(BridgePreconditionError):
            project_com.project_remove(app, "NonExistent", delete_from_disk=False)


# ── project_backup ────────────────────────────────────────────────────────────


class TestProjectBackup:
    def test_creates_backup(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        result = project_com.project_backup(app, "C:\\Backups\\proj.zip")
        app.ActiveProject.Backup.assert_called_once_with("C:\\Backups\\proj.zip")
        assert result == {"backup_path": "C:\\Backups\\proj.zip", "success": True}

    def test_raises_when_no_active_project(self) -> None:
        app = _make_app(active_project=None)
        with pytest.raises(BridgePreconditionError):
            project_com.project_backup(app, "C:\\Backups\\proj.zip")


# ── project_open_from_backup ──────────────────────────────────────────────────


class TestProjectOpenFromBackup:
    def test_restores_project(self) -> None:
        restored = MagicMock()
        restored.Name = "RestoredProject"
        app = MagicMock()
        app.Projects.OpenFromBackup.return_value = restored
        result = project_com.project_open_from_backup(app, "C:\\Backups\\proj.zip", "RestoredProject", False)
        assert result["restored"] is True
        assert result["name"] == "RestoredProject"


# ── project_exists ────────────────────────────────────────────────────────────


class TestProjectExists:
    def test_returns_true_when_exists(self) -> None:
        root = _make_root()
        app = _make_app(active_root=root)
        app.ActiveProjectRoot.Projects.Contains.return_value = True
        result = project_com.project_exists(app, "TestProject")
        assert result == {"name": "TestProject", "exists": True}

    def test_returns_false_when_not_exists(self) -> None:
        root = _make_root()
        app = _make_app(active_root=root)
        app.ActiveProjectRoot.Projects.Contains.return_value = False
        result = project_com.project_exists(app, "Ghost")
        assert result == {"name": "Ghost", "exists": False}


# ── project_get_info ──────────────────────────────────────────────────────────


class TestProjectGetInfo:
    def test_returns_project_metadata(self) -> None:
        proj = _make_project("TestProject", "C:\\Root\\TestProject")
        proj.IsModified = True
        proj.Experiments.Count = 3
        app = _make_app(active_project=proj)
        result = project_com.project_get_info(app)
        assert result["name"] == "TestProject"
        assert result["path"] == "C:\\Root\\TestProject"
        assert result["is_modified"] is True
        assert result["experiment_count"] == 3

    def test_raises_when_no_active_project(self) -> None:
        app = _make_app(active_project=None)
        with pytest.raises(BridgePreconditionError):
            project_com.project_get_info(app)


# ── experiment_create ─────────────────────────────────────────────────────────


class TestExperimentCreate:
    def test_creates_experiment_activated(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        result = project_com.experiment_create(app, "Experiment1", activate=True)
        app.ActiveProject.Experiments.Add.assert_called_once_with("Experiment1", True)
        assert result == {"name": "Experiment1", "created": True, "is_active": True}

    def test_creates_experiment_not_activated(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        result = project_com.experiment_create(app, "Experiment1", activate=False)
        assert result["is_active"] is False

    def test_raises_when_no_active_project(self) -> None:
        app = _make_app(active_project=None)
        with pytest.raises(BridgePreconditionError):
            project_com.experiment_create(app, "Experiment1", activate=True)


# ── experiment_activate ───────────────────────────────────────────────────────


class TestExperimentActivate:
    def test_activates_experiment(self) -> None:
        exp = _make_experiment("Experiment1")
        proj = _make_project()
        app = _make_app(active_project=proj)
        app.ActiveProject.Experiments.Item.return_value = exp
        result = project_com.experiment_activate(app, "Experiment1")
        exp.Activate.assert_called_once()
        assert result == {"activated": True, "name": "Experiment1"}

    def test_raises_when_experiment_not_found(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        app.ActiveProject.Experiments.Item.side_effect = Exception("not found")
        with pytest.raises(BridgePreconditionError, match="not found"):
            project_com.experiment_activate(app, "NonExistent")


# ── experiment_list ───────────────────────────────────────────────────────────


class TestExperimentList:
    def test_returns_experiment_list(self) -> None:
        exp1 = MagicMock()
        exp1.Name = "Experiment1"
        exp2 = MagicMock()
        exp2.Name = "Experiment2"

        proj = _make_project()
        app = _make_app(active_project=proj)
        app.ActiveProject.Experiments.Count = 2
        app.ActiveProject.Experiments.Item.side_effect = [exp1, exp2]

        result = project_com.experiment_list(app)
        # Verify Item was called with 0 and 1 (0-based)
        app.ActiveProject.Experiments.Item.assert_any_call(0)
        app.ActiveProject.Experiments.Item.assert_any_call(1)
        assert len(result) == 2
        assert result[0]["name"] == "Experiment1"
        assert result[1]["name"] == "Experiment2"

    def test_returns_empty_list_when_no_experiments(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        app.ActiveProject.Experiments.Count = 0
        result = project_com.experiment_list(app)
        assert result == []


# ── experiment_remove ─────────────────────────────────────────────────────────


class TestExperimentRemove:
    def test_removes_experiment(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        app.ActiveProject.Experiments.Item.return_value.Active = False
        result = project_com.experiment_remove(app, "Experiment1", delete_from_disk=False)
        app.ActiveProject.Experiments.Item.assert_called_once_with("Experiment1")
        app.ActiveProject.Experiments.Item.return_value.Remove.assert_called_once_with(False)
        assert result == {"removed": True}

    def test_raises_precondition_when_experiment_is_active(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        app.ActiveProject.Experiments.Item.return_value.Active = True
        with pytest.raises(BridgePreconditionError, match="currently active"):
            project_com.experiment_remove(app, "ActiveExp", delete_from_disk=False)


# ── experiment_get_info ───────────────────────────────────────────────────────


class TestExperimentGetInfo:
    def test_returns_experiment_metadata(self) -> None:
        exp = _make_experiment("Experiment1")
        app = _make_app(active_experiment=exp)
        result = project_com.experiment_get_info(app)
        assert result["name"] == "Experiment1"
        assert result["platform_count"] == 2

    def test_raises_when_no_active_experiment(self) -> None:
        app = _make_app(active_experiment=None)
        with pytest.raises(BridgePreconditionError):
            project_com.experiment_get_info(app)


# ── experiment_export ─────────────────────────────────────────────────────────


class TestExperimentExport:
    def test_exports_experiment(self) -> None:
        exp = _make_experiment()
        app = _make_app(active_experiment=exp)
        result = project_com.experiment_export(app, "C:\\Exports\\exp.dsa")
        exp.Export.assert_called_once_with("C:\\Exports\\exp.dsa")
        assert result == {"export_path": "C:\\Exports\\exp.dsa", "success": True}

    def test_raises_when_no_active_experiment(self) -> None:
        app = _make_app(active_experiment=None)
        with pytest.raises(BridgePreconditionError):
            project_com.experiment_export(app, "C:\\Exports\\exp.dsa")


# ── experiment_import ─────────────────────────────────────────────────────────


class TestExperimentImport:
    def test_imports_experiment(self) -> None:
        imported_exp = MagicMock()
        imported_exp.Name = "ImportedExp"
        proj = _make_project()
        app = _make_app(active_project=proj)
        app.ActiveProject.Experiments.Import.return_value = imported_exp
        result = project_com.experiment_import(app, "C:\\Exports\\exp.dsa", "MyExpName")
        app.ActiveProject.Experiments.Import.assert_called_once_with("C:\\Exports\\exp.dsa", "MyExpName", False)
        assert result["imported"] is True
        assert result["name"] == "ImportedExp"

    def test_raises_when_no_active_project(self) -> None:
        app = _make_app(active_project=None)
        with pytest.raises(BridgePreconditionError):
            project_com.experiment_import(app, "C:\\Exports\\exp.dsa", "MyExpName")


# ── experiment_rename ─────────────────────────────────────────────────────────


class TestExperimentRename:
    def test_renames_experiment(self) -> None:
        exp = _make_experiment()
        app = _make_app(active_experiment=exp)
        result = project_com.experiment_rename(app, "NewName")
        exp.Rename.assert_called_once_with("NewName")
        assert result == {"new_name": "NewName", "renamed": True}

    def test_raises_when_no_active_experiment(self) -> None:
        app = _make_app(active_experiment=None)
        with pytest.raises(BridgePreconditionError):
            project_com.experiment_rename(app, "NewName")


# ── experiment_save_as ────────────────────────────────────────────────────────


class TestExperimentSaveAs:
    def test_saves_as_new_name(self) -> None:
        exp = _make_experiment()
        app = _make_app(active_experiment=exp)
        result = project_com.experiment_save_as(app, "Experiment1_Copy")
        exp.SaveAs.assert_called_once_with("Experiment1_Copy")
        assert result == {"new_name": "Experiment1_Copy", "saved": True}

    def test_raises_when_no_active_experiment(self) -> None:
        app = _make_app(active_experiment=None)
        with pytest.raises(BridgePreconditionError):
            project_com.experiment_save_as(app, "Experiment1_Copy")


# ── project_configure_settings ────────────────────────────────────────────────


class TestProjectConfigureSettings:
    def test_sets_auto_save(self) -> None:
        proj = _make_project()
        proj.GeneralSettings = MagicMock()
        app = _make_app(active_project=proj)
        result = project_com.project_configure_settings(app, auto_save=True, open_last_experiment_on_startup=None)
        assert proj.GeneralSettings.AutoSave == True  # noqa: E712
        assert result == {"configured": True}

    def test_sets_open_last_experiment(self) -> None:
        proj = _make_project()
        proj.GeneralSettings = MagicMock()
        app = _make_app(active_project=proj)
        result = project_com.project_configure_settings(app, auto_save=None, open_last_experiment_on_startup=True)
        assert proj.GeneralSettings.OpenLastExperimentOnStartup == True  # noqa: E712
        assert result == {"configured": True}

    def test_no_change_when_none(self) -> None:
        proj = _make_project()
        app = _make_app(active_project=proj)
        result = project_com.project_configure_settings(app, auto_save=None, open_last_experiment_on_startup=None)
        assert result == {"configured": True}

    def test_raises_when_no_active_project(self) -> None:
        app = _make_app(active_project=None)
        with pytest.raises(BridgePreconditionError):
            project_com.project_configure_settings(app, auto_save=True, open_last_experiment_on_startup=None)
