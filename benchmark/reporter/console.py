"""Console reporter — pretty-prints the benchmark report using click + tabulate."""

from __future__ import annotations

import click
from tabulate import tabulate

from ..models import BenchmarkReport, DomainMetrics, ToolMetrics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _progress_bar(pct: float, width: int = 24) -> str:
    filled = int(min(pct / 100, 1.0) * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct:5.1f}%"


def _color_pct(pct: float) -> str:
    bar = _progress_bar(pct)
    color = "red" if pct > 50 else "yellow" if pct > 15 else "green"
    return click.style(bar, fg=color)


def _sep(width: int = 72, color: str = "cyan") -> None:
    click.secho("─" * width, fg=color)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def print_report(
    report: BenchmarkReport,
    top_n: int = 20,
    sort_by: str = "tokens",
    domain_filter: str | None = None,
) -> None:
    """Print the full benchmark report to stdout."""

    tools = report.tools
    if domain_filter:
        tools = [t for t in tools if (t.domain or "").lower() == domain_filter.lower()]

    _print_header(report)
    _print_context_budget(report)
    _print_domain_breakdown(report)
    _print_top_tools(tools, top_n=top_n, sort_by=sort_by)
    _print_stats(report.tools)  # stats always over full set


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def _print_header(report: BenchmarkReport) -> None:
    _sep(color="cyan")
    click.secho(f"  MCP Token Benchmark  —  {report.server_name}", fg="cyan", bold=True)
    _sep(color="cyan")
    click.echo(f"  Timestamp    : {report.timestamp}")
    click.echo(f"  Tokenizer    : {report.tokenizer_used}  (approximation — see BENCHMARK.md)")
    click.echo(f"  Total Tools  : {report.total_tools}")
    click.echo(f"  Total Tokens : {report.total_tokens:,}  (approx)")
    click.echo(f"  Total Size   : {report.total_bytes / 1024:.1f} KB")
    click.echo()


def _print_context_budget(report: BenchmarkReport) -> None:
    _sep(color="yellow")
    click.secho("  Context Window Budget", fg="yellow", bold=True)
    click.secho(
        "  (How much of each model's context window the tool schemas consume)", fg="yellow"
    )
    _sep(color="yellow")

    rows = []
    for model, info in report.context_budget.items():
        bar = _color_pct(info["pct"])
        rows.append(
            [
                model,
                f"{info['window_tokens']:,}",
                f"{info['consumed_tokens']:,}",
                f"{info['remaining_tokens']:,}",
                bar,
            ]
        )

    click.echo(
        tabulate(
            rows,
            headers=["Model", "Window", "Tool Tokens", "Remaining", "Usage"],
            tablefmt="simple",
        )
    )
    click.echo()


def _print_domain_breakdown(report: BenchmarkReport) -> None:
    _sep(color="green")
    click.secho("  Domain Breakdown", fg="green", bold=True)
    _sep(color="green")

    sorted_domains: list[DomainMetrics] = sorted(
        report.domains, key=lambda d: d.total_tokens, reverse=True
    )
    rows = []
    for d in sorted_domains:
        rows.append(
            [
                d.domain,
                d.tool_count,
                f"{d.total_tokens:,}",
                f"{d.avg_tokens:.0f}",
                d.min_tokens,
                d.max_tokens,
                d.top_tool[:35],
            ]
        )

    click.echo(
        tabulate(
            rows,
            headers=["Domain", "Tools", "Total Tokens", "Avg", "Min", "Max", "Heaviest Tool"],
            tablefmt="simple",
        )
    )
    click.echo()


def _print_top_tools(tools: list[ToolMetrics], top_n: int, sort_by: str) -> None:
    _sort_key = {
        "tokens": lambda t: t.total_tokens,
        "name": lambda t: t.name,
        "bytes": lambda t: t.schema_bytes,
        "params": lambda t: t.param_count,
        "description": lambda t: t.description_tokens,
        "input-schema": lambda t: t.input_schema_tokens,
        "output-schema": lambda t: t.output_schema_tokens,
    }.get(sort_by, lambda t: t.total_tokens)

    reverse = sort_by != "name"
    sorted_tools = sorted(tools, key=_sort_key, reverse=reverse)
    top = sorted_tools[:top_n]

    _sep(color="magenta")
    click.secho(
        f"  Top {min(top_n, len(top))} Tools  (sorted by: {sort_by})", fg="magenta", bold=True
    )
    _sep(color="magenta")

    rows = []
    for i, t in enumerate(top, 1):
        rows.append(
            [
                i,
                t.name[:38],
                t.domain or "-",
                t.total_tokens,
                t.description_tokens,
                t.input_schema_tokens,
                t.output_schema_tokens,
                t.param_count,
                f"{t.schema_bytes} B",
            ]
        )

    click.echo(
        tabulate(
            rows,
            headers=["#", "Tool", "Domain", "Tokens", "Desc", "InSchema", "OutSchema", "Params", "Bytes"],
            tablefmt="simple",
        )
    )
    click.echo()


def _print_stats(tools: list[ToolMetrics]) -> None:
    if not tools:
        return

    _sep(color="white")
    click.secho("  Statistical Summary  (full tool set)", fg="white", bold=True)
    _sep(color="white")

    by_tok = sorted(tools, key=lambda t: t.total_tokens, reverse=True)
    n = len(by_tok)
    p50 = by_tok[n // 2].total_tokens
    p90 = by_tok[max(0, n // 10)].total_tokens
    avg = sum(t.total_tokens for t in tools) / n

    click.echo(f"  Average tokens / tool : {avg:.0f}")
    click.echo(f"  Median  (p50)         : {p50}")
    click.echo(f"  90th percentile (p90) : {p90}")
    click.echo(f"  Largest  : {by_tok[0].name}  ({by_tok[0].total_tokens} tokens)")
    click.echo(f"  Smallest : {by_tok[-1].name}  ({by_tok[-1].total_tokens} tokens)")

    tools_with_out = sum(1 for t in tools if t.has_output_schema)
    click.echo(f"  Tools with outputSchema : {tools_with_out} / {n}")
    click.echo()
