# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock Audio Backend Implementation.

This module provides a clean mock audio backend implementation for testing and development.
It implements the AudioBackendProtocol interface and focuses purely on simulating audio
operations without requiring real hardware.
"""

import time
from typing import Optional, Any
import logging

from app.src.config import config
from app.src.domain.audio.backends.implementations.base_audio_backend import BaseAudioBackend
from app.src.domain.decorators.error_handler import handle_domain_errors

def handle_errors(*dargs, **dkwargs):
    def _decorator(func):
        return handle_domain_errors(*dargs, **dkwargs)(func)

    return _decorator

logger = logging.getLogger(__name__)


class MockAudioBackend(BaseAudioBackend):
    """Clean mock audio backend for testing and development.

    This implementation simulates audio playback without requiring real hardware.
    It provides predictable behavior for testing auto-advance and playlist functionality.
    """

    def __init__(self, playback_subject: Optional[Any] = None):
        """Initialize the mock audio backend."""
        super().__init__(playback_subject)
        self._track_duration = config.audio.mock_track_duration  # Simulated duration
        self._play_start_time: Optional[float] = None
        self._volume = 50  # Default volume
        self._initialized = False

        logger.info("🧪 Mock Audio Backend initialized")

    @handle_errors("initialize")
    def initialize(self) -> bool:
        """Initialize the audio backend (legacy compatibility method).

        Returns:
            bool: True if initialization was successful
        """
        with self._state_lock:
            self._initialized = True
        logger.debug("🧪 Mock: Audio backend initialized")
        return True

    @handle_errors("shutdown")
    def shutdown(self) -> None:
        """Shutdown the audio backend (legacy compatibility method)."""
        with self._state_lock:
            self._is_playing = False
            self._current_file_path = None
            self._play_start_time = None
            self._initialized = False
        logger.debug("🧪 Mock: Audio backend shutdown")

    # AudioBackendProtocol required methods
    @handle_errors("play")
    async def play(self, file_path: str) -> bool:
        """Play an audio file (AudioBackendProtocol interface)."""
        return self.play_file(file_path)

    @handle_errors("pause")
    async def pause(self) -> bool:
        """Pause current playback."""
        with self._state_lock:
            if self._is_playing:
                self._is_playing = False
                logger.info("🧪 Mock: Playback paused")
                return True
            return False

    @handle_errors("resume")
    async def resume(self) -> bool:
        """Resume paused playback."""
        with self._state_lock:
            if not self._is_playing and self._current_file_path:
                self._is_playing = True
                logger.info("🧪 Mock: Playback resumed")
                return True
            return False

    @handle_errors("stop")
    async def stop(self) -> bool:
        """Stop current playback (async version)."""
        with self._state_lock:
            self._is_playing = False
            self._current_file_path = None
            self._play_start_time = None
            logger.info("🧪 Mock: Playback stopped")
            return True

    @handle_errors("set_volume")
    async def set_volume(self, volume: int) -> bool:
        """Set playback volume."""
        if 0 <= volume <= 100:
            self._volume = volume
            logger.info(f"🧪 Mock: Volume set to {volume}")
            return True
        return False

    @handle_errors("get_volume")
    async def get_volume(self) -> int:
        """Get current volume level."""
        return getattr(self, '_volume', 50)

    @handle_errors("seek")
    async def seek(self, position_ms: int) -> bool:
        """Seek to a specific position."""
        if position_ms >= 0:
            logger.info(f"🧪 Mock: Seeked to {position_ms}ms")
            return True
        return False

    @handle_errors("get_position")
    async def get_position(self) -> Optional[int]:
        """Get current playback position."""
        # Update internal state to check for track completion
        self._update_internal_state()

        if self._is_playing and self._play_start_time:
            elapsed = time.time() - self._play_start_time
            return int(elapsed * 1000)  # Convert to ms
        return None

    @handle_errors("get_duration")
    async def get_duration(self) -> Optional[int]:
        """Get duration of current track."""
        if self._current_file_path:
            return int(self._track_duration * 1000)  # Convert to ms
        return None

    def get_duration_sync(self) -> float:
        """Get duration of current track in seconds (for unified_audio_player compatibility)."""
        if self._current_file_path:
            logger.debug(f"🧪 Mock: Returning duration: {self._track_duration:.1f}s")
            return self._track_duration
        return 0.0

    # Removed duplicate is_playing method - using property below

    @handle_errors("play_file")
    def play_file(self, file_path: str, duration_ms: Optional[int] = None) -> bool:
        """Play a single audio file (simulated).

        Args:
            file_path: Path to the audio file to play
            duration_ms: Optional duration hint in milliseconds

        Returns:
            bool: True if playback started successfully, False otherwise
        """
        path = self._validate_file_path(file_path)
        if not path:
            return False

        with self._state_lock:
            # Simulate stopping current playback
            self._is_playing = False

            # Use provided duration or default
            if duration_ms and duration_ms > 0:
                self._track_duration = duration_ms / 1000.0  # Convert to seconds
            else:
                self._track_duration = config.audio.mock_track_duration  # Use config default

            # Start "playing" the new file
            self._current_file_path = str(path)
            self._is_playing = True
            self._play_start_time = time.time()
            logger.info(f"🧪 Mock: Started playing {path.name} (duration: {self._track_duration:.1f}s)")
            self._notify_playback_event("track_started", {"file_path": str(path)})
            return True

    # Removed duplicate sync versions - using async versions above

    # Removed duplicate sync set_volume - using async version above

    def get_current_file(self) -> Optional[str]:
        """Get the currently playing file path.

        Returns:
            Optional[str]: Current file path or None
        """
        with self._state_lock:
            return self._current_file_path

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing (simulated).

        Returns:
            bool: True if playing, False otherwise
        """
        with self._state_lock:
            return self._is_playing

    @property
    def is_busy(self) -> bool:
        """Check if the backend is busy (simulated).

        This is used by PlaylistController to detect when a track has finished playing.

        Returns:
            bool: True if backend is busy, False if idle/finished
        """
        # Update internal state to check for track completion
        self._update_internal_state()

        with self._state_lock:
            # Check if track has finished based on duration
            if self._is_playing and self._play_start_time:
                elapsed = time.time() - self._play_start_time
                return elapsed < self._track_duration

            return self._is_playing

    def _update_internal_state(self) -> None:
        """Update internal state by checking if track has finished.

        This method should be called by monitoring systems to ensure
        state consistency without side effects in properties.
        """
        with self._state_lock:
            if self._is_playing and self._play_start_time:
                elapsed = time.time() - self._play_start_time
                if elapsed >= self._track_duration:
                    self._is_playing = False
                    logger.debug("🧪 Mock: Track finished, state updated")
                    self._notify_playback_event(
                        "track_ended",
                        {
                            "file_path": self._current_file_path,
                            "duration": self._track_duration,
                            "elapsed": elapsed,
                        },
                    )

    @handle_errors("cleanup")
    def cleanup(self) -> None:
        """Clean up audio resources (simulated)."""
        logger.info("🧪 Cleaning up mock audio backend")
        with self._state_lock:
            self._is_playing = False
            self._current_file_path = None
            self._play_start_time = None
        logger.info("🧪 Mock audio backend cleanup completed")
