# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Upload Domain Constants

Domain-level constants for upload validation and business rules.
These represent invariants and constraints defined by the business domain.
"""

# Windows reserved filenames that cannot be used
# This is a domain business rule - these names are fundamentally invalid for files
# See: https://docs.microsoft.com/en-us/windows/win32/fileio/naming-a-file
WINDOWS_RESERVED_NAMES = frozenset({
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
})
