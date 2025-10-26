# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Helpers module initialization for TheOpenMusicBox backend.

Exposes utility classes for error handling, system dependency checking,
and exception management. Provides a centralized collection of helper
functionality used across the application.
"""

# This module is deprecated - all functionality has been migrated to domain layer
# Keeping only for backwards compatibility during transition period

from .system_dependency_checker import SystemDependencyChecker

# Import exceptions from domain layer for backwards compatibility
from app.src.infrastructure.error_handling.unified_error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorSeverity
)

# AppError is now replaced by the domain unified error handler
class AppError(Exception):
    """Deprecated - use domain error handling instead."""
    pass

__all__ = [
    "AppError",
    "ErrorCategory",
    "ErrorSeverity",
    "ErrorContext",
    "SystemDependencyChecker",
]
