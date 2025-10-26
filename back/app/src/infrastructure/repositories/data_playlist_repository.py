# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain playlist repository implementation."""

from typing import List, Optional, Dict, Any

from app.src.monitoring import get_logger
from app.src.domain.data.protocols.repository_protocol import PlaylistRepositoryProtocol
from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import (
    PureSQLitePlaylistRepository
)

logger = get_logger(__name__)


class DataPlaylistRepository(PlaylistRepositoryProtocol):
    """Data domain adapter for playlist repository."""

    def __init__(self, sqlite_repository: PureSQLitePlaylistRepository):
        """Initialize with the SQLite repository.

        Args:
            sqlite_repository: The underlying SQLite repository
        """
        self._repo = sqlite_repository
        logger.info("✅ DataPlaylistRepository initialized")

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all playlists with pagination."""
        playlists = await self._repo.find_all(limit=limit, offset=skip)
        # Convert Playlist domain objects to dictionaries, filter out None values
        return [self._playlist_to_dict(playlist) for playlist in playlists if playlist is not None]

    async def get_by_id(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get a playlist by its ID."""
        playlist = await self._repo.find_by_id(playlist_id)
        return self._playlist_to_dict(playlist) if playlist else None

    async def get_by_nfc_tag(self, nfc_tag_id: str) -> Optional[Dict[str, Any]]:
        """Get a playlist by its associated NFC tag."""
        playlist = await self._repo.find_by_nfc_tag(nfc_tag_id)
        return self._playlist_to_dict(playlist) if playlist else None

    async def create(self, playlist_data: Dict[str, Any]) -> str:
        """Create a new playlist."""
        from app.src.domain.data.models.playlist import Playlist
        # Convert dict to domain object using API compatibility factory
        playlist = Playlist.from_api_data(
            title=playlist_data.get('title', ''),
            description=playlist_data.get('description', ''),
            id=playlist_data.get('id'),
            nfc_tag_id=playlist_data.get('nfc_tag_id'),
            tracks=[]
        )
        saved_playlist = await self._repo.save(playlist)
        return saved_playlist.id

    async def update(self, playlist_id: str, playlist_data: Dict[str, Any]) -> bool:
        """Update an existing playlist."""
        # Get existing playlist
        existing = await self._repo.find_by_id(playlist_id)
        if not existing:
            return False

        # Update fields
        if 'title' in playlist_data:
            existing.title = playlist_data['title']
        if 'description' in playlist_data:
            existing.description = playlist_data['description']
        if 'nfc_tag_id' in playlist_data:
            existing.nfc_tag_id = playlist_data['nfc_tag_id']

        # Save updated playlist
        await self._repo.update(existing)
        return True

    async def delete(self, playlist_id: str) -> bool:
        """Delete a playlist."""
        return await self._repo.delete(playlist_id)

    async def exists(self, playlist_id: str) -> bool:
        """Check if a playlist exists."""
        playlist = await self.get_by_id(playlist_id)
        return playlist is not None

    async def count(self) -> int:
        """Count total playlists."""
        return await self._repo.count()

    def _playlist_to_dict(self, playlist) -> Optional[Dict[str, Any]]:
        """Convert Playlist domain object to dictionary."""
        if not playlist:
            return None

        return {
            'id': playlist.id,
            'title': playlist.title,
            'description': playlist.description or '',  # Ensure empty string instead of None
            'nfc_tag_id': playlist.nfc_tag_id or '',  # Ensure empty string instead of None
            'tracks': [self._track_to_dict(track) for track in playlist.tracks if track is not None],
            'created_at': getattr(playlist, 'created_at', '') or '',  # Ensure empty string instead of None
            'updated_at': getattr(playlist, 'updated_at', '') or ''  # Ensure empty string instead of None
        }

    def _track_to_dict(self, track) -> Dict[str, Any]:
        """Convert Track domain object to dictionary."""
        if not track:
            return None

        return {
            'id': track.id,
            'track_number': track.track_number,
            'title': track.title,
            'filename': track.filename,
            'file_path': track.file_path,
            'duration_ms': track.duration_ms,
            'artist': track.artist,
            'album': track.album
        }