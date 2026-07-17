"""Compatibility server entrypoint.

Keeps `python -m controldesk_mcp.server` working while delegating to
existing implementation in `sources.main`.
"""

from sources.main import main


if __name__ == "__main__":
    main()
