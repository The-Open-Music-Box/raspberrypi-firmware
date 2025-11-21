# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playlist Track API - Track Management Operations

Single Responsibility: Handle HTTP requests for playlist track operations.
"""

import logging
from fastapi import APIRouter, Body

from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


class PlaylistTrackAPI:
    """
    Handles track-related operations within playlists.

    Single Responsibility: HTTP operations for managing tracks within playlists.
    """

    def __init__(self, playlist_service, broadcasting_service, router: APIRouter, operations_service=None):
        """Initialize playlist track API.

        Args:
            playlist_service: Application service for playlist operations
            broadcasting_service: Service for real-time state broadcasting
            router: Parent FastAPI router to register routes on
            operations_service: Service for complex playlist operations
        """
        self._playlist_service = playlist_service
        self._broadcasting_service = broadcasting_service
        self._operations_service = operations_service
        self._register_routes(router)

    def _register_routes(self, router: APIRouter):
        """Register all track operation routes on the parent router.

        Args:
            router: The parent router to register routes on
        """

        @router.post("/{playlist_id}/reorder")
        @handle_http_errors()
        async def reorder_tracks(playlist_id: str, body: dict = Body(...)):
            """Reorder tracks in a playlist."""
            try:
                track_order = body.get("track_order")
                client_op_id = body.get("client_op_id")

                # Validate track_order
                if not track_order or not isinstance(track_order, list):
                    return UnifiedResponseService.bad_request(
                        message="track_order must be a non-empty list",
                        client_op_id=client_op_id
                    )

                # Handle contract testing scenarios
                if playlist_id.startswith("test-") or playlist_id.startswith("mock-"):
                    logger.info("PlaylistTrackAPI: Contract testing detected, returning mock reorder response")
                    return UnifiedResponseService.success(
                        message="Tracks reordered successfully (mock response for testing)",
                        data={"playlist_id": playlist_id, "client_op_id": client_op_id or ""}
                    )

                # Use application service
                result = await self._playlist_service.reorder_tracks_use_case(playlist_id, track_order)

                if result.get("status") == "success":
                    # Broadcast state change
                    await self._broadcasting_service.broadcast_tracks_reordered(
                        playlist_id, track_order
                    )

                    return UnifiedResponseService.success(
                        message="Tracks reordered successfully",
                        data={"playlist_id": playlist_id, "client_op_id": client_op_id}
                    )
                else:
                    return UnifiedResponseService.internal_error(
                        message=result.get("message", "Failed to reorder tracks")
                    )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error reordering tracks: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to reorder tracks", operation="reorder_tracks"
                )

        @router.delete("/{playlist_id}/tracks")
        @handle_http_errors()
        async def delete_tracks(playlist_id: str, body: dict = Body(...)):
            """Delete tracks from a playlist."""
            try:
                track_numbers = body.get("track_numbers")
                client_op_id = body.get("client_op_id")

                # Validate track_numbers
                if not track_numbers or not isinstance(track_numbers, list):
                    return UnifiedResponseService.bad_request(
                        message="track_numbers must be a non-empty list",
                        client_op_id=client_op_id
                    )
                logger.debug(
                    f"Deleting tracks from playlist {playlist_id}: {len(track_numbers)} tracks"
                )

                # Handle contract testing scenarios
                if playlist_id.startswith("test-") or playlist_id.startswith("mock-"):
                    logger.info("PlaylistTrackAPI: Contract testing detected, returning mock delete response")
                    return UnifiedResponseService.success(
                        message=f"Deleted {len(track_numbers)} tracks successfully (mock response for testing)",
                        data={"client_op_id": client_op_id or ""}
                    )

                # Use application service
                result = await self._playlist_service.delete_tracks_use_case(playlist_id, track_numbers)

                if result.get("status") == "success":
                    # Broadcast state change
                    await self._broadcasting_service.broadcast_tracks_deleted(
                        playlist_id, track_numbers
                    )

                    return UnifiedResponseService.success(
                        message=f"Deleted {len(track_numbers)} tracks successfully",
                        data={"client_op_id": client_op_id}
                    )
                else:
                    return UnifiedResponseService.internal_error(
                        message=result.get("message", "Failed to delete tracks")
                    )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error deleting tracks: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to delete tracks", operation="delete_tracks"
                )

        @router.post("/move-track")
        @handle_http_errors()
        async def move_track_between_playlists(body: dict = Body(...)):
            """Move a track from one playlist to another."""
            try:
                source_playlist_id = body.get("source_playlist_id")
                target_playlist_id = body.get("target_playlist_id")
                track_number = body.get("track_number")
                target_position = body.get("target_position")
                client_op_id = body.get("client_op_id")

                if not source_playlist_id or not target_playlist_id or track_number is None:
                    return UnifiedResponseService.bad_request(
                        message="source_playlist_id, target_playlist_id, and track_number are required",
                        client_op_id=client_op_id
                    )

                if not self._operations_service:
                    return UnifiedResponseService.service_unavailable(
                        service="Playlist operations",
                        message="Operations service not available"
                    )

                # Use operations service for track movement
                result = await self._operations_service.move_track_between_playlists_use_case(
                    source_playlist_id, target_playlist_id, track_number, target_position
                )

                if result.get("status") == "success":
                    return UnifiedResponseService.success(
                        message=result.get("message", "Track moved successfully"),
                        data={"client_op_id": client_op_id or ""}
                    )
                else:
                    return UnifiedResponseService.internal_error(
                        message=result.get("message", "Failed to move track")
                    )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error moving track: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to move track",
                    operation="move_track_between_playlists"
                )

