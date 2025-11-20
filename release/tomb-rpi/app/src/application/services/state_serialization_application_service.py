# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
State Serialization Application Service (DDD Architecture)

Single responsibility: Serializes domain objects for transport layer.
Clean separation following Domain-Driven Design principles.
"""

from typing import Any, Dict, List
import logging

from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.services.sequence_generator import SequenceGenerator

logger = logging.getLogger(__name__)


class StateSerializationApplicationService:
    """
    Handles serialization of domain objects for state broadcasting.

    Single Responsibility: Converting domain objects to transport-ready dictionaries.

    Responsibilities:
    - Playlist serialization with sequence numbers
    - Track serialization with metadata
    - Ensuring consistent data format for Socket.IO transport

    Does NOT handle:
    - Event broadcasting (delegated to StateEventCoordinator)
    - Business logic (handled by domain services)
    - Transport (handled by Socket.IO layer)
    """

    def __init__(self, sequences: SequenceGenerator = None):
        """Initialize state serialization service.

        Args:
            sequences: Sequence generator for adding sequence numbers to serialized objects
        """
        self.sequences = sequences or SequenceGenerator()
        logger.info("StateSerializationApplicationService initialized with clean DDD architecture")

    @handle_service_errors("state_serialization_service")
    def serialize_playlist(self, playlist, include_tracks: bool = True) -> Dict[str, Any]:
        """
        Serialize a playlist object or dict for transmission.

        Args:
            playlist: Playlist domain object or dictionary
            include_tracks: Whether to include track data in serialization

        Returns:
            Serialized playlist data
        """
        if isinstance(playlist, dict):
            serialized = {
                "id": playlist.get("id"),
                "title": playlist.get("title") or playlist.get("name", ""),
                "description": playlist.get("description", ""),
                "nfc_tag_id": playlist.get("nfc_tag_id"),
                "track_count": playlist.get("track_count", len(playlist.get("tracks", []))),
                "created_at": playlist.get("created_at"),
                "updated_at": playlist.get("updated_at"),
                "server_seq": self.sequences.get_current_global_seq(),
                "playlist_seq": self.sequences.get_current_playlist_seq(playlist.get("id")),
            }

            if include_tracks:
                serialized["tracks"] = [
                    self.serialize_track(track) for track in playlist.get("tracks", [])
                ]
        else:
            # Handle domain object
            serialized = {
                "id": playlist.id,
                "title": playlist.title,
                "description": getattr(playlist, "description", ""),
                "nfc_tag_id": getattr(playlist, "nfc_tag_id", None),
                "track_count": getattr(
                    playlist, "track_count", len(getattr(playlist, "tracks", []))
                ),
                "created_at": getattr(playlist, "created_at", None),
                "updated_at": getattr(playlist, "updated_at", None),
                "server_seq": self.sequences.get_current_global_seq(),
                "playlist_seq": self.sequences.get_current_playlist_seq(playlist.id),
            }

            if include_tracks:
                serialized["tracks"] = [
                    self.serialize_track(track) for track in getattr(playlist, "tracks", [])
                ]

        return serialized

    @handle_service_errors("state_serialization_service")
    def serialize_track(self, track) -> Dict[str, Any]:
        """
        Serialize a track object or dict for transmission.

        Args:
            track: Track domain object or dictionary

        Returns:
            Serialized track data
        """
        if isinstance(track, dict):
            return {
                **track,
                "server_seq": self.sequences.get_current_global_seq(),
            }
        else:
            # Handle domain object
            return {
                "id": track.id,
                "title": track.title,
                "filename": track.filename,
                "duration_ms": int((track.duration or 0) * 1000),
                "artist": getattr(track, "artist", None),
                "album": getattr(track, "album", None),
                "track_number": getattr(track, "number", None),
                "play_count": getattr(track, "play_count", 0),
                "created_at": getattr(track, "created_at", None),
                "server_seq": self.sequences.get_current_global_seq(),
            }

    @handle_service_errors("state_serialization_service")
    def serialize_playlists_collection(self, playlists: List) -> List[Dict[str, Any]]:
        """
        Serialize a collection of playlists.

        Args:
            playlists: List of playlist objects or dictionaries

        Returns:
            List of serialized playlist data
        """
        return [self.serialize_playlist(playlist, include_tracks=False) for playlist in playlists]

    @handle_service_errors("state_serialization_service")
    def serialize_tracks_collection(self, tracks: List) -> List[Dict[str, Any]]:
        """
        Serialize a collection of tracks.

        Args:
            tracks: List of track objects or dictionaries

        Returns:
            List of serialized track data
        """
        return [self.serialize_track(track) for track in tracks]

    @handle_service_errors("state_serialization_service")
    def serialize_playback_state(
        self,
        state: str,
        track_info: Dict[str, Any] = None,
        playlist_info: Dict[str, Any] = None,
        position: float = 0.0,
        volume: int = 50,
        error: str = None,
    ) -> Dict[str, Any]:
        """
        Serialize current playback state for broadcasting.

        Args:
            state: Current playback state string
            track_info: Current track information
            playlist_info: Current playlist information
            position: Current playback position in seconds
            volume: Current volume level
            error: Error message if any

        Returns:
            Serialized playback state
        """
        serialized_state = {
            "state": state,
            "position_seconds": position,
            "volume": volume,
            "server_seq": self.sequences.get_current_global_seq(),
            "timestamp": self.sequences.get_current_global_seq(),  # Use seq as timestamp reference
        }

        if track_info:
            serialized_state["track"] = track_info

        if playlist_info:
            serialized_state["playlist"] = playlist_info

        if error:
            serialized_state["error"] = error

        return serialized_state
