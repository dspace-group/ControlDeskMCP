"""Service facade for ControlDesk variable read/write management operations.

Owns: orchestration of variable discovery, scalar/curve/map/array read-write flows,
      data set page activation, and variable description management.
Calls: com_bridge.dispatch() exclusively — never imports win32com/comtypes.
"""

from __future__ import annotations

from dataclasses import asdict
import json
import re

from controldesk_mcp import com_bridge
from controldesk_mcp.com_bridge.errors import BridgeError, BridgeOperationError
from controldesk_mcp.config.settings import get_settings
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
from controldesk_mcp.services.variable_path_resolver import (
    ResolutionStatus,
    VariablePathResolver,
    extract_instrument_tail_hint,
    is_connection_path,
)
from controldesk_mcp.utils.pagination import paginate
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)
_path_resolver: VariablePathResolver | None = None


def _get_app_lambda():
    return lambda: com_bridge.get_connection().get_app()


def _array_path_from_element_path(element_path: str) -> str:
    return re.sub(r"\[\d+\]$", "", element_path)


def _normalize_read_array_element_result(result: dict) -> dict:
    normalized = dict(result)
    element_path = str(normalized.get("element_path", "") or "")
    if element_path:
        normalized.setdefault("array_path", _array_path_from_element_path(element_path))
        normalized.setdefault("variable_name", normalized["array_path"])
    return normalized


def _normalize_write_array_element_result(result: dict) -> dict:
    normalized = dict(result)
    element_path = str(normalized.get("element_path", "") or "")
    if element_path:
        normalized.setdefault("array_path", _array_path_from_element_path(element_path))
        normalized.setdefault("variable_name", normalized["array_path"])
    return normalized


def _build_resolution_details(
    *,
    status: ResolutionStatus,
    confidence: float,
    attempt_log: list[str],
    resolved_path: str | None = None,
    candidates: list[dict] | None = None,
) -> dict:
    return {
        "status": status.value,
        "confidence": confidence,
        "resolved_path": resolved_path,
        "attempt_log": attempt_log,
        "candidates": candidates or [],
    }


def _resolver_not_found_or_ambiguous_error(identifier: str, status: ResolutionStatus, details: dict) -> ErrorEnvelope:
    attempt_log = details.get("attempt_log", [])
    candidate_list = details.get("candidates", [])
    telemetry = details.get("telemetry", {})
    candidate_lines = [
        f"{idx + 1}. {item.get('name', '<unknown>')} -> {item.get('connection_path', '')}"
        for idx, item in enumerate(candidate_list[:5])
    ]
    recovery_hint = "Run controldesk_variable_find or retry with one of the suggested candidates."
    if candidate_lines:
        recovery_hint = "Closest matches:\n" + "\n".join(candidate_lines)

    return ErrorEnvelope(
        error_code="VARIABLE_RESOLUTION_FAILED" if status == ResolutionStatus.not_found else "VARIABLE_RESOLUTION_AMBIGUOUS",
        category="INPUT_VALIDATION",
        message=(
            f"Could not resolve variable '{identifier}'."
            if status == ResolutionStatus.not_found
            else f"Variable '{identifier}' matched multiple candidates."
        ),
        detail=json.dumps(
            {
                "attempt_log": attempt_log,
                "candidates": candidate_list[:5],
                "telemetry": telemetry,
            },
            ensure_ascii=True,
        ),
        retryable=False,
        recovery_hint=recovery_hint,
    )


async def _resolver_find_variable(identifier: str, search_mode: str | None) -> dict:
    app = await com_bridge.dispatch(_get_app_lambda())
    return await com_bridge.dispatch(com_bridge.domains.variable_com.find_variable, app, identifier, search_mode)


async def _resolver_list_all_page(offset: int, limit: int) -> dict:
    app = await com_bridge.dispatch(_get_app_lambda())
    payload = await com_bridge.dispatch(com_bridge.domains.variable_com.list_all_variables, app)
    if "by_type" in payload:
        return payload
    return paginate(payload, offset=offset, limit=limit, list_key="variables")


