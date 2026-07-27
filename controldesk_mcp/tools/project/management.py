"""MCP tools for ControlDesk project and experiment lifecycle management.

Tools implemented (domain: project & experiment management):

  MAIN (always loaded):
    project_list_recent    — List recently used projects; primary discovery entry point
    project_open           — Open an existing project from the active root

  ADD_ON lazy (access via project_discover):
    GROUP: PROJECT_ROOTS
      project_root_manage  — Register, activate, list, or remove project root folders
                             (actions: add, activate, list, remove)
    GROUP: PROJECT_MANAGEMENT
      project_manage       — Core project lifecycle operations
                             (actions: create, save, close, remove, exists, get_info, configure, list)
      project_backup_manage — Backup and restore operations
                             (actions: backup, restore)
    GROUP: EXPERIMENT_MANAGEMENT
      experiment_manage    — Core experiment lifecycle operations
                             (actions: create, activate, list, remove, get_info)
      experiment_io_manage — Experiment I/O and copy operations
                             (actions: export, import, rename, save_as)

  META / Discovery:
    project_discover       — Returns a catalogue of all lazy add-on tools and their actions

Layer: MCP Tool (thin adapter) — owns @mcp.tool annotations and parameter declarations only.
All orchestration is delegated to controldesk_mcp.services.project_service.
"""

from __future__ import annotations

from mcp.server.fastmcp import Context

from controldesk_mcp.config.settings import get_settings
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
    ExperimentIoManageAction,
    ExperimentIoManageInput,
    ExperimentListResult,
    ExperimentManageAction,
    ExperimentManageInput,
    ExperimentRemoveInput,
    ExperimentRemoveResult,
    ExperimentRenameInput,
    ExperimentRenameResult,
    ExperimentSaveAsInput,
    ExperimentSaveAsResult,
    ProjectBackupInput,
    ProjectBackupManageAction,
    ProjectBackupManageInput,
    ProjectBackupResult,
    ProjectCloseInput,
    ProjectCloseResult,
    ProjectConfigureSettingsInput,
    ProjectConfigureSettingsResult,
    ProjectCreateInput,
    ProjectCreateResult,
    ProjectDiscoverResult,
    ProjectExistsInput,
    ProjectExistsResult,
    ProjectGetInfoResult,
    ProjectListRecentInput,
    ProjectListRecentResult,
    ProjectListResult,
    ProjectManageAction,
    ProjectManageInput,
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
    ProjectRootManageAction,
    ProjectRootManageInput,
    ProjectRootRemoveInput,
    ProjectRootRemoveResult,
    ProjectSaveResult,
    ToolActionEntry,
)
from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, MetaInfo, ToolDomain, ToolGroup
from controldesk_mcp.server.app import mcp
from controldesk_mcp.server.server import MCPToolCategory
from controldesk_mcp.services import project_service
from controldesk_mcp.utils.pagination import paginate

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN tools — always loaded, ≤ 3 per domain
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 1 — project_list_recent ─────────────────────────────────────────────


@mcp.tool(
    name="project_list_recent",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Lists the most recently used projects across all registered project roots, "
        "ordered by last-modified timestamp (most recent first). "
        "Mirrors ControlDesk's 'Recent' section: use this to pick a project to open "
        "without knowing its exact name in advance. "
        "Each entry includes root_path, name, full_path, last_modified_utc "
        "(ISO-8601 UTC timestamp of the project file), and experiments "
        "(list of experiment names discovered from the project directory on disk). "
        "Use the 'limit' parameter to control how many projects are returned (default 10). "
        "No prerequisite — safe to call as soon as ControlDesk is running. "
        "IMPORTANT: To create, save, close, remove, configure, or back up a project, "
        "or to create/manage experiments, call project_discover first — "
        "it activates project_manage, project_backup_manage, experiment_manage, "
        "and experiment_io_manage tools."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.PROJECT, ToolGroup.PROJECT_MANAGEMENT),
)
async def project_list_recent(
    params: ProjectListRecentInput,
) -> ProjectListRecentResult | ErrorEnvelope:
    result = await project_service.project_list_recent(params)
    if isinstance(result, ErrorEnvelope):
        return result
    return ProjectListRecentResult(**paginate(result.model_dump(), params.offset, params.limit, "projects"))


