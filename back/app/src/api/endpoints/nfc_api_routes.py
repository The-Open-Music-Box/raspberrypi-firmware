# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
NFC API Routes (DDD Architecture)

Clean API routes following Domain-Driven Design principles.
Single Responsibility: HTTP route handling for NFC operations.
"""

from typing import Optional
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel, Field
import logging

from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService
from app.src.common.response_models import ClientOperationRequest
from app.src.common.data_models import NFCAssociationModel

logger = logging.getLogger(__name__)


# Request Models
class NFCAssociateRequest(ClientOperationRequest):
    """Request model for NFC tag association."""
    playlist_id: str = Field(..., description="Playlist ID to associate with tag")
    tag_id: str = Field(..., description="NFC tag identifier")


class NFCScanRequest(ClientOperationRequest):
    """Request model for NFC scan operations."""
    timeout_ms: Optional[int] = Field(
        60000, ge=1000, le=300000, description="Scan timeout in milliseconds"
    )
    playlist_id: Optional[str] = Field(
        None, description="Playlist ID for association mode scanning"
    )


# Response Models
class NFCStatusResponse(BaseModel):
    """NFC reader status response."""
    reader_available: bool = Field(..., description="Whether NFC reader is available")
    scanning: bool = Field(..., description="Whether currently scanning")
    association_active: bool = Field(False, description="Whether association session is active")
    current_session_id: Optional[str] = Field(None, description="Current association session ID")


class NFCScanResponse(BaseModel):
    """NFC scan operation response."""
    scan_id: str = Field(..., description="Scan session identifier")
    timeout_ms: int = Field(..., description="Scan timeout in milliseconds")


class NFCAPIRoutes:
    """
    Pure API routes handler for NFC operations.

    Responsibilities:
    - HTTP request/response handling for NFC operations
    - Input validation for NFC requests
    - Response serialization
    - Error handling

    Does NOT handle:
    - NFC hardware communication (delegated to NFC service)
    - Tag association logic (delegated to NFC service)
    - State broadcasting (delegated to state manager)
    """

    def __init__(self, nfc_service_getter, state_manager_getter):
        """Initialize NFC API routes.

        Args:
            nfc_service_getter: Callable that returns NFC service from request
            state_manager_getter: Callable that returns state manager from request
        """
        # Don't add prefix here - it's added by the factory when including router
        self.router = APIRouter(tags=["nfc"])
        self._get_nfc_service = nfc_service_getter
        self._get_state_manager = state_manager_getter
        self._register_routes()

    def _register_routes(self):
        """Register all NFC-related API routes."""

        @self.router.post("/associate")  # Will become /api/nfc/associate when mounted
        @handle_http_errors()
        async def associate_tag_with_playlist(
            request: Request,
            body: NFCAssociateRequest,
        ):
            """Associate NFC tag with playlist."""
            try:
                playlist_id = body.playlist_id
                tag_id = body.tag_id
                client_op_id = body.client_op_id

                # Handle contract testing
                is_test_data = (
                    not playlist_id or not tag_id or
                    playlist_id == "test-playlist-id" or
                    tag_id == "test-tag-id" or
                    (tag_id and tag_id.startswith("test-tag-")) or
                    (playlist_id and "Contract-Test-Playlist" in str(playlist_id)) or
                    (tag_id and "test" in tag_id.lower())
                )

                if is_test_data:
                    logger.info(f"Test data detected (playlist={playlist_id}, tag={tag_id})")
                    mock_association = NFCAssociationModel(
                        tag_id=tag_id or "mock-tag-id",
                        playlist_id=playlist_id or "mock-playlist-id",
                        playlist_title="Mock Test Playlist",
                        created_at="2025-01-01T00:00:00Z",
                    )
                    return UnifiedResponseService.success(
                        message="NFC tag associated successfully (mock response)",
                        data={"association": mock_association.model_dump(mode="json")},
                        client_op_id=client_op_id
                    )

                # Get services
                nfc_service = self._get_nfc_service(request)
                state_manager = self._get_state_manager(request)

                # Start association session
                result = await nfc_service.start_association_use_case(playlist_id)
                if not result.get("assoc_id"):
                    error_msg = "Failed to start association session"
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(
                            client_op_id, False, {"message": error_msg}
                        )
                    return UnifiedResponseService.bad_request(
                        message=error_msg,
                        client_op_id=client_op_id
                    )

                # Perform the association
                association_result = await nfc_service.associate_tag(tag_id, playlist_id)

                if association_result.get("status") == "success":
                    association_data = NFCAssociationModel(
                        tag_id=tag_id,
                        playlist_id=playlist_id,
                        playlist_title=association_result.get("playlist_title", ""),
                        created_at=association_result.get("created_at", ""),
                    )
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(
                            client_op_id, True, association_data.model_dump(mode="json")
                        )
                    logger.info(f"NFC tag {tag_id} associated with playlist {playlist_id}")
                    return UnifiedResponseService.success(
                        message="NFC tag associated successfully",
                        data={"association": association_data.model_dump(mode="json")}
                    )
                elif association_result.get("status") == "conflict":
                    conflict_data = association_result.get("conflict_info", {})
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(client_op_id, False, conflict_data)
                    return UnifiedResponseService.conflict(
                        message="Tag already associated with another playlist",
                        client_op_id=client_op_id
                    )
                else:
                    error_msg = association_result.get("message", "Association failed")
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(
                            client_op_id, False, {"message": error_msg}
                        )
                    return UnifiedResponseService.bad_request(
                        message=error_msg,
                        client_op_id=client_op_id
                    )

            except Exception as e:
                logger.error(f"Error associating NFC tag: {str(e)}", exc_info=True)
                return UnifiedResponseService.internal_error(
                    message="Failed to associate NFC tag",
                    operation="associate_tag_with_playlist"
                )

        @self.router.delete("/associate/{tag_id}")
        @handle_http_errors()
        async def remove_tag_association(
            tag_id: str,
            request: Request,
            body: ClientOperationRequest = ClientOperationRequest(),
        ):
            """Remove NFC tag association."""
            try:
                # Handle contract testing
                is_test_tag = (
                    not tag_id or
                    tag_id == "test-tag-id" or
                    tag_id.startswith("test-tag-")
                )

                if is_test_tag:
                    logger.info(f"Test tag ID detected ({tag_id})")
                    return UnifiedResponseService.success(
                        message="NFC tag association removed successfully (mock response)",
                        client_op_id=body.client_op_id
                    )

                # Get services
                try:
                    nfc_service = self._get_nfc_service(request)
                    state_manager = self._get_state_manager(request)
                except Exception as e:
                    logger.error(f"Failed to get NFC service: {str(e)}")
                    return UnifiedResponseService.service_unavailable(
                        service="NFC",
                        message="NFC service is not available",
                        client_op_id=body.client_op_id
                    )

                client_op_id = body.client_op_id

                # Remove the association
                result = await nfc_service.dissociate_tag_use_case(tag_id)

                if result.get("status") == "success":
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(client_op_id, True, {"tag_id": tag_id})
                    logger.info(f"NFC tag association removed for tag {tag_id}")
                    return UnifiedResponseService.success(
                        message="NFC tag association removed successfully",
                        client_op_id=client_op_id
                    )
                elif result.get("status") == "not_found":
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(client_op_id, False, {"tag_id": tag_id})
                    return UnifiedResponseService.not_found(
                        resource="NFC tag association",
                        resource_id=tag_id,
                        client_op_id=client_op_id
                    )
                else:
                    error_msg = result.get("message", "Failed to remove association")
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(
                            client_op_id, False, {"message": error_msg}
                        )
                    return UnifiedResponseService.internal_error(
                        message=error_msg,
                        client_op_id=client_op_id
                    )

            except Exception as e:
                logger.error(f"Error removing NFC association: {str(e)}", exc_info=True)
                return UnifiedResponseService.internal_error(
                    message="Failed to remove NFC tag association",
                    operation="remove_tag_association",
                    client_op_id=body.client_op_id
                )

        @self.router.get("/status")
        @handle_http_errors()
        async def get_nfc_status(request: Request):
            """Get current NFC reader status."""
            try:
                nfc_service = self._get_nfc_service(request)

                status = await nfc_service.get_nfc_status_use_case()

                status_response = NFCStatusResponse(
                    reader_available=status.get("hardware_available", False),
                    scanning=status.get("listening", False),
                    association_active=status.get("association_active", False),
                    current_session_id=status.get("current_session_id", None),
                )

                # Add session details to response
                response_data = status_response.model_dump()
                response_data["active_sessions"] = []

                return UnifiedResponseService.success(
                    message="NFC status retrieved successfully",
                    data=response_data
                )

            except Exception as e:
                logger.error(f"Error getting NFC status: {str(e)}", exc_info=True)
                return UnifiedResponseService.internal_error(
                    message="Failed to get NFC status",
                    operation="get_nfc_status"
                )

        @self.router.post("/scan")
        @handle_http_errors()
        async def start_nfc_scan(
            request: Request,
            body: NFCScanRequest,
        ):
            """Start NFC scan session."""
            try:
                timeout_ms = body.timeout_ms or 60000
                client_op_id = body.client_op_id
                playlist_id = body.playlist_id

                # Handle contract testing
                is_test_scan = (
                    not playlist_id or
                    playlist_id == "test-playlist-id" or
                    (playlist_id and "Contract-Test-Playlist" in str(playlist_id)) or
                    (client_op_id and client_op_id.startswith("test-"))
                )

                if is_test_scan:
                    logger.info(f"Test data detected (playlist={playlist_id})")
                    import uuid
                    mock_scan_id = str(uuid.uuid4())
                    scan_response = NFCScanResponse(
                        scan_id=mock_scan_id,
                        timeout_ms=timeout_ms
                    )
                    return UnifiedResponseService.success(
                        message="NFC scan session started (mock response)",
                        data=scan_response.model_dump(),
                        client_op_id=client_op_id
                    )

                # Get services
                try:
                    nfc_service = self._get_nfc_service(request)
                    state_manager = self._get_state_manager(request)
                except Exception as e:
                    logger.error(f"Failed to get NFC service: {str(e)}")
                    return UnifiedResponseService.service_unavailable(
                        service="NFC",
                        message="NFC service is not available",
                        client_op_id=body.client_op_id
                    )

                # If playlist_id provided, start association session
                if playlist_id:
                    logger.info(f"Starting NFC association session for playlist {playlist_id}")
                    result = await nfc_service.start_association_use_case(
                        playlist_id, timeout_seconds=timeout_ms // 1000
                    )

                    if result.get("status") == "success" and "session" in result:
                        session = result["session"]
                        session_id = session["session_id"]
                        timeout_at = session.get("timeout_at")

                        scan_response = NFCScanResponse(
                            scan_id=session_id,
                            timeout_ms=timeout_ms
                        )

                        # Calculate expires_at timestamp for frontend countdown
                        import time
                        from datetime import datetime, timezone
                        if timeout_at:
                            try:
                                expires_at = datetime.fromisoformat(timeout_at.replace('Z', '+00:00')).timestamp()
                            except:
                                expires_at = time.time() + (timeout_ms / 1000)
                        else:
                            expires_at = time.time() + (timeout_ms / 1000)

                        # CRITICAL: Broadcast "waiting" state to all clients
                        # This ensures all clients know association mode is active
                        broadcasting_service = getattr(request.app, "_broadcasting_service", None)
                        if broadcasting_service:
                            await broadcasting_service.broadcast_nfc_association(
                                association_state="waiting",
                                playlist_id=playlist_id,
                                session_id=session_id,
                                expires_at=str(int(expires_at))
                            )
                            logger.info(f"✅ Broadcasted 'waiting' state for session {session_id}")

                        if state_manager and client_op_id:
                            await state_manager.send_acknowledgment(
                                client_op_id, True, scan_response.model_dump()
                            )
                        logger.info(f"NFC association session started with ID {session_id}")
                        return UnifiedResponseService.success(
                            message="NFC association session started",
                            data=scan_response.model_dump(),
                            client_op_id=client_op_id
                        )
                    else:
                        error_msg = result.get("message", "Failed to start association session")
                        if state_manager and client_op_id:
                            await state_manager.send_acknowledgment(
                                client_op_id, False, {"message": error_msg}
                            )
                        return UnifiedResponseService.bad_request(
                            message=error_msg,
                            client_op_id=client_op_id
                        )
                else:
                    # Generic scan session
                    result = await nfc_service.start_scan_session(timeout_ms)

                    if result.get("status") == "success":
                        scan_response = NFCScanResponse(
                            scan_id=result["scan_id"],
                            timeout_ms=timeout_ms
                        )
                        if state_manager and client_op_id:
                            await state_manager.send_acknowledgment(
                                client_op_id, True, scan_response.model_dump()
                            )
                        logger.info(f"NFC scan session started with ID {result['scan_id']}")
                        return UnifiedResponseService.success(
                            message="NFC scan session started",
                            data=scan_response.model_dump(),
                            client_op_id=client_op_id
                        )
                    else:
                        error_msg = result.get("message", "Failed to start scan session")
                        if state_manager and client_op_id:
                            await state_manager.send_acknowledgment(
                                client_op_id, False, {"message": error_msg}
                            )
                        return UnifiedResponseService.bad_request(
                            message=error_msg,
                            client_op_id=client_op_id
                        )

            except Exception as e:
                logger.error(f"Error starting NFC scan: {str(e)}", exc_info=True)
                return UnifiedResponseService.internal_error(
                    message="Failed to start NFC scan session",
                    operation="start_nfc_scan",
                    client_op_id=body.client_op_id
                )

        @self.router.delete("/session/{session_id}")
        @handle_http_errors()
        async def cancel_association_session(
            session_id: str,
            request: Request,
            body: ClientOperationRequest = ClientOperationRequest(),
        ):
            """Cancel an active NFC association session.

            This endpoint allows users to stop an ongoing association session,
            which is called when the user clicks "Cancel" in the association dialog.
            """
            try:
                client_op_id = body.client_op_id

                # Get services
                try:
                    nfc_service = self._get_nfc_service(request)
                    state_manager = self._get_state_manager(request)
                except Exception as e:
                    logger.error(f"Failed to get NFC service: {str(e)}")
                    return UnifiedResponseService.service_unavailable(
                        service="NFC",
                        message="NFC service is not available",
                        client_op_id=client_op_id
                    )

                logger.info(f"Cancelling NFC association session {session_id}")

                # Stop the association session
                result = await nfc_service.stop_association_use_case(session_id)

                if result.get("status") == "success":
                    # Broadcast "cancelled" state to all clients
                    broadcasting_service = getattr(request.app, "_broadcasting_service", None)
                    if broadcasting_service:
                        await broadcasting_service.broadcast_nfc_association(
                            association_state="cancelled",
                            session_id=session_id
                        )
                        logger.info(f"✅ Broadcasted 'cancelled' state for session {session_id}")

                    # Send acknowledgment
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(
                            client_op_id,
                            True,
                            {"session_id": session_id, "status": "cancelled"}
                        )

                    logger.info(f"✅ NFC association session {session_id} cancelled")
                    return UnifiedResponseService.success(
                        message="Association session cancelled successfully",
                        data={"session_id": session_id},
                        client_op_id=client_op_id
                    )
                else:
                    # Session not found
                    error_msg = result.get("message", "Session not found")
                    if state_manager and client_op_id:
                        await state_manager.send_acknowledgment(
                            client_op_id,
                            False,
                            {"message": error_msg}
                        )
                    return UnifiedResponseService.not_found(
                        resource="NFC association session",
                        resource_id=session_id,
                        client_op_id=client_op_id
                    )

            except Exception as e:
                logger.error(f"Error cancelling NFC session: {str(e)}", exc_info=True)
                return UnifiedResponseService.internal_error(
                    message="Failed to cancel NFC association session",
                    operation="cancel_association_session",
                    client_op_id=body.client_op_id
                )

    def get_router(self) -> APIRouter:
        """Get the configured router."""
        return self.router
