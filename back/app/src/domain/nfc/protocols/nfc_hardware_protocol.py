# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Hardware Protocol Interface."""

from abc import ABC, abstractmethod
from typing import Optional, Callable, Any

from ..value_objects.tag_identifier import TagIdentifier


class NfcHardwareProtocol(ABC):
    """Protocol for NFC hardware interactions.

    Defines the contract for NFC hardware adapters, allowing different
    implementations (real hardware, mock, etc.) while maintaining
    domain separation.
    """

    @abstractmethod
    async def start_detection(self) -> None:
        """Start NFC tag detection.

        Raises:
            NfcHardwareError: If hardware cannot be started
        """
        pass

    @abstractmethod
    async def stop_detection(self) -> None:
        """Stop NFC tag detection."""
        pass

    @abstractmethod
    def is_detecting(self) -> bool:
        """Check if currently detecting tags."""
        pass

    @abstractmethod
    def set_tag_detected_callback(self, callback: Callable[[TagIdentifier], None]) -> None:
        """Set callback for when a tag is detected.

        Args:
            callback: Function to call when tag is detected
        """
        pass

    @abstractmethod
    def set_tag_removed_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for when a tag is removed.

        Args:
            callback: Function to call when tag is removed
        """
        pass

    @abstractmethod
    async def get_hardware_status(self) -> dict:
        """Get current hardware status.

        Returns:
            Dictionary with hardware status information
        """
        pass


class NfcRepositoryProtocol(ABC):
    """Protocol for NFC tag persistence."""

    @abstractmethod
    async def save_tag(self, tag: "NfcTag") -> None:
        """Save an NFC tag.

        Args:
            tag: NFC tag entity to save
        """
        pass

    @abstractmethod
    async def find_by_identifier(self, identifier: TagIdentifier) -> Optional["NfcTag"]:
        """Find tag by identifier.

        Args:
            identifier: Tag identifier to search for

        Returns:
            NFC tag if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_playlist_id(self, playlist_id: str) -> Optional["NfcTag"]:
        """Find tag associated with a playlist.

        Args:
            playlist_id: Playlist ID to search for

        Returns:
            NFC tag if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete_tag(self, identifier: TagIdentifier) -> bool:
        """Delete a tag.

        Args:
            identifier: Tag identifier to delete

        Returns:
            True if deleted, False if not found
        """
        pass
