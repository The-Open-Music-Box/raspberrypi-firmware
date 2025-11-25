# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Color scheme definitions for logging system.

Provides color and symbol mappings for different log levels using colorama
to enhance log readability and visual distinction between severity levels.
"""

from colorama import Back, Fore


class ColorScheme:
    """Defines color and symbol schemes for log levels."""

    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Back.WHITE,
    }

    SYMBOLS = {"DEBUG": "→", "INFO": "✓", "WARNING": "⚠️", "ERROR": "✗", "CRITICAL": "‼"}
