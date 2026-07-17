"""Pydantic input and response models for the project and experiment management domain.

Domain: ControlDesk project & experiment lifecycle
(project_root_add, project_create, project_open, experiment_create, etc.)

Convention: one models module per domain under sources/models/<domain>.py.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from sources.models.base import DictModelMixin


def _validate_abs_path(field_name: str, v: str) -> str:
    """Reject relative paths and directory-traversal segments."""
    p = Path(v)
    if not p.is_absolute():
        raise ValueError(f"{field_name} must be an absolute path.")
    if ".." in p.parts:
        raise ValueError(f"{field_name} must not contain '..' segments.")
    return v


# ── Input models ──────────────────────────────────────────────────────────────


class ProjectRootAddInput(BaseModel):
    """Input for project_root_add."""

    path: str = Field(
        description="Absolute file-system path to the folder that acts as the project root.",
        examples=["C:\\MyProjects"],
    )


class ProjectRootActivateInput(BaseModel):
    """Input for project_root_activate."""

    path: str = Field(
        description="Absolute path of the project root to activate (must already be registered).",
        examples=["C:\\MyProjects"],
    )


class ProjectRootRemoveInput(BaseModel):
    """Input for project_root_remove."""

    path: str = Field(
        description="Absolute path of the project root to unregister from ControlDesk.",
        examples=["C:\\MyProjects"],
    )


class ProjectCreateInput(BaseModel):
    """Input for project_create."""

    name: str = Field(
        description="Name of the new project. Must be unique within the active project root.",
        examples=["ECU_TestProject"],
    )


class ProjectOpenInput(BaseModel):
    """Input for project_open."""

    name: str = Field(
        description="Name of an existing project inside the active project root.",
        examples=["ECU_TestProject"],
    )


class ProjectCloseInput(BaseModel):
    """Input for project_close."""

    save: bool = Field(
        default=True,
        description=(
            "If True the project is saved before closing. "
            "If False unsaved changes are discarded."
        ),
        examples=[True, False],
    )


class ProjectRemoveInput(BaseModel):
    """Input for project_remove."""

    name: str = Field(
        description=("Name of the project to remove from the active project root."),
        examples=["ECU_TestProject"],
    )
    delete_from_disk: bool = Field(
        default=False,
        description="If True the project folder is permanently deleted from disk.",
        examples=[False, True],
    )


class ProjectBackupInput(BaseModel):
    """Input for project_backup."""

    backup_path: str = Field(
        description="Absolute path for the backup zip archive (e.g. 'C:\\Backups\\proj.zip').",
        examples=["C:\\Backups\\ECU_TestProject_backup.zip"],
    )

    @field_validator("backup_path")
    @classmethod
    def _validate_backup_path(cls, v: str) -> str:
        return _validate_abs_path("backup_path", v)


class ProjectOpenFromBackupInput(BaseModel):
    """Input for project_open_from_backup."""

    backup_path: str = Field(
        description="Absolute path to the backup zip archive to restore from.",
        examples=["C:\\Backups\\ECU_TestProject_backup.zip"],
    )

    @field_validator("backup_path")
    @classmethod
    def _validate_backup_path(cls, v: str) -> str:
        return _validate_abs_path("backup_path", v)

    project_name: str = Field(
        default="",
        description=(
            "Name to assign to the restored project. "
            "Leave empty to use the name stored in the archive."
        ),
        examples=["ECU_TestProject", ""],
    )
    overwrite: bool = Field(
        default=False,
        description="If True and a project with the same name already exists, overwrite it.",
        examples=[False, True],
    )


class ProjectExistsInput(BaseModel):
    """Input for project_exists."""

    name: str = Field(
        description="Project name to check for existence in the active project root.",
        examples=["ECU_TestProject"],
    )


class ExperimentCreateInput(BaseModel):
    """Input for experiment_create."""

    name: str = Field(
        description="Name of the new experiment. Must be unique within the active project.",
        examples=["Experiment1"],
    )
    activate: bool = Field(
        default=True,
        description=(
            "If True the new experiment becomes the active experiment "
            "immediately after creation."
        ),
        examples=[True, False],
    )


class ExperimentActivateInput(BaseModel):
    """Input for experiment_activate."""

    name: str = Field(
        description="Name of an existing experiment in the active project to activate.",
        examples=["Experiment1"],
    )


class ExperimentRemoveInput(BaseModel):
    """Input for experiment_remove."""

    name: str = Field(
        description="Name of the experiment to remove from the active project.",
        examples=["Experiment1"],
    )
    delete_from_disk: bool = Field(
        default=False,
        description="If True the experiment folder is permanently deleted from disk.",
        examples=[False, True],
    )


class ExperimentExportInput(BaseModel):
    """Input for experiment_export."""

    export_path: str = Field(
        description="Absolute path for the exported .DSA file (e.g. 'C:\\Exports\\exp.dsa').",
        examples=["C:\\Exports\\Experiment1.dsa"],
    )

    @field_validator("export_path")
    @classmethod
    def _validate_export_path(cls, v: str) -> str:
        return _validate_abs_path("export_path", v)


class ExperimentImportInput(BaseModel):
    """Input for experiment_import."""

    import_path: str = Field(
        description="Absolute path of the .DSA file to import into the active project.",
        examples=["C:\\Exports\\Experiment1.dsa"],
    )

    @field_validator("import_path")
    @classmethod
    def _validate_import_path(cls, v: str) -> str:
        return _validate_abs_path("import_path", v)

    new_experiment_name: str = Field(
        default="",
        description=(
            "Name for the imported experiment. "
            "Leave empty to derive the name from the archive file name (without extension)."
        ),
        examples=["", "MyImportedExperiment"],
    )


class ExperimentRenameInput(BaseModel):
    """Input for experiment_rename."""

    new_name: str = Field(
        description="New name for the active experiment.",
        examples=["Experiment_Renamed"],
    )


class ExperimentSaveAsInput(BaseModel):
    """Input for experiment_save_as."""

    new_name: str = Field(
        description="Name for the new experiment copy created from the active experiment.",
        examples=["Experiment1_Copy"],
    )


class ProjectConfigureSettingsInput(BaseModel):
    """Input for project_configure_settings."""

    auto_save: bool | None = Field(
        default=None,
        description="Enable or disable auto-save for the active project. None = no change.",
        examples=[True, False, None],
    )
    open_last_experiment_on_startup: bool | None = Field(
        default=None,
        description=(
            "If True the last active experiment is reopened when the project is opened. "
            "None = no change."
        ),
        examples=[True, False, None],
    )


# ── Response models ───────────────────────────────────────────────────────────


class ProjectRootAddResult(DictModelMixin, BaseModel):
    """Successful response from project_root_add."""

    status: Literal["ok"] = "ok"
    path: str
    added: bool
    timestamp_utc: str


class ProjectRootActivateResult(DictModelMixin, BaseModel):
    """Successful response from project_root_activate."""

    status: Literal["ok"] = "ok"
    activated: bool
    path: str
    timestamp_utc: str


class ProjectRootListInput(BaseModel):
    """Input for project_root_list."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class ProjectRootListResult(DictModelMixin, BaseModel):
    """Successful response from project_root_list."""

    model_config = {"extra": "allow"}

    status: Literal["ok"] = "ok"
    roots: list[dict]
    count: int
    timestamp_utc: str


