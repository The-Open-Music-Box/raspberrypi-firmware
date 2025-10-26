# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Repository protocols for the data domain."""

from typing import Protocol, List, Optional, Dict, Any
from abc import abstractmethod


class PlaylistRepositoryProtocol(Protocol):
    """Protocol for playlist repository operations."""

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all playlists with pagination."""
        ...

    @abstractmethod
    async def get_by_id(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get a playlist by its ID."""
        ...

    @abstractmethod
    async def get_by_nfc_tag(self, nfc_tag_id: str) -> Optional[Dict[str, Any]]:
        """Get a playlist by its associated NFC tag."""
        ...

    @abstractmethod
    async def create(self, playlist_data: Dict[str, Any]) -> str:
        """Create a new playlist."""
        ...

    @abstractmethod
    async def update(self, playlist_id: str, playlist_data: Dict[str, Any]) -> bool:
        """Update an existing playlist."""
        ...

    @abstractmethod
    async def delete(self, playlist_id: str) -> bool:
        """Delete a playlist."""
        ...

    @abstractmethod
    async def exists(self, playlist_id: str) -> bool:
        """Check if a playlist exists."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Count total playlists."""
        ...


class TrackRepositoryProtocol(Protocol):
    """Protocol for track repository operations."""

    @abstractmethod
    async def get_by_playlist(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get all tracks for a playlist."""
        ...

    @abstractmethod
    async def get_by_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get a track by its ID."""
        ...

    @abstractmethod
    async def add_to_playlist(self, playlist_id: str, track_data: Dict[str, Any]) -> str:
        """Add a track to a playlist."""
        ...

    @abstractmethod
    async def update(self, track_id: str, track_data: Dict[str, Any]) -> bool:
        """Update a track."""
        ...

    @abstractmethod
    async def delete(self, track_id: str) -> bool:
        """Delete a track."""
        ...

    @abstractmethod
    async def reorder(self, playlist_id: str, track_orders: List[Dict[str, int]]) -> bool:
        """Reorder tracks in a playlist."""
        ...

    @abstractmethod
    async def delete_by_playlist(self, playlist_id: str) -> int:
        """Delete all tracks from a playlist."""
        ...