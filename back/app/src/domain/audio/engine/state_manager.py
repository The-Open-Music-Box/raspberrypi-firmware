# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""State manager implementation."""

import time
from typing import Dict, Any, Optional

from app.src.monitoring import get_logger
from app.src.domain.protocols.state_manager_protocol import StateManagerProtocol, PlaybackState

logger = get_logger(__name__)


class StateManager(StateManagerProtocol):
    """Simple state manager implementation for audio state."""

    def __init__(self):
        self._current_state = PlaybackState.STOPPED
        self._track_info: Dict[str, Any] = {}
        self._playlist_info: Dict[str, Any] = {}
        self._position_seconds = 0.0
        self._volume = 50
        self._last_error: Optional[str] = None
        self._last_updated = time.time()

    def get_current_state(self) -> PlaybackState:
        """Get current playback state."""
        return self._current_state

    def set_state(self, state: PlaybackState) -> None:
        """Set current playback state."""
        if self._current_state != state:
            old_state = self._current_state
            self._current_state = state
            self._last_updated = time.time()
            logger.info(f"State changed: {old_state.value} -> {state.value}")

    def get_state_dict(self) -> Dict[str, Any]:
        """Get complete state as dictionary."""
        return {
            "state": self._current_state.value,
            "position_seconds": self._position_seconds,
            "volume": self._volume,
            "last_error": self._last_error,
            "last_updated": self._last_updated,
            "track_info": self._track_info.copy(),
            "playlist_info": self._playlist_info.copy(),
        }

    def update_track_info(self, track_info: Dict[str, Any]) -> None:
        """Update current track information."""
        self._track_info = track_info.copy()
        self._last_updated = time.time()
        logger.debug(f"Track info updated: {track_info.get('title', 'Unknown')}")

    def update_playlist_info(self, playlist_info: Dict[str, Any]) -> None:
        """Update current playlist information."""
        self._playlist_info = playlist_info.copy()
        self._last_updated = time.time()
        logger.debug(f"Playlist info updated: {playlist_info.get('title', 'Unknown')}"
        )

    def update_position(self, position_seconds: float) -> None:
        """Update current playback position."""
        self._position_seconds = max(0.0, position_seconds)
        # Don't log this as it's very frequent

    def update_volume(self, volume: int) -> None:
        """Update current volume level."""
        self._volume = max(0, min(100, volume))
        self._last_updated = time.time()
        logger.debug(f"Volume updated: {self._volume}")

    def set_error(self, error_message: str) -> None:
        """Set error state with message."""
        self._last_error = error_message
        self._current_state = PlaybackState.ERROR
        self._last_updated = time.time()
        logger.error(f"Error state set: {error_message}")

    def clear_error(self) -> None:
        """Clear error state."""
        if self._last_error:
            self._last_error = None
            if self._current_state == PlaybackState.ERROR:
                self._current_state = PlaybackState.STOPPED
            self._last_updated = time.time()
            logger.info("Error state cleared")

    def get_last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error
