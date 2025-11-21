# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Track service for data domain."""

import uuid
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from app.src.domain.decorators.error_handler import handle_domain_errors

logger = logging.getLogger(__name__)

 


class TrackService:
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
        self._track_repo = track_repository
        self._playlist_repo = playlist_repository
        logger.info("✅ TrackService initialized in data domain")

    @handle_domain_errors(operation_name="get_tracks")
    async def get_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
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
        return sorted(tracks, key=lambda t: t.track_number if hasattr(t, 'track_number') else t.get('track_number', 0))

    @handle_domain_errors(operation_name="add_track")
    async def add_track(self, playlist_id: str, track_data: Dict[str, Any]) -> Dict[str, Any]:
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
            'track_number': track_data.get('track_number', next_track_number),
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

        return await self._track_repo.get_by_id(track_id)

    @handle_domain_errors(operation_name="update_track")
    async def update_track(self, track_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
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
        return await self._track_repo.get_by_id(track_id)

    @handle_domain_errors(operation_name="delete_track")
    async def delete_track(self, track_id: str) -> bool:
        """Delete a track.

        Args:
            track_id: The track ID

        Returns:
            True if successful
        """
        success = await self._track_repo.delete(track_id)
        if success:
            logger.info(f"✅ Deleted track {track_id}")
        else:
            logger.warning(f"Failed to delete track {track_id}")

        return success

    @handle_domain_errors(operation_name="reorder_tracks")
    async def reorder_tracks(self, playlist_id: str, track_ids: List[str]) -> bool:
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
        existing_track_ids = {t.id if hasattr(t, 'id') else t['id'] for t in existing_tracks}

        for track_id in track_ids:
            if track_id not in existing_track_ids:
                raise ValueError(f"Track {track_id} does not belong to playlist {playlist_id}")

        # Create track order updates
        track_orders = [
            {'track_id': track_id, 'track_number': idx + 1}
            for idx, track_id in enumerate(track_ids)
        ]

        success = await self._track_repo.reorder(playlist_id, track_orders)
        if success:
            logger.info(f"✅ Reordered {len(track_ids)} tracks in playlist {playlist_id}")

        return success

    @handle_domain_errors(operation_name="get_next_track")
    async def get_next_track(
        self,
        playlist_id: str,
        current_track_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
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
            return tracks[0]

        # Find current track index
        current_index = None
        for i, track in enumerate(tracks):
            track_id = track.id if hasattr(track, 'id') else track['id']
            if track_id == current_track_id:
                current_index = i
                break

        if current_index is None:
            # Current track not found, return first track
            return tracks[0]

        # Return next track or None if at end
        next_index = current_index + 1
        if next_index < len(tracks):
            return tracks[next_index]

        return None

    @handle_domain_errors(operation_name="get_previous_track")
    async def get_previous_track(
        self,
        playlist_id: str,
        current_track_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
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
            return tracks[-1]

        # Find current track index
        current_index = None
        for i, track in enumerate(tracks):
            track_id = track.id if hasattr(track, 'id') else track['id']
            if track_id == current_track_id:
                current_index = i
                break

        if current_index is None:
            # Current track not found, return last track
            return tracks[-1]

        # Return previous track or None if at beginning
        if current_index > 0:
            return tracks[current_index - 1]

        return None
