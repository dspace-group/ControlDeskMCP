"""COM wrappers for ControlDesk layout instrument management interfaces.

All functions must be called on the STA thread via com_bridge.dispatch().

COM entry point:
  app.LayoutManagement.ActiveLayout.Instruments   (IViTopLevelInstruments)

IViTopLevelInstruments methods used:
  .Count                  → int
  .Item(name)             → IViInstrumentRoot
  .Add(type, name, x, y, w, h) → IViInstrumentRoot

IViInstrumentRoot properties / methods used:
  .Name                   → str  (read-only)
  .TypeString             → str  (instrument type string, read-only)
  .Position.X             → int  (read/write)
  .Position.Y             → int  (read/write)
  .Position.Width         → int  (read/write)
  .Position.Height        → int  (read/write)
  .MainVariable           → str  (read/write — for simple instruments)
  .Caption                → str  (read/write)
  .BackColor              → int  (read/write — RGB integer)
  .ForeColor              → int  (read/write — RGB integer)
  .ShowBorder             → bool (read/write)
  .Remove()               → void
  .SelectMulti()          → void (add to multi-selection)

IViPlotter2Instrument (Time Plotter, XY Plotter) extension:
  .ActivePlot.YAxes.Add()                → IViYAxis
  .ActivePlot.YAxes.Item(i).Signals.Add() → IViSignal
  signal.MainVariable = path

IViVariableArrayInstrument (variable Array) extension:
  .Rows.Add()                            → IViRow
  row.MainVariable = path

IViTableEditorInstrument (Table Editor) extension:
  .SubInstruments.Add()                  → void
  .ActiveSubInstrument.MainVariable = path

IViTopLevelSelection (via layout.Selection):
  .AlignTop(), .AlignBottom(), .AlignLeft(), .AlignRight()
  .CenterInViewHorizontally(), .CenterInViewVertically()
  .SpaceEvenlyAcross(), .SpaceEvenlyDown()
  .Group()    → IViGroupInstrument
  .Ungroup()  → void  (called on the group instrument itself)

Signal mode resolution (by instrument type string):
  "Time Plotter", "XY Plotter"  → plotter_signal
  "variable Array"              → array_row
  "Table Editor"                → sub_instrument
  all others                    → main_variable
"""

from __future__ import annotations

from typing import Any

from controldesk_mcp.com_bridge.error_handling.hresult import map_com_error
from controldesk_mcp.com_bridge.errors import BridgeOperationError, BridgePreconditionError

# ── Plotter signal COM interface helper ───────────────────────────────────────
# Some signal auto-dispatch classes do not expose MainVariable directly.
# Use IDispatch name lookup as a GUID-free fallback to read the property.
_UNRESOLVED_VARIABLE_PATH_SENTINEL = "<unresolved>"


def _get_main_variable(signal_obj: Any) -> Any:
    """Read MainVariable from a signal object, with IDispatch fallback."""
    try:
        return signal_obj.MainVariable
    except Exception:
        pass

    try:
        import pythoncom  # noqa: PLC0415

        dispid = signal_obj._oleobj_.GetIDsOfNames("MainVariable")
        return signal_obj._oleobj_.Invoke(dispid, 0, pythoncom.INVOKE_PROPERTYGET, 1)
    except Exception:
        return None


def _safe_str(value: Any) -> str | None:
    try:
        text = str(value).strip()
        return text or None
    except Exception:
        return None


def _is_opaque_com_string(value: str | None) -> bool:
    if not value:
        return False
    lowered = value.lower()
    return "<comobject" in lowered and "<unknown>" in lowered


def _extract_variable_path(main_variable: Any) -> tuple[str | None, str | None, str | None]:
    """Extract a variable path from a COM MainVariable object.

    Returns (path, source, unavailable_reason).
    """
    if main_variable is None:
        return None, None, None

    raw_text = _safe_str(main_variable)
    if raw_text and not _is_opaque_com_string(raw_text):
        return raw_text, "main_variable", None

    try:
        path = _safe_str(main_variable.Path)
        if path and not _is_opaque_com_string(path):
            return path, "main_variable.path", None
    except Exception:
        pass

    try:
        path = _safe_str(main_variable.Connection.Variable.Path)
        if path and not _is_opaque_com_string(path):
            return path, "connection.variable.path", None
    except Exception:
        pass

    if raw_text and _is_opaque_com_string(raw_text):
        return None, None, "opaque_main_variable"
    return None, None, "path_not_available"


