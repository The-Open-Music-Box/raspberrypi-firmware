# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Upload API Routes (DDD Architecture)

Clean API routes following Domain-Driven Design principles.
Single Responsibility: HTTP route handling for upload session management.
"""

from typing import Optional
from fastapi import APIRouter, Query, Request
import logging

from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


class UploadAPIRoutes:
    """
    Pure API routes handler for upload session management.

    Responsibilities:
    - HTTP request/response handling for upload sessions
    - Session listing and filtering
    - Session cleanup operations
    - Error handling

    Does NOT handle:
    - Actual file uploads (delegated to upload controller)
    - Business logic (delegated to upload services)
    - File storage (delegated to storage adapters)
    """

    def __init__(self, upload_controller_getter):
        """Initialize upload API routes.

        Args:
            upload_controller_getter: Callable that returns upload controller from request
        """
        # Don't add prefix here - it's added by the factory when including router
        self.router = APIRouter(tags=["uploads"])
        self._get_upload_controller = upload_controller_getter
        self._register_routes()

    def _register_routes(self):
        """Register all upload session management routes."""

        @self.router.get("/sessions")
        @handle_http_errors()
        async def list_upload_sessions(
            request: Request,
            status: Optional[str] = Query(None, description="Filter by upload status"),
            limit: int = Query(50, ge=1, le=100, description="Maximum sessions to return"),
        ):
            """List all upload sessions with optional filtering."""
            try:
                # Get upload controller
                upload_controller = self._get_upload_controller(request)
                if not upload_controller:
                    return UnifiedResponseService.error(
                        message="Upload service not available",
                        error_type="service_unavailable",
                        status_code=503
                    )

                # Get all active sessions
                sessions_data = []
                if hasattr(upload_controller, "chunked") and hasattr(
                    upload_controller.chunked, "_sessions"
                ):
                    for session_id, session_info in upload_controller.chunked._sessions.items():
                        if not session_info or not isinstance(session_info, dict):
                            continue

                        session_data = {
                            "session_id": session_id,
                            "filename": session_info.get("filename", "unknown"),
                            "file_size": session_info.get("file_size", 0),
                            "chunks_uploaded": session_info.get("chunks_received", 0),
                            "chunks_total": session_info.get("total_chunks", 0),
                            "progress_percent": round(
                                (
                                    session_info.get("chunks_received", 0)
                                    / max(1, session_info.get("total_chunks", 1))
                                )
                                * 100,
                                2,
                            ),
                            "playlist_id": session_info.get("playlist_id"),
                            "created_at": session_info.get("created_at"),
                            "status": self._determine_session_status(session_info),
                        }

                        # Apply status filter
                        if status is None or session_data["status"] == status:
                            sessions_data.append(session_data)
                            if len(sessions_data) >= limit:
                                break

                logger.info(f"Listed {len(sessions_data)} upload sessions")
                return UnifiedResponseService.success(
                    message=f"Found {len(sessions_data)} upload sessions",
                    data={"sessions": sessions_data}
                )

            except Exception as e:
                logger.error(f"Error listing upload sessions: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to list upload sessions",
                    operation="list_upload_sessions"
                )

        @self.router.delete("/sessions/{session_id}")
        @handle_http_errors()
        async def delete_upload_session(session_id: str, request: Request):
            """Delete a specific upload session."""
            try:
                # Get upload controller
                upload_controller = self._get_upload_controller(request)
                if not upload_controller:
                    return UnifiedResponseService.error(
                        message="Upload service not available",
                        error_type="service_unavailable",
                        status_code=503
                    )

                # Try to remove the session
                if hasattr(upload_controller, "chunked") and upload_controller.chunked:
                    if hasattr(upload_controller.chunked, "_sessions") and upload_controller.chunked._sessions:
                        if session_id not in upload_controller.chunked._sessions:
                            return UnifiedResponseService.not_found(
                                resource="Upload session",
                                resource_id=session_id
                            )

                        # Remove session
                        del upload_controller.chunked._sessions[session_id]
                        logger.info(f"Deleted upload session: {session_id}")

                        # Cleanup temporary files
                        if hasattr(upload_controller.chunked, "_cleanup_session_files"):
                            await upload_controller.chunked._cleanup_session_files(session_id)

                return UnifiedResponseService.success(
                    message=f"Upload session deleted: {session_id}"
                )

            except Exception as e:
                logger.error(f"Error deleting upload session: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to delete upload session",
                    operation="delete_upload_session"
                )

        @self.router.post("/cleanup")
        @handle_http_errors()
        async def cleanup_stale_sessions(
            request: Request,
            max_age_hours: int = Query(24, ge=1, le=168, description="Maximum age in hours for cleanup"),
        ):
            """Cleanup stale upload sessions older than specified age."""
            try:
                # Get upload controller
                upload_controller = self._get_upload_controller(request)
                if not upload_controller:
                    return UnifiedResponseService.error(
                        message="Upload service not available",
                        error_type="service_unavailable",
                        status_code=503
                    )

                from datetime import datetime, timedelta

                cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
                cleaned_sessions = []

                if hasattr(upload_controller, "chunked") and upload_controller.chunked:
                    if hasattr(upload_controller.chunked, "_sessions") and upload_controller.chunked._sessions:
                        sessions_to_remove = []

                        for session_id, session_info in upload_controller.chunked._sessions.items():
                            created_at = session_info.get("created_at")
                            if created_at:
                                try:
                                    if isinstance(created_at, str):
                                        session_time = datetime.fromisoformat(
                                            created_at.replace("Z", "+00:00")
                                        )
                                    else:
                                        session_time = created_at

                                    if session_time < cutoff_time:
                                        sessions_to_remove.append(session_id)
                                        cleaned_sessions.append({
                                            "session_id": session_id,
                                            "filename": session_info.get("filename", "unknown"),
                                            "age_hours": (datetime.now() - session_time).total_seconds() / 3600,
                                        })
                                except Exception as e:
                                    logger.warning(f"Could not parse creation time for session {session_id}: {e}")

                        # Remove stale sessions
                        for session_id in sessions_to_remove:
                            del upload_controller.chunked._sessions[session_id]
                            if hasattr(upload_controller.chunked, "_cleanup_session_files"):
                                await upload_controller.chunked._cleanup_session_files(session_id)

                logger.info(f"Cleaned up {len(cleaned_sessions)} stale upload sessions")
                return UnifiedResponseService.success(
                    message=f"Cleaned up {len(cleaned_sessions)} stale sessions",
                    data={"cleaned_sessions": cleaned_sessions}
                )

            except Exception as e:
                logger.error(f"Error cleaning up sessions: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to cleanup stale sessions",
                    operation="cleanup_stale_sessions"
                )

    def _determine_session_status(self, session_info: dict) -> str:
        """Determine the status of an upload session."""
        chunks_received = session_info.get("chunks_received", 0)
        total_chunks = session_info.get("total_chunks", 0)

        if chunks_received == 0:
            return "pending"
        elif chunks_received < total_chunks:
            return "uploading"
        elif chunks_received == total_chunks:
            return "completed"
        else:
            return "error"

    def get_router(self) -> APIRouter:
        """Get the configured router."""
        return self.router