class ProjectRootRemoveResult(DictModelMixin, BaseModel):
    """Successful response from project_root_remove."""

    status: Literal["ok"] = "ok"
    removed: bool
    path: str
    timestamp_utc: str


class ProjectCreateResult(DictModelMixin, BaseModel):
    """Successful response from project_create."""

    status: Literal["ok"] = "ok"
    name: str
    path: str
    created: bool
    timestamp_utc: str


class ProjectOpenResult(DictModelMixin, BaseModel):
    """Successful response from project_open."""

    status: Literal["ok"] = "ok"
    name: str
    open: bool
    experiment_count: int
    timestamp_utc: str


class ProjectSaveResult(DictModelMixin, BaseModel):
    """Successful response from project_save."""

    status: Literal["ok"] = "ok"
    saved: bool
    timestamp_utc: str


class ProjectCloseResult(DictModelMixin, BaseModel):
    """Successful response from project_close."""

    status: Literal["ok"] = "ok"
    closed: bool
    timestamp_utc: str


class ProjectRemoveResult(DictModelMixin, BaseModel):
    """Successful response from project_remove."""

    status: Literal["ok"] = "ok"
    removed: bool
    timestamp_utc: str


class ProjectBackupResult(DictModelMixin, BaseModel):
    """Successful response from project_backup."""

    status: Literal["ok"] = "ok"
    backup_path: str
    success: bool
    timestamp_utc: str


