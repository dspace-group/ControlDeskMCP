"""Core analysis engine.

Converts raw MCP tool objects into structured ToolMetrics and assembles the
final BenchmarkReport including domain aggregation and context-budget analysis.

How tool schemas map to LLM context
-------------------------------------
When an LLM client discovers MCP tools it receives a tools/list response.
Each tool entry is serialised to JSON and injected into the model's context
window alongside the conversation.  The token cost of the whole tool list is
therefore the sum of each individual tool's serialised JSON token count.

This module serialises each tool to compact JSON (no extra whitespace) and
measures that string with the caller-supplied TokenCounter.  Individual field
slices (name, description, inputSchema, outputSchema, annotations) are counted
separately so the reporter can show where tokens come from.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .models import BenchmarkReport, DomainMetrics, ToolMetrics
from .tokenizer import TokenCounter

# Reference context windows used for budget analysis.
# Values are in tokens.
_CONTEXT_WINDOWS: dict[str, int] = {
    "Claude Sonnet / Opus (200k)": 200_000,
    "GPT-4 Turbo / GPT-4o (128k)": 128_000,
    "Gemini 1.5 Pro (1M)": 1_000_000,
    "GitHub Copilot tool budget (~8k)": 8_000,
    "GitHub Copilot tool budget (~32k)": 32_000,
    "Typical 10 % tool budget of 200k": 20_000,
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _to_dict(tool: Any) -> dict:
    return tool.model_dump(mode="json") if hasattr(tool, "model_dump") else dict(tool)


def _compact(obj: Any) -> str:
    """Compact JSON string with no extra whitespace."""
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _serialize_tool(data: dict) -> str:
    """Produce the compact JSON representation that an LLM client transmits.

    Fields with None values and implementation-internal fields (icons,
    execution) are dropped — they are not meaningful to the model.
    """
    clean = {k: v for k, v in data.items() if v is not None and k not in ("icons", "execution")}
    return _compact(clean)


def _count_params(input_schema: dict | None) -> tuple[int, int]:
    if not input_schema:
        return 0, 0

    props = input_schema.get("properties") or {}
    defs = input_schema.get("$defs") or {}

    # FastMCP wraps Pydantic models as a single 'params' property with a $ref.
    # Unwrap one level to count the actual input parameters.
    if len(props) == 1 and "params" in props and defs:
        ref = (props["params"] or {}).get("$ref", "")
        model_name = ref.split("/")[-1] if ref else ""
        if model_name in defs:
            nested = defs[model_name]
            return len(nested.get("properties") or {}), len(nested.get("required") or [])

    return len(props), len(input_schema.get("required") or [])


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class MCPBenchmarkAnalyzer:
    """Produces a BenchmarkReport from a list of raw MCP Tool objects."""

    def __init__(self, counter: TokenCounter) -> None:
        self._ct = counter

    # ------------------------------------------------------------------
    # Per-tool analysis
    # ------------------------------------------------------------------

    def analyze_tool(self, tool: Any) -> ToolMetrics:
        data = _to_dict(tool)

        name: str = data.get("name") or ""
        description: str = data.get("description") or ""
        input_schema: dict = data.get("inputSchema") or {}
        output_schema: dict | None = data.get("outputSchema")
        annotations: dict | None = data.get("annotations")
        meta: dict = data.get("meta") or {}

        schema_json = _serialize_tool(data)
        schema_bytes = len(schema_json.encode("utf-8"))
        param_count, req_count = _count_params(input_schema)

        ct = self._ct.count

        return ToolMetrics(
            name=name,
            domain=meta.get("domain"),
            group=meta.get("group"),
            description=description,
            schema_json=schema_json,
            schema_bytes=schema_bytes,
            total_tokens=ct(schema_json),
            name_tokens=ct(name),
            description_tokens=ct(description),
            input_schema_tokens=ct(_compact(input_schema)) if input_schema else 0,
            output_schema_tokens=ct(_compact(output_schema)) if output_schema else 0,
            annotation_tokens=ct(_compact(annotations)) if annotations else 0,
            total_tokens_heuristic=max(1, len(schema_json) // 4),
            param_count=param_count,
            required_param_count=req_count,
            has_output_schema=output_schema is not None,
        )

    # ------------------------------------------------------------------
    # Full report assembly
    # ------------------------------------------------------------------

    def build_report(self, server_name: str, tools: list[Any]) -> BenchmarkReport:
        tool_metrics = [self.analyze_tool(t) for t in tools]

        # --- domain aggregation ---
        domain_map: dict[str, list[ToolMetrics]] = {}
        for tm in tool_metrics:
            key = tm.domain or "unclassified"
            domain_map.setdefault(key, []).append(tm)

        domain_metrics: list[DomainMetrics] = []
        for domain, tms in sorted(domain_map.items()):
            tok_list = [tm.total_tokens for tm in tms]
            heaviest = max(tms, key=lambda t: t.total_tokens)
            domain_metrics.append(
                DomainMetrics(
                    domain=domain,
                    tool_count=len(tms),
                    total_tokens=sum(tok_list),
                    avg_tokens=sum(tok_list) / len(tok_list),
                    min_tokens=min(tok_list),
                    max_tokens=max(tok_list),
                    top_tool=heaviest.name,
                )
            )

        total_tokens = sum(tm.total_tokens for tm in tool_metrics)
        total_bytes = sum(tm.schema_bytes for tm in tool_metrics)

        # --- context budget ---
        context_budget: dict[str, dict] = {}
        for label, window in _CONTEXT_WINDOWS.items():
            pct = (total_tokens / window) * 100
            context_budget[label] = {
                "window_tokens": window,
                "consumed_tokens": total_tokens,
                "pct": round(pct, 1),
                "remaining_tokens": max(0, window - total_tokens),
            }

        return BenchmarkReport(
            server_name=server_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tokenizer_used=self._ct.name,
            total_tools=len(tool_metrics),
            total_tokens=total_tokens,
            total_bytes=total_bytes,
            tools=tool_metrics,
            domains=domain_metrics,
            context_budget=context_budget,
        )
