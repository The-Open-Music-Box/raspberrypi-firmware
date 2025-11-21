# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playback State Manager (DDD Architecture)

Single responsibility: Manages playback state following StateManagerProtocol.
Clean Domain-Driven Design implementation focused on state storage and retrieval.
"""

import time
from typing import Dict, Any, Optional
from app.src.monitoring import get_logger
from app.src.domain.protocols.state_manager_protocol import StateManagerProtocol, PlaybackState

logger = get_logger(__name__)


class PlaybackStateManager(StateManagerProtocol):
    """
    Manages playback state following clean DDD architecture.

    Single Responsibility: Playback state storage and management.

    Responsibilities:
    - Current playback state tracking
    - Track and playlist information storage
    - Position and volume state management
    - Error state handling
    - Protocol compliance (StateManagerProtocol)

    Does NOT handle:
    - Event broadcasting (delegated to StateEventCoordinator)
    - Serialization (delegated to StateSerializationService)
    - Client subscriptions (delegated to ClientSubscriptionManager)
    - Cleanup tasks (delegated to StateManagerLifecycleService)
    """

    def __init__(self):
        """Initialize playback state manager with clean state."""
        # Core state management following protocol
        self._current_state = PlaybackState.STOPPED
        self._current_track_info: Dict[str, Any] = {}
        self._current_playlist_info: Dict[str, Any] = {}
        self._current_position: float = 0.0
        self._current_volume: int = 50
        self._last_error: Optional[str] = None

        # Extended state for playlist navigation
        self._current_playlist: Optional[Dict[str, Any]] = None
        self._current_track_number: Optional[int] = None

        # Timestamp tracking
        self._last_updated = time.time()

        logger.info("PlaybackStateManager initialized with clean DDD architecture")

    # StateManagerProtocol implementation
    def get_current_state(self) -> PlaybackState:
        """Get current playback state."""
        return self._current_state

    def set_state(self, state: PlaybackState) -> None:
        """Set current playback state."""
        if self._current_state != state:
            old_state = self._current_state
            self._current_state = state
            self._last_updated = time.time()
            logger.debug(f"State updated: {old_state.value} -> {state.value}")

    def get_state_dict(self) -> Dict[str, Any]:
        """Get complete state as dictionary."""
        return {
            "state": self._current_state.value,
            "track": self._current_track_info,
            "playlist": self._current_playlist_info,
            "position": self._current_position,
            "volume": self._current_volume,
            "error": self._last_error,
            "last_updated": self._last_updated,
            # Extended state
            "current_playlist": self._current_playlist,
            "current_track_number": self._current_track_number,
        }

    def update_track_info(self, track_info: Dict[str, Any]) -> None:
        """Update current track information."""
        self._current_track_info = track_info.copy()
        self._last_updated = time.time()
        logger.debug(f"Track info updated: {track_info.get('title', 'Unknown')}")

    def update_playlist_info(self, playlist_info: Dict[str, Any]) -> None:
        """Update current playlist information."""
        self._current_playlist_info = playlist_info.copy()
        self._last_updated = time.time()
        logger.debug(f"Playlist info updated: {playlist_info.get('title', 'Unknown')}")

    def update_position(self, position_seconds: float) -> None:
        """Update current playback position."""
        self._current_position = max(0.0, position_seconds)
        # Don't log position updates as they're very frequent

    def update_volume(self, volume: int) -> None:
        """Update current volume level."""
        self._current_volume = max(0, min(100, volume))
        self._last_updated = time.time()
        logger.debug(f"Volume updated to: {self._current_volume}")

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
            logger.debug("Error state cleared")

    def get_last_error(self) -> Optional[str]:
        """Get last error message."""
        return self._last_error

    # Extended state management methods
    def get_current_playlist(self) -> Optional[Dict[str, Any]]:
        """Get current playlist information.

        Returns:
            Current playlist data or None if no playlist is loaded
        """
        return self._current_playlist

    def set_current_playlist(self, playlist: Optional[Dict[str, Any]]) -> None:
        """Set current playlist information.

        Args:
            playlist: Playlist data to set as current
        """
        self._current_playlist = playlist
        self._last_updated = time.time()
        logger.debug(f"Current playlist updated: {playlist.get('title', 'Unknown') if playlist else 'None'}"
        )

    def get_current_track_number(self) -> Optional[int]:
        """Get current track number in playlist.

        Returns:
            Current track number (1-based) or None if no track is playing
        """
        return self._current_track_number

    def set_current_track_number(self, track_number: Optional[int]) -> None:
        """Set current track number in playlist.

        Args:
            track_number: Track number to set (1-based)
        """
        self._current_track_number = track_number
        self._last_updated = time.time()
        logger.debug(f"Current track number updated: {track_number}")

    # Utility methods
    def get_position_seconds(self) -> float:
        """Get current position in seconds."""
        return self._current_position

    def get_volume(self) -> int:
        """Get current volume level."""
        return self._current_volume

    def get_last_updated(self) -> float:
        """Get timestamp of last state update."""
        return self._last_updated

    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self._current_state == PlaybackState.PLAYING

    def is_paused(self) -> bool:
        """Check if currently paused."""
        return self._current_state == PlaybackState.PAUSED

    def is_stopped(self) -> bool:
        """Check if currently stopped."""
        return self._current_state == PlaybackState.STOPPED

    def is_error(self) -> bool:
        """Check if in error state."""
        return self._current_state == PlaybackState.ERROR

    def reset_state(self) -> None:
        """Reset to clean initial state."""
        self._current_state = PlaybackState.STOPPED
        self._current_track_info = {}
        self._current_playlist_info = {}
        self._current_position = 0.0
        self._current_volume = 50
        self._last_error = None
        self._current_playlist = None
        self._current_track_number = None
        self._last_updated = time.time()
        logger.info("PlaybackStateManager reset to initial state")