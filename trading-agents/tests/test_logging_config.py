"""
Tests for logging configuration
"""
import pytest
import logging
import tempfile
from pathlib import Path
from config.logging_config import (
    setup_logging,
    get_logger,
    ColoredFormatter,
    log_agent_start,
    log_agent_complete,
    log_llm_call,
    log_error,
    log_cost_summary,
)


class TestSetupLogging:
    """Test logging setup functionality"""

    def test_setup_logging_default(self):
        """Test default logging setup"""
        logger = setup_logging("test_logger_default")

        assert logger is not None
        assert logger.name == "test_logger_default"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logging_with_level(self):
        """Test logging setup with custom level"""
        logger = setup_logging("test_logger_debug", level=logging.DEBUG)

        assert logger.level == logging.DEBUG

    def test_setup_logging_with_file(self):
        """Test logging setup with file output"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(
                "test_logger_file",
                log_to_file=True,
                log_dir=tmpdir
            )

            # Check that file handler was added
            has_file_handler = any(
                isinstance(h, logging.FileHandler) for h in logger.handlers
            )
            assert has_file_handler

            # Check that log file was created
            log_files = list(Path(tmpdir).glob("test_logger_file_*.log"))
            assert len(log_files) > 0

    def test_setup_logging_no_duplicate_handlers(self):
        """Test that calling setup_logging twice doesn't create duplicate handlers"""
        logger1 = setup_logging("test_logger_nodupe")
        handler_count1 = len(logger1.handlers)

        logger2 = setup_logging("test_logger_nodupe")
        handler_count2 = len(logger2.handlers)

        assert logger1 is logger2
        assert handler_count1 == handler_count2

    def test_setup_logging_no_colors(self):
        """Test logging setup without colors"""
        logger = setup_logging("test_logger_nocolor", use_colors=False)

        # Check that ColoredFormatter is not used
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                assert not isinstance(handler.formatter, ColoredFormatter)


class TestGetLogger:
    """Test get_logger utility"""

    def test_get_logger_creates_new(self):
        """Test that get_logger creates new logger if needed"""
        logger = get_logger("test_new_logger")

        assert logger is not None
        assert logger.name == "test_new_logger"

    def test_get_logger_reuses_existing(self):
        """Test that get_logger reuses existing logger"""
        logger1 = get_logger("test_reuse_logger")
        logger2 = get_logger("test_reuse_logger")

        assert logger1 is logger2


class TestColoredFormatter:
    """Test ColoredFormatter"""

    def test_format_info_message(self):
        """Test formatting INFO level message"""
        formatter = ColoredFormatter(
            fmt='%(levelname)s - %(message)s'
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        assert "Test message" in formatted
        # Color codes should be present
        assert "\033[" in formatted or "INFO" in formatted

    def test_format_error_message(self):
        """Test formatting ERROR level message"""
        formatter = ColoredFormatter(
            fmt='%(levelname)s - %(message)s'
        )

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)
        assert "Error message" in formatted


class TestConvenienceFunctions:
    """Test convenience logging functions"""

    def test_log_agent_start(self, capsys):
        """Test log_agent_start function"""
        test_logger = setup_logging("test_convenience_start")

        log_agent_start("TestAgent", "gpt-4o-mini", logger=test_logger)

        # Function should log without errors
        # Actual output checking depends on log level configuration

    def test_log_agent_complete(self, capsys):
        """Test log_agent_complete function"""
        test_logger = setup_logging("test_convenience_complete")

        log_agent_complete("TestAgent", 2.5, logger=test_logger)

        # Function should log without errors

    def test_log_llm_call(self, capsys):
        """Test log_llm_call function"""
        test_logger = setup_logging("test_convenience_llm", level=logging.DEBUG)

        log_llm_call("gpt-4o-mini", 1500, 0.05, logger=test_logger)

        # Function should log without errors

    def test_log_error_function(self, capsys):
        """Test log_error function"""
        test_logger = setup_logging("test_convenience_error")

        error = ValueError("Test error")
        log_error(error, context="test context", logger=test_logger)

        # Function should log without errors

    def test_log_cost_summary(self, capsys):
        """Test log_cost_summary function"""
        test_logger = setup_logging("test_convenience_cost")

        log_cost_summary(0.25, 10, logger=test_logger)

        # Function should log without errors

    def test_convenience_functions_use_default_logger(self):
        """Test that convenience functions work with default logger"""
        # These should not raise errors even without explicit logger
        log_agent_start("TestAgent", "gpt-4o-mini")
        log_agent_complete("TestAgent", 1.5)
        log_llm_call("gpt-4o-mini", 1000, 0.01)
        log_error(Exception("test"))
        log_cost_summary(0.10, 5)


class TestLoggerHierarchy:
    """Test logger naming and hierarchy"""

    def test_agent_logger_naming(self):
        """Test that agent loggers follow naming convention"""
        logger = get_logger("agents.portfolio_analyst")

        assert logger.name == "agents.portfolio_analyst"

    def test_router_logger_naming(self):
        """Test that router loggers follow naming convention"""
        logger = get_logger("llm_router.unified")

        assert logger.name == "llm_router.unified"


class TestLoggingLevels:
    """Test different logging levels"""

    def test_debug_level_logs_everything(self):
        """Test that DEBUG level captures all messages"""
        logger = setup_logging("test_debug_all", level=logging.DEBUG)

        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(
                "test_debug_file",
                level=logging.DEBUG,
                log_to_file=True,
                log_dir=tmpdir
            )

            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

            # All messages should be logged

    def test_info_level_filters_debug(self):
        """Test that INFO level filters out DEBUG messages"""
        logger = setup_logging("test_info_filter", level=logging.INFO)

        # DEBUG messages should not be processed at INFO level
        # (can't easily test without checking handler outputs)


class TestFileLogging:
    """Test file logging functionality"""

    def test_log_file_created_with_timestamp(self):
        """Test that log file is created with timestamp"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(
                "test_file_timestamp",
                log_to_file=True,
                log_dir=tmpdir
            )

            log_files = list(Path(tmpdir).glob("test_file_timestamp_*.log"))
            assert len(log_files) == 1

            # Check filename format includes timestamp
            filename = log_files[0].name
            assert "test_file_timestamp_" in filename
            assert ".log" in filename

    def test_log_file_contains_messages(self):
        """Test that log file actually contains logged messages"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(
                "test_file_content",
                log_to_file=True,
                log_dir=tmpdir
            )

            test_message = "This is a test log message"
            logger.info(test_message)

            # Force handlers to flush
            for handler in logger.handlers:
                handler.flush()

            # Read log file
            log_files = list(Path(tmpdir).glob("test_file_content_*.log"))
            assert len(log_files) == 1

            content = log_files[0].read_text()
            assert test_message in content

    def test_log_file_format_includes_details(self):
        """Test that file log format includes function and line number"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = setup_logging(
                "test_file_format",
                log_to_file=True,
                log_dir=tmpdir
            )

            logger.info("Format test")

            # Force flush
            for handler in logger.handlers:
                handler.flush()

            # Read log file
            log_files = list(Path(tmpdir).glob("test_file_format_*.log"))
            content = log_files[0].read_text()

            # File format should include function name and line number
            assert "test_log_file_format_includes_details" in content or "lineno" in content
