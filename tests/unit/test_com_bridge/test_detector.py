"""Unit tests for controldesk_mcp.com_bridge.detector."""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

from controldesk_mcp.com_bridge.detector import (
    _parse_version,
    detect_prog_id,
    is_version_installed,
    normalize_user_version,
    resolve_prog_id,
    version_to_prog_id,
)
from controldesk_mcp.com_bridge.errors import BridgeNotInstalledError

# ── version_to_prog_id ─────────────────────────────────────────────────────────


class TestVersionToProgId:
    def test_converts_version_to_prog_id(self) -> None:
        assert version_to_prog_id("2026-A") == "ControlDeskNG.Application.2026-A"

    def test_lowercases_uppercased(self) -> None:
        assert version_to_prog_id("2025-b") == "ControlDeskNG.Application.2025-B"


# ── _parse_version ─────────────────────────────────────────────────────────────


class TestParseVersion:
    def test_valid_prog_id(self) -> None:
        assert _parse_version("ControlDeskNG.Application.2026-A") == (2026, "A")

    def test_lowercase_letter_normalised(self) -> None:
        year, letter = _parse_version("ControlDeskNG.Application.2025-b")  # type: ignore[misc]
        assert letter == "B"

    def test_base_prog_id_returns_none(self) -> None:
        assert _parse_version("ControlDeskNG.Application") is None

    def test_unrelated_string_returns_none(self) -> None:
        assert _parse_version("SomeOther.ProgID") is None


# ── detect_prog_id ─────────────────────────────────────────────────────────────


def _make_winreg_mock(
    cur_ver_value: str | None = None,
    probed: list[str] | None = None,
) -> ModuleType:
    """Build a minimal winreg mock that simulates registry entries."""
    probed_set = set(probed or [])

    winreg = MagicMock()
    winreg.HKEY_CLASSES_ROOT = 0

    class _FakeKey:
        def __init__(self, value: str) -> None:
            self._value = value

        def __enter__(self) -> "_FakeKey":
            return self

        def __exit__(self, *_: object) -> None:
            pass

    def open_key(_root: int, path: str) -> _FakeKey:
        # CurVer path
        if path.endswith("\\CurVer"):
            if cur_ver_value is not None:
                return _FakeKey(cur_ver_value)
            raise OSError("not found")
        # Probed ProgID paths
        if path in probed_set:
            return _FakeKey(path)
        raise OSError("not found")

    def query_value_ex(key: _FakeKey, _name: str) -> tuple[str, int]:
        return key._value, 1

    winreg.OpenKey.side_effect = open_key
    winreg.QueryValueEx.side_effect = query_value_ex
    return winreg


class TestDetectProgId:
    def setup_method(self) -> None:
        detect_prog_id.cache_clear()

    def test_returns_cur_ver_when_valid(self) -> None:
        winreg_mock = _make_winreg_mock(cur_ver_value="ControlDeskNG.Application.2026-A")
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            result = detect_prog_id()
        assert result == "ControlDeskNG.Application.2026-A"

    def test_ignores_invalid_cur_ver_falls_back_to_probe(self) -> None:
        detect_prog_id.cache_clear()
        winreg_mock = _make_winreg_mock(
            cur_ver_value="ControlDeskNG.Application",  # not versioned
            probed=["ControlDeskNG.Application.2025-B", "ControlDeskNG.Application.2024-A"],
        )
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            result = detect_prog_id()
        assert result == "ControlDeskNG.Application.2025-B"  # latest wins

    def test_raises_when_nothing_found(self) -> None:
        detect_prog_id.cache_clear()
        winreg_mock = _make_winreg_mock()  # no entries at all
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            with pytest.raises(BridgeNotInstalledError):
                detect_prog_id()

    def test_raises_on_non_windows(self) -> None:
        detect_prog_id.cache_clear()
        with patch.dict(sys.modules, {"winreg": None}):  # type: ignore[dict-item]
            with pytest.raises(BridgeNotInstalledError):
                detect_prog_id()


# ── resolve_prog_id ────────────────────────────────────────────────────────────


class TestResolveProgId:
    def setup_method(self) -> None:
        detect_prog_id.cache_clear()

    def test_returns_configured_when_provided(self) -> None:
        assert resolve_prog_id("2026-A") == "ControlDeskNG.Application.2026-A"

    def test_version_is_uppercased(self) -> None:
        assert resolve_prog_id("2025-b") == "ControlDeskNG.Application.2025-B"

    def test_calls_detect_when_empty(self) -> None:
        detect_prog_id.cache_clear()
        winreg_mock = _make_winreg_mock(cur_ver_value="ControlDeskNG.Application.2026-B")
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            result = resolve_prog_id("")
        assert result == "ControlDeskNG.Application.2026-B"


# ── is_version_installed ───────────────────────────────────────────────────────


class TestIsVersionInstalled:
    def test_returns_true_when_prog_id_exists(self) -> None:
        winreg_mock = _make_winreg_mock(
            probed=["ControlDeskNG.Application.2024-A"],
        )
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            assert is_version_installed("2024-A") is True

    def test_returns_false_when_prog_id_absent(self) -> None:
        winreg_mock = _make_winreg_mock()  # empty registry
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            assert is_version_installed("2024-A") is False

    def test_returns_false_on_non_windows(self) -> None:
        with patch.dict(sys.modules, {"winreg": None}):  # type: ignore[dict-item]
            assert is_version_installed("2026-A") is False

    def test_version_lowercased_normalised(self) -> None:
        """is_version_installed normalises through version_to_prog_id (uppercase)."""
        winreg_mock = _make_winreg_mock(
            probed=["ControlDeskNG.Application.2025-B"],
        )
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            assert is_version_installed("2025-b") is True


# ── normalize_user_version ─────────────────────────────────────────────────────


class TestNormalizeUserVersion:
    def test_empty_string_returned_unchanged(self) -> None:
        assert normalize_user_version("") == ""

    def test_canonical_version_uppercased(self) -> None:
        assert normalize_user_version("2026-a") == "2026-A"

    def test_canonical_version_already_uppercase_unchanged(self) -> None:
        assert normalize_user_version("2026-A") == "2026-A"

    def test_whitespace_stripped(self) -> None:
        assert normalize_user_version("  2026-A  ") == "2026-A"

    def test_year_only_resolves_to_latest_letter(self) -> None:
        """'2026' with A and B installed returns '2026-B' (highest = most recent)."""
        winreg_mock = _make_winreg_mock(
            probed=[
                "ControlDeskNG.Application.2026-A",
                "ControlDeskNG.Application.2026-B",
            ],
        )
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            assert normalize_user_version("2026") == "2026-B"

    def test_year_only_single_letter_installed(self) -> None:
        winreg_mock = _make_winreg_mock(
            probed=["ControlDeskNG.Application.2024-A"],
        )
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            assert normalize_user_version("2024") == "2024-A"

    def test_year_only_raises_when_no_version_installed(self) -> None:
        winreg_mock = _make_winreg_mock()  # empty registry
        with patch.dict(sys.modules, {"winreg": winreg_mock}):
            with pytest.raises(BridgeNotInstalledError) as exc_info:
                normalize_user_version("2099")
        assert "2099" in str(exc_info.value)

    def test_year_only_non_windows_raises(self) -> None:
        with patch.dict(sys.modules, {"winreg": None}):  # type: ignore[dict-item]
            with pytest.raises(BridgeNotInstalledError):
                normalize_user_version("2026")

    def test_unrecognised_format_returned_as_is(self) -> None:
        """Unrecognised inputs (not year, not YYYY-L) pass through unchanged."""
        assert normalize_user_version("latest") == "latest"
