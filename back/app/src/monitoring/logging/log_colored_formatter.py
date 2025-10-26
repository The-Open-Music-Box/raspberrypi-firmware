# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Colored log formatter for enhanced console output.

Implements a custom logging formatter that applies colors and symbols to log
messages based on severity level, with startup phase detection and component
highlighting for improved readability.
"""

import logging

from colorama import Fore, Style

from .log_base_formatter import BaseLogFormatter
from .log_color_scheme import ColorScheme
from .log_filter import LogFilter


class ColoredLogFormatter(BaseLogFormatter, logging.Formatter):
    """Formatter for colored log output with level and component highlighting."""

    def __init__(self, fmt=None, datefmt=None):
        BaseLogFormatter.__init__(self)
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record):
        """Format the log record with color and symbols for output."""
        if not LogFilter.should_log(record.msg):
            return ""
        record.msg = LogFilter.clean_message(record.msg)
        if not record.msg.strip():
            return ""

        color = ColorScheme.COLORS.get(record.levelname, Fore.WHITE)
        symbol = ColorScheme.SYMBOLS.get(record.levelname, "•")
        record.name = self._simplify_component_name(record.name)
        if "Initializing" in str(record.msg):
            self._startup_phase = self._extract_component(record.msg)
            return f"{Fore.CYAN}◉ Initializing {self._startup_phase}...{Style.RESET_ALL}"

        elif "ready" in str(record.msg) and self._startup_phase:
            result = f"{Fore.GREEN}  ↳ {self._startup_phase} ready{Style.RESET_ALL}"
            self._startup_phase = None
            return result

        record.levelname = f"{color}{record.levelname:<8}{Style.RESET_ALL}"
        record.name = f"{Fore.BLUE}{record.name:<20}{Style.RESET_ALL}"
        record.msg = f"{color}{symbol} {record.msg}{Style.RESET_ALL}"

        return super().format(record)
