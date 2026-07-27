"""Tests for the release version validation script."""

from importlib import util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "verify_release_version.py"


def load_release_validator():
    spec = util.spec_from_file_location("verify_release_version", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_validate_release_accepts_current_version() -> None:
    validator = load_release_validator()

    validator.validate_release("v0.1.0")


def test_validate_release_rejects_mismatched_tag() -> None:
    validator = load_release_validator()

    with pytest.raises(ValueError, match="Release version mismatch"):
        validator.validate_release("v9.9.9")
