"""Unit tests for controldesk_mcp.prompts.session_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestStartAutomationSession:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        result = start_automation_session()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_server_info_resource_and_app_start(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _text(start_automation_session())
        assert "controldesk://server/info" in text
        assert "controldesk_app_start_or_attach" in text

    def test_project_path_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _text(start_automation_session(project_path="C:/demo.cdprj"))
        assert "C:/demo.cdprj" in text
        assert "controldesk_project_open" in text

    def test_platform_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _text(start_automation_session(platform_name="DS1006"))
        assert "DS1006" in text
        assert "controldesk_platform_connect" in text

    def test_version_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _text(start_automation_session(controldesk_version="2026-A"))
        assert "2026-A" in text

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.session_prompts import start_automation_session

        text = _text(start_automation_session())
        assert len(text) > 50


class TestDiagnoseConnection:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        result = diagnose_connection()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_server_info_resource(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        assert "controldesk://server/info" in _text(diagnose_connection())

    def test_reads_connection_status_resource(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        assert "controldesk://server/connection-status" in _text(diagnose_connection())

    def test_error_message_in_prompt(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        text = _text(diagnose_connection(error_message="RPC_E_DISCONNECTED"))
        assert "RPC_E_DISCONNECTED" in text

    def test_tool_name_in_prompt(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        text = _text(diagnose_connection(tool_name="variable_read_scalar"))
        assert "variable_read_scalar" in text

    def test_includes_platform_check_steps(self) -> None:
        from controldesk_mcp.prompts.session_prompts import diagnose_connection

        text = _text(diagnose_connection())
        assert "controldesk_platform_query" in text
        assert "get_connection_state" in text
