# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified PlayerState builder service for TheOpenMusicBox.

This service provides a single, consistent way to build PlayerState objects
across all endpoints, eliminating the multiple patterns found in the codebase.
Refactored to use standardized data models and error handling.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from ..common.data_models import PlayerStateModel, TrackModel, PlaybackState
from ..monitoring import get_error_handler
from app.src.infrastructure.error_handling.unified_error_handler import service_unavailable_error
from app.src.common.socket_events import StateEventType
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = get_logger(__name__)


class PlayerStateService:
    """
    Service responsible for building consistent PlayerState objects.

    This service acts as the single source of truth for PlayerState construction,
    ensuring all endpoints return consistent data structures.
    """

    def __init__(self, audio_controller=None, state_manager=None):
        """Initialize PlayerState service.

        Args:
            audio_controller: Audio controller instance (optional for dependency injection)
            state_manager: State manager instance (optional for dependency injection)
        """
        self.audio_controller = audio_controller
        self.state_manager = state_manager
        self.error_handler = get_error_handler()
        self.std_logger = logging.getLogger("tomb.player_state_service")

    @handle_service_errors("player_state")
    async def build_current_player_state(
        self, audio_controller=None, state_manager=None, include_error_info: bool = False
    ) -> PlayerStateModel:
        """
        Build complete current player state from audio controller.

        Args:
            audio_controller: Audio controller instance (overrides instance var)
            state_manager: State manager for sequence numbers (overrides instance var)
            include_error_info: Whether to include error information in response

        Returns:
            Complete PlayerStateModel object

        Raises:
            StandardHTTPException: If audio controller is unavailable
        """
        controller = audio_controller or self.audio_controller
        manager = state_manager or self.state_manager

        if not controller:
            raise service_unavailable_error(
                "Audio controller", {"method": "build_current_player_state"}
            )

        # Get all data sources
        status = await controller.get_playback_status()
        playlist_info = controller.get_current_playlist_info()
        # Parse playback state
        raw_state = status.get("state", "stopped")
        playback_state = self._parse_playback_state(raw_state)
        is_playing = playback_state == PlaybackState.PLAYING
        # Get playlist information (with fallback to status data)
        active_playlist_id = (
            playlist_info.get("playlist_id") if playlist_info else status.get("playlist_id")
        )
        # Try multiple possible keys for playlist title
        active_playlist_title = None
        if playlist_info:
            active_playlist_title = playlist_info.get("playlist_title") or playlist_info.get(
                "title"
            )
        # Enhanced diagnostic: Log playlist info to debug missing title
        if active_playlist_id and not active_playlist_title:
            logger.warning(f"⚠️ Missing playlist title for ID {active_playlist_id}. playlist_info: {playlist_info}",
            )
            # Try to get title from status fallback
            if status.get("playlist_title"):
                active_playlist_title = status.get("playlist_title")
                logger.info(f"✅ Recovered playlist title from status: {active_playlist_title}",
                )
        # Get track information
        active_track_data = playlist_info.get("current_track") if playlist_info else None
        active_track = self._build_track_model(active_track_data) if active_track_data else None
        active_track_id = active_track.id if active_track else None
        # Get timing information - prioritize _ms fields for consistency
        position_ms = status.get("position_ms") or status.get("current_time", 0) or 0
        duration_ms = status.get("duration_ms") or status.get("duration", 0) or 0
        # Convert legacy second values if needed
        if position_ms < 1000 and status.get("current_time", 0) > 1:
            # Assume it's in seconds and convert
            position_ms = int(status.get("current_time", 0) * 1000)
        if duration_ms < 1000 and status.get("duration", 0) > 1:
            # Assume it's in seconds and convert
            duration_ms = int(status.get("duration", 0) * 1000)
        # Get navigation information
        track_index = playlist_info.get("current_track_index", 0) if playlist_info else 0
        track_count = playlist_info.get("track_count", 0) if playlist_info else 0
        can_prev = playlist_info.get("can_prev", False) if playlist_info else False
        can_next = playlist_info.get("can_next", False) if playlist_info else False
        # Get audio information
        volume = controller.get_current_volume() or 100
        muted = getattr(controller, "is_muted", lambda: False)()
        # Get sequence number
        server_seq = manager.get_global_sequence() if manager else 0
        # Build complete state
        player_state = PlayerStateModel(
            is_playing=is_playing,
            state=playback_state,
            active_playlist_id=active_playlist_id,
            active_playlist_title=active_playlist_title,
            active_track_id=active_track_id,
            active_track=active_track,
            position_ms=position_ms,
            duration_ms=duration_ms,
            track_index=track_index,
            track_count=track_count,
            can_prev=can_prev,
            can_next=can_next,
            volume=volume,
            muted=muted,
            server_seq=server_seq,
        )
        logger.debug(f"Built player state - playing={is_playing}, playlist={active_playlist_id}, "
            f"track={active_track_id}, position={position_ms}ms",
        )
        return player_state

    async def build_stopped_player_state(self, state_manager=None) -> PlayerStateModel:
        """
        Build player state for stopped playback.

        Args:
            state_manager: State manager for sequence numbers (overrides instance var)

        Returns:
            PlayerStateModel representing stopped state
        """
        manager = state_manager or self.state_manager
        server_seq = manager.get_global_sequence() if manager else 0

        return PlayerStateModel(
            is_playing=False,
            state=PlaybackState.STOPPED,
            active_playlist_id=None,
            active_playlist_title=None,
            active_track_id=None,
            active_track=None,
            position_ms=0,
            duration_ms=0,
            track_index=0,
            track_count=0,
            can_prev=False,
            can_next=False,
            volume=100,
            muted=False,
            server_seq=server_seq,
        )

    async def build_error_player_state(
        self,
        state_manager=None,
        error_message: str = None,
        preserve_current_info: Optional[Dict[str, Any]] = None,
    ) -> PlayerStateModel:
        """
        Build player state for error conditions.

        Args:
            state_manager: State manager for sequence numbers (overrides instance var)
            error_message: Error message to include
            preserve_current_info: Current player info to preserve if available

        Returns:
            PlayerStateModel representing error state
        """
        manager = state_manager or self.state_manager
        return await self._build_error_player_state(manager, error_message, preserve_current_info)

    @handle_service_errors("player_state")
    async def build_track_progress_state(
        self, audio_controller=None, state_manager=None
    ) -> Dict[str, Any]:
        """
        Build track progress state for progress events.

        Args:
            audio_controller: Audio controller instance (overrides instance var)
            state_manager: State manager for sequence numbers (overrides instance var)

        Returns:
            Track progress data dictionary
        """
        controller = audio_controller or self.audio_controller
        manager = state_manager or self.state_manager

        if not controller:
            return {
                "position_ms": 0,
                "duration_ms": 0,
                "is_playing": False,
                "active_track_id": None,
                "server_seq": manager.get_global_sequence() if manager else 0,
                "timestamp": int(datetime.now().timestamp() * 1000),
            }

        status = await controller.get_playback_status()
        playlist_info = controller.get_current_playlist_info()
        # Get position and duration - prioritize _ms fields for consistency
        position_ms = status.get("position_ms") or status.get("current_time", 0) or 0
        duration_ms = status.get("duration_ms") or status.get("duration", 0) or 0
        # Convert legacy second values if needed
        if position_ms < 1000 and status.get("current_time", 0) > 1:
            position_ms = int(status.get("current_time", 0) * 1000)
        if duration_ms < 1000 and status.get("duration", 0) > 1:
            duration_ms = int(status.get("duration", 0) * 1000)
        raw_state = status.get("state", "stopped")
        is_playing = raw_state == "playing"
        active_track_data = playlist_info.get("current_track") if playlist_info else None
        active_track_id = active_track_data.get("id") if active_track_data else None
        return {
            "position_ms": position_ms,
            "duration_ms": duration_ms,
            "is_playing": is_playing,
            "active_track_id": active_track_id,
            "server_seq": manager.get_global_sequence() if manager else 0,
            "timestamp": int(datetime.now().timestamp() * 1000),
        }

    @handle_service_errors("player_state")
    async def broadcast_playlist_started(
        self,
        playlist_data: Dict[str, Any],
        source: str = "unknown",
        client_op_id: Optional[str] = None,
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Legacy method - broadcast playlist start state to all connected clients.

        Maintained for backwards compatibility during transition period.

        Args:
            playlist_data: Playlist information dictionary
            source: Source of the playlist start ("ui", "nfc", "api", etc.)
            client_op_id: Optional client operation ID for acknowledgment
            extra_context: Optional additional context (e.g., nfc_tag_id)

        Returns:
            Constructed player state dictionary
        """
        # Use new standardized method
        player_state = await self.build_current_player_state()
        player_state_dict = player_state.model_dump()
        # Add legacy fields for compatibility
        player_state_dict["source"] = source
        if extra_context:
            player_state_dict.update(extra_context)
        # Broadcast state using WebSocket
        if self.state_manager:
            await self.state_manager.broadcast_state_change(
                StateEventType.PLAYER_STATE, player_state_dict
            )
            # Send acknowledgment if client operation ID provided
            if client_op_id:
                await self.state_manager.send_acknowledgment(client_op_id, True, player_state_dict)
        logger.info(f"Player state broadcasted: {playlist_data.get('title')} (source: {source})",
        )
        return player_state_dict

    def _parse_playback_state(self, raw_state: str) -> PlaybackState:
        """Convert raw state string to PlaybackState enum."""
        state_mapping = {
            "playing": PlaybackState.PLAYING,
            "paused": PlaybackState.PAUSED,
            "stopped": PlaybackState.STOPPED,
            "loading": PlaybackState.LOADING,
            "error": PlaybackState.ERROR,
        }
        return state_mapping.get(raw_state.lower(), PlaybackState.STOPPED)

    @handle_service_errors("player_state")
    def _build_track_model(self, track_data: Dict[str, Any]) -> Optional[TrackModel]:
        """Build TrackModel from track data dictionary."""
        if not track_data:
            return None

        # Handle duration conversion (seconds to milliseconds)
        duration_seconds = track_data.get("duration", 0)
        if isinstance(duration_seconds, (int, float)):
            duration_ms = int(duration_seconds * 1000)
        else:
            duration_ms = track_data.get("duration_ms", 0)
        # Ensure required fields are not None
        track_id = track_data.get("id") or ""
        track_title = track_data.get("title") or ""
        track_filename = track_data.get("filename") or ""
        track_file_path = track_data.get("file_path") or ""
        return TrackModel(
            id=track_id,
            title=track_title,
            filename=track_filename,
            duration_ms=duration_ms,
            file_path=track_file_path,
            file_hash=track_data.get("file_hash"),
            file_size=track_data.get("file_size"),
            artist=track_data.get("artist"),
            album=track_data.get("album"),
            track_number=track_data.get("track_number"),
            play_count=track_data.get("play_count", 0),
            created_at=track_data.get("created_at", datetime.now()),
            updated_at=track_data.get("updated_at"),
            server_seq=track_data.get("server_seq", 0),
        )

    async def _build_error_player_state(
        self,
        state_manager,
        error_message: Optional[str] = None,
        preserve_current_info: Optional[Dict[str, Any]] = None,
    ) -> PlayerStateModel:
        """Internal method to build error player state."""
        server_seq = state_manager.get_global_sequence() if state_manager else 0

        # Use preserved info if available
        if preserve_current_info:
            active_playlist_id = preserve_current_info.get("playlist_id")
            active_playlist_title = preserve_current_info.get("playlist_title")
            track_count = preserve_current_info.get("track_count", 0)
            volume = preserve_current_info.get("volume", 100)
        else:
            active_playlist_id = None
            active_playlist_title = None
            track_count = 0
            volume = 100

        return PlayerStateModel(
            is_playing=False,
            state=PlaybackState.ERROR if error_message else PlaybackState.STOPPED,
            active_playlist_id=active_playlist_id,
            active_playlist_title=active_playlist_title,
            active_track_id=None,
            active_track=None,
            position_ms=0,
            duration_ms=0,
            track_index=0,
            track_count=track_count,
            can_prev=False,
            can_next=False,
            volume=volume,
            muted=False,
            server_seq=server_seq,
            error_message=error_message,
        )


# Note: PlayerStateService should be retrieved from DI container
# Use: container.get("player_state_service")
# Legacy global instance removed - use dependency injection
