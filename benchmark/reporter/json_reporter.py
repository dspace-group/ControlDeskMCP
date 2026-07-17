"""JSON reporter — serialises a BenchmarkReport to a JSON file."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from ..models import BenchmarkReport


def save(report: BenchmarkReport, output_path: str) -> None:
    """Write the report as indented JSON to *output_path*."""
    data = dataclasses.asdict(report)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load(input_path: str) -> BenchmarkReport:
    """Deserialise a JSON file previously created by :func:`save`."""
    from ..models import DomainMetrics, ToolMetrics

    raw = json.loads(Path(input_path).read_text(encoding="utf-8"))

    tools = [ToolMetrics(**t) for t in raw.pop("tools", [])]
    domains = [DomainMetrics(**d) for d in raw.pop("domains", [])]
    return BenchmarkReport(**raw, tools=tools, domains=domains)
