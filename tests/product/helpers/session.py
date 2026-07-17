"""Environment variable loading and validation for product tests.

All product tests require a live ControlDesk installation.
LLM-driven (Tier 2) tests additionally require a GitHub token.

Usage in conftest.py:
    from tests.product.helpers.session import require_env, get_model, get_base_url
"""

from __future__ import annotations

import os

import pytest

# ── Required for LLM tests ────────────────────────────────────────────────────

_REQUIRED_LLM_VARS: dict[str, str] = {
    "GITHUB_TOKEN": (
        "GitHub Personal Access Token with 'models:read' permission. "
        "See: https://docs.github.com/en/github-models/use-github-models/prototyping-with-ai-models"
    ),
}

# ── Optional with defaults ────────────────────────────────────────────────────

_DEFAULTS: dict[str, str] = {
    "GITHUB_MODELS_MODEL": "gpt-4.1",
    "GITHUB_MODELS_BASE_URL": "https://models.inference.ai.azure.com",
    "LLM_MAX_ITERATIONS": "15",
    "CONTROLDESK_VERSION": "",
    "COPILOT_MODEL": "gpt-4.1",
    "COPILOT_CLI_PATH": "",
    "COPILOT_GITHUB_TOKEN": "",
}


def require_env(key: str) -> str:
    """Return the env var value or skip the test session with a clear message."""
    val = os.environ.get(key, "").strip()
    if not val:
        hint = _REQUIRED_LLM_VARS.get(key, f"Set the '{key}' environment variable to proceed.")
        pytest.skip(f"Skipping LLM product tests: '{key}' is not set.\n  Hint: {hint}")
    return val


def get_env(key: str, default: str = "") -> str:
    """Return env var or the documented default."""
    return os.environ.get(key, _DEFAULTS.get(key, default)).strip()


def get_model() -> str:
    """LLM model name (default: gpt-4.1 via GitHub Models)."""
    return get_env("GITHUB_MODELS_MODEL")


def get_base_url() -> str:
    """GitHub Models API base URL."""
    return get_env("GITHUB_MODELS_BASE_URL")


def get_max_iterations() -> int:
    """Max agentic loop turns per scenario (default: 15)."""
    return int(get_env("LLM_MAX_ITERATIONS", "15"))


def get_controldesk_version() -> str:
    """ControlDesk version override (e.g. '2026-A'). Empty = auto-detect."""
    return get_env("CONTROLDESK_VERSION", "")


def get_copilot_model() -> str:
    """Model name for Copilot SDK sessions (default: gpt-4.1)."""
    return get_env("COPILOT_MODEL")


def get_copilot_github_token() -> str:
    """Fine-grained PAT with 'Copilot Requests' permission.

    Returns empty string if not set — ``CopilotAgentRunner`` then relies on
    credentials stored by ``copilot login`` (system keychain / ~/.copilot/).

    This is DIFFERENT from ``GITHUB_TOKEN`` (GitHub Models API).  Do not mix
    them up — wrong-scope tokens produce an authentication error in the CLI.
    """
    return get_env("COPILOT_GITHUB_TOKEN", "")


def get_copilot_cli_path() -> str:
    """Absolute path to the copilot CLI binary override.

    Returns empty string if not set — ``CopilotAgentRunner`` then passes
    ``None`` to the SDK, which uses the bundled ``copilot/bin/copilot.exe``
    shipped with the ``github-copilot-sdk`` package automatically.
    """
    return get_env("COPILOT_CLI_PATH", "")
