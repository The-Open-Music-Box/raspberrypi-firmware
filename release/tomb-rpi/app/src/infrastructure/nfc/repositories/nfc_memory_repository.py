# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""In-Memory NFC Repository Implementation."""

from typing import Dict, Optional

from app.src.domain.nfc.entities.nfc_tag import NfcTag
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.domain.nfc.protocols.nfc_hardware_protocol import NfcRepositoryProtocol


class NfcMemoryRepository(NfcRepositoryProtocol):
    """In-memory implementation of NFC repository.

    Simple implementation for development and testing.
    Can be replaced with database implementation later.
    """

    def __init__(self):
        """Initialize empty repository."""
        self._tags: Dict[str, NfcTag] = {}

    async def save_tag(self, tag: NfcTag) -> None:
        """Save an NFC tag.

        Args:
            tag: NFC tag entity to save
        """
        self._tags[tag.identifier.uid] = tag

    async def find_by_identifier(self, identifier: TagIdentifier) -> Optional[NfcTag]:
        """Find tag by identifier.

        Args:
            identifier: Tag identifier to search for

        Returns:
            NFC tag if found, None otherwise
        """
        return self._tags.get(identifier.uid)

    async def find_by_playlist_id(self, playlist_id: str) -> Optional[NfcTag]:
        """Find tag associated with a playlist.

        Args:
            playlist_id: Playlist ID to search for

        Returns:
            NFC tag if found, None otherwise
        """
        for tag in self._tags.values():
            if tag.get_associated_playlist_id() == playlist_id:
                return tag
        return None

    async def delete_tag(self, identifier: TagIdentifier) -> bool:
        """Delete a tag.

        Args:
            identifier: Tag identifier to delete

        Returns:
            True if deleted, False if not found
        """
        if identifier.uid in self._tags:
            del self._tags[identifier.uid]
            return True
        return False

    def clear_all(self) -> None:
        """Clear all tags (for testing)."""
        self._tags.clear()

    def get_all_tags(self) -> Dict[str, NfcTag]:
        """Get all tags (for testing)."""
        return self._tags.copy()
