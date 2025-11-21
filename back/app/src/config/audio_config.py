# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Audio configuration settings for TheOpenMusicBox.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class AudioConfig:
    """
    Configuration parameters for audio playback and control.

    This is the single source of truth for all audio-related settings.
    """

    # Volume settings
    default_volume: int = 80  # Default system volume (0-100)
    volume_step: int = 5  # Volume change step for encoder/buttons
    min_volume: int = 0  # Minimum allowed volume
    max_volume: int = 100  # Maximum allowed volume

    # Playback settings
    fade_in_duration: float = 0.5  # Fade in duration in seconds
    fade_out_duration: float = 0.5  # Fade out duration in seconds
    crossfade_duration: float = 2.0  # Crossfade between tracks in seconds
    buffer_size: int = 4096  # Audio buffer size in bytes

    # Audio format settings
    sample_rate: int = 44100  # Sample rate in Hz
    channels: int = 2  # Number of audio channels (1=mono, 2=stereo)
    bits_per_sample: int = 16  # Bit depth

    # SDL environment settings for pygame
    sdl_audiodriver: str = "alsa"  # Audio driver (alsa, pulseaudio, etc.)
    sdl_audiodev: str = "default"  # Audio device (uses ALSA default, configured for WM8960)
    sdl_videodriver: str = "dummy"  # Video driver (dummy to disable video)

    # Mock audio settings for development/testing
    mock_track_duration: float = 30.0  # Default duration for mock tracks in seconds (shortened for testing)

    # Progress tracking settings
    progress_update_interval: float = 0.1  # Update interval in seconds for progress tracking

    # File format support
    supported_formats: List[str] = None

    def __post_init__(self):
        """
        Initialize default values for mutable fields.
        """
        if self.supported_formats is None:
            self.supported_formats = ["mp3", "wav", "flac", "ogg", "m4a"]

    def validate(self) -> None:
        """
        Validate configuration values.
        """
        if not 0 <= self.default_volume <= 100:
            raise ValueError(f"default_volume must be between 0 and 100, got {self.default_volume}")

        if not 1 <= self.volume_step <= 20:
            raise ValueError(f"volume_step must be between 1 and 20, got {self.volume_step}")

        if self.min_volume < 0 or self.max_volume > 100:
            raise ValueError("Volume limits must be between 0 and 100")

        if self.min_volume >= self.max_volume:
            raise ValueError("min_volume must be less than max_volume")
