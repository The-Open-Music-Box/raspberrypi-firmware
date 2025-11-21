# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Audio engine protocol for coordinating audio operations."""

from typing import Protocol, Optional, Dict, Any
from abc import abstractmethod


class AudioEngineProtocol(Protocol):
    """Protocol for audio engine operations.

    Coordinates audio playback with system state and events.
    Focused on audio orchestration without data management.
    """

    @abstractmethod
    async def play_track_by_path(self, file_path: str, track_id: Optional[str] = None) -> bool:
        """Play a track by file path.

        Args:
            file_path: Path to the audio file
            track_id: Optional track ID for tracking

        Returns:
            True if playback started successfully
        """
        ...

    @abstractmethod
    async def pause_playback(self) -> bool:
        """Pause current playback.

        Returns:
            True if pause was successful
        """
        ...

    @abstractmethod
    async def resume_playback(self) -> bool:
        """Resume paused playback.

        Returns:
            True if resume was successful
        """
        ...

    @abstractmethod
    async def stop_playback(self) -> bool:
        """Stop current playback.

        Returns:
            True if stop was successful
        """
        ...

    @abstractmethod
    async def set_volume(self, volume: int) -> bool:
        """Set playback volume.

        Args:
            volume: Volume level (0-100)

        Returns:
            True if volume was set successfully
        """
        ...

    @abstractmethod
    def get_playback_state(self) -> Dict[str, Any]:
        """Get current playback state.

        Returns:
            Dictionary with current playback state
        """
        ...

    @abstractmethod
    async def seek_to_position(self, position_ms: int) -> bool:
        """Seek to a specific position.

        Args:
            position_ms: Position in milliseconds

        Returns:
            True if seek was successful
        """
        ...