"""Data models for benchmark results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolMetrics:
    """Token and size metrics for a single MCP tool."""

    name: str
    domain: str | None
    group: str | None
    description: str

    # Raw size
    schema_json: str
    schema_bytes: int

    # Token counts (primary tokenizer)
    total_tokens: int
    name_tokens: int
    description_tokens: int
    input_schema_tokens: int
    output_schema_tokens: int
    annotation_tokens: int

    # Token count via char/4 heuristic (secondary estimate)
    total_tokens_heuristic: int

    # Schema complexity
    param_count: int
    required_param_count: int
    has_output_schema: bool


@dataclass
class DomainMetrics:
    """Aggregated metrics for all tools in a domain."""

    domain: str
    tool_count: int
    total_tokens: int
    avg_tokens: float
    min_tokens: int
    max_tokens: int
    top_tool: str  # name of the heaviest tool in this domain


@dataclass
class BenchmarkReport:
    """Complete benchmark report for an MCP server."""

    server_name: str
    timestamp: str
    tokenizer_used: str

    total_tools: int
    total_tokens: int
    total_bytes: int

    tools: list[ToolMetrics] = field(default_factory=list)
    domains: list[DomainMetrics] = field(default_factory=list)

    # Per context-window budget analysis
    # key = model label, value = {window_tokens, consumed_tokens, pct, remaining_tokens}
    context_budget: dict[str, dict] = field(default_factory=dict)
