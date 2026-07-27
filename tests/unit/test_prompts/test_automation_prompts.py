"""Unit tests for session, measurement, and variable prompts (split from automation_prompts).

Prompts are pure Python functions — no COM, no service calls.
Tests call prompt functions directly and assert message structure and content.
"""

from __future__ import annotations

# ── Helpers ───────────────────────────────────────────────────────────────────


def _first_message_text(result: list[dict]) -> str:
    """Return the text content of the first message in a prompt result."""
    assert result, "Prompt must return at least one message"
    assert result[0]["role"] == "user"
    return result[0]["content"]


# ── start_automation_session ──────────────────────────────────────────────────


class TestStartAutomationSession:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        result = start_automation_session()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_always_includes_server_info_resource_and_app_start(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _first_message_text(start_automation_session())
        assert "controldesk://server/info" in text
        assert "start_controldesk" in text

    def test_project_path_included_when_provided(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _first_message_text(start_automation_session(project_path="C:/Projects/demo.cdprj"))
        assert "C:/Projects/demo.cdprj" in text
        assert "project_open" in text

    def test_platform_name_included_when_provided(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _first_message_text(start_automation_session(platform_name="DS1006"))
        assert "DS1006" in text
        assert "platform_connect" in text

    def test_version_included_when_provided(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _first_message_text(start_automation_session(controldesk_version="2026-A"))
        assert "2026-A" in text

    def test_all_defaults_still_produces_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        result = start_automation_session()
        text = _first_message_text(result)
        assert len(text) > 50  # non-trivial content


# ── diagnose_connection ───────────────────────────────────────────────────────


class TestDiagnoseConnection:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        result = diagnose_connection()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_always_includes_server_info_resource(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        text = _first_message_text(diagnose_connection())
        assert "controldesk://server/info" in text

    def test_always_reads_connection_status_resource(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        text = _first_message_text(diagnose_connection())
        assert "controldesk://server/connection-status" in text

    def test_error_message_inserted_in_prompt(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        text = _first_message_text(diagnose_connection(error_message="RPC_E_DISCONNECTED: 0x80010108"))
        assert "RPC_E_DISCONNECTED" in text

    def test_tool_name_inserted_in_prompt(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        text = _first_message_text(diagnose_connection(tool_name="variable_read_scalar"))
        assert "variable_read_scalar" in text

    def test_includes_platform_check_steps(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        text = _first_message_text(diagnose_connection())
        assert "platform_list" in text
        assert "platform_get_connection_state" in text


# ── run_measurement_workflow ──────────────────────────────────────────────────


class TestRunMeasurementWorkflow:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.measurement_prompts import run_measurement_workflow

        result = run_measurement_workflow()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_default_raster_name_in_prompt(self) -> None:
        from controldesk_mcp.prompts.measurement_prompts import run_measurement_workflow

        text = _first_message_text(run_measurement_workflow())
        assert "BaseSampleRaster" in text

    def test_custom_raster_replaces_default(self) -> None:
        from controldesk_mcp.prompts.measurement_prompts import run_measurement_workflow

        text = _first_message_text(run_measurement_workflow(raster_name="FastRaster"))
        assert "FastRaster" in text

    def test_sample_time_in_prompt(self) -> None:
        from controldesk_mcp.prompts.measurement_prompts import run_measurement_workflow

        text = _first_message_text(run_measurement_workflow(sample_time_ms=5.0))
        assert "5.0" in text

    def test_signals_included_when_provided(self) -> None:
        from controldesk_mcp.prompts.measurement_prompts import run_measurement_workflow

        text = _first_message_text(run_measurement_workflow(signals="Model/Speed, Model/Torque"))
        assert "Model/Speed" in text

    def test_includes_start_stop_and_list_recordings(self) -> None:
        from controldesk_mcp.prompts.measurement_prompts import run_measurement_workflow

        text = _first_message_text(run_measurement_workflow())
        assert "measurement_start" in text
        assert "measurement_stop" in text
        assert "measurement_list_recordings" in text


# ── read_write_variables ──────────────────────────────────────────────────────


class TestReadWriteVariables:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        result = read_write_variables()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_variable_path_included_when_provided(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _first_message_text(read_write_variables(variable_path="Model/Root/Speed"))
        assert "Model/Root/Speed" in text

    def test_write_value_included_when_provided(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _first_message_text(read_write_variables(variable_path="Model/Root/Speed", write_value="42.0"))
        assert "42.0" in text

    def test_read_only_mode_when_no_write_value(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _first_message_text(read_write_variables())
        assert "read-only" in text.lower()

    def test_includes_variable_get_info_step(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _first_message_text(read_write_variables())
        assert "variable_get_info" in text

    def test_includes_all_read_tool_variants(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _first_message_text(read_write_variables())
        assert "variable_read_scalar" in text
        assert "variable_read_curve" in text
        assert "variable_read_map" in text
        assert "variable_read_string" in text
