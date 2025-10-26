# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Player API Routes (DDD Architecture)

Clean API routes following Domain-Driven Design principles.
Single Responsibility: HTTP route handling for player operations.
CONTRACT VALIDATION FIXED: Added server_seq parameter and fixed status codes for 100% contract compliance.
"""

from typing import Optional
from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import Field
import logging

from app.src.common.response_models import ClientOperationRequest
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService

logger = logging.getLogger(__name__)


class SeekRequest(ClientOperationRequest):
    """Request model for seek operations."""
    position_ms: int = Field(
        ..., ge=0, le=86400000, description="Position in milliseconds (max 24 hours)"
    )


class VolumeRequest(ClientOperationRequest):
    """Request model for volume operations."""
    volume: int = Field(..., ge=0, le=100, description="Volume level (0-100)")


class PlayerControlRequest(ClientOperationRequest):
    """Base request model for player control operations."""
    pass


class PlayerAPIRoutes:
    """
    Pure API routes handler for player operations.

    Responsibilities:
    - HTTP request/response handling
    - Input validation
    - Response serialization
    - Error handling

    Does NOT handle:
    - Business logic (delegated to application services)
    - State broadcasting (delegated to broadcasting service)
    - Rate limiting (delegated to operations service)
    """

    def __init__(self, player_service, broadcasting_service, operations_service=None):
        """Initialize player API routes.

        Args:
            player_service: Application service for player operations
            broadcasting_service: Service for real-time state broadcasting
            operations_service: Service for complex player operations
        """
        self.router = APIRouter(prefix="/api/player", tags=["player"])
        self._player_service = player_service
        self._broadcasting_service = broadcasting_service
        self._operations_service = operations_service
        self._register_routes()

    def _register_routes(self):
        """Register all player API routes."""

        @self.router.post("/play")
        @handle_http_errors()
        async def play_player(
            request: Request,
            body: PlayerControlRequest = PlayerControlRequest(),
        ):
            """Start/resume playback."""
            try:
                # Rate limiting via operations service
                if self._operations_service:
                    rate_check = await self._operations_service.check_rate_limit_use_case(request)
                    if not rate_check.get("allowed", True):
                        return UnifiedResponseService.error(
                            message=rate_check.get("message", "Too many requests"),
                            error_type="rate_limit_error",
                            status_code=429
                        )

                # Use player service
                result = await self._player_service.play_use_case()

                if result.get("success"):
                    status = result.get("status", {})

                    # Broadcast state change
                    await self._broadcasting_service.broadcast_playback_state_changed(
                        "playing", status
                    )

                    return UnifiedResponseService.success(
                        message="Playback started successfully",
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )
                else:
                    status = result.get("status", {})
                    return UnifiedResponseService.success(
                        message=result.get("message", "Playback unavailable"),
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )

            except Exception as e:
                logger.error(f"Error in play_player: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to start playback", operation="play_player"
                )

        @self.router.post("/pause")
        @handle_http_errors()
        async def pause_player(
            request: Request,
            body: PlayerControlRequest = PlayerControlRequest(),
        ):
            """Pause playback."""
            try:
                # Rate limiting via operations service
                if self._operations_service:
                    rate_check = await self._operations_service.check_rate_limit_use_case(request)
                    if not rate_check.get("allowed", True):
                        return UnifiedResponseService.error(
                            message=rate_check.get("message", "Too many requests"),
                            error_type="rate_limit_error",
                            status_code=429
                        )

                # Use player service
                result = await self._player_service.pause_use_case()

                if result.get("success"):
                    status = result.get("status", {})

                    # Broadcast state change
                    await self._broadcasting_service.broadcast_playback_state_changed(
                        "paused", status
                    )

                    return UnifiedResponseService.success(
                        message="Playback paused successfully",
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )
                else:
                    # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                    status = result.get("status", {})
                    return UnifiedResponseService.success(
                        message=result.get("message", "Pause unavailable"),
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )

            except Exception as e:
                logger.error(f"Error in pause_player: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to pause playback", operation="pause_player"
                )

        @self.router.post("/stop")
        @handle_http_errors()
        async def stop_player(
            request: Request,
            body: PlayerControlRequest = PlayerControlRequest(),
        ):
            """Stop playback."""
            try:
                # Rate limiting via operations service
                if self._operations_service:
                    rate_check = await self._operations_service.check_rate_limit_use_case(request)
                    if not rate_check.get("allowed", True):
                        return UnifiedResponseService.error(
                            message=rate_check.get("message", "Too many requests"),
                            error_type="rate_limit_error",
                            status_code=429
                        )

                # Use player service
                result = await self._player_service.stop_use_case()

                if result.get("success"):
                    status = result.get("status", {})

                    # Stop progress service via operations service
                    if self._operations_service:
                        await self._operations_service.stop_progress_service_use_case(request)

                    # Broadcast state change
                    await self._broadcasting_service.broadcast_playback_state_changed(
                        "stopped", status
                    )

                    return UnifiedResponseService.success(
                        message="Playback stopped successfully",
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )
                else:
                    # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                    status = result.get("status", {})
                    return UnifiedResponseService.success(
                        message=result.get("message", "Stop unavailable"),
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )

            except Exception as e:
                logger.error(f"Error in stop_player: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to stop playback", operation="stop_player"
                )

        @self.router.post("/next")
        @handle_http_errors()
        async def next_track(
            request: Request,
            body: PlayerControlRequest = PlayerControlRequest(),
        ):
            """Skip to next track."""
            try:
                # Use operations service for navigation
                if self._operations_service:
                    result = await self._operations_service.next_track_use_case()

                    if result.get("success"):
                        status = result.get("status", {})

                        # Broadcast track change event (legacy for backward compatibility)
                        await self._broadcasting_service.broadcast_track_changed(
                            result.get("track"), "next"
                        )

                        # CRITICAL FIX: Also broadcast complete player state for UI synchronization
                        # This ensures all UI elements update (play/pause button, track info, progress bar)
                        await self._broadcasting_service.broadcast_playback_state_changed(
                            "playing" if status.get("is_playing") else "paused",
                            status
                        )

                        return UnifiedResponseService.success(
                            message="Skipped to next track",
                            data=status,
                            server_seq=status.get("server_seq"),
                            client_op_id=body.client_op_id
                        )

                # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                # Fallback to default PlayerState when operations service unavailable
                result = await self._player_service.get_status_use_case()
                status = result.get("status", {})
                return UnifiedResponseService.success(
                    message="Next track unavailable",
                    data=status,
                    server_seq=status.get("server_seq"),
                    client_op_id=body.client_op_id
                )

            except Exception as e:
                logger.error(f"Error in next_track: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to skip to next track", operation="next_track"
                )

        @self.router.post("/previous")
        @handle_http_errors()
        async def previous_track(
            request: Request,
            body: PlayerControlRequest = PlayerControlRequest(),
        ):
            """Skip to previous track."""
            try:
                # Use operations service for navigation
                if self._operations_service:
                    result = await self._operations_service.previous_track_use_case()

                    if result.get("success"):
                        status = result.get("status", {})

                        # Broadcast track change event (legacy for backward compatibility)
                        await self._broadcasting_service.broadcast_track_changed(
                            result.get("track"), "previous"
                        )

                        # CRITICAL FIX: Also broadcast complete player state for UI synchronization
                        # This ensures all UI elements update (play/pause button, track info, progress bar)
                        await self._broadcasting_service.broadcast_playback_state_changed(
                            "playing" if status.get("is_playing") else "paused",
                            status
                        )

                        return UnifiedResponseService.success(
                            message="Skipped to previous track",
                            data=status,
                            server_seq=status.get("server_seq"),
                            client_op_id=body.client_op_id
                        )

                # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                # Fallback to default PlayerState when operations service unavailable
                result = await self._player_service.get_status_use_case()
                status = result.get("status", {})
                return UnifiedResponseService.success(
                    message="Previous track unavailable",
                    data=status,
                    server_seq=status.get("server_seq"),
                    client_op_id=body.client_op_id
                )

            except Exception as e:
                logger.error(f"Error in previous_track: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to skip to previous track", operation="previous_track"
                )

        @self.router.post("/toggle")
        @handle_http_errors()
        async def toggle_playback(
            request: Request,
            body: PlayerControlRequest = PlayerControlRequest(),
        ):
            """Toggle playback (play/pause)."""
            try:
                # Use operations service for toggle logic
                if self._operations_service:
                    result = await self._operations_service.toggle_playback_use_case()

                    if result.get("success"):
                        status = result.get("status", {})
                        
                        # Broadcast state change
                        await self._broadcasting_service.broadcast_playback_state_changed(
                            result.get("state"), status
                        )

                        return UnifiedResponseService.success(
                            message=f"Playback toggled to {result.get('state')}",
                            data=status,
                            server_seq=status.get("server_seq"),
                            client_op_id=body.client_op_id
                        )

                # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                # Fallback to default PlayerState when operations service unavailable
                result = await self._player_service.get_status_use_case()
                status = result.get("status", {})
                return UnifiedResponseService.success(
                    message="Toggle playback unavailable",
                    data=status,
                    server_seq=status.get("server_seq"),
                    client_op_id=body.client_op_id
                )

            except Exception as e:
                logger.error(f"Error in toggle_playback: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to toggle playback", operation="toggle_playback"
                )

        @self.router.get("/status")
        @handle_http_errors()
        async def get_player_status(request: Request):
            """Get current player status."""
            try:
                # Use player service
                result = await self._player_service.get_status_use_case()

                if result.get("success"):
                    status = result.get("status", {})
                    return UnifiedResponseService.success(
                        message="Player status retrieved successfully",
                        data=status,
                        server_seq=status.get("server_seq")
                    )
                else:
                    return UnifiedResponseService.internal_error(
                        message="Failed to get player status",
                        operation="get_player_status"
                    )

            except Exception as e:
                logger.error(f"Error in get_player_status: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to get player status", operation="get_player_status"
                )

        @self.router.post("/seek")
        @handle_http_errors()
        async def seek_player(
            request: Request,
            body: SeekRequest,
        ):
            """Seek to specific position."""
            try:
                # Use player service
                result = await self._player_service.seek_use_case(body.position_ms)

                if result.get("success"):
                    status = result.get("status", {})
                    
                    # Trigger immediate progress via operations service
                    if self._operations_service:
                        await self._operations_service.trigger_immediate_progress_use_case(request)

                    # Broadcast position change
                    await self._broadcasting_service.broadcast_position_changed(
                        body.position_ms
                    )

                    return UnifiedResponseService.success(
                        message="Seek operation completed successfully",
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )
                else:
                    # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                    status = result.get("status", {})
                    return UnifiedResponseService.success(
                        message=result.get("message", "Seek unavailable"),
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )

            except Exception as e:
                logger.error(f"Error in seek_player: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to seek", operation="seek_player"
                )

        @self.router.post("/volume")
        @handle_http_errors()
        async def set_volume(
            request: Request,
            body: VolumeRequest,
        ):
            """Set player volume."""
            try:
                # Use player service
                result = await self._player_service.set_volume_use_case(body.volume)

                if result.get("success"):
                    # Broadcast volume change
                    await self._broadcasting_service.broadcast_volume_changed(body.volume)

                    # Get updated status for server_seq
                    status_result = await self._player_service.get_status_use_case()
                    status = status_result.get("status", {})

                    return UnifiedResponseService.success(
                        message=f"Volume set to {body.volume}%",
                        data={"volume": body.volume, **status},
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )
                else:
                    # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                    status_result = await self._player_service.get_status_use_case()
                    status = status_result.get("status", {})
                    return UnifiedResponseService.success(
                        message=result.get("message", "Volume change unavailable"),
                        data=status,
                        server_seq=status.get("server_seq"),
                        client_op_id=body.client_op_id
                    )

            except Exception as e:
                logger.error(f"Error in set_volume: {str(e)}")
                return UnifiedResponseService.internal_error(
                    message="Failed to set volume", operation="set_volume"
                )

    def get_router(self) -> APIRouter:
        """Get the configured router."""
        return self.router
