# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Audio backend protocol for pure audio playback operations."""

from typing import Protocol, Optional, runtime_checkable
from abc import abstractmethod


@runtime_checkable
class AudioBackendProtocol(Protocol):
    """Protocol for pure audio backend operations.

    This protocol defines the contract for audio playback backends.
    It is focused solely on audio playback control, without any
    playlist or data management responsibilities.
    """

    @abstractmethod
    async def play(self, file_path: str) -> bool:
        """Play an audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            True if playback started successfully
        """
        ...

    @abstractmethod
    async def pause(self) -> bool:
        """Pause current playback.

        Returns:
            True if pause was successful
        """
        ...

    @abstractmethod
    async def resume(self) -> bool:
        """Resume paused playback.

        Returns:
            True if resume was successful
        """
        ...

    @abstractmethod
    async def stop(self) -> bool:
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
    async def get_volume(self) -> int:
        """Get current volume level.

        Returns:
            Current volume (0-100)
        """
        ...

    @abstractmethod
    async def seek(self, position_ms: int) -> bool:
        """Seek to a specific position.

        Args:
            position_ms: Position in milliseconds

        Returns:
            True if seek was successful
        """
        ...

    @abstractmethod
    async def get_position(self) -> Optional[int]:
        """Get current playback position.

        Returns:
            Current position in milliseconds or None if not playing
        """
        ...

    @abstractmethod
    async def get_duration(self) -> Optional[int]:
        """Get duration of current track.

        Returns:
            Duration in milliseconds or None if not available
        """
        ...

    @abstractmethod
    def is_playing(self) -> bool:
        """Check if audio is currently playing.

        Returns:
            True if audio is playing
        """
        ...