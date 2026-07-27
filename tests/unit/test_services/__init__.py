"""Unit tests for TTL-based tool eviction in MCPServer (Phases 1-3)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from controldesk_mcp.models.tooldecorator.metainfo import ToolDomain
from controldesk_mcp.server.server import _STATEFUL_DOMAINS, MCPServer

# ── helpers ───────────────────────────────────────────────────────────────────


def _make_server() -> MCPServer:
    """Create a minimal MCPServer with patched FastMCP internals."""
    with patch("controldesk_mcp.server.server.MCPServer._patch_list_changed_capability"):
        srv = MCPServer.__new__(MCPServer)
        # Bootstrap the attributes MCPServer.__init__ sets.
        srv._domain_has_deferred_addon_tools = {}
        srv._deferred_search_tools = {}
        srv._deferred_addon_tools = {}
        srv._tool_last_used = {}
        srv._domain_tool_names = {}
        srv._activated_tool_registry = {}
        srv._activated_addon_domains = set()
        # activate_domain_tools calls super().tool() → FastMCP.add_tool() → _tool_manager
        srv._tool_manager = MagicMock()
        return srv


def _make_ctx():
    """Return a mock FastMCP Context with an async send_tool_list_changed."""
    ctx = MagicMock()
    ctx.request_context.session.send_tool_list_changed = AsyncMock()
    return ctx


def _register_deferred(srv: MCPServer, domain: ToolDomain, tool_names: list[str]) -> None:
    """Populate _deferred_addon_tools as if @mcp.tool(lazy_loading=True) had run."""
    pairs = []
    for n in tool_names:

        async def _fn(**kwargs):
            return {}

        _fn.__name__ = n
        pairs.append(
            (
                _fn,
                {
                    "name": n,
                    "title": None,
                    "description": None,
                    "annotations": None,
                    "icons": None,
                    "meta": None,
                    "structured_output": None,
                },
            )
        )
    srv._deferred_addon_tools[domain] = pairs


# ── Phase 1: tracking structures ─────────────────────────────────────────────


class TestTTLTrackingStructures:
    def test_initial_state_empty(self) -> None:
        srv = _make_server()
        assert srv._tool_last_used == {}
        assert srv._domain_tool_names == {}
        assert srv._activated_addon_domains == set()
        assert srv._activated_tool_registry == {}

    @pytest.mark.asyncio
    async def test_activate_stamps_last_used(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        _register_deferred(srv, ToolDomain.APPLICATION, ["app_window_manage"])

        before = time.monotonic()
        await srv.activate_domain_tools(ToolDomain.APPLICATION, ctx)
        after = time.monotonic()

        assert "app_window_manage" in srv._tool_last_used
        assert before <= srv._tool_last_used["app_window_manage"] <= after

    @pytest.mark.asyncio
    async def test_activate_adds_to_activated_domains(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        _register_deferred(srv, ToolDomain.APPLICATION, ["app_window_manage"])

        await srv.activate_domain_tools(ToolDomain.APPLICATION, ctx)

        assert ToolDomain.APPLICATION in srv._activated_addon_domains

    @pytest.mark.asyncio
    async def test_activate_idempotent_when_already_active(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        _register_deferred(srv, ToolDomain.APPLICATION, ["app_window_manage"])

        result1 = await srv.activate_domain_tools(ToolDomain.APPLICATION, ctx)
        result2 = await srv.activate_domain_tools(ToolDomain.APPLICATION, ctx)

        assert len(result1) == 1
        assert result2 == []  # nothing new to register

    @pytest.mark.asyncio
    async def test_domain_last_used_returns_max(self) -> None:
        srv = _make_server()
        srv._domain_tool_names[ToolDomain.APPLICATION] = ["tool_a", "tool_b"]
        srv._tool_last_used["tool_a"] = 100.0
        srv._tool_last_used["tool_b"] = 200.0

        assert srv._domain_last_used(ToolDomain.APPLICATION) == 200.0

    def test_domain_last_used_missing_domain_returns_zero(self) -> None:
        srv = _make_server()
        assert srv._domain_last_used(ToolDomain.APPLICATION) == 0.0

    def test_usage_tracking_wrapper_updates_timestamp(self) -> None:
        srv = _make_server()

        def _sync_fn():
            return "ok"

        wrapped = srv._wrap_with_usage_tracking(_sync_fn, "my_tool", ToolDomain.APPLICATION)
        before = time.monotonic()
        wrapped()
        after = time.monotonic()

        assert "my_tool" in srv._tool_last_used
        assert before <= srv._tool_last_used["my_tool"] <= after

    @pytest.mark.asyncio
    async def test_usage_tracking_async_wrapper_updates_timestamp(self) -> None:
        srv = _make_server()

        async def _async_fn():
            return "ok"

        wrapped = srv._wrap_with_usage_tracking(_async_fn, "my_async_tool", ToolDomain.APPLICATION)
        before = time.monotonic()
        await wrapped()
        after = time.monotonic()

        assert "my_async_tool" in srv._tool_last_used
        assert before <= srv._tool_last_used["my_async_tool"] <= after


# ── Phase 2: lazy eviction ────────────────────────────────────────────────────


class TestLazyEviction:
    def _prime_active_domain(
        self, srv: MCPServer, domain: ToolDomain, tool_names: list[str], last_used: float
    ) -> None:
        """Simulate a domain that was activated and last used at `last_used`."""
        srv._activated_addon_domains.add(domain)
        srv._domain_tool_names[domain] = tool_names
        for n in tool_names:
            srv._tool_last_used[n] = last_used
        # Build minimal (fn, kwargs) pairs for the registry.
        pairs = []
        for n in tool_names:

            async def _fn(**kw):
                return {}

            _fn.__name__ = n
            pairs.append((_fn, {"name": n}))
        srv._activated_tool_registry[domain] = pairs

    @pytest.mark.asyncio
    async def test_evicts_stale_domain(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        # last used 10 minutes ago
        self._prime_active_domain(
            srv,
            ToolDomain.APPLICATION,
            ["app_window_manage"],
            time.monotonic() - 600,
        )

        mock_tm = MagicMock()
        mock_tm.remove_tool = MagicMock()
        with patch.object(srv, "_tool_manager", mock_tm, create=True):
            evicted = await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        assert ToolDomain.APPLICATION in evicted
        assert ToolDomain.APPLICATION not in srv._activated_addon_domains
        mock_tm.remove_tool.assert_called_once_with("app_window_manage")

    @pytest.mark.asyncio
    async def test_does_not_evict_fresh_domain(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        # last used 1 minute ago (< 5-min TTL)
        self._prime_active_domain(
            srv,
            ToolDomain.APPLICATION,
            ["app_window_manage"],
            time.monotonic() - 60,
        )

        mock_tm = MagicMock()
        with patch.object(srv, "_tool_manager", mock_tm, create=True):
            evicted = await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        assert evicted == []
        assert ToolDomain.APPLICATION in srv._activated_addon_domains
        mock_tm.remove_tool.assert_not_called()

    @pytest.mark.asyncio
    async def test_evicted_domain_moved_back_to_deferred(self) -> None:
        """After eviction the domain must be re-deferrable for re-activation."""
        srv = _make_server()
        ctx = _make_ctx()
        self._prime_active_domain(
            srv,
            ToolDomain.APPLICATION,
            ["app_window_manage"],
            time.monotonic() - 600,
        )

        mock_tm = MagicMock()
        with patch.object(srv, "_tool_manager", mock_tm, create=True):
            await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        assert ToolDomain.APPLICATION in srv._deferred_addon_tools
        assert len(srv._deferred_addon_tools[ToolDomain.APPLICATION]) == 1

    @pytest.mark.asyncio
    async def test_eviction_clears_last_used_entries(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        self._prime_active_domain(
            srv,
            ToolDomain.APPLICATION,
            ["app_window_manage"],
            time.monotonic() - 600,
        )

        mock_tm = MagicMock()
        with patch.object(srv, "_tool_manager", mock_tm, create=True):
            await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        assert "app_window_manage" not in srv._tool_last_used

    @pytest.mark.asyncio
    async def test_eviction_sends_tools_list_changed(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        self._prime_active_domain(
            srv,
            ToolDomain.APPLICATION,
            ["app_window_manage"],
            time.monotonic() - 600,
        )

        mock_tm = MagicMock()
        with patch.object(srv, "_tool_manager", mock_tm, create=True):
            await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        ctx.request_context.session.send_tool_list_changed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_eviction_no_notification(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()

        evicted = await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        assert evicted == []
        ctx.request_context.session.send_tool_list_changed.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_multiple_domains_evicts_only_stale(self) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        # APPLICATION: stale (10 min idle)
        self._prime_active_domain(
            srv,
            ToolDomain.APPLICATION,
            ["app_window_manage"],
            time.monotonic() - 600,
        )
        # PROJECT: fresh (30 sec idle)
        self._prime_active_domain(
            srv,
            ToolDomain.PROJECT,
            ["project_list"],
            time.monotonic() - 30,
        )

        mock_tm = MagicMock()
        with patch.object(srv, "_tool_manager", mock_tm, create=True):
            evicted = await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        assert ToolDomain.APPLICATION in evicted
        assert ToolDomain.PROJECT not in evicted
        assert ToolDomain.PROJECT in srv._activated_addon_domains


# ── Phase 3: stateful domain whitelist ───────────────────────────────────────


class TestStatefulDomainWhitelist:
    def test_stateful_domains_constant(self) -> None:
        assert ToolDomain.BUS_LOGGING in _STATEFUL_DOMAINS
        assert ToolDomain.BUS_MONITOR in _STATEFUL_DOMAINS
        assert ToolDomain.BUS_REPLAY in _STATEFUL_DOMAINS
        assert ToolDomain.MEASUREMENT in _STATEFUL_DOMAINS
        assert ToolDomain.RECORDER in _STATEFUL_DOMAINS

    def test_non_stateful_domains_not_in_whitelist(self) -> None:
        assert ToolDomain.APPLICATION not in _STATEFUL_DOMAINS
        assert ToolDomain.PROJECT not in _STATEFUL_DOMAINS
        assert ToolDomain.PLATFORM not in _STATEFUL_DOMAINS
        assert ToolDomain.CALIBRATION not in _STATEFUL_DOMAINS
        assert ToolDomain.TOOL_WINDOW not in _STATEFUL_DOMAINS
        assert ToolDomain.VARIABLE not in _STATEFUL_DOMAINS

    @pytest.mark.asyncio
    @pytest.mark.parametrize("stateful_domain", list(_STATEFUL_DOMAINS))
    async def test_stateful_domain_never_evicted(self, stateful_domain: ToolDomain) -> None:
        srv = _make_server()
        ctx = _make_ctx()
        # last used 1 hour ago — well past any TTL
        srv._activated_addon_domains.add(stateful_domain)
        srv._domain_tool_names[stateful_domain] = ["some_tool"]
        srv._tool_last_used["some_tool"] = time.monotonic() - 3600

        mock_tm = MagicMock()
        with patch.object(srv, "_tool_manager", mock_tm, create=True):
            evicted = await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        assert stateful_domain not in evicted
        assert stateful_domain in srv._activated_addon_domains
        mock_tm.remove_tool.assert_not_called()


# ── Integration: activate → use → evict → re-activate cycle ─────────────────


class TestActivateEvictCycle:
    @pytest.mark.asyncio
    async def test_full_cycle(self) -> None:
        """Activate a domain, evict it, then re-activate it."""
        srv = _make_server()
        ctx = _make_ctx()
        _register_deferred(srv, ToolDomain.APPLICATION, ["app_window_manage"])

        names = await srv.activate_domain_tools(ToolDomain.APPLICATION, ctx)

        assert names == ["app_window_manage"]
        assert ToolDomain.APPLICATION in srv._activated_addon_domains

        # Simulate the domain going stale.
        srv._tool_last_used["app_window_manage"] = time.monotonic() - 600

        mock_tm = MagicMock()
        with patch.object(srv, "_tool_manager", mock_tm, create=True):
            evicted = await srv.evict_stale_domains(ttl_seconds=300, ctx=ctx)

        assert ToolDomain.APPLICATION in evicted
        assert ToolDomain.APPLICATION not in srv._activated_addon_domains

        # Re-activate — domain should be back in _deferred_addon_tools now.
        assert ToolDomain.APPLICATION in srv._deferred_addon_tools

        names2 = await srv.activate_domain_tools(ToolDomain.APPLICATION, ctx)

        assert names2 == ["app_window_manage"]
        assert ToolDomain.APPLICATION in srv._activated_addon_domains
