"""Unit tests for sources.prompts.recorder_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestRunRecorderMainWorkflow:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        result = run_recorder_main_workflow()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_get_state_step(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        assert "recorder_main_get_state" in _text(run_recorder_main_workflow())

    def test_includes_configure_step(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        assert "recorder_main_configure" in _text(run_recorder_main_workflow())

    def test_includes_add_signal_step(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        assert "recorder_main_add_signal" in _text(run_recorder_main_workflow())

    def test_includes_remove_signal_step(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        assert "recorder_main_remove_signal" in _text(run_recorder_main_workflow())

    def test_includes_list_signals_step(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        assert "recorder_main_list_signals" in _text(run_recorder_main_workflow())

    def test_includes_start_stop_steps(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        text = _text(run_recorder_main_workflow())
        assert "recorder_main_start" in text
        assert "recorder_main_stop" in text

    def test_includes_pause_and_resume_steps(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        text = _text(run_recorder_main_workflow())
        assert "recorder_main_pause" in text
        assert "recorder_main_resume" in text

    def test_signal_path_in_prompt_when_provided(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        assert "Model/Speed" in _text(run_recorder_main_workflow(signal_path="Model/Speed"))

    def test_output_file_in_prompt_when_provided(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        assert "C:/output.mf4" in _text(run_recorder_main_workflow(output_file="C:/output.mf4"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.recorder_prompts import run_recorder_main_workflow

        assert len(_text(run_recorder_main_workflow())) > 50