# ── Tool 2 — project_open ─────────────────────────────────────────────────────


@mcp.tool(
    name="project_open",
    tool_category=MCPToolCategory.MAIN,
    description=(
        "Opens an existing ControlDesk project by name from the active project root, "
        "making it the active project for all subsequent operations. "
        "Use project_list_recent to discover available project names beforehand. "
        "Prerequisite: at least one project root must be registered "
        "(use project_discover → project_root_manage to add one if needed). "
        "IMPORTANT: To create, save, close, remove, configure, or back up a project, "
        "or to create/manage experiments, call project_discover first — "
        "it activates project_manage, project_backup_manage, experiment_manage, "
        "and experiment_io_manage tools."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.PROJECT, ToolGroup.PROJECT_MANAGEMENT),
)
async def project_open(params: ProjectOpenInput) -> ProjectOpenResult | ErrorEnvelope:
    return await project_service.project_open(params)


# ═══════════════════════════════════════════════════════════════════════════════
# ADD_ON lazy tools — deferred; accessed after calling project_discover
# ═══════════════════════════════════════════════════════════════════════════════

# ── GROUP: PROJECT_ROOTS ──────────────────────────────────────────────────────
# ── Tool 3 — project_root_manage ─────────────────────────────────────────────


@mcp.tool(
    name="project_root_manage",
    tool_category=MCPToolCategory.ADD_ON,
    description=(
        "Manages project root folder operations. Set 'action' to specify what to do: "
        "'add' — register a folder as a ControlDesk project root (requires path); "
        "'activate' — set a registered root as the active working root (requires path); "
        "'list' — list all registered roots with path and project count; "
        "'remove' — unregister a root from ControlDesk, files remain on disk (requires path). "
        "Use project_discover to see a full catalogue of available project tools."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.PROJECT, ToolGroup.PROJECT_ROOTS),
    lazy_loading=True,
)
async def project_root_manage(
    params: ProjectRootManageInput,
) -> ProjectRootAddResult | ProjectRootActivateResult | ProjectRootListResult | ProjectRootRemoveResult | ErrorEnvelope:
    if params.action == ProjectRootManageAction.add:
        if params.path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="path is required when action='add'.",
                recovery_hint="Set path to the absolute folder path to register as a project root.",
            )
        return await project_service.project_root_add(ProjectRootAddInput(path=params.path))
    if params.action == ProjectRootManageAction.activate:
        if params.path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="path is required when action='activate'.",
                recovery_hint="Set path to the absolute path of an already-registered project root.",
            )
        return await project_service.project_root_activate(ProjectRootActivateInput(path=params.path))
    if params.action == ProjectRootManageAction.list:
        result = await project_service.project_root_list()
        if isinstance(result, ErrorEnvelope):
            return result
        return ProjectRootListResult(**paginate(result.model_dump(), params.offset, params.limit, "roots"))
    # remove
    if params.path is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="path is required when action='remove'.",
            recovery_hint="Set path to the absolute path of the project root to unregister.",
        )
    return await project_service.project_root_remove(ProjectRootRemoveInput(path=params.path))


# ── GROUP: PROJECT_MANAGEMENT ─────────────────────────────────────────────────
# ── Tool 4 — project_manage ───────────────────────────────────────────────────


