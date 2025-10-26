# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playlist NFC API - NFC Tag Association Operations

Single Responsibility: Handle HTTP requests for NFC tag association with playlists.
"""

import logging
from fastapi import APIRouter, Body

from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


class PlaylistNfcAPI:
    """
    Handles NFC tag association operations for playlists.

    Single Responsibility: HTTP operations for linking NFC tags to playlists.
    """

    def __init__(self, broadcasting_service, router: APIRouter, operations_service):
        """Initialize playlist NFC API.

        Args:
            broadcasting_service: Service for real-time state broadcasting
            router: Parent FastAPI router to register routes on
            operations_service: Service for complex playlist operations
        """
        self._broadcasting_service = broadcasting_service
        self._operations_service = operations_service
        self._register_routes(router)

    def _register_routes(self, router: APIRouter):
        """Register all NFC association routes on the parent router.

        Args:
            router: The parent router to register routes on
        """

        @router.post("/nfc/{nfc_tag_id}/associate/{playlist_id}")
        @handle_http_errors()
        async def associate_nfc_tag(nfc_tag_id: str, playlist_id: str, body: dict = Body(None)):
            """Associate NFC tag with playlist."""
            try:
                body = body or {}
                client_op_id = body.get("client_op_id")

                if not self._operations_service:
                    return UnifiedResponseService.service_unavailable(
                        service="Playlist operations",
                        message="Operations service not available"
                    )

                # Use operations service for NFC association
                success = await self._operations_service.associate_nfc_tag_use_case(playlist_id, nfc_tag_id)

                if success:
                    # Broadcast NFC association
                    await self._broadcasting_service.broadcast_nfc_associated(playlist_id, nfc_tag_id)

                    return UnifiedResponseService.success(
                        message="NFC tag associated successfully",
                        data={"client_op_id": client_op_id}
                    )
                else:
                    return UnifiedResponseService.internal_error(
                        message="Failed to associate NFC tag"
                    )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error associating NFC tag: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to associate NFC tag",
                    operation="associate_nfc_tag"
                )

        @router.delete("/nfc/{playlist_id}")
        @handle_http_errors()
        async def remove_nfc_association(playlist_id: str, body: dict = Body(None)):
            """Remove NFC association from playlist."""
            try:
                body = body or {}
                client_op_id = body.get("client_op_id")

                if not self._operations_service:
                    return UnifiedResponseService.service_unavailable(
                        service="Playlist operations",
                        message="Operations service not available"
                    )

                # Use operations service for NFC disassociation
                success = await self._operations_service.disassociate_nfc_tag_use_case(playlist_id)

                if success:
                    # Broadcast NFC disassociation
                    await self._broadcasting_service.broadcast_nfc_disassociated(playlist_id)

                    return UnifiedResponseService.success(
                        message="NFC association removed successfully",
                        data={"client_op_id": client_op_id}
                    )
                else:
                    return UnifiedResponseService.internal_error(
                        message="Failed to remove NFC association"
                    )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error removing NFC association: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to remove NFC association",
                    operation="remove_nfc_association"
                )

        @router.get("/nfc/{nfc_tag_id}")
        @handle_http_errors()
        async def get_nfc_playlist(nfc_tag_id: str):
            """Get playlist associated with NFC tag."""
            try:
                if not self._operations_service:
                    return UnifiedResponseService.service_unavailable(
                        service="Playlist operations",
                        message="Operations service not available"
                    )

                # Use operations service to find playlist
                playlist = await self._operations_service.find_playlist_by_nfc_tag_use_case(nfc_tag_id)

                if playlist:
                    return UnifiedResponseService.success(
                        message="Playlist found for NFC tag",
                        data={"playlist": playlist}
                    )
                else:
                    return UnifiedResponseService.not_found(
                        resource="playlist",
                        message="No playlist found for NFC tag"
                    )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error getting NFC playlist: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to get playlist for NFC tag",
                    operation="get_nfc_playlist"
                )

