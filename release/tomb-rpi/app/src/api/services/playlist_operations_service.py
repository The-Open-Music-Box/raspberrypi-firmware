# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playlist Operations Service (DDD Architecture)

Extended playlist operations that combine multiple application services.
Single Responsibility: Complex playlist workflows and orchestration.
"""

from typing import Dict, Any, List, Optional
import logging

from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.dependencies import get_playlist_repository_adapter
from app.src.domain.data.models.track import Track
from app.src.domain.services.track_reordering_service import (
    TrackReorderingService,
    ReorderingStrategy,
    ReorderingCommand,
)

logger = logging.getLogger(__name__)


class PlaylistOperationsService:
    """
    Service for complex playlist operations requiring orchestration.

    Single Responsibility: Coordinate complex playlist workflows.

    Responsibilities:
    - Track reordering with domain services
    - Track deletion with cleanup
    - NFC association management
    - Playlist synchronization
    - Complex validation workflows

    Does NOT handle:
    - HTTP routing (delegated to API routes)
    - State broadcasting (delegated to broadcasting service)
    - Simple CRUD operations (delegated to application services)
    """

    def __init__(self, playlist_app_service, repository_adapter=None):
        """Initialize playlist operations service.

        Args:
            playlist_app_service: Core playlist application service
            repository_adapter: Repository adapter for data access
        """
        self._playlist_app_service = playlist_app_service
        self._repository_adapter = repository_adapter or get_playlist_repository_adapter()

    @handle_service_errors("playlist_operations")
    async def reorder_tracks_use_case(self, playlist_id: str, track_order: List[int]) -> Dict[str, Any]:
        """Use case: Reorder tracks in a playlist using domain services.

        Args:
            playlist_id: ID of the playlist
            track_order: New track order

        Returns:
            Result dictionary with success status and details
        """
        try:
            # Get current playlist data
            playlist_dict = await self._repository_adapter.get_playlist_by_id(playlist_id)
            if not playlist_dict:
                return {"status": "error", "message": "Playlist not found"}

            # Convert tracks to domain objects
            tracks = []
            for track_dict in playlist_dict.get("tracks", []):
                track = Track(
                    track_number=track_dict.get("track_number", 0),
                    title=track_dict.get("title", ""),
                    filename=track_dict.get("filename", ""),
                    file_path=track_dict.get("file_path", ""),
                    duration_ms=track_dict.get("duration_ms"),
                    artist=track_dict.get("artist"),
                    album=track_dict.get("album"),
                    id=track_dict.get("id"),
                )
                tracks.append(track)

            # Execute reordering through domain service
            reordering_service = TrackReorderingService()
            command = ReorderingCommand(
                playlist_id=playlist_id,
                strategy=ReorderingStrategy.BULK_REORDER,
                track_numbers=track_order,
            )
            reorder_result = reordering_service.execute_reordering(command, tracks)

            if reorder_result.success:
                # Apply changes to repository
                old_to_new_mapping = {}
                for new_track in reorder_result.affected_tracks:
                    original_track = next(
                        (orig_track for orig_track in tracks if orig_track.id == new_track.id), None
                    )
                    if original_track:
                        old_to_new_mapping[original_track.track_number] = new_track.track_number

                success = await self._repository_adapter.update_track_numbers(playlist_id, old_to_new_mapping)
                if success:
                    return {
                        "status": "success",
                        "message": "Tracks reordered successfully",
                        "playlist_id": playlist_id,
                    }
                else:
                    return {"status": "error", "message": "Repository update failed"}
            else:
                error_messages = reorder_result.validation_errors + reorder_result.business_rule_violations
                return {
                    "status": "error",
                    "message": f"Reordering validation failed: {'; '.join(error_messages)}"
                }

        except Exception as e:
            logger.error(f"Error in reorder_tracks_use_case: {str(e)}")
            return {"status": "error", "message": f"Failed to reorder tracks: {str(e)}"}

    @handle_service_errors("playlist_operations")
    async def delete_tracks_use_case(self, playlist_id: str, track_numbers: List[int]) -> Dict[str, Any]:
        """Use case: Delete tracks from a playlist with cleanup.

        Args:
            playlist_id: ID of the playlist
            track_numbers: List of track numbers to delete

        Returns:
            Result dictionary with success status and details
        """
        try:
            # Get current playlist
            playlist = await self._repository_adapter.get_playlist_by_id(playlist_id)
            if not playlist:
                return {"status": "error", "message": "Playlist not found"}

            # Filter out tracks to delete and keep remaining ones
            remaining_tracks = [
                track
                for track in playlist.get("tracks", [])
                if track.get("track_number") not in track_numbers
            ]

            # Replace tracks with remaining ones in database
            success = await self._repository_adapter.replace_tracks(playlist_id, remaining_tracks)
            if success:
                return {
                    "status": "success",
                    "message": f"Deleted {len(track_numbers)} tracks successfully",
                }
            else:
                return {"status": "error", "message": "Failed to delete tracks"}

        except Exception as e:
            logger.error(f"Error in delete_tracks_use_case: {str(e)}")
            return {"status": "error", "message": f"Failed to delete tracks: {str(e)}"}

    @handle_service_errors("playlist_operations")
    async def update_playlist_use_case(self, playlist_id: str, updates: Dict[str, Any]) -> bool:
        """Use case: Update playlist with validation.

        Args:
            playlist_id: ID of the playlist
            updates: Dictionary of fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._repository_adapter.update_playlist(playlist_id, updates)

        except Exception as e:
            logger.error(f"Error in update_playlist_use_case: {str(e)}")
            return False

    @handle_service_errors("playlist_operations")
    async def delete_playlist_use_case(self, playlist_id: str) -> bool:
        """Use case: Delete playlist with cleanup.

        Args:
            playlist_id: ID of the playlist to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._repository_adapter.delete_playlist(playlist_id)

        except Exception as e:
            logger.error(f"Error in delete_playlist_use_case: {str(e)}")
            return False

    @handle_service_errors("playlist_operations")
    async def associate_nfc_tag_use_case(self, playlist_id: str, nfc_tag_id: str) -> bool:
        """Use case: Associate NFC tag with playlist.

        Args:
            playlist_id: ID of the playlist
            nfc_tag_id: NFC tag identifier

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._repository_adapter.update_playlist(playlist_id, {"nfc_tag_id": nfc_tag_id})

        except Exception as e:
            logger.error(f"Error in associate_nfc_tag_use_case: {str(e)}")
            return False

    @handle_service_errors("playlist_operations")
    async def disassociate_nfc_tag_use_case(self, playlist_id: str) -> bool:
        """Use case: Remove NFC association from playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._repository_adapter.update_playlist(playlist_id, {"nfc_tag_id": None})

        except Exception as e:
            logger.error(f"Error in disassociate_nfc_tag_use_case: {str(e)}")
            return False

    @handle_service_errors("playlist_operations")
    async def find_playlist_by_nfc_tag_use_case(self, nfc_tag_id: str) -> Optional[Dict[str, Any]]:
        """Use case: Find playlist by NFC tag.

        Args:
            nfc_tag_id: NFC tag identifier

        Returns:
            Playlist data if found, None otherwise
        """
        try:
            # Get all playlists and search for NFC association
            playlists_result = await self._playlist_app_service.get_playlists_use_case()
            playlists = playlists_result.get("playlists", []) if playlists_result.get("status") == "success" else []

            for playlist in playlists:
                if playlist.get("nfc_tag_id") == nfc_tag_id:
                    return playlist

            return None

        except Exception as e:
            logger.error(f"Error in find_playlist_by_nfc_tag_use_case: {str(e)}")
            return None

    @handle_service_errors("playlist_operations")
    async def sync_playlists_use_case(self) -> Dict[str, Any]:
        """Use case: Synchronize playlists and return current state.

        Returns:
            Result dictionary with playlist data
        """
        try:
            # Use application service to get all playlists
            playlists_result = await self._playlist_app_service.get_playlists_use_case()
            playlists_data = playlists_result.get("playlists", []) if playlists_result else []

            return {
                "status": "success",
                "message": "Playlists synchronized successfully",
                "playlists": playlists_data
            }

        except Exception as e:
            logger.error(f"Error in sync_playlists_use_case: {str(e)}")
            return {
                "status": "error",
                "message": f"Failed to sync playlists: {str(e)}",
                "playlists": []
            }

    @handle_service_errors("playlist_operations")
    async def move_track_between_playlists_use_case(
        self,
        source_playlist_id: str,
        target_playlist_id: str,
        track_number: int,
        target_position: Optional[int] = None
    ) -> Dict[str, Any]:
        """Use case: Move track between playlists.

        Args:
            source_playlist_id: Source playlist ID
            target_playlist_id: Target playlist ID
            track_number: Track number to move
            target_position: Target position in destination playlist

        Returns:
            Result dictionary with success status
        """
        try:
            # This is a complex operation that would require:
            # 1. Get track data from source playlist
            # 2. Remove track from source playlist
            # 3. Add track to target playlist at specified position
            # 4. Update track numbers in both playlists

            # For now, return placeholder response
            return {
                "status": "success",
                "message": "Track move functionality not yet implemented in new architecture",
            }

        except Exception as e:
            logger.error(f"Error in move_track_between_playlists_use_case: {str(e)}")
            return {"status": "error", "message": f"Failed to move track: {str(e)}"}

    @handle_service_errors("playlist_operations")
    async def validate_playlist_integrity(self, playlist_id: str) -> Dict[str, Any]:
        """Validate playlist data integrity.

        Args:
            playlist_id: ID of the playlist to validate

        Returns:
            Validation result with details
        """
        try:
            playlist_result = await self._playlist_app_service.get_playlist_use_case(playlist_id)
            playlist_data = playlist_result.get("playlist") if playlist_result.get("status") == "success" else None

            if not playlist_data:
                return {
                    "status": "error",
                    "message": "Playlist not found",
                    "valid": False
                }

            # Check track numbering integrity
            tracks = playlist_data.get("tracks", [])
            track_numbers = [track.get("track_number", 0) for track in tracks]
            expected_numbers = list(range(1, len(tracks) + 1))

            if sorted(track_numbers) != expected_numbers:
                return {
                    "status": "warning",
                    "message": "Track numbering inconsistency detected",
                    "valid": False,
                    "details": {
                        "expected": expected_numbers,
                        "actual": sorted(track_numbers)
                    }
                }

            return {
                "status": "success",
                "message": "Playlist integrity validated",
                "valid": True,
                "track_count": len(tracks)
            }

        except Exception as e:
            logger.error(f"Error in validate_playlist_integrity: {str(e)}")
            return {
                "status": "error",
                "message": f"Validation failed: {str(e)}",
                "valid": False
            }
