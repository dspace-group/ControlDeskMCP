"""Unit tests for controldesk_mcp.services.variable_path_resolver."""

from __future__ import annotations

import pytest

from controldesk_mcp.services.variable_path_resolver import (
    ResolutionStatus,
    VariablePathResolver,
    collect_list_all_candidates,
    extract_instrument_tail_hint,
    generate_name_variants,
    rank_candidates,
)


def test_generate_name_variants_order_and_dedup() -> None:
    variants = generate_name_variants("air mass flow")
    assert variants == [
        "AirMassFlow",
        "airMassFlow",
        "air_mass_flow",
        "AIR_MASS_FLOW",
        "Air Mass Flow",
        "AIR MASS FLOW",
        "air mass flow",
        "air-mass-flow",
    ]


def test_generate_name_variants_handles_camel_case_input() -> None:
    variants = generate_name_variants("AirMassFlow")
    assert variants[0] == "AirMassFlow"
    assert variants[1] == "airMassFlow"
    assert "air_mass_flow" in variants


def test_rank_candidates_prefers_exact_name_match() -> None:
    candidates = [
        {"name": "air_mass", "connection_path": "XCP()://air_mass"},
        {"name": "air_mass_flow", "connection_path": "XCP()://air_mass_flow"},
        {"name": "mass_air", "connection_path": "XCP()://mass_air"},
    ]
    ranked = rank_candidates("air mass", candidates, limit=3)
    assert ranked[0].name == "air_mass"
    assert ranked[0].score == 1.0
    assert ranked[1].score >= ranked[2].score


@pytest.mark.asyncio
async def test_collect_list_all_candidates_supports_grouped_payload() -> None:
    async def _fetch_page(offset: int, limit: int) -> dict:
        assert offset == 0
        assert limit == 500
        return {
            "total_count": 2,
            "by_type": {
                "Parameter": [{"name": "f_Kp_1", "connection_path": "XCP()://f_Kp_1"}],
                "Measurement": [{"name": "control_out", "connection_path": "XCP(5ms)://control_out"}],
            },
        }

    items, attempt_log = await collect_list_all_candidates(_fetch_page, page_size=500)
    assert len(items) == 2
    assert items[0]["connection_path"] == "XCP()://f_Kp_1"
    assert items[1]["connection_path"] == "XCP(5ms)://control_out"
    assert any("grouped payload" in entry for entry in attempt_log)


@pytest.mark.asyncio
async def test_collect_list_all_candidates_supports_paginated_payload() -> None:
    calls: list[tuple[int, int]] = []

    async def _fetch_page(offset: int, limit: int) -> dict:
        calls.append((offset, limit))
        if offset == 0:
            return {
                "variables": [{"name": "a", "connection_path": "XCP()://a"}],
                "has_more": True,
                "next_offset": 1,
            }
        return {
            "variables": [{"name": "b", "connection_path": "XCP()://b"}],
            "has_more": False,
            "next_offset": None,
        }

    items, _attempt_log = await collect_list_all_candidates(_fetch_page, page_size=1)
    assert calls == [(0, 1), (1, 1)]
    assert [item["name"] for item in items] == ["a", "b"]


@pytest.mark.asyncio
async def test_resolver_returns_resolved_when_find_succeeds() -> None:
    async def _find(identifier: str, search_mode: str | None) -> dict:
        assert search_mode == "name"
        if identifier == "f_Kp_1":
            return {
                "found": True,
                "name": "f_Kp_1",
                "identifier": {"connection_path": "XCP()://f_Kp_1"},
            }
        return {"found": False}

    async def _list_all(_offset: int, _limit: int) -> dict:
        return {"variables": []}

    resolver = VariablePathResolver(_find, _list_all)
    result = await resolver.resolve("f_Kp_1")
    assert result.status == ResolutionStatus.resolved
    assert result.resolved_path == "XCP()://f_Kp_1"
    assert result.confidence >= 0.9


@pytest.mark.asyncio
async def test_resolver_uses_list_all_fallback_and_preserves_path_verbatim() -> None:
    async def _find(_identifier: str, _search_mode: str | None) -> dict:
        return {"found": False}

    async def _list_all(_offset: int, _limit: int) -> dict:
        return {
            "by_type": {
                "Measurement": [
                    {
                        "name": "control_out",
                        "connection_path": "XCP(5ms)://control_out[0]{sig}",
                    }
                ]
            }
        }

    resolver = VariablePathResolver(_find, _list_all)
    result = await resolver.resolve("control out")
    assert result.status == ResolutionStatus.resolved
    assert result.resolved_path == "XCP(5ms)://control_out[0]{sig}"


