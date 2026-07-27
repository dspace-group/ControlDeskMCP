"""Auto-detect the installed ControlDesk COM ProgID from the Windows Registry.

Detection strategy (in order):
1. ``HKCR\\ControlDeskNG.Application\\CurVer`` — standard COM convention, fastest path.
2. Probe year-letter patterns for recent releases — bounded O(n) registry lookups.

ProgID is *internal*. Callers use the human-readable version string (e.g. ``"2026-A"``).
The result is cached after the first successful detection.
"""

from __future__ import annotations

import re
from datetime import datetime
from functools import lru_cache

from controldesk_mcp.com_bridge.errors import BridgeNotInstalledError

_PROG_ID_BASE = "ControlDeskNG.Application"
_VERSION_RE = re.compile(r"^ControlDeskNG\.Application\.(\d{4})-([A-Za-z])$")
_USER_VERSION_RE = re.compile(r"^\d{4}-[A-Za-z]$")
_YEAR_ONLY_RE = re.compile(r"^\d{4}$")

# Probe window: current year ± _PROBE_YEARS_BACK, letters A–E cover all known releases.
_PROBE_YEARS_BACK: int = 6
_PROBE_LETTERS: str = "ABCDE"


def version_to_prog_id(version: str) -> str:
    """Convert a user-facing version string to the internal COM ProgID.

    Args:
        version: Human-readable version, e.g. ``"2026-A"``.

    Returns:
        Full ProgID, e.g. ``"ControlDeskNG.Application.2026-A"``.
    """
    return f"{_PROG_ID_BASE}.{version.upper()}"


def _parse_version(prog_id: str) -> tuple[int, str] | None:
    """Return ``(year, letter)`` sort key or ``None`` for unversioned ProgIDs."""
    m = _VERSION_RE.match(prog_id)
    return (int(m.group(1)), m.group(2).upper()) if m else None


def _cur_ver_prog_id() -> str | None:
    """Read ``HKCR\\ControlDeskNG.Application\\CurVer`` (standard COM convention)."""
    try:
        import winreg  # noqa: PLC0415
    except ImportError:
        return None
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, rf"{_PROG_ID_BASE}\CurVer") as key:
            value, _ = winreg.QueryValueEx(key, "")
            return str(value) if value else None
    except OSError:
        return None


def _probe_versions() -> list[str]:
    """Probe HKCR for versioned ProgIDs matching ``YEAR-LETTER`` patterns.

    Probes at most ``_PROBE_YEARS_BACK * len(_PROBE_LETTERS)`` registry keys — O(constant).
    """
    try:
        import winreg  # noqa: PLC0415
    except ImportError:
        return []

    current_year = datetime.now().year
    found: list[str] = []
    for year in range(current_year + 1, current_year - _PROBE_YEARS_BACK - 1, -1):
        for letter in _PROBE_LETTERS:
            prog_id = f"{_PROG_ID_BASE}.{year}-{letter}"
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog_id):
                    found.append(prog_id)
            except OSError:
                pass
    return found


@lru_cache(maxsize=1)
def detect_prog_id() -> str:
    """Return the ProgID of the latest installed ControlDesk.

    Raises:
        BridgeNotInstalledError: No ControlDesk installation found.
    """
    cur = _cur_ver_prog_id()
    if cur and _parse_version(cur):
        return cur

    candidates = [p for p in _probe_versions() if _parse_version(p)]
    if not candidates:
        raise BridgeNotInstalledError(
            "No ControlDesk installation found in the Windows Registry. "
            "Install ControlDesk or set the CONTROLDESK_VERSION environment variable."
        )

    candidates.sort(key=_parse_version, reverse=True)  # type: ignore[arg-type]
    return candidates[0]


def resolve_prog_id(controldesk_version: str) -> str:
    """Return the ProgID for *controldesk_version*.

    Args:
        controldesk_version: Human-readable version like ``"2026-A"``, or empty to auto-detect.

    Returns:
        Full internal ProgID, e.g. ``"ControlDeskNG.Application.2026-A"``.
    """
    if controldesk_version:
        return version_to_prog_id(controldesk_version)
    return detect_prog_id()


def is_version_installed(version: str) -> bool:
    """Return ``True`` if *version* is present in the Windows Registry.

    Performs a direct registry probe (no cache) so callers always get a
    fresh answer even when the user installs or removes ControlDesk at runtime.

    Args:
        version: Human-readable version like ``"2024-A"``.

    Returns:
        ``True`` when the version's ProgID key exists under ``HKEY_CLASSES_ROOT``.
    """
    try:
        import winreg  # noqa: PLC0415
    except ImportError:
        return False

    prog_id = version_to_prog_id(version)
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog_id):
            return True
    except OSError:
        return False


def normalize_user_version(version: str) -> str:
    """Normalize a user-supplied version string to the canonical ``YYYY-L`` format.

    Handles three cases:

    * ``""`` — auto-detect path; returned unchanged.
    * ``"2026-A"`` — already canonical; uppercased and returned.
    * ``"2026"`` — year-only shorthand; probed against the registry and resolved
      to the latest installed letter (e.g. ``"2026-B"`` when both A and B exist).

    Args:
        version: Raw version string from the user, e.g. ``"2026"`` or ``"2026-A"``.

    Returns:
        Canonical ``YYYY-L`` string, or empty string for auto-detect.

    Raises:
        BridgeNotInstalledError: Year-only input with no ControlDesk installed for that year.
    """
    version = version.strip()
    if not version:
        return version

    if _USER_VERSION_RE.match(version):
        # Already canonical YYYY-L — normalise casing only.
        return version.upper()

    if _YEAR_ONLY_RE.match(version):
        # Year-only shorthand — find the highest installed letter for that year.
        installed = [letter for letter in _PROBE_LETTERS if is_version_installed(f"{version}-{letter}")]
        if not installed:
            raise BridgeNotInstalledError(
                f"No ControlDesk installation found for year '{version}'. "
                "Provide the full version string (e.g. '2026-A') or install ControlDesk.",
                recovery_hint=(f"Install ControlDesk {version}-A or specify the exact version, e.g. '2026-A'."),
            )
        # _PROBE_LETTERS is ordered A→E; last found = highest letter = most recent.
        return f"{version}-{installed[-1]}"

    # Unrecognised format — return as-is; downstream will produce a clear error.
    return version
