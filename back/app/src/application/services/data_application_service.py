# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data application service for playlist and track operations."""

from typing import Dict, Any, List, Optional

from app.src.monitoring import get_logger
from app.src.domain.data.services.playlist_service import PlaylistService
from app.src.domain.data.services.track_service import TrackService
from app.src.common.exceptions import BusinessLogicError

logger = get_logger(__name__)


class DataApplicationService:
    """Application service for data operations.

    This service coordinates data domain operations and provides
    a unified interface for playlist and track management.
    """

    def __init__(
        self,
        playlist_service: PlaylistService,
        track_service: TrackService
    ):
        """Initialize the data application service.

        Args:
            playlist_service: Domain playlist service
            track_service: Domain track service
        """
        self._playlist_service = playlist_service
        self._track_service = track_service
        logger.info("✅ DataApplicationService initialized")

    # Playlist operations
    async def get_playlists_use_case(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Get paginated playlists.

        Args:
            page: Page number
            page_size: Items per page

        Returns:
            Paginated playlist data
        """
        try:
            return await self._playlist_service.get_playlists(page, page_size)
        except Exception as e:
            logger.error(f"Failed to get playlists: {e}")
            raise BusinessLogicError(f"Failed to retrieve playlists: {str(e)}")

    async def get_playlist_use_case(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get a single playlist with tracks.

        Args:
            playlist_id: The playlist ID

        Returns:
            Playlist data with tracks or None if not found
        """
        try:
            playlist = await self._playlist_service.get_playlist(playlist_id)
            return playlist  # Return None if not found (handled gracefully by API routes)
        except Exception as e:
            logger.error(f"Failed to get playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to retrieve playlist: {str(e)}")

    async def create_playlist_use_case(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new playlist.

        Args:
            name: Playlist name
            description: Optional description

        Returns:
            Created playlist data
        """
        try:
            if not name or not name.strip():
                raise BusinessLogicError("Playlist name is required")

            return await self._playlist_service.create_playlist(name.strip(), description)
        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Failed to create playlist {name}: {e}")
            raise BusinessLogicError(f"Failed to create playlist: {str(e)}")

    async def update_playlist_use_case(self, playlist_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update playlist metadata.

        Args:
            playlist_id: The playlist ID
            updates: Dictionary of updates

        Returns:
            Updated playlist data or None if not found
        """
        try:
            # Validate updates
            if 'title' in updates and not updates['title'].strip():
                raise BusinessLogicError("Playlist title cannot be empty")

            # Check if playlist exists first
            existing = await self._playlist_service.get_playlist(playlist_id)
            if not existing:
                return None  # Playlist not found - return None instead of raising exception

            return await self._playlist_service.update_playlist(playlist_id, updates)
        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Failed to update playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to update playlist: {str(e)}")

    async def delete_playlist_use_case(self, playlist_id: str) -> bool:
        """Delete a playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            True if successful, False if playlist not found
        """
        try:
            # Call delete directly - it will return False if playlist doesn't exist
            # No need to check existence first, as delete_playlist already does that
            success = await self._playlist_service.delete_playlist(playlist_id)
            return success
        except Exception as e:
            logger.error(f"Failed to delete playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to delete playlist: {str(e)}")

    async def associate_nfc_tag_use_case(self, playlist_id: str, nfc_tag_id: str) -> bool:
        """Associate an NFC tag with a playlist.

        Args:
            playlist_id: The playlist ID
            nfc_tag_id: The NFC tag ID

        Returns:
            True if successful
        """
        try:
            return await self._playlist_service.associate_nfc_tag(playlist_id, nfc_tag_id)
        except Exception as e:
            logger.error(f"Failed to associate NFC tag {nfc_tag_id} with playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to associate NFC tag: {str(e)}")

    async def get_playlist_by_nfc_use_case(self, nfc_tag_id: str) -> Optional[Dict[str, Any]]:
        """Get playlist by NFC tag.

        Args:
            nfc_tag_id: The NFC tag ID

        Returns:
            Playlist data or None
        """
        try:
            return await self._playlist_service.get_playlist_by_nfc(nfc_tag_id)
        except Exception as e:
            logger.error(f"Failed to get playlist by NFC tag {nfc_tag_id}: {e}")
            raise BusinessLogicError(f"Failed to get playlist by NFC tag: {str(e)}")

    async def sync_filesystem_use_case(self, upload_folder: str) -> Dict[str, Any]:
        """Synchronize playlists with filesystem.

        Args:
            upload_folder: Path to uploads folder

        Returns:
            Sync statistics
        """
        try:
            return await self._playlist_service.sync_with_filesystem(upload_folder)
        except Exception as e:
            logger.error(f"Failed to sync filesystem: {e}")
            raise BusinessLogicError(f"Failed to sync filesystem: {str(e)}")

    # Track operations
    async def get_tracks_use_case(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get tracks for a playlist.

        Args:
            playlist_id: The playlist ID

        Returns:
            List of tracks
        """
        try:
            return await self._track_service.get_tracks(playlist_id)
        except Exception as e:
            logger.error(f"Failed to get tracks for playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to get tracks: {str(e)}")

    async def add_track_use_case(self, playlist_id: str, track_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a track to a playlist.

        Args:
            playlist_id: The playlist ID
            track_data: Track information

        Returns:
            Created track data
        """
        try:
            if not track_data.get('title'):
                raise BusinessLogicError("Track title is required")

            return await self._track_service.add_track(playlist_id, track_data)
        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Failed to add track to playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to add track: {str(e)}")

    async def update_track_use_case(self, track_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update track metadata.

        Args:
            track_id: The track ID
            updates: Dictionary of updates

        Returns:
            Updated track data
        """
        try:
            if 'title' in updates and not updates['title'].strip():
                raise BusinessLogicError("Track title cannot be empty")

            return await self._track_service.update_track(track_id, updates)
        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Failed to update track {track_id}: {e}")
            raise BusinessLogicError(f"Failed to update track: {str(e)}")

    async def delete_track_use_case(self, track_id: str) -> bool:
        """Delete a track.

        Args:
            track_id: The track ID

        Returns:
            True if successful
        """
        try:
            return await self._track_service.delete_track(track_id)
        except Exception as e:
            logger.error(f"Failed to delete track {track_id}: {e}")
            raise BusinessLogicError(f"Failed to delete track: {str(e)}")

    async def reorder_tracks_use_case(self, playlist_id: str, track_ids: List[str]) -> Dict[str, Any]:
        """Reorder tracks in a playlist.

        Args:
            playlist_id: The playlist ID
            track_ids: List of track IDs in new order

        Returns:
            Dict with status and message
        """
        try:
            if not track_ids:
                raise BusinessLogicError("Track IDs list cannot be empty")

            success = await self._track_service.reorder_tracks(playlist_id, track_ids)

            if success:
                return {
                    "status": "success",
                    "message": f"Reordered {len(track_ids)} tracks successfully"
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to reorder tracks"
                }
        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Failed to reorder tracks in playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to reorder tracks: {str(e)}")

    async def delete_tracks_use_case(self, playlist_id: str, track_numbers: List[int]) -> Dict[str, Any]:
        """Delete tracks from a playlist by track numbers.

        Args:
            playlist_id: The playlist ID
            track_numbers: List of track numbers to delete

        Returns:
            Dict with status and message
        """
        try:
            if not track_numbers:
                raise BusinessLogicError("Track numbers list cannot be empty")

            # Get playlist with tracks
            playlist = await self._playlist_service.get_playlist(playlist_id)
            if not playlist:
                raise BusinessLogicError(f"Playlist {playlist_id} not found")

            # Delete each track by number
            deleted_count = 0
            for track_number in track_numbers:
                # Find track by number - handle both Track objects and dictionaries
                tracks = await self._track_service.get_tracks(playlist_id)
                track_to_delete = next(
                    (t for t in tracks if (hasattr(t, 'track_number') and t.track_number == track_number) or
                     (isinstance(t, dict) and t.get('track_number') == track_number)),
                    None
                )

                if track_to_delete:
                    track_id = track_to_delete.id if hasattr(track_to_delete, 'id') else track_to_delete['id']
                    await self._track_service.delete_track(track_id)
                    deleted_count += 1

            return {
                "status": "success",
                "message": f"Deleted {deleted_count} tracks",
                "deleted_count": deleted_count
            }
        except BusinessLogicError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete tracks from playlist {playlist_id}: {e}")
            return {
                "status": "error",
                "message": f"Failed to delete tracks: {str(e)}"
            }

    async def get_next_track_use_case(
        self,
        playlist_id: str,
        current_track_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the next track in a playlist.

        Args:
            playlist_id: The playlist ID
            current_track_id: Current track ID

        Returns:
            Next track data or None
        """
        try:
            return await self._track_service.get_next_track(playlist_id, current_track_id)
        except Exception as e:
            logger.error(f"Failed to get next track for playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to get next track: {str(e)}")

    async def get_previous_track_use_case(
        self,
        playlist_id: str,
        current_track_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the previous track in a playlist.

        Args:
            playlist_id: The playlist ID
            current_track_id: Current track ID

        Returns:
            Previous track data or None
        """
        try:
            return await self._track_service.get_previous_track(playlist_id, current_track_id)
        except Exception as e:
            logger.error(f"Failed to get previous track for playlist {playlist_id}: {e}")
            raise BusinessLogicError(f"Failed to get previous track: {str(e)}")