"""CLI entry point for the MCP token benchmark tool.

Usage examples
--------------
  python -m benchmark analyze
  python -m benchmark analyze --top 30 --sort-by tokens
  python -m benchmark analyze --domain platform --format markdown --output report.md
  python -m benchmark analyze --format json --output report.json
  python -m benchmark inspect health
  python -m benchmark diff old_report.json new_report.json
  python -m benchmark domains
"""

from __future__ import annotations

import sys

import click

from .analyzer import MCPBenchmarkAnalyzer
from .loader import load_tools_sync
from .tokenizer import create_counter


# ---------------------------------------------------------------------------
# Shared context object
# ---------------------------------------------------------------------------


class _Ctx:
    tokenizer: str = "gpt2"  # "gpt2" | "heuristic"


pass_ctx = click.make_pass_decorator(_Ctx, ensure=True)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--tokenizer",
    type=click.Choice(["gpt2", "heuristic"]),
    default="gpt2",
    show_default=True,
    help="Token counting strategy.  'gpt2' uses the cached GPT-2 BPE tokenizer; "
    "'heuristic' divides character count by 4.",
)
@click.pass_context
def cli(ctx: click.Context, tokenizer: str) -> None:
    """MCP Token Benchmark — measure context-window cost of MCP tool schemas.

    Analyses the ControlDesk MCP server without running it or requiring API keys.
    Token counts are approximations (see BENCHMARK.md for methodology).
    """
    obj = ctx.ensure_object(_Ctx)
    obj.tokenizer = tokenizer


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


@cli.command()
@click.option("--top", default=20, show_default=True, help="Number of tools to list.")
@click.option(
    "--sort-by",
    "sort_by",
    type=click.Choice(["tokens", "name", "bytes", "params", "description", "input-schema", "output-schema"]),
    default="tokens",
    show_default=True,
    help="Column to sort the tool table by.",
)
@click.option("--domain", default=None, help="Filter tool table to a specific domain.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["console", "json", "markdown"]),
    default="console",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    help="File path for json/markdown output.  Defaults to benchmark_report.{ext}.",
)
@pass_ctx
def analyze(
    ctx: _Ctx,
    top: int,
    sort_by: str,
    domain: str | None,
    fmt: str,
    output_path: str | None,
) -> None:
    """Analyse all MCP tools and report token consumption."""
    counter = create_counter(prefer_gpt2=(ctx.tokenizer == "gpt2"))
    click.echo(f"Loading tools  (tokenizer: {counter.name}) …", err=True)

    try:
        server_name, tools = load_tools_sync()
    except Exception as exc:
        click.secho(f"ERROR: Could not load MCP server tools — {exc}", fg="red", err=True)
        sys.exit(1)

    click.echo(f"Analysing {len(tools)} tools …", err=True)
    analyzer = MCPBenchmarkAnalyzer(counter)
    report = analyzer.build_report(server_name, tools)

    if fmt == "console":
        from .reporter.console import print_report

        print_report(report, top_n=top, sort_by=sort_by, domain_filter=domain)

    elif fmt == "json":
        from .reporter.json_reporter import save

        path = output_path or "benchmark_report.json"
        save(report, path)
        click.secho(f"Report saved → {path}", fg="green")

    elif fmt == "markdown":
        from .reporter.markdown import save

        path = output_path or "benchmark_report.md"
        save(report, path, top_n=top)
        click.secho(f"Report saved → {path}", fg="green")


