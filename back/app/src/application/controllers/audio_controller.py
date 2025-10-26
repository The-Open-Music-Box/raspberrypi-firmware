# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
AudioController - DDD Clean Architecture Implementation

This controller provides audio control functionality using clean DDD AudioPlayer implementation.
Maintains full AudioController API while following proper DDD architecture patterns.
"""

from typing import Dict, Any, Optional
import logging

from app.src.application.controllers.audio_player_controller import AudioPlayer, PlaybackState
from app.src.services.error.unified_error_decorator import handle_errors

logger = logging.getLogger(__name__)


class AudioController:
    """
    Clean DDD AudioController implementation using AudioPlayer.

    This controller maintains the AudioController API while delegating to the clean
    DDD AudioPlayer implementation, following proper DDD architecture patterns.
    """

    def __init__(self, audio_service=None, config=None, state_manager=None):
        """Initialize AudioController with DDD AudioPlayer.

        Args:
            audio_service: The underlying audio service for hardware operations
            config: Configuration object with audio settings
            state_manager: StateManager for broadcasting state changes
        """
        self._config = config or {}
        self._state_manager = state_manager
        self._current_volume = 50  # Default volume

        # Extract backend for AudioPlayer
        self._backend = None
        if audio_service:
            if hasattr(audio_service, "_backend") and audio_service._backend:
                self._backend = audio_service._backend
            else:
                self._backend = audio_service

        # Initialize DDD AudioPlayer
        if self._backend:
            self._audio_player = AudioPlayer(self._backend)
            logger.info("AudioController initialized with DDD AudioPlayer")
        else:
            self._audio_player = None
            logger.warning("AudioController initialized without backend")

        # Store audio_service reference for backward compatibility
        self._audio_service = audio_service

    @property
    def audio_service(self):
        """Get the underlying audio service."""
        return self._audio_service

    @handle_errors("is_available")
    def is_available(self) -> bool:
        """Check if audio service is available."""
        return self._backend is not None and getattr(self._backend, "is_available", lambda: False)()

    @handle_errors("play")
    def play(self, track_path=None) -> bool:
        """Play audio track from given path."""
        if not track_path:
            logger.warning("No track path provided for playback")
            return False

        if not self._audio_player:
            logger.error("No audio player available")
            return False

        return self._audio_player.play_file(track_path)

    @handle_errors("pause")
    def pause(self) -> bool:
        """Pause current audio playback."""
        if not self._audio_player:
            logger.error("No audio player available for pause")
            return False

        return self._audio_player.pause()

    @handle_errors("resume")
    def resume(self) -> bool:
        """Resume paused audio playback."""
        if not self._audio_player:
            logger.error("No audio player available for resume")
            return False

        return self._audio_player.resume()

    @handle_errors("stop")
    def stop(self) -> bool:
        """Stop audio playback completely."""
        if not self._audio_player:
            logger.error("No audio player available for stop")
            return False

        return self._audio_player.stop()

    @handle_errors("toggle_play_pause")
    def toggle_play_pause(self) -> bool:
        """Toggle between play and pause states."""
        if not self._audio_player:
            logger.warning("No audio player available for toggle")
            return False

        current_state = self._audio_player.get_state()
        if current_state == PlaybackState.PLAYING:
            return self.pause()
        elif current_state == PlaybackState.PAUSED:
            return self.resume()
        else:
            logger.warning("Cannot toggle: no audio currently loaded")
            return False

    def toggle_playback(self) -> bool:
        """Alias for toggle_play_pause for backward compatibility."""
        return self.toggle_play_pause()

    @handle_errors("seek_to")
    def seek_to(self, position_ms: int) -> bool:
        """Seek to specific position in current track."""
        if not self._audio_player:
            logger.error("No audio player available for seek")
            return False

        position_seconds = position_ms / 1000.0
        return self._audio_player.seek(position_seconds)

    @handle_errors("is_playing")
    def is_playing(self) -> bool:
        """Check if audio is currently playing."""
        if not self._audio_player:
            return False

        return self._audio_player.is_playing()

    def get_playback_state(self) -> str:
        """Get current playback state as string."""
        if not self._audio_player:
            return "stopped"

        state = self._audio_player.get_state()
        return state.value

    @handle_errors("set_volume")
    def set_volume(self, volume: int) -> bool:
        """Set audio volume."""
        volume = max(0, min(100, volume))

        if not self._audio_player:
            self._current_volume = volume
            logger.warning(f"No player available, stored volume: {volume}%")
            return True

        success = self._audio_player.set_volume(volume)
        if success:
            self._current_volume = volume
        return success

    def get_current_volume(self) -> int:
        """Get current volume level (0-100)."""
        if self._audio_player:
            return self._audio_player.get_volume()
        return self._current_volume

    def get_volume(self) -> int:
        """Alias for get_current_volume for compatibility."""
        return self.get_current_volume()

    @handle_errors("volume_up")
    def volume_up(self, step: int = 5) -> bool:
        """Increase volume by specified step."""
        current_vol = self.get_current_volume()
        new_volume = min(100, current_vol + step)
        return self.set_volume(new_volume)

    def increase_volume(self, step: int = 5) -> bool:
        """Alias for volume_up for backward compatibility."""
        return self.volume_up(step)

    @handle_errors("volume_down")
    def volume_down(self, step: int = 5) -> bool:
        """Decrease volume by specified step."""
        current_vol = self.get_current_volume()
        new_volume = max(0, current_vol - step)
        return self.set_volume(new_volume)

    def decrease_volume(self, step: int = 5) -> bool:
        """Alias for volume_down for backward compatibility."""
        return self.volume_down(step)

    def get_current_position(self) -> float:
        """Get current playback position in seconds."""
        if not self._audio_player:
            return 0.0

        return self._audio_player.get_position()

    def get_duration(self) -> float:
        """Get total duration of current track in seconds."""
        if not self._audio_player:
            return 0.0

        return self._audio_player.get_duration()

    async def get_playback_status(self) -> Dict[str, Any]:
        """Get comprehensive playback status for API responses."""
        try:
            current_position = self.get_current_position()
            duration = self.get_duration()

            status = {
                "is_playing": self.is_playing(),
                "state": self.get_playback_state(),
                "position": current_position,
                "duration": duration,
                "volume": self.get_current_volume(),
                "backend_available": self.is_available(),
                "current_track": None,  # No track info in pure audio controller
                "playlist_info": None,  # No playlist info in pure audio controller
                "controller_type": "AudioController",
                "supports_seek": self._audio_player is not None,
                "supports_volume": self._audio_player is not None,
            }

            return status

        except Exception as e:
            logger.error(f"❌ Error getting playback status: {e}")
            return {
                "is_playing": False,
                "state": "error",
                "position": 0.0,
                "duration": 0.0,
                "volume": self._current_volume,
                "backend_available": False,
                "error": str(e)
            }

    # Additional methods from AudioPlayer for enhanced compatibility
    def get_state(self) -> PlaybackState:
        """Get current playback state as enum."""
        if not self._audio_player:
            return PlaybackState.STOPPED
        return self._audio_player.get_state()

    def get_current_file(self) -> Optional[str]:
        """Get currently loaded file path."""
        if not self._audio_player:
            return None
        return self._audio_player.get_current_file()
