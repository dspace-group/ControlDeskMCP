"""Unit tests for controldesk_mcp.prompts.application_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestManageApplicationWindow:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        result = manage_application_window()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_get_visibility_step(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert "controldesk_app_window_manage" in _text(manage_application_window())
        assert "action='get_visibility'" in _text(manage_application_window())

    def test_includes_set_visible_step(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert "action='set_visible'" in _text(manage_application_window())

    def test_includes_get_state_step(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert "action='get_state'" in _text(manage_application_window())

    def test_includes_set_window_state_step(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert "action='set_state'" in _text(manage_application_window())

    def test_includes_set_window_position_step(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert "action='set_position'" in _text(manage_application_window())

    def test_fullscreen_uses_set_fullscreen_tool(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert "action='set_fullscreen'" in _text(manage_application_window(fullscreen=True))

    def test_includes_quit_step(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert "controldesk_app_stop" in _text(manage_application_window())

    def test_window_state_in_prompt(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert "maximized" in _text(manage_application_window(window_state="maximized"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.application_prompts import manage_application_window

        assert len(_text(manage_application_window())) > 50
