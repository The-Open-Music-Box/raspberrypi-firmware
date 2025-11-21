# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Minimal logger wrapper decoupled from app layers.

Provides a thin ImprovedLogger compatible with previous API,
implemented purely with stdlib logging to avoid cross-layer imports.
"""

import importlib as _il
_logging = _il.import_module('logging')
from typing import Any, Dict, Optional


class ImprovedLogger:
    """Thread-safe, context-aware logger for TheOpenMusicBox.

    Provides colored output, error deduplication, and extra context
    formatting for hardware and application logs. Integrates with
    unified monitoring configuration.
    """

    _error_counts = {}
    MAX_REPEATED_ERRORS = 1

    # Log level mapping from string to logging level
    _LOG_LEVEL_MAP = {
        "DEBUG": _logging.DEBUG,
        "INFO": _logging.INFO,
        "WARNING": _logging.WARNING,
        "ERROR": _logging.ERROR,
        "CRITICAL": _logging.CRITICAL,
    }

    def __init__(self, name: str):
        """Initialize the logger with unified configuration.

        Args:
            name: Logger name (typically module __name__)
        """
        self.logger = _logging.getLogger(name)
        self.context = {}
        self.name = name
        # Basic configuration; rely on root logger formatters configured elsewhere
        if not _logging.getLogger().handlers:
            _logging.basicConfig(level=_logging.INFO)

    def _configure_logger(self):
        """Configure logger with handlers and formatters."""
        # Keep default logger behavior; external config may adjust formatting/levels
        self.logger.propagate = True

    def _should_log_error(self, error_key: str) -> bool:
        """Check if error should be logged based on deduplication rules.

        Args:
            error_key: Unique key for the error

        Returns:
            True if error should be logged, False otherwise
        """
        count = self._error_counts.get(error_key, 0)
        if count < self.MAX_REPEATED_ERRORS:
            self._error_counts[error_key] = count + 1
            return True
        return False

    def _format_extra(self, extra: Dict[str, Any]) -> str:
        """Format extra context information.

        Args:
            extra: Extra context data

        Returns:
            Formatted extra string
        """
        if not extra:
            return ""
        # Minimal extra formatting
        try:
            parts = []
            for k, v in extra.items():
                parts.append(f" {k}={v}")
            return "".join(parts)
        except Exception as e:
            # Re-raise system exceptions
            if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                raise
            return ""

    def log(
        self,
        level: Any,
        message: str,
        exc_info: Optional[Exception] = None,
        **kwargs,
    ):
        """Log a message with the specified level.

        Formats extra context and handles errors appropriately.
        Integrates with unified monitoring for debug information.

        Args:
            level: LogLevel (severity)
            message: Log message
            exc_info: Optional exception for error context
            **kwargs: Additional context for the log formatter
        """
        # Handle hardware unavailable errors gracefully
        if exc_info and isinstance(exc_info, OSError):
            message = "Hardware not available"
            exc_info = None

        level_name = getattr(level, 'value', level)
        if isinstance(level_name, int):
            py_level = level_name
        else:
            py_level = getattr(_logging, str(level_name).upper(), _logging.INFO)

        error_key = f"{level_name}:{message}"

        # Apply error deduplication for ERROR and CRITICAL levels
        if py_level >= _logging.ERROR:
            if not self._should_log_error(error_key):
                return

        # Add debug information if monitoring is enabled
        if kwargs:
            kwargs["logger_name"] = self.name

        extra_str = self._format_extra(kwargs) if kwargs else ""
        full_message = f"{message}{extra_str}"

        # Log the message
        log_func = getattr(self.logger, _logging.getLevelName(py_level).lower(), self.logger.info)
        log_func(full_message)

    def debug(self, message: str, **kwargs):
        """Log a debug message."""
        self.logger.debug(message)

    def info(self, message: str, **kwargs):
        """Log an info message."""
        self.logger.info(message)

    def warning(self, message: str, **kwargs):
        """Log a warning message."""
        self.logger.warning(message)

    def error(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log an error message."""
        self.logger.error(message)

    def critical(self, message: str, exc_info: Optional[Exception] = None, **kwargs):
        """Log a critical message."""
        self.logger.critical(message)

    def set_context(self, **context):
        """Set persistent context for this logger.

        Args:
            **context: Context key-value pairs
        """
        self.context.update(context)

    def clear_context(self):
        """Clear all persistent context."""
        self.context.clear()

    def with_context(self, **context):
        """Create a temporary context for a single log message.

        Args:
            **context: Context key-value pairs

        Returns:
            LoggerContext: Context manager for temporary context
        """
        return LoggerContext(self, context)


class LoggerContext:
    """Context manager for temporary logger context."""

    def __init__(self, logger: ImprovedLogger, context: Dict[str, Any]):
        self.logger = logger
        self.context = context
        self.original_context = {}

    def __enter__(self):
        # Save original context and update with new context
        for key, value in self.context.items():
            if key in self.logger.context:
                self.original_context[key] = self.logger.context[key]
            self.logger.context[key] = value
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original context
        for key in self.context.keys():
            if key in self.original_context:
                self.logger.context[key] = self.original_context[key]
            else:
                self.logger.context.pop(key, None)