@mcp.tool(
    name="project_manage",
    tool_category=MCPToolCategory.ADD_ON,
    description=(
        "Manages core project lifecycle operations. Set 'action' to specify what to do: "
        "'create' — create a new project in the active root (requires name); "
        "'save' — save all unsaved changes in the active project; "
        "'close' — close the active project (optional: save=True/False); "
        "'remove' — remove a project from the active root (requires name; optional: delete_from_disk); "
        "'exists' — check whether a project name exists in the active root (requires name); "
        "'get_info' — get metadata about the active project (name, path, experiment count); "
        "'configure' — configure project settings (optional: auto_save, open_last_experiment_on_startup); "
        "'list' — list all projects across every registered root with pagination. "
        "For backup/restore operations use project_backup_manage. "
        "Use project_discover to see a full catalogue of available project tools."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.PROJECT, ToolGroup.PROJECT_MANAGEMENT),
    lazy_loading=True,
)
async def project_manage(
    params: ProjectManageInput,
) -> (
    ProjectCreateResult
    | ProjectSaveResult
    | ProjectCloseResult
    | ProjectRemoveResult
    | ProjectExistsResult
    | ProjectGetInfoResult
    | ProjectConfigureSettingsResult
    | ProjectListResult
    | ErrorEnvelope
):
    if params.action == ProjectManageAction.create:
        if params.name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="name is required when action='create'.",
                recovery_hint="Set name to the desired project name.",
            )
        return await project_service.project_create(ProjectCreateInput(name=params.name))
    if params.action == ProjectManageAction.save:
        return await project_service.project_save()
    if params.action == ProjectManageAction.close:
        return await project_service.project_close(ProjectCloseInput(save=params.save))
    if params.action == ProjectManageAction.remove:
        if params.name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="name is required when action='remove'.",
                recovery_hint="Set name to the name of the project to remove.",
            )
        return await project_service.project_remove(
            ProjectRemoveInput(name=params.name, delete_from_disk=params.delete_from_disk)
        )
    if params.action == ProjectManageAction.exists:
        if params.name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="name is required when action='exists'.",
                recovery_hint="Set name to the project name to check.",
            )
        return await project_service.project_exists(ProjectExistsInput(name=params.name))
    if params.action == ProjectManageAction.get_info:
        return await project_service.project_get_info()
    if params.action == ProjectManageAction.configure:
        return await project_service.project_configure_settings(
            ProjectConfigureSettingsInput(
                auto_save=params.auto_save,
                open_last_experiment_on_startup=params.open_last_experiment_on_startup,
            )
        )
    # list
    result = await project_service.project_list()
    if isinstance(result, ErrorEnvelope):
        return result
    return ProjectListResult(**paginate(result.model_dump(), params.offset, params.limit, "projects"))


# ── Tool 5 — project_backup_manage ───────────────────────────────────────────


@mcp.tool(
    name="project_backup_manage",
    tool_category=MCPToolCategory.ADD_ON,
    description=(
        "Manages project backup and restore operations. Set 'action' to specify what to do: "
        "'backup' — create a zip archive backup of the active project (requires backup_path); "
        "'restore' — restore a project from a backup zip archive and open it "
        "(requires backup_path; optional: project_name, overwrite). "
        "Use project_discover to see a full catalogue of available project tools."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.PROJECT, ToolGroup.PROJECT_MANAGEMENT),
    lazy_loading=True,
)
async def project_backup_manage(
    params: ProjectBackupManageInput,
) -> ProjectBackupResult | ProjectOpenFromBackupResult | ErrorEnvelope:
    if params.action == ProjectBackupManageAction.backup:
        if params.backup_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="backup_path is required when action='backup'.",
                recovery_hint="Set backup_path to the absolute destination path for the zip archive.",
            )
        return await project_service.project_backup(ProjectBackupInput(backup_path=params.backup_path))
    # restore
    if params.backup_path is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="backup_path is required when action='restore'.",
            recovery_hint="Set backup_path to the absolute path of the backup zip archive.",
        )
    return await project_service.project_open_from_backup(
        ProjectOpenFromBackupInput(
            backup_path=params.backup_path,
            project_name=params.project_name,
            overwrite=params.overwrite,
        )
    )


# ── GROUP: EXPERIMENT_MANAGEMENT ─────────────────────────────────────────────
# ── Tool 6 — experiment_manage ────────────────────────────────────────────────