def _build_signal_connection_entry(
    *,
    main_variable: Any,
    axis_index: int | None,
    signal_index: int | None,
    color: str | None,
) -> dict[str, Any] | None:
    path, source, unavailable_reason = _extract_variable_path(main_variable)
    if path:
        return {
            "axis_index": axis_index,
            "signal_index": signal_index,
            "variable_path": path,
            "color": color,
            "variable_path_source": source,
        }

    if unavailable_reason:
        return {
            "axis_index": axis_index,
            "signal_index": signal_index,
            "variable_path": _UNRESOLVED_VARIABLE_PATH_SENTINEL,
            "color": color,
            "variable_path_unavailable_reason": unavailable_reason,
        }
    return None


def _get_type_string(instr: Any) -> str:
    """Return instrument type string, trying TypeString then TypeName as fallback."""
    for attr in ("TypeString", "TypeName"):
        try:
            val = getattr(instr, attr, None)
            if val is not None:
                return str(val)
        except Exception:
            pass
    return "Unknown"


# ── Hardcoded instrument type catalogue ───────────────────────────────────────
# Returned by instrument_list_types; avoids COM library query when not needed.

_INSTRUMENT_TYPE_CATALOG: list[dict[str, Any]] = [
    {"type_string": "3-D Viewer", "category": "Data Displays", "signal_mode": "main_variable"},
    {
        "type_string": "AirspeedIndicator",
        "category": "Data Displays",
        "signal_mode": "main_variable",
    },
    {"type_string": "Altimeter", "category": "Data Displays", "signal_mode": "main_variable"},
    {
        "type_string": "ArtificialHorizon",
        "category": "Data Displays",
        "signal_mode": "main_variable",
    },
    {"type_string": "Diagnostics Instrument", "category": "Utility", "signal_mode": None},
    {"type_string": "Fault Memory Instrument", "category": "Utility", "signal_mode": None},
    {"type_string": "Index Plotter", "category": "Data Displays", "signal_mode": "plotter_signal"},
    {"type_string": "MultiSwitch", "category": "Utility", "signal_mode": None},
    {"type_string": "Time Plotter", "category": "Data Displays", "signal_mode": "plotter_signal"},
    {"type_string": "XY Plotter", "category": "Data Displays", "signal_mode": "plotter_signal"},
    {"type_string": "Knob", "category": "Controls", "signal_mode": "main_variable"},
    {"type_string": "Slider", "category": "Controls", "signal_mode": "main_variable"},
    {"type_string": "Display", "category": "Data Displays", "signal_mode": "main_variable"},
    {"type_string": "Gauge", "category": "Data Displays", "signal_mode": "main_variable"},
    {"type_string": "Bar", "category": "Data Displays", "signal_mode": "main_variable"},
    {"type_string": "Animated Needle", "category": "Data Displays", "signal_mode": "main_variable"},
    {
        "type_string": "Multistate Display",
        "category": "Data Displays",
        "signal_mode": "main_variable",
    },
    {"type_string": "OnOff Button", "category": "Controls", "signal_mode": "main_variable"},
    {"type_string": "Push Button", "category": "Controls", "signal_mode": "main_variable"},
    {"type_string": "Numeric Input", "category": "Controls", "signal_mode": "main_variable"},
    {"type_string": "Check Button", "category": "Controls", "signal_mode": "main_variable"},
    {"type_string": "Radio Button", "category": "Controls", "signal_mode": "main_variable"},
    {"type_string": "Selectionbox", "category": "Controls", "signal_mode": "main_variable"},
    {"type_string": "variable Array", "category": "Data Displays", "signal_mode": "array_row"},
    {"type_string": "Table Editor", "category": "Calibration", "signal_mode": "sub_instrument"},
    {"type_string": "Frame", "category": "Decorations", "signal_mode": None},
    {"type_string": "Static Text", "category": "Decorations", "signal_mode": None},
    {"type_string": "Browser", "category": "Utility", "signal_mode": None},
    {"type_string": "SteeringController", "category": "Controls", "signal_mode": "main_variable"},
]

