# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Pure audio playback controller - no data management."""

import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from app.src.monitoring import get_logger
from app.src.domain.decorators.error_handler import handle_domain_errors

logger = get_logger(__name__)


@dataclass
class PlaybackState:
    """Current playback state."""
    is_playing: bool = False
    current_track_id: Optional[str] = None
    position_ms: int = 0
    volume: int = 50
    playlist_id: Optional[str] = None


class PlaybackController:
    """Pure audio playback controller.

    Responsibilities:
    - Control audio playback (play/pause/stop)
    - Track position management
    - Volume control
    - Playback state tracking

    NOT responsible for:
    - Playlist CRUD operations (belongs to data domain)
    - Track metadata management (belongs to data domain)
    """

    def __init__(self, audio_backend):
        """Initialize playback controller.

        Args:
            audio_backend: Audio backend for playback operations
        """
        self._backend = audio_backend
        self._state = PlaybackState()
        logger.info("✅ PlaybackController initialized (audio-only)")

    @handle_domain_errors(operation_name="play_track")
    async def play_track(self, track_file_path: str, track_id: str) -> bool:
        """Play a specific track.

        Args:
            track_file_path: Path to the audio file
            track_id: ID of the track for state tracking

        Returns:
            True if playback started successfully
        """
        try:
            success = await self._backend.play(track_file_path)
            if success:
                self._state.is_playing = True
                self._state.current_track_id = track_id
                logger.info(f"✅ Playing track: {track_id}")
            return success
        except Exception as e:
            logger.error(f"❌ Failed to play track {track_id}: {e}")
            return False

    @handle_domain_errors(operation_name="pause")
    async def pause(self) -> bool:
        """Pause current playback."""
        try:
            success = await self._backend.pause()
            if success:
                self._state.is_playing = False
                logger.info("⏸️ Playback paused")
            return success
        except Exception as e:
            logger.error(f"❌ Failed to pause: {e}")
            return False

    @handle_domain_errors(operation_name="resume")
    async def resume(self) -> bool:
        """Resume paused playback."""
        try:
            success = await self._backend.resume()
            if success:
                self._state.is_playing = True
                logger.info("▶️ Playback resumed")
            return success
        except Exception as e:
            logger.error(f"❌ Failed to resume: {e}")
            return False

    @handle_domain_errors(operation_name="stop")
    async def stop(self) -> bool:
        """Stop current playback."""
        try:
            success = await self._backend.stop()
            if success:
                self._state.is_playing = False
                self._state.current_track_id = None
                self._state.position_ms = 0
                logger.info("⏹️ Playback stopped")
            return success
        except Exception as e:
            logger.error(f"❌ Failed to stop: {e}")
            return False

    @handle_domain_errors(operation_name="set_volume")
    async def set_volume(self, volume: int) -> bool:
        """Set playback volume.

        Args:
            volume: Volume level (0-100)

        Returns:
            True if volume was set successfully
        """
        try:
            volume = max(0, min(100, volume))  # Clamp to 0-100
            success = await self._backend.set_volume(volume)
            if success:
                self._state.volume = volume
                logger.info(f"🔊 Volume set to {volume}")
            return success
        except Exception as e:
            logger.error(f"❌ Failed to set volume: {e}")
            return False

    @handle_domain_errors(operation_name="seek")
    async def seek(self, position_ms: int) -> bool:
        """Seek to a specific position.

        Args:
            position_ms: Position in milliseconds

        Returns:
            True if seek was successful
        """
        try:
            success = await self._backend.seek(position_ms)
            if success:
                self._state.position_ms = position_ms
                logger.info(f"⏭️ Seeked to position {position_ms}ms")
            return success
        except Exception as e:
            logger.error(f"❌ Failed to seek: {e}")
            return False

    def get_playback_state(self) -> Dict[str, Any]:
        """Get current playback state.

        Returns:
            Dictionary with current playback state
        """
        return {
            'is_playing': self._state.is_playing,
            'current_track_id': self._state.current_track_id,
            'position_ms': self._state.position_ms,
            'volume': self._state.volume,
            'playlist_id': self._state.playlist_id
        }

    @handle_domain_errors(operation_name="update_position")
    async def update_position(self) -> Optional[int]:
        """Update current position from backend.

        Returns:
            Current position in milliseconds or None if not playing
        """
        if not self._state.is_playing:
            return None

        try:
            position = await self._backend.get_position()
            if position is not None:
                self._state.position_ms = position
            return position
        except Exception as e:
            logger.error(f"❌ Failed to get position: {e}")
            return None

    def set_playlist_context(self, playlist_id: str):
        """Set the current playlist context for state tracking.

        Args:
            playlist_id: ID of the current playlist
        """
        self._state.playlist_id = playlist_id
        logger.info(f"📋 Playlist context set to: {playlist_id}")

    def clear_playlist_context(self):
        """Clear the current playlist context."""
        self._state.playlist_id = None
        logger.info("📋 Playlist context cleared")