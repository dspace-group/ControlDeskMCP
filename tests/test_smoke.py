"""Smoke tests — verify the server package imports and bootstrap tools work."""


def test_package_imports() -> None:
    """Server package and submodules must import without errors."""
    import controldesk_mcp  # noqa: F401
    import controldesk_mcp.config.settings  # noqa: F401
    import controldesk_mcp.main  # noqa: F401
    import controldesk_mcp.models.errors  # noqa: F401
    import controldesk_mcp.server.app  # noqa: F401
    import controldesk_mcp.utils.logger  # noqa: F401


def test_mcp_instance_exists() -> None:
    """FastMCP instance must be created and named correctly."""
    from controldesk_mcp.server.app import mcp

    assert mcp is not None
    assert "ControlDesk" in mcp.name
