# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""State manager protocol for dependency injection."""

from typing import Protocol, Dict, Any, Optional
from enum import Enum


class PlaybackState(Enum):
    """Enumeration of playback states."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    LOADING = "loading"
    ERROR = "error"


class StateManagerProtocol(Protocol):
    """Protocol defining the interface for state management."""

    def get_current_state(self) -> PlaybackState:
        """Get current playback state."""
        ...

    def set_state(self, state: PlaybackState) -> None:
        """Set current playback state."""
        ...

    def get_state_dict(self) -> Dict[str, Any]:
        """Get complete state as dictionary."""
        ...

    def update_track_info(self, track_info: Dict[str, Any]) -> None:
        """Update current track information."""
        ...

    def update_playlist_info(self, playlist_info: Dict[str, Any]) -> None:
        """Update current playlist information."""
        ...

    def update_position(self, position_seconds: float) -> None:
        """Update current playback position."""
        ...

    def update_volume(self, volume: int) -> None:
        """Update current volume level."""
        ...

    def set_error(self, error_message: str) -> None:
        """Set error state with message."""
        ...

    def clear_error(self) -> None:
        """Clear error state."""
        ...

    def get_last_error(self) -> Optional[str]:
        """Get last error message."""
        ...