class ProjectOpenFromBackupResult(DictModelMixin, BaseModel):
    """Successful response from project_open_from_backup."""

    status: Literal["ok"] = "ok"
    name: str
    restored: bool
    timestamp_utc: str


class ProjectExistsResult(DictModelMixin, BaseModel):
    """Successful response from project_exists."""

    status: Literal["ok"] = "ok"
    name: str
    exists: bool
    timestamp_utc: str


class ProjectGetInfoResult(DictModelMixin, BaseModel):
    """Successful response from project_get_info."""

    status: Literal["ok"] = "ok"
    name: str
    path: str
    is_modified: bool
    experiment_count: int
    timestamp_utc: str


class ExperimentCreateResult(DictModelMixin, BaseModel):
    """Successful response from experiment_create."""

    status: Literal["ok"] = "ok"
    name: str
    created: bool
    is_active: bool
    timestamp_utc: str


class ExperimentActivateResult(DictModelMixin, BaseModel):
    """Successful response from experiment_activate."""

    status: Literal["ok"] = "ok"
    activated: bool
    name: str
    timestamp_utc: str


class ExperimentListInput(BaseModel):
    """Input for experiment_list."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class ExperimentListResult(DictModelMixin, BaseModel):
    """Successful response from experiment_list."""

    model_config = {"extra": "allow"}

    status: Literal["ok"] = "ok"
    experiments: list[dict]
    count: int
    timestamp_utc: str


class ExperimentRemoveResult(DictModelMixin, BaseModel):
    """Successful response from experiment_remove."""

    status: Literal["ok"] = "ok"
    removed: bool
    timestamp_utc: str


class ExperimentGetInfoResult(DictModelMixin, BaseModel):
    """Successful response from experiment_get_info."""

    status: Literal["ok"] = "ok"
    name: str
    platform_count: int
    timestamp_utc: str


class ExperimentExportResult(DictModelMixin, BaseModel):
    """Successful response from experiment_export."""

    status: Literal["ok"] = "ok"
    export_path: str
    success: bool
    timestamp_utc: str


class ExperimentImportResult(DictModelMixin, BaseModel):
    """Successful response from experiment_import."""

    status: Literal["ok"] = "ok"
    name: str
    imported: bool
    timestamp_utc: str


class ExperimentRenameResult(DictModelMixin, BaseModel):
    """Successful response from experiment_rename."""

    status: Literal["ok"] = "ok"
    new_name: str
    renamed: bool
    timestamp_utc: str


class ExperimentSaveAsResult(DictModelMixin, BaseModel):
    """Successful response from experiment_save_as."""

    status: Literal["ok"] = "ok"
    new_name: str
    saved: bool
    timestamp_utc: str


class ProjectConfigureSettingsResult(DictModelMixin, BaseModel):
    """Successful response from project_configure_settings."""

    status: Literal["ok"] = "ok"
    configured: bool
    timestamp_utc: str


class ProjectListInput(BaseModel):
    """Input for project_list."""

    limit: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Maximum number of records to return per call.",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class ProjectListResult(DictModelMixin, BaseModel):
    """Successful response from project_list."""

    model_config = {"extra": "allow"}

    status: Literal["ok"] = "ok"
    projects: list[dict]
    count: int
    timestamp_utc: str


class ProjectListRecentInput(BaseModel):
    """Input for project_list_recent."""

    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description=(
            "Maximum number of projects to return, ordered by most recently used first. "
            "Mirrors the count shown in ControlDesk's Recent section."
        ),
        examples=[10, 5, 20],
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Zero-based offset for pagination.",
    )


class ProjectListRecentResult(DictModelMixin, BaseModel):
    """Successful response from project_list_recent."""

    model_config = {"extra": "allow"}

    status: Literal["ok"] = "ok"
    projects: list[dict]
    count: int
    timestamp_utc: str


# ── Manage-tool action enums ──────────────────────────────────────────────────


class ProjectRootManageAction(str, Enum):
    """Actions for project_root_manage."""

    add = "add"
    activate = "activate"
    list = "list"
    remove = "remove"


class ProjectManageAction(str, Enum):
    """Actions for project_manage (core lifecycle only)."""

    create = "create"
    save = "save"
    close = "close"
    remove = "remove"
    exists = "exists"
    get_info = "get_info"
    configure = "configure"
    list = "list"


class ProjectBackupManageAction(str, Enum):
    """Actions for project_backup_manage."""

    backup = "backup"
    restore = "restore"


class ExperimentManageAction(str, Enum):
    """Actions for experiment_manage (core lifecycle only)."""

    create = "create"
    activate = "activate"
    list = "list"
    remove = "remove"
    get_info = "get_info"


class ExperimentIoManageAction(str, Enum):
    """Actions for experiment_io_manage."""

    export = "export"
    import_ = "import"
    rename = "rename"
    save_as = "save_as"


# ── Manage-tool input models ──────────────────────────────────────────────────


class ProjectRootManageInput(BaseModel):
    """Input for project_root_manage."""

    action: ProjectRootManageAction = Field(
        description=(
            "Operation to perform: "
            "'add' — register a folder as a project root (requires path); "
            "'activate' — set a registered root as active (requires path); "
            "'list' — list all registered roots with pagination; "
            "'remove' — unregister a root (requires path)."
        )
    )
    path: str | None = Field(
        default=None,
        description="Absolute path of the project root. Required for: add, activate, remove.",
        examples=["C:\\MyProjects"],
    )
    offset: int = Field(default=0, ge=0, description="Zero-based offset for pagination.")
    limit: int = Field(
        default=200, ge=1, le=1000, description="Maximum number of records to return per call."
    )


class ProjectManageInput(BaseModel):
    """Input for project_manage (core lifecycle operations)."""

    action: ProjectManageAction = Field(
        description=(
            "Operation to perform: "
            "'create' — create a new project (requires name); "
            "'save' — save the active project; "
            "'close' — close the active project (optional: save=True/False); "
            "'remove' — remove a project (requires name; optional: delete_from_disk); "
            "'exists' — check if a project exists (requires name); "
            "'get_info' — get metadata about the active project; "
            "'configure' — configure project settings (optional: auto_save, open_last_experiment_on_startup); "
            "'list' — list all projects with pagination. "
            "For backup/restore use project_backup_manage."
        )
    )
    name: str | None = Field(
        default=None,
        description="Project name. Required for: create, remove, exists.",
        examples=["ECU_TestProject"],
    )
    save: bool = Field(
        default=True,
        description="Whether to save before closing. Used by: close.",
        examples=[True, False],
    )
    delete_from_disk: bool = Field(
        default=False,
        description="If True permanently delete files from disk. Used by: remove.",
        examples=[False, True],
    )
    auto_save: bool | None = Field(
        default=None,
        description="Enable or disable project auto-save. None = no change. Used by: configure.",
        examples=[True, False, None],
    )
    open_last_experiment_on_startup: bool | None = Field(
        default=None,
        description=(
            "Reopen last active experiment on project load. "
            "None = no change. Used by: configure."
        ),
        examples=[True, False, None],
    )
    offset: int = Field(default=0, ge=0, description="Zero-based offset for pagination.")
    limit: int = Field(
        default=200, ge=1, le=1000, description="Maximum number of records to return per call."
    )


class ProjectBackupManageInput(BaseModel):
    """Input for project_backup_manage."""

    action: ProjectBackupManageAction = Field(
        description=(
            "Operation to perform: "
            "'backup' — create a zip backup of the active project (requires backup_path); "
            "'restore' — open a project from a backup archive (requires backup_path; "
            "optional: project_name, overwrite)."
        )
    )
    backup_path: str | None = Field(
        default=None,
        description=(
            "Absolute path to the backup zip archive. "
            "Required for: backup (destination path), restore (source path)."
        ),
        examples=["C:\\Backups\\ECU_TestProject_backup.zip"],
    )
    project_name: str = Field(
        default="",
        description=(
            "Name to assign to the restored project. "
            "Leave empty to use the name from the archive. Used by: restore."
        ),
        examples=["ECU_TestProject", ""],
    )
    overwrite: bool = Field(
        default=False,
        description="If True overwrite an existing project with the same name. Used by: restore.",
        examples=[False, True],
    )


class ExperimentManageInput(BaseModel):
    """Input for experiment_manage (core lifecycle operations)."""

    action: ExperimentManageAction = Field(
        description=(
            "Operation to perform: "
            "'create' — create a new experiment (requires name; optional: activate); "
            "'activate' — activate an existing experiment (requires name); "
            "'list' — list all experiments with pagination; "
            "'remove' — remove an experiment (requires name; optional: delete_from_disk); "
            "'get_info' — get metadata about the active experiment. "
            "For export/import/rename/save_as use experiment_io_manage."
        )
    )
    name: str | None = Field(
        default=None,
        description="Experiment name. Required for: create, activate, remove.",
        examples=["Experiment1"],
    )
    activate: bool = Field(
        default=True,
        description="Auto-activate after creation. Used by: create.",
        examples=[True, False],
    )
    delete_from_disk: bool = Field(
        default=False,
        description="If True permanently delete files from disk. Used by: remove.",
        examples=[False, True],
    )
    offset: int = Field(default=0, ge=0, description="Zero-based offset for pagination.")
    limit: int = Field(
        default=200, ge=1, le=1000, description="Maximum number of records to return per call."
    )


class ExperimentIoManageInput(BaseModel):
    """Input for experiment_io_manage (I/O and copy operations)."""

    action: ExperimentIoManageAction = Field(
        description=(
            "Operation to perform: "
            "'export' — export the active experiment to a .DSA file (requires export_path); "
            "'import' — import a .DSA archive into the active project (requires import_path; "
            "optional: new_experiment_name); "
            "'rename' — rename the active experiment (requires new_name); "
            "'save_as' — save the active experiment as a new copy (requires new_name)."
        )
    )
    export_path: str | None = Field(
        default=None,
        description="Absolute path for the exported .DSA file. Required for: export.",
        examples=["C:\\Exports\\Experiment1.dsa"],
    )
    import_path: str | None = Field(
        default=None,
        description="Absolute path of the .DSA file to import. Required for: import.",
        examples=["C:\\Exports\\Experiment1.dsa"],
    )
    new_experiment_name: str = Field(
        default="",
        description=(
            "Name for the imported experiment. "
            "Leave empty to derive from archive filename. Used by: import."
        ),
        examples=["", "MyImportedExperiment"],
    )
    new_name: str | None = Field(
        default=None,
        description="New experiment name. Required for: rename, save_as.",
        examples=["Experiment_Renamed", "Experiment1_Copy"],
    )


# ── Discover result models ────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the project domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class ProjectDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from project_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
