"""COM wrappers for ControlDesk project and experiment management interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry points:
  - app.ProjectRoots               (IXaProjectRoots)
  - app.ActiveProjectRoot          (IXaProjectRoot)
  - app.ActiveProject              (IXaProject)
  - app.ActiveExperiment           (IXaExperiment)
"""

from __future__ import annotations

from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgeOperationError, BridgePreconditionError

# ── Precondition guards ───────────────────────────────────────────────────────


def _require_active_project(app: Any) -> Any:
    """Return app.ActiveProject or raise BridgePreconditionError."""
    try:
        project = app.ActiveProject
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="ActiveProject") from exc
    if project is None:
        raise BridgePreconditionError(
            "No active project open. Call project_open or project_create first.",
            error_code="BRIDGE_NO_PROJECT",
            recovery_hint="Open or create a project before calling project tools.",
        )
    return project


def _require_active_root(app: Any) -> Any:
    """Return app.ActiveProjectRoot or raise BridgePreconditionError."""
    try:
        root = app.ActiveProjectRoot
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="ActiveProjectRoot") from exc
    if root is None:
        raise BridgePreconditionError(
            "No active project root. Call project_root_add and project_root_activate first.",
            error_code="BRIDGE_NO_ROOT",
            recovery_hint="Add and activate a project root before calling project tools.",
        )
    return root


def _require_active_experiment(app: Any) -> Any:
    """Return app.ActiveExperiment or raise BridgePreconditionError."""
    try:
        exp = app.ActiveExperiment
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="ActiveExperiment") from exc
    if exp is None:
        raise BridgePreconditionError(
            "No active experiment open. Call experiment_activate or experiment_create first.",
            error_code="BRIDGE_NO_EXPERIMENT",
            recovery_hint="Activate or create an experiment before calling experiment tools.",
        )
    return exp


# ── project_root_add ──────────────────────────────────────────────────────────


def project_root_add(app: Any, path: str) -> dict[str, Any]:
    """Register *path* as a project root folder.

    If the path is already registered, the existing root is returned without
    raising an error (idempotent per ControlDesk COM behaviour).
    """
    try:
        app.ProjectRoots.Add(path)
        return {"path": path, "added": True}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjectRoots", method="Add") from exc


# ── project_root_activate ─────────────────────────────────────────────────────


def project_root_activate(app: Any, path: str) -> dict[str, Any]:
    """Activate the project root identified by *path*."""
    try:
        root = app.ProjectRoots.Item(path)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Project root '{path}' is not registered. Call project_root_add first.",
            error_code="BRIDGE_ROOT_NOT_FOUND",
            recovery_hint="Register the root with project_root_add before activating it.",
        ) from exc
    try:
        root.Activate()
        return {"activated": True, "path": path}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjectRoot", method="Activate") from exc


# ── project_root_list ─────────────────────────────────────────────────────────


def project_root_list(app: Any) -> list[dict[str, Any]]:
    """Return a snapshot of all registered project roots."""
    try:
        roots_col = app.ProjectRoots
        count = int(roots_col.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjectRoots", method="Count") from exc

    result: list[dict[str, Any]] = []
    for i in range(0, count):
        try:
            root = roots_col.Item(i)
            entry: dict[str, Any] = {"path": str(root.PathName)}
            try:
                entry["project_count"] = int(root.Projects.Count)
            except Exception:  # noqa: BLE001
                entry["project_count"] = 0
            result.append(entry)
        except Exception as exc:
            raise map_com_error(exc, interface="IXaProjectRoot", method="PathName") from exc
    return result


# ── project_root_remove ───────────────────────────────────────────────────────


def project_root_remove(app: Any, path: str) -> dict[str, Any]:
    """Unregister the project root at *path* from ControlDesk."""
    try:
        root = app.ProjectRoots.Item(path)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Project root '{path}' not found.",
            error_code="BRIDGE_ROOT_NOT_FOUND",
            recovery_hint="Use project_root_list to enumerate registered roots.",
        ) from exc
    try:
        root.Remove()
        return {"removed": True, "path": path}
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjectRoot", method="Remove") from exc


