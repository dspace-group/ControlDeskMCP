import asyncio
import functools
import time
from enum import Enum

from mcp import Tool  # noqa: F401
from mcp.server import FastMCP
from mcp.server.lowlevel.server import NotificationOptions

from controldesk_mcp.models.tooldecorator.metainfo import AnnotationInfo, ToolDomain
from controldesk_mcp.utils.logger import get_logger

_log = get_logger(__name__)

# Domains whose tools must not be auto-evicted while their COM state may be active.
# A bus logger or measurement session continues running in the background and the LLM
# must be able to call stop/cleanup tools even after a long pause.
_STATEFUL_DOMAINS: frozenset[ToolDomain] = frozenset(
    {
        ToolDomain.BUS_LOGGING,
        ToolDomain.BUS_MONITOR,
        ToolDomain.BUS_REPLAY,
        ToolDomain.MEASUREMENT,
        ToolDomain.RECORDER,
    }
)


class MCPToolCategory(Enum):
    MAIN = "main"
    ADD_ON = "add_on"
    SEARCH = "search"
    NONE = "none"


class MCPServer(FastMCP):

    tool_domain_dict: dict[str, list[str]] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._domain_has_deferred_addon_tools: dict[ToolDomain, bool] = {}
        self._deferred_search_tools: dict[str, list[tuple]] = {}
        self._deferred_addon_tools: dict[ToolDomain, list[tuple]] = {}

        # ── TTL / eviction tracking (Phase 1) ─────────────────────────────────
        # Per-TOOL last-used timestamp; a domain stays alive as long as any of its
        # tools was called within the TTL window.
        self._tool_last_used: dict[str, float] = {}
        # Which tools belong to each activated domain (for eviction bookkeeping).
        self._domain_tool_names: dict[ToolDomain, list[str]] = {}
        # Original (fn, kwargs) stored at activation time so the domain can be
        # re-deferred after eviction and re-activated on the next discover call.
        self._activated_tool_registry: dict[ToolDomain, list[tuple]] = {}
        # Set of currently active (non-deferred) ADD_ON domains.
        self._activated_addon_domains: set[ToolDomain] = set()

        self._patch_list_changed_capability()

    def _patch_list_changed_capability(self) -> None:
        """Ensure the initialization response advertises tools.listChanged=true.

        Clients (VS Code Copilot, etc.) check this flag before subscribing to
        notifications/tools/list_changed. Without it they ignore the notification.
        """
        original = self._mcp_server.create_initialization_options

        def _patched(notification_options=None, experimental_capabilities=None):
            opts = NotificationOptions(
                tools_changed=True,
                resources_changed=(
                    notification_options.resources_changed if notification_options else False
                ),
                prompts_changed=(
                    notification_options.prompts_changed if notification_options else False
                ),
            )
            return original(opts, experimental_capabilities or {})

        self._mcp_server.create_initialization_options = _patched

    def tool(
        self,
        name=None,
        title=None,
        description=None,
        annotations=AnnotationInfo,
        icons=None,
        meta=None,
        structured_output=None,
        tool_category: MCPToolCategory = MCPToolCategory.NONE,
        lazy_loading: bool = False,
    ):
        tool_domain = getattr(meta, "domain", None)

        def defer_decorator(fn):
            fn._mcp_tool_deferred = {
                "name": name,
                "title": title,
                "description": description,
                "annotations": annotations,
                "icons": icons,
                "meta": meta,
                "structured_output": structured_output,
            }
            if tool_domain not in self._deferred_addon_tools:
                self._deferred_addon_tools[tool_domain] = []
            self._deferred_addon_tools[tool_domain].append(
                (
                    fn,
                    {
                        "name": name,
                        "title": title,
                        "description": description,
                        "annotations": annotations,
                        "icons": icons,
                        "meta": meta,
                        "structured_output": structured_output,
                    },
                )
            )
            return fn

        match tool_category:
            case MCPToolCategory.MAIN:
                return super().tool(
                    name, title, description, annotations, icons, meta, structured_output
                )
            case MCPToolCategory.ADD_ON:
                if lazy_loading:
                    self._domain_has_deferred_addon_tools[tool_domain] = True
                    self._flush_deferred_search_tools_for_domain(tool_domain)
                    return defer_decorator
                else:
                    return super().tool(
                        name, title, description, annotations, icons, meta, structured_output
                    )
            case MCPToolCategory.SEARCH:
                if self._domain_has_deferred_addon_tools.get(tool_domain, False):
                    return super().tool(
                        name, title, description, annotations, icons, meta, structured_output
                    )
                else:

                    def deferred_search_decorator(fn):
                        if tool_domain not in self._deferred_search_tools:
                            self._deferred_search_tools[tool_domain] = []
                        self._deferred_search_tools[tool_domain].append(
                            (
                                fn,
                                {
                                    "name": name,
                                    "title": title,
                                    "description": description,
                                    "annotations": annotations,
                                    "icons": icons,
                                    "meta": meta,
                                    "structured_output": structured_output,
                                },
                            )
                        )
                        return fn

                    return deferred_search_decorator
            case MCPToolCategory.NONE:
                if lazy_loading:
                    self._domain_has_deferred_addon_tools[tool_domain] = True
                    self._flush_deferred_search_tools_for_domain(tool_domain)
                    return defer_decorator
                else:
                    return super().tool(
                        name, title, description, annotations, icons, meta, structured_output
                    )
            case _:
                raise ValueError(f"Invalid tool category: {tool_category}")

        return defer_decorator

    def _flush_deferred_search_tools_for_domain(self, domain: str) -> None:
        """Register all deferred SEARCH tools for a specific domain."""
        if domain in self._deferred_search_tools:
            while self._deferred_search_tools[domain]:
                fn, kwargs = self._deferred_search_tools[domain].pop(0)
                super().tool(**kwargs)(fn)
            del self._deferred_search_tools[domain]

    # ── Phase 1: per-tool usage tracking ─────────────────────────────────────

    def _wrap_with_usage_tracking(self, fn, tool_name: str, domain: ToolDomain):
        """Return a wrapper that stamps last_used on every ADD_ON tool call."""

        @functools.wraps(fn)
        async def _tracked(*args, **kwargs):
            self._tool_last_used[tool_name] = time.monotonic()
            _log.debug(
                "TTL touch: tool=%s domain=%s last_used=%.3f",
                tool_name,
                domain.value,
                self._tool_last_used[tool_name],
            )
            if asyncio.iscoroutinefunction(fn):
                return await fn(*args, **kwargs)
            return fn(*args, **kwargs)

        @functools.wraps(fn)
        def _tracked_sync(*args, **kwargs):
            self._tool_last_used[tool_name] = time.monotonic()
            _log.debug(
                "TTL touch: tool=%s domain=%s last_used=%.3f",
                tool_name,
                domain.value,
                self._tool_last_used[tool_name],
            )
            return fn(*args, **kwargs)

        return _tracked if asyncio.iscoroutinefunction(fn) else _tracked_sync

    def _domain_last_used(self, domain: ToolDomain) -> float:
        """Return the most recent last_used timestamp for any tool in domain."""
        names = self._domain_tool_names.get(domain, [])
        if not names:
            return 0.0
        return max((self._tool_last_used.get(n, 0.0) for n in names), default=0.0)

    # ── Phase 2: lazy eviction ────────────────────────────────────────────────

    async def evict_stale_domains(self, ttl_seconds: float, ctx) -> list[ToolDomain]:
        """Remove ADD_ON tools for domains idle longer than ttl_seconds.

        Safe to call from any SEARCH tool handler because ctx is available there.
        SEARCH tools and MAIN tools are never evicted.
        Stateful domains (bus_logging, bus_monitor, etc.) are skipped — see
        _STATEFUL_DOMAINS.
        Returns the list of evicted domains (empty when nothing is evicted).
        """
        now = time.monotonic()
        evicted: list[ToolDomain] = []

        for domain in list(self._activated_addon_domains):
            # Phase 3: stateful domain whitelist — never auto-evict
            if domain in _STATEFUL_DOMAINS:
                _log.debug("TTL eviction skipped: domain=%s is stateful", domain.value)
                continue

            last = self._domain_last_used(domain)
            idle_seconds = now - last
            if idle_seconds > ttl_seconds:
                _log.info(
                    "TTL evicting domain=%s idle_seconds=%.1f ttl_seconds=%.1f",
                    domain.value,
                    idle_seconds,
                    ttl_seconds,
                )
                await self._deactivate_domain_tools(domain, ctx)
                evicted.append(domain)

        return evicted

    async def _deactivate_domain_tools(self, domain: ToolDomain, ctx) -> None:
        """Remove activated ADD_ON tools for domain from FastMCP and notify client.

        The (fn, kwargs) pairs are moved back to _deferred_addon_tools so the
        domain can be re-activated by a subsequent discover call.
        """
        tool_names = self._domain_tool_names.get(domain, [])
        if not tool_names:
            _log.debug("TTL deactivate: domain=%s has no tracked tool names", domain.value)
            return

        tool_mgr = self._tool_manager
        removed: list[str] = []
        for tool_name in tool_names:
            try:
                tool_mgr.remove_tool(tool_name)
                removed.append(tool_name)
                self._tool_last_used.pop(tool_name, None)
            except Exception:
                _log.warning(
                    "TTL deactivate: could not remove tool=%s domain=%s",
                    tool_name,
                    domain.value,
                    exc_info=True,
                )

        # Move original (fn, kwargs) back to deferred so re-activation works.
        original_pairs = self._activated_tool_registry.pop(domain, [])
        if original_pairs:
            self._deferred_addon_tools[domain] = original_pairs

        self._domain_tool_names.pop(domain, None)
        self._activated_addon_domains.discard(domain)

        _log.info(
            "TTL evicted domain=%s removed_tools=%s",
            domain.value,
            removed,
        )

        # Notify the client to re-fetch tools/list.
        try:
            await ctx.request_context.session.send_tool_list_changed()
        except Exception:
            _log.warning(
                "TTL deactivate: failed to send tools/list_changed for domain=%s",
                domain.value,
                exc_info=True,
            )

    # ── Activation (enhanced for TTL tracking) ────────────────────────────────

    async def activate_domain_tools(self, domain: ToolDomain, ctx) -> list[str]:
        """Register deferred ADD_ON tools for a domain and notify the client.

        Called from SEARCH tool handlers so the client re-fetches tools/list
        immediately after discovery, making the ADD_ON tools callable.
        Returns the list of newly registered tool names.
        """
        pending = self._deferred_addon_tools.pop(domain, [])
        if not pending:
            if domain in self._activated_addon_domains:
                _log.debug("activate_domain_tools: domain=%s already active", domain.value)
            return []

        registered: list[str] = []
        stored_pairs: list[tuple] = []

        for fn, kwargs in pending:
            tool_name = kwargs.get("name") or fn.__name__
            tracked_fn = self._wrap_with_usage_tracking(fn, tool_name, domain)
            super().tool(**kwargs)(tracked_fn)
            registered.append(tool_name)
            stored_pairs.append((fn, kwargs))  # store originals for re-deferred on eviction

        # Record tracking state.
        self._domain_tool_names[domain] = registered
        self._activated_tool_registry[domain] = stored_pairs
        self._activated_addon_domains.add(domain)
        # Stamp initial last_used so the TTL countdown starts from activation.
        now = time.monotonic()
        for tool_name in registered:
            self._tool_last_used[tool_name] = now

        _log.info(
            "Activated domain=%s tools=%s",
            domain.value,
            registered,
        )

        await ctx.request_context.session.send_tool_list_changed()
        return registered
