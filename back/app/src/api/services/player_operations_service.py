# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Player Operations Service (DDD Architecture)

Single Responsibility: Complex player workflow orchestration.
"""

import time
from typing import Dict, Any
from collections import defaultdict
from fastapi import Request
import logging

from app.src.services.error.unified_error_decorator import handle_service_errors

logger = logging.getLogger(__name__)

# Rate limiting configuration
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 30  # max requests per window


class PlayerOperationsService:
    """
    Service responsible for complex player workflow orchestration.

    Single Responsibility: Complex player operations beyond basic playback.

    Responsibilities:
    - Rate limiting for player endpoints
    - Track navigation workflow coordination
    - Progress service management
    - Session management
    - Complex playback state logic

    Does NOT handle:
    - HTTP request/response (delegated to API routes)
    - Simple playback operations (delegated to player service)
    - State broadcasting (delegated to broadcasting service)
    """

    def __init__(self, player_service):
        """Initialize player operations service.

        Args:
            player_service: Application service for basic player operations
        """
        self._player_service = player_service
        self._rate_limit_store = defaultdict(lambda: {"count": 0, "window_start": 0})

    @handle_service_errors("player_operations")
    async def check_rate_limit_use_case(self, request: Request) -> Dict[str, Any]:
        """Check rate limiting for player operations.

        Args:
            request: HTTP request for client identification

        Returns:
            Dict with 'allowed' boolean and optional 'message'
        """
        try:
            client_id = self._get_client_id(request)

            current_time = time.time()
            client_data = self._rate_limit_store[client_id]

            # Reset window if expired
            if current_time - client_data["window_start"] > RATE_LIMIT_WINDOW:
                client_data["count"] = 0
                client_data["window_start"] = current_time

            # Check limit
            if client_data["count"] >= RATE_LIMIT_MAX_REQUESTS:
                return {
                    "allowed": False,
                    "message": "Too many player control requests. Please slow down."
                }

            # Increment count
            client_data["count"] += 1

            return {"allowed": True}

        except Exception as e:
            logger.error(f"Error in rate limiting: {str(e)}")
            # Allow request on error to avoid blocking users
            return {"allowed": True}

    @handle_service_errors("player_operations")
    async def next_track_use_case(self) -> Dict[str, Any]:
        """Navigate to next track.

        Returns:
            Dict with operation result
        """
        try:
            # Use player service for navigation
            result = await self._player_service.next_track_use_case()

            if result.get("success"):
                logger.info("✅ Successfully navigated to next track")
                return {
                    "success": True,
                    "track": result.get("track"),
                    "status": result.get("status", {})
                }
            else:
                logger.warning(f"⚠️ Failed to navigate to next track: {result.get('message')}")
                return {
                    "success": False,
                    "message": result.get("message", "Failed to navigate to next track")
                }

        except Exception as e:
            logger.error(f"Error in next_track_use_case: {str(e)}")
            return {
                "success": False,
                "message": "Internal error during track navigation"
            }

    @handle_service_errors("player_operations")
    async def previous_track_use_case(self) -> Dict[str, Any]:
        """Navigate to previous track.

        Returns:
            Dict with operation result
        """
        try:
            # Use player service for navigation
            result = await self._player_service.previous_track_use_case()

            if result.get("success"):
                logger.info("✅ Successfully navigated to previous track")
                return {
                    "success": True,
                    "track": result.get("track"),
                    "status": result.get("status", {})
                }
            else:
                logger.warning(f"⚠️ Failed to navigate to previous track: {result.get('message')}")
                return {
                    "success": False,
                    "message": result.get("message", "Failed to navigate to previous track")
                }

        except Exception as e:
            logger.error(f"Error in previous_track_use_case: {str(e)}")
            return {
                "success": False,
                "message": "Internal error during track navigation"
            }

    @handle_service_errors("player_operations")
    async def toggle_playback_use_case(self) -> Dict[str, Any]:
        """Toggle playback state (play/pause).

        Returns:
            Dict with operation result and new state
        """
        try:
            # Get current status first
            status_result = await self._player_service.get_status_use_case()

            if not status_result.get("success"):
                return {
                    "success": False,
                    "message": "Unable to determine current playback state"
                }

            # Get current playback flags (is_playing, is_paused)
            current_status = status_result.get("status", {})
            is_playing = current_status.get("is_playing", False)
            is_paused = current_status.get("is_paused", False)

            # Toggle based on current state
            if is_playing and not is_paused:
                # Currently playing → pause it
                result = await self._player_service.pause_use_case()
                new_state = "paused"
            elif is_paused:
                # Currently paused → resume playback
                # Use play_use_case which should handle resume when paused
                result = await self._player_service.play_use_case()
                new_state = "playing"
            else:
                # stopped or no track - use play to start from beginning
                result = await self._player_service.play_use_case()
                new_state = "playing"

            if result.get("success"):
                logger.info(f"✅ Successfully toggled playback to {new_state}")
                return {
                    "success": True,
                    "state": new_state,
                    "status": result.get("status", {})
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", f"Failed to toggle to {new_state}")
                }

        except Exception as e:
            logger.error(f"Error in toggle_playback_use_case: {str(e)}")
            return {
                "success": False,
                "message": "Internal error during playback toggle"
            }

    @handle_service_errors("player_operations")
    async def stop_progress_service_use_case(self, request: Request) -> Dict[str, Any]:
        """Stop progress service when playback stops.

        Args:
            request: HTTP request to access app state

        Returns:
            Dict with operation result
        """
        try:
            # Access progress service through app state
            playlist_routes_ddd = getattr(request.app, "playlist_routes_ddd", None)

            if playlist_routes_ddd and hasattr(playlist_routes_ddd, "progress_service"):
                await playlist_routes_ddd.progress_service.stop()
                logger.info("✅ Progress service stopped")
                return {"success": True}
            else:
                logger.warning("⚠️ Progress service not found")
                return {"success": False, "message": "Progress service not found"}

        except Exception as e:
            logger.error(f"Error stopping progress service: {str(e)}")
            return {"success": False, "message": "Failed to stop progress service"}

    @handle_service_errors("player_operations")
    async def trigger_immediate_progress_use_case(self, request: Request) -> Dict[str, Any]:
        """Trigger immediate progress update for UI responsiveness.

        Args:
            request: HTTP request to access app state

        Returns:
            Dict with operation result
        """
        try:
            # Access progress service through app state
            playlist_routes_ddd = getattr(request.app, "playlist_routes_ddd", None)

            if playlist_routes_ddd and hasattr(playlist_routes_ddd, "progress_service"):
                logger.debug("Triggering immediate progress emission for UI responsiveness")
                await playlist_routes_ddd.progress_service.emit_immediate_position()
                return {"success": True}
            else:
                logger.warning("⚠️ Progress service not found for immediate trigger")
                return {"success": False, "message": "Progress service not found"}

        except Exception as e:
            logger.error(f"Error triggering immediate progress: {str(e)}")
            return {"success": False, "message": "Failed to trigger progress update"}

    def _get_client_id(self, request: Request) -> str:
        """Extract client identifier from request.

        Args:
            request: HTTP request

        Returns:
            Client identifier string
        """
        # Try different client identification methods
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        # Combine IP and user agent for unique client ID
        return f"{client_ip}:{hash(user_agent) % 10000}"

    def _validate_client_op_id(self, client_op_id: str) -> str:
        """Validate and format client operation ID.

        Args:
            client_op_id: Client-provided operation ID

        Returns:
            Validated operation ID
        """
        if not client_op_id or not isinstance(client_op_id, str):
            return f"auto-{int(time.time() * 1000)}"

        # Sanitize and truncate if needed
        sanitized = "".join(c for c in client_op_id if c.isalnum() or c in "-_")
        return sanitized[:50] if sanitized else f"auto-{int(time.time() * 1000)}"
