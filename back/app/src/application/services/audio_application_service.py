# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Audio application service following Domain-Driven Design principles.

This service coordinates audio operations between the domain layer
and external services, implementing audio use cases without containing business logic.
"""

from typing import Dict, Any
import logging

from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track

logger = logging.getLogger(__name__)


class AudioApplicationService:
    """Application service for audio operations.

    Coordinates between domain layer and infrastructure to implement
    audio use cases following DDD principles.
    """

    def __init__(self, audio_domain_container, playlist_application_service, state_manager=None):
        """Initialize audio application service.

        Args:
            audio_domain_container: Domain audio container (required)
            playlist_application_service: Playlist application service (required)
            state_manager: State management service
        """
        if audio_domain_container is None:
            raise ValueError("Audio domain container is required for application service")
        if playlist_application_service is None:
            raise ValueError("Playlist application service is required for audio service")
        self._audio_container = audio_domain_container
        self._playlist_service = playlist_application_service
        self._state_manager = state_manager

    async def play_playlist_use_case(self, playlist_id: str) -> Dict[str, Any]:
        """Use case: Start playing a playlist.

        Args:
            playlist_id: ID of playlist to play

        Returns:
            Result dictionary with operation status
        """
        # Get playlist through injected application service
        playlist_result = await self._playlist_service.get_playlist_use_case(playlist_id)
        if playlist_result["status"] != "success":
            return playlist_result
        playlist_data = playlist_result["playlist"]
        # Validate playlist has tracks
        if not playlist_data.get("tracks") or len(playlist_data["tracks"]) == 0:
            return {
                "status": "error",
                "message": "Cannot play empty playlist",
                "error_type": "validation_error",
            }
        # Use domain audio engine if available
        if self._audio_container and self._audio_container.is_initialized:
            audio_engine = self._audio_container.audio_engine
            # Convert to domain entity for audio engine
            tracks = []
            for track_data in playlist_data["tracks"]:
                track = Track(
                    track_number=track_data.get("track_number", 1),
                    title=track_data.get("title", "Unknown"),
                    filename=track_data.get("filename", ""),
                    file_path=track_data.get("file_path", ""),
                    duration_ms=track_data.get("duration_ms"),
                    artist=track_data.get("artist"),
                    album=track_data.get("album"),
                    id=track_data.get("id"),
                )
                tracks.append(track)
            playlist = Playlist(
                name=playlist_data.get("name", ""),
                tracks=tracks,
                description=playlist_data.get("description"),
                id=playlist_data.get("id"),
                nfc_tag_id=playlist_data.get("nfc_tag_id"),
            )
            # Set playlist in audio engine
            success = await audio_engine.set_playlist(playlist)
            if success:
                logger.info(f"✅ Playing playlist via domain audio engine: {playlist_id}")
                # Broadcast state change if state manager available
                if self._state_manager:
                    await self._state_manager.broadcast_playlist_started(playlist_id)
                return {
                    "status": "success",
                    "message": "Playlist started successfully",
                    "playlist_id": playlist_id,
                    "track_count": len(tracks),
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to start playlist in audio engine",
                    "error_type": "audio_error",
                }
        else:
            return {
                "status": "error",
                "message": "Audio domain container not initialized",
                "error_type": "service_unavailable",
            }

    async def control_playback_use_case(self, action: str) -> Dict[str, Any]:
        """Use case: Control audio playback.

        Args:
            action: Playback action (play, pause, stop, next, previous)

        Returns:
            Result dictionary with operation status
        """
        # Use domain audio engine
        if self._audio_container.is_initialized:
            audio_engine = self._audio_container.audio_engine
            success = False
            if action == "play":
                success = await audio_engine.resume()
            elif action == "pause":
                success = await audio_engine.pause()
            elif action == "stop":
                success = await audio_engine.stop()
            elif action == "next":
                success = await audio_engine.next_track()
            elif action == "previous":
                success = await audio_engine.previous_track()
            else:
                return {
                    "status": "error",
                    "message": f"Unknown playback action: {action}",
                    "error_type": "validation_error",
                }
            if success:
                logger.info(f"✅ Playback control via domain engine: {action}")
                # Broadcast state change if state manager available
                if self._state_manager:
                    await self._state_manager.broadcast_playback_changed(action)
                return {
                    "status": "success",
                    "message": f"Playback {action} executed successfully",
                    "action": action,
                }
            else:
                return {
                    "status": "error",
                    "message": f"Failed to execute playback {action}",
                    "error_type": "audio_error",
                }
        else:
            return {
                "status": "error",
                "message": "Audio domain container not initialized",
                "error_type": "service_unavailable",
            }

    def get_playback_status_use_case(self) -> Dict[str, Any]:
        """Use case: Get current playback status.

        Returns:
            Result dictionary with playback status
        """
        # Use domain audio engine
        if self._audio_container.is_initialized:
            audio_engine = self._audio_container.audio_engine
            state = audio_engine.get_state_dict()
            return {
                "status": "success",
                "message": "Playback status retrieved successfully",
                "playback_status": state,
            }
        else:
            return {
                "status": "error",
                "message": "Audio domain container not initialized",
                "error_type": "service_unavailable",
            }

    async def set_volume_use_case(self, volume: int) -> Dict[str, Any]:
        """Use case: Set audio volume.

        Args:
            volume: Volume level (0-100)

        Returns:
            Result dictionary with operation status
        """
        try:
            # Validate volume range
            if not 0 <= volume <= 100:
                return {
                    "status": "error",
                    "message": "Volume must be between 0 and 100",
                    "error_type": "validation_error",
                }

            # Use domain audio engine
            if self._audio_container.is_initialized:
                audio_engine = self._audio_container.audio_engine
                success = await audio_engine.set_volume(volume)

                if success:
                    logger.info(f"✅ Volume set via domain engine: {volume}")

                    # Broadcast state change if state manager available
                    if self._state_manager:
                        await self._state_manager.broadcast_volume_changed(volume)

                    return {
                        "status": "success",
                        "message": f"Volume set to {volume}",
                        "volume": volume,
                    }
                else:
                    return {
                        "status": "error",
                        "message": "Failed to set volume",
                        "error_type": "audio_error",
                    }
            else:
                return {
                    "status": "error",
                    "message": "Audio domain container not initialized",
                    "error_type": "service_unavailable",
                }

        except Exception as e:
            logger.error(f"❌ Failed to set volume {volume}: {e}")
            return {
                "status": "error",
                "message": f"Volume control failed: {str(e)}",
                "error_type": "application_error",
            }
