"""Variable path resolution foundation for ControlDesk variable workflows.

Phase 1 scope:
  - deterministic name variant generation
  - authoritative list-all pagination helper
  - lightweight scoring and ranked candidate selection
  - shared resolver result shape for later tool/service wiring
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable

_CAMEL_BOUNDARY_RE = re.compile(r"([a-z0-9])([A-Z])")
_NON_ALNUM_RE = re.compile(r"[^A-Za-z0-9]+")
_DSPACE_INSTRUMENT_TAIL_RE = re.compile(r"^dSPACE\s+\S+\s+\S+\s+(.+)$", re.IGNORECASE)


class ResolutionStatus(str, Enum):
    """Resolver status values for downstream orchestration flows."""

    resolved = "resolved"
    ambiguous = "ambiguous"
    not_found = "not_found"


@dataclass(slots=True)
class ScoredCandidate:
    """A ranked candidate result from authoritative list-all matching."""

    name: str
    connection_path: str
    score: float
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ResolverResult:
    """Standardized resolver output for read/write/signal-add entry points."""

    status: ResolutionStatus
    resolved_path: str | None
    confidence: float
    candidates: list[ScoredCandidate] = field(default_factory=list)
    attempt_log: list[str] = field(default_factory=list)
    telemetry: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class _CacheEntry:
    path: str
    expires_at: float


FindVariableFn = Callable[[str, str | None], Awaitable[dict[str, Any]]]
ListAllPageFn = Callable[[int, int], Awaitable[dict[str, Any]]]


def is_connection_path(value: str) -> bool:
    """Return True when *value* already looks like a qualified connection path."""
    return "://" in value


def extract_instrument_tail_hint(query: str, instrument_names: list[str]) -> str | None:
    """Extract an instrument-derived tail hint for variable path resolution.

    Instrument names following `dSPACE <Category> <SubCategory> <Tail>` can
    provide a semantic `<Tail>` hint for variable lookup.
    """
    if not query.strip():
        return None

    query_tokens = set(_tokenize(query))
    query_lower = query.strip().lower()

    for instrument_name in instrument_names:
        name = instrument_name.strip()
        if not name:
            continue
        tail = _parse_dspace_tail(name)
        if not tail:
            continue

        name_lower = name.lower()
        if query_lower == name_lower or query_lower in name_lower or name_lower in query_lower:
            return tail

        name_tokens = set(_tokenize(name))
        if query_tokens and len(query_tokens.intersection(name_tokens)) >= 2:
            return tail

    return None


def generate_name_variants(raw: str) -> list[str]:
    """Generate bounded deterministic variants for user-provided variable text.

    Order is intentionally fixed and mirrors the implementation plan.
    """
    original = raw.strip()
    if not original:
        return []

    words = _split_words(original)
    if not words:
        return [original]

    pascal = "".join(part.capitalize() for part in words)
    camel = words[0].lower() + "".join(part.capitalize() for part in words[1:])
    snake = "_".join(part.lower() for part in words)
    upper_snake = snake.upper()
    title_case = " ".join(part.capitalize() for part in words)
    upper_spaced = " ".join(part.upper() for part in words)
    lower_spaced = " ".join(part.lower() for part in words)
    kebab = "-".join(part.lower() for part in words)

    ordered = [
        pascal,
        camel,
        snake,
        upper_snake,
        title_case,
        upper_spaced,
        lower_spaced,
        kebab,
        original,
    ]
    return _dedupe_preserve_order(ordered)


def rank_candidates(query: str, candidates: list[dict[str, Any]], limit: int = 5) -> list[ScoredCandidate]:
    """Rank candidate variables by deterministic token and exactness heuristics."""
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    ranked: list[ScoredCandidate] = []
    normalized_query = " ".join(query_tokens)

    for candidate in candidates:
        name = str(candidate.get("name", "") or "")
        path = str(candidate.get("connection_path", "") or "")
        score, rationale = _score_candidate(normalized_query, query_tokens, name, path)
        if score <= 0.0:
            continue
        ranked.append(
            ScoredCandidate(
                name=name,
                connection_path=path,
                score=score,
                rationale=rationale,
                metadata={k: v for k, v in candidate.items() if k not in {"name", "connection_path"}},
            )
        )

    ranked.sort(key=lambda item: (-item.score, item.name.lower(), item.connection_path.lower()))
    return ranked[: max(limit, 1)]


async def collect_list_all_candidates(
    fetch_page: ListAllPageFn,
    page_size: int = 500,
    max_pages: int = 200,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Collect variable candidates from list-all responses with pagination support."""
    if page_size < 1:
        raise ValueError("page_size must be >= 1")
    if max_pages < 1:
        raise ValueError("max_pages must be >= 1")

    attempt_log: list[str] = []
    candidates: list[dict[str, Any]] = []
    offset = 0
    page_index = 0

    while page_index < max_pages:
        page_index += 1
        payload = await fetch_page(offset, page_size)
        attempt_log.append(f"list_all page={page_index} offset={offset} limit={page_size}")

        if "by_type" in payload:
            flattened = _flatten_by_type(payload.get("by_type", {}))
            candidates.extend(flattened)
            attempt_log.append(f"list_all grouped payload entries={len(flattened)}")
            break

        page_items = _extract_page_items(payload)
        candidates.extend(page_items)

        has_more_value = payload.get("has_more")
        has_more = bool(has_more_value)
        next_offset = payload.get("next_offset")
        if has_more and isinstance(next_offset, int) and next_offset > offset:
            offset = next_offset
            continue

        if has_more_value is False:
            break

        if len(page_items) >= page_size:
            offset += page_size
            continue

        break

    return candidates, attempt_log


