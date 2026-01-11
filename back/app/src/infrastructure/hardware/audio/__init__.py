# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Audio hardware infrastructure implementations.

This package contains hardware-specific implementations for audio-related
functionality including headphone jack detection.
"""

from .base_jack_detection import BaseJackDetection
from .gpio_jack_detection import GPIOJackDetection
from .jack_detection_factory import JackDetectionFactory
from .mock_jack_detection import MockJackDetection

__all__ = [
    "BaseJackDetection",
    "GPIOJackDetection",
    "JackDetectionFactory",
    "MockJackDetection",
]
