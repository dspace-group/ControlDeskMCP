"""Unit tests for controldesk_mcp.prompts.bus_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestConfigureBusLogging:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import configure_bus_logging

        result = configure_bus_logging()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_create_start_stop_steps(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import configure_bus_logging

        text = _text(configure_bus_logging())
        assert "bus_logger_create" in text
        assert "bus_logger_start" in text
        assert "bus_logger_stop" in text

    def test_includes_list_step(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import configure_bus_logging

        assert "bus_logger_list" in _text(configure_bus_logging())

    def test_logger_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import configure_bus_logging

        assert "MyLogger" in _text(configure_bus_logging(logger_name="MyLogger"))

    def test_database_path_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import configure_bus_logging

        assert "C:/bus.blf" in _text(configure_bus_logging(database_path="C:/bus.blf"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import configure_bus_logging

        assert len(_text(configure_bus_logging())) > 50


class TestRunBusMonitor:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import run_bus_monitor

        result = run_bus_monitor()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_create_start_stop_save_steps(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import run_bus_monitor

        text = _text(run_bus_monitor())
        assert "bus_monitor_create" in text
        assert "bus_monitor_start" in text
        assert "bus_monitor_stop" in text
        assert "bus_monitor_save_data" in text

    def test_monitor_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import run_bus_monitor

        assert "CanMonitor1" in _text(run_bus_monitor(monitor_name="CanMonitor1"))

    def test_output_path_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import run_bus_monitor

        assert "C:/capture.mf4" in _text(run_bus_monitor(output_path="C:/capture.mf4"))


class TestReplayBusData:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import replay_bus_data

        result = replay_bus_data()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_create_configure_start_stop_steps(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import replay_bus_data

        text = _text(replay_bus_data())
        assert "bus_replay_create" in text
        assert "bus_replay_configure" in text
        assert "bus_replay_start" in text
        assert "bus_replay_stop" in text

    def test_replay_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import replay_bus_data

        assert "Replay1" in _text(replay_bus_data(replay_name="Replay1"))

    def test_source_path_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import replay_bus_data

        assert "C:/recording.blf" in _text(replay_bus_data(source_path="C:/recording.blf"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import replay_bus_data

        assert len(_text(replay_bus_data())) > 50


class TestManageBusFilters:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import manage_bus_filters

        result = manage_bus_filters()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_create_configure_start_stop(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import manage_bus_filters

        text = _text(manage_bus_filters())
        for tool in (
            "bus_filter_create",
            "bus_filter_configure",
            "bus_filter_start",
            "bus_filter_stop",
        ):
            assert tool in text

    def test_includes_list_and_remove_steps(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import manage_bus_filters

        text = _text(manage_bus_filters())
        assert "bus_filter_list" in text
        assert "bus_filter_remove" in text

    def test_filter_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import manage_bus_filters

        assert "CanFilter1" in _text(manage_bus_filters(filter_name="CanFilter1"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.bus_prompts import manage_bus_filters

        assert len(_text(manage_bus_filters())) > 50
