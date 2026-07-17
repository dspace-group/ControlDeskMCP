"""Manual product tests — application lifecycle tools (direct tool calls).

Each test calls the tool function directly with a Pydantic input model,
parses the JSON response envelope, and asserts the response fields.

No LLM involvement.  Requires a live ControlDesk instance (started by the
session fixture in tests/product/conftest.py).

Run:
    .\\scripts\\run_product_tests.ps1 -Suite manual
"""

from __future__ import annotations

import asyncio
import json

import pytest

from sources.models.application import (
    AppStartOrAttachInput,
    AppWindowManageAction,
    AppWindowManageInput,
    MainWindowState,
)
from sources.tools.application.lifecycle import (
    app_window_manage,
    start_controldesk,
)

pytestmark = pytest.mark.product

_VALID_STATES = {"Normal", "Maximized", "Minimized", "Hidden"}
_SETTLE_S: float = 1.0


# ── Helpers ───────────────────────────────────────────────────────────────────


def _ok(raw: str) -> dict:
    """Parse tool JSON and assert it is not an error envelope."""
    data = json.loads(raw)
    assert "error_code" not in data, f"Tool returned error: {data}"
    return data


async def _restore_normal() -> None:
    """Set window to Normal + visible and wait for COM to settle."""
    await app_window_manage(
        AppWindowManageInput(
            action=AppWindowManageAction.set_state,
            window_state=MainWindowState.Normal,
        )
    )
    await asyncio.sleep(_SETTLE_S)
    await app_window_manage(
        AppWindowManageInput(action=AppWindowManageAction.set_visible, visible=True)
    )
    await asyncio.sleep(_SETTLE_S)


# ── start_controldesk ───────────────────────────────────────────────────────


class TestAttach:
    async def test_attach_reports_attached(self) -> None:
        """Re-attaching to a running instance returns action='attached'."""
        raw = await start_controldesk(AppStartOrAttachInput())
        data = _ok(raw)
        assert data["status"] == "ok"
        assert data["action"] == "attached"
        assert data["is_new_instance"] is False
        assert data["controldesk_version"], "Expected non-empty version string"

    async def test_attach_returns_version(self) -> None:
        """Version field in tool response is a non-empty string."""
        raw = await start_controldesk(AppStartOrAttachInput())
        data = _ok(raw)
        assert isinstance(data["controldesk_version"], str)
        assert data["controldesk_version"]


# ── app_window_manage: visibility ────────────────────────────────────────────


class TestWindowVisibility:
    async def test_get_visibility_returns_bool(self) -> None:
        """get_visibility response contains a bool is_visible field."""
        raw = await app_window_manage(
            AppWindowManageInput(action=AppWindowManageAction.get_visibility)
        )
        data = json.loads(raw)
        assert isinstance(data["is_visible"], bool)

    async def test_set_visible_true(self) -> None:
        raw = await app_window_manage(
            AppWindowManageInput(action=AppWindowManageAction.set_visible, visible=True)
        )
        data = _ok(raw)
        await asyncio.sleep(_SETTLE_S)
        assert data["is_now_visible"] is True

    async def test_set_visible_false_then_restore(self) -> None:
        raw = await app_window_manage(
            AppWindowManageInput(action=AppWindowManageAction.set_visible, visible=False)
        )
        data = _ok(raw)
        await asyncio.sleep(_SETTLE_S)
        assert data["is_now_visible"] is False
        await app_window_manage(
            AppWindowManageInput(action=AppWindowManageAction.set_visible, visible=True)
        )
        await asyncio.sleep(_SETTLE_S)


# ── app_window_manage: state ─────────────────────────────────────────────────


class TestWindowState:
    async def test_get_state_returns_valid_state(self) -> None:
        raw = await app_window_manage(AppWindowManageInput(action=AppWindowManageAction.get_state))
        data = json.loads(raw)
        assert data["window_state"] in _VALID_STATES
        assert isinstance(data["is_visible"], bool)

    async def test_set_state_normal(self) -> None:
        raw = await app_window_manage(
            AppWindowManageInput(
                action=AppWindowManageAction.set_state,
                window_state=MainWindowState.Normal,
            )
        )
        data = _ok(raw)
        await asyncio.sleep(_SETTLE_S)
        assert data["window_state"] == "Normal"

    async def test_set_state_minimized_then_restore(self) -> None:
        await _restore_normal()
        raw = await app_window_manage(
            AppWindowManageInput(
                action=AppWindowManageAction.set_state,
                window_state=MainWindowState.Minimized,
            )
        )
        data = _ok(raw)
        await asyncio.sleep(_SETTLE_S)
        assert data["window_state"] == "Minimized"
        await app_window_manage(
            AppWindowManageInput(
                action=AppWindowManageAction.set_state,
                window_state=MainWindowState.Normal,
            )
        )
        await asyncio.sleep(_SETTLE_S)


# ── app_window_manage: fullscreen ────────────────────────────────────────────


class TestFullscreen:
    async def test_set_fullscreen_enabled(self) -> None:
        await _restore_normal()
        raw = await app_window_manage(
            AppWindowManageInput(action=AppWindowManageAction.set_fullscreen, enabled=True)
        )
        data = _ok(raw)
        await asyncio.sleep(_SETTLE_S)
        assert data["fullscreen_set"] is True
        assert data["fullscreen_enabled"] is True

    async def test_set_fullscreen_disabled(self) -> None:
        raw = await app_window_manage(
            AppWindowManageInput(action=AppWindowManageAction.set_fullscreen, enabled=False)
        )
        data = _ok(raw)
        await asyncio.sleep(_SETTLE_S)
        assert data["fullscreen_set"] is True
        assert data["fullscreen_enabled"] is False
