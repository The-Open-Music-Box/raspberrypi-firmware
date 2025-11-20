# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playlist repository interface following Domain-Driven Design principles.

This interface defines the contract for playlist persistence operations
that infrastructure implementations must fulfill.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any


class PlaylistRepositoryProtocol(ABC):
    """Protocol for playlist repository operations.

    Following DDD principles, this protocol belongs in the domain layer
    and defines the contract for playlist persistence without coupling
    to specific infrastructure implementations.
    """

    @abstractmethod
    async def save(self, playlist: Any) -> Any:
        """Save a playlist and return the saved entity.

        Args:
            playlist: Playlist entity to save

        Returns:
            Saved playlist entity with ID assigned
        """
        pass

    @abstractmethod
    async def find_by_id(self, playlist_id: str) -> Optional[Any]:
        """Find a playlist by its ID.

        Args:
            playlist_id: Unique identifier

        Returns:
            Playlist entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Any]:
        """Find a playlist by its name.

        Args:
            name: Playlist name

        Returns:
            Playlist entity or None if not found
        """
        pass

    @abstractmethod
    async def find_by_nfc_tag(self, nfc_tag_id: str) -> Optional[Any]:
        """Find a playlist by associated NFC tag.

        Args:
            nfc_tag_id: NFC tag identifier

        Returns:
            Playlist entity or None if not found
        """
        pass

    @abstractmethod
    async def find_all(self, limit: int = None, offset: int = 0) -> List[Any]:
        """Find all playlists with optional pagination.

        Args:
            limit: Maximum number of playlists to return
            offset: Number of playlists to skip

        Returns:
            List of playlist entities
        """
        pass

    @abstractmethod
    async def update(self, playlist: Any) -> Any:
        """Update an existing playlist.

        Args:
            playlist: Updated playlist entity

        Returns:
            Updated playlist entity
        """
        pass

    @abstractmethod
    async def delete(self, playlist_id: str) -> bool:
        """Delete a playlist by ID.

        Args:
            playlist_id: Playlist identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total number of playlists.

        Returns:
            Total playlist count
        """
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = None) -> List[Any]:
        """Search playlists by name or description.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching playlist entities
        """
        pass

    @abstractmethod
    async def update_track_numbers(self, playlist_id: str, track_number_mapping: dict) -> bool:
        """Update track numbers for tracks in a playlist.

        Args:
            playlist_id: Playlist identifier
            track_number_mapping: Dictionary mapping old track numbers to new track numbers

        Returns:
            True if successful, False otherwise
        """
        pass
