# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Audio Service Protocol for Domain-Driven Architecture.

This module defines the protocol interface for audio services,
promoting loose coupling and testability in the domain layer.
"""

from typing import Protocol, Dict, Any, Optional
from abc import abstractmethod


class AudioServiceProtocol(Protocol):
    """Protocol defining the audio service interface for domain architecture.

    This protocol ensures that any audio service implementation provides
    the necessary methods for audio playback, volume control, and state management.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the audio service is available and ready.

        Returns:
            True if audio service is available, False otherwise
        """
        ...

    @abstractmethod
    def play(self) -> bool:
        """Start or resume audio playback.

        Returns:
            True if operation was successful, False otherwise
        """
        ...

    @abstractmethod
    def pause(self) -> bool:
        """Pause audio playback.

        Returns:
            True if operation was successful, False otherwise
        """
        ...

    @abstractmethod
    def stop(self) -> bool:
        """Stop audio playback.

        Returns:
            True if operation was successful, False otherwise
        """
        ...

    @abstractmethod
    def is_playing(self) -> bool:
        """Check if audio is currently playing.

        Returns:
            True if audio is playing, False otherwise
        """
        ...

    @abstractmethod
    def get_volume(self) -> int:
        """Get current volume level.

        Returns:
            Volume level (0-100)
        """
        ...

    @abstractmethod
    def set_volume(self, volume: int) -> bool:
        """Set volume level.

        Args:
            volume: Volume level (0-100)

        Returns:
            True if operation was successful, False otherwise
        """
        ...

    @abstractmethod
    def get_position(self) -> float:
        """Get current playback position in seconds.

        Returns:
            Current position in seconds
        """
        ...

    @abstractmethod
    def set_position(self, position: float) -> bool:
        """Set playback position.

        Args:
            position: Position in seconds

        Returns:
            True if operation was successful, False otherwise
        """
        ...

    @abstractmethod
    def get_duration(self) -> Optional[float]:
        """Get duration of current track in seconds.

        Returns:
            Duration in seconds, or None if no track loaded
        """
        ...

    @abstractmethod
    def load_playlist(self, playlist_data: Dict[str, Any]) -> bool:
        """Load a playlist for playback.

        Args:
            playlist_data: Playlist data dictionary

        Returns:
            True if playlist was loaded successfully, False otherwise
        """
        ...

    @abstractmethod
    def next_track(self) -> bool:
        """Skip to next track.

        Returns:
            True if operation was successful, False otherwise
        """
        ...

    @abstractmethod
    def previous_track(self) -> bool:
        """Skip to previous track.

        Returns:
            True if operation was successful, False otherwise
        """
        ...

    @abstractmethod
    def get_current_track_index(self) -> int:
        """Get index of currently playing track.

        Returns:
            Track index (0-based)
        """
        ...

    @abstractmethod
    def get_track_count(self) -> int:
        """Get total number of tracks in playlist.

        Returns:
            Number of tracks
        """
        ...


# Type alias for convenience
AudioService = AudioServiceProtocol