@pytest.mark.asyncio
async def test_resolver_returns_ambiguous_for_close_scores() -> None:
    async def _find(_identifier: str, _search_mode: str | None) -> dict:
        return {"found": False}

    async def _list_all(_offset: int, _limit: int) -> dict:
        return {
            "variables": [
                {"name": "air_mass_front", "connection_path": "XCP()://air_mass_front"},
                {"name": "air_mass_rear", "connection_path": "XCP()://air_mass_rear"},
            ]
        }

    resolver = VariablePathResolver(_find, _list_all)
    result = await resolver.resolve("air mass")
    assert result.status == ResolutionStatus.ambiguous
    assert result.resolved_path is None
    assert len(result.candidates) >= 2


@pytest.mark.asyncio
async def test_resolver_requires_user_pick_when_multiple_candidates_exist() -> None:
    async def _find(_identifier: str, _search_mode: str | None) -> dict:
        return {"found": False}

    async def _list_all(_offset: int, _limit: int) -> dict:
        return {
            "variables": [
                {"name": "control_out", "connection_path": "XCP(5ms)://control_out"},
                {"name": "control_out_filtered", "connection_path": "XCP(5ms)://control_out_filtered"},
            ]
        }

    resolver = VariablePathResolver(_find, _list_all)
    result = await resolver.resolve("control out")

    assert result.status == ResolutionStatus.ambiguous
    assert result.resolved_path is None
    assert len(result.candidates) == 2


def test_extract_instrument_tail_hint_from_dspace_name() -> None:
    hint = extract_instrument_tail_hint(
        "dSPACE Data Measurements air_mass",
        [
            "dSPACE Data Measurements air_mass",
            "Some Other Instrument",
        ],
    )
    assert hint == "air_mass"


def test_extract_instrument_tail_hint_from_partial_phrase_overlap() -> None:
    hint = extract_instrument_tail_hint(
        "please add air mass signal",
        [
            "dSPACE Data Measurements air_mass",
            "dSPACE Data Measurements coolant_temp",
        ],
    )
    assert hint == "air_mass"


@pytest.mark.asyncio
async def test_resolver_uses_hint_variants_for_direct_find() -> None:
    calls: list[str] = []

    async def _find(identifier: str, _search_mode: str | None) -> dict:
        calls.append(identifier)
        if identifier == "air_mass":
            return {
                "found": True,
                "identifier": {"connection_path": "XCP()://air_mass"},
                "name": "air_mass",
            }
        return {"found": False}

    async def _list_all(_offset: int, _limit: int) -> dict:
        return {"variables": []}

    resolver = VariablePathResolver(_find, _list_all)
    result = await resolver.resolve("dSPACE Data Measurements air_mass", hint_query="air_mass")

    assert result.status == ResolutionStatus.resolved
    assert result.resolved_path == "XCP()://air_mass"
    assert "air_mass" in calls


@pytest.mark.asyncio
async def test_resolver_cache_hit_and_expiry() -> None:
    calls: list[str] = []
    now = 100.0

    def _now() -> float:
        return now

    async def _find(identifier: str, _search_mode: str | None) -> dict:
        calls.append(identifier)
        if identifier == "f_Kp_1":
            return {
                "found": True,
                "name": "f_Kp_1",
                "identifier": {"connection_path": "XCP()://f_Kp_1"},
            }
        return {"found": False}

    async def _list_all(_offset: int, _limit: int) -> dict:
        return {"variables": []}

    resolver = VariablePathResolver(_find, _list_all, cache_ttl_seconds=5.0, now_fn=_now)

    first = await resolver.resolve("f_Kp_1")
    assert first.status == ResolutionStatus.resolved
    assert first.telemetry["cache_hit"] is False
    assert len(calls) > 0
    call_count_after_first = len(calls)

    second = await resolver.resolve("f_Kp_1")
    assert second.status == ResolutionStatus.resolved
    assert second.telemetry["cache_hit"] is True
    assert len(calls) == call_count_after_first

    now = 106.0
    third = await resolver.resolve("f_Kp_1")
    assert third.status == ResolutionStatus.resolved
    assert third.telemetry["cache_hit"] is False
    assert "cache expired" in third.attempt_log
    assert len(calls) > call_count_after_first


@pytest.mark.asyncio
async def test_resolver_telemetry_fields_present() -> None:
    async def _find(_identifier: str, _search_mode: str | None) -> dict:
        return {"found": False}

    async def _list_all(_offset: int, _limit: int) -> dict:
        return {"variables": []}

    resolver = VariablePathResolver(_find, _list_all)
    result = await resolver.resolve("unknown variable")

    assert result.status == ResolutionStatus.not_found
    assert result.telemetry["strategy"] == "list_all_not_found"
    assert isinstance(result.telemetry["attempts_count"], int)
    assert result.telemetry["fallback_activated"] is True
    assert result.telemetry["candidate_count"] == 0
    assert result.telemetry["cache_hit"] is False
