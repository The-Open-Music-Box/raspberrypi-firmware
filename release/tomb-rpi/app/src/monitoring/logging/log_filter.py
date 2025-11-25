# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Log message filtering and cleanup utilities.

Provides filtering capabilities to ignore irrelevant log patterns and message
cleanup functions to normalize log output formatting for better readability.
"""

import re


class LogFilter:
    """Filter for log messages, ignoring known irrelevant patterns."""

    IGNORED_PATTERNS = [
        "pygame.*Hello from the pygame community.*",
        "Restarting with stat",
        "Debugger is active!",
        "Debugger PIN:.*",
        "wsgi starting up on.*",
    ]

    @classmethod
    def should_log(cls, message: str) -> bool:
        """Determine if a log message should be emitted."""
        return not any(re.match(pattern, message) for pattern in cls.IGNORED_PATTERNS)

    @classmethod
    def clean_message(cls, message: str) -> str:
        """Clean and normalize log message formatting for output."""
        message = re.sub(r"\[blue\]", "", str(message))
        message = re.sub(r"\[/.*?\]", "", message)
        message = re.sub(r"✓\s*✓", "✓", message)
        return message.strip()
