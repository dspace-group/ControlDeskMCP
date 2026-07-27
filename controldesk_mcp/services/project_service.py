"""Service facade for ControlDesk project and experiment lifecycle operations.

Owns: orchestration of project root management, project CRUD, and experiment lifecycle.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.project import (
    ExperimentActivateInput,
    ExperimentActivateResult,
    ExperimentCreateInput,
    ExperimentCreateResult,
    ExperimentExportInput,
    ExperimentExportResult,
    ExperimentGetInfoResult,
    ExperimentImportInput,
    ExperimentImportResult,
    ExperimentListResult,
    ExperimentRemoveInput,
    ExperimentRemoveResult,
    ExperimentRenameInput,
    ExperimentRenameResult,
    ExperimentSaveAsInput,
    ExperimentSaveAsResult,
    ProjectBackupInput,
    ProjectBackupResult,
    ProjectCloseInput,
    ProjectCloseResult,
    ProjectConfigureSettingsInput,
    ProjectConfigureSettingsResult,
    ProjectCreateInput,
    ProjectCreateResult,
    ProjectExistsInput,
    ProjectExistsResult,
    ProjectGetInfoResult,
    ProjectListRecentInput,
    ProjectListRecentResult,
    ProjectListResult,
    ProjectOpenFromBackupInput,
    ProjectOpenFromBackupResult,
    ProjectOpenInput,
    ProjectOpenResult,
    ProjectRemoveInput,
    ProjectRemoveResult,
    ProjectRootActivateInput,
    ProjectRootActivateResult,
    ProjectRootAddInput,
    ProjectRootAddResult,
    ProjectRootListResult,
    ProjectRootRemoveInput,
    ProjectRootRemoveResult,
    ProjectSaveResult,
)
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _get_app():
    return com_bridge.get_connection().get_app()


async def project_root_add(params: ProjectRootAddInput) -> ProjectRootAddResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_root_add, app, params.path
        )
        return ProjectRootAddResult(
            path=result["path"],
            added=result["added"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_root_add failed: %s", exc)
        return build_envelope(exc)


async def project_root_activate(
    params: ProjectRootActivateInput,
) -> ProjectRootActivateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_root_activate, app, params.path
        )
        return ProjectRootActivateResult(
            activated=result["activated"],
            path=result["path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_root_activate failed: %s", exc)
        return build_envelope(exc)


async def project_root_list() -> ProjectRootListResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        roots = await com_bridge.dispatch(com_bridge.domains.project_com.project_root_list, app)
        return ProjectRootListResult(
            roots=roots,
            count=len(roots),
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_root_list failed: %s", exc)
        return build_envelope(exc)


async def project_root_remove(
    params: ProjectRootRemoveInput,
) -> ProjectRootRemoveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_root_remove, app, params.path
        )
        return ProjectRootRemoveResult(
            removed=result["removed"],
            path=result["path"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_root_remove failed: %s", exc)
        return build_envelope(exc)


async def project_create(params: ProjectCreateInput) -> ProjectCreateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_create, app, params.name
        )
        return ProjectCreateResult(
            name=result["name"],
            path=result["path"],
            created=result["created"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_create failed: %s", exc)
        return build_envelope(exc)


async def project_open(params: ProjectOpenInput) -> ProjectOpenResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_open, app, params.name
        )
        return ProjectOpenResult(
            name=result["name"],
            open=result["open"],
            experiment_count=result["experiment_count"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_open failed: %s", exc)
        return build_envelope(exc)


async def project_save() -> ProjectSaveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.project_com.project_save, app)
        return ProjectSaveResult(
            saved=result["saved"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_save failed: %s", exc)
        return build_envelope(exc)


async def project_close(params: ProjectCloseInput) -> ProjectCloseResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_close, app, params.save
        )
        return ProjectCloseResult(
            closed=result["closed"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_close failed: %s", exc)
        return build_envelope(exc)


async def project_remove(params: ProjectRemoveInput) -> ProjectRemoveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_remove,
            app,
            params.name,
            params.delete_from_disk,
        )
        return ProjectRemoveResult(
            removed=result["removed"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_remove failed: %s", exc)
        return build_envelope(exc)


async def project_backup(params: ProjectBackupInput) -> ProjectBackupResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_backup, app, params.backup_path
        )
        return ProjectBackupResult(
            backup_path=result["backup_path"],
            success=result["success"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_backup failed: %s", exc)
        return build_envelope(exc)


async def project_open_from_backup(
    params: ProjectOpenFromBackupInput,
) -> ProjectOpenFromBackupResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_open_from_backup,
            app,
            params.backup_path,
            params.project_name,
            params.overwrite,
        )
        return ProjectOpenFromBackupResult(
            name=result["name"],
            restored=result["restored"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_open_from_backup failed: %s", exc)
        return build_envelope(exc)


async def project_exists(params: ProjectExistsInput) -> ProjectExistsResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_exists, app, params.name
        )
        return ProjectExistsResult(
            name=result["name"],
            exists=result["exists"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_exists failed: %s", exc)
        return build_envelope(exc)


async def project_get_info() -> ProjectGetInfoResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.project_com.project_get_info, app)
        return ProjectGetInfoResult(
            name=result["name"],
            path=result["path"],
            is_modified=result["is_modified"],
            experiment_count=result["experiment_count"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_get_info failed: %s", exc)
        return build_envelope(exc)


async def experiment_create(
    params: ExperimentCreateInput,
) -> ExperimentCreateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.experiment_create, app, params.name, params.activate
        )
        return ExperimentCreateResult(
            name=result["name"],
            created=result["created"],
            is_active=result["is_active"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_create failed: %s", exc)
        return build_envelope(exc)


async def experiment_activate(
    params: ExperimentActivateInput,
) -> ExperimentActivateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.experiment_activate, app, params.name
        )
        return ExperimentActivateResult(
            activated=result["activated"],
            name=result["name"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_activate failed: %s", exc)
        return build_envelope(exc)


async def experiment_list() -> ExperimentListResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        experiments = await com_bridge.dispatch(com_bridge.domains.project_com.experiment_list, app)
        return ExperimentListResult(
            experiments=experiments,
            count=len(experiments),
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_list failed: %s", exc)
        return build_envelope(exc)


async def experiment_remove(
    params: ExperimentRemoveInput,
) -> ExperimentRemoveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.experiment_remove,
            app,
            params.name,
            params.delete_from_disk,
        )
        return ExperimentRemoveResult(
            removed=result["removed"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_remove failed: %s", exc)
        return build_envelope(exc)


async def experiment_get_info() -> ExperimentGetInfoResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(com_bridge.domains.project_com.experiment_get_info, app)
        return ExperimentGetInfoResult(
            name=result["name"],
            platform_count=result["platform_count"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_get_info failed: %s", exc)
        return build_envelope(exc)


async def experiment_export(
    params: ExperimentExportInput,
) -> ExperimentExportResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.experiment_export, app, params.export_path
        )
        return ExperimentExportResult(
            export_path=result["export_path"],
            success=result["success"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_export failed: %s", exc)
        return build_envelope(exc)


async def experiment_import(
    params: ExperimentImportInput,
) -> ExperimentImportResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        # Derive experiment name from archive filename when caller leaves it empty
        exp_name = params.new_experiment_name.strip()
        if not exp_name:
            exp_name = os.path.splitext(os.path.basename(params.import_path))[0]
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.experiment_import,
            app,
            params.import_path,
            exp_name,
        )
        return ExperimentImportResult(
            name=result["name"],
            imported=result["imported"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_import failed: %s", exc)
        return build_envelope(exc)


async def experiment_rename(
    params: ExperimentRenameInput,
) -> ExperimentRenameResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.experiment_rename, app, params.new_name
        )
        return ExperimentRenameResult(
            new_name=result["new_name"],
            renamed=result["renamed"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_rename failed: %s", exc)
        return build_envelope(exc)


async def experiment_save_as(
    params: ExperimentSaveAsInput,
) -> ExperimentSaveAsResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.experiment_save_as, app, params.new_name
        )
        return ExperimentSaveAsResult(
            new_name=result["new_name"],
            saved=result["saved"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("experiment_save_as failed: %s", exc)
        return build_envelope(exc)


async def project_configure_settings(
    params: ProjectConfigureSettingsInput,
) -> ProjectConfigureSettingsResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        result = await com_bridge.dispatch(
            com_bridge.domains.project_com.project_configure_settings,
            app,
            params.auto_save,
            params.open_last_experiment_on_startup,
        )
        return ProjectConfigureSettingsResult(
            configured=result["configured"],
            timestamp_utc=_now_utc(),
        )
    except BridgeError as exc:
        _log.warning("project_configure_settings failed: %s", exc)
        return build_envelope(exc)


async def project_list() -> ProjectListResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app)
        raw_projects = await com_bridge.dispatch(com_bridge.domains.project_com.project_list, app)
    except BridgeError as exc:
        _log.warning("project_list failed: %s", exc)
        return build_envelope(exc)

    enriched: list[dict] = []
    for proj in raw_projects:
        full_path: str = proj.get("full_path", "")
        proj_dir = os.path.dirname(full_path) if full_path else ""
        entry = dict(proj)
        entry["experiments"] = _experiments_from_disk(proj_dir) if proj_dir else []
        enriched.append(entry)

    return ProjectListResult(
        projects=enriched,
        count=len(enriched),
        timestamp_utc=_now_utc(),
    )


def _experiments_from_disk(project_dir: str) -> list[str]:
    """Scan *project_dir* for experiment names without opening the project.

    ControlDesk stores each experiment as a subdirectory inside the project
    directory.  The presence of a ``.CDE`` file named after the folder confirms
    it is an experiment directory (e.g. ``MCP_Exp/MCP_Exp.CDE``).

    Returns a sorted, deduplicated list of experiment names.
    """
    names: set[str] = set()
    try:
        for entry in os.scandir(project_dir):
            if entry.is_dir():
                try:
                    for sub in os.scandir(entry.path):
                        if sub.is_file() and sub.name.lower().endswith(".cde"):
                            # Subdirectory name is the experiment name
                            names.add(entry.name)
                            break
                except OSError:
                    pass
    except OSError:
        pass
    return sorted(names)


def _mtime_utc(path: str) -> str:
    """Return ISO-8601 UTC modification time for *path*, or empty string on error."""
    if not path:
        return ""
    try:
        mtime = os.path.getmtime(path)
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat(timespec="seconds")
    except OSError:
        return ""


async def project_list_recent(
    params: ProjectListRecentInput,
) -> ProjectListRecentResult | ErrorEnvelope:
    """Return projects sorted by last-modified timestamp (most recent first).

    Filesystem metadata (last_modified_utc, experiments) is resolved from the
    project CDP file and its parent directory — no project needs to be opened.
    """
    try:
        app = await com_bridge.dispatch(_get_app)
        raw_projects = await com_bridge.dispatch(com_bridge.domains.project_com.project_list, app)
    except BridgeError as exc:
        _log.warning("project_list_recent failed: %s", exc)
        return build_envelope(exc)

    enriched: list[dict] = []
    for proj in raw_projects:
        full_path: str = proj.get("full_path", "")
        proj_dir = os.path.dirname(full_path) if full_path else ""
        entry = dict(proj)
        entry["last_modified_utc"] = _mtime_utc(full_path)
        entry["experiments"] = _experiments_from_disk(proj_dir) if proj_dir else []
        enriched.append(entry)

    # Sort: projects with a known timestamp first (most recent), unknowns last
    enriched.sort(key=lambda p: p["last_modified_utc"], reverse=True)
    limited = enriched[: params.limit]

    return ProjectListRecentResult(
        projects=limited,
        count=len(limited),
        timestamp_utc=_now_utc(),
    )
