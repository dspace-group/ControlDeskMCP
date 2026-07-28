"""Unit tests for layout MCP tools.

Tests verify tool annotations and parameter marshalling.
Service functions are mocked to verify integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from controldesk_mcp.models.errors import ErrorEnvelope
from controldesk_mcp.models.layout import (
    LayoutActivateResult,
    LayoutCreateResult,
    LayoutDiscoverResult,
    LayoutExportResult,
    LayoutInfo,
    LayoutIoManageInput,
    LayoutListInput,
    LayoutListResult,
    LayoutManageAction,
    LayoutManageInput,
)

_TS = "2024-01-01T00:00:00Z"
_ERROR = ErrorEnvelope(error_code="E001", category="UNKNOWN", message="fail", retryable=False)
_INFO = LayoutInfo(
    name="ControlLayout",
    file_path="C:/test/ControlLayout.cdl",
    is_open=True,
    is_active=True,
    editing_mode="Runtime",
)


def _patch_svc(method: str, *, return_value):
    return patch(
        f"controldesk_mcp.services.layout_service.{method}",
        new_callable=AsyncMock,
        return_value=return_value,
    )


# ── layout_list ───────────────────────────────────────────────────────────────


class TestLayoutList:
    @pytest.mark.asyncio
    async def test_returns_list_result(self) -> None:
        expected = LayoutListResult(total_layouts=1, layouts=[_INFO])
        with _patch_svc("layout_list", return_value=expected):
            from controldesk_mcp.tools.layout.management import layout_list

            result = await layout_list(LayoutListInput())

        assert isinstance(result, LayoutListResult)
        assert result["total_layouts"] == 1

    @pytest.mark.asyncio
    async def test_returns_error_envelope(self) -> None:
        with _patch_svc("layout_list", return_value=_ERROR):
            from controldesk_mcp.tools.layout.management import layout_list

            result = await layout_list(LayoutListInput())

        assert isinstance(result, ErrorEnvelope)


# ── layout_manage — create ────────────────────────────────────────────────────


class TestLayoutManageCreate:
    @pytest.mark.asyncio
    async def test_create_returns_result(self) -> None:
        expected = LayoutCreateResult(created=True, name="NewLayout", file_path="", timestamp_utc=_TS)
        with _patch_svc("layout_create", return_value=expected):
            from controldesk_mcp.tools.layout.management import layout_manage

            result = await layout_manage(LayoutManageInput(action=LayoutManageAction.create, name="NewLayout"))

        assert isinstance(result, LayoutCreateResult)
        assert result["created"] is True

    @pytest.mark.asyncio
    async def test_create_missing_name_returns_error(self) -> None:
        from controldesk_mcp.tools.layout.management import layout_manage

        result = await layout_manage(LayoutManageInput(action=LayoutManageAction.create))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── layout_manage — configure ─────────────────────────────────────────────────


class TestLayoutManageConfigure:
    @pytest.mark.asyncio
    async def test_configure_missing_editing_mode_returns_error(self) -> None:
        from controldesk_mcp.tools.layout.management import layout_manage

        result = await layout_manage(LayoutManageInput(action=LayoutManageAction.configure, name="Layout1"))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"


# ── layout_manage — activate ──────────────────────────────────────────────────


class TestLayoutManageActivate:
    @pytest.mark.asyncio
    async def test_activate_returns_result(self) -> None:
        expected = LayoutActivateResult(activated=True, name="ControlLayout", timestamp_utc=_TS)
        with _patch_svc("layout_activate", return_value=expected):
            from controldesk_mcp.tools.layout.management import layout_manage

            result = await layout_manage(LayoutManageInput(action=LayoutManageAction.activate, name="ControlLayout"))

        assert isinstance(result, LayoutActivateResult)
        assert result["activated"] is True


# ── layout_io_manage ──────────────────────────────────────────────────────────


class TestLayoutIoManage:
    @pytest.mark.asyncio
    async def test_export_missing_path_returns_error(self) -> None:
        from controldesk_mcp.models.layout import LayoutIoManageAction
        from controldesk_mcp.tools.layout.management import layout_io_manage

        result = await layout_io_manage(LayoutIoManageInput(action=LayoutIoManageAction.export))

        assert isinstance(result, ErrorEnvelope)
        assert result["error_code"] == "MISSING_PARAM"

    @pytest.mark.asyncio
    async def test_export_returns_result(self) -> None:
        from controldesk_mcp.models.layout import LayoutIoManageAction

        expected = LayoutExportResult(
            exported=True,
            layout_name="ControlLayout",
            export_path="C:/out/export.lax",
            timestamp_utc=_TS,
        )
        with _patch_svc("layout_export", return_value=expected):
            from controldesk_mcp.tools.layout.management import layout_io_manage

            result = await layout_io_manage(
                LayoutIoManageInput(action=LayoutIoManageAction.export, export_path="C:/out/export.lax")
            )

        assert isinstance(result, LayoutExportResult)
        assert result["exported"] is True


# ── layout_discover ───────────────────────────────────────────────────────────


class TestLayoutDiscover:
    @pytest.mark.asyncio
    async def test_returns_discover_result(self) -> None:
        from unittest.mock import MagicMock

        ctx = MagicMock()
        with (
            patch("controldesk_mcp.tools.layout.management.get_settings") as mock_settings,
            patch("controldesk_mcp.tools.layout.management.mcp.evict_stale_domains", new_callable=AsyncMock),
            patch("controldesk_mcp.tools.layout.management.mcp.activate_domain_tools", new_callable=AsyncMock),
        ):
            mock_settings.return_value.tool_ttl_enabled = False
            from controldesk_mcp.tools.layout.management import layout_discover

            result = await layout_discover(ctx)

        assert isinstance(result, LayoutDiscoverResult)
        assert len(result["tools"]) == 1
        assert result["tools"][0]["tool_name"] == "controldesk_layout_io_manage"
