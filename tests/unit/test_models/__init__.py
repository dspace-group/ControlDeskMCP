"""Unit tests for controldesk_mcp.com_bridge.domains.variable_com."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock

import pytest

from controldesk_mcp.com_bridge.domains.variable_com import (
    activate_reference_page,
    activate_variable_description,
    activate_working_page,
    find_variable,
    get_variable_info,
    list_all_variables,
    list_array_elements,
    list_group_variables,
    list_variable_descriptions,
    read_array_element,
    read_curve_variable,
    read_map_variable,
    read_scalar_variable,
    read_string_variable,
    remove_variable_description,
    write_array_element,
    write_curve_variable,
    write_map_variable,
    write_scalar_variable,
    write_string_variable,
)
from controldesk_mcp.com_bridge.errors import BridgePreconditionError

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_identifier(
    unique_name: str = "f_Kp_1",
    connection_path: str = "XCP()://f_Kp_1",
    path: str = "Model Root/f_Kp_1",
) -> MagicMock:
    ident = MagicMock()
    type(ident).UniqueName = PropertyMock(return_value=unique_name)
    type(ident).ConnectionPath = PropertyMock(return_value=connection_path)
    type(ident).Path = PropertyMock(return_value=path)
    type(ident).URI = PropertyMock(return_value=f"dspace://XCP/{path}")
    type(ident).RasterName = PropertyMock(return_value="")
    plat = MagicMock()
    type(plat).Name = PropertyMock(return_value="XCP")
    type(ident).Platform = PropertyMock(return_value=plat)
    return ident


def _make_variable(
    name: str = "f_Kp_1",
    var_type: str = "Parameter",
    is_readable: bool = True,
    is_writable: bool = True,
    unit: str = "deg",
    value_converted: float = 0.5,
) -> MagicMock:
    var = MagicMock()
    ident = _make_identifier(unique_name=name)
    type(var).Identifier = PropertyMock(return_value=ident)
    type(var).Type = PropertyMock(return_value=var_type)
    type(var).IsReadable = PropertyMock(return_value=is_readable)
    type(var).IsWritable = PropertyMock(return_value=is_writable)
    type(var).IsChangeableOnlyDuringInitialization = PropertyMock(return_value=False)
    type(var).Unit = PropertyMock(return_value=unit)
    type(var).Description = PropertyMock(return_value="")
    type(var).ValueConverted = PropertyMock(return_value=value_converted)
    type(var).ValueSource = PropertyMock(return_value=int(value_converted))

    hard = MagicMock()
    type(hard).Minimum = PropertyMock(return_value=-100.0)
    type(hard).Maximum = PropertyMock(return_value=100.0)
    type(var).HardLimits = PropertyMock(return_value=hard)

    weak = MagicMock()
    type(weak).Minimum = PropertyMock(return_value=-50.0)
    type(weak).Maximum = PropertyMock(return_value=50.0)
    type(var).WeakLimits = PropertyMock(return_value=weak)
    return var


def _make_variables_collection(var_list: list[MagicMock]) -> MagicMock:
    col = MagicMock()
    type(col).Count = PropertyMock(return_value=len(var_list))

    def _item(key):
        if isinstance(key, int):
            return var_list[key - 1]
        for v in var_list:
            try:
                if str(v.Identifier.UniqueName) == str(key):
                    return v
            except Exception:
                pass
        raise Exception(f"Variable '{key}' not found")

    def _item_by_path(key):
        for v in var_list:
            try:
                if str(v.Identifier.ConnectionPath) == str(key):
                    return v
            except Exception:
                pass
        raise Exception(f"Variable path '{key}' not found")

    col.Item.side_effect = _item
    col.ItemByPath.side_effect = _item_by_path

    root_group = MagicMock()
    sg_col = MagicMock()
    type(sg_col).Count = PropertyMock(return_value=0)
    root_group.Groups = sg_col
    var_group_col = MagicMock()
    type(var_group_col).Count = PropertyMock(return_value=0)
    root_group.Variables = var_group_col
    col.RootGroup = root_group
    return col


def _make_app_with_variables(var_list: list[MagicMock]) -> MagicMock:
    """Return a mock IXaApplication with one platform and given variables."""
    app = MagicMock()
    exp = MagicMock()
    plats = MagicMock()
    type(plats).Count = PropertyMock(return_value=1)

    plat = MagicMock()
    type(plat).Name = PropertyMock(return_value="XCP")
    var_desc = MagicMock()
    variables = _make_variables_collection(var_list)
    var_desc.Variables = variables

    # DataSets for working/reference page tests
    working_ds = MagicMock()
    reference_ds = MagicMock()
    datasets = MagicMock()
    datasets.WorkingDataSet = working_ds
    datasets.ReferenceDataSet = reference_ds
    var_desc.DataSets = datasets

    plat.ActiveVariableDescription = var_desc

    # RootGroup on the active variable description (for list_group_variables)
    root_group = MagicMock()
    root_grp_groups = MagicMock()
    type(root_grp_groups).Count = PropertyMock(return_value=0)
    root_group.Groups = root_grp_groups
    root_grp_vars = MagicMock()
    type(root_grp_vars).Count = PropertyMock(return_value=0)
    root_group.Variables = root_grp_vars
    var_desc.RootGroup = root_group

    # VariableDescriptions collection on platform
    vd_col = MagicMock()
    type(vd_col).Count = PropertyMock(return_value=1)
    vd_item = MagicMock()
    type(vd_item).Name = PropertyMock(return_value="myecu")
    type(vd_item).Active = PropertyMock(return_value=True)
    type(vd_item).FullName = PropertyMock(return_value="C:\\ECU\\myecu.a2l")
    vd_col.Contains.return_value = True
    vd_col.Item.return_value = vd_item
    plat.VariableDescriptions = vd_col

    def _plat_item(key):
        return plat

    plats.Item.side_effect = _plat_item

    exp.Platforms = plats
    app.ActiveExperiment = exp
    return app


def _make_no_experiment_app() -> MagicMock:
    app = MagicMock()
    app.ActiveExperiment = None
    return app


def _make_app_no_var_desc() -> MagicMock:
    """App with one platform but no active variable description."""
    app = MagicMock()
    exp = MagicMock()
    plats = MagicMock()
    type(plats).Count = PropertyMock(return_value=1)
    plat = MagicMock()
    plat.ActiveVariableDescription = None
    plats.Item.return_value = plat
    exp.Platforms = plats
    app.ActiveExperiment = exp
    return app


# ── find_variable ─────────────────────────────────────────────────────────────


class TestFindVariable:
    def test_found_by_name_returns_metadata(self) -> None:
        var = _make_variable(name="f_Kp_1")
        app = _make_app_with_variables([var])
        result = find_variable(app, "f_Kp_1")
        assert result["found"] is True
        assert result["name"] == "f_Kp_1"
        assert result["variable_type"] == "Parameter"
        assert result["is_readable"] is True
        assert result["is_writable"] is True

    def test_not_found_returns_found_false(self) -> None:
        app = _make_app_with_variables([])
        result = find_variable(app, "missing_var")
        assert result["found"] is False

    def test_raises_precondition_when_no_experiment(self) -> None:
        app = _make_no_experiment_app()
        with pytest.raises(BridgePreconditionError):
            find_variable(app, "f_Kp_1")

    def test_raises_precondition_when_no_var_desc(self) -> None:
        app = _make_app_no_var_desc()
        with pytest.raises(BridgePreconditionError):
            find_variable(app, "f_Kp_1")

    def test_found_by_path_search_mode(self) -> None:
        var = _make_variable(name="f_Kp_1")
        app = _make_app_with_variables([var])
        result = find_variable(app, "XCP()://f_Kp_1", search_mode="path")
        assert result["found"] is True

    def test_has_hard_limits(self) -> None:
        var = _make_variable(name="f_Kp_1")
        app = _make_app_with_variables([var])
        result = find_variable(app, "f_Kp_1")
        assert "hard_limits" in result
        assert result["hard_limits"]["min"] == -100.0
        assert result["hard_limits"]["max"] == 100.0

    def test_has_unit(self) -> None:
        var = _make_variable(name="f_Kp_1", unit="deg")
        app = _make_app_with_variables([var])
        result = find_variable(app, "f_Kp_1")
        assert result["unit"] == "deg"


# ── get_variable_info ─────────────────────────────────────────────────────────


class TestGetVariableInfo:
    def test_returns_same_as_find_variable(self) -> None:
        var = _make_variable(name="f_Kp_1")
        app = _make_app_with_variables([var])
        result = get_variable_info(app, "f_Kp_1")
        assert result["found"] is True
        assert result["name"] == "f_Kp_1"


# ── list_all_variables ────────────────────────────────────────────────────────


class TestListAllVariables:
    def test_returns_total_count(self) -> None:
        vars_ = [
            _make_variable(name="f_Kp_1", var_type="Parameter"),
            _make_variable(name="control_out", var_type="Measurement"),
        ]
        app = _make_app_with_variables(vars_)
        result = list_all_variables(app)
        assert result["total_count"] == 2

    def test_groups_by_type(self) -> None:
        vars_ = [
            _make_variable(name="f_Kp_1", var_type="Parameter"),
            _make_variable(name="control_out", var_type="Measurement"),
        ]
        app = _make_app_with_variables(vars_)
        result = list_all_variables(app)
        assert "Parameter" in result["by_type"]
        assert "Measurement" in result["by_type"]
        assert len(result["by_type"]["Parameter"]) == 1
        assert len(result["by_type"]["Measurement"]) == 1

    def test_empty_when_no_variables(self) -> None:
        app = _make_app_with_variables([])
        result = list_all_variables(app)
        assert result["total_count"] == 0
        assert result["by_type"] == {}

    def test_raises_precondition_when_no_var_desc(self) -> None:
        app = _make_app_no_var_desc()
        with pytest.raises(BridgePreconditionError):
            list_all_variables(app)


# ── read_scalar_variable ──────────────────────────────────────────────────────


class TestReadScalarVariable:
    def test_reads_converted_value(self) -> None:
        var = _make_variable(name="f_Kp_1", value_converted=0.5)
        app = _make_app_with_variables([var])
        result = read_scalar_variable(app, "f_Kp_1")
        assert result["variable_name"] == "f_Kp_1"
        assert result["value_format"] == "Converted"
        assert "value" in result
        assert "timestamp_utc" in result

    def test_reads_source_value(self) -> None:
        var = _make_variable(name="f_Kp_1", value_converted=1.0)
        app = _make_app_with_variables([var])
        result = read_scalar_variable(app, "f_Kp_1", value_format="Source")
        assert result["value_format"] == "Source"
        assert result["unit"] == "raw"

    def test_raises_precondition_for_missing_variable(self) -> None:
        app = _make_app_with_variables([])
        with pytest.raises(BridgePreconditionError):
            read_scalar_variable(app, "nonexistent")

    def test_includes_timestamp(self) -> None:
        var = _make_variable(name="f_Kp_1")
        app = _make_app_with_variables([var])
        result = read_scalar_variable(app, "f_Kp_1")
        assert result["timestamp_utc"].endswith("Z")


# ── write_scalar_variable ─────────────────────────────────────────────────────


class TestWriteScalarVariable:
    def test_writes_converted_value(self) -> None:
        var = _make_variable(name="f_Kp_1")
        app = _make_app_with_variables([var])
        result = write_scalar_variable(app, "f_Kp_1", 0.12)
        assert result["written"] is True
        assert result["variable_name"] == "f_Kp_1"
        assert result["value_written"] == 0.12
        assert result["value_format"] == "Converted"

    def test_writes_source_value(self) -> None:
        var = _make_variable(name="f_Kp_1")
        app = _make_app_with_variables([var])
        result = write_scalar_variable(app, "f_Kp_1", 2048, value_format="Source")
        assert result["written"] is True
        assert result["unit"] == "raw"

    def test_raises_precondition_for_missing_variable(self) -> None:
        app = _make_app_with_variables([])
        with pytest.raises(BridgePreconditionError):
            write_scalar_variable(app, "nonexistent", 1.0)

    def test_includes_timestamp(self) -> None:
        var = _make_variable(name="f_Kp_1")
        app = _make_app_with_variables([var])
        result = write_scalar_variable(app, "f_Kp_1", 0.5)
        assert result["timestamp_utc"].endswith("Z")


# ── read_curve_variable ───────────────────────────────────────────────────────


def _make_curve_variable(name: str = "FuelCurve") -> MagicMock:
    var = MagicMock()
    ident = _make_identifier(unique_name=name)
    type(var).Identifier = PropertyMock(return_value=ident)
    type(var).Type = PropertyMock(return_value="Curve")

    axis = MagicMock()
    type(axis).ValueConverted = PropertyMock(return_value=(0.0, 1.0, 2.0))
    type(axis).ValueSource = PropertyMock(return_value=(0, 1, 2))
    type(axis).Unit = PropertyMock(return_value="rpm")
    var.Axis = axis

    func = MagicMock()
    type(func).ValueConverted = PropertyMock(return_value=(1.5, 1.6, 1.7))
    type(func).ValueSource = PropertyMock(return_value=(100, 110, 120))
    type(func).Unit = PropertyMock(return_value="V")
    var.FunctionValues = func
    return var


class TestReadCurveVariable:
    def test_reads_axis_and_function_values(self) -> None:
        var = _make_curve_variable("FuelCurve")
        app = _make_app_with_variables([var])
        result = read_curve_variable(app, "FuelCurve")
        assert result["variable_type"] == "Curve"
        assert result["axis"]["size"] == 3
        assert len(result["axis"]["values"]) == 3
        assert result["function_values"]["size"] == 3
        assert result["axis"]["unit"] == "rpm"
        assert result["function_values"]["unit"] == "V"

    def test_reads_source_format(self) -> None:
        var = _make_curve_variable("FuelCurve")
        app = _make_app_with_variables([var])
        result = read_curve_variable(app, "FuelCurve", value_format="Source")
        assert result["value_format"] == "Source"

    def test_includes_timestamp(self) -> None:
        var = _make_curve_variable("FuelCurve")
        app = _make_app_with_variables([var])
        result = read_curve_variable(app, "FuelCurve")
        assert result["timestamp_utc"].endswith("Z")


# ── write_curve_variable ──────────────────────────────────────────────────────


class TestWriteCurveVariable:
    def test_writes_function_values(self) -> None:
        var = _make_curve_variable("FuelCurve")
        app = _make_app_with_variables([var])
        result = write_curve_variable(app, "FuelCurve", [1.4, 1.5, 1.6])
        assert result["written"] is True
        assert result["function_values_written"] == 3
        assert result["axis_values_written"] == 0

    def test_writes_function_and_axis_values(self) -> None:
        var = _make_curve_variable("FuelCurve")
        app = _make_app_with_variables([var])
        result = write_curve_variable(
            app, "FuelCurve", [1.4, 1.5, 1.6], axis_values=[0.0, 1.5, 3.0]
        )
        assert result["written"] is True
        assert result["axis_values_written"] == 3

    def test_includes_timestamp(self) -> None:
        var = _make_curve_variable("FuelCurve")
        app = _make_app_with_variables([var])
        result = write_curve_variable(app, "FuelCurve", [1.4, 1.5, 1.6])
        assert result["timestamp_utc"].endswith("Z")


# ── read_map_variable ─────────────────────────────────────────────────────────


def _make_map_variable(name: str = "FuelMap") -> MagicMock:
    var = MagicMock()
    ident = _make_identifier(unique_name=name)
    type(var).Identifier = PropertyMock(return_value=ident)
    type(var).Type = PropertyMock(return_value="Map")

    x_axis = MagicMock()
    type(x_axis).ValueConverted = PropertyMock(return_value=(0.0, 50.0, 100.0))
    type(x_axis).ValueSource = PropertyMock(return_value=(0, 50, 100))
    type(x_axis).Unit = PropertyMock(return_value="percent")
    var.XAxis = x_axis

    y_axis = MagicMock()
    type(y_axis).ValueConverted = PropertyMock(return_value=(0, 3000))
    type(y_axis).ValueSource = PropertyMock(return_value=(0, 3000))
    type(y_axis).Unit = PropertyMock(return_value="rpm")
    var.YAxis = y_axis

    func = MagicMock()
    # COM format: [x_count][y_count] = 3 outer × 2 inner (x-major)
    # x=0,y=0→1.0  x=0,y=1→1.3 | x=1,y=0→1.1  x=1,y=1→1.4 | x=2,y=0→1.2  x=2,y=1→1.5
    type(func).ValueConverted = PropertyMock(return_value=((1.0, 1.3), (1.1, 1.4), (1.2, 1.5)))
    type(func).ValueSource = PropertyMock(return_value=((10, 13), (11, 14), (12, 15)))
    type(func).Unit = PropertyMock(return_value="mg")
    var.FunctionValues = func
    return var


class TestReadMapVariable:
    def test_reads_axes_and_matrix(self) -> None:
        var = _make_map_variable("FuelMap")
        app = _make_app_with_variables([var])
        result = read_map_variable(app, "FuelMap")
        assert result["variable_type"] == "Map"
        assert result["x_axis"]["size"] == 3
        assert result["y_axis"]["size"] == 2
        assert result["function_values"]["rows"] == 2
        assert result["function_values"]["cols"] == 3
        assert len(result["function_values"]["values"]) == 2
        assert len(result["function_values"]["values"][0]) == 3

    def test_reads_source_format(self) -> None:
        var = _make_map_variable("FuelMap")
        app = _make_app_with_variables([var])
        result = read_map_variable(app, "FuelMap", value_format="Source")
        assert result["value_format"] == "Source"

    def test_includes_timestamp(self) -> None:
        var = _make_map_variable("FuelMap")
        app = _make_app_with_variables([var])
        result = read_map_variable(app, "FuelMap")
        assert result["timestamp_utc"].endswith("Z")


# ── write_map_variable ────────────────────────────────────────────────────────


class TestWriteMapVariable:
    def test_writes_function_matrix(self) -> None:
        var = _make_map_variable("FuelMap")
        app = _make_app_with_variables([var])
        matrix = [[1.0, 1.1, 1.2], [1.3, 1.4, 1.5]]
        result = write_map_variable(app, "FuelMap", matrix)
        assert result["written"] is True
        assert result["function_values_written"] == [2, 3]
        assert result["x_axis_written"] is False
        assert result["y_axis_written"] is False

    def test_writes_with_axes(self) -> None:
        var = _make_map_variable("FuelMap")
        app = _make_app_with_variables([var])
        matrix = [[1.0, 1.1, 1.2], [1.3, 1.4, 1.5]]
        result = write_map_variable(
            app, "FuelMap", matrix, x_axis_values=[0.0, 50.0, 100.0], y_axis_values=[0, 3000]
        )
        assert result["x_axis_written"] is True
        assert result["y_axis_written"] is True

    def test_includes_timestamp(self) -> None:
        var = _make_map_variable("FuelMap")
        app = _make_app_with_variables([var])
        result = write_map_variable(app, "FuelMap", [[1.0, 1.1, 1.2]])
        assert result["timestamp_utc"].endswith("Z")


# ── list_array_elements ───────────────────────────────────────────────────────


def _make_array_variable(name: str = "ParamVector", count: int = 3) -> MagicMock:
    var = MagicMock()
    ident = _make_identifier(unique_name=name)
    type(var).Identifier = PropertyMock(return_value=ident)
    type(var).Type = PropertyMock(return_value="MeasurementArray")

    elements = []
    for i in range(count):
        elem = MagicMock()
        elem_ident = _make_identifier(
            unique_name=f"{name}[{i}]",
            connection_path=f"XCP()://{name}[{i}]",
            path=f"XCP()://{name}[{i}]",
        )
        type(elem).Identifier = PropertyMock(return_value=elem_ident)
        type(elem).Type = PropertyMock(return_value="Measurement")
        type(elem).IsReadable = PropertyMock(return_value=True)
        type(elem).IsWritable = PropertyMock(return_value=False)
        type(elem).Unit = PropertyMock(return_value="V")
        elements.append(elem)

    sub_col = MagicMock()
    type(sub_col).Count = PropertyMock(return_value=count)

    def _item(key):
        if isinstance(key, int):
            return elements[key]  # 0-based
        raise Exception(f"Not found: {key}")

    sub_col.Item.side_effect = _item
    var.SubElements = sub_col
    return var


class TestListArrayElements:
    def test_returns_elements_with_paths(self) -> None:
        var = _make_array_variable("ParamVector", count=3)
        app = _make_app_with_variables([var])
        result = list_array_elements(app, "ParamVector")
        assert result["total_elements"] == 3
        assert len(result["elements"]) == 3
        assert result["elements"][0]["index"] == 0
        assert result["elements"][0]["path"] == "XCP()://ParamVector[0]"

    def test_raises_precondition_for_missing_variable(self) -> None:
        app = _make_app_with_variables([])
        with pytest.raises(BridgePreconditionError):
            list_array_elements(app, "nonexistent")


# ── read_array_element ────────────────────────────────────────────────────────


class TestReadArrayElement:
    def test_reads_element_by_path(self) -> None:
        elem = MagicMock()
        elem_ident = _make_identifier(
            unique_name="ParamVector[0]",
            connection_path="XCP()://ParamVector[0]",
        )
        type(elem).Identifier = PropertyMock(return_value=elem_ident)
        type(elem).Type = PropertyMock(return_value="Measurement")
        type(elem).ValueConverted = PropertyMock(return_value=12.34)
        type(elem).Unit = PropertyMock(return_value="V")

        col = _make_variables_collection([])
        col.ItemByPath.side_effect = None
        col.ItemByPath.return_value = elem

        app = MagicMock()
        exp = MagicMock()
        plats = MagicMock()
        type(plats).Count = PropertyMock(return_value=1)
        plat = MagicMock()
        var_desc = MagicMock()
        var_desc.Variables = col
        plat.ActiveVariableDescription = var_desc
        plats.Item.return_value = plat
        exp.Platforms = plats
        app.ActiveExperiment = exp

        result = read_array_element(app, "XCP()://ParamVector[0]")
        assert result["element_path"] == "XCP()://ParamVector[0]"
        assert result["index"] == 0
        assert "value" in result

    def test_includes_timestamp(self) -> None:
        elem = MagicMock()
        elem_ident = _make_identifier(
            unique_name="P[1]",
            connection_path="XCP()://ParamVector[1]",
        )
        type(elem).Identifier = PropertyMock(return_value=elem_ident)
        type(elem).Type = PropertyMock(return_value="Measurement")
        type(elem).ValueConverted = PropertyMock(return_value=5.0)
        type(elem).Unit = PropertyMock(return_value="V")

        col = _make_variables_collection([])
        col.ItemByPath.side_effect = None
        col.ItemByPath.return_value = elem

        app = MagicMock()
        exp = MagicMock()
        plats = MagicMock()
        type(plats).Count = PropertyMock(return_value=1)
        plat = MagicMock()
        var_desc = MagicMock()
        var_desc.Variables = col
        plat.ActiveVariableDescription = var_desc
        plats.Item.return_value = plat
        exp.Platforms = plats
        app.ActiveExperiment = exp

        result = read_array_element(app, "XCP()://ParamVector[1]")
        assert result["timestamp_utc"].endswith("Z")


# ── write_array_element ───────────────────────────────────────────────────────


class TestWriteArrayElement:
    def test_writes_element_by_path(self) -> None:
        elem = MagicMock()
        elem_ident = _make_identifier(
            unique_name="ParamVector[0]",
            connection_path="XCP()://ParamVector[0]",
        )
        type(elem).Identifier = PropertyMock(return_value=elem_ident)
        type(elem).Type = PropertyMock(return_value="Parameter")
        type(elem).Unit = PropertyMock(return_value="V")

        col = _make_variables_collection([])
        col.ItemByPath.side_effect = None
        col.ItemByPath.return_value = elem

        app = MagicMock()
        exp = MagicMock()
        plats = MagicMock()
        type(plats).Count = PropertyMock(return_value=1)
        plat = MagicMock()
        var_desc = MagicMock()
        var_desc.Variables = col
        plat.ActiveVariableDescription = var_desc
        plats.Item.return_value = plat
        exp.Platforms = plats
        app.ActiveExperiment = exp

        result = write_array_element(app, "XCP()://ParamVector[0]", 15.0)
        assert result["written"] is True
        assert result["value_written"] == 15.0
        assert result["index"] == 0


# ── list_group_variables ──────────────────────────────────────────────────────


class TestListGroupVariables:
    def test_returns_root_group_when_path_empty(self) -> None:
        app = _make_app_with_variables([])
        result = list_group_variables(app, "")
        assert result["group_path"] == ""
        assert "variables" in result
        assert "sub_groups" in result

    def test_raises_precondition_for_missing_group(self) -> None:
        app = _make_app_with_variables([])
        # Force Groups.Item to raise to simulate group not found
        plat = app.ActiveExperiment.Platforms.Item(0)
        var_desc = plat.ActiveVariableDescription
        root_group = var_desc.RootGroup
        root_group.Groups.Item.side_effect = Exception("Group not found")
        with pytest.raises(BridgePreconditionError):
            list_group_variables(app, "NonExistentGroup")


# ── activate_working_page ─────────────────────────────────────────────────────


class TestActivateWorkingPage:
    def test_activates_working_page(self) -> None:
        app = _make_app_with_variables([])
        result = activate_working_page(app)
        assert result["activated"] is True
        assert result["data_set"] == "WorkingDataSet"
        assert result["platform_name"] == "XCP"
        assert result["timestamp_utc"].endswith("Z")

    def test_calls_activate_on_working_dataset(self) -> None:
        app = _make_app_with_variables([])
        activate_working_page(app)
        plat = app.ActiveExperiment.Platforms.Item(1)
        var_desc = plat.ActiveVariableDescription
        var_desc.DataSets.WorkingDataSet.Activate.assert_called_once()

    def test_raises_precondition_when_no_var_desc(self) -> None:
        app = _make_app_no_var_desc()
        with pytest.raises(BridgePreconditionError):
            activate_working_page(app)


# ── activate_reference_page ───────────────────────────────────────────────────


class TestActivateReferencePage:
    def test_activates_reference_page(self) -> None:
        app = _make_app_with_variables([])
        result = activate_reference_page(app)
        assert result["activated"] is True
        assert result["data_set"] == "ReferenceDataSet"
        assert result["platform_name"] == "XCP"

    def test_calls_activate_on_reference_dataset(self) -> None:
        app = _make_app_with_variables([])
        activate_reference_page(app)
        plat = app.ActiveExperiment.Platforms.Item(1)
        var_desc = plat.ActiveVariableDescription
        var_desc.DataSets.ReferenceDataSet.Activate.assert_called_once()


# ── list_variable_descriptions ────────────────────────────────────────────────


class TestListVariableDescriptions:
    def test_returns_descriptions(self) -> None:
        app = _make_app_with_variables([])
        result = list_variable_descriptions(app, "XCP")
        assert result["platform_name"] == "XCP"
        assert result["total_count"] == 1
        assert result["variable_descriptions"][0]["name"] == "myecu"
        assert result["variable_descriptions"][0]["is_active"] is True

    def test_raises_precondition_for_unknown_platform(self) -> None:
        app = _make_app_with_variables([])
        app.ActiveExperiment.Platforms.Item.side_effect = Exception("Not found")
        with pytest.raises(BridgePreconditionError):
            list_variable_descriptions(app, "Unknown")


# ── activate_variable_description ─────────────────────────────────────────────


class TestActivateVariableDescription:
    def test_activates_description(self) -> None:
        app = _make_app_with_variables([])
        result = activate_variable_description(app, "XCP", "myecu")
        assert result["activated"] is True
        assert result["platform_name"] == "XCP"
        assert result["description_name"] == "myecu"

    def test_raises_precondition_for_missing_description(self) -> None:
        app = _make_app_with_variables([])
        app.ActiveExperiment.Platforms.Item(1).VariableDescriptions.Item.side_effect = Exception(
            "Not found"
        )
        with pytest.raises(BridgePreconditionError):
            activate_variable_description(app, "XCP", "nonexistent")


# ── remove_variable_description ───────────────────────────────────────────────


class TestRemoveVariableDescription:
    def test_removes_description(self) -> None:
        app = _make_app_with_variables([])
        result = remove_variable_description(app, "XCP", "myecu")
        assert result["removed"] is True
        assert result["platform_name"] == "XCP"
        assert result["description_name"] == "myecu"
        # Verify Remove() was called on the individual item, not the collection
        app.ActiveExperiment.Platforms.Item("XCP").VariableDescriptions.Item.assert_called_with(
            "myecu"
        )
        app.ActiveExperiment.Platforms.Item(
            "XCP"
        ).VariableDescriptions.Item.return_value.Remove.assert_called_once()

    def test_raises_when_description_not_found(self) -> None:
        app = _make_app_with_variables([])
        app.ActiveExperiment.Platforms.Item("XCP").VariableDescriptions.Contains.return_value = (
            False
        )
        with pytest.raises(BridgePreconditionError):
            remove_variable_description(app, "XCP", "nonexistent")


# ── read_string_variable ──────────────────────────────────────────────────────


def _make_string_variable(name: str = "ECU_Label", value: str = "Calibration_v1") -> MagicMock:
    var = MagicMock()
    ident = _make_identifier(unique_name=name)
    type(var).Identifier = PropertyMock(return_value=ident)
    type(var).Type = PropertyMock(return_value="String")
    type(var).Value = PropertyMock(return_value=value)
    type(var).MaxLength = PropertyMock(return_value=64)
    return var


class TestReadStringVariable:
    def test_reads_string_value(self) -> None:
        var = _make_string_variable("ECU_Label", "Calibration_v1")
        app = _make_app_with_variables([var])
        result = read_string_variable(app, "ECU_Label")
        assert result["variable_name"] == "ECU_Label"
        assert result["variable_type"] == "String"
        assert result["value"] == "Calibration_v1"
        assert result["max_length"] == 64
        assert result["timestamp_utc"].endswith("Z")

    def test_raises_precondition_for_missing_variable(self) -> None:
        app = _make_app_with_variables([])
        with pytest.raises(BridgePreconditionError):
            read_string_variable(app, "nonexistent")


# ── write_string_variable ─────────────────────────────────────────────────────


class TestWriteStringVariable:
    def test_writes_string_value(self) -> None:
        var = _make_string_variable("ECU_Label")
        app = _make_app_with_variables([var])
        result = write_string_variable(app, "ECU_Label", "Calibration_v2.0.0")
        assert result["written"] is True
        assert result["variable_name"] == "ECU_Label"
        assert result["value_written"] == "Calibration_v2.0.0"
        assert result["timestamp_utc"].endswith("Z")

    def test_raises_precondition_for_missing_variable(self) -> None:
        app = _make_app_with_variables([])
        with pytest.raises(BridgePreconditionError):
            write_string_variable(app, "nonexistent", "value")