class VariablePathResolver:
    """Resolve user-facing variable text to concrete connection paths."""

    def __init__(
        self,
        find_variable: FindVariableFn,
        list_all_page: ListAllPageFn,
        *,
        cache_ttl_seconds: float = 300.0,
        enable_cache: bool = True,
        debug_telemetry: bool = False,
        now_fn: Callable[[], float] | None = None,
    ):
        self._find_variable = find_variable
        self._list_all_page = list_all_page
        self._cache_ttl_seconds = max(0.0, cache_ttl_seconds)
        self._enable_cache = enable_cache
        self._debug_telemetry = debug_telemetry
        self._now_fn = now_fn or time.monotonic
        self._cache: dict[str, _CacheEntry] = {}

    def clear_cache(self) -> None:
        self._cache.clear()

    def cache_size(self) -> int:
        return len(self._cache)

    async def resolve(self, query: str, *, max_find_attempts: int = 9, hint_query: str | None = None) -> ResolverResult:
        attempt_log: list[str] = []
        text = query.strip()
        if not text:
            return ResolverResult(
                status=ResolutionStatus.not_found,
                resolved_path=None,
                confidence=0.0,
                candidates=[],
                attempt_log=["empty query"],
                telemetry=self._telemetry(
                    strategy="empty_query",
                    attempt_log=["empty query"],
                    fallback_activated=False,
                    candidate_count=0,
                    confidence=0.0,
                    hint_used=False,
                    cache_hit=False,
                ),
            )

        cache_key = _cache_key(text)
        entry = self._cache.get(cache_key)
        if entry is not None and self._enable_cache:
            if entry.expires_at > self._now_fn():
                telemetry = self._telemetry(
                    strategy="cache_hit",
                    attempt_log=["cache hit"],
                    fallback_activated=False,
                    candidate_count=0,
                    confidence=1.0,
                    hint_used=bool((hint_query or "").strip()),
                    cache_hit=True,
                )
                if self._debug_telemetry:
                    telemetry["cache_ttl_seconds"] = self._cache_ttl_seconds
                return ResolverResult(
                    status=ResolutionStatus.resolved,
                    resolved_path=entry.path,
                    confidence=1.0,
                    candidates=[],
                    attempt_log=["cache hit"],
                    telemetry=telemetry,
                )
            self._cache.pop(cache_key, None)
            attempt_log.append("cache expired")

        if is_connection_path(text):
            telemetry = self._telemetry(
                strategy="already_connection_path",
                attempt_log=["already connection path"],
                fallback_activated=False,
                candidate_count=0,
                confidence=1.0,
                hint_used=False,
                cache_hit=False,
            )
            return ResolverResult(
                status=ResolutionStatus.resolved,
                resolved_path=text,
                confidence=1.0,
                candidates=[],
                attempt_log=["already connection path"],
                telemetry=telemetry,
            )

        variants = generate_name_variants(text)
        normalized_hint = (hint_query or "").strip()
        if normalized_hint and normalized_hint.lower() != text.lower():
            attempt_log.append(f"instrument hint='{normalized_hint}'")
            variants = _dedupe_preserve_order(generate_name_variants(normalized_hint) + variants)

        for variant in variants[:max_find_attempts]:
            attempt_log.append(f"find name variant='{variant}'")
            result = await self._find_variable(variant, "name")
            if not bool(result.get("found")):
                continue

            resolved_path = _extract_connection_path(result)
            if not resolved_path:
                continue

            self._store_cache(cache_key, resolved_path)
            return ResolverResult(
                status=ResolutionStatus.resolved,
                resolved_path=resolved_path,
                confidence=0.95,
                candidates=[],
                attempt_log=attempt_log,
                telemetry=self._telemetry(
                    strategy="find_name",
                    attempt_log=attempt_log,
                    fallback_activated=False,
                    candidate_count=0,
                    confidence=0.95,
                    hint_used=bool(normalized_hint),
                    cache_hit=False,
                ),
            )

        fallback_candidates, fallback_log = await collect_list_all_candidates(self._list_all_page)
        attempt_log.extend(fallback_log)
        ranking_query = normalized_hint if normalized_hint else text
        if normalized_hint:
            attempt_log.append(f"ranking query='{ranking_query}'")
        ranked = rank_candidates(ranking_query, fallback_candidates, limit=5)
        if not ranked:
            return ResolverResult(
                status=ResolutionStatus.not_found,
                resolved_path=None,
                confidence=0.0,
                candidates=[],
                attempt_log=attempt_log,
                telemetry=self._telemetry(
                    strategy="list_all_not_found",
                    attempt_log=attempt_log,
                    fallback_activated=True,
                    candidate_count=0,
                    confidence=0.0,
                    hint_used=bool(normalized_hint),
                    cache_hit=False,
                ),
            )

        top = ranked[0]
        # Strict disambiguation mode: require explicit user choice when more
        # than one candidate is available.
        if len(ranked) == 1:
            self._store_cache(cache_key, top.connection_path)
            return ResolverResult(
                status=ResolutionStatus.resolved,
                resolved_path=top.connection_path,
                confidence=round(min(top.score, 0.99), 2),
                candidates=ranked,
                attempt_log=attempt_log,
                telemetry=self._telemetry(
                    strategy="list_all_single_candidate",
                    attempt_log=attempt_log,
                    fallback_activated=True,
                    candidate_count=len(ranked),
                    confidence=round(min(top.score, 0.99), 2),
                    hint_used=bool(normalized_hint),
                    cache_hit=False,
                ),
            )

        return ResolverResult(
            status=ResolutionStatus.ambiguous,
            resolved_path=None,
            confidence=round(top.score, 2),
            candidates=ranked,
            attempt_log=attempt_log,
            telemetry=self._telemetry(
                strategy="list_all_ambiguous",
                attempt_log=attempt_log,
                fallback_activated=True,
                candidate_count=len(ranked),
                confidence=round(top.score, 2),
                hint_used=bool(normalized_hint),
                cache_hit=False,
            ),
        )

    def _store_cache(self, key: str, path: str) -> None:
        if not self._enable_cache or self._cache_ttl_seconds <= 0:
            return
        self._cache[key] = _CacheEntry(path=path, expires_at=self._now_fn() + self._cache_ttl_seconds)

    def _telemetry(
        self,
        *,
        strategy: str,
        attempt_log: list[str],
        fallback_activated: bool,
        candidate_count: int,
        confidence: float,
        hint_used: bool,
        cache_hit: bool,
    ) -> dict[str, Any]:
        telemetry: dict[str, Any] = {
            "strategy": strategy,
            "attempts_count": len(attempt_log),
            "fallback_activated": fallback_activated,
            "candidate_count": candidate_count,
            "confidence": confidence,
            "hint_used": hint_used,
            "cache_hit": cache_hit,
        }
        if self._debug_telemetry:
            telemetry["attempt_log"] = list(attempt_log)
            telemetry["cache_size"] = len(self._cache)
            telemetry["cache_ttl_seconds"] = self._cache_ttl_seconds
        return telemetry


