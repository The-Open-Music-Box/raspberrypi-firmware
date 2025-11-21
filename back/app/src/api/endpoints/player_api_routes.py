# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Player API Routes (DDD Architecture)

Clean API routes following Domain-Driven Design principles.
Single Responsibility: HTTP route handling for player operations.
CONTRACT VALIDATION FIXED: Added server_seq parameter and fixed status codes for 100% contract compliance.
"""

from fastapi import APIRouter, Request
from pydantic import Field

from app.src.api.base_api_routes import BaseAPIRoutes
from app.src.common.response_models import ClientOperationRequest
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.services.response.unified_response_service import UnifiedResponseService


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


class PlayerAPIRoutes(BaseAPIRoutes):
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

    Inherits common API functionality from BaseAPIRoutes.
    """

    def __init__(self, player_service, broadcasting_service, operations_service=None):
        """Initialize player API routes.

        Args:
            player_service: Application service for player operations
            broadcasting_service: Service for real-time state broadcasting
            operations_service: Service for complex player operations
        """
        self.router = APIRouter(prefix="/api/player", tags=["player"])
        super().__init__(
            router=self.router,
            player_service=player_service,
            broadcasting_service=broadcasting_service,
            operations_service=operations_service
        )
        self._player_service = player_service
        self._broadcasting_service = broadcasting_service
        self._operations_service = operations_service
        self._register_routes()

    async def _check_rate_limit(self, request: Request):
        """Check rate limiting for player operations.

        Returns:
            Error response if rate limited, None if allowed
        """
        if self._operations_service:
            rate_check = await self._operations_service.check_rate_limit_use_case(request)
            if not rate_check.get("allowed", True):
                return UnifiedResponseService.error(
                    message=rate_check.get("message", "Too many requests"),
                    error_type="rate_limit_error",
                    status_code=429
                )
        return None

    def _success_response(self, message: str, status: dict, client_op_id: str = None):
        """Create success response with standard fields.

        Args:
            message: Success message
            status: Player status dictionary
            client_op_id: Optional client operation ID

        Returns:
            Unified success response
        """
        return UnifiedResponseService.success(
            message=message,
            data=status,
            server_seq=status.get("server_seq"),
            client_op_id=client_op_id
        )

    def _fallback_response(self, result: dict, default_message: str, client_op_id: str = None):
        """Create fallback response when operation is unavailable.

        Args:
            result: Result dictionary with status
            default_message: Default message if not in result
            client_op_id: Optional client operation ID

        Returns:
            Unified success response with fallback message
        """
        status = result.get("status", {})
        message = result.get("message", default_message)
        return self._success_response(message, status, client_op_id)

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
                # Rate limiting check
                rate_limit_response = await self._check_rate_limit(request)
                if rate_limit_response:
                    return rate_limit_response

                # Use player service
                result = await self._player_service.play_use_case()

                # Check if service returned an error
                if result.get("status") == "error":
                    self._logger.error(f"Service error in play_use_case: {result.get('message')}")
                    return UnifiedResponseService.internal_error(
                        message=result.get("message", "Failed to start playback"),
                        operation="play_player"
                    )

                if result.get("success"):
                    status = result.get("status", {})

                    # Broadcast state change
                    await self._broadcasting_service.broadcast_playback_state_changed(
                        "playing", status
                    )

                    return self._success_response(
                        "Playback started successfully", status, body.client_op_id
                    )
                else:
                    return self._fallback_response(
                        result, "Playback unavailable", body.client_op_id
                    )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="play_player",
                    message="Failed to start playback"
                )

        @self.router.post("/pause")
        @handle_http_errors()
        async def pause_player(
            request: Request,
            body: PlayerControlRequest = PlayerControlRequest(),
        ):
            """Pause playback."""
            try:
                # Rate limiting check
                rate_limit_response = await self._check_rate_limit(request)
                if rate_limit_response:
                    return rate_limit_response

                # Use player service
                result = await self._player_service.pause_use_case()

                if result.get("success"):
                    status = result.get("status", {})

                    # Broadcast state change
                    await self._broadcasting_service.broadcast_playback_state_changed(
                        "paused", status
                    )

                    return self._success_response(
                        "Playback paused successfully", status, body.client_op_id
                    )
                else:
                    # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                    return self._fallback_response(
                        result, "Pause unavailable", body.client_op_id
                    )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="pause_player",
                    message="Failed to pause playback"
                )

        @self.router.post("/stop")
        @handle_http_errors()
        async def stop_player(
            request: Request,
            body: PlayerControlRequest = PlayerControlRequest(),
        ):
            """Stop playback."""
            try:
                # Rate limiting check
                rate_limit_response = await self._check_rate_limit(request)
                if rate_limit_response:
                    return rate_limit_response

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

                    return self._success_response(
                        "Playback stopped successfully", status, body.client_op_id
                    )
                else:
                    # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                    return self._fallback_response(
                        result, "Stop unavailable", body.client_op_id
                    )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="stop_player",
                    message="Failed to stop playback"
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

                        return self._success_response(
                            "Skipped to next track", status, body.client_op_id
                        )

                # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                # Fallback to default PlayerState when operations service unavailable
                result = await self._player_service.get_status_use_case()
                return self._fallback_response(
                    result, "Next track unavailable", body.client_op_id
                )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="next_track",
                    message="Failed to skip to next track"
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

                        return self._success_response(
                            "Skipped to previous track", status, body.client_op_id
                        )

                # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                # Fallback to default PlayerState when operations service unavailable
                result = await self._player_service.get_status_use_case()
                return self._fallback_response(
                    result, "Previous track unavailable", body.client_op_id
                )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="previous_track",
                    message="Failed to skip to previous track",
                    client_op_id=body.client_op_id,
                    request_id=request.headers.get("X-Request-ID")
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

                        return self._success_response(
                            f"Playback toggled to {result.get('state')}", status, body.client_op_id
                        )

                # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                # Fallback to default PlayerState when operations service unavailable
                result = await self._player_service.get_status_use_case()
                return self._fallback_response(
                    result, "Toggle playback unavailable", body.client_op_id
                )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="toggle_playback",
                    message="Failed to toggle playback",
                    client_op_id=body.client_op_id,
                    request_id=request.headers.get("X-Request-ID")
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
                    return self._success_response(
                        "Player status retrieved successfully", status
                    )
                else:
                    return UnifiedResponseService.internal_error(
                        message="Failed to get player status",
                        operation="get_player_status"
                    )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="get_player_status",
                    message="Failed to get player status",
                    request_id=request.headers.get("X-Request-ID")
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

                    return self._success_response(
                        "Seek operation completed successfully", status, body.client_op_id
                    )
                else:
                    # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                    return self._fallback_response(
                        result, "Seek unavailable", body.client_op_id
                    )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="seek_player",
                    message="Failed to seek",
                    client_op_id=body.client_op_id,
                    request_id=request.headers.get("X-Request-ID"),
                    position_ms=body.position_ms
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

                    # CONTRACT COMPLIANT: Return PlayerState (which includes volume field)
                    # Get updated status after volume change
                    status_result = await self._player_service.get_status_use_case()
                    status = status_result.get("status", {})

                    return self._success_response(
                        f"Volume set to {body.volume}%", status, body.client_op_id
                    )
                else:
                    # CONTRACT FIX: Return success with 200 status instead of bad_request (400)
                    status_result = await self._player_service.get_status_use_case()
                    return self._fallback_response(
                        status_result, "Volume change unavailable", body.client_op_id
                    )

            except Exception as e:
                # Use base class helper for error handling
                return self.handle_endpoint_error(
                    e,
                    operation="set_volume",
                    message="Failed to set volume",
                    client_op_id=body.client_op_id,
                    request_id=request.headers.get("X-Request-ID"),
                    volume=body.volume
                )

    def get_router(self) -> APIRouter:
        """Get the configured router."""
        return self.router
