"""Unit tests for controldesk_mcp.prompts.layout_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestManageLayoutWorkflow:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.layout_prompts import manage_layout_workflow

        result = manage_layout_workflow()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_layout_list_step(self) -> None:
        from controldesk_mcp.prompts.layout_prompts import manage_layout_workflow

        assert "layout_list" in _text(manage_layout_workflow())

    def test_includes_layout_manage_step(self) -> None:
        from controldesk_mcp.prompts.layout_prompts import manage_layout_workflow

        assert "layout_manage" in _text(manage_layout_workflow())

    def test_includes_layout_io_manage_step(self) -> None:
        from controldesk_mcp.prompts.layout_prompts import manage_layout_workflow

        assert "layout_io_manage" in _text(manage_layout_workflow())

    def test_includes_layout_discover_step(self) -> None:
        from controldesk_mcp.prompts.layout_prompts import manage_layout_workflow

        assert "layout_discover" in _text(manage_layout_workflow())

    def test_layout_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.layout_prompts import manage_layout_workflow

        assert "ControlLayout" in _text(manage_layout_workflow(layout_name="ControlLayout"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.layout_prompts import manage_layout_workflow

        assert len(_text(manage_layout_workflow())) > 50