@mcp.tool(
    name="experiment_manage",
    tool_category=MCPToolCategory.ADD_ON,
    description=(
        "Manages core experiment lifecycle operations within the active project. "
        "Set 'action' to specify what to do: "
        "'create' — create a new experiment (requires name; optional: activate=True); "
        "'activate' — activate an existing experiment (requires name); "
        "'list' — list all experiments in the active project with pagination; "
        "'remove' — remove an experiment (requires name; optional: delete_from_disk); "
        "'get_info' — get metadata about the active experiment (name, platform count). "
        "For export/import/rename/save_as use experiment_io_manage. "
        "Use project_discover to see a full catalogue of available project tools."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=True, idempotent=False),
    meta=MetaInfo(ToolDomain.PROJECT, ToolGroup.EXPERIMENT_MANAGEMENT),
    lazy_loading=True,
)
async def experiment_manage(
    params: ExperimentManageInput,
) -> (
    ExperimentCreateResult
    | ExperimentActivateResult
    | ExperimentListResult
    | ExperimentRemoveResult
    | ExperimentGetInfoResult
    | ErrorEnvelope
):
    if params.action == ExperimentManageAction.create:
        if params.name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="name is required when action='create'.",
                recovery_hint="Set name to the desired experiment name.",
            )
        return await project_service.experiment_create(
            ExperimentCreateInput(name=params.name, activate=params.activate)
        )
    if params.action == ExperimentManageAction.activate:
        if params.name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="name is required when action='activate'.",
                recovery_hint="Set name to the experiment name to activate.",
            )
        return await project_service.experiment_activate(ExperimentActivateInput(name=params.name))
    if params.action == ExperimentManageAction.list:
        result = await project_service.experiment_list()
        if isinstance(result, ErrorEnvelope):
            return result
        return ExperimentListResult(**paginate(result.model_dump(), params.offset, params.limit, "experiments"))
    if params.action == ExperimentManageAction.remove:
        if params.name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="name is required when action='remove'.",
                recovery_hint="Set name to the experiment name to remove.",
            )
        return await project_service.experiment_remove(
            ExperimentRemoveInput(name=params.name, delete_from_disk=params.delete_from_disk)
        )
    # get_info
    return await project_service.experiment_get_info()


# ── Tool 7 — experiment_io_manage ────────────────────────────────────────────


@mcp.tool(
    name="experiment_io_manage",
    tool_category=MCPToolCategory.ADD_ON,
    description=(
        "Manages experiment I/O and copy operations within the active project. "
        "Set 'action' to specify what to do: "
        "'export' — export the active experiment to a .DSA archive file (requires export_path); "
        "'import' — import a .DSA experiment archive into the active project "
        "(requires import_path; optional: new_experiment_name); "
        "'rename' — rename the active experiment (requires new_name); "
        "'save_as' — save the active experiment as a new copy with a different name (requires new_name). "
        "For create/activate/list/remove/get_info use experiment_manage. "
        "Use project_discover to see a full catalogue of available project tools."
    ),
    annotations=AnnotationInfo(read_only=False, destructive=False, idempotent=False),
    meta=MetaInfo(ToolDomain.PROJECT, ToolGroup.EXPERIMENT_MANAGEMENT),
    lazy_loading=True,
)
async def experiment_io_manage(
    params: ExperimentIoManageInput,
) -> ExperimentExportResult | ExperimentImportResult | ExperimentRenameResult | ExperimentSaveAsResult | ErrorEnvelope:
    if params.action == ExperimentIoManageAction.export:
        if params.export_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="export_path is required when action='export'.",
                recovery_hint="Set export_path to the absolute destination path for the .DSA file.",
            )
        return await project_service.experiment_export(ExperimentExportInput(export_path=params.export_path))
    if params.action == ExperimentIoManageAction.import_:
        if params.import_path is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="import_path is required when action='import'.",
                recovery_hint="Set import_path to the absolute path of the .DSA archive to import.",
            )
        return await project_service.experiment_import(
            ExperimentImportInput(
                import_path=params.import_path,
                new_experiment_name=params.new_experiment_name,
            )
        )
    if params.action == ExperimentIoManageAction.rename:
        if params.new_name is None:
            return ErrorEnvelope(
                error_code="MISSING_PARAM",
                category="INPUT_VALIDATION",
                message="new_name is required when action='rename'.",
                recovery_hint="Set new_name to the desired new experiment name.",
            )
        return await project_service.experiment_rename(ExperimentRenameInput(new_name=params.new_name))
    # save_as
    if params.new_name is None:
        return ErrorEnvelope(
            error_code="MISSING_PARAM",
            category="INPUT_VALIDATION",
            message="new_name is required when action='save_as'.",
            recovery_hint="Set new_name to the name for the new experiment copy.",
        )
    return await project_service.experiment_save_as(ExperimentSaveAsInput(new_name=params.new_name))