# Instrument types that use plotter signal connection mode
_PLOTTER_TYPES = {"Index Plotter", "Time Plotter", "XY Plotter"}
# Instrument types that use array row connection mode
_ARRAY_TYPES = {"variable Array"}
# Instrument types that use sub-instrument connection mode
_SUBINSTRUMENT_TYPES = {"Table Editor"}


def _resolve_signal_mode(type_string: str) -> str:
    """Return the signal connection mode string for the given instrument type."""
    if type_string in _PLOTTER_TYPES:
        return "plotter_signal"
    if type_string in _ARRAY_TYPES:
        return "array_row"
    if type_string in _SUBINSTRUMENT_TYPES:
        return "sub_instrument"
    return "main_variable"


def _hex_to_rgb_int(hex_color: str) -> int:
    """Convert '#RRGGBB' hex string to a BGR integer (as used by Windows COM color)."""
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    # COM BackColor / ForeColor uses OLE color: 0x00BBGGRR
    return (b << 16) | (g << 8) | r


# ── Precondition guards ───────────────────────────────────────────────────────


def _get_active_layout(app: Any) -> Any:
    """Return the active layout document; raises BridgePreconditionError if none open."""
    try:
        mgmt = app.LayoutManagement
        active = mgmt.ActiveLayout
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayoutManagement", method="ActiveLayout") from exc
    if active is None:
        raise BridgePreconditionError(
            "No active layout open. Call layout_open or layout_create + layout_open first.",
            error_code="BRIDGE_NO_ACTIVE_LAYOUT",
            recovery_hint="Open and activate a layout before managing instruments.",
        )
    return active


def _get_instruments(app: Any) -> Any:
    """Return the IViTopLevelInstruments collection from the active layout."""
    active = _get_active_layout(app)
    try:
        return active.Instruments
    except Exception as exc:
        raise map_com_error(exc, interface="IXaLayoutDocument", method="Instruments") from exc


def _get_instrument_item(instruments: Any, name: str) -> Any:
    """Return the IViInstrumentRoot for *name*; raises BridgePreconditionError if not found."""
    try:
        return instruments.Item(name)
    except Exception as exc:
        raise BridgePreconditionError(
            f"Instrument '{name}' does not exist on the active layout. "
            "Call instrument_list to see available instruments.",
            error_code="BRIDGE_INSTRUMENT_NOT_FOUND",
            recovery_hint=(
                "Use instrument_list() to enumerate instruments on the active layout. "
                "Instrument names are case-sensitive."
            ),
        ) from exc


# ── instrument_list ───────────────────────────────────────────────────────────


def instrument_list(app: Any) -> dict[str, Any]:
    """Return layout name and list of instruments on the active layout.

    Each instrument dict has: name, type, x, y, width, height, main_variable.
    """
    active = _get_active_layout(app)
    instruments = _get_instruments(app)

    try:
        layout_name = str(active.Name) if hasattr(active, "Name") else ""
        count = int(instruments.Count)
    except Exception as exc:
        raise map_com_error(exc, interface="IViTopLevelInstruments", method="Count") from exc

    result: list[dict[str, Any]] = []
    for i in range(count):
        try:
            instr = instruments.Item(i)
            name = str(instr.Name)
            type_string = _get_type_string(instr)
            pos = instr.Position
            x = int(pos.X)
            y = int(pos.Y)
            w = int(pos.Width)
            h = int(pos.Height)
            # Only attempt MainVariable for simple instruments
            main_var: str | None = None
            main_var_source: str | None = None
            main_var_unavailable_reason: str | None = None
            signal_mode = _resolve_signal_mode(type_string)
            if signal_mode == "main_variable":
                try:
                    main_var, main_var_source, main_var_unavailable_reason = _extract_variable_path(instr.MainVariable)
                except Exception:
                    pass
            result.append(
                {
                    "name": name,
                    "type": type_string,
                    "x": x,
                    "y": y,
                    "width": w,
                    "height": h,
                    "main_variable": main_var,
                    "main_variable_source": main_var_source,
                    "main_variable_unavailable_reason": main_var_unavailable_reason,
                }
            )
        except Exception as exc:
            raise map_com_error(exc, interface="IViTopLevelInstruments", method="Item") from exc

    return {"layout_name": layout_name, "instruments": result}


