"""Unit tests for controldesk_mcp.prompts.variable_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestReadWriteVariables:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        result = read_write_variables()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_variable_path_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        assert "Model/Root/Speed" in _text(read_write_variables(variable_path="Model/Root/Speed"))

    def test_write_value_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables(variable_path="Model/X", write_value="42.0"))
        assert "42.0" in text

    def test_read_only_mode_when_no_write_value(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        assert "read-only" in _text(read_write_variables()).lower()

    def test_includes_canonical_variable_read_step(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        assert "controldesk_variable_read" in _text(read_write_variables())

    def test_includes_canonical_variable_write_step(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        assert "controldesk_variable_write" in text

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        assert len(text) > 50

    def test_enforces_resolver_first_ordering(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        assert "instrument hint -> bounded `controldesk_variable_find` name attempts" in text
        assert "`controldesk_variable_list(action='list_all')` fallback" in text

    def test_includes_ambiguity_candidate_selection_guidance(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        assert "top 3-5 candidates" in text
        assert "ask the operator to pick one" in text

    def test_includes_no_early_full_path_request_guidance(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        assert "Do not ask the operator for a fully qualified path" in text

    def test_includes_ignore_unknown_com_object_guidance(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        assert "<COMObject <unknown>>" in text

    def test_includes_write_safety_guidance(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        assert "is_writable" in text
        assert "init-only lock state" in text


class TestDiscoverVariables:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import discover_variables

        result = discover_variables()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_list_all_step(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import discover_variables

        assert "controldesk_variable_list" in _text(discover_variables())

    def test_includes_find_step(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import discover_variables

        assert "controldesk_variable_find" in _text(discover_variables())

    def test_includes_list_group_variables(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import discover_variables

        assert "list_group_variables" in _text(discover_variables(group_path="Engine"))

    def test_includes_list_array_elements(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import discover_variables

        assert "list_array_elements" in _text(discover_variables())

    def test_search_pattern_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import discover_variables

        assert "Speed" in _text(discover_variables(search_pattern="Speed"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import discover_variables

        assert len(_text(discover_variables())) > 50

    def test_discover_includes_list_all_before_manual_path_guidance(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import discover_variables

        text = _text(discover_variables())
        assert "fallback before requesting manual full paths" in text


class TestManageVariableDescriptions:
    def test_returns_one_user_message(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import manage_variable_descriptions

        result = manage_variable_descriptions()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_list_step(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import manage_variable_descriptions

        assert "controldesk_variable_description_manage" in _text(manage_variable_descriptions())

    def test_includes_activate_step(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import manage_variable_descriptions

        assert "action='activate'" in _text(manage_variable_descriptions())

    def test_includes_remove_step(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import manage_variable_descriptions

        assert "action='remove'" in _text(manage_variable_descriptions())

    def test_file_path_in_prompt_when_provided(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import manage_variable_descriptions

        result = _text(manage_variable_descriptions(description_file="C:/model.a2l"))
        assert "C:/model.a2l" in result

    def test_defaults_produce_valid_prompt(self) -> None:
        from controldesk_mcp.prompts.variable_prompts import manage_variable_descriptions

        assert len(_text(manage_variable_descriptions())) > 50
