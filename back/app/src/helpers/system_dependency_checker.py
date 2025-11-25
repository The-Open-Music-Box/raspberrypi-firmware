# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""System dependency checker for TheOpenMusicBox backend.

Provides utilities to verify that required system dependencies (like FFmpeg)
are properly installed and accessible before application startup. Helps ensure
a smooth runtime experience by catching missing dependencies early.
"""

import shutil
import subprocess  # nosec B404 - subprocess required for system dependency verification
from dataclasses import dataclass

from app.src.monitoring import get_logger

logger = get_logger(__name__)


@dataclass
class DependencyError:
    name: str
    message: str


class SystemDependencyChecker:
    @staticmethod
    def check_ffmpeg() -> DependencyError | None:
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            return DependencyError(name="ffmpeg", message="FFmpeg binary not found in PATH")

        try:
            # Hardcoded ffmpeg command for version check, not user input
            subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)  # nosec B603 B607
            return None
        except Exception as e:
            return DependencyError(name="ffmpeg", message=f"Error executing FFmpeg: {e!s}")

    @staticmethod
    def check_dependencies() -> list[DependencyError]:
        errors = []
        ffmpeg_error = SystemDependencyChecker.check_ffmpeg()
        if ffmpeg_error:
            errors.append(ffmpeg_error)
        return errors
