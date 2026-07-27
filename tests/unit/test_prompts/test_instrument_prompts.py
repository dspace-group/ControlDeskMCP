"""Unit tests for controldesk_mcp.prompts.instrument_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestManageInstrumentWorkflow:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.instrument_prompts import manage_instrument_workflow

        result = manage_instrument_workflow()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_instrument_list_step(self) -> None:
        from controldesk_mcp.prompts.instrument_prompts import manage_instrument_workflow

        assert "instrument_list" in _text(manage_instrument_workflow())

    def test_includes_instrument_manage_step(self) -> None:
        from controldesk_mcp.prompts.instrument_prompts import manage_instrument_workflow

        assert "instrument_manage" in _text(manage_instrument_workflow())

    def test_includes_instrument_signal_manage_step(self) -> None:
        from controldesk_mcp.prompts.instrument_prompts import manage_instrument_workflow

        assert "instrument_signal_manage" in _text(manage_instrument_workflow())

    def test_includes_instrument_discover_step(self) -> None:
        from controldesk_mcp.prompts.instrument_prompts import manage_instrument_workflow

        assert "instrument_discover" in _text(manage_instrument_workflow())

    def test_instrument_name_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.instrument_prompts import manage_instrument_workflow

        assert "SpeedKnob" in _text(manage_instrument_workflow(instrument_name="SpeedKnob"))

    def test_layout_name_hint_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.instrument_prompts import manage_instrument_workflow

        assert "ControlLayout" in _text(manage_instrument_workflow(layout_name="ControlLayout"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.instrument_prompts import manage_instrument_workflow

        assert len(_text(manage_instrument_workflow())) > 50
