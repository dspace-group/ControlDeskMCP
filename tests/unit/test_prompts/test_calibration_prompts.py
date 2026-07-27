"""Unit tests for controldesk_mcp.prompts.calibration_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestRunCalibrationWorkflow:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import run_calibration_workflow

        result = run_calibration_workflow()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_calibration_start_and_stop(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import run_calibration_workflow

        text = _text(run_calibration_workflow())
        assert "calibration_start" in text
        assert "calibration_stop" in text

    def test_includes_page_switch_steps(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import run_calibration_workflow

        text = _text(run_calibration_workflow())
        assert "calibration_activate_working_page" in text
        assert "calibration_activate_reference_page" in text

    def test_includes_refresh_step(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import run_calibration_workflow

        assert "calibration_refresh_parameters" in _text(run_calibration_workflow())

    def test_platform_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import run_calibration_workflow

        assert "DS1006" in _text(run_calibration_workflow(platform_name="DS1006"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import run_calibration_workflow

        text = _text(run_calibration_workflow())
        assert len(text) > 50


class TestProposedCalibrationFlow:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import proposed_calibration_flow

        result = proposed_calibration_flow()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_proposed_start_and_stop(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import proposed_calibration_flow

        text = _text(proposed_calibration_flow())
        assert "proposed_calibration_start" in text
        assert "proposed_calibration_stop" in text

    def test_includes_apply_and_cancel_paths(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import proposed_calibration_flow

        text = _text(proposed_calibration_flow())
        assert "proposed_calibration_apply" in text
        assert "proposed_calibration_cancel" in text

    def test_platform_arg_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import proposed_calibration_flow

        assert "MicroAutoBox" in _text(proposed_calibration_flow(platform_name="MicroAutoBox"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import proposed_calibration_flow

        text = _text(proposed_calibration_flow())
        assert len(text) > 50


class TestManageCalibrationDataSets:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import manage_calibration_data_sets

        result = manage_calibration_data_sets()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_data_set_working_page(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import manage_calibration_data_sets

        assert "data_set_activate_working_page" in _text(manage_calibration_data_sets())

    def test_includes_data_set_reference_page(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import manage_calibration_data_sets

        assert "data_set_activate_reference_page" in _text(manage_calibration_data_sets())

    def test_includes_calibration_working_page(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import manage_calibration_data_sets

        assert "calibration_activate_working_page" in _text(manage_calibration_data_sets())

    def test_includes_calibration_reference_page(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import manage_calibration_data_sets

        assert "calibration_activate_reference_page" in _text(manage_calibration_data_sets())

    def test_platform_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import manage_calibration_data_sets

        assert "DS1202" in _text(manage_calibration_data_sets(platform_name="DS1202"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.calibration_prompts import manage_calibration_data_sets

        assert len(_text(manage_calibration_data_sets())) > 50
