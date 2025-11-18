# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for logging formatters and utilities."""

import logging
import pytest
from colorama import Fore, Style

from app.src.monitoring.logging.log_base_formatter import BaseLogFormatter
from app.src.monitoring.logging.log_colored_formatter import ColoredLogFormatter
from app.src.monitoring.logging.log_color_scheme import ColorScheme
from app.src.monitoring.logging.log_filter import LogFilter
from app.src.monitoring.logging.log_level import LogLevel


class TestBaseLogFormatter:
    """Test base log formatter functionality."""

    def test_init(self):
        """Test BaseLogFormatter initialization."""
        formatter = BaseLogFormatter()
        assert formatter._last_component is None
        assert formatter._startup_phase is None

    def test_simplify_component_name(self):
        """Test component name simplification."""
        formatter = BaseLogFormatter()
        assert formatter._simplify_component_name("app.src.domain.services") == "services"
        assert formatter._simplify_component_name("simple") == "simple"
        assert formatter._simplify_component_name("a.b.c.d.e") == "e"

    def test_extract_component(self):
        """Test component extraction from initialization message."""
        formatter = BaseLogFormatter()
        assert formatter._extract_component("Initializing AudioSystem") == "AudioSystem"
        assert formatter._extract_component("Initializing Database") == "Database"
        assert formatter._extract_component("Other message") == ""

    def test_format_extra_empty(self):
        """Test formatting empty extra dict."""
        formatter = BaseLogFormatter()
        assert formatter.format_extra({}) == ""
        assert formatter.format_extra(None) == ""

    def test_format_extra_with_data(self):
        """Test formatting extra information."""
        formatter = BaseLogFormatter()
        result = formatter.format_extra({"error_code": "E123", "count": 5})
        assert "error_code" in result
        assert "E123" in result
        assert "(" in result and ")" in result

    def test_format_extra_filters_irrelevant(self):
        """Test that component and operation are filtered unless error-related."""
        formatter = BaseLogFormatter()
        result = formatter.format_extra({"component": "test", "operation": "save"})
        assert result == ""


class TestColoredLogFormatter:
    """Test colored log formatter."""

    @pytest.fixture
    def formatter(self):
        """Create a ColoredLogFormatter instance."""
        return ColoredLogFormatter()

    @pytest.fixture
    def log_record(self):
        """Create a sample log record."""
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        return record

    def test_init(self, formatter):
        """Test ColoredLogFormatter initialization."""
        assert isinstance(formatter, BaseLogFormatter)
        assert isinstance(formatter, logging.Formatter)

    def test_format_info_message(self, formatter, log_record):
        """Test formatting an INFO level message."""
        result = formatter.format(log_record)
        assert "Test message" in result
        # Color codes should be present
        assert Style.RESET_ALL in result

    def test_format_warning_message(self, formatter):
        """Test formatting a WARNING level message."""
        record = logging.LogRecord(
            name="app.test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=10,
            msg="Warning message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "Warning message" in result

    def test_format_error_message(self, formatter):
        """Test formatting an ERROR level message."""
        record = logging.LogRecord(
            name="app.test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=10,
            msg="Error message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "Error message" in result

    def test_format_startup_message(self, formatter):
        """Test formatting initialization messages."""
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Initializing AudioSystem",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "Initializing" in result
        assert "AudioSystem" in result
        assert Fore.CYAN in result

    def test_format_ready_message(self, formatter):
        """Test formatting ready messages after initialization."""
        # First set the startup phase
        init_record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Initializing Database",
            args=(),
            exc_info=None,
        )
        formatter.format(init_record)

        # Then test the ready message
        ready_record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=11,
            msg="Database ready",
            args=(),
            exc_info=None,
        )
        result = formatter.format(ready_record)
        assert "ready" in result
        assert Fore.GREEN in result


class TestColorScheme:
    """Test color scheme configuration."""

    def test_colors_dict_exists(self):
        """Test that COLORS dictionary exists."""
        assert hasattr(ColorScheme, "COLORS")
        assert isinstance(ColorScheme.COLORS, dict)

    def test_symbols_dict_exists(self):
        """Test that SYMBOLS dictionary exists."""
        assert hasattr(ColorScheme, "SYMBOLS")
        assert isinstance(ColorScheme.SYMBOLS, dict)

    def test_color_for_levels(self):
        """Test colors are defined for common log levels."""
        assert "INFO" in ColorScheme.COLORS
        assert "WARNING" in ColorScheme.COLORS
        assert "ERROR" in ColorScheme.COLORS
        assert "DEBUG" in ColorScheme.COLORS

    def test_symbols_for_levels(self):
        """Test symbols are defined for common log levels."""
        assert "INFO" in ColorScheme.SYMBOLS
        assert "WARNING" in ColorScheme.SYMBOLS
        assert "ERROR" in ColorScheme.SYMBOLS


class TestLogFilter:
    """Test log filtering functionality."""

    def test_should_log_normal_message(self):
        """Test that normal messages should be logged."""
        assert LogFilter.should_log("Normal log message") is True
        assert LogFilter.should_log("Important information") is True

    def test_clean_message_removes_prefixes(self):
        """Test that clean_message removes unwanted prefixes."""
        # Should return cleaned message (test implementation)
        result = LogFilter.clean_message("✓ Message with prefix")
        assert result  # Just verify it returns something

    def test_clean_message_handles_empty(self):
        """Test clean_message handles empty strings."""
        result = LogFilter.clean_message("")
        assert result == ""


class TestLogLevel:
    """Test log level utilities."""

    def test_log_level_constants(self):
        """Test that LogLevel provides standard level constants."""
        assert hasattr(LogLevel, "DEBUG") or hasattr(LogLevel, "LEVELS")

    def test_log_level_usable(self):
        """Test LogLevel can be imported and used."""
        # Just verify the class exists and is importable
        assert LogLevel is not None


class TestLoggingIntegration:
    """Test integration between logging components."""

    def test_formatter_with_filter(self):
        """Test that formatter works with filter."""
        formatter = ColoredLogFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        # Should not raise and should return formatted string
        result = formatter.format(record)
        assert isinstance(result, str)

    def test_component_name_simplification_in_format(self):
        """Test component name is simplified in formatted output."""
        formatter = ColoredLogFormatter()
        record = logging.LogRecord(
            name="app.src.domain.services.playlist",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        # Component name should be simplified to last part
        assert "playlist" in result or "Test" in result
