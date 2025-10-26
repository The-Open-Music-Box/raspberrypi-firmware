# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

import os
from pathlib import Path

# Read version from VERSION file at project root
_version_file = Path(__file__).parent.parent.parent / "VERSION"
if _version_file.exists():
    __version__ = _version_file.read_text().strip()
else:
    __version__ = "0.0.0-dev"
