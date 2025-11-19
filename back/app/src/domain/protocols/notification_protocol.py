# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Protocol for notification services in domain layer."""

from typing import Protocol, Dict, Optional, Any


class PlaybackNotifierProtocol(Protocol):
    """Protocol for playback notification without infrastructure dependency."""

    def notify_playback_status(
        self,
        status: str,
        playlist_info: Optional[Dict] = None,
        track_info: Optional[Dict] = None
    ) -> None:
        """Notify playback status change.

        Args:
            status: Playback status (playing, paused, stopped, etc.)
            playlist_info: Optional playlist information
            track_info: Optional track information
        """
        ...

    def notify_track_progress(
        self,
        progress_percent: float,
        elapsed_seconds: int,
        total_seconds: int,
        track_info: Optional[Dict] = None
    ) -> None:
        """Notify track progress update.

        Args:
            progress_percent: Progress percentage (0-100)
            elapsed_seconds: Elapsed time in seconds
            total_seconds: Total track duration in seconds
            track_info: Optional track information
        """
        ...

    def notify(self, event_data: Dict[str, Any]) -> None:
        """Notify observers with event data.

        Args:
            event_data: Event data dictionary
        """
        ...


class MockPlaybackNotifier:
    """Mock implementation of PlaybackNotifierProtocol for testing."""

    _instance = None

    @classmethod
    def get_instance(cls):
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def notify_playback_status(
        self,
        status: str,
        playlist_info: Optional[Dict] = None,
        track_info: Optional[Dict] = None
    ) -> None:
        """Mock notification - does nothing."""
        pass

    def notify_track_progress(
        self,
        progress_percent: float,
        elapsed_seconds: int,
        total_seconds: int,
        track_info: Optional[Dict] = None
    ) -> None:
        """Mock notification - does nothing."""
        pass

    def notify(self, event_data: Dict[str, Any]) -> None:
        """Mock notification - does nothing."""
        pass


# Note: Use MockPlaybackNotifier.get_instance() directly for singleton access
# PlaybackNotifierProtocol is a Protocol class and shouldn't have class methods added
