# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""macOS Audio Backend Implementation.

This module provides a clean audio backend implementation for macOS using pygame
with Core Audio. It implements the AudioBackendProtocol interface and focuses
purely on audio playback, leaving playlist management to the PlaylistController.
"""

import os
import asyncio
import time
from pathlib import Path
from typing import Optional

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    pygame = None


from app.src.monitoring import get_logger
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors
from app.src.domain.protocols.notification_protocol import PlaybackNotifierProtocol as PlaybackSubject

from .base_audio_backend import BaseAudioBackend

logger = get_logger(__name__)


class MacOSAudioBackend(BaseAudioBackend):
    """Clean macOS audio backend implementation using pygame with Core Audio.

    This implementation focuses purely on audio playback operations and does not
    handle playlist logic, which is managed by the PlaylistController.
    """

    @handle_errors("__init__")
    def __init__(self, playback_subject: Optional[PlaybackSubject] = None):
        """Initialize the macOS audio backend."""
        super().__init__(playback_subject)
        self._mixer_initialized = False

        # Time tracking for position calculation
        self._play_start_time = None
        self._pause_time = None
        self._is_paused = False

        # Track current file and its duration
        self._current_file_path = None
        self._current_file_duration = None  # in seconds

        if not PYGAME_AVAILABLE:
            logger.error("❌ pygame not available for macOS audio backend")
            raise ImportError("pygame is required for macOS audio backend but not installed")

        # Set macOS-compatible pygame audio settings
        os.environ["SDL_AUDIODRIVER"] = "coreaudio"  # macOS native audio
        # Initialize pygame mixer for macOS
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=2048)
        pygame.mixer.init()
        self._mixer_initialized = True
        logger.info("✓ macOS Audio Backend initialized with Core Audio")

    @handle_errors("play_file")
    def play_file(self, file_path: str, duration_ms: Optional[int] = None) -> bool:
        """Play a single audio file.

        Args:
            file_path: Path to the audio file to play
            duration_ms: Optional track duration in milliseconds from playlist

        Returns:
            bool: True if playback started successfully, False otherwise
        """
        if not self._mixer_initialized:
            logger.error("Audio mixer not initialized")
            return False

        with self._state_lock:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"Audio file not found: {path}")
                return False
            # Stop any current playback with proper cleanup
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                # Wait for mixer to fully stop to avoid race conditions
                time.sleep(0.1)
            # Ensure mixer is in clean state
            pygame.mixer.music.unload()
            # Load and play the file with error handling
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            # Verify playback actually started
            if not pygame.mixer.music.get_busy():
                logger.warning(f"⚠️️ macOS: Playback may not have started for {path.name}"
                )
            # Update state and start timing
            self._is_playing = True
            self._current_file_path = str(path)

            # Use duration from playlist if provided, convert to seconds
            self._current_file_duration = (duration_ms / 1000.0) if duration_ms else None

            self._play_start_time = time.time()
            self._pause_time = None
            self._is_paused = False
            logger.info(f"🎵 macOS: Started playing {path.name}")
            return True

    @handle_errors("stop")
    def _stop_impl(self) -> bool:
        """Stop playback.

        Returns:
            bool: True if stopped successfully, False otherwise
        """
        with self._state_lock:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                # Brief pause to ensure clean stop
                time.sleep(0.05)
            # Properly unload to free resources
            pygame.mixer.music.unload()
            self._is_playing = False
            self._current_file_path = None
            self._current_file_duration = None
            # Reset timing
            self._play_start_time = None
            self._pause_time = None
            self._is_paused = False
        logger.info("⏹️ macOS: Playback stopped")
        return True

    @handle_errors("pause")
    def _pause_impl(self) -> bool:
        """Pause playbook.

        Returns:
            bool: True if paused successfully, False otherwise
        """
        if not self._is_playing:
            return False

        with self._state_lock:
            pygame.mixer.music.pause()
            self._is_playing = False
            self._is_paused = True
            self._pause_time = time.time()
        logger.info("⏸️ macOS: Playback paused")
        return True

    @handle_errors("resume")
    def _resume_impl(self) -> bool:
        """Resume paused playback.

        Returns:
            bool: True if resumed successfully, False otherwise
        """
        if self._is_playing or not self._current_file_path:
            return False

        with self._state_lock:
            pygame.mixer.music.unpause()
            self._is_playing = True

            # Adjust play start time to account for pause duration
            if self._pause_time and self._play_start_time:
                pause_duration = time.time() - self._pause_time
                self._play_start_time += pause_duration

            self._pause_time = None
            self._is_paused = False
        logger.info("▶️ macOS: Playback resumed")
        return True

    @handle_errors("get_position")
    def get_position(self) -> float:
        """Get current playback position in seconds.

        Returns:
            float: Current position in seconds, 0.0 if not available
        """
        with self._state_lock:
            if not self._current_file_path or not self._play_start_time:
                return 0.0

            # Calculate position based on elapsed time
            if self._is_paused and self._pause_time:
                # If paused, calculate position up to pause time
                position = self._pause_time - self._play_start_time
            elif self._is_playing:
                # If playing, calculate current position
                position = time.time() - self._play_start_time
            else:
                return 0.0

            return max(0.0, position)

    @handle_errors("set_volume_sync")
    def _set_volume_sync(self, volume: int) -> bool:
        """Set playback volume.

        Args:
            volume: Volume level (0-100)

        Returns:
            bool: True if volume was set successfully, False otherwise
        """
        with self._state_lock:
            self._volume = max(0, min(100, volume))
            # pygame volume is 0.0 to 1.0
            pygame_volume = self._volume / 100.0
            pygame.mixer.music.set_volume(pygame_volume)
        logger.debug(f"🔊 macOS: Volume set to {self._volume}%")
        return True

    @property
    def is_playing(self) -> bool:
        """Check if audio is currently playing.

        Returns:
            bool: True if playing, False otherwise
        """
        with self._state_lock:
            # Sync with pygame state
            if self._is_playing and not pygame.mixer.music.get_busy():
                self._is_playing = False
                logger.debug("macOS: Track finished, updated internal state")

            return self._is_playing

    @property
    def is_busy(self) -> bool:
        """Check if the backend is busy (playing or loading).

        This is used by PlaylistController to detect when a track has finished playing.

        Returns:
            bool: True if backend is busy, False if idle/finished
        """
        with self._state_lock:
            pygame_busy = pygame.mixer.music.get_busy()

            # Update internal state based on pygame state
            if self._is_playing and not pygame_busy:
                self._is_playing = False
                logger.debug("macOS: Track ended, backend no longer busy")

            return pygame_busy

    @handle_errors("cleanup")
    def cleanup(self) -> None:
        """Clean up audio resources."""
        logger.info("🧹 Cleaning up macOS audio backend")
        with self._state_lock:
            if self._mixer_initialized:
                pygame.mixer.music.stop()
            self._is_playing = False
            self._current_file_path = None
            self._current_file_duration = None
            # Reset timing
            self._play_start_time = None
            self._pause_time = None
            self._is_paused = False
        if self._mixer_initialized:
            pygame.mixer.quit()
            self._mixer_initialized = False
        logger.info("✓ macOS audio backend cleanup completed")

    # Async protocol methods (wrap sync implementations)
    async def play(self, file_path: str) -> bool:
        """Async wrapper for play_file."""
        return await asyncio.get_running_loop().run_in_executor(None, self.play_file, file_path)

    async def pause(self) -> bool:
        """Async wrapper for pause."""
        return self._pause_impl()

    async def resume(self) -> bool:
        """Async wrapper for resume."""
        return self._resume_impl()

    async def stop(self) -> bool:
        """Async wrapper for stop."""
        return self._stop_impl()

    async def get_volume(self) -> int:
        """Get current volume level."""
        with self._state_lock:
            return self._volume

    async def set_volume(self, volume: int) -> bool:
        """Async wrapper for set_volume (protocol requirement)."""
        return self._set_volume_sync(volume)

    async def seek(self, position_ms: int) -> bool:
        """Seek to a specific position (not implemented for pygame)."""
        logger.warning("⚠️ macOS: Seek not supported with pygame backend")
        return False


    async def get_duration(self) -> Optional[int]:
        """Get duration of current track.

        Returns:
            int: Duration in milliseconds or None if not available
        """
        if self._current_file_duration and self._current_file_duration > 0:
            duration_ms = int(self._current_file_duration * 1000)
            logger.debug(f"🍎 macOS: Returning duration: {duration_ms}ms ({self._current_file_duration:.1f}s)")
            return duration_ms
        return None
