# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock audio service for testing.

This module provides a mock implementation of the audio service interface
for testing purposes without requiring actual audio hardware.
"""

from typing import Dict, Optional

from app.src.domain.protocols.audio_service_protocol import AudioServiceProtocol


class MockAudioService(AudioServiceProtocol):
    """Mock audio service implementation for testing.

    Simulates audio service behavior without actual hardware dependencies,
    enabling comprehensive testing of audio-related functionality.
    """

    def __init__(self):
        """Initialize the mock audio service."""
        self._is_available = True
        self._is_playing = False
        self._volume = 50
        self._current_track = 0
        self._playlist_data: Optional[Dict] = None
        self._track_count = 0

    def is_available(self) -> bool:
        """Check if the audio service is available and ready.

        Returns:
            True if audio service is available, False otherwise
        """
        return self._is_available

    def play(self) -> bool:
        """Start or resume audio playback.

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available:
            return False
        self._is_playing = True
        return True

    def pause(self) -> bool:
        """Pause audio playback.

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available:
            return False
        self._is_playing = False
        return True

    def stop(self) -> bool:
        """Stop audio playback.

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available:
            return False
        self._is_playing = False
        self._current_track = 0
        return True

    def resume(self) -> bool:
        """Resume audio playback from paused state.

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available:
            return False
        self._is_playing = True
        return True

    def is_playing(self) -> bool:
        """Check if audio is currently playing.

        Returns:
            True if audio is playing, False otherwise
        """
        return self._is_playing

    def get_position(self) -> float:
        """Get current playback position in seconds.

        Returns:
            Current position in seconds
        """
        # For mocking, return a simulated position
        return 30.0 if self._is_playing else 0.0

    def get_duration(self) -> Optional[float]:
        """Get duration of current track in seconds.

        Returns:
            Duration in seconds, or None if no track loaded
        """
        if not self._playlist_data or self._track_count == 0:
            return None
        # For mocking, return a simulated duration
        return 180.0  # 3 minutes

    def get_current_track_index(self) -> int:
        """Get index of currently playing track.

        Returns:
            Track index (0-based)
        """
        return self._current_track

    def get_track_count(self) -> int:
        """Get total number of tracks in playlist.

        Returns:
            Number of tracks
        """
        return self._track_count

    def set_volume(self, volume: int) -> bool:
        """Set the audio volume level.

        Args:
            volume: Volume level (0-100)

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available or volume < 0 or volume > 100:
            return False
        self._volume = volume
        return True

    def get_volume(self) -> int:
        """Get the current audio volume level.

        Returns:
            Current volume level (0-100)
        """
        return self._volume

    def set_position(self, position_seconds: float) -> bool:
        """Set the playback position in seconds.

        Args:
            position_seconds: Position in seconds

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available:
            return False
        # In a real implementation, this would seek to the position
        # For mocking, we just return success
        return True

    def next_track(self) -> bool:
        """Skip to the next track.

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available or not self._playlist_data:
            return False

        if self._current_track < self._track_count - 1:
            self._current_track += 1
            return True
        return False

    def previous_track(self) -> bool:
        """Go to the previous track.

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available or not self._playlist_data:
            return False

        if self._current_track > 0:
            self._current_track -= 1
            return True
        return False

    def play_track(self, track_number: int) -> bool:
        """Play a specific track by number.

        Args:
            track_number: Track number to play

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available or not self._playlist_data:
            return False

        if 1 <= track_number <= self._track_count:
            self._current_track = track_number - 1
            self._is_playing = True
            return True
        return False

    def load_playlist(self, playlist_data: dict) -> bool:
        """Load a playlist for playback.

        Args:
            playlist_data: Playlist data dictionary

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available:
            return False

        self._playlist_data = playlist_data
        self._track_count = len(playlist_data.get("tracks", []))
        self._current_track = 0
        return True

    def set_playlist(self, playlist) -> bool:
        """Set a playlist for playback (AudioController expects this method).

        Args:
            playlist: Playlist object with tracks

        Returns:
            True if operation was successful, False otherwise
        """
        if not self._is_available:
            return False

        if hasattr(playlist, "tracks"):
            self._track_count = len(playlist.tracks)
        else:
            self._track_count = 0

        self._playlist_data = playlist
        self._current_track = 0
        return True

    # Mock-specific methods for testing
    def set_availability(self, available: bool):
        """Set the availability state for testing.

        Args:
            available: Whether the service should be available
        """
        self._is_available = available

    def get_current_track(self) -> int:
        """Get the current track number (0-based).

        Returns:
            Current track number
        """
        return self._current_track

    def get_track_count(self) -> int:
        """Get the total number of tracks.

        Returns:
            Total track count
        """
        return self._track_count

    def reset(self):
        """Reset the mock service to initial state."""
        self._is_available = True
        self._is_playing = False
        self._volume = 50
        self._current_track = 0
        self._playlist_data = None
        self._track_count = 0