# ── instrument_list_types ─────────────────────────────────────────────────────


def instrument_list_types() -> list[dict[str, Any]]:
    """Return the static instrument type catalogue.

    Returns the hardcoded catalog. In future, this could be replaced with a live
    query to app.LayoutManagement.InstrumentLibraries when available.
    """
    return _INSTRUMENT_TYPE_CATALOG


# ── instrument_add ─────────────────────────────────────────────────────────────


def instrument_add(
    app: Any,
    instrument_type: str,
    instrument_name: str,
    x: int,
    y: int,
    width: int,
    height: int,
) -> dict[str, Any]:
    """Add a new instrument to the active layout.

    Returns dict with: instrument_name, instrument_type, x, y, width, height.
    """
    instruments = _get_instruments(app)
    try:
        instruments.Add(instrument_type, instrument_name, x, y, width, height)
        return {
            "instrument_name": instrument_name,
            "instrument_type": instrument_type,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IViTopLevelInstruments", method="Add") from exc


# ── instrument_remove ──────────────────────────────────────────────────────────


def instrument_remove(app: Any, instrument_name: str) -> dict[str, Any]:
    """Remove an instrument from the active layout by name.

    Returns dict with: instrument_name.
    """
    instruments = _get_instruments(app)
    instr = _get_instrument_item(instruments, instrument_name)
    try:
        instr.Delete()
        return {"instrument_name": instrument_name}
    except Exception as exc:
        raise map_com_error(exc, interface="IViInstrumentRoot", method="Delete") from exc


# ── instrument_get_info ────────────────────────────────────────────────────────


def instrument_get_info(app: Any, instrument_name: str) -> dict[str, Any]:
    """Return detailed metadata about an instrument including signal connections.

    Returns dict with: instrument_name, instrument_type, x, y, width, height,
    signal_connections (list).
    """
    instruments = _get_instruments(app)
    instr = _get_instrument_item(instruments, instrument_name)

    try:
        type_string = _get_type_string(instr)
        pos = instr.Position
        x = int(pos.X)
        y = int(pos.Y)
        w = int(pos.Width)
        h = int(pos.Height)
    except Exception as exc:
        raise map_com_error(exc, interface="IViInstrumentRoot", method="properties") from exc

    signal_mode = _resolve_signal_mode(type_string)
    connections: list[dict[str, Any]] = []

    try:
        if signal_mode == "main_variable":
            entry = _build_signal_connection_entry(
                main_variable=instr.MainVariable,
                axis_index=None,
                signal_index=None,
                color=None,
            )
            if entry:
                connections.append(entry)
        elif signal_mode == "plotter_signal":
            plot = instr.ActivePlot
            y_axes = plot.YAxes
            for ai in range(int(y_axes.Count)):
                axis = y_axes.Item(ai)
                sigs = axis.Signals
                for si in range(int(sigs.Count)):
                    sig = sigs.Item(si)
                    entry = _build_signal_connection_entry(
                        main_variable=_get_main_variable(sig),
                        axis_index=ai,
                        signal_index=si,
                        color=None,
                    )
                    if entry:
                        connections.append(entry)
        elif signal_mode == "array_row":
            rows = instr.Rows
            for ri in range(int(rows.Count)):
                row = rows.Item(ri)
                entry = _build_signal_connection_entry(
                    main_variable=row.MainVariable,
                    axis_index=None,
                    signal_index=ri,
                    color=None,
                )
                if entry:
                    connections.append(entry)
        elif signal_mode == "sub_instrument":
            entry = _build_signal_connection_entry(
                main_variable=instr.ActiveSubInstrument.MainVariable,
                axis_index=None,
                signal_index=None,
                color=None,
            )
            if entry:
                connections.append(entry)
    except Exception:
        pass  # Signal info is best-effort; don't fail the whole call

    return {
        "instrument_name": instrument_name,
        "instrument_type": type_string,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "signal_connections": connections,
    }


# ── instrument_move ────────────────────────────────────────────────────────────


def instrument_move(
    app: Any,
    instrument_name: str,
    x: int | None,
    y: int | None,
    width: int | None,
    height: int | None,
) -> dict[str, Any]:
    """Move and/or resize an instrument on the active layout.

    Only provided values are updated; others remain unchanged.
    Returns dict with: instrument_name, x, y, width, height.
    """
    instruments = _get_instruments(app)
    instr = _get_instrument_item(instruments, instrument_name)

    try:
        pos = instr.Position
        new_x = x if x is not None else int(pos.X)
        new_y = y if y is not None else int(pos.Y)
        new_w = width if width is not None else int(pos.Width)
        new_h = height if height is not None else int(pos.Height)

        if x is not None:
            pos.X = x
        if y is not None:
            pos.Y = y
        if width is not None:
            pos.Width = width
        if height is not None:
            pos.Height = height

        return {
            "instrument_name": instrument_name,
            "x": new_x,
            "y": new_y,
            "width": new_w,
            "height": new_h,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IViPosition", method="X/Y/Width/Height") from exc


# ── instrument_configure ───────────────────────────────────────────────────────


def instrument_configure(
    app: Any,
    instrument_name: str,
    caption: str | None,
    back_color: str | None,
    fore_color: str | None,
    show_border: bool | None,
) -> dict[str, Any]:
    """Configure display properties of an instrument.

    Only provided values are updated.
    Returns dict with applied values.
    """
    instruments = _get_instruments(app)
    instr = _get_instrument_item(instruments, instrument_name)

    try:
        if caption is not None:
            instr.Caption = caption
        if back_color is not None:
            instr.BackColor = _hex_to_rgb_int(back_color)
        if fore_color is not None:
            instr.ForeColor = _hex_to_rgb_int(fore_color)
        if show_border is not None:
            instr.ShowBorder = show_border
        return {
            "instrument_name": instrument_name,
            "caption": caption,
            "back_color": back_color,
            "fore_color": fore_color,
            "show_border": show_border,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IViInstrumentRoot", method="configure") from exc


# ── instrument_connect_signal ──────────────────────────────────────────────────


def instrument_connect_signal(
    app: Any,
    instrument_name: str,
    variable_path: str,
    signal_color: str | None,
    axis_index: int,
) -> dict[str, Any]:
    """Connect a variable/signal to an instrument.

    Connection method depends on the instrument type:
    - main_variable: instrument.MainVariable = variable_path
    - plotter_signal: YAxes.Add() + Signals.Add() + signal.MainVariable
    - array_row: Rows.Add() + row.MainVariable
    - sub_instrument: SubInstruments.Add() + ActiveSubInstrument.MainVariable

    Returns dict with: instrument_name, instrument_type, variable_path, connection_mode.
    """
    instruments = _get_instruments(app)
    instr = _get_instrument_item(instruments, instrument_name)

    try:
        type_string = _get_type_string(instr)
    except Exception as exc:
        raise map_com_error(exc, interface="IViInstrumentRoot", method="TypeString") from exc

    signal_mode = _resolve_signal_mode(type_string)

    try:
        if signal_mode == "main_variable":
            instr.MainVariable = variable_path
        elif signal_mode == "plotter_signal":
            # Always add a new Y-axis and signal (confirmed correct API pattern)
            plot = instr.ActivePlot
            y_axis = plot.YAxes.Add()
            sig = y_axis.Signals.Add()
            sig.MainVariable = variable_path
            if signal_color is not None:
                try:
                    sig.Color = _hex_to_rgb_int(signal_color)
                except Exception:
                    pass
        elif signal_mode == "array_row":
            row = instr.Rows.Add()
            row.MainVariable = variable_path
        elif signal_mode == "sub_instrument":
            instr.SubInstruments.Add()
            instr.ActiveSubInstrument.MainVariable = variable_path

        return {
            "instrument_name": instrument_name,
            "instrument_type": type_string,
            "variable_path": variable_path,
            "connection_mode": signal_mode,
        }
    except Exception as exc:
        raise map_com_error(exc, interface="IViConnectableInstrument", method="connect_signal") from exc


# ── instrument_disconnect_signal ───────────────────────────────────────────────


def instrument_disconnect_signal(
    app: Any,
    instrument_name: str,
    variable_path: str | None,
    axis_index: int,
) -> dict[str, Any]:
    """Disconnect a variable/signal from an instrument.

    If variable_path is None, all connections are cleared.
    Returns dict with: instrument_name, variable_path.
    """
    instruments = _get_instruments(app)
    instr = _get_instrument_item(instruments, instrument_name)

    try:
        type_string = _get_type_string(instr)
    except Exception as exc:
        raise map_com_error(exc, interface="IViInstrumentRoot", method="TypeString") from exc

    signal_mode = _resolve_signal_mode(type_string)

    try:
        if signal_mode == "main_variable":
            instr.MainVariable = ""
        elif signal_mode == "plotter_signal":
            plot = instr.ActivePlot
            y_axes = plot.YAxes
            if variable_path is None:
                # Clear all signals from all axes
                for ai in range(int(y_axes.Count)):
                    axis = y_axes.Item(ai)
                    sigs = axis.Signals
                    for _ in range(int(sigs.Count)):
                        sigs.Item(0).Remove()
            else:
                # Remove specific signal matching variable_path
                if int(y_axes.Count) > axis_index:
                    axis = y_axes.Item(axis_index)
                    sigs = axis.Signals
                    for si in range(int(sigs.Count)):
                        sig = sigs.Item(si)
                        current_main_variable = _get_main_variable(sig)
                        current_path, _, _ = _extract_variable_path(current_main_variable)
                        if current_path == variable_path:
                            sig.Remove()
                            break
        elif signal_mode == "array_row":
            rows = instr.Rows
            if variable_path is None:
                for _ in range(int(rows.Count)):
                    rows.Item(0).Remove()
            else:
                for ri in range(int(rows.Count)):
                    row = rows.Item(ri)
                    if str(row.MainVariable) == variable_path:
                        row.Remove()
                        break
        elif signal_mode == "sub_instrument":
            instr.ActiveSubInstrument.MainVariable = ""

        return {"instrument_name": instrument_name, "variable_path": variable_path}
    except Exception as exc:
        raise map_com_error(exc, interface="IViConnectableInstrument", method="disconnect_signal") from exc


# ── instrument_arrange ─────────────────────────────────────────────────────────

_ARRANGE_METHOD_MAP: dict[str, str] = {
    "align_top": "AlignTop",
    "align_bottom": "AlignBottom",
    "align_left": "AlignLeft",
    "align_right": "AlignRight",
    "center_horizontally": "CenterInViewHorizontally",
    "center_vertically": "CenterInViewVertically",
    "space_evenly_horizontal": "SpaceEvenlyAcross",
    "space_evenly_vertical": "SpaceEvenlyDown",
}


def instrument_arrange(
    app: Any,
    instrument_names: list[str],
    action: str,
) -> dict[str, Any]:
    """Align, distribute, group, or ungroup instruments on the active layout.

    Returns dict with: action, instrument_names, group_name (for group action).
    """
    active = _get_active_layout(app)
    instruments = _get_instruments(app)

    group_name: str | None = None

    try:
        if action == "ungroup":
            # For ungroup, the first name should be the group instrument
            if not instrument_names:
                raise BridgeOperationError(
                    "instrument_names must contain the group instrument name for action='ungroup'.",
                )
            group_instr = _get_instrument_item(instruments, instrument_names[0])
            group_instr.Ungroup()
        elif action == "group":
            # Select all instruments, then group
            for name in instrument_names:
                instr = _get_instrument_item(instruments, name)
                instr.SelectMulti()
            sel = active.Selection
            group = sel.Group()
            try:
                group_name = str(group.Name)
            except Exception:
                group_name = None
        else:
            # Alignment / distribution
            method_name = _ARRANGE_METHOD_MAP.get(action)
            if method_name is None:
                raise BridgeOperationError(
                    f"Unknown arrange action '{action}'. "
                    f"Valid values: {list(_ARRANGE_METHOD_MAP.keys()) + ['group', 'ungroup']}",
                )
            for name in instrument_names:
                instr = _get_instrument_item(instruments, name)
                instr.SelectMulti()
            sel = active.Selection
            getattr(sel, method_name)()

        return {
            "action": action,
            "instrument_names": instrument_names,
            "group_name": group_name,
        }
    except (BridgePreconditionError, BridgeOperationError):
        raise
    except Exception as exc:
        raise map_com_error(exc, interface="IViTopLevelSelection", method=action) from exc
