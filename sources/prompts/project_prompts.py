"""MCP prompts for ControlDesk project and experiment management workflows.

Prompts registered:
  manage_project_workflow — create or open a project, add platforms, create experiments
  export_experiment       — export an experiment to a zip archive for sharing or backup
  manage_project_roots    — register, activate, list, and remove project root folders
  manage_experiments      — full experiment lifecycle: create, rename, import, save-as, remove

All 25 project-domain tools are covered across these prompts:
  Project management: project_create, project_open, project_save, project_close,
                      project_remove, project_get_info, project_exists,
                      project_backup, project_open_from_backup, project_configure_settings,
                      project_list, project_list_recent
  Project roots:      project_root_add, project_root_activate, project_root_list,
                      project_root_remove
  Experiments:        experiment_create, experiment_activate, experiment_list,
                      experiment_get_info, experiment_export, experiment_import,
                      experiment_rename, experiment_save_as, experiment_remove

Layer: MCP Prompt adapter — pure Python; no COM or service calls.
"""

from __future__ import annotations

from sources.server.app import mcp

# ── Prompt — Manage Project Workflow ──────────────────────────────────────────


@mcp.prompt(
    name="manage_project_workflow",
    description=(
        "Step-by-step guide for creating or opening a ControlDesk project, "
        "adding a platform, and setting up an experiment. "
        "Accepts optional project path to distinguish new vs. existing projects."
    ),
)
def manage_project_workflow(
    project_path: str = "",
    project_name: str = "",
    platform_name: str = "",
) -> list[dict]:
    """Generate a project management workflow prompt."""
    path_arg = f", project_path='{project_path}'" if project_path else ""
    name_arg = f", name='{project_name}'" if project_name else ""
    platform_arg = f", platform_name='{platform_name}'" if platform_name else ""

    open_or_create = (
        f"Call `project_open`{path_arg} to open the existing project."
        if project_path
        else f"Call `project_create`{name_arg} to create a new project."
    )

    return [
        {
            "role": "user",
            "content": (
                f"Set up a ControlDesk project and experiment.\n\n"
                f"**Parameters:**\n"
                f"- Project path: {project_path or '(create new)'}\n"
                f"- Project name: {project_name or '(required if creating new)'}\n"
                f"- Platform: {platform_name or '(add manually if needed)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `project_list_recent` to see the most recently used projects "
                f"   (sorted by last-modified timestamp, mirrors ControlDesk's Recent "
                f"   section). Each entry includes root_path, name, full_path, "
                f"   last_modified_utc, and experiments (experiment names on disk).\n"
                f"   - If the recent list is empty, call `project_list` for a full "
                f"   enumeration across all roots.\n"
                f"   - If both lists are empty, call `project_root_list` to check "
                f"   registered roots. If no roots exist, call `project_root_add` first.\n"
                f"2. Call `project_exists`{name_arg} to check if the target project exists.\n"
                f"3. If opening an existing project from a non-active root: call "
                f"   `project_root_activate` with the root_path from step 1 first.\n"
                f"4. {open_or_create}\n"
                f"5. Call `project_get_info` to confirm the project is loaded and report "
                f"   its name, path, and active experiment.\n"
                f"6. Optionally call `project_configure_settings` to set project-level "
                f"   options (save path, backup settings, etc.).\n"
                f"7. If a platform name was provided: call `platform_add`{platform_arg} "
                f"   to register the platform, then call `platform_connect`{platform_arg}.\n"
                f"8. Call `experiment_list` to see existing experiments.\n"
                f"9. If no suitable experiment exists: call `experiment_create` with an "
                f"   appropriate name.\n"
                f"10. Call `experiment_activate` to make the experiment active.\n"
                f"11. Call `project_save` to persist the project configuration.\n"
                f"12. To back up the project: call `project_backup` to create an archive.\n"
                f"13. Report: project name, active experiment, registered platforms, "
                f"    and save status."
            ),
        }
    ]


# ── Prompt — Export Experiment ────────────────────────────────────────────────