# ── project_create ────────────────────────────────────────────────────────────


def project_create(app: Any, name: str) -> dict[str, Any]:
    """Create a new project under the active project root."""
    _require_active_root(app)
    try:
        project = app.ActiveProjectRoot.Projects.Add(name)
        path = ""
        try:
            path = str(project.DirectoryName)
        except Exception:  # noqa: BLE001
            pass
        return {"name": name, "path": path, "created": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjects", method="Add") from exc


# ── project_open ──────────────────────────────────────────────────────────────


def project_open(app: Any, name: str) -> dict[str, Any]:
    """Open the named project from the active project root."""
    _require_active_root(app)
    try:
        project = app.ActiveProjectRoot.Projects.Item(name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Project '{name}' not found in the active root.",
            error_code="BRIDGE_PROJECT_NOT_FOUND",
            recovery_hint="Use project_root_list or project_exists to verify the project name.",
        ) from exc
    try:
        project.Open()
        exp_count = 0
        try:
            exp_count = int(app.ActiveProject.Experiments.Count)
        except Exception:  # noqa: BLE001
            pass
        return {"name": name, "open": True, "experiment_count": exp_count}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProject", method="Open") from exc


# ── project_save ──────────────────────────────────────────────────────────────


def project_save(app: Any) -> dict[str, Any]:
    """Save all changes in the active project."""
    _require_active_project(app)
    try:
        app.ActiveProject.Save()
        return {"saved": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProject", method="Save") from exc


# ── project_close ─────────────────────────────────────────────────────────────


def project_close(app: Any, save: bool) -> dict[str, Any]:
    """Close the active project, optionally saving it first."""
    _require_active_project(app)
    try:
        app.ActiveProject.Close(save)
        return {"closed": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProject", method="Close") from exc


# ── project_remove ────────────────────────────────────────────────────────────


def project_remove(app: Any, name: str, delete_from_disk: bool) -> dict[str, Any]:
    """Remove the named project from the active root."""
    _require_active_root(app)
    try:
        project = app.ActiveProjectRoot.Projects.Item(name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Project '{name}' not found in the active root.",
            error_code="BRIDGE_PROJECT_NOT_FOUND",
            recovery_hint="Use project_exists to verify the project name.",
        ) from exc
    try:
        project.Remove(delete_from_disk)
        return {"removed": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProject", method="Remove") from exc


# ── project_backup ────────────────────────────────────────────────────────────


def project_backup(app: Any, backup_path: str) -> dict[str, Any]:
    """Create a backup zip archive of the active project."""
    _require_active_project(app)
    try:
        app.ActiveProject.Backup(backup_path)
        return {"backup_path": backup_path, "success": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProject", method="Backup") from exc


# ── project_open_from_backup ──────────────────────────────────────────────────


def project_open_from_backup(app: Any, backup_path: str, project_name: str, overwrite: bool) -> dict[str, Any]:
    """Restore a project from a backup archive and open it."""
    try:
        project = app.Projects.OpenFromBackup(backup_path, project_name, overwrite)
        name = project_name
        try:
            name = str(project.Name)
        except Exception:  # noqa: BLE001
            pass
        return {"name": name, "restored": True}
    except BridgeOperationError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjects", method="OpenFromBackup") from exc


# ── project_exists ────────────────────────────────────────────────────────────


def project_exists(app: Any, name: str) -> dict[str, Any]:
    """Check whether *name* exists in the active project root."""
    _require_active_root(app)
    try:
        exists = bool(app.ActiveProjectRoot.Projects.Contains(name))
        return {"name": name, "exists": exists}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjects", method="Contains") from exc


# ── project_get_info ──────────────────────────────────────────────────────────


def project_get_info(app: Any) -> dict[str, Any]:
    """Return metadata about the active project."""
    project = _require_active_project(app)
    try:
        name = str(project.Name)
        path = ""
        try:
            path = str(project.DirectoryName)
        except Exception:  # noqa: BLE001
            pass
        is_modified = False
        try:
            is_modified = bool(project.IsModified)
        except Exception:  # noqa: BLE001
            pass
        exp_count = 0
        try:
            exp_count = int(project.Experiments.Count)
        except Exception:  # noqa: BLE001
            pass
        return {
            "name": name,
            "path": path,
            "is_modified": is_modified,
            "experiment_count": exp_count,
        }
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProject", method="Name") from exc


# ── experiment_create ─────────────────────────────────────────────────────────


def experiment_create(app: Any, name: str, activate: bool) -> dict[str, Any]:
    """Create a new experiment in the active project."""
    _require_active_project(app)
    try:
        app.ActiveProject.Experiments.Add(name, activate)
        return {"name": name, "created": True, "is_active": activate}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiments", method="Add") from exc


# ── experiment_activate ───────────────────────────────────────────────────────


def experiment_activate(app: Any, name: str) -> dict[str, Any]:
    """Activate the named experiment in the active project."""
    _require_active_project(app)
    try:
        exp = app.ActiveProject.Experiments.Item(name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Experiment '{name}' not found in the active project.",
            error_code="BRIDGE_EXPERIMENT_NOT_FOUND",
            recovery_hint="Use experiment_list to enumerate available experiments.",
        ) from exc
    try:
        exp.Activate()
        return {"activated": True, "name": name}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiment", method="Activate") from exc


# ── experiment_list ───────────────────────────────────────────────────────────


def experiment_list(app: Any) -> list[dict[str, Any]]:
    """Return a snapshot of all experiments in the active project."""
    _require_active_project(app)
    try:
        exps = app.ActiveProject.Experiments
        count = int(exps.Count)
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiments", method="Count") from exc

    result: list[dict[str, Any]] = []
    for i in range(0, count):
        try:
            exp = exps.Item(i)
            entry: dict[str, Any] = {"name": str(exp.Name)}
            result.append(entry)
        except Exception as exc:
            raise map_com_error(exc, interface="IXaExperiment", method="Name") from exc
    return result


# ── experiment_remove ─────────────────────────────────────────────────────────


def experiment_remove(app: Any, name: str, delete_from_disk: bool) -> dict[str, Any]:
    """Remove the named experiment from the active project.

    ``Remove`` lives on ``IXaExperiment`` (singular), not on the collection.
    Retrieve the experiment via ``Experiments.Item(name)`` first.

    ControlDesk raises ``COMException`` (E_FAIL) when the caller attempts to
    remove the currently active experiment.  We detect this upfront and raise
    a ``BridgePreconditionError`` so the LLM receives a clear, actionable
    message instead of a generic BRIDGE_OPERATION_FAILED.
    """
    _require_active_project(app)
    try:
        exp = app.ActiveProject.Experiments.Item(name)
        try:
            is_active = bool(exp.Active)
        except Exception:  # noqa: BLE001
            is_active = False
        if is_active:
            raise BridgePreconditionError(
                f"Cannot remove experiment '{name}' because it is currently active. "
                "Activate a different experiment first, then retry."
            )
        exp.Remove(delete_from_disk)
        return {"removed": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiment", method="Remove") from exc


# ── experiment_get_info ───────────────────────────────────────────────────────


def experiment_get_info(app: Any) -> dict[str, Any]:
    """Return metadata about the active experiment."""
    exp = _require_active_experiment(app)
    try:
        name = str(exp.Name)
        platform_count = 0
        try:
            platform_count = int(exp.Platforms.Count)
        except Exception:  # noqa: BLE001
            pass
        return {"name": name, "platform_count": platform_count}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiment", method="Name") from exc


# ── experiment_export ─────────────────────────────────────────────────────────


def experiment_export(app: Any, export_path: str) -> dict[str, Any]:
    """Export the active experiment to a .DSA archive file."""
    exp = _require_active_experiment(app)
    try:
        exp.Export(export_path)
        return {"export_path": export_path, "success": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiment", method="Export") from exc


# ── experiment_import ─────────────────────────────────────────────────────────


def experiment_import(app: Any, import_path: str, new_experiment_name: str) -> dict[str, Any]:
    """Import a .DSA experiment archive into the active project.

    ``IXaExperiments.Import`` requires three positional arguments:
    ``ArchiveFullPath``, ``NewExperimentName``, and (optional) ``AutoSaveActiveExperiment``.
    """
    _require_active_project(app)
    try:
        exp = app.ActiveProject.Experiments.Import(import_path, new_experiment_name, False)
        name = ""
        try:
            name = str(exp.Name)
        except Exception:  # noqa: BLE001
            pass
        return {"name": name, "imported": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiments", method="Import") from exc


# ── experiment_rename ─────────────────────────────────────────────────────────


def experiment_rename(app: Any, new_name: str) -> dict[str, Any]:
    """Rename the active experiment."""
    exp = _require_active_experiment(app)
    try:
        exp.Rename(new_name)
        return {"new_name": new_name, "renamed": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiment", method="Rename") from exc


# ── experiment_save_as ────────────────────────────────────────────────────────


def experiment_save_as(app: Any, new_name: str) -> dict[str, Any]:
    """Save the active experiment as a new copy with a different name."""
    exp = _require_active_experiment(app)
    try:
        exp.SaveAs(new_name)
        return {"new_name": new_name, "saved": True}
    except BridgePreconditionError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperiment", method="SaveAs") from exc


# ── project_configure_settings ────────────────────────────────────────────────


def project_configure_settings(
    app: Any,
    auto_save: bool | None,
    open_last_experiment_on_startup: bool | None,
) -> dict[str, Any]:
    """Apply general settings to the active project."""
    project = _require_active_project(app)
    try:
        if auto_save is not None:
            try:
                project.GeneralSettings.AutoSave = auto_save
            except Exception as exc:
                raise map_com_error(exc, interface="IXaProjectGeneralSettings", method="AutoSave") from exc
        if open_last_experiment_on_startup is not None:
            try:
                project.GeneralSettings.OpenLastExperimentOnStartup = open_last_experiment_on_startup
            except Exception as exc:
                raise map_com_error(
                    exc,
                    interface="IXaProjectGeneralSettings",
                    method="OpenLastExperimentOnStartup",
                ) from exc
        return {"configured": True}
    except BridgePreconditionError:
        raise
    except BridgeOperationError:
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjectGeneralSettings", method="Configure") from exc


# ── project_list ──────────────────────────────────────────────────────────────


def project_list(app: Any) -> list[dict[str, Any]]:
    """Return all projects across every registered project root.

    Enumerates ``app.ProjectRoots`` and, for each root, enumerates
    ``root.Projects``.  No active-root precondition — safe to call immediately
    after ControlDesk starts.

    Each entry contains:
      ``root_path`` — ``IXaProjectRoot.PathName``
      ``name``      — ``IXaProject.Name``
      ``full_path`` — ``IXaProject.FullPath`` (CDP file path)
    """
    try:
        roots_col = app.ProjectRoots
        roots_count = int(roots_col.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaProjectRoots", method="Count") from exc

    result: list[dict[str, Any]] = []
    for i in range(0, roots_count):
        try:
            root = roots_col.Item(i)
            root_path = str(root.PathName)
        except Exception as exc:
            raise map_com_error(exc, interface="IXaProjectRoot", method="PathName") from exc
        try:
            projects_col = root.Projects
            project_count = int(projects_col.Count)
        except Exception:  # noqa: BLE001
            continue
        for j in range(0, project_count):
            try:
                project = projects_col.Item(j)
                entry: dict[str, Any] = {
                    "root_path": root_path,
                    "name": str(project.Name),
                }
                try:
                    entry["full_path"] = str(project.FullPath)
                except Exception:  # noqa: BLE001
                    entry["full_path"] = ""
                result.append(entry)
            except Exception as exc:
                raise map_com_error(exc, interface="IXaProject", method="Name") from exc
    return result
