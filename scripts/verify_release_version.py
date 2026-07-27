"""Validate that a release tag matches package metadata and runtime versions."""

from __future__ import annotations

import argparse
import importlib
import re
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
TAG_PREFIX = "v"


def version_from_tag(tag: str) -> str:
    """Return a version from a release tag, accepting an optional v prefix."""
    version = tag.removeprefix(TAG_PREFIX)
    if not version or not re.fullmatch(r"\d+\.\d+\.\d+(?:[.-][0-9A-Za-z.-]+)?", version):
        raise ValueError(f"Release tag must contain a semantic version: {tag!r}")
    return version


def project_version(pyproject_path: Path) -> str:
    """Read the declared package version without requiring build dependencies."""
    with pyproject_path.open("rb") as pyproject_file:
        project = tomllib.load(pyproject_file)["project"]
    return str(project["version"])


def runtime_versions() -> dict[str, str]:
    """Read the version constant from the canonical import path."""
    sys.path.insert(0, str(PROJECT_ROOT))
    return {
        module_name: str(importlib.import_module(module_name).__version__)
        for module_name in ("controldesk_mcp",)
    }


def validate_release(
    tag: str, pyproject_path: Path = PYPROJECT_PATH, changelog_path: Path = CHANGELOG_PATH
) -> None:
    """Raise ValueError unless tag, package metadata, runtime, and changelog agree."""
    expected_version = version_from_tag(tag)
    versions = {"pyproject.toml": project_version(pyproject_path), **runtime_versions()}
    mismatches = [
        f"{source}={version}" for source, version in versions.items() if version != expected_version
    ]
    if mismatches:
        raise ValueError(f"Release version mismatch for {tag}: {', '.join(mismatches)}")

    changelog = changelog_path.read_text(encoding="utf-8")
    if f"## [{expected_version}]" not in changelog:
        raise ValueError(f"CHANGELOG.md does not contain a section for {expected_version}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Release tag, for example v0.1.0")
    arguments = parser.parse_args()

    try:
        validate_release(arguments.tag)
    except (KeyError, OSError, ValueError) as error:
        print(f"Release validation failed: {error}", file=sys.stderr)
        return 1

    print(f"Release validation passed for {arguments.tag}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
