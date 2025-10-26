# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
AudioPlayer - Simplified audio control with single responsibility.

This controller ONLY handles audio playback operations.
NO playlist logic, NO state management beyond current playback status.
"""

from typing import Optional, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PlaybackState(Enum):
    """Enumeration of playback states."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class AudioPlayer:
    """
    Pure audio playback controller.

    Responsibilities:
    - Play audio files
    - Control playback (pause, resume, stop)
    - Manage volume
    - Report playback position and duration

    NOT responsible for:
    - Playlist management
    - Track navigation
    - File path resolution
    """

    def __init__(self, audio_backend):
        """
        Initialize the audio player.

        Args:
            audio_backend: The audio backend to use for playback
        """
        self._backend = audio_backend
        self._state = PlaybackState.STOPPED
        self._current_file: Optional[str] = None
        self._volume: int = 50  # Default volume 0-100

        logger.info(f"✅ AudioPlayer initialized with backend: {type(audio_backend).__name__}")

    # --- Core Playback Controls ---

    def play_file(self, file_path: str, duration_ms: Optional[int] = None) -> bool:
        """
        Play an audio file.

        Args:
            file_path: Full path to the audio file
            duration_ms: Optional duration hint in milliseconds

        Returns:
            bool: True if playback started successfully
        """
        if not file_path:
            logger.warning("Cannot play empty file path")
            return False

        try:
            # Stop current playback if any
            if self._state != PlaybackState.STOPPED:
                self.stop()

            # Start new playback
            if hasattr(self._backend, 'play_file'):
                # Use play_file if available (sync method)
                if duration_ms is not None:
                    success = self._backend.play_file(file_path, duration_ms=duration_ms)
                else:
                    success = self._backend.play_file(file_path)
            else:
                # Use async play method
                import asyncio
                loop = asyncio.new_event_loop()
                success = loop.run_until_complete(self._backend.play(file_path))
                loop.close()

            if success:
                self._current_file = file_path
                self._state = PlaybackState.PLAYING
                logger.info(f"▶️ Playing: {file_path}")
                return True
            else:
                logger.error(f"Failed to play: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Error playing file: {e}")
            return False

    def pause(self) -> bool:
        """
        Pause current playback.

        Returns:
            bool: True if paused successfully
        """
        if self._state != PlaybackState.PLAYING:
            logger.warning("Cannot pause - not playing")
            return False

        try:
            # Try sync method first (WM8960 has pause_sync)
            if hasattr(self._backend, 'pause_sync'):
                success = self._backend.pause_sync()
            elif hasattr(self._backend, 'pause'):
                import inspect
                if inspect.iscoroutinefunction(self._backend.pause):
                    logger.warning("pause is async but called from sync context")
                    success = False
                else:
                    success = self._backend.pause()
            else:
                success = False

            if success:
                self._state = PlaybackState.PAUSED
                logger.info("⏸️ Playback paused")
                return True
            else:
                logger.warning("Failed to pause playback")
                return False

        except Exception as e:
            logger.error(f"Error pausing: {e}")
            return False

    def resume(self) -> bool:
        """
        Resume paused playback.

        Returns:
            bool: True if resumed successfully
        """
        if self._state != PlaybackState.PAUSED:
            logger.warning("Cannot resume - not paused")
            return False

        try:
            # Try sync method first (WM8960 has resume_sync)
            if hasattr(self._backend, 'resume_sync'):
                success = self._backend.resume_sync()
            elif hasattr(self._backend, 'resume'):
                import inspect
                if inspect.iscoroutinefunction(self._backend.resume):
                    logger.warning("resume is async but called from sync context")
                    success = False
                else:
                    success = self._backend.resume()
            else:
                success = False

            if success:
                self._state = PlaybackState.PLAYING
                logger.info("▶️ Playback resumed")
                return True
            else:
                logger.warning("Failed to resume playback")
                return False

        except Exception as e:
            logger.error(f"Error resuming: {e}")
            return False

    def stop(self) -> bool:
        """
        Stop current playback.

        Returns:
            bool: True if stopped successfully
        """
        if self._state == PlaybackState.STOPPED:
            return True  # Already stopped

        try:
            # Try sync method first (WM8960 has stop_sync)
            if hasattr(self._backend, 'stop_sync'):
                success = self._backend.stop_sync()
            elif hasattr(self._backend, 'stop'):
                import inspect
                if inspect.iscoroutinefunction(self._backend.stop):
                    logger.warning("stop is async but called from sync context")
                    success = False
                else:
                    success = self._backend.stop()
            else:
                success = False

            self._state = PlaybackState.STOPPED
            self._current_file = None
            logger.info("⏹️ Playback stopped")
            return success

        except Exception as e:
            logger.error(f"Error stopping: {e}")
            self._state = PlaybackState.STOPPED
            self._current_file = None
            return False

    def toggle_pause(self) -> bool:
        """
        Toggle between play and pause.

        Returns:
            bool: True if toggled successfully
        """
        if self._state == PlaybackState.PLAYING:
            return self.pause()
        elif self._state == PlaybackState.PAUSED:
            return self.resume()
        else:
            logger.warning("Cannot toggle - playback stopped")
            return False

    # --- Volume Control ---

    def set_volume(self, volume: int) -> bool:
        """
        Set playback volume.

        Args:
            volume: Volume level (0-100)

        Returns:
            bool: True if volume set successfully
        """
        if not 0 <= volume <= 100:
            logger.warning(f"Invalid volume: {volume}")
            return False

        try:
            if hasattr(self._backend, 'set_volume'):
                import asyncio
                import inspect
                if inspect.iscoroutinefunction(self._backend.set_volume):
                    loop = asyncio.new_event_loop()
                    success = loop.run_until_complete(self._backend.set_volume(volume))
                    loop.close()
                else:
                    success = self._backend.set_volume(volume)

                if success:
                    self._volume = volume
                    logger.info(f"🔊 Volume set to {volume}%")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False

    def get_volume(self) -> int:
        """
        Get current volume level.

        Returns:
            int: Current volume (0-100)
        """
        return self._volume

    # --- Playback Information ---

    def get_position(self) -> float:
        """
        Get current playback position in seconds.

        Returns:
            float: Position in seconds, or 0 if not playing
        """
        if self._state == PlaybackState.STOPPED:
            return 0.0

        try:
            # Try sync method first (preferred for backends like WM8960)
            if hasattr(self._backend, 'get_position_sync'):
                position = self._backend.get_position_sync()
                if position is not None:
                    return float(position)  # Already in seconds

            # Fallback to get_position (which might return ms or be async)
            if hasattr(self._backend, 'get_position'):
                import inspect
                if inspect.iscoroutinefunction(self._backend.get_position):
                    # NEVER create new event loop - must be called from async context
                    logger.warning("get_position is async but called from sync context")
                    return 0.0
                else:
                    position_ms = self._backend.get_position()
                    if position_ms is not None:
                        return position_ms / 1000.0  # Convert to seconds

            return 0.0

        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return 0.0

    def get_duration(self) -> float:
        """
        Get duration of current track in seconds.

        Returns:
            float: Duration in seconds, or 0 if not available
        """
        if not self._current_file:
            return 0.0

        try:
            # Try get_duration first (sync method in WM8960 backend)
            if hasattr(self._backend, 'get_duration'):
                import inspect
                if not inspect.iscoroutinefunction(self._backend.get_duration):
                    # Sync method - call directly
                    duration = self._backend.get_duration()
                    if duration and duration > 0:
                        return float(duration)  # Already in seconds
                else:
                    # NEVER create new event loop - must be called from async context
                    logger.warning("get_duration is async but called from sync context")
                    return 0.0

            # Fallback to get_duration_sync if exists
            if hasattr(self._backend, 'get_duration_sync'):
                duration = self._backend.get_duration_sync()
                if duration and duration > 0:
                    return float(duration)

            return 0.0

        except Exception as e:
            logger.error(f"Error getting duration: {e}")
            return 0.0

    def seek(self, position_seconds: float) -> bool:
        """
        Seek to a specific position.

        Args:
            position_seconds: Target position in seconds

        Returns:
            bool: True if seek successful
        """
        if self._state == PlaybackState.STOPPED:
            logger.warning("Cannot seek - playback stopped")
            return False

        try:
            position_ms = int(position_seconds * 1000)

            if hasattr(self._backend, 'seek'):
                import asyncio
                import inspect
                if inspect.iscoroutinefunction(self._backend.seek):
                    loop = asyncio.new_event_loop()
                    success = loop.run_until_complete(self._backend.seek(position_ms))
                    loop.close()
                else:
                    success = self._backend.seek(position_ms)

                if success:
                    logger.info(f"⏩ Seeked to {position_seconds:.1f}s")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error seeking: {e}")
            return False

    # --- Status Queries ---

    def get_state(self) -> Dict[str, Any]:
        """
        Get current player state.

        Returns:
            Dict[str, Any]: Player state information
        """
        return {
            "state": self._state.value,
            "is_playing": self._state == PlaybackState.PLAYING,
            "is_paused": self._state == PlaybackState.PAUSED,
            "current_file": self._current_file,
            "volume": self._volume,
            "position": self.get_position(),
            "duration": self.get_duration()
        }

    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._state == PlaybackState.PLAYING

    def is_paused(self) -> bool:
        """Check if currently paused."""
        return self._state == PlaybackState.PAUSED

    def is_stopped(self) -> bool:
        """Check if currently stopped."""
        return self._state == PlaybackState.STOPPED

    def has_finished(self) -> bool:
        """
        Check if current track has finished playing.

        Returns:
            bool: True if track finished
        """
        if self._state != PlaybackState.PLAYING:
            return False

        # Check backend's is_busy property
        if hasattr(self._backend, 'is_busy'):
            is_busy = self._backend.is_busy
            if not is_busy:
                # Track has finished - update our state to reflect this
                logger.info("🏁 Track finished - backend is no longer busy")
                self._state = PlaybackState.STOPPED
                return True
            return False

        # Fallback: check if position >= duration
        position = self.get_position()
        duration = self.get_duration()
        if duration > 0 and position >= duration:
            logger.info(f"🏁 Track finished - position {position:.1f}s >= duration {duration:.1f}s")
            self._state = PlaybackState.STOPPED
            return True

        return False
