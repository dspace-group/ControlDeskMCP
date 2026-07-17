"""Enables running the benchmark as a module: python -m benchmark [command]."""

import sys

# Ensure stdout/stderr use UTF-8 on Windows (default console is CP1252).
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from benchmark.cli import cli

if __name__ == "__main__":
    cli()
