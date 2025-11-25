# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Audio backend implementations for domain-driven architecture."""

# Import all implementations for easy access
from .macos_audio_backend import MacOSAudioBackend
from .wm8960_audio_backend import WM8960AudioBackend
from .mock_audio_backend import MockAudioBackend
from .base_audio_backend import BaseAudioBackend

__all__ = [
    "MacOSAudioBackend",
    "WM8960AudioBackend",
    "MockAudioBackend",
    "BaseAudioBackend",
]
