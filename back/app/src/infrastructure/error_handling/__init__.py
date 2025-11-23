# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Domain error handling package."""

from .unified_error_handler import (
    ErrorCategory,
    ErrorContext,
    ErrorRecord,
    ErrorSeverity,
    UnifiedErrorHandler,
    unified_error_handler,
)

__all__ = [
    "ErrorCategory",
    "ErrorContext",
    "ErrorRecord",
    "ErrorSeverity",
    "UnifiedErrorHandler",
    "unified_error_handler",
]
