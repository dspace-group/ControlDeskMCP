"""Unit tests for controldesk_mcp.prompts.tool_window_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestManageToolWindows:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        result = manage_tool_windows()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_list_step(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        assert "tool_window_list" in _text(manage_tool_windows())

    def test_includes_check_exists_step(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        assert "tool_window_check_exists" in _text(manage_tool_windows())

    def test_includes_show_step(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        assert "tool_window_show" in _text(manage_tool_windows())

    def test_includes_get_state_step(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        assert "tool_window_get_state" in _text(manage_tool_windows())

    def test_includes_set_dock_state_step(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        assert "tool_window_set_dock_state" in _text(manage_tool_windows())

    def test_includes_close_step(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        assert "tool_window_close" in _text(manage_tool_windows())

    def test_window_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        assert "Instruments" in _text(manage_tool_windows(window_name="Instruments"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.tool_window_prompts import manage_tool_windows

        assert len(_text(manage_tool_windows())) > 50
