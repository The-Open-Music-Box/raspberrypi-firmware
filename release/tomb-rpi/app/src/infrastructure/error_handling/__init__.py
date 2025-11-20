# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Domain error handling package."""

from .unified_error_handler import (
    UnifiedErrorHandler,
    unified_error_handler,
    ErrorSeverity,
    ErrorCategory,
    ErrorContext,
    ErrorRecord,
)

__all__ = [
    "UnifiedErrorHandler",
    "unified_error_handler",
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorContext",
    "ErrorRecord",
]
