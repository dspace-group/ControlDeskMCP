"""Unit tests for sources.prompts.project_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestManageProjectWorkflow:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.project_prompts import manage_project_workflow

        result = manage_project_workflow()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_uses_project_open_when_path_provided(self) -> None:
        from sources.prompts.project_prompts import manage_project_workflow

        text = _text(manage_project_workflow(project_path="C:/proj.cdprj"))
        assert "project_open" in text
        assert "C:/proj.cdprj" in text

    def test_uses_project_create_when_no_path(self) -> None:
        from sources.prompts.project_prompts import manage_project_workflow

        assert "project_create" in _text(manage_project_workflow(project_name="NewProject"))

    def test_project_name_in_prompt_when_provided(self) -> None:
        from sources.prompts.project_prompts import manage_project_workflow

        assert "NewProject" in _text(manage_project_workflow(project_name="NewProject"))

    def test_platform_steps_included_when_provided(self) -> None:
        from sources.prompts.project_prompts import manage_project_workflow

        text = _text(manage_project_workflow(platform_name="DS1006"))
        assert "platform_add" in text
        assert "platform_connect" in text
        assert "DS1006" in text

    def test_includes_experiment_and_save_steps(self) -> None:
        from sources.prompts.project_prompts import manage_project_workflow

        text = _text(manage_project_workflow())
        assert "experiment_list" in text
        assert "experiment_activate" in text
        assert "project_save" in text

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.project_prompts import manage_project_workflow

        assert len(_text(manage_project_workflow())) > 50


class TestExportExperiment:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.project_prompts import export_experiment

        result = export_experiment()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_export_step(self) -> None:
        from sources.prompts.project_prompts import export_experiment

        assert "experiment_export" in _text(export_experiment())

    def test_experiment_name_in_prompt_when_provided(self) -> None:
        from sources.prompts.project_prompts import export_experiment

        assert "RunA" in _text(export_experiment(experiment_name="RunA"))

    def test_output_path_in_prompt_when_provided(self) -> None:
        from sources.prompts.project_prompts import export_experiment

        assert "C:/export.zip" in _text(export_experiment(output_path="C:/export.zip"))

    def test_includes_list_and_activate_steps(self) -> None:
        from sources.prompts.project_prompts import export_experiment

        text = _text(export_experiment())
        assert "experiment_list" in text
        assert "experiment_get_info" in text

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.project_prompts import export_experiment

        assert len(_text(export_experiment())) > 50


class TestManageProjectRoots:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.project_prompts import manage_project_roots

        result = manage_project_roots()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_list_step(self) -> None:
        from sources.prompts.project_prompts import manage_project_roots

        assert "project_root_list" in _text(manage_project_roots())

    def test_includes_add_step(self) -> None:
        from sources.prompts.project_prompts import manage_project_roots

        assert "project_root_add" in _text(manage_project_roots())

    def test_includes_activate_step(self) -> None:
        from sources.prompts.project_prompts import manage_project_roots

        assert "project_root_activate" in _text(manage_project_roots())

    def test_includes_remove_step(self) -> None:
        from sources.prompts.project_prompts import manage_project_roots

        assert "project_root_remove" in _text(manage_project_roots())

    def test_root_path_in_prompt_when_provided(self) -> None:
        from sources.prompts.project_prompts import manage_project_roots

        assert "C:/Projects" in _text(manage_project_roots(root_path="C:/Projects"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.project_prompts import manage_project_roots

        assert len(_text(manage_project_roots())) > 50


class TestManageExperiments:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.project_prompts import manage_experiments

        result = manage_experiments()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_create_activate_list(self) -> None:
        from sources.prompts.project_prompts import manage_experiments

        text = _text(manage_experiments())
        assert "experiment_create" in text
        assert "experiment_activate" in text
        assert "experiment_list" in text

    def test_includes_rename_and_save_as(self) -> None:
        from sources.prompts.project_prompts import manage_experiments

        text = _text(manage_experiments())
        assert "experiment_rename" in text
        assert "experiment_save_as" in text

    def test_includes_import_and_export(self) -> None:
        from sources.prompts.project_prompts import manage_experiments

        text = _text(manage_experiments())
        assert "experiment_import" in text
        assert "experiment_export" in text

    def test_includes_remove_step(self) -> None:
        from sources.prompts.project_prompts import manage_experiments

        assert "experiment_remove" in _text(manage_experiments())

    def test_experiment_name_in_prompt_when_provided(self) -> None:
        from sources.prompts.project_prompts import manage_experiments

        assert "TestRun" in _text(manage_experiments(experiment_name="TestRun"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.project_prompts import manage_experiments

        assert len(_text(manage_experiments())) > 50
