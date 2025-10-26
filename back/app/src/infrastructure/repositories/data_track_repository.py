# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain track repository implementation."""

from typing import List, Optional, Dict, Any

from app.src.monitoring import get_logger
from app.src.domain.data.protocols.repository_protocol import TrackRepositoryProtocol
from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import (
    PureSQLitePlaylistRepository
)

logger = get_logger(__name__)


class DataTrackRepository(TrackRepositoryProtocol):
    """Data domain adapter for track repository."""

    def __init__(self, sqlite_repository: PureSQLitePlaylistRepository):
        """Initialize with the SQLite repository.

        Args:
            sqlite_repository: The underlying SQLite repository
        """
        self._repo = sqlite_repository
        logger.info("✅ DataTrackRepository initialized")

    async def get_by_playlist(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get all tracks for a playlist."""
        return await self._repo.get_tracks_by_playlist(playlist_id)

    async def get_by_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get a track by its ID."""
        return await self._repo.get_track_by_id(track_id)

    async def add_to_playlist(self, playlist_id: str, track_data: Dict[str, Any]) -> str:
        """Add a track to a playlist."""
        return await self._repo.add_track_to_playlist(playlist_id, track_data)

    async def update(self, track_id: str, track_data: Dict[str, Any]) -> bool:
        """Update a track."""
        return await self._repo.update_track(track_id, track_data)

    async def delete(self, track_id: str) -> bool:
        """Delete a track."""
        return await self._repo.delete_track(track_id)

    async def reorder(self, playlist_id: str, track_orders: List[Dict[str, int]]) -> bool:
        """Reorder tracks in a playlist."""
        return await self._repo.reorder_tracks(playlist_id, track_orders)

    async def delete_by_playlist(self, playlist_id: str) -> int:
        """Delete all tracks from a playlist."""
        return await self._repo.delete_tracks_by_playlist(playlist_id)