def _split_words(raw: str) -> list[str]:
    spaced = _CAMEL_BOUNDARY_RE.sub(r"\1 \2", raw)
    normalized = _NON_ALNUM_RE.sub(" ", spaced).strip()
    if not normalized:
        return []
    return [token for token in normalized.split(" ") if token]


def _tokenize(raw: str) -> list[str]:
    return [token.lower() for token in _split_words(raw)]


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _flatten_by_type(by_type: dict[str, Any]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for variable_type, entries in by_type.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            item = dict(entry)
            item.setdefault("variable_type", variable_type)
            flattened.append(item)
    return flattened


def _extract_page_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("variables", "items", "entries"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _score_candidate(
    normalized_query: str,
    query_tokens: list[str],
    candidate_name: str,
    connection_path: str,
) -> tuple[float, str]:
    name_tokens = _tokenize(candidate_name)
    path_tokens = _tokenize(connection_path)

    if not name_tokens and not path_tokens:
        return 0.0, "missing searchable tokens"

    normalized_name = " ".join(name_tokens)
    normalized_path = " ".join(path_tokens)

    if normalized_name == normalized_query:
        return 1.0, "exact name token match"

    if normalized_query in normalized_name:
        return 0.92, "name contains full query"

    if normalized_query in normalized_path:
        return 0.82, "path contains full query"

    query_set = set(query_tokens)
    name_overlap = len(query_set.intersection(name_tokens))
    path_overlap = len(query_set.intersection(path_tokens))

    if name_overlap == 0 and path_overlap == 0:
        return 0.0, "no overlapping tokens"

    # Keep this lightweight and deterministic for Phase 1.
    token_score = (name_overlap * 2 + path_overlap) / (len(query_set) * 2)
    score = min(0.79, 0.4 + token_score * 0.39)
    return score, "token overlap"


def _extract_connection_path(found_result: dict[str, Any]) -> str | None:
    identifier = found_result.get("identifier")
    if isinstance(identifier, dict):
        path = identifier.get("connection_path") or identifier.get("path")
        if isinstance(path, str) and path.strip():
            return path

    name = found_result.get("name")
    if isinstance(name, str) and is_connection_path(name):
        return name
    return None


def _cache_key(raw: str) -> str:
    return " ".join(_tokenize(raw))


def _parse_dspace_tail(instrument_name: str) -> str | None:
    match = _DSPACE_INSTRUMENT_TAIL_RE.match(instrument_name.strip())
    if not match:
        return None
    tail = match.group(1).strip()
    return tail or None
