"""COM wrappers for ControlDesk variable read/write interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry points:
  - app.ActiveExperiment.Platforms.Item(n).ActiveVariableDescription.Variables
    (IXaVariables)
  - app.ActiveExperiment.Platforms.Item(n).ActiveVariableDescription.DataSets
    (IXaDataSets)
  - app.ActiveExperiment.Platforms.Item(n).VariableDescriptions
    (IXaVariableDescriptions)

Prerequisites for variable read/write tools:
  - Online calibration must be running (calibration_start completed).
  - For write operations: data_set_activate_working_page must be called first.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgeOperationError, BridgePreconditionError

# ── Internal helpers ──────────────────────────────────────────────────────────


def _utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _safe_to_list(com_value: Any) -> list:
    """Convert a COM SAFEARRAY / tuple / single value to a flat Python list."""
    if com_value is None:
        return []
    if isinstance(com_value, (list, tuple)):
        result = list(com_value)
        # Flatten 2D SAFEARRAY (tuple of tuples) e.g. from axis ValueConverted
        if result and isinstance(result[0], (list, tuple)):
            return [item for row in result for item in row]
        return result
    try:
        result = list(com_value)
        if result and isinstance(result[0], (list, tuple)):
            return [item for row in result for item in row]
        return result
    except TypeError:
        return [com_value]


def _require_active_experiment(app: Any) -> Any:
    """Return app.ActiveExperiment or raise BridgePreconditionError."""
    try:
        exp = app.ActiveExperiment
    except Exception as exc:
        raise map_com_error(exc, interface="IXaApplication", method="ActiveExperiment") from exc
    if exp is None:
        raise BridgePreconditionError(
            "No active experiment open. Call experiment_activate first.",
            error_code="BRIDGE_NO_EXPERIMENT",
            recovery_hint="Load and activate an experiment before calling variable tools.",
        )
    return exp


def _get_platform(app: Any, platform_name: str) -> Any:
    """Return the IXaExperimentPlatform COM object for *platform_name*."""
    _require_active_experiment(app)
    try:
        return app.ActiveExperiment.Platforms.Item(platform_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Platform '{platform_name}' not found in the active experiment. "
            "Use platform_list to enumerate valid names.",
            error_code="BRIDGE_PLATFORM_NOT_FOUND",
            recovery_hint="Use platform_list to get the current platform names.",
        ) from exc


def _get_active_variables(app: Any) -> Any:
    """Return the IXaVariables collection from the first platform with an
    active variable description.

    Raises BridgePreconditionError if no such platform exists.
    """
    _require_active_experiment(app)
    try:
        platforms = app.ActiveExperiment.Platforms
        count = int(platforms.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatforms", method="Count") from exc

    for i in range(0, count):
        try:
            plat = platforms.Item(i)
            var_desc = plat.ActiveVariableDescription
            if var_desc is not None:
                return var_desc.Variables
        except Exception:  # noqa: BLE001
            continue

    raise BridgePreconditionError(
        "No platform has an active variable description. "
        "Ensure online calibration is running and a variable description is loaded.",
        error_code="BRIDGE_NO_VARIABLE_DESCRIPTION",
        recovery_hint=(
            "Call calibration_start and ensure a variable description is loaded via platform_add_variable_description."
        ),
    )


def _get_active_variable_description(app: Any) -> Any:
    """Return the IXaActiveVariableDescription from the first platform with one."""
    _require_active_experiment(app)
    try:
        platforms = app.ActiveExperiment.Platforms
        count = int(platforms.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatforms", method="Count") from exc

    for i in range(0, count):
        try:
            plat = platforms.Item(i)
            var_desc = plat.ActiveVariableDescription
            if var_desc is not None:
                return var_desc, str(plat.Name)
        except Exception:  # noqa: BLE001
            continue

    raise BridgePreconditionError(
        "No platform has an active variable description.",
        error_code="BRIDGE_NO_VARIABLE_DESCRIPTION",
        recovery_hint=("Ensure calibration_start has been called and a variable description is loaded."),
    )


def _lookup_variable(variables: Any, identifier: str, search_mode: str | None) -> Any:
    """Look up a variable by name or path.

    Uses variables.Item(identifier) for name search and
    variables.ItemByPath(identifier) for path search.
    """
    if search_mode is None:
        search_mode = "path" if "://" in identifier else "name"

    if search_mode == "path":
        try:
            return variables.ItemByPath(identifier)
        except Exception as exc:
            raise BridgePreconditionError(
                f"Variable with path '{identifier}' not found in the active variable "
                "description. Verify the path format is correct "
                "(e.g., 'XCP()://VariableName').",
                error_code="BRIDGE_VARIABLE_NOT_FOUND",
                recovery_hint="Use variable_list_all or variable_find to discover valid paths.",
            ) from exc
    else:
        try:
            return variables.Item(identifier)
        except Exception as exc:
            raise BridgePreconditionError(
                f"Variable '{identifier}' not found in the active variable description. "
                "Variable names are case-sensitive.",
                error_code="BRIDGE_VARIABLE_NOT_FOUND",
                recovery_hint="Use variable_list_all to discover available variable names.",
            ) from exc


def _variable_type_str(var: Any) -> str:
    """Return the type string for a variable COM object."""
    try:
        return str(var.Type)
    except Exception:  # noqa: BLE001
        return "Unknown"


def _variable_metadata(var: Any) -> dict[str, Any]:
    """Build the full metadata dict for a variable COM object."""
    meta: dict[str, Any] = {"variable_type": _variable_type_str(var)}

    # Identifier
    identifier: dict[str, Any] = {}
    try:
        ident = var.Identifier
        try:
            identifier["unique_name"] = str(ident.UniqueName)
        except Exception:  # noqa: BLE001
            pass
        try:
            identifier["path"] = str(ident.Path)
        except Exception:  # noqa: BLE001
            pass
        try:
            identifier["connection_path"] = str(ident.ConnectionPath)
        except Exception:  # noqa: BLE001
            pass
        try:
            identifier["uri"] = str(ident.URI)
        except Exception:  # noqa: BLE001
            pass
        try:
            identifier["platform_name"] = str(ident.Platform.Name)
        except Exception:  # noqa: BLE001
            pass
        try:
            identifier["raster_name"] = str(ident.RasterName)
        except Exception:  # noqa: BLE001
            pass
    except Exception:  # noqa: BLE001
        pass
    meta["identifier"] = identifier

    # Name (top-level convenience field)
    meta["name"] = identifier.get("unique_name", "")

    # Readability / writability
    try:
        meta["is_readable"] = bool(var.IsReadable)
    except Exception:  # noqa: BLE001
        meta["is_readable"] = True
    try:
        meta["is_writable"] = bool(var.IsWritable)
    except Exception:  # noqa: BLE001
        meta["is_writable"] = False
    try:
        meta["is_changeable_only_during_initialization"] = bool(var.IsChangeableOnlyDuringInitialization)
    except Exception:  # noqa: BLE001
        meta["is_changeable_only_during_initialization"] = False

    # Limits
    try:
        meta["hard_limits"] = {
            "min": float(var.HardLimits.Minimum),
            "max": float(var.HardLimits.Maximum),
        }
    except Exception:  # noqa: BLE001
        pass
    try:
        meta["weak_limits"] = {
            "min": float(var.WeakLimits.Minimum),
            "max": float(var.WeakLimits.Maximum),
        }
    except Exception:  # noqa: BLE001
        pass

    # Unit
    try:
        meta["unit"] = str(var.Unit)
    except Exception:  # noqa: BLE001
        meta["unit"] = ""

    # Description
    try:
        meta["description"] = str(var.Description)
    except Exception:  # noqa: BLE001
        meta["description"] = ""

    return meta


# ── Tool 1 — find_variable ────────────────────────────────────────────────────


def find_variable(app: Any, identifier: str, search_mode: str | None = None) -> dict[str, Any]:
    """Find a variable by name or path and return full metadata."""
    variables = _get_active_variables(app)
    try:
        var = _lookup_variable(variables, identifier, search_mode)
    except BridgePreconditionError:
        return {"found": False}
    meta = _variable_metadata(var)
    meta["found"] = True
    return meta


# ── Tool 2 — list_all_variables ───────────────────────────────────────────────


def list_all_variables(app: Any) -> dict[str, Any]:
    """Enumerate all variables grouped by type."""
    variables = _get_active_variables(app)
    try:
        count = int(variables.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaVariables", method="Count") from exc

    by_type: dict[str, list[dict[str, Any]]] = {}
    for i in range(0, count):
        try:
            var = variables.Item(i)
            var_type = _variable_type_str(var)
            entry: dict[str, Any] = {}
            try:
                entry["name"] = str(var.Identifier.UniqueName)
            except Exception:  # noqa: BLE001
                entry["name"] = f"[{i}]"
            try:
                entry["is_readable"] = bool(var.IsReadable)
            except Exception:  # noqa: BLE001
                entry["is_readable"] = True
            try:
                entry["is_writable"] = bool(var.IsWritable)
            except Exception:  # noqa: BLE001
                entry["is_writable"] = False
            try:
                entry["unit"] = str(var.Unit)
            except Exception:  # noqa: BLE001
                entry["unit"] = ""
            try:
                entry["connection_path"] = str(var.Identifier.Path)
            except Exception:  # noqa: BLE001
                entry["connection_path"] = ""
            by_type.setdefault(var_type, []).append(entry)
        except Exception:  # noqa: BLE001
            continue

    return {"total_count": count, "by_type": by_type}


# ── Tool 3 — get_variable_info (alias to find_variable) ──────────────────────


def get_variable_info(app: Any, variable_name: str) -> dict[str, Any]:
    """Return full metadata for a named variable (alias to find_variable)."""
    return find_variable(app, variable_name)


# ── Tool 4 — read_scalar_variable ─────────────────────────────────────────────


def read_scalar_variable(app: Any, variable_name: str, value_format: str = "Converted") -> dict[str, Any]:
    """Read the current value of a scalar variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        if value_format == "Source":
            raw_value = var.ValueSource
        else:
            raw_value = var.ValueConverted

        # Convert to a JSON-serialisable scalar
        try:
            value = float(raw_value)
            if value.is_integer():
                value = int(value)
        except (TypeError, ValueError):
            value = raw_value

        unit = ""
        try:
            unit = str(var.Unit)
        except Exception:  # noqa: BLE001
            pass

        return {
            "variable_name": variable_name,
            "variable_type": _variable_type_str(var),
            "value": value,
            "value_format": value_format,
            "unit": unit if value_format != "Source" else "raw",
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaParameterVariable", method="ValueConverted") from exc


# ── Tool 5 — write_scalar_variable ────────────────────────────────────────────


def write_scalar_variable(
    app: Any,
    variable_name: str,
    value: float | int | str,
    value_format: str = "Converted",
) -> dict[str, Any]:
    """Write a new value to a scalar parameter variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        if value_format == "Source":
            var.ValueSource = value
        else:
            var.ValueConverted = value

        unit = ""
        try:
            unit = str(var.Unit)
        except Exception:  # noqa: BLE001
            pass

        return {
            "written": True,
            "variable_name": variable_name,
            "variable_type": _variable_type_str(var),
            "value_written": value,
            "value_format": value_format,
            "unit": unit if value_format != "Source" else "raw",
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaParameterVariable", method="ValueConverted(set)") from exc


# ── Tool 6 — read_curve_variable ──────────────────────────────────────────────


def read_curve_variable(app: Any, variable_name: str, value_format: str = "Converted") -> dict[str, Any]:
    """Read axis and function values from a 1-D curve variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        axis = var.Axis
        func_vals = var.FunctionValues

        if value_format == "Source":
            axis_values = _safe_to_list(axis.ValueSource)
            func_values = _safe_to_list(func_vals.ValueSource)
        else:
            axis_values = _safe_to_list(axis.ValueConverted)
            func_values = _safe_to_list(func_vals.ValueConverted)

        axis_unit = ""
        func_unit = ""
        try:
            axis_unit = str(axis.Unit)
        except Exception:  # noqa: BLE001
            pass
        try:
            func_unit = str(func_vals.Unit)
        except Exception:  # noqa: BLE001
            pass

        return {
            "variable_name": variable_name,
            "variable_type": "Curve",
            "axis": {
                "size": len(axis_values),
                "values": [float(v) for v in axis_values],
                "unit": axis_unit,
            },
            "function_values": {
                "size": len(func_values),
                "values": [float(v) for v in func_values],
                "unit": func_unit,
            },
            "value_format": value_format,
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaCurveVariable", method="Axis") from exc


# ── Tool 7 — write_curve_variable ─────────────────────────────────────────────


def write_curve_variable(
    app: Any,
    variable_name: str,
    function_values: list,
    axis_values: list | None = None,
    value_format: str = "Converted",
) -> dict[str, Any]:
    """Write function values (and optionally axis) to a 1-D curve variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        func_vals = var.FunctionValues
        axis_written = 0

        if value_format == "Source":
            func_vals.ValueSource = tuple(function_values)
            if axis_values is not None:
                var.Axis.ValueSource = tuple(axis_values)
                axis_written = len(axis_values)
        else:
            func_vals.ValueConverted = tuple(function_values)
            if axis_values is not None:
                var.Axis.ValueConverted = tuple(axis_values)
                axis_written = len(axis_values)

        return {
            "written": True,
            "variable_name": variable_name,
            "variable_type": "Curve",
            "function_values_written": len(function_values),
            "axis_values_written": axis_written,
            "value_format": value_format,
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaCurveVariable", method="FunctionValues.ValueConverted(set)") from exc


# ── Tool 8 — read_map_variable ────────────────────────────────────────────────


def read_map_variable(app: Any, variable_name: str, value_format: str = "Converted") -> dict[str, Any]:
    """Read X axis, Y axis, and 2-D function matrix from a map variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        x_axis = var.XAxis
        y_axis = var.YAxis
        func_vals = var.FunctionValues

        if value_format == "Source":
            x_values = _safe_to_list(x_axis.ValueSource)
            y_values = _safe_to_list(y_axis.ValueSource)
            raw_2d = func_vals.ValueSource
        else:
            x_values = _safe_to_list(x_axis.ValueConverted)
            y_values = _safe_to_list(y_axis.ValueConverted)
            raw_2d = func_vals.ValueConverted

        cols = len(x_values)  # x_count
        rows = len(y_values)  # y_count

        # COM stores FunctionValues as [x_count][y_count] (x-major).
        # Convert to user-friendly [y_count][x_count] (y-major) by transposing.
        matrix: list[list[float]] = []
        if cols > 0 and rows > 0 and raw_2d:
            for y in range(rows):
                matrix.append([float(raw_2d[x][y]) for x in range(cols)])
        else:
            flat_values = _safe_to_list(raw_2d)
            matrix = [[float(v) for v in flat_values]]

        x_unit = ""
        y_unit = ""
        func_unit = ""
        try:
            x_unit = str(x_axis.Unit)
        except Exception:  # noqa: BLE001
            pass
        try:
            y_unit = str(y_axis.Unit)
        except Exception:  # noqa: BLE001
            pass
        try:
            func_unit = str(func_vals.Unit)
        except Exception:  # noqa: BLE001
            pass

        return {
            "variable_name": variable_name,
            "variable_type": "Map",
            "x_axis": {
                "size": cols,
                "values": [float(v) for v in x_values],
                "unit": x_unit,
            },
            "y_axis": {
                "size": rows,
                "values": [float(v) for v in y_values],
                "unit": y_unit,
            },
            "function_values": {
                "rows": rows,
                "cols": cols,
                "values": matrix,
                "unit": func_unit,
            },
            "value_format": value_format,
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMapVariable", method="XAxis") from exc


# ── Tool 9 — write_map_variable ───────────────────────────────────────────────


def write_map_variable(
    app: Any,
    variable_name: str,
    function_values: list[list],
    x_axis_values: list | None = None,
    y_axis_values: list | None = None,
    value_format: str = "Converted",
) -> dict[str, Any]:
    """Write function matrix (and optionally axes) to a 2-D map variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        func_vals = var.FunctionValues

        # User provides function_values in y-major [y_count][x_count] format.
        # COM FunctionValues.ValueConverted expects x-major [x_count][y_count].
        # Must transpose: nested[x][y] = function_values[y][x].
        rows = len(function_values)  # y_count
        cols = len(function_values[0]) if function_values else 0  # x_count
        nested = [[float(function_values[y][x]) for y in range(rows)] for x in range(cols)]

        x_axis_written = False
        y_axis_written = False

        if value_format == "Source":
            # Write axes first (axes must be monotonic before function values)
            if x_axis_values is not None:
                var.XAxis.ValueSource = tuple(x_axis_values)
                x_axis_written = True
            if y_axis_values is not None:
                var.YAxis.ValueSource = tuple(y_axis_values)
                y_axis_written = True
            func_vals.ValueSource = nested
        else:
            # Write axes first (axes must be monotonic before function values)
            if x_axis_values is not None:
                var.XAxis.ValueConverted = tuple(x_axis_values)
                x_axis_written = True
            if y_axis_values is not None:
                var.YAxis.ValueConverted = tuple(y_axis_values)
                y_axis_written = True
            func_vals.ValueConverted = nested

        return {
            "written": True,
            "variable_name": variable_name,
            "variable_type": "Map",
            "function_values_written": [rows, cols],
            "x_axis_written": x_axis_written,
            "y_axis_written": y_axis_written,
            "value_format": value_format,
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMapVariable", method="FunctionValues.ValueConverted(set)") from exc


# ── Tool 10 — list_array_elements ─────────────────────────────────────────────


def list_array_elements(app: Any, variable_name: str) -> dict[str, Any]:
    """List all sub-elements of an array variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        sub_elements = var.SubElements
        count = int(sub_elements.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaMeasurementArrayVariable", method="SubElements") from exc

    elements = []
    for i in range(0, count):
        try:
            elem = sub_elements.Item(i)
            entry: dict[str, Any] = {"index": i}
            try:
                entry["path"] = str(elem.Identifier.Path)
            except Exception:  # noqa: BLE001
                entry["path"] = ""
            try:
                entry["type"] = _variable_type_str(elem)
            except Exception:  # noqa: BLE001
                entry["type"] = "Unknown"
            try:
                entry["is_readable"] = bool(elem.IsReadable)
            except Exception:  # noqa: BLE001
                entry["is_readable"] = True
            try:
                entry["is_writable"] = bool(elem.IsWritable)
            except Exception:  # noqa: BLE001
                entry["is_writable"] = False
            try:
                entry["unit"] = str(elem.Unit)
            except Exception:  # noqa: BLE001
                entry["unit"] = ""
            elements.append(entry)
        except Exception:  # noqa: BLE001
            continue

    return {
        "variable_name": variable_name,
        "variable_type": _variable_type_str(var),
        "total_elements": count,
        "elements": elements,
    }


# ── Tool 11 — read_array_element ──────────────────────────────────────────────


def read_array_element(app: Any, element_path: str, value_format: str = "Converted") -> dict[str, Any]:
    """Read the value of a specific array element by its path."""
    variables = _get_active_variables(app)
    # Array elements are accessed via ItemByPath
    elem = _lookup_variable(variables, element_path, "path")
    try:
        if value_format == "Source":
            raw_value = elem.ValueSource
        else:
            raw_value = elem.ValueConverted

        try:
            value = float(raw_value)
            if value.is_integer():
                value = int(value)
        except (TypeError, ValueError):
            value = raw_value

        unit = ""
        try:
            unit = str(elem.Unit)
        except Exception:  # noqa: BLE001
            pass

        # Extract index from path (e.g., "XCP()://ParamVector[3]" → 3)
        index = None
        try:
            import re  # noqa: PLC0415

            m = re.search(r"\[(\d+)\]$", element_path)
            if m:
                index = int(m.group(1))
        except Exception:  # noqa: BLE001
            pass

        return {
            "element_path": element_path,
            "variable_type": _variable_type_str(elem),
            "index": index,
            "value": value,
            "value_format": value_format,
            "unit": unit if value_format != "Source" else "raw",
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaVariableBase", method="ValueConverted") from exc


# ── Tool 12 — write_array_element ─────────────────────────────────────────────


def write_array_element(
    app: Any,
    element_path: str,
    value: float | int | str,
    value_format: str = "Converted",
) -> dict[str, Any]:
    """Write a new value to a specific array element by its path."""
    variables = _get_active_variables(app)
    elem = _lookup_variable(variables, element_path, "path")
    try:
        if value_format == "Source":
            elem.ValueSource = value
        else:
            elem.ValueConverted = value

        unit = ""
        try:
            unit = str(elem.Unit)
        except Exception:  # noqa: BLE001
            pass

        import re  # noqa: PLC0415

        index = None
        try:
            m = re.search(r"\[(\d+)\]$", element_path)
            if m:
                index = int(m.group(1))
        except Exception:  # noqa: BLE001
            pass

        return {
            "written": True,
            "element_path": element_path,
            "variable_type": _variable_type_str(elem),
            "index": index,
            "value_written": value,
            "value_format": value_format,
            "unit": unit if value_format != "Source" else "raw",
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaVariableBase", method="ValueConverted(set)") from exc


# ── Tool 13 — list_group_variables ────────────────────────────────────────────


def list_group_variables(app: Any, group_path: str = "") -> dict[str, Any]:
    """List all variables in a group within the variable hierarchy."""
    var_desc, _ = _get_active_variable_description(app)
    try:
        root_group = var_desc.RootGroup
    except Exception as exc:
        raise map_com_error(exc, interface="IXaActiveVariableDescription", method="RootGroup") from exc

    # Navigate to the requested group
    group = root_group
    if group_path:
        parts = group_path.strip("/").split("/")
        for part in parts:
            try:
                group = group.Groups.Item(part)
            except Exception as exc:
                raise BridgePreconditionError(
                    f"Group '{group_path}' not found. Use variable_list_all to discover available groups.",
                    error_code="BRIDGE_GROUP_NOT_FOUND",
                    recovery_hint="Check the group path spelling (case-sensitive).",
                ) from exc

    # Enumerate sub-groups (0-based)
    sub_groups: list[str] = []
    try:
        sg_coll = group.Groups
        sg_count = int(sg_coll.Count)
        for i in range(0, sg_count):
            try:
                sg = sg_coll.Item(i)
                sub_groups.append(str(sg.Name))
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass

    # Enumerate variables in the group (0-based)
    var_entries: list[dict[str, Any]] = []
    try:
        var_coll = group.Variables
        var_count = int(var_coll.Count)
        for i in range(0, var_count):
            try:
                var = var_coll.Item(i)
                entry: dict[str, Any] = {}
                try:
                    entry["name"] = str(var.Identifier.UniqueName)
                except Exception:  # noqa: BLE001
                    entry["name"] = f"[{i}]"
                try:
                    entry["type"] = _variable_type_str(var)
                except Exception:  # noqa: BLE001
                    entry["type"] = "Unknown"
                try:
                    entry["is_readable"] = bool(var.IsReadable)
                except Exception:  # noqa: BLE001
                    entry["is_readable"] = True
                try:
                    entry["is_writable"] = bool(var.IsWritable)
                except Exception:  # noqa: BLE001
                    entry["is_writable"] = False
                try:
                    entry["unit"] = str(var.Unit)
                except Exception:  # noqa: BLE001
                    entry["unit"] = ""
                var_entries.append(entry)
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass

    return {
        "group_path": group_path or "",
        "total_count": len(var_entries),
        "sub_groups": sub_groups,
        "variables": var_entries,
    }


# ── Tool 14 — activate_working_page ──────────────────────────────────────────


def activate_working_page(app: Any) -> dict[str, Any]:
    """Activate the working (RAM) data set."""
    var_desc, platform_name = _get_active_variable_description(app)
    try:
        var_desc.DataSets.WorkingDataSet.Activate()
        return {
            "activated": True,
            "data_set": "WorkingDataSet",
            "platform_name": platform_name,
            "timestamp_utc": _utc_now(),
        }
    except Exception as exc:
        raise map_com_error(
            exc, interface="IXaActiveVariableDescription", method="DataSets.WorkingDataSet.Activate"
        ) from exc


# ── Tool 15 — activate_reference_page ────────────────────────────────────────


def activate_reference_page(app: Any) -> dict[str, Any]:
    """Activate the reference (flash) data set."""
    var_desc, platform_name = _get_active_variable_description(app)
    try:
        var_desc.DataSets.ReferenceDataSet.Activate()
        return {
            "activated": True,
            "data_set": "ReferenceDataSet",
            "platform_name": platform_name,
            "timestamp_utc": _utc_now(),
        }
    except Exception as exc:
        raise map_com_error(
            exc,
            interface="IXaActiveVariableDescription",
            method="DataSets.ReferenceDataSet.Activate",
        ) from exc


# ── Tool 16 — list_variable_descriptions ─────────────────────────────────────


def list_variable_descriptions(app: Any, platform_name: str) -> dict[str, Any]:
    """List all variable descriptions loaded in the named platform."""
    plat = _get_platform(app, platform_name)
    try:
        var_descs = plat.VariableDescriptions
        count = int(var_descs.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IXaExperimentPlatform", method="VariableDescriptions") from exc

    def _build_entry(vd: Any, fallback_name: str) -> dict[str, Any]:
        entry: dict[str, Any] = {}
        try:
            entry["name"] = str(vd.Name)
        except Exception:  # noqa: BLE001
            entry["name"] = fallback_name
        try:
            entry["is_active"] = bool(vd.Active)
        except Exception:  # noqa: BLE001
            entry["is_active"] = False
        try:
            entry["a2l_path"] = str(vd.FullName)
        except Exception:  # noqa: BLE001
            entry["a2l_path"] = ""
        entry["mot_path"] = ""
        return entry

    descriptions = []
    # Try direct COM iteration first (works for any collection with _NewEnum).
    try:
        for vd in var_descs:
            descriptions.append(_build_entry(vd, f"[{len(descriptions)}]"))
    except Exception:  # noqa: BLE001
        descriptions = []

    # Fall back to integer indexing if iteration produced no results.
    if not descriptions:
        for i in range(1, count + 1):
            try:
                vd = var_descs.Item(i)
                descriptions.append(_build_entry(vd, f"[{i}]"))
            except Exception:  # noqa: BLE001
                # Try 0-based index for COM collections that start at 0.
                try:
                    vd = var_descs.Item(i - 1)
                    descriptions.append(_build_entry(vd, f"[{i - 1}]"))
                except Exception:  # noqa: BLE001
                    continue

    return {
        "platform_name": platform_name,
        "total_count": count,
        "variable_descriptions": descriptions,
    }


# ── Tool 17 — activate_variable_description ───────────────────────────────────


def activate_variable_description(app: Any, platform_name: str, description_name: str) -> dict[str, Any]:
    """Activate a named variable description on a platform."""
    plat = _get_platform(app, platform_name)
    try:
        vd = plat.VariableDescriptions.Item(description_name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Variable description '{description_name}' not found on platform '{platform_name}'. "
            "Use variable_description_list to enumerate loaded descriptions.",
            error_code="BRIDGE_VARIABLE_DESCRIPTION_NOT_FOUND",
            recovery_hint="Load the description via platform_add_variable_description first.",
        ) from exc
    try:
        vd.Activate()
        return {
            "activated": True,
            "platform_name": platform_name,
            "description_name": description_name,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IXaVariableDescription", method="Activate") from exc


# ── Tool 18 — remove_variable_description ─────────────────────────────────────


def remove_variable_description(app: Any, platform_name: str, description_name: str) -> dict[str, Any]:
    """Remove a named variable description from a platform."""
    plat = _get_platform(app, platform_name)
    var_descs = plat.VariableDescriptions
    try:
        exists = bool(var_descs.Contains(description_name))
    except Exception:  # noqa: BLE001
        exists = False
    if not exists:
        raise BridgePreconditionError(
            f"Variable description '{description_name}' not found on platform '{platform_name}'.",
            error_code="BRIDGE_VARIABLE_DESCRIPTION_NOT_FOUND",
            recovery_hint="Use variable_description_list to enumerate loaded descriptions.",
        )
    try:
        vd = var_descs.Item(description_name)
        vd.Remove()
        return {
            "removed": True,
            "platform_name": platform_name,
            "description_name": description_name,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IXaVariableDescription", method="Remove") from exc


# ── Tool 19 — read_string_variable ────────────────────────────────────────────


def read_string_variable(app: Any, variable_name: str) -> dict[str, Any]:
    """Read the current string value from a string-type variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        value = str(var.Value)
        max_length = None
        try:
            max_length = int(var.MaxLength)
        except Exception:  # noqa: BLE001
            pass

        result: dict[str, Any] = {
            "variable_name": variable_name,
            "variable_type": "String",
            "value": value,
            "timestamp_utc": _utc_now(),
        }
        if max_length is not None:
            result["max_length"] = max_length
        return result
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaStringVariable", method="Value") from exc


# ── Tool 20 — write_string_variable ───────────────────────────────────────────


def write_string_variable(app: Any, variable_name: str, value: str) -> dict[str, Any]:
    """Write a new string value to a string-type variable."""
    variables = _get_active_variables(app)
    var = _lookup_variable(variables, variable_name, None)
    try:
        var.Value = value
        return {
            "written": True,
            "variable_name": variable_name,
            "variable_type": "String",
            "value_written": value,
            "timestamp_utc": _utc_now(),
        }
    except (BridgeOperationError, BridgePreconditionError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IXaStringVariable", method="Value(set)") from exc
