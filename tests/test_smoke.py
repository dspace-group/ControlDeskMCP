"""Smoke tests — verify the server package imports and bootstrap tools work."""


def test_package_imports() -> None:
    """Server package and submodules must import without errors."""
    import sources  # noqa: F401
    import sources.config.settings  # noqa: F401
    import sources.main  # noqa: F401
    import sources.models.errors  # noqa: F401
    import sources.server.app  # noqa: F401
    import sources.utils.logger  # noqa: F401


def test_mcp_instance_exists() -> None:
    """FastMCP instance must be created and named correctly."""
    from sources.server.app import mcp

    assert mcp is not None
    assert "ControlDesk" in mcp.name
