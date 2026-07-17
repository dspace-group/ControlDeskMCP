"""Pydantic input and response models for the online calibration domain.

Domain: ControlDesk Online Calibration (start/stop calibration, page switching,
        parameter refresh, proposed calibration lifecycle, page copy).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from sources.models.base import DictModelMixin

# ── Enums ───────────────────────────────────────────────────────────────────────


class InitialPageType(str, Enum):
    """ECU memory page type."""

    WorkingPage = "WorkingPage"
    ReferencePage = "ReferencePage"


class CalibrationQueryAction(str, Enum):
    """Actions for calibration_query read-only tool."""

    get_state = "get_state"


class CalibrationManageAction(str, Enum):
    """Actions for calibration_manage consolidated tool (mutating only)."""

    activate_reference_page = "activate_reference_page"
    activate_working_page = "activate_working_page"
    refresh_parameters = "refresh_parameters"


class ProposedCalibrationManageAction(str, Enum):
    """Actions for proposed_calibration_manage consolidated tool."""

    start = "start"
    stop = "stop"
    apply = "apply"
    cancel = "cancel"


class CalibrationPageManageAction(str, Enum):
    """Actions for calibration_page_manage consolidated tool."""

    copy_working_to_reference = "copy_working_to_reference"
    copy_reference_to_working = "copy_reference_to_working"


# ── Input models (no parameters — all calibration tools take no input) ──────────
# Tools 1–5 and 6–9 require no user parameters; empty BaseModels satisfy the
# 5-layer pattern requirement that every tool uses a Pydantic BaseModel for input.


class CalibrationStartInput(BaseModel):
    """Input for calibration_start."""

    dry_run: bool = Field(
        default=False,
        description=(
            "When True, checks whether online calibration is already running and returns "
            "a preview without starting it. Use this to preview a start before committing it."
        ),
    )


class CalibrationStopInput(BaseModel):
    """Input for calibration_stop (no parameters required)."""


class CalibrationActivateReferencePageInput(BaseModel):
    """Input for calibration_activate_reference_page (no parameters required)."""


class CalibrationActivateWorkingPageInput(BaseModel):
    """Input for calibration_activate_working_page (no parameters required)."""


class CalibrationRefreshParametersInput(BaseModel):
    """Input for calibration_refresh_parameters (no parameters required)."""


class ProposedCalibrationStartInput(BaseModel):
    """Input for proposed_calibration_start (no parameters required)."""


class ProposedCalibrationStopInput(BaseModel):
    """Input for proposed_calibration_stop (no parameters required)."""


class ProposedCalibrationApplyInput(BaseModel):
    """Input for proposed_calibration_apply (no parameters required)."""


class ProposedCalibrationCancelInput(BaseModel):
    """Input for proposed_calibration_cancel (no parameters required)."""


class CalibrationQueryInput(BaseModel):
    """Input for calibration_query (read-only actions)."""

    action: CalibrationQueryAction = CalibrationQueryAction.get_state


class CalibrationGetStateInput(BaseModel):
    """Input for calibration_get_state (no parameters required)."""


class CalibrationCopyWorkingPageToReferenceInput(BaseModel):
    """Input for calibration_copy_working_page_to_reference."""

    platform_name: str = Field(
        description="Name of the platform whose working page will be copied to the reference page.",
        examples=["XCP", "XCPonEth"],
    )


class CalibrationCopyReferencePageToWorkingInput(BaseModel):
    """Input for calibration_copy_reference_page_to_working."""

    platform_name: str = Field(
        description="Name of the platform whose reference page will be copied to the working page.",
        examples=["XCP", "XCPonEth"],
    )


# ── Result models (Category B — COM bridge returns raw dicts) ─────────────────


class CalibrationStartResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    started: bool


class CalibrationStopResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    stopped: bool


class CalibrationActivateReferencePageResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    activated: bool
    page: str


class CalibrationActivateWorkingPageResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    activated: bool
    page: str


class CalibrationRefreshParametersResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    refreshed: bool
    timestamp_utc: str


class ProposedCalibrationStartResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    started: bool
    proposed_calibration_active: bool


class ProposedCalibrationStopResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    stopped: bool
    changes_applied: bool
    proposed_calibration_active: bool


class ProposedCalibrationApplyResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    applied: bool
    proposed_calibration_active: bool


class ProposedCalibrationCancelResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    cancelled: bool
    proposed_calibration_active: bool


class CalibrationGetStateResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    calibration_state: str
    calibration_state_raw: int
    proposed_calibration_state: str
    proposed_calibration_state_raw: int


class CalibrationCopyWorkingPageToReferenceResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    copied: bool
    platform_name: str
    source_page: str
    target_page: str


class CalibrationCopyReferencePageToWorkingResult(DictModelMixin, BaseModel):
    model_config = {"extra": "allow"}
    copied: bool
    platform_name: str
    source_page: str
    target_page: str


# ── Consolidated manage input models ─────────────────────────────────────────


class CalibrationManageInput(BaseModel):
    """Input for calibration_manage consolidated tool."""

    action: CalibrationManageAction = Field(
        description="Action to perform: activate_reference_page, "
        "activate_working_page, or refresh_parameters. "
        "For read-only state queries, use calibration_query instead.",
        examples=["activate_working_page", "refresh_parameters"],
    )


class ProposedCalibrationManageInput(BaseModel):
    """Input for proposed_calibration_manage consolidated tool."""

    action: ProposedCalibrationManageAction = Field(
        description="Action to perform: start, stop, apply, or cancel.",
        examples=["start", "apply"],
    )


class CalibrationPageManageInput(BaseModel):
    """Input for calibration_page_manage consolidated tool."""

    action: CalibrationPageManageAction = Field(
        description="Action to perform: copy_working_to_reference or copy_reference_to_working.",
        examples=["copy_working_to_reference"],
    )
    platform_name: Optional[str] = Field(
        default=None,
        description="Name of the platform for the page copy operation.",
        examples=["XCP", "XCPonEth"],
    )


# ── Discover result models ────────────────────────────────────────────────────


class ToolActionEntry(DictModelMixin, BaseModel):
    """Single tool entry in the calibration domain catalogue."""

    tool_name: str
    purpose: str
    actions: list[str]
    required_params_per_action: dict[str, list[str]]


class CalibrationDiscoverResult(DictModelMixin, BaseModel):
    """Successful response from calibration_discover."""

    status: Literal["ok"] = "ok"
    tools: list[ToolActionEntry]