@mcp.prompt(
    name="export_experiment",
    description=(
        "Guided workflow for exporting a ControlDesk experiment to a zip archive: "
        "select the experiment, export it, and verify the output file. "
        "Accepts optional experiment name and output path."
    ),
)
def export_experiment(
    experiment_name: str = "",
    output_path: str = "",
) -> list[dict]:
    """Generate an experiment export workflow prompt."""
    exp_arg = f", name='{experiment_name}'" if experiment_name else ""
    path_arg = f", export_path='{output_path}'" if output_path else ""

    return [
        {
            "role": "user",
            "content": (
                f"Export a ControlDesk experiment to a file.\n\n"
                f"**Parameters:**\n"
                f"- Experiment name: {experiment_name or '(use active experiment)'}\n"
                f"- Output path: {output_path or '(auto-generated)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `experiment_list` to see available experiments.\n"
                f"2. If a specific experiment was named: call `experiment_activate`"
                f"{exp_arg} to make it active.\n"
                f"3. Call `experiment_get_info` to confirm the correct experiment is active "
                f"   and note its name and path.\n"
                f"4. Call `experiment_export`{path_arg} to export the experiment archive.\n"
                f"5. Confirm the output file exists and report: experiment name, "
                f"   archive path, and file size."
            ),
        }
    ]


# ── Prompt — Manage Project Roots ─────────────────────────────────────────────


@mcp.prompt(
    name="manage_project_roots",
    description=(
        "Guided workflow for managing ControlDesk project root folders: "
        "register new root folders, set the active root, list all roots, "
        "and remove roots that are no longer needed. "
        "Project roots are file-system folders that ControlDesk searches for projects."
    ),
)
def manage_project_roots(
    root_path: str = "",
) -> list[dict]:
    """Generate a project root management workflow prompt."""
    path_arg = f", path='{root_path}'" if root_path else ""

    return [
        {
            "role": "user",
            "content": (
                f"Manage ControlDesk project root folders.\n\n"
                f"**Parameters:**\n"
                f"- Root path: {root_path or '(not specified)'}\n\n"
                f"**Steps — execute in order:**\n\n"
                f"1. Call `project_root_list` to see all currently registered root folders "
                f"   and which one is active.\n"
                f"2. To add a new root: call `project_root_add`{path_arg} with the "
                f"   folder path. The folder will become visible in the ControlDesk project "
                f"   tree.\n"
                f"3. To set a root as active: call `project_root_activate`{path_arg}. "
                f"   The active root is where `project_create` will create new projects.\n"
                f"4. After activating a root, call `project_root_list` again to confirm the "
                f"   active root changed correctly.\n"
                f"5. To remove a root that is no longer needed: call "
                f"   `project_root_remove`{path_arg}. This does not delete the folder or "
                f"   its projects — only the registration is removed.\n"
                f"6. Report: registered roots, active root, and projects visible in each."
            ),
        }
    ]


# ── Prompt — Manage Experiments ───────────────────────────────────────────────


@mcp.prompt(
    name="manage_experiments",
    description=(
        "Guided workflow for the full experiment lifecycle in a ControlDesk project: "
        "create, rename, clone (save-as), import, and remove experiments. "
        "Use this when the project is already open and you need to manage its experiments."
    ),
)
def manage_experiments(
    experiment_name: str = "",
) -> list[dict]:
    """Generate an experiment lifecycle management workflow prompt."""
    exp_arg = f", name='{experiment_name}'" if experiment_name else ""

    return [
        {
            "role": "user",
            "content": (
                f"Manage experiments in the active ControlDesk project.\n\n"
                f"**Parameters:**\n"
                f"- Experiment name: {experiment_name or '(not specified)'}\n\n"
                f"**Available experiment operations:**\n\n"
                f"**Create / activate:**\n"
                f"1. Call `experiment_list` to see existing experiments.\n"
                f"2. Call `experiment_create`{exp_arg} to create a new experiment.\n"
                f"3. Call `experiment_activate`{exp_arg} to make an experiment active.\n"
                f"4. Call `experiment_get_info` to inspect the active experiment.\n\n"
                f"**Rename / clone:**\n"
                f"5. Call `experiment_rename` to rename the active experiment.\n"
                f"6. Call `experiment_save_as` to create a named copy of the current "
                f"   experiment (useful for branching configurations).\n\n"
                f"**Import / export:**\n"
                f"7. Call `experiment_export` to export the active experiment to a .DSA "
                f"   archive for sharing or backup.\n"
                f"8. Call `experiment_import` to restore an experiment from a .DSA archive "
                f"   into the current project.\n\n"
                f"**Remove:**\n"
                f"9. Call `experiment_remove`{exp_arg} to permanently delete an experiment "
                f"   from the project.\n\n"
                f"10. Call `project_save` after any structural changes to persist them.\n"
                f"11. Report: experiments affected and current experiment list."
            ),
        }
    ]
