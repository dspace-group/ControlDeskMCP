"""Tests for the stderr logger utility."""

import logging
import sys


class TestGetLogger:
    def test_returns_logger(self) -> None:
        from controldesk_mcp.utils.logger import get_logger

        lg = get_logger("test.module")
        assert isinstance(lg, logging.Logger)
        assert lg.name == "test.module"

    def test_same_name_returns_same_instance(self) -> None:
        from controldesk_mcp.utils.logger import get_logger

        lg1 = get_logger("test.dedup")
        lg2 = get_logger("test.dedup")
        assert lg1 is lg2

    def test_handler_writes_to_stderr(self) -> None:
        from controldesk_mcp.utils.logger import get_logger

        lg = get_logger("test.stderr_check")
        assert any(isinstance(h, logging.StreamHandler) and h.stream is sys.stderr for h in lg.handlers)

    def test_propagate_is_false(self) -> None:
        """Logger must not forward to root — root handler may use stdout."""
        from controldesk_mcp.utils.logger import get_logger

        lg = get_logger("test.propagate")
        assert lg.propagate is False

    def test_no_stdout_handler(self) -> None:
        from controldesk_mcp.utils.logger import get_logger

        lg = get_logger("test.no_stdout")
        for handler in lg.handlers:
            if isinstance(handler, logging.StreamHandler):
                assert handler.stream is not sys.stdout


class TestConfigureRootLevel:
    def test_handler_level_reflects_config(self) -> None:
        """Handler level should match configured log level, with WARNING as minimum on stdio."""
        from controldesk_mcp.utils.logger import (
            _configured,
            _StderrOnlyHandler,
            configure_root_level,
            get_logger,
        )

        _configured.discard("test.handler_level")
        _configured.discard("test.handler_level_warn")

        lg = get_logger("test.handler_level")
        configure_root_level("DEBUG")
        # DEBUG enables all levels on stderr
        handler = next((h for h in lg.handlers if isinstance(h, _StderrOnlyHandler)), None)
        assert handler is not None
        assert handler.level == logging.DEBUG

        lg2 = get_logger("test.handler_level_warn")
        configure_root_level("WARNING")
        # WARNING filters out INFO/DEBUG on stderr
        handler2 = next((h for h in lg2.handlers if isinstance(h, _StderrOnlyHandler)), None)
        assert handler2 is not None
        assert handler2.level == logging.WARNING

    def test_info_messages_filtered_by_default(self) -> None:
        """INFO messages should not reach stderr handler by default (WARNING+)."""
        from controldesk_mcp.utils.logger import (
            _configured,
            _StderrOnlyHandler,
            configure_root_level,
            get_logger,
        )

        _configured.discard("test.info_filter")

        lg = get_logger("test.info_filter")
        configure_root_level("INFO")
        # Even though configured to INFO, handler filters to WARNING
        handler = next((h for h in lg.handlers if isinstance(h, _StderrOnlyHandler)), None)
        assert handler is not None
        assert handler.level == logging.WARNING
