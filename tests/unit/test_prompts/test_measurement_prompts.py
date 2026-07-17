"""Unit tests for sources.prompts.measurement_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestRunMeasurementWorkflow:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.measurement_prompts import run_measurement_workflow

        result = run_measurement_workflow()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_default_raster_in_prompt(self) -> None:
        from sources.prompts.measurement_prompts import run_measurement_workflow

        assert "BaseSampleRaster" in _text(run_measurement_workflow())

    def test_custom_raster_replaces_default(self) -> None:
        from sources.prompts.measurement_prompts import run_measurement_workflow

        assert "FastRaster" in _text(run_measurement_workflow(raster_name="FastRaster"))

    def test_sample_time_in_prompt(self) -> None:
        from sources.prompts.measurement_prompts import run_measurement_workflow

        assert "5.0" in _text(run_measurement_workflow(sample_time_ms=5.0))

    def test_signals_included_when_provided(self) -> None:
        from sources.prompts.measurement_prompts import run_measurement_workflow

        text = _text(run_measurement_workflow(signals="Model/Speed, Model/Torque"))
        assert "Model/Speed" in text

    def test_includes_start_stop_and_list_recordings(self) -> None:
        from sources.prompts.measurement_prompts import run_measurement_workflow

        text = _text(run_measurement_workflow())
        assert "measurement_start" in text
        assert "measurement_stop" in text
        assert "measurement_list_recordings" in text

    def test_recording_name_in_prompt_when_provided(self) -> None:
        from sources.prompts.measurement_prompts import run_measurement_workflow

        text = _text(run_measurement_workflow(recording_name="test_run_01"))
        assert "test_run_01" in text


class TestAddMeasurementBookmark:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.measurement_prompts import add_measurement_bookmark

        result = add_measurement_bookmark()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_bookmark_add_step(self) -> None:
        from sources.prompts.measurement_prompts import add_measurement_bookmark

        assert "measurement_bookmark_add" in _text(add_measurement_bookmark())

    def test_label_in_prompt_when_provided(self) -> None:
        from sources.prompts.measurement_prompts import add_measurement_bookmark

        assert "FaultInjection" in _text(add_measurement_bookmark(label="FaultInjection"))

    def test_includes_bookmark_list_step(self) -> None:
        from sources.prompts.measurement_prompts import add_measurement_bookmark

        assert "measurement_bookmark_list" in _text(add_measurement_bookmark())

    def test_includes_bookmark_remove_step(self) -> None:
        from sources.prompts.measurement_prompts import add_measurement_bookmark

        assert "measurement_bookmark_remove" in _text(add_measurement_bookmark())

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.measurement_prompts import add_measurement_bookmark

        text = _text(add_measurement_bookmark())
        assert len(text) > 50


class TestManageDataLoggers:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.measurement_prompts import manage_data_loggers

        result = manage_data_loggers()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_create_configure_start_stop(self) -> None:
        from sources.prompts.measurement_prompts import manage_data_loggers

        text = _text(manage_data_loggers())
        for tool in (
            "data_logger_create",
            "data_logger_configure",
            "data_logger_start",
            "data_logger_stop",
        ):
            assert tool in text

    def test_includes_list_and_remove_steps(self) -> None:
        from sources.prompts.measurement_prompts import manage_data_loggers

        text = _text(manage_data_loggers())
        assert "data_logger_list" in text
        assert "data_logger_remove" in text

    def test_logger_name_in_prompt_when_provided(self) -> None:
        from sources.prompts.measurement_prompts import manage_data_loggers

        assert "MyLogger" in _text(manage_data_loggers(logger_name="MyLogger"))

    def test_output_file_in_prompt_when_provided(self) -> None:
        from sources.prompts.measurement_prompts import manage_data_loggers

        assert "C:/data.mf4" in _text(manage_data_loggers(output_file="C:/data.mf4"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.measurement_prompts import manage_data_loggers

        assert len(_text(manage_data_loggers())) > 50


class TestConfigureMeasurementTriggers:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.measurement_prompts import configure_measurement_triggers

        result = configure_measurement_triggers()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_trigger_rule_tools(self) -> None:
        from sources.prompts.measurement_prompts import configure_measurement_triggers

        text = _text(configure_measurement_triggers())
        assert "trigger_rule_create" in text
        assert "trigger_rule_remove" in text

    def test_includes_time_limit_condition(self) -> None:
        from sources.prompts.measurement_prompts import configure_measurement_triggers

        assert "trigger_condition_time_limit" in _text(configure_measurement_triggers())

    def test_includes_trigger_based_condition(self) -> None:
        from sources.prompts.measurement_prompts import configure_measurement_triggers

        assert "trigger_condition_trigger_based" in _text(configure_measurement_triggers())

    def test_signal_path_in_prompt_when_provided(self) -> None:
        from sources.prompts.measurement_prompts import configure_measurement_triggers

        assert "Model/Speed" in _text(configure_measurement_triggers(signal_path="Model/Speed"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.measurement_prompts import configure_measurement_triggers

        assert len(_text(configure_measurement_triggers())) > 50