# ---------------------------------------------------------------------------
# inspect
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("tool_name")
@pass_ctx
def inspect(ctx: _Ctx, tool_name: str) -> None:
    """Show full schema and token breakdown for a single tool."""
    import json

    counter = create_counter(prefer_gpt2=(ctx.tokenizer == "gpt2"))

    try:
        _, tools = load_tools_sync()
    except Exception as exc:
        click.secho(f"ERROR: {exc}", fg="red", err=True)
        sys.exit(1)

    match = next((t for t in tools if t.name == tool_name), None)
    if match is None:
        names = sorted(t.name for t in tools)
        click.secho(f"Tool '{tool_name}' not found.", fg="red")
        # suggest close matches
        candidates = [n for n in names if tool_name.lower() in n.lower()][:5]
        if candidates:
            click.echo("Did you mean one of: " + ", ".join(candidates))
        sys.exit(1)

    analyzer = MCPBenchmarkAnalyzer(counter)
    m = analyzer.analyze_tool(match)

    click.secho(f"\nTool: {m.name}", fg="cyan", bold=True)
    click.echo(f"  Domain            : {m.domain or '—'}")
    click.echo(f"  Group             : {m.group or '—'}")
    click.echo(f"  Total tokens      : {m.total_tokens}  (heuristic: {m.total_tokens_heuristic})")
    click.echo(f"  Name tokens       : {m.name_tokens}")
    click.echo(f"  Description tokens: {m.description_tokens}")
    click.echo(f"  Input schema tokens: {m.input_schema_tokens}")
    click.echo(f"  Output schema tok. : {m.output_schema_tokens}")
    click.echo(f"  Annotation tokens : {m.annotation_tokens}")
    click.echo(f"  Schema bytes      : {m.schema_bytes} B")
    click.echo(f"  Param count       : {m.param_count} ({m.required_param_count} required)")
    click.echo(f"\nFull schema JSON:\n")
    click.echo(json.dumps(json.loads(m.schema_json), indent=2))


# ---------------------------------------------------------------------------
# domains
# ---------------------------------------------------------------------------


@cli.command()
@pass_ctx
def domains(ctx: _Ctx) -> None:
    """List all domains and their tool counts."""
    from tabulate import tabulate

    counter = create_counter(prefer_gpt2=(ctx.tokenizer == "gpt2"))

    try:
        server_name, tools = load_tools_sync()
    except Exception as exc:
        click.secho(f"ERROR: {exc}", fg="red", err=True)
        sys.exit(1)

    analyzer = MCPBenchmarkAnalyzer(counter)
    report = analyzer.build_report(server_name, tools)

    rows = [
        [d.domain, d.tool_count, f"{d.total_tokens:,}", f"{d.avg_tokens:.0f}", d.top_tool[:40]]
        for d in sorted(report.domains, key=lambda d: d.total_tokens, reverse=True)
    ]
    click.echo(
        tabulate(rows, headers=["Domain", "Tools", "Total Tokens", "Avg Tokens", "Heaviest Tool"], tablefmt="simple")
    )


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


@cli.command()
@click.argument("old_report", type=click.Path(exists=True))
@click.argument("new_report", type=click.Path(exists=True))
def diff(old_report: str, new_report: str) -> None:
    """Compare two saved JSON reports and show token deltas.

    OLD_REPORT and NEW_REPORT must be JSON files produced by
    'analyze --format json'.
    """
    from tabulate import tabulate
    from .reporter.json_reporter import load

    old = load(old_report)
    new = load(new_report)

    old_map = {t.name: t for t in old.tools}
    new_map = {t.name: t for t in new.tools}

    added = sorted(set(new_map) - set(old_map))
    removed = sorted(set(old_map) - set(new_map))
    changed = sorted(
        n for n in set(old_map) & set(new_map)
        if old_map[n].total_tokens != new_map[n].total_tokens
    )

    click.secho(f"\nDiff: {old_report}  →  {new_report}", bold=True)
    click.echo(f"  Old total: {old.total_tokens:,} tokens  ({old.total_tools} tools)")
    click.echo(f"  New total: {new.total_tokens:,} tokens  ({new.total_tools} tools)")
    delta = new.total_tokens - old.total_tokens
    color = "red" if delta > 0 else "green"
    click.secho(f"  Delta    : {delta:+,} tokens", fg=color)

    if added:
        click.secho(f"\nAdded ({len(added)} tools):", fg="green")
        click.echo("  " + ", ".join(added))

    if removed:
        click.secho(f"\nRemoved ({len(removed)} tools):", fg="red")
        click.echo("  " + ", ".join(removed))

    if changed:
        click.secho(f"\nChanged ({len(changed)} tools):", fg="yellow")
        rows = []
        for name in changed:
            old_t = old_map[name]
            new_t = new_map[name]
            d = new_t.total_tokens - old_t.total_tokens
            rows.append([name, old_t.total_tokens, new_t.total_tokens, f"{d:+}"])
        click.echo(tabulate(rows, headers=["Tool", "Old Tokens", "New Tokens", "Δ"], tablefmt="simple"))

    click.echo()
