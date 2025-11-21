# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Minimal monitoring interface (std logging based).

Provides get_logger and stubs for event monitor without cross-layer imports.
Uses lazy loading to avoid circular dependencies.
"""

from typing import Optional
import logging as _logging

# Lazy loaded references
_ImprovedLogger = None
_error_handler = None


def get_logger(name: str) -> object:
    """Get a logger instance for the specified module.

    Args:
        name: Module name (typically __name__)

    Returns:
        ImprovedLogger instance
    """
    # Lazy load to avoid circular dependencies
    global _ImprovedLogger
    if _ImprovedLogger is None:
        from app.src.monitoring.core.logger import ImprovedLogger
        _ImprovedLogger = ImprovedLogger
    return _ImprovedLogger(name)


def get_error_handler():
    """Get the unified error handler instance.

    Returns:
        Domain error handler instance
    """
    # Lazy load to avoid circular dependencies
    global _error_handler
    if _error_handler is None:
        from app.src.infrastructure.error_handling import unified_error_handler
        _error_handler = unified_error_handler
    return _error_handler


def get_event_monitor() -> Optional[object]:
    """Get event monitor instance (only if debug enabled).

    Returns:
        EventMonitor instance if debug mode is enabled, None otherwise
    """
    # Stubbed out in minimal implementation
    return None


def shutdown_monitoring():
    """Shutdown all monitoring components."""
    return None


def get_monitoring_statistics() -> dict:
    """Get comprehensive monitoring statistics.

    Returns:
        Dictionary with monitoring statistics
    """
    return {"active": False, "stub": True}


# Export public interface
__all__ = [
    "get_logger",
    "get_error_handler",
    "get_event_monitor",
    "shutdown_monitoring",
    "get_monitoring_statistics",
    # Monitoring config removed from public interface
]
