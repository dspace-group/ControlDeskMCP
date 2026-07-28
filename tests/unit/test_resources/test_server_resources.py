"""Unit tests for controldesk_mcp.resources.server_resources."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_settings(**overrides):
    cfg = MagicMock()
    cfg.server_version = overrides.get("server_version", "0.1.0")
    cfg.mcp_transport = overrides.get("mcp_transport", "stdio")
    cfg.mcp_host = overrides.get("mcp_host", "127.0.0.1")
    cfg.mcp_port = overrides.get("mcp_port", 8000)
    cfg.controldesk_version = overrides.get("controldesk_version", "")
    cfg.com_timeout_ms = overrides.get("com_timeout_ms", 8000)
    cfg.com_launch_timeout_ms = overrides.get("com_launch_timeout_ms", 30_000)
    cfg.com_reconnect_attempts = overrides.get("com_reconnect_attempts", 3)
    return cfg


def _make_tool(name: str, description: str) -> MagicMock:
    t = MagicMock()
    t.name = name
    t.description = description
    return t


# ── get_server_info ───────────────────────────────────────────────────────────


class TestGetServerInfo:
    def test_returns_all_config_fields(self) -> None:
        cfg = _make_settings(server_version="1.2.3", mcp_transport="streamable-http", mcp_port=9000)
        with patch("controldesk_mcp.resources.server_resources.get_settings", return_value=cfg):
            from controldesk_mcp.resources.server_resources import get_server_info

            result = json.loads(get_server_info())

        assert result["server_version"] == "1.2.3"
        assert result["transport"] == "streamable-http"
        assert result["port"] == 9000
        assert result["com_timeout_ms"] == 8000
        assert result["com_reconnect_attempts"] == 3

    def test_empty_version_shows_auto_detect(self) -> None:
        cfg = _make_settings(controldesk_version="")
        with patch("controldesk_mcp.resources.server_resources.get_settings", return_value=cfg):
            from controldesk_mcp.resources.server_resources import get_server_info

            result = json.loads(get_server_info())

        assert result["controldesk_version_target"] == "auto-detect"

    def test_set_version_shown_as_is(self) -> None:
        cfg = _make_settings(controldesk_version="2026-A")
        with patch("controldesk_mcp.resources.server_resources.get_settings", return_value=cfg):
            from controldesk_mcp.resources.server_resources import get_server_info

            result = json.loads(get_server_info())

        assert result["controldesk_version_target"] == "2026-A"


# ── get_tool_catalog ──────────────────────────────────────────────────────────


class TestGetToolCatalog:
    def test_returns_sorted_tool_list(self) -> None:
        fake_tools = [
            _make_tool("variable_read_scalar", "Read a scalar variable"),
            _make_tool("start_controldesk", "Start or attach to ControlDesk"),
        ]
        mock_mgr = MagicMock()
        mock_mgr.list_tools.return_value = fake_tools

        with patch("controldesk_mcp.resources.server_resources.mcp") as mock_mcp:
            mock_mcp._tool_manager = mock_mgr
            from controldesk_mcp.resources import server_resources

            result = json.loads(server_resources.get_tool_catalog())

        assert result["count"] == 2
        names = [t["name"] for t in result["tools"]]
        assert names == sorted(names), "Tools must be sorted alphabetically"

    def test_count_matches_tool_list_length(self) -> None:
        fake_tools = [_make_tool(f"tool_{i}", f"Description {i}") for i in range(5)]
        mock_mgr = MagicMock()
        mock_mgr.list_tools.return_value = fake_tools

        with patch("controldesk_mcp.resources.server_resources.mcp") as mock_mcp:
            mock_mcp._tool_manager = mock_mgr
            from controldesk_mcp.resources import server_resources

            result = json.loads(server_resources.get_tool_catalog())

        assert result["count"] == 5
        assert len(result["tools"]) == 5

    def test_empty_description_handled(self) -> None:
        fake_tools = [_make_tool("no_desc_tool", "")]
        mock_mgr = MagicMock()
        mock_mgr.list_tools.return_value = fake_tools

        with patch("controldesk_mcp.resources.server_resources.mcp") as mock_mcp:
            mock_mcp._tool_manager = mock_mgr
            from controldesk_mcp.resources import server_resources

            result = json.loads(server_resources.get_tool_catalog())

        assert result["tools"][0]["description"] == ""


# ── get_connection_status ─────────────────────────────────────────────────────


class TestGetConnectionStatus:
    def test_returns_health_when_connected(self) -> None:
        mock_conn = MagicMock()
        mock_conn.health.return_value = {
            "connected": True,
            "state": "CONNECTED",
            "prog_id": "ControlDeskNG.Application.2026-A",
        }

        with patch("controldesk_mcp.resources.server_resources.com_bridge") as mock_bridge:
            mock_bridge.get_connection.return_value = mock_conn
            from controldesk_mcp.resources import server_resources

            result = json.loads(server_resources.get_connection_status())

        assert result["connected"] is True
        assert result["state"] == "CONNECTED"

    def test_returns_not_started_when_bridge_uninitialized(self) -> None:
        with patch("controldesk_mcp.resources.server_resources.com_bridge") as mock_bridge:
            mock_bridge.get_connection.side_effect = RuntimeError("Bridge not started")
            from controldesk_mcp.resources import server_resources

            result = json.loads(server_resources.get_connection_status())

        assert result["connected"] is False
        assert result["state"] == "NOT_STARTED"
        assert "message" in result

    def test_not_started_message_is_actionable(self) -> None:
        with patch("controldesk_mcp.resources.server_resources.com_bridge") as mock_bridge:
            mock_bridge.get_connection.side_effect = RuntimeError("not started")
            from controldesk_mcp.resources import server_resources

            result = json.loads(server_resources.get_connection_status())

        assert "controldesk_app_start_or_attach" in result["message"]
