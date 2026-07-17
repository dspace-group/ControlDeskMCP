#!/usr/bin/env bash
set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is not available on PATH."
  echo "Install: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

uv sync --extra dev
uv run ruff check sources tests
uv run black --check sources tests
uv run python scripts/validate_mcp_tools.py
uv run pytest tests/unit/ -q -m "not integration"

echo "Quality gate passed."
