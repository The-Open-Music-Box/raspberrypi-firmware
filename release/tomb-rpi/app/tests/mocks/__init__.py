# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock implementations for testing hardware dependencies.

This package contains mock implementations of hardware-dependent services
to enable testing without actual hardware components.
"""

from .mock_audio_service import MockAudioService
from .mock_controls_manager import MockControlsManager
from .mock_nfc_service import MockNfcService

__all__ = [
    "MockAudioService",
    "MockControlsManager",
    "MockNfcService",
]
