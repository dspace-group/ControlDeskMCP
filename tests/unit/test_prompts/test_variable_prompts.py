"""Unit tests for sources.prompts.variable_prompts."""

from __future__ import annotations


def _text(result: list[dict]) -> str:
    assert result and result[0]["role"] == "user"
    return result[0]["content"]


class TestReadWriteVariables:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.variable_prompts import read_write_variables

        result = read_write_variables()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_variable_path_in_prompt_when_provided(self) -> None:
        from sources.prompts.variable_prompts import read_write_variables

        assert "Model/Root/Speed" in _text(read_write_variables(variable_path="Model/Root/Speed"))

    def test_write_value_in_prompt_when_provided(self) -> None:
        from sources.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables(variable_path="Model/X", write_value="42.0"))
        assert "42.0" in text

    def test_read_only_mode_when_no_write_value(self) -> None:
        from sources.prompts.variable_prompts import read_write_variables

        assert "read-only" in _text(read_write_variables()).lower()

    def test_includes_variable_get_info_step(self) -> None:
        from sources.prompts.variable_prompts import read_write_variables

        assert "variable_get_info" in _text(read_write_variables())

    def test_includes_all_read_tool_variants(self) -> None:
        from sources.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        for tool in (
            "variable_read_scalar",
            "variable_read_curve",
            "variable_read_map",
            "variable_read_string",
        ):
            assert tool in text

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.variable_prompts import read_write_variables

        text = _text(read_write_variables())
        assert len(text) > 50


class TestDiscoverVariables:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.variable_prompts import discover_variables

        result = discover_variables()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_list_all_step(self) -> None:
        from sources.prompts.variable_prompts import discover_variables

        assert "variable_list_all" in _text(discover_variables())

    def test_includes_find_step(self) -> None:
        from sources.prompts.variable_prompts import discover_variables

        assert "variable_find" in _text(discover_variables())

    def test_includes_list_group_variables(self) -> None:
        from sources.prompts.variable_prompts import discover_variables

        assert "variable_list_group_variables" in _text(discover_variables())

    def test_includes_list_array_elements(self) -> None:
        from sources.prompts.variable_prompts import discover_variables

        assert "variable_list_array_elements" in _text(discover_variables())

    def test_search_pattern_in_prompt_when_provided(self) -> None:
        from sources.prompts.variable_prompts import discover_variables

        assert "Speed" in _text(discover_variables(search_pattern="Speed"))

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.variable_prompts import discover_variables

        assert len(_text(discover_variables())) > 50


class TestManageVariableDescriptions:
    def test_returns_one_user_message(self) -> None:
        from sources.prompts.variable_prompts import manage_variable_descriptions

        result = manage_variable_descriptions()
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_includes_list_step(self) -> None:
        from sources.prompts.variable_prompts import manage_variable_descriptions

        assert "variable_description_list" in _text(manage_variable_descriptions())

    def test_includes_activate_step(self) -> None:
        from sources.prompts.variable_prompts import manage_variable_descriptions

        assert "variable_description_activate" in _text(manage_variable_descriptions())

    def test_includes_remove_step(self) -> None:
        from sources.prompts.variable_prompts import manage_variable_descriptions

        assert "variable_description_remove" in _text(manage_variable_descriptions())

    def test_file_path_in_prompt_when_provided(self) -> None:
        from sources.prompts.variable_prompts import manage_variable_descriptions

        result = _text(manage_variable_descriptions(description_file="C:/model.a2l"))
        assert "C:/model.a2l" in result

    def test_defaults_produce_valid_prompt(self) -> None:
        from sources.prompts.variable_prompts import manage_variable_descriptions

        assert len(_text(manage_variable_descriptions())) > 50
