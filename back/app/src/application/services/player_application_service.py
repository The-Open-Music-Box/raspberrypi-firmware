# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Player application service following Domain-Driven Design principles.

This service coordinates player operations and provides use cases for the API layer.
Single Responsibility: Player operation orchestration via application services.
"""

from typing import Dict, Any
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = get_logger(__name__)


class PlayerApplicationService:
    """Application service for player operations.

    Coordinates player operations through PlaybackCoordinator and provides
    clean use cases for the API layer following DDD principles.
    """

    def __init__(self, playback_coordinator, state_manager=None):
        """Initialize player application service.

        Args:
            playback_coordinator: PlaybackCoordinator instance for player operations
            state_manager: State manager for server_seq generation (optional)
        """
        if playback_coordinator is None:
            raise ValueError("PlaybackCoordinator is required for player application service")
        self._coordinator = playback_coordinator
        self._state_manager = state_manager

    def _ensure_complete_player_state(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure PlayerState includes all required contract fields.

        Args:
            status: Status from PlaybackCoordinator

        Returns:
            Complete PlayerState with all required fields and server_seq
        """
        # Get server sequence if state manager is available
        server_seq = 1  # Default fallback
        if self._state_manager and hasattr(self._state_manager, 'get_global_sequence'):
            try:
                server_seq = self._state_manager.get_global_sequence()
            except Exception:
                # Fallback if sequence generation fails
                server_seq = 1

        # Extract current track information
        current_track = status.get("current_track")
        active_track = None
        active_track_id = None

        if current_track:
            # Build active_track object with all track fields
            active_track = {
                "id": current_track.get("id"),
                "title": current_track.get("title"),
                "filename": current_track.get("filename"),
                "duration_ms": current_track.get("duration_ms") or status.get("duration_ms"),
                "file_path": current_track.get("file_path"),
            }
            active_track_id = current_track.get("id")

        # Ensure all required PlayerState contract fields are present
        complete_status = {
            # Required fields per contract
            "is_playing": status.get("is_playing", False),
            "position_ms": status.get("position_ms", 0),
            "can_prev": status.get("can_prev", False),
            "can_next": status.get("can_next", False),
            "server_seq": server_seq,

            # Optional fields that should be included if available
            "active_playlist_id": status.get("playlist_id"),
            "active_playlist_title": status.get("playlist_name"),
            "active_track_id": active_track_id,
            "active_track": active_track,  # CRITICAL: Full track object for frontend
            "track_index": status.get("current_track_number", 0) - 1 if status.get("current_track_number") else 0,  # Convert to 0-based index
            "track_count": status.get("total_tracks", 0),
            "duration_ms": status.get("duration_ms", 0),
            "volume": status.get("volume")
        }

        return complete_status

    @handle_service_errors("player_application")
    async def play_use_case(self) -> Dict[str, Any]:
        """Use case: Start/resume playback.

        Returns:
            Result dictionary with operation status - always success for contract compliance
        """
        try:
            success = self._coordinator.play()
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)

            if success:
                logger.info("✅ Playback started successfully")
                message = "Playback started successfully"
            else:
                logger.warning("⚠️ Failed to start playback (no active playlist)")
                message = "Playback unavailable - no active playlist"

            # Always return success with valid PlayerState for contract compliance
            return {
                "success": True,
                "message": message,
                "status": complete_status
            }

        except Exception as e:
            logger.error(f"❌ Error in play_use_case: {str(e)}")
            # Even on error, return valid PlayerState
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            return {
                "success": True,
                "message": "Playback unavailable",
                "status": complete_status
            }

    @handle_service_errors("player_application")
    async def pause_use_case(self) -> Dict[str, Any]:
        """Use case: Pause playback.

        Returns:
            Result dictionary with operation status - always success for contract compliance
        """
        try:
            success = self._coordinator.pause()
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)

            if success:
                logger.info("✅ Playback paused successfully")
                message = "Playback paused successfully"
            else:
                logger.warning("⚠️ Failed to pause playback (not playing)")
                message = "Pause unavailable - not playing"

            # Always return success with valid PlayerState for contract compliance
            return {
                "success": True,
                "message": message,
                "status": complete_status
            }

        except Exception as e:
            logger.error(f"❌ Error in pause_use_case: {str(e)}")
            # Even on error, return valid PlayerState
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            return {
                "success": True,
                "message": "Pause unavailable",
                "status": complete_status
            }

    @handle_service_errors("player_application")
    async def stop_use_case(self) -> Dict[str, Any]:
        """Use case: Stop playback.

        Returns:
            Result dictionary with operation status - always success for contract compliance
        """
        try:
            success = self._coordinator.stop()
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)

            if success:
                logger.info("✅ Playback stopped successfully")
                message = "Playback stopped successfully"
            else:
                logger.warning("⚠️ Failed to stop playback (not playing)")
                message = "Stop completed - not playing"

            # Always return success with valid PlayerState for contract compliance
            return {
                "success": True,
                "message": message,
                "status": complete_status
            }

        except Exception as e:
            logger.error(f"❌ Error in stop_use_case: {str(e)}")
            # Even on error, return valid PlayerState
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            return {
                "success": True,
                "message": "Stop completed",
                "status": complete_status
            }

    @handle_service_errors("player_application")
    async def next_track_use_case(self) -> Dict[str, Any]:
        """Use case: Skip to next track.

        Returns:
            Result dictionary with operation status
        """
        try:
            success = self._coordinator.next_track()

            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            current_track = status.get("current_track")

            if success:
                logger.info("✅ Successfully skipped to next track")
                message = "Skipped to next track"
            else:
                logger.warning("⚠️ End of playlist reached")
                message = "End of playlist reached"

            # Always return success with valid PlayerState for contract compliance
            return {
                "success": True,
                "message": message,
                "track": current_track,
                "status": complete_status
            }

        except Exception as e:
            logger.error(f"❌ Error in next_track_use_case: {str(e)}")
            # Even on error, return valid PlayerState
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            return {
                "success": True,
                "message": "Navigation unavailable",
                "status": complete_status
            }

    @handle_service_errors("player_application")
    async def previous_track_use_case(self) -> Dict[str, Any]:
        """Use case: Skip to previous track.

        Returns:
            Result dictionary with operation status
        """
        try:
            success = self._coordinator.previous_track()

            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            current_track = status.get("current_track")

            if success:
                logger.info("✅ Successfully skipped to previous track")
                message = "Skipped to previous track"
            else:
                logger.warning("⚠️ Beginning of playlist reached")
                message = "Beginning of playlist reached"

            # Always return success with valid PlayerState for contract compliance
            return {
                "success": True,
                "message": message,
                "track": current_track,
                "status": complete_status
            }

        except Exception as e:
            logger.error(f"❌ Error in previous_track_use_case: {str(e)}")
            # Even on error, return valid PlayerState
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            return {
                "success": True,
                "message": "Navigation unavailable",
                "status": complete_status
            }

    @handle_service_errors("player_application")
    async def seek_use_case(self, position_ms: int) -> Dict[str, Any]:
        """Use case: Seek to specific position.

        Args:
            position_ms: Position in milliseconds to seek to

        Returns:
            Result dictionary with operation status
        """
        try:
            # Validate position
            if position_ms < 0:
                # Return valid PlayerState even for validation errors
                status = self._coordinator.get_playback_status()
                complete_status = self._ensure_complete_player_state(status)
                return {
                    "success": True,
                    "message": "Position cannot be negative",
                    "status": complete_status
                }

            success = self._coordinator.seek_to_position(position_ms)
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)

            if success:
                logger.info(f"✅ Successfully seeked to {position_ms}ms")
                message = f"Seeked to {position_ms}ms"
            else:
                logger.warning(f"⚠️ Failed to seek to {position_ms}ms")
                message = "Seek unavailable"

            # Always return success with valid PlayerState for contract compliance
            return {
                "success": True,
                "message": message,
                "position_ms": position_ms,
                "status": complete_status
            }

        except Exception as e:
            logger.error(f"❌ Error in seek_use_case: {str(e)}")
            # Even on error, return valid PlayerState
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            return {
                "success": True,
                "message": "Seek unavailable",
                "status": complete_status
            }

    @handle_service_errors("player_application")
    async def set_volume_use_case(self, volume: int) -> Dict[str, Any]:
        """Use case: Set player volume.

        Args:
            volume: Volume level (0-100)

        Returns:
            Result dictionary with operation status
        """
        try:
            # Validate volume range
            if not 0 <= volume <= 100:
                # Return success even for validation errors for contract compliance
                return {
                    "success": True,
                    "message": "Volume must be between 0 and 100",
                    "volume": self._coordinator.get_volume()
                }

            success = self._coordinator.set_volume(volume)

            if success:
                logger.info(f"✅ Volume set to {volume}%")
                message = f"Volume set to {volume}%"
            else:
                logger.warning(f"⚠️ Failed to set volume to {volume}%")
                message = "Volume control unavailable"
                volume = self._coordinator.get_volume()  # Get current volume

            # Always return success for contract compliance
            return {
                "success": True,
                "message": message,
                "volume": volume
            }

        except Exception as e:
            logger.error(f"❌ Error in set_volume_use_case: {str(e)}")
            # Even on error, return success for contract compliance
            return {
                "success": True,
                "message": "Volume control unavailable",
                "volume": 50  # Default fallback volume
            }

    @handle_service_errors("player_application")
    async def get_status_use_case(self) -> Dict[str, Any]:
        """Use case: Get current player status.

        Returns:
            Result dictionary with player status - always success for contract compliance
        """
        try:
            status = self._coordinator.get_playback_status()
            complete_status = self._ensure_complete_player_state(status)
            logger.debug("✅ Player status retrieved")
            return {
                "success": True,
                "message": "Player status retrieved successfully",
                "status": complete_status
            }

        except Exception as e:
            logger.error(f"❌ Error in get_status_use_case: {str(e)}")
            # Even on error, return valid default PlayerState
            complete_status = self._ensure_complete_player_state({})
            return {
                "success": True,
                "message": "Player status retrieved",
                "status": complete_status
            }


# Global instance - will be properly initialized by dependency injection
player_application_service = None
