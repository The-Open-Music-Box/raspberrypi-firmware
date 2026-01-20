# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playlist Track API - Track Management Operations

Single Responsibility: Handle HTTP requests for playlist track operations.
"""

from fastapi import APIRouter, Body

from app.src.api.base_api_routes import BaseAPIRoutes
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService


class PlaylistTrackAPI(BaseAPIRoutes):
    """
    Handles track-related operations within playlists.

    Single Responsibility: HTTP operations for managing tracks within playlists.
    Inherits common API functionality from BaseAPIRoutes.
    """

    def __init__(self, playlist_service, broadcasting_service, router: APIRouter, operations_service=None):
        """Initialize playlist track API.

        Args:
            playlist_service: Application service for playlist operations
            broadcasting_service: Service for real-time state broadcasting
            router: Parent FastAPI router to register routes on
            operations_service: Service for complex playlist operations
        """
        super().__init__(
            router=router,
            playlist_service=playlist_service,
            broadcasting_service=broadcasting_service,
            operations_service=operations_service
        )
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
                # Accept both 'track_ids' (OpenAPI contract) and 'track_order' (legacy)
                track_ids = body.get("track_ids") or body.get("track_order")
                client_op_id = body.get("client_op_id")

                # Validate track_ids
                if not track_ids or not isinstance(track_ids, list):
                    return UnifiedResponseService.bad_request(
                        message="track_ids must be a non-empty list",
                        client_op_id=client_op_id
                    )

                # Use application service
                result = await self._playlist_service.reorder_tracks_use_case(playlist_id, track_ids)

                if result.get("status") == "success":
                    # Broadcast state change
                    await self._broadcasting_service.broadcast_tracks_reordered(
                        playlist_id, track_ids
                    )

                    return UnifiedResponseService.success(
                        message="Tracks reordered successfully",
                        data={"playlist_id": playlist_id, "client_op_id": client_op_id}
                    )
                return UnifiedResponseService.internal_error(
                    message=result.get("message", "Failed to reorder tracks")
                )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="reorder_tracks",
                    message="Failed to reorder tracks",
                    client_op_id=body.get("client_op_id") if isinstance(body, dict) else None,
                    playlist_id=playlist_id,
                    track_count=len(track_ids) if isinstance(track_ids, list) else None
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
                self.log_operation(
                    f"Deleting tracks from playlist {playlist_id}: {len(track_numbers)} tracks",
                    level="debug"
                )

                # Use application service
                result = await self._playlist_service.delete_tracks_use_case(playlist_id, track_numbers)

                if result.get("status") == "success":
                    # Broadcast state change
                    await self._broadcasting_service.broadcast_track_deleted(
                        playlist_id, track_numbers
                    )

                    return UnifiedResponseService.success(
                        message=f"Deleted {len(track_numbers)} tracks successfully",
                        data={"client_op_id": client_op_id}
                    )
                return UnifiedResponseService.internal_error(
                    message=result.get("message", "Failed to delete tracks")
                )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="delete_tracks",
                    message="Failed to delete tracks",
                    client_op_id=body.get("client_op_id") if isinstance(body, dict) else None,
                    playlist_id=playlist_id,
                    track_count=len(track_numbers) if isinstance(track_numbers, list) else None
                )

        @router.post("/move-track")
        @handle_http_errors()
        async def move_track_between_playlists(body: dict = Body(...)):
            """Move a track from one playlist to another."""
            try:
                source_playlist_id = body.get("source_playlist_id")
                target_playlist_id = body.get("target_playlist_id")
                track_number = body.get("number")
                target_position = body.get("target_position")
                client_op_id = body.get("client_op_id")

                if not source_playlist_id or not target_playlist_id or track_number is None:
                    return UnifiedResponseService.bad_request(
                        message="source_playlist_id, target_playlist_id, and track_number are required",
                        client_op_id=client_op_id
                    )

                # Use base class helper for service availability check
                service_check = self.check_service_available("Playlist operations", self._operations_service)
                if service_check:
                    return service_check

                # Use operations service for track movement
                result = await self._operations_service.move_track_between_playlists_use_case(
                    source_playlist_id, target_playlist_id, track_number, target_position
                )

                if result.get("status") == "success":
                    return UnifiedResponseService.success(
                        message=result.get("message", "Track moved successfully"),
                        data={"client_op_id": client_op_id or ""}
                    )
                return UnifiedResponseService.internal_error(
                    message=result.get("message", "Failed to move track")
                )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="move_track_between_playlists",
                    message="Failed to move track",
                    client_op_id=body.get("client_op_id") if isinstance(body, dict) else None,
                    source_playlist_id=body.get("source_playlist_id") if isinstance(body, dict) else None,
                    target_playlist_id=body.get("target_playlist_id") if isinstance(body, dict) else None,
                    track_number=body.get("number") if isinstance(body, dict) else None
                )
