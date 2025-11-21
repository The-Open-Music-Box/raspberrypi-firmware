# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unified error handler that replaces all legacy error handlers."""

import sys
import traceback
import time
from typing import Dict, Any, Optional, Callable, List
from enum import Enum
from dataclasses import dataclass

from app.src.monitoring import get_logger
import logging
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors

logger = get_logger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories."""

    AUDIO = "audio"
    NFC = "nfc"
    PLAYLIST = "playlist"
    NETWORK = "network"
    FILE_SYSTEM = "filesystem"
    DATABASE = "database"
    HARDWARE = "hardware"
    GENERAL = "general"


@dataclass
class ErrorContext:
    """Context information for error handling."""

    component: str
    operation: str
    category: ErrorCategory = ErrorCategory.GENERAL
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""

    timestamp: float
    error_type: str
    message: str
    context: ErrorContext
    traceback_str: Optional[str] = None
    resolved: bool = False
    resolution_time: Optional[float] = None


class UnifiedErrorHandler:
    """Unified error handler that consolidates all legacy error handling."""

    def __init__(self):
        """Initialize the unified error handler."""
        self._error_records: List[ErrorRecord] = []
        self._error_callbacks: Dict[ErrorCategory, List[Callable]] = {}
        self._error_count_by_category: Dict[ErrorCategory, int] = {}
        self._error_count_by_severity: Dict[ErrorSeverity, int] = {}
        self._max_records = 1000  # Keep last 1000 errors

        # Initialize counters
        for category in ErrorCategory:
            self._error_count_by_category[category] = 0

        for severity in ErrorSeverity:
            self._error_count_by_severity[severity] = 0

        logger.info("UnifiedErrorHandler initialized")

    def handle_error(self, error: Exception, context: ErrorContext, reraise: bool = False) -> None:
        """Handle an error with context information.

        Args:
            error: The exception that occurred
            context: Context information about the error
            reraise: Whether to reraise the exception after handling

        Note:
            This method does NOT use @handle_errors decorator to prevent recursion.
            It has its own try/catch to prevent error handler crashes.
        """
        try:
            # Create error record
            error_record = ErrorRecord(
                timestamp=time.time(),
                error_type=type(error).__name__,
                message=str(error),
                context=context,
                traceback_str=traceback.format_exc() if sys.exc_info()[0] else None,
            )
            # Store record
            self._add_error_record(error_record)
            # Update counters
            self._error_count_by_category[context.category] += 1
            self._error_count_by_severity[context.severity] += 1
            # Log the error
            self._log_error(error_record)
            # Notify callbacks
            self._notify_callbacks(error_record)
            # Handle critical errors
            if context.severity == ErrorSeverity.CRITICAL:
                self._handle_critical_error(error_record)
        except Exception as handler_error:
            # Last resort: print to stderr to avoid infinite recursion
            # Cannot use logger here since the logging system may have failed
            # This ensures critical errors are visible even when error handling crashes
            import sys
            print(f"CRITICAL: Error handler itself failed: {handler_error}", file=sys.stderr)
            print(f"Original error was: {error}", file=sys.stderr)

        # Reraise original error if requested (after handling completes)
        if reraise:
            raise error

    def handle_audio_error(
        self, error: Exception, component: str, operation: str, **metadata
    ) -> None:
        """Handle audio-specific errors."""
        context = ErrorContext(
            component=component,
            operation=operation,
            category=ErrorCategory.AUDIO,
            severity=ErrorSeverity.HIGH,
            metadata=metadata,
        )
        self.handle_error(error, context)

    def handle_nfc_error(
        self, error: Exception, component: str, operation: str, **metadata
    ) -> None:
        """Handle NFC-specific errors."""
        context = ErrorContext(
            component=component,
            operation=operation,
            category=ErrorCategory.NFC,
            severity=ErrorSeverity.MEDIUM,
            metadata=metadata,
        )
        self.handle_error(error, context)

    def handle_playlist_error(
        self, error: Exception, component: str, operation: str, **metadata
    ) -> None:
        """Handle playlist-specific errors."""
        context = ErrorContext(
            component=component,
            operation=operation,
            category=ErrorCategory.PLAYLIST,
            severity=ErrorSeverity.MEDIUM,
            metadata=metadata,
        )
        self.handle_error(error, context)

    def handle_filesystem_error(
        self, error: Exception, component: str, operation: str, **metadata
    ) -> None:
        """Handle filesystem-specific errors."""
        context = ErrorContext(
            component=component,
            operation=operation,
            category=ErrorCategory.FILE_SYSTEM,
            severity=ErrorSeverity.HIGH,
            metadata=metadata,
        )
        self.handle_error(error, context)

    def handle_network_error(
        self, error: Exception, component: str, operation: str, **metadata
    ) -> None:
        """Handle network-specific errors."""
        context = ErrorContext(
            component=component,
            operation=operation,
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            metadata=metadata,
        )
        self.handle_error(error, context)

    def handle_database_error(
        self, error: Exception, component: str, operation: str, **metadata
    ) -> None:
        """Handle database-specific errors."""
        context = ErrorContext(
            component=component,
            operation=operation,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            metadata=metadata,
        )
        self.handle_error(error, context)

    def handle_hardware_error(
        self, error: Exception, component: str, operation: str, **metadata
    ) -> None:
        """Handle hardware-specific errors."""
        context = ErrorContext(
            component=component,
            operation=operation,
            category=ErrorCategory.HARDWARE,
            severity=ErrorSeverity.CRITICAL,
            metadata=metadata,
        )
        self.handle_error(error, context)

    def register_callback(
        self, category: ErrorCategory, callback: Callable[[ErrorRecord], None]
    ) -> None:
        """Register a callback for specific error category.

        Args:
            category: Error category to listen for
            callback: Function to call when error occurs
        """
        if category not in self._error_callbacks:
            self._error_callbacks[category] = []

        self._error_callbacks[category].append(callback)

    def mark_resolved(self, record_id: int) -> bool:
        """Mark an error as resolved.

        Args:
            record_id: Index of the error record

        Returns:
            bool: True if error was found and marked resolved
        """
        if 0 <= record_id < len(self._error_records):
            error_record = self._error_records[record_id]
            if not error_record.resolved:
                error_record.resolved = True
                error_record.resolution_time = time.time()
                logger.info(
                    f"Error resolved: {error_record.error_type} in {error_record.context.component}"
                )
                return True

        return False

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get comprehensive error statistics."""
        recent_errors = [
            r for r in self._error_records if time.time() - r.timestamp < 3600
        ]  # Last hour

        return {
            "total_errors": len(self._error_records),
            "recent_errors": len(recent_errors),
            "errors_by_category": dict(self._error_count_by_category),
            "errors_by_severity": dict(self._error_count_by_severity),
            "resolved_errors": sum(1 for r in self._error_records if r.resolved),
            "unresolved_errors": sum(1 for r in self._error_records if not r.resolved),
            "average_resolution_time": self._calculate_average_resolution_time(),
            "most_common_errors": self._get_most_common_errors(10),
        }

    def get_recent_errors(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent error records.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of error record dictionaries
        """
        recent_records = self._error_records[-limit:] if self._error_records else []

        return [
            {
                "timestamp": record.timestamp,
                "error_type": record.error_type,
                "message": record.message,
                "component": record.context.component,
                "operation": record.context.operation,
                "category": record.context.category.value,
                "severity": record.context.severity.value,
                "metadata": record.context.metadata,
                "resolved": record.resolved,
                "resolution_time": record.resolution_time,
            }
            for record in recent_records
        ]

    def clear_old_errors(self, max_age_hours: int = 24) -> int:
        """Clear old error records.

        Args:
            max_age_hours: Maximum age of errors to keep

        Returns:
            Number of errors cleared
        """
        cutoff_time = time.time() - (max_age_hours * 3600)
        initial_count = len(self._error_records)

        self._error_records = [r for r in self._error_records if r.timestamp > cutoff_time]

        cleared_count = initial_count - len(self._error_records)

        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} old error records")

        return cleared_count

    def handle_internal_error(self, error: Exception, operation: str) -> Dict[str, Any]:
        """Handle internal server errors and return appropriate response data."""
        # Simple error response without dependencies
        error_response = {
            "success": False,
            "error": {
                "type": "INTERNAL_ERROR",
                "message": f"Internal server error during {operation}",
            },
        }

        context = ErrorContext(
            component="internal",
            operation=operation,
            category=ErrorCategory.GENERAL,
            severity=ErrorSeverity.HIGH,
        )

        self.handle_error(error, context)

        return {"content": error_response, "status_code": 500}

    def handle_http_error(self, error: Exception, message: str) -> Dict[str, Any]:
        """Handle HTTP errors and return appropriate response data."""
        # Determine error type and status code
        if hasattr(error, 'status_code') and hasattr(error, 'detail'):
            # HTTPException-like object
            status_code = error.status_code
            error_message = error.detail
        elif isinstance(error, (ValueError, TypeError)):
            status_code = 400
            error_message = str(error)
        elif isinstance(error, FileNotFoundError):
            status_code = 404
            error_message = "Resource not found"
        else:
            status_code = 500
            error_message = message

        error_response = {
            "success": False,
            "error": {"type": "HTTP_ERROR", "message": error_message, "context": message},
        }

        context = ErrorContext(
            component="http",
            operation=message,
            category=ErrorCategory.GENERAL,
            severity=ErrorSeverity.MEDIUM if status_code < 500 else ErrorSeverity.HIGH,
        )

        self.handle_error(error, context)

        return {"content": error_response, "status_code": status_code}

    # === Internal Methods ===

    def _add_error_record(self, record: ErrorRecord) -> None:
        """Add an error record, maintaining max records limit."""
        self._error_records.append(record)

        # Remove oldest records if we exceed the limit
        if len(self._error_records) > self._max_records:
            self._error_records = self._error_records[-self._max_records :]

    def _log_error(self, record: ErrorRecord) -> None:
        """Log the error with appropriate level."""
        log_level = self._severity_to_log_level(record.context.severity)

        message = (
            f"🚨 {record.context.category.value.upper()} ERROR in {record.context.component}: "
            f"{record.error_type}: {record.message}"
        )

        if record.context.metadata:
            message += f" | Metadata: {record.context.metadata}"

        logger.log(log_level, message)

        # Log traceback for high severity errors
        if (
            record.context.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]
            and record.traceback_str
        ):
            logger.debug(f"Traceback:\n{record.traceback_str}")

    @handle_errors("_notify_callbacks")
    def _notify_callbacks(self, record: ErrorRecord) -> None:
        """Notify registered callbacks."""
        callbacks = self._error_callbacks.get(record.context.category, [])

        for callback in callbacks:
            callback(record)

    def _handle_critical_error(self, record: ErrorRecord) -> None:
        """Handle critical errors with special attention."""
        logger.error(
            f"🔥 CRITICAL ERROR detected: {record.error_type} in {record.context.component}"
        )

        # Could add additional actions like:
        # - Send notifications
        # - Trigger system recovery
        # - Create incident reports

    def _severity_to_log_level(self, severity: ErrorSeverity) -> int:
        """Convert error severity to log level."""
        mapping = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.ERROR,
        }
        return mapping.get(severity, logging.WARNING)

    def _calculate_average_resolution_time(self) -> Optional[float]:
        """Calculate average resolution time for resolved errors."""
        resolved_records = [r for r in self._error_records if r.resolved and r.resolution_time]

        if not resolved_records:
            return None

        total_time = sum(r.resolution_time - r.timestamp for r in resolved_records)
        return total_time / len(resolved_records)

    def _get_most_common_errors(self, limit: int) -> List[Dict[str, Any]]:
        """Get most common error types."""
        error_counts = {}

        for record in self._error_records:
            key = f"{record.error_type}:{record.context.component}"
            error_counts[key] = error_counts.get(key, 0) + 1

        # Sort by count and return top N
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

        return [{"error_key": key, "count": count} for key, count in sorted_errors[:limit]]


# === HTTP Error Exceptions ===


class StandardHTTPException(Exception):
    """Base HTTP exception class."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def rate_limit_error(detail: str = "Rate limit exceeded") -> StandardHTTPException:
    """Create a rate limit error (429)."""
    return StandardHTTPException(429, detail)


def service_unavailable_error(service: str) -> StandardHTTPException:
    """Create a service unavailable error (503)."""
    return StandardHTTPException(503, f"{service} service unavailable")


def bad_request_error(detail: str) -> StandardHTTPException:
    """Create a bad request error (400)."""
    return StandardHTTPException(400, detail)


# Legacy exception classes for compatibility
class InvalidFileError(Exception):
    """Exception raised when a file is invalid."""
    pass


class ProcessingError(Exception):
    """Exception raised during processing operations."""
    pass


# Global instance
# Note: UnifiedErrorHandler should be retrieved from DI container
# Use: container.get("unified_error_handler")
# Legacy global instance kept for backward compatibility during transition
unified_error_handler = UnifiedErrorHandler()
