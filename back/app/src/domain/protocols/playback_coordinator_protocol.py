# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playback Coordinator Protocol (Domain Layer).

Defines the interface that button actions need from a playback coordinator.
This allows the domain layer to remain pure without depending on application layer.
"""

from typing import Protocol, Dict, Any


class PlaybackCoordinatorProtocol(Protocol):
    """
    Protocol defining the interface for playback coordination.

    This protocol is used by button actions in the domain layer,
    allowing them to interact with playback functionality without
    depending on the concrete PlaybackCoordinator implementation.
    """

    def play(self) -> bool:
        """
        Start or resume playback.

        Returns:
            True if playback started successfully, False otherwise
        """
        ...

    def pause(self) -> bool:
        """
        Pause current playback.

        Returns:
            True if paused successfully, False otherwise
        """
        ...

    def toggle_pause(self) -> bool:
        """
        Toggle between play and pause states.

        Returns:
            True if toggled successfully, False otherwise
        """
        ...

    def stop(self) -> bool:
        """
        Stop current playback.

        Returns:
            True if stopped successfully, False otherwise
        """
        ...

    def next_track(self) -> bool:
        """
        Move to and play next track.

        Returns:
            True if moved to next track successfully, False otherwise
        """
        ...

    def previous_track(self) -> bool:
        """
        Move to and play previous track.

        Returns:
            True if moved to previous track successfully, False otherwise
        """
        ...

    def get_volume(self) -> int:
        """
        Get current playback volume.

        Returns:
            Current volume level (0-100)
        """
        ...

    async def set_volume(self, volume: int) -> bool:
        """
        Set playback volume.

        Args:
            volume: Volume level to set (0-100)

        Returns:
            True if volume set successfully, False otherwise
        """
        ...

    def get_playback_status(self) -> Dict[str, Any]:
        """
        Get complete playback status information.

        Returns:
            Dictionary containing playback state information including:
            - is_playing: bool
            - is_paused: bool
            - volume: int
            - position_ms: int
            - duration_ms: int
            - active_playlist_title: str
            - active_track: dict
            - track_index: int
            - track_count: int
            - repeat_mode: str
            - shuffle_enabled: bool
            - auto_advance_enabled: bool
        """
        ...