# ═══════════════════════════════════════════════════════════════════════════════
# META / Discovery tool — registered only when lazy ADD_ON tools exist
# ═══════════════════════════════════════════════════════════════════════════════

# ── Tool 8 — project_discover ────────────────────────────────────────────────


@mcp.tool(
    name="project_discover",
    tool_category=MCPToolCategory.SEARCH,
    description=(
        "Returns a catalogue of all project management tools that are not loaded by default. "
        "ALWAYS call this tool first when you need to: "
        "CREATE a new project or experiment, "
        "save, close, remove, configure, or back up a project, "
        "manage project root folders, "
        "or create, activate, rename, export, or import experiments. "
        "The catalogue lists each tool name, its purpose, all supported actions, "
        "and the required parameters per action. "
        "After calling this tool, use the listed tool names and actions directly."
    ),
    annotations=AnnotationInfo(read_only=True, destructive=False, idempotent=True),
    meta=MetaInfo(ToolDomain.PROJECT, ToolGroup.PROJECT_MANAGEMENT),
)
async def project_discover(ctx: Context) -> ProjectDiscoverResult | ErrorEnvelope:
    cfg = get_settings()
    if cfg.tool_ttl_enabled:
        await mcp.evict_stale_domains(cfg.tool_ttl_seconds, ctx)
    await mcp.activate_domain_tools(ToolDomain.PROJECT, ctx)
    return ProjectDiscoverResult(
        tools=[
            ToolActionEntry(
                tool_name="project_root_manage",
                purpose="Register, activate, list, or remove project root folders.",
                actions=["add", "activate", "list", "remove"],
                required_params_per_action={
                    "add": ["path"],
                    "activate": ["path"],
                    "list": [],
                    "remove": ["path"],
                },
            ),
            ToolActionEntry(
                tool_name="project_manage",
                purpose=(
                    "Core project lifecycle: create, save, close, remove, "
                    "check existence, get metadata, configure settings, list."
                ),
                actions=[
                    "create",
                    "save",
                    "close",
                    "remove",
                    "exists",
                    "get_info",
                    "configure",
                    "list",
                ],
                required_params_per_action={
                    "create": ["name"],
                    "save": [],
                    "close": [],
                    "remove": ["name"],
                    "exists": ["name"],
                    "get_info": [],
                    "configure": [],
                    "list": [],
                },
            ),
            ToolActionEntry(
                tool_name="project_backup_manage",
                purpose="Backup the active project to a zip archive, or restore from one.",
                actions=["backup", "restore"],
                required_params_per_action={
                    "backup": ["backup_path"],
                    "restore": ["backup_path"],
                },
            ),
            ToolActionEntry(
                tool_name="experiment_manage",
                purpose=("Core experiment lifecycle: create, activate, list, remove, get metadata."),
                actions=["create", "activate", "list", "remove", "get_info"],
                required_params_per_action={
                    "create": ["name"],
                    "activate": ["name"],
                    "list": [],
                    "remove": ["name"],
                    "get_info": [],
                },
            ),
            ToolActionEntry(
                tool_name="experiment_io_manage",
                purpose=("Experiment I/O and copy: export to .DSA, import from .DSA, rename, save as copy."),
                actions=["export", "import", "rename", "save_as"],
                required_params_per_action={
                    "export": ["export_path"],
                    "import": ["import_path"],
                    "rename": ["new_name"],
                    "save_as": ["new_name"],
                },
            ),
        ]
    )
