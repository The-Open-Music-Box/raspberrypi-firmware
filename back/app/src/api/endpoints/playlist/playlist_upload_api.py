# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playlist Upload API - Chunked File Upload Operations

Single Responsibility: Handle HTTP requests for file uploads to playlists.
"""

import logging
from fastapi import APIRouter, Body, File

from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


class PlaylistUploadAPI:
    """
    Handles chunked file upload operations for playlists.

    Single Responsibility: HTTP operations for uploading files to playlists.
    """

    def __init__(self, playlist_service, broadcasting_service, router: APIRouter, upload_controller):
        """Initialize playlist upload API.

        Args:
            playlist_service: Application service for playlist operations
            broadcasting_service: Service for real-time state broadcasting
            router: Parent FastAPI router to register routes on
            upload_controller: Controller for file upload operations
        """
        self._playlist_service = playlist_service
        self._broadcasting_service = broadcasting_service
        self._upload_controller = upload_controller
        self._register_routes(router)

    def _register_routes(self, router: APIRouter):
        """Register all upload routes on the parent router.

        Args:
            router: The parent router to register routes on
        """

        @router.post("/{playlist_id}/uploads/session", status_code=201)
        @handle_http_errors()
        async def init_upload_session(playlist_id: str, body: dict = Body(...)):
            """Initialize chunked upload session."""
            try:
                filename = body.get("filename")
                file_size = body.get("file_size")
                chunk_size = body.get("chunk_size", 1024 * 1024)
                file_hash = body.get("file_hash")

                if not filename or not file_size:
                    return UnifiedResponseService.bad_request(
                        message="filename and file_size are required"
                    )

                if not self._upload_controller:
                    return UnifiedResponseService.service_unavailable(
                        service="Upload",
                        message="Upload service not available"
                    )

                result = await self._upload_controller.init_upload_session(
                    playlist_id, filename, file_size, chunk_size, file_hash
                )

                return UnifiedResponseService.success(
                    message="Upload session initialized successfully",
                    data=result
                )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error initializing upload session: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to initialize upload session",
                    operation="init_upload_session"
                )

        @router.put("/{playlist_id}/uploads/{session_id}/chunks/{chunk_index}")
        @handle_http_errors()
        async def upload_chunk(playlist_id: str, session_id: str, chunk_index: int, file: bytes = File(...)):
            """Upload a file chunk."""
            try:
                if not self._upload_controller:
                    return UnifiedResponseService.service_unavailable(
                        service="Upload",
                        message="Upload service not available"
                    )

                result = await self._upload_controller.upload_chunk(
                    playlist_id=playlist_id,
                    session_id=session_id,
                    chunk_index=chunk_index,
                    chunk_data=file,
                )

                return UnifiedResponseService.success(
                    message="Chunk uploaded successfully",
                    data=result
                )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error uploading chunk: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to upload chunk",
                    operation="upload_chunk"
                )

        @router.post("/{playlist_id}/uploads/{session_id}/finalize")
        @handle_http_errors()
        async def finalize_upload(playlist_id: str, session_id: str, body: dict = Body(None)):
            """Finalize upload and broadcast track addition."""
            try:
                body = body or {}
                client_op_id = body.get("client_op_id")

                logger.info(f"Finalizing upload for session {session_id} in playlist {playlist_id}")

                if not self._upload_controller:
                    return UnifiedResponseService.service_unavailable(
                        service="Upload",
                        message="Upload service not available"
                    )

                # Finalize upload via upload controller
                result = await self._upload_controller.finalize_upload(
                    playlist_id=playlist_id,
                    session_id=session_id,
                    file_hash=body.get("file_hash"),
                    metadata_override=body.get("metadata_override"),
                )

                if result.get("status") != "success":
                    return UnifiedResponseService.internal_error(
                        message=result.get("message", "Upload finalization failed"),
                        operation="finalize_upload",
                    )

                # Upload successful, integrate with playlist
                if result.get("track"):
                    track_data = result["track"]
                    track_entry = {
                        "title": track_data.get("title"),
                        "filename": track_data.get("filename"),
                        "file_path": track_data.get("file_path"),
                        "duration_ms": track_data.get("duration"),
                        "artist": track_data.get("artist"),
                        "album": track_data.get("album"),
                        "file_size": track_data.get("file_size"),
                        "track_number": track_data.get("track_number", 1),
                    }

                    # Add track via application service
                    try:
                        created_track = await self._playlist_service.add_track_use_case(
                            playlist_id=playlist_id, track_data=track_entry
                        )
                        integration_result = {"status": "success", "track": created_track}
                    except Exception as e:
                        # Re-raise system exceptions
                        if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                            raise
                        logger.error(f"Failed to add track to playlist: {e}")
                        integration_result = {"status": "error", "message": str(e)}

                    if integration_result.get("status") != "success":
                        return UnifiedResponseService.internal_error(
                            message=integration_result.get(
                                "message", "Failed to integrate track into playlist"
                            ),
                            operation="finalize_upload",
                        )

                    # Broadcast track addition
                    await self._broadcasting_service.broadcast_track_added(playlist_id, track_entry)

                return UnifiedResponseService.success(
                    message="Upload finalized and track added to playlist successfully",
                    data=result
                )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error finalizing upload: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to finalize upload",
                    operation="finalize_upload"
                )

        @router.get("/{playlist_id}/uploads/{session_id}")
        @handle_http_errors()
        async def get_upload_status(playlist_id: str, session_id: str):
            """Get upload session status."""
            try:
                if not self._upload_controller:
                    return UnifiedResponseService.service_unavailable(
                        service="Upload",
                        message="Upload service not available"
                    )

                result = await self._upload_controller.get_session_status(session_id)

                return UnifiedResponseService.success(
                    message="Upload status retrieved successfully",
                    data=result
                )

            except Exception as e:
                # Re-raise system exceptions
                if isinstance(e, (SystemExit, KeyboardInterrupt, GeneratorExit)):
                    raise
                logger.error(f"Error getting upload status: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to get upload status",
                    operation="get_upload_status"
                )

