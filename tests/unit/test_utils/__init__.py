"""Unit tests for variable management MCP tools.

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.variable import (
    DataSetActivateReferencePageResult,
    DataSetActivateWorkingPageResult,
    DataSetManageAction,
    DataSetManageInput,
    VariableDescriptionActivateResult,
    VariableDescriptionListResult,
    VariableDescriptionManageAction,
    VariableDescriptionManageInput,
    VariableDescriptionRemoveResult,
    VariableDiscoverResult,
    VariableFindInput,
    VariableFindResult,
    VariableListAction,
    VariableListAllResult,
    VariableListArrayElementsResult,
    VariableListGroupVariablesResult,
    VariableListInput,
    VariableReadArrayElementResult,
    VariableReadCurveResult,
    VariableReadInput,
    VariableReadMapResult,
    VariableReadScalarResult,
    VariableReadStringResult,
    VariableReadType,
    VariableWriteAction,
    VariableWriteArrayElementResult,
    VariableWriteCurveResult,
    VariableWriteInput,
    VariableWriteMapResult,
    VariableWriteScalarResult,
    VariableWriteStringResult,
)

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.variable_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── TestVariableFind ──────────────────────────────────────────────────────────


class TestVariableFind:
    @pytest.mark.asyncio
    async def test_calls_service(self) -> None:
        expected = VariableFindResult(
            found=True,
            name="f_Kp_1",
            variable_type="Parameter",
            is_readable=True,
            is_writable=True,
        )
        with _patch_svc("find_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_find

            result = await variable_find(VariableFindInput(identifier="f_Kp_1"))

        assert isinstance(result, VariableFindResult)
        assert result["found"] is True
        assert result["name"] == "f_Kp_1"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("find_variable", return_value=_ERROR):
            from controldesk_mcp.tools.variable_management.management import variable_find

            result = await variable_find(VariableFindInput(identifier="missing"))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "E001"


# ── TestVariableRead ──────────────────────────────────────────────────────────


class TestVariableRead:
    @pytest.mark.asyncio
    async def test_scalar_calls_service(self) -> None:
        expected = VariableReadScalarResult(
            variable_name="f_Kp_1",
            variable_type="Parameter",
            value=0.5,
            value_format="Converted",
            unit="deg",
            timestamp_utc=_TS,
        )
        with _patch_svc("read_scalar_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_read

            result = await variable_read(
                VariableReadInput(read_type=VariableReadType.scalar, variable_name="f_Kp_1")
            )

        assert isinstance(result, VariableReadScalarResult)
        assert result["value"] == 0.5

    @pytest.mark.asyncio
    async def test_scalar_missing_variable_name(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_read

        result = await variable_read(VariableReadInput(read_type=VariableReadType.scalar))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_curve_calls_service(self) -> None:
        expected = VariableReadCurveResult(
            variable_name="FuelCurve",
            variable_type="Curve",
            axis={"size": 3, "values": [0.0, 1.0, 2.0], "unit": "rpm"},
            function_values={"size": 3, "values": [1.5, 1.6, 1.7], "unit": "V"},
            value_format="Converted",
            timestamp_utc=_TS,
        )
        with _patch_svc("read_curve_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_read

            result = await variable_read(
                VariableReadInput(read_type=VariableReadType.curve, variable_name="FuelCurve")
            )

        assert isinstance(result, VariableReadCurveResult)
        assert result["variable_type"] == "Curve"

    @pytest.mark.asyncio
    async def test_curve_missing_variable_name(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_read

        result = await variable_read(VariableReadInput(read_type=VariableReadType.curve))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_map_calls_service(self) -> None:
        expected = VariableReadMapResult(
            variable_name="FuelMap",
            variable_type="Map",
            x_axis={"size": 3, "values": [0.0, 50.0, 100.0], "unit": "percent"},
            y_axis={"size": 2, "values": [0, 3000], "unit": "rpm"},
            function_values={"rows": 2, "cols": 3, "values": [[1.0, 1.1, 1.2], [1.3, 1.4, 1.5]]},
            value_format="Converted",
            timestamp_utc=_TS,
        )
        with _patch_svc("read_map_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_read

            result = await variable_read(
                VariableReadInput(read_type=VariableReadType.map, variable_name="FuelMap")
            )

        assert isinstance(result, VariableReadMapResult)
        assert result["variable_type"] == "Map"

    @pytest.mark.asyncio
    async def test_map_missing_variable_name(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_read

        result = await variable_read(VariableReadInput(read_type=VariableReadType.map))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_array_element_calls_service(self) -> None:
        expected = VariableReadArrayElementResult(
            variable_name="ParamVector",
            array_path="XCP()://ParamVector",
            index=0,
            value=12.34,
            unit="V",
            timestamp_utc=_TS,
        )
        with _patch_svc("read_array_element", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_read

            result = await variable_read(
                VariableReadInput(
                    read_type=VariableReadType.array_element,
                    element_path="XCP()://ParamVector[0]",
                )
            )

        assert isinstance(result, VariableReadArrayElementResult)
        assert result["index"] == 0

    @pytest.mark.asyncio
    async def test_array_element_missing_element_path(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_read

        result = await variable_read(VariableReadInput(read_type=VariableReadType.array_element))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_string_calls_service(self) -> None:
        expected = VariableReadStringResult(
            variable_name="ECU_Label",
            variable_type="String",
            value="Calibration_v1.2.3",
            timestamp_utc=_TS,
        )
        with _patch_svc("read_string_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_read

            result = await variable_read(
                VariableReadInput(read_type=VariableReadType.string, variable_name="ECU_Label")
            )

        assert isinstance(result, VariableReadStringResult)
        assert result["value"] == "Calibration_v1.2.3"

    @pytest.mark.asyncio
    async def test_string_missing_variable_name(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_read

        result = await variable_read(VariableReadInput(read_type=VariableReadType.string))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("read_scalar_variable", return_value=_ERROR):
            from controldesk_mcp.tools.variable_management.management import variable_read

            result = await variable_read(
                VariableReadInput(read_type=VariableReadType.scalar, variable_name="f_Kp_1")
            )

        assert isinstance(result, ErrorEnvelope)


# ── TestVariableWrite ─────────────────────────────────────────────────────────


class TestVariableWrite:
    @pytest.mark.asyncio
    async def test_scalar_calls_service(self) -> None:
        expected = VariableWriteScalarResult(
            written=True,
            variable_name="f_Kp_1",
            variable_type="Parameter",
            value_written=0.12,
            value_format="Converted",
            unit="deg",
            timestamp_utc=_TS,
        )
        with _patch_svc("write_scalar_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_write

            result = await variable_write(
                VariableWriteInput(
                    action=VariableWriteAction.scalar,
                    variable_name="f_Kp_1",
                    value=0.12,
                )
            )

        assert isinstance(result, VariableWriteScalarResult)
        assert result["written"] is True
        assert result["value_written"] == 0.12

    @pytest.mark.asyncio
    async def test_scalar_missing_params(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_write

        result = await variable_write(
            VariableWriteInput(action=VariableWriteAction.scalar, variable_name="f_Kp_1")
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_array_element_calls_service(self) -> None:
        expected = VariableWriteArrayElementResult(
            written=True,
            variable_name="ParamVector",
            array_path="XCP()://ParamVector",
            index=0,
            value_written=15.0,
            timestamp_utc=_TS,
        )
        with _patch_svc("write_array_element", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_write

            result = await variable_write(
                VariableWriteInput(
                    action=VariableWriteAction.array_element,
                    element_path="XCP()://ParamVector[0]",
                    value=15.0,
                )
            )

        assert isinstance(result, VariableWriteArrayElementResult)
        assert result["written"] is True

    @pytest.mark.asyncio
    async def test_array_element_missing_params(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_write

        result = await variable_write(
            VariableWriteInput(action=VariableWriteAction.array_element, value=1.0)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_string_calls_service(self) -> None:
        expected = VariableWriteStringResult(
            written=True,
            variable_name="ECU_Label",
            value_written="Calibration_v2.0.0",
            timestamp_utc=_TS,
        )
        with _patch_svc("write_string_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_write

            result = await variable_write(
                VariableWriteInput(
                    action=VariableWriteAction.string,
                    variable_name="ECU_Label",
                    value="Calibration_v2.0.0",
                )
            )

        assert isinstance(result, VariableWriteStringResult)
        assert result["value_written"] == "Calibration_v2.0.0"

    @pytest.mark.asyncio
    async def test_string_missing_params(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_write

        result = await variable_write(
            VariableWriteInput(action=VariableWriteAction.string, value="test")
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_curve_calls_service(self) -> None:
        expected = VariableWriteCurveResult(
            written=True,
            variable_name="FuelCurve",
            function_values_count=3,
            axis_values_count=0,
            value_format="Converted",
            timestamp_utc=_TS,
        )
        with _patch_svc("write_curve_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_write

            result = await variable_write(
                VariableWriteInput(
                    action=VariableWriteAction.curve,
                    variable_name="FuelCurve",
                    function_values=[1.4, 1.5, 1.6],
                )
            )

        assert isinstance(result, VariableWriteCurveResult)
        assert result["function_values_count"] == 3

    @pytest.mark.asyncio
    async def test_curve_missing_params(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_write

        result = await variable_write(
            VariableWriteInput(action=VariableWriteAction.curve, variable_name="FuelCurve")
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_map_calls_service(self) -> None:
        expected = VariableWriteMapResult(
            written=True,
            variable_name="FuelMap",
            rows=2,
            cols=3,
            value_format="Converted",
            timestamp_utc=_TS,
        )
        with _patch_svc("write_map_variable", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_write

            result = await variable_write(
                VariableWriteInput(
                    action=VariableWriteAction.map,
                    variable_name="FuelMap",
                    function_values=[[1.0, 1.1, 1.2], [1.3, 1.4, 1.5]],
                )
            )

        assert isinstance(result, VariableWriteMapResult)
        assert result["rows"] == 2

    @pytest.mark.asyncio
    async def test_map_missing_params(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_write

        result = await variable_write(
            VariableWriteInput(action=VariableWriteAction.map, variable_name="FuelMap")
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("write_scalar_variable", return_value=_ERROR):
            from controldesk_mcp.tools.variable_management.management import variable_write

            result = await variable_write(
                VariableWriteInput(
                    action=VariableWriteAction.scalar,
                    variable_name="f_Kp_1",
                    value=0.5,
                )
            )

        assert isinstance(result, ErrorEnvelope)


# ── TestVariableList ──────────────────────────────────────────────────────────


class TestVariableList:
    @pytest.mark.asyncio
    async def test_list_all_calls_service(self) -> None:
        expected = VariableListAllResult(
            total_count=2,
            by_type={"Parameter": [{"name": "f_Kp_1"}], "Measurement": [{"name": "control_out"}]},
        )
        with _patch_svc("list_all_variables", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_list

            result = await variable_list(VariableListInput(action=VariableListAction.list_all))

        assert isinstance(result, VariableListAllResult)
        assert result["total_count"] == 2

    @pytest.mark.asyncio
    async def test_list_array_elements_calls_service(self) -> None:
        expected = VariableListArrayElementsResult(
            total_count=3,
            elements=[
                {"index": 0, "path": "XCP()://ParamVector[0]"},
                {"index": 1, "path": "XCP()://ParamVector[1]"},
                {"index": 2, "path": "XCP()://ParamVector[2]"},
            ],
        )
        with _patch_svc("list_array_elements", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_list

            result = await variable_list(
                VariableListInput(
                    action=VariableListAction.list_array_elements,
                    variable_name="ParamVector",
                )
            )

        assert isinstance(result, VariableListArrayElementsResult)
        assert result["total_count"] == 3

    @pytest.mark.asyncio
    async def test_list_array_elements_missing_variable_name(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_list

        result = await variable_list(
            VariableListInput(action=VariableListAction.list_array_elements)
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_list_group_variables_calls_service(self) -> None:
        expected = VariableListGroupVariablesResult(
            total_count=1,
            group_path="Engine Control",
            variables=[{"name": "fuel_pressure_target", "type": "Parameter"}],
        )
        with _patch_svc("list_group_variables", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_list

            result = await variable_list(
                VariableListInput(
                    action=VariableListAction.list_group_variables,
                    group_path="Engine Control",
                )
            )

        assert isinstance(result, VariableListGroupVariablesResult)
        assert result["group_path"] == "Engine Control"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("list_all_variables", return_value=_ERROR):
            from controldesk_mcp.tools.variable_management.management import variable_list

            result = await variable_list(VariableListInput(action=VariableListAction.list_all))

        assert isinstance(result, ErrorEnvelope)


# ── TestDataSetManage ─────────────────────────────────────────────────────────


class TestDataSetManage:
    @pytest.mark.asyncio
    async def test_activate_working_page_calls_service(self) -> None:
        expected = DataSetActivateWorkingPageResult(activated=True, data_set="WorkingDataSet")
        with _patch_svc("activate_working_page", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import data_set_manage

            result = await data_set_manage(
                DataSetManageInput(action=DataSetManageAction.activate_working_page)
            )

        assert isinstance(result, DataSetActivateWorkingPageResult)
        assert result["activated"] is True
        assert result["data_set"] == "WorkingDataSet"

    @pytest.mark.asyncio
    async def test_activate_reference_page_calls_service(self) -> None:
        expected = DataSetActivateReferencePageResult(activated=True, data_set="ReferenceDataSet")
        with _patch_svc("activate_reference_page", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import data_set_manage

            result = await data_set_manage(
                DataSetManageInput(action=DataSetManageAction.activate_reference_page)
            )

        assert isinstance(result, DataSetActivateReferencePageResult)
        assert result["activated"] is True

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("activate_working_page", return_value=_ERROR):
            from controldesk_mcp.tools.variable_management.management import data_set_manage

            result = await data_set_manage(
                DataSetManageInput(action=DataSetManageAction.activate_working_page)
            )

        assert isinstance(result, ErrorEnvelope)


# ── TestVariableDescriptionManage ─────────────────────────────────────────────


class TestVariableDescriptionManage:
    @pytest.mark.asyncio
    async def test_list_calls_service(self) -> None:
        expected = VariableDescriptionListResult(
            platform_name="XCP",
            total_count=1,
            variable_descriptions=[{"name": "myecu", "is_active": True}],
        )
        with _patch_svc("list_variable_descriptions", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_description_manage

            result = await variable_description_manage(
                VariableDescriptionManageInput(
                    action=VariableDescriptionManageAction.list,
                    platform_name="XCP",
                )
            )

        assert isinstance(result, VariableDescriptionListResult)
        assert result["total_count"] == 1

    @pytest.mark.asyncio
    async def test_activate_calls_service(self) -> None:
        expected = VariableDescriptionActivateResult(
            activated=True,
            platform_name="XCP",
            variable_description_name="myecu_v2",
        )
        with _patch_svc("activate_variable_description", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_description_manage

            result = await variable_description_manage(
                VariableDescriptionManageInput(
                    action=VariableDescriptionManageAction.activate,
                    platform_name="XCP",
                    variable_description_name="myecu_v2",
                )
            )

        assert isinstance(result, VariableDescriptionActivateResult)
        assert result["activated"] is True
        assert result["variable_description_name"] == "myecu_v2"

    @pytest.mark.asyncio
    async def test_remove_calls_service(self) -> None:
        expected = VariableDescriptionRemoveResult(
            removed=True,
            platform_name="XCP",
            variable_description_name="myecu",
            timestamp_utc=_TS,
        )
        with _patch_svc("remove_variable_description", return_value=expected):
            from controldesk_mcp.tools.variable_management.management import variable_description_manage

            result = await variable_description_manage(
                VariableDescriptionManageInput(
                    action=VariableDescriptionManageAction.remove,
                    platform_name="XCP",
                    variable_description_name="myecu",
                )
            )

        assert isinstance(result, VariableDescriptionRemoveResult)
        assert result["removed"] is True

    @pytest.mark.asyncio
    async def test_missing_platform_name_returns_error(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_description_manage

        result = await variable_description_manage(
            VariableDescriptionManageInput(
                action=VariableDescriptionManageAction.list,
                platform_name=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_missing_description_name_returns_error(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_description_manage

        result = await variable_description_manage(
            VariableDescriptionManageInput(
                action=VariableDescriptionManageAction.activate,
                platform_name="XCP",
                variable_description_name=None,
            )
        )

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("list_variable_descriptions", return_value=_ERROR):
            from controldesk_mcp.tools.variable_management.management import variable_description_manage

            result = await variable_description_manage(
                VariableDescriptionManageInput(
                    action=VariableDescriptionManageAction.list,
                    platform_name="Unknown",
                )
            )

        assert isinstance(result, ErrorEnvelope)


# ── TestVariableDiscover ──────────────────────────────────────────────────────


class TestVariableDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_discover

        result = await variable_discover(AsyncMock())

        assert isinstance(result, VariableDiscoverResult)
        assert result["status"] == "ok"
        assert len(result["tools"]) == 3

    @pytest.mark.asyncio
    async def test_discover_has_variable_list_tool(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_discover

        result = await variable_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "variable_list" in tool_names

    @pytest.mark.asyncio
    async def test_discover_has_data_set_manage_tool(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_discover

        result = await variable_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "data_set_manage" in tool_names

    @pytest.mark.asyncio
    async def test_discover_has_variable_description_manage_tool(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_discover

        result = await variable_discover(AsyncMock())

        tool_names = [t["tool_name"] for t in result["tools"]]
        assert "variable_description_manage" in tool_names

    @pytest.mark.asyncio
    async def test_variable_list_actions(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_discover

        result = await variable_discover(AsyncMock())

        variable_list_tool = next(t for t in result["tools"] if t["tool_name"] == "variable_list")
        assert "list_all" in variable_list_tool["actions"]
        assert "list_array_elements" in variable_list_tool["actions"]
        assert "list_group_variables" in variable_list_tool["actions"]

    @pytest.mark.asyncio
    async def test_data_set_manage_actions(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_discover

        result = await variable_discover(AsyncMock())

        ds_tool = next(t for t in result["tools"] if t["tool_name"] == "data_set_manage")
        assert "activate_working_page" in ds_tool["actions"]
        assert "activate_reference_page" in ds_tool["actions"]

    @pytest.mark.asyncio
    async def test_variable_description_manage_actions(self) -> None:
        from controldesk_mcp.tools.variable_management.management import variable_discover

        result = await variable_discover(AsyncMock())

        vd_tool = next(
            t for t in result["tools"] if t["tool_name"] == "variable_description_manage"
        )
        assert "list" in vd_tool["actions"]
        assert "activate" in vd_tool["actions"]
        assert "remove" in vd_tool["actions"]


# ── TestVariableInputModels ───────────────────────────────────────────────────


class TestVariableInputModels:
    def test_variable_write_input_instantiates(self) -> None:
        assert (
            VariableWriteInput(
                action=VariableWriteAction.scalar,
                variable_name="f_Kp_1",
                value=0.5,
            )
            is not None
        )

    def test_variable_list_input_instantiates(self) -> None:
        assert VariableListInput(action=VariableListAction.list_all) is not None

    def test_variable_list_input_defaults(self) -> None:
        params = VariableListInput(action=VariableListAction.list_all)
        assert params.limit == 200
        assert params.offset == 0
        assert params.group_path == ""

    def test_data_set_manage_input_instantiates(self) -> None:
        assert DataSetManageInput(action=DataSetManageAction.activate_working_page) is not None

    def test_variable_description_manage_input_instantiates(self) -> None:
        assert (
            VariableDescriptionManageInput(
                action=VariableDescriptionManageAction.list,
                platform_name="XCP",
            )
            is not None
        )

    def test_variable_description_manage_pagination_defaults(self) -> None:
        params = VariableDescriptionManageInput(
            action=VariableDescriptionManageAction.list,
            platform_name="XCP",
        )
        assert params.limit == 200
        assert params.offset == 0
