# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Track service for data domain."""

import logging
import uuid
from datetime import datetime
from typing import Any, cast

from app.src.domain.base.base_domain_service import BaseDomainService
from app.src.domain.decorators.error_handler import handle_domain_errors

logger = logging.getLogger(__name__)


class TrackService(BaseDomainService):
    """Service for managing track data operations."""

    def __init__(
        self,
        track_repository: Any,
        playlist_repository: Any
    ):
        """Initialize the track service.

        Args:
            track_repository: Repository for track operations
            playlist_repository: Repository for playlist operations
        """
        super().__init__()
        self._track_repo = track_repository
        self._playlist_repo = playlist_repository
        logger.info("✅ TrackService initialized in data domain")

    @handle_domain_errors(operation_name="get_tracks")
    async def get_tracks(self, playlist_id: str) -> list[dict[str, Any]]:
        """Get all tracks for a playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of track data
        """
        # Verify playlist exists
        if not await self._playlist_repo.exists(playlist_id):
            raise ValueError(f"Playlist {playlist_id} not found")

        tracks = await self._track_repo.get_by_playlist(playlist_id)
        # Handle both Track objects and dictionaries
        return sorted(tracks, key=lambda t: t.number if hasattr(t, 'number') else t.get('number', 0))

    @handle_domain_errors(operation_name="add_track")
    async def add_track(self, playlist_id: str, track_data: dict[str, Any]) -> dict[str, Any]:
        """Add a track to a playlist.

        Args:
            playlist_id: The playlist ID
            track_data: Track information

        Returns:
            Created track data
        """
        # Verify playlist exists
        if not await self._playlist_repo.exists(playlist_id):
            raise ValueError(f"Playlist {playlist_id} not found")

        # Get current tracks to determine track number
        existing_tracks = await self._track_repo.get_by_playlist(playlist_id)
        next_track_number = len(existing_tracks) + 1

        # Prepare track data
        track_id = str(uuid.uuid4())
        full_track_data = {
            'id': track_id,
            'playlist_id': playlist_id,
            'number': track_data.get('number', next_track_number),
            'title': track_data.get('title', 'Unknown Track'),
            'filename': track_data.get('filename'),
            'file_path': track_data.get('file_path'),
            'duration_ms': track_data.get('duration_ms', 0),
            'artist': track_data.get('artist'),
            'album': track_data.get('album'),
            'play_count': 0,
            'server_seq': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        await self._track_repo.add_to_playlist(playlist_id, full_track_data)
        logger.info(f"✅ Added track {track_data.get('title')} to playlist {playlist_id}")

        return cast(dict[str, Any], await self._track_repo.get_by_id(track_id))

    @handle_domain_errors(operation_name="update_track")
    async def update_track(self, track_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Update track metadata.

        Args:
            track_id: The track ID
            updates: Dictionary of updates

        Returns:
            Updated track data
        """
        # Check if track exists
        existing_track = await self._track_repo.get_by_id(track_id)
        if not existing_track:
            raise ValueError(f"Track {track_id} not found")

        # Add updated timestamp
        updates['updated_at'] = datetime.utcnow().isoformat()

        success = await self._track_repo.update(track_id, updates)
        if not success:
            raise RuntimeError(f"Failed to update track {track_id}")

        logger.info(f"✅ Updated track {track_id}")
        return cast(dict[str, Any], await self._track_repo.get_by_id(track_id))

    @handle_domain_errors(operation_name="delete_track")
    async def delete_track(self, track_id: str) -> bool:
        """Delete a track and its associated file.

        Args:
            track_id: The track ID

        Returns:
            True if successful
        """
        # Get track info before deletion (for filesystem cleanup)
        track = await self._track_repo.get_by_id(track_id)

        # Delete from database
        success = await self._track_repo.delete(track_id)

        if success:
            logger.info(f"✅ Deleted track {track_id} from database")

            # Clean up track file from filesystem
            if track and track.get('file_path'):
                await self._cleanup_track_file(track)
        else:
            logger.warning(f"Failed to delete track {track_id}")

        return cast(bool, success)

    async def _cleanup_track_file(self, track: dict[str, Any]) -> None:
        """Clean up the filesystem file for a deleted track.

        Args:
            track: Track data dictionary
        """
        try:
            import os
            from pathlib import Path

            file_path = track.get('file_path')
            if not file_path:
                logger.debug(f"No file_path for track {track.get('id')}, skipping filesystem cleanup")
                return

            file_path_obj = Path(file_path)

            if file_path_obj.exists() and file_path_obj.is_file():
                os.remove(file_path_obj)
                logger.info(f"🗑️ Removed track file: {file_path}")
            else:
                logger.debug(f"📁 Track file not found (may have been manually deleted): {file_path}")

        except Exception as e:
            logger.warning(f"⚠️ Failed to clean up track file {file_path}: {e}")
            # Don't fail the delete operation if file cleanup fails

    @handle_domain_errors(operation_name="reorder_tracks")
    async def reorder_tracks(self, playlist_id: str, track_ids: list[str]) -> bool:
        """Reorder tracks in a playlist.

        Args:
            playlist_id: The playlist ID
            track_ids: List of track IDs in new order

        Returns:
            True if successful
        """
        # Verify playlist exists
        if not await self._playlist_repo.exists(playlist_id):
            raise ValueError(f"Playlist {playlist_id} not found")

        # Verify all tracks belong to the playlist
        existing_tracks = await self._track_repo.get_by_playlist(playlist_id)

        # Per OpenAPI contract v3.3.2: track_ids are filenames (Track schema has no 'id' field)
        existing_filenames = {
            t.filename if hasattr(t, 'filename') else t.get('filename')
            for t in existing_tracks
        }

        for track_id in track_ids:
            if track_id not in existing_filenames:
                raise ValueError(f"Track {track_id} does not belong to playlist {playlist_id}")

        # Map filenames to internal UUIDs for repository operations
        filename_to_uuid = {}
        for t in existing_tracks:
            t_uuid = t.id if hasattr(t, 'id') else t.get('id')
            t_filename = t.filename if hasattr(t, 'filename') else t.get('filename')
            filename_to_uuid[t_filename] = t_uuid

        logger.debug(f"Filename to UUID mapping has {len(filename_to_uuid)} entries")
        logger.debug(f"Track IDs received (filenames): {track_ids[:3] if len(track_ids) > 3 else track_ids}")

        # Create track order updates using internal UUIDs
        track_orders = []
        for idx, filename in enumerate(track_ids):
            internal_uuid = filename_to_uuid[filename]
            new_position = idx + 1
            track_orders.append({'track_id': internal_uuid, 'number': new_position})
            logger.debug(f"Position {new_position}: {filename} → UUID {internal_uuid}")

        success = await self._track_repo.reorder(playlist_id, track_orders)
        if success:
            logger.info(f"✅ Reordered {len(track_ids)} tracks in playlist {playlist_id}")

        return cast(bool, success)

    @handle_domain_errors(operation_name="get_next_track")
    async def get_next_track(
        self,
        playlist_id: str,
        current_track_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get the next track in a playlist.

        Args:
            playlist_id: The playlist ID
            current_track_id: Current track ID (if None, returns first track)

        Returns:
            Next track data or None
        """
        tracks = await self.get_tracks(playlist_id)
        if not tracks:
            return None

        if current_track_id is None:
            # Return first track
            return cast(dict[str, Any] | None, tracks[0])

        # Find current track index
        current_index = self._find_track_index(tracks, current_track_id)

        if current_index is None:
            # Current track not found, return first track
            return cast(dict[str, Any] | None, tracks[0])

        # Return next track or None if at end
        next_index = current_index + 1
        if next_index < len(tracks):
            return cast(dict[str, Any] | None, tracks[next_index])

        return None

    @handle_domain_errors(operation_name="get_previous_track")
    async def get_previous_track(
        self,
        playlist_id: str,
        current_track_id: str | None = None
    ) -> dict[str, Any] | None:
        """Get the previous track in a playlist.

        Args:
            playlist_id: The playlist ID
            current_track_id: Current track ID (if None, returns last track)

        Returns:
            Previous track data or None
        """
        tracks = await self.get_tracks(playlist_id)
        if not tracks:
            return None

        if current_track_id is None:
            # Return last track
            return cast(dict[str, Any] | None, tracks[-1])

        # Find current track index
        current_index = self._find_track_index(tracks, current_track_id)

        if current_index is None:
            # Current track not found, return last track
            return cast(dict[str, Any] | None, tracks[-1])

        # Return previous track or None if at beginning
        if current_index > 0:
            return cast(dict[str, Any] | None, tracks[current_index - 1])

        return None