def _get_variable_path_resolver() -> VariablePathResolver:
    global _path_resolver
    if _path_resolver is None:
        cfg = get_settings()
        _path_resolver = VariablePathResolver(
            find_variable=_resolver_find_variable,
            list_all_page=_resolver_list_all_page,
            cache_ttl_seconds=cfg.variable_resolution_cache_ttl_seconds,
            enable_cache=True,
            debug_telemetry=cfg.variable_resolution_debug_telemetry,
        )
    return _path_resolver


def clear_resolution_cache() -> None:
    """Clear cached variable resolution entries for the current process/session."""
    global _path_resolver
    if _path_resolver is None:
        return
    _path_resolver.clear_cache()


async def _resolve_variable_name_for_read(
    variable_name: str,
    *,
    instrument_names: list[str] | None = None,
) -> str | ErrorEnvelope:
    if is_connection_path(variable_name):
        return variable_name

    hint_query = extract_instrument_tail_hint(variable_name, instrument_names or [])
    resolver = _get_variable_path_resolver()
    resolution = await resolver.resolve(variable_name, hint_query=hint_query)
    if resolution.status == ResolutionStatus.resolved and resolution.resolved_path:
        return resolution.resolved_path

    return _resolver_not_found_or_ambiguous_error(
        variable_name,
        resolution.status,
        {
            "attempt_log": resolution.attempt_log,
            "candidates": [asdict(candidate) for candidate in resolution.candidates],
            "telemetry": resolution.telemetry,
        },
    )


async def _resolve_variable_name_for_write(variable_name: str) -> str | ErrorEnvelope:
    resolved_or_error = await _resolve_variable_name_for_read(variable_name)
    if isinstance(resolved_or_error, ErrorEnvelope):
        return resolved_or_error

    metadata = await _resolver_find_variable(resolved_or_error, "path")
    if not bool(metadata.get("found")):
        return ErrorEnvelope(
            error_code="VARIABLE_NOT_FOUND",
            category="INPUT_VALIDATION",
            message=f"Resolved variable path '{resolved_or_error}' is not available in the active variable description.",
            retryable=False,
            recovery_hint="Call controldesk_variable_find or controldesk_variable_list(action='list_all') and retry.",
        )

    if not bool(metadata.get("is_writable")):
        return ErrorEnvelope(
            error_code="VARIABLE_NOT_WRITABLE",
            category="PRECONDITION",
            message=f"Variable '{metadata.get('name', resolved_or_error)}' is not writable.",
            retryable=False,
            recovery_hint="Choose a writable parameter or verify the active variable description and calibration mode.",
        )

    if bool(metadata.get("is_changeable_only_during_initialization")):
        try:
            app = await com_bridge.dispatch(_get_app_lambda())
            state = await com_bridge.dispatch(com_bridge.domains.calibration_com.calibration_get_state, app)
        except BridgeError as exc:
            _log.warning("write safety calibration state probe failed: %s", exc)
            return build_envelope(exc)
        except Exception as exc:
            _log.exception("write safety calibration state probe unexpected error")
            return build_envelope(BridgeOperationError(f"Unexpected error: {exc}", error_code="BRIDGE_UNKNOWN"))

        if str(state.get("calibration_state", "")).lower() == "started":
            return ErrorEnvelope(
                error_code="VARIABLE_INIT_ONLY_LOCKED",
                category="PRECONDITION",
                message=(
                    f"Variable '{metadata.get('name', resolved_or_error)}' can only be changed during initialization "
                    "and is currently runtime-locked."
                ),
                retryable=False,
                recovery_hint="Stop online calibration or switch to an initialization context before writing this variable.",
            )

    return resolved_or_error


async def resolve_variable_path(
    identifier: str,
    *,
    instrument_names: list[str] | None = None,
) -> str | ErrorEnvelope:
    """Resolve an identifier into a concrete connection path for cross-service usage."""
    return await _resolve_variable_name_for_read(identifier, instrument_names=instrument_names)


async def find_variable(params: VariableFindInput) -> VariableFindResult | ErrorEnvelope:
    try:
        app = await com_bridge.dispatch(_get_app_lambda())
        search_mode = params.search_mode.value if params.search_mode else None
        result: dict = await com_bridge.dispatch(
            com_bridge.domains.variable_com.find_variable, app, params.identifier, search_mode
        )

        # Keep current behavior for explicit path lookups and direct hits.
        if bool(result.get("found")) or search_mode == "path" or is_connection_path(params.identifier):
            return VariableFindResult(**result)

        # For name-mode misses, run resolver fallback before returning found=False.
        resolution = await _get_variable_path_resolver().resolve(params.identifier)
        if resolution.status == ResolutionStatus.resolved and resolution.resolved_path:
            resolved_result: dict = await com_bridge.dispatch(
                com_bridge.domains.variable_com.find_variable,
                app,
                resolution.resolved_path,
                "path",
            )
            resolved_result["resolution_details"] = _build_resolution_details(
                status=resolution.status,
                confidence=resolution.confidence,
                resolved_path=resolution.resolved_path,
                attempt_log=resolution.attempt_log,
                candidates=[],
            )
            resolved_result["resolution_details"]["telemetry"] = resolution.telemetry
            return VariableFindResult(**resolved_result)

        result["resolution_details"] = _build_resolution_details(
            status=resolution.status,
            confidence=resolution.confidence,
            attempt_log=resolution.attempt_log,
            candidates=[asdict(candidate) for candidate in resolution.candidates],
        )
        result["resolution_details"]["telemetry"] = resolution.telemetry
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
        resolved_or_error = await _resolve_variable_name_for_read(params.variable_name)
        if isinstance(resolved_or_error, ErrorEnvelope):
            return resolved_or_error

        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_scalar_variable,
            app,
            resolved_or_error,
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
        resolved_or_error = await _resolve_variable_name_for_write(params.variable_name)
        if isinstance(resolved_or_error, ErrorEnvelope):
            return resolved_or_error

        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_scalar_variable,
            app,
            resolved_or_error,
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
        resolved_or_error = await _resolve_variable_name_for_read(params.variable_name)
        if isinstance(resolved_or_error, ErrorEnvelope):
            return resolved_or_error

        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_curve_variable,
            app,
            resolved_or_error,
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
        resolved_or_error = await _resolve_variable_name_for_write(params.variable_name)
        if isinstance(resolved_or_error, ErrorEnvelope):
            return resolved_or_error

        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_curve_variable,
            app,
            resolved_or_error,
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
        resolved_or_error = await _resolve_variable_name_for_read(params.variable_name)
        if isinstance(resolved_or_error, ErrorEnvelope):
            return resolved_or_error

        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_map_variable,
            app,
            resolved_or_error,
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
        resolved_or_error = await _resolve_variable_name_for_write(params.variable_name)
        if isinstance(resolved_or_error, ErrorEnvelope):
            return resolved_or_error

        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_map_variable,
            app,
            resolved_or_error,
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
        return VariableReadArrayElementResult(**_normalize_read_array_element_result(result))
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
        return VariableWriteArrayElementResult(**_normalize_write_array_element_result(result))
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
        resolved_or_error = await _resolve_variable_name_for_read(params.variable_name)
        if isinstance(resolved_or_error, ErrorEnvelope):
            return resolved_or_error

        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.read_string_variable, app, resolved_or_error
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
        resolved_or_error = await _resolve_variable_name_for_write(params.variable_name)
        if isinstance(resolved_or_error, ErrorEnvelope):
            return resolved_or_error

        app = await com_bridge.dispatch(_get_app_lambda())
        result = await com_bridge.dispatch(
            com_bridge.domains.variable_com.write_string_variable,
            app,
            resolved_or_error,
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
        if not is_connection_path(variable_name):
            resolved_or_error = await _resolve_variable_name_for_read(variable_name)
            if isinstance(resolved_or_error, ErrorEnvelope):
                return resolved_or_error
            variable_name = resolved_or_error

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
