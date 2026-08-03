"""Markdown reporter — generates a human-readable .md benchmark report."""

from __future__ import annotations

from pathlib import Path

from ..models import BenchmarkReport


def _progress(pct: float, width: int = 20) -> str:
    filled = int(min(pct / 100, 1.0) * width)
    return "█" * filled + "░" * (width - filled) + f" {pct:.1f}%"


def save(report: BenchmarkReport, output_path: str, top_n: int = 30) -> None:
    """Write a Markdown report to *output_path*."""
    lines: list[str] = []

    # --- Title & metadata ---
    lines += [
        f"# MCP Token Benchmark — {report.server_name}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Generated | {report.timestamp} |",
        f"| Tokenizer | `{report.tokenizer_used}` (approximation) |",
        f"| Total tools | {report.total_tools} |",
        f"| Total tokens (approx) | {report.total_tokens:,} |",
        f"| Total schema size | {report.total_bytes / 1024:.1f} KB |",
        "",
    ]

    # --- Context budget ---
    lines += [
        "## Context Window Budget",
        "",
        "How much of each model's context window the full tool list consumes.",
        "",
        "| Model | Window | Tool Tokens | Remaining | Usage |",
        "|---|---|---|---|---|",
    ]
    for model, info in report.context_budget.items():
        bar = _progress(info["pct"])
        lines.append(
            f"| {model} | {info['window_tokens']:,} | {info['consumed_tokens']:,}"
            f" | {info['remaining_tokens']:,} | `{bar}` |"
        )
    lines.append("")

    # --- Domain breakdown ---
    lines += [
        "## Domain Breakdown",
        "",
        "| Domain | Tools | Total Tokens | Avg Tokens | Min | Max | Heaviest Tool |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in sorted(report.domains, key=lambda x: x.total_tokens, reverse=True):
        lines.append(
            f"| {d.domain} | {d.tool_count} | {d.total_tokens:,} | {d.avg_tokens:.0f}"
            f" | {d.min_tokens} | {d.max_tokens} | `{d.top_tool}` |"
        )
    lines.append("")

    # --- Top N tools ---
    top = sorted(report.tools, key=lambda t: t.total_tokens, reverse=True)[:top_n]
    lines += [
        f"## Top {len(top)} Tools by Token Count",
        "",
        "| # | Tool | Domain | Tokens | Desc | InSchema | OutSchema | Params | Bytes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for i, t in enumerate(top, 1):
        lines.append(
            f"| {i} | `{t.name}` | {t.domain or '-'} | {t.total_tokens}"
            f" | {t.description_tokens} | {t.input_schema_tokens}"
            f" | {t.output_schema_tokens} | {t.param_count} | {t.schema_bytes} |"
        )
    lines.append("")

    # --- Statistical summary ---
    all_tokens = sorted(t.total_tokens for t in report.tools)
    n = len(all_tokens)
    if n:
        avg = sum(all_tokens) / n
        p50 = all_tokens[n // 2]
        p90 = all_tokens[max(0, n // 10)]
        by_tok = sorted(report.tools, key=lambda t: t.total_tokens, reverse=True)
        lines += [
            "## Statistical Summary",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Average tokens / tool | {avg:.0f} |",
            f"| Median (p50) | {p50} |",
            f"| 90th percentile (p90) | {p90} |",
            f"| Largest tool | `{by_tok[0].name}` ({by_tok[0].total_tokens} tokens) |",
            f"| Smallest tool | `{by_tok[-1].name}` ({by_tok[-1].total_tokens} tokens) |",
            f"| Tools with outputSchema | {sum(1 for t in report.tools if t.has_output_schema)} |",
            "",
        ]

    # --- Methodology note ---
    lines += [
        "## Methodology",
        "",
        "Token counts are **approximations** produced by the `gpt2_bpe` tokenizer",
        "(or a char/4 heuristic fallback).  Claude uses a proprietary tokenizer;",
        "actual counts may differ by ±10–20%.  The relative ordering between tools",
        "is reliable for optimisation decisions even if absolute numbers are not exact.",
        "",
        "Each tool is serialised to compact JSON (the format transmitted in a",
        "`tools/list` MCP response) and that string is tokenised.",
        "Fields `icons` and `execution` are excluded as they are not sent to the LLM.",
        "",
    ]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
