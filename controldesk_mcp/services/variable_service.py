"""Service facade for ControlDesk variable read/write management operations.

Owns: orchestration of variable discovery, scalar/curve/map/array read-write flows,
      data set page activation, and variable description management.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError, BridgeOperationError
from controldesk_mcp.models.envelope_builder import build_envelope
from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.variable import (
    DataSetActivateReferencePageResult,
    DataSetActivateWorkingPageResult,
    VariableDescriptionActivateInput,
    VariableDescriptionActivateResult,
    VariableDescriptionListInput,
    VariableDescriptionListResult,
    VariableDescriptionRemoveInput,
    VariableDescriptionRemoveResult,
    VariableFindInput,
    VariableFindResult,
    VariableGetInfoInput,
    VariableGetInfoResult,
    VariableListAllResult,
    VariableListArrayElementsInput,
    VariableListArrayElementsResult,
    VariableListGroupVariablesInput,
    VariableListGroupVariablesResult,
    VariableReadArrayElementInput,
    VariableReadArrayElementResult,
    VariableReadCurveInput,
    VariableReadCurveResult,
    VariableReadMapInput,
    VariableReadMapResult,
    VariableReadScalarInput,
    VariableReadScalarResult,
    VariableReadStringInput,
    VariableReadStringResult,
    VariableWriteArrayElementInput,
    VariableWriteArrayElementResult,
    VariableWriteCurveInput,
    VariableWriteCurveResult,
    VariableWriteDryRunResult,
    VariableWriteMapInput,
    VariableWriteMapResult,
    VariableWriteScalarInput,
    VariableWriteScalarResult,
    VariableWriteStringInput,
    VariableWriteStringResult,
)
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)


def _get_app_lambda():
    return lambda: com_bridge.get_connection().get_app()


async def find_variable(params: VariableFindInput) -> VariableFindResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        search_mode = params.search_mode.value if params.search_mode else None
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.find_variable, app, params.identifier, search_mode
        )
        return VariableFindResult(**result)
    except BridgeError as exc:
        _log.warning("variable_find failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_find unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def list_all_variables() -> VariableListAllResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(com_bridge.domains.variable_com.list_all_variables, app)
        return VariableListAllResult(**result)
    except BridgeError as exc:
        _log.warning("variable_list_all failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_list_all unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def get_variable_info(params: VariableGetInfoInput) -> VariableGetInfoResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(com_bridge.domains.variable_com.get_variable_info, app, params.variable_name)
        return VariableGetInfoResult(**result)
    except BridgeError as exc:
        _log.warning("variable_get_info failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_get_info unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def read_scalar_variable(
    params: VariableReadScalarInput,
) -> VariableReadScalarResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_scalar_variable,
            app,
            params.variable_name,
            params.value_format.value,
        )
        return VariableReadScalarResult(**result)
    except BridgeError as exc:
        _log.warning("variable_read_scalar failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_read_scalar unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def write_scalar_variable(
    params: VariableWriteScalarInput,
) -> VariableWriteScalarResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_scalar_variable,
            app,
            params.variable_name,
            params.value,
            params.value_format.value,
        )
        return VariableWriteScalarResult(**result)
    except BridgeError as exc:
        _log.warning("variable_write_scalar failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_write_scalar unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def read_curve_variable(
    params: VariableReadCurveInput,
) -> VariableReadCurveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_curve_variable,
            app,
            params.variable_name,
            params.value_format.value,
        )
        return VariableReadCurveResult(**result)
    except BridgeError as exc:
        _log.warning("variable_read_curve failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_read_curve unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def write_curve_variable(
    params: VariableWriteCurveInput,
) -> VariableWriteCurveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_curve_variable,
            app,
            params.variable_name,
            params.function_values,
            params.axis_values,
            params.value_format.value,
        )
        return VariableWriteCurveResult(**result)
    except BridgeError as exc:
        _log.warning("variable_write_curve failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_write_curve unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def read_map_variable(params: VariableReadMapInput) -> VariableReadMapResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_map_variable,
            app,
            params.variable_name,
            params.value_format.value,
        )
        return VariableReadMapResult(**result)
    except BridgeError as exc:
        _log.warning("variable_read_map failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_read_map unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def write_map_variable(
    params: VariableWriteMapInput,
) -> VariableWriteMapResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_map_variable,
            app,
            params.variable_name,
            params.function_values,
            params.x_axis_values,
            params.y_axis_values,
            params.value_format.value,
        )
        return VariableWriteMapResult(**result)
    except BridgeError as exc:
        _log.warning("variable_write_map failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_write_map unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def list_array_elements(
    params: VariableListArrayElementsInput,
) -> VariableListArrayElementsResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.list_array_elements, app, params.variable_name
        )
        return VariableListArrayElementsResult(**result)
    except BridgeError as exc:
        _log.warning("variable_list_array_elements failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_list_array_elements unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def read_array_element(
    params: VariableReadArrayElementInput,
) -> VariableReadArrayElementResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_array_element,
            app,
            params.element_path,
            params.value_format.value,
        )
        return VariableReadArrayElementResult(**result)
    except BridgeError as exc:
        _log.warning("variable_read_array_element failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_read_array_element unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def write_array_element(
    params: VariableWriteArrayElementInput,
) -> VariableWriteArrayElementResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_array_element,
            app,
            params.element_path,
            params.value,
            params.value_format.value,
        )
        return VariableWriteArrayElementResult(**result)
    except BridgeError as exc:
        _log.warning("variable_write_array_element failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_write_array_element unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def list_group_variables(
    params: VariableListGroupVariablesInput,
) -> VariableListGroupVariablesResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(com_bridge.domains.variable_com.list_group_variables, app, params.group_path)
        return VariableListGroupVariablesResult(**result)
    except BridgeError as exc:
        _log.warning("variable_list_group_variables failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_list_group_variables unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def activate_working_page() -> DataSetActivateWorkingPageResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(com_bridge.domains.variable_com.activate_working_page, app)
        return DataSetActivateWorkingPageResult(**result)
    except BridgeError as exc:
        _log.warning("data_set_activate_working_page failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("data_set_activate_working_page unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def activate_reference_page() -> DataSetActivateReferencePageResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(com_bridge.domains.variable_com.activate_reference_page, app)
        return DataSetActivateReferencePageResult(**result)
    except BridgeError as exc:
        _log.warning("data_set_activate_reference_page failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("data_set_activate_reference_page unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def list_variable_descriptions(
    params: VariableDescriptionListInput,
) -> VariableDescriptionListResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.list_variable_descriptions, app, params.platform_name
        )
        return VariableDescriptionListResult(**result)
    except BridgeError as exc:
        _log.warning("variable_description_list failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_description_list unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def activate_variable_description(
    params: VariableDescriptionActivateInput,
) -> VariableDescriptionActivateResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.activate_variable_description,
            app,
            params.platform_name,
            params.variable_description_name,
        )
        return VariableDescriptionActivateResult(**result)
    except BridgeError as exc:
        _log.warning("variable_description_activate failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_description_activate unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def remove_variable_description(
    params: VariableDescriptionRemoveInput,
) -> VariableDescriptionRemoveResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.remove_variable_description,
            app,
            params.platform_name,
            params.variable_description_name,
        )
        return VariableDescriptionRemoveResult(**result)
    except BridgeError as exc:
        _log.warning("variable_description_remove failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_description_remove unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def read_string_variable(
    params: VariableReadStringInput,
) -> VariableReadStringResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_string_variable, app, params.variable_name
        )
        return VariableReadStringResult(**result)
    except BridgeError as exc:
        _log.warning("variable_read_string failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_read_string unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def write_string_variable(
    params: VariableWriteStringInput,
) -> VariableWriteStringResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_string_variable,
            app,
            params.variable_name,
            params.value,
        )
        return VariableWriteStringResult(**result)
    except BridgeError as exc:
        _log.warning("variable_write_string failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_write_string unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))


async def dry_run_write(
    action: str,
    variable_name: str,
    proposed_value: object,
    value_format: str,
) -> VariableWriteDryRunResult | ErrorEnvelope:
    """Read the current value and return a diff without writing to the ECU."""
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        # Read via the generic scalar path; curves/maps fall back gracefully
        current_raw = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_scalar_variable,
            app,
            variable_name,
            value_format,
        )
        current_value = current_raw.get("value")
        unit = current_raw.get("unit", "")
        return VariableWriteDryRunResult(
            action=action,
            variable_name=variable_name,
            current_value=current_value,
            proposed_value=proposed_value,
            value_format=value_format,
            unit=unit,
            would_change=current_value != proposed_value,
        )
    except BridgeError as exc:
        _log.warning("variable_dry_run_write failed: %s", exc)
        return build_envelope(exc)
    except Exception as exc:
        _log.exception("variable_dry_run_write unexpected error")
        return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))
