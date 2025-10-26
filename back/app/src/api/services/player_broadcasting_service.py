# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Player Broadcasting Service (DDD Architecture)

Single Responsibility: Real-time state broadcasting for player operations.
"""

from typing import Dict, Any, Optional
import logging
from app.src.domain.audio.engine.state_manager import StateManager
from app.src.common.socket_events import StateEventType
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = logging.getLogger(__name__)


class PlayerBroadcastingService:
    """
    Service responsible for broadcasting player state changes.

    Single Responsibility: WebSocket state broadcasting for player events.

    Responsibilities:
    - Broadcast playback state changes (play/pause/stop)
    - Broadcast track navigation events
    - Broadcast volume changes
    - Broadcast position/seek updates
    - Broadcast player status updates

    Does NOT handle:
    - HTTP request/response (delegated to API routes)
    - Business logic (delegated to application services)
    - Data persistence (delegated to repositories)
    """

    def __init__(self, state_manager: StateManager):
        """Initialize player broadcasting service.

        Args:
            state_manager: StateManager instance for WebSocket broadcasting
        """
        self._state_manager = state_manager

    @handle_service_errors("player_broadcasting")
    async def broadcast_playback_state_changed(self, state: str, player_status: Dict[str, Any]):
        """Broadcast playback state change event.

        Args:
            state: New playback state (playing/paused/stopped)
            player_status: Current player status data
        """
        try:
            # Frontend expects PlayerState fields at the top level, not nested
            event_data = {
                **player_status,  # Spread player status fields at top level
                "operation": "playback_state_change"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.PLAYER_STATE,
                event_data
            )

            logger.info(f"✅ Broadcasted playback state change: {state}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast playback state change: {str(e)}")

    @handle_service_errors("player_broadcasting")
    async def broadcast_track_changed(self, track_data: Optional[Dict[str, Any]], direction: str):
        """Broadcast track navigation event.

        Args:
            track_data: Current track information
            direction: Navigation direction (next/previous)
        """
        try:
            event_data = {
                "track": track_data,
                "direction": direction,
                "operation": "track_change"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.TRACK_CHANGED,
                event_data
            )

            track_title = track_data.get("title", "Unknown") if track_data else "No track"
            logger.info(f"✅ Broadcasted track change: {direction} -> {track_title}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast track change: {str(e)}")

    @handle_service_errors("player_broadcasting")
    async def broadcast_volume_changed(self, volume: int):
        """Broadcast volume change event.

        Args:
            volume: New volume level (0-100)
        """
        try:
            event_data = {
                "volume": volume,
                "operation": "volume_change"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.VOLUME_CHANGED,
                event_data
            )

            logger.info(f"✅ Broadcasted volume change: {volume}%")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast volume change: {str(e)}")

    @handle_service_errors("player_broadcasting")
    async def broadcast_position_changed(self, position_ms: int):
        """Broadcast position/seek event.

        Args:
            position_ms: New position in milliseconds
        """
        try:
            event_data = {
                "position_ms": position_ms,
                "operation": "position_change"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.POSITION_CHANGED,
                event_data
            )

            logger.debug(f"✅ Broadcasted position change: {position_ms}ms")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast position change: {str(e)}")

    @handle_service_errors("player_broadcasting")
    async def broadcast_player_status(self, status: Dict[str, Any]):
        """Broadcast complete player status update.

        Args:
            status: Complete player status information
        """
        try:
            event_data = {
                "status": status,
                "operation": "status_update"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.PLAYER_STATE,
                event_data
            )

            logger.debug("✅ Broadcasted player status update")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast player status: {str(e)}")

    @handle_service_errors("player_broadcasting")
    async def broadcast_progress_update(self, progress_data: Dict[str, Any]):
        """Broadcast progress tracking update.

        Args:
            progress_data: Progress information (position, duration, etc.)
        """
        try:
            event_data = {
                "progress": progress_data,
                "operation": "progress_update"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.PROGRESS_UPDATE,
                event_data
            )

            logger.debug("✅ Broadcasted progress update")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast progress update: {str(e)}")

    @handle_service_errors("player_broadcasting")
    async def broadcast_player_error(self, error_message: str, error_context: Optional[Dict[str, Any]] = None):
        """Broadcast player error event.

        Args:
            error_message: Error description
            error_context: Additional error context
        """
        try:
            event_data = {
                "error": error_message,
                "context": error_context or {},
                "operation": "player_error"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.PLAYER_ERROR,
                event_data
            )

            logger.info(f"✅ Broadcasted player error: {error_message}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast player error: {str(e)}")

    def get_global_sequence(self) -> int:
        """Get the current global sequence number for state synchronization.

        Returns:
            Current global sequence number
        """
        return self._state_manager.get_global_sequence()
