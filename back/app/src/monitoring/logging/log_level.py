# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Log level enumeration for the monitoring system.

Defines standardized logging severity levels used throughout the application
for consistent log categorization and filtering.
"""

from enum import Enum


class LogLevel(Enum):
    """Enumeration for log severity levels used throughout the application."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
