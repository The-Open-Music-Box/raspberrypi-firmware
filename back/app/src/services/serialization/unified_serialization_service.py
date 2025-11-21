# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified Serialization Service

This service centralizes all data serialization logic to eliminate duplications
across the application. It provides consistent formats for playlists, tracks,
and player states across all layers (API, WebSocket, Database).
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = get_logger(__name__)


class UnifiedSerializationService:
    """
    Service centralisé pour toutes les sérialisations de données.

    Élimine les duplications de sérialisation identifiées dans:
    - PlaylistRoutesState
    - DataApplicationService
    - SQLitePlaylistRepository
    - UnifiedController
    - AudioController
    - PlayerStateService
    """

    # Format constants for consistency
    FORMAT_API = "api"
    FORMAT_WEBSOCKET = "websocket"
    FORMAT_DATABASE = "database"
    FORMAT_INTERNAL = "internal"

    @staticmethod
    @handle_service_errors("unified_serialization")
    def serialize_playlist(
        playlist: Any,
        include_tracks: bool = True,
        format: str = "api",
        calculate_duration: bool = True,
    ) -> Dict[str, Any]:
        """
        Sérialise une playlist dans le format spécifié.

        Args:
            playlist: Objet playlist (Domain entity, dict, ou DB row)
            include_tracks: Inclure les tracks dans la sérialisation
            format: Format cible ('api', 'websocket', 'database', 'internal')
            calculate_duration: Calculer la durée totale de la playlist

        Returns:
            Playlist sérialisée selon le format demandé
        """
        # Handle different input types
        if playlist is None:
            # Handle None input
            playlist_data = {
                "id": None,
                "title": "",
                "description": "",
                "nfc_tag_id": None,
                "created_at": None,
                "updated_at": None,
                "tracks": [],
            }
        elif isinstance(playlist, dict):
            playlist_data = playlist
        elif hasattr(playlist, "__dict__"):
            # Domain entity
            playlist_data = {
                "id": getattr(playlist, "id", None),
                "title": getattr(playlist, "name", getattr(playlist, "title", "")),
                "description": getattr(playlist, "description", ""),
                "nfc_tag_id": getattr(playlist, "nfc_tag_id", None),
                "created_at": getattr(playlist, "created_at", None),
                "updated_at": getattr(playlist, "updated_at", None),
                "tracks": getattr(playlist, "tracks", []),
            }
        else:
            # Database row or tuple
            playlist_data = {
                "id": playlist[0] if len(playlist) > 0 else None,
                "title": playlist[1] if len(playlist) > 1 else "",
                "description": playlist[2] if len(playlist) > 2 else "",
                "nfc_tag_id": playlist[3] if len(playlist) > 3 else None,
                "created_at": playlist[4] if len(playlist) > 4 else None,
                "updated_at": playlist[5] if len(playlist) > 5 else None,
                "tracks": [],
            }
        # Build base structure
        result = {
            "id": playlist_data.get("id"),
            "title": playlist_data.get("title", playlist_data.get("name", "")),
            "description": playlist_data.get("description", ""),
            "nfc_tag_id": playlist_data.get("nfc_tag_id"),
        }
        # Add tracks if requested
        if include_tracks:
            tracks = playlist_data.get("tracks", [])
            if tracks:
                result["tracks"] = [
                    UnifiedSerializationService.serialize_track(track, format) for track in tracks
                ]
            else:
                result["tracks"] = []
            # Calculate total duration if requested
            if calculate_duration:
                total_duration_ms = sum(track.get("duration_ms", 0) or 0 for track in result["tracks"])
                result["total_duration_ms"] = total_duration_ms
                result["track_count"] = len(result["tracks"])
        # Format-specific adjustments
        if format == UnifiedSerializationService.FORMAT_API:
            # API format includes additional metadata required by frontend
            result["created_at"] = UnifiedSerializationService._format_datetime(
                playlist_data.get("created_at")
            )
            result["updated_at"] = UnifiedSerializationService._format_datetime(
                playlist_data.get("updated_at")
            )
            # Add required frontend fields
            result["type"] = "playlist"  # Required by frontend PlayList interface
            result["last_played"] = playlist_data.get("last_played", 0)  # Default to 0 if not set
        elif format == UnifiedSerializationService.FORMAT_WEBSOCKET:
            # WebSocket format is more compact
            if not include_tracks:
                result.pop("tracks", None)
            # Add type for WebSocket events
            result["type"] = "playlist"
        elif format == UnifiedSerializationService.FORMAT_DATABASE:
            # Database format uses different field names
            result = {
                "id": result["id"],
                "title": result["title"],
                "description": result["description"],
                "nfc_tag_id": result["nfc_tag_id"],
                "path": playlist_data.get("path", ""),  # Use path from original data
                "created_at": playlist_data.get("created_at"),
                "updated_at": playlist_data.get("updated_at"),
            }
        elif format == UnifiedSerializationService.FORMAT_INTERNAL:
            # Internal format keeps all data
            result.update(
                {
                    "path": playlist_data.get("path"),
                    "server_seq": playlist_data.get("server_seq"),
                    "playlist_seq": playlist_data.get("playlist_seq"),
                    "last_played": playlist_data.get("last_played"),
                }
            )
        return result

    @staticmethod
    @handle_service_errors("unified_serialization")
    def serialize_track(track: Any, format: str = "api") -> Dict[str, Any]:
        """
        Sérialise une track dans le format spécifié.

        Args:
            track: Objet track (Domain entity, dict, ou DB row)
            format: Format cible ('api', 'websocket', 'database', 'internal')

        Returns:
            Track sérialisée selon le format
        """
        # Handle different input types
        if isinstance(track, dict):
            track_data = track
        elif hasattr(track, "__dict__"):
            # Domain entity
            track_data = {
                "id": getattr(track, "id", None),
                "track_number": getattr(track, "track_number", 0),
                "title": getattr(track, "title", ""),
                "filename": getattr(track, "filename", ""),
                "file_path": getattr(track, "file_path", ""),
                "duration_ms": getattr(track, "duration_ms", 0),
                "artist": getattr(track, "artist", None),
                "album": getattr(track, "album", None),
                "play_count": getattr(track, "play_count", 0),
            }
        else:
            # Database row or tuple
            track_data = {
                "id": track[0] if len(track) > 0 else None,
                "track_number": track[1] if len(track) > 1 else 0,
                "title": track[2] if len(track) > 2 else "",
                "filename": track[3] if len(track) > 3 else "",
                "file_path": track[4] if len(track) > 4 else "",
                "duration_ms": track[5] if len(track) > 5 else 0,
                "artist": track[6] if len(track) > 6 else None,
                "album": track[7] if len(track) > 7 else None,
            }
        # Build base structure
        result = {
            "id": track_data.get("id"),
            "track_number": track_data.get("track_number", track_data.get("number", 0)),
            "title": track_data.get("title", ""),
            "filename": track_data.get("filename", ""),
            "duration_ms": track_data.get("duration_ms", track_data.get("duration", 0)) or 0,
        }
        # Format-specific adjustments
        if format == UnifiedSerializationService.FORMAT_API:
            # API includes all metadata required by frontend
            result.update(
                {
                    "file_path": track_data.get("file_path", ""),
                    "artist": track_data.get("artist"),
                    "album": track_data.get("album"),
                    "play_count": track_data.get("play_count", 0),
                    # Add required frontend fields
                    "created_at": UnifiedSerializationService._format_datetime(
                        track_data.get("created_at")
                    ),
                    "updated_at": UnifiedSerializationService._format_datetime(
                        track_data.get("updated_at")
                    ),
                    "server_seq": track_data.get("server_seq", 1),  # Default to 1 if not set
                }
            )
        elif format == UnifiedSerializationService.FORMAT_WEBSOCKET:
            # WebSocket format is minimal
            result = {
                "id": result["id"],
                "track_number": result["track_number"],
                "title": result["title"],
                "duration_ms": result["duration_ms"],
            }
        elif format == UnifiedSerializationService.FORMAT_DATABASE:
            # Database format with all fields
            result = {
                "id": result["id"],
                "track_number": result["track_number"],
                "title": result["title"],
                "filename": result["filename"],
                "file_path": track_data.get("file_path", ""),
                "duration_ms": result["duration_ms"],
                "file_hash": track_data.get("file_hash"),
                "file_size": track_data.get("file_size"),
                "artist": track_data.get("artist"),
                "album": track_data.get("album"),
                "play_count": track_data.get("play_count", 0),
                "created_at": track_data.get("created_at"),
                "updated_at": track_data.get("updated_at"),
            }
        elif format == UnifiedSerializationService.FORMAT_INTERNAL:
            # Internal format keeps everything
            result.update(track_data)
        return result

    @staticmethod
    @handle_service_errors("unified_serialization")
    def serialize_player_state(
        audio_controller: Any, state_manager: Any = None, include_playlist: bool = True
    ) -> Dict[str, Any]:
        """
        Construit l'état player unifié.

        Remplace les implémentations dupliquées dans:
        - PlayerStateService.build_current_player_state()
        - AudioController.get_playback_state()
        - SystemRoutes.get_playback_status_direct()

        Args:
            audio_controller: Instance AudioController
            state_manager: Instance StateManager optionnelle
            include_playlist: Inclure les détails de la playlist active

        Returns:
            État player unifié et cohérent
        """
        # Get basic player state
        is_playing = audio_controller.is_playing() if audio_controller else False
        is_paused = getattr(audio_controller, "is_paused", lambda: False)()
        # Get current position
        position_ms = 0
        if audio_controller and hasattr(audio_controller, "get_current_position"):
            position_ms = audio_controller.get_current_position()
        # Get volume
        volume = 50  # Default
        if audio_controller and hasattr(audio_controller, "get_volume"):
            volume = audio_controller.get_volume()
        # Build base state
        state = {
            "is_playing": is_playing,
            "is_paused": is_paused,
            "is_stopped": not is_playing and not is_paused,
            "position_ms": position_ms,
            "volume": volume,
            "timestamp": datetime.now().isoformat(),
        }
        # Add playlist information if available
        if include_playlist and audio_controller:
            current_playlist = getattr(audio_controller, "_current_playlist", None)
            current_playlist_id = getattr(audio_controller, "_current_playlist_id", None)
            current_track_index = getattr(audio_controller, "_current_track_index", 0)
            if current_playlist:
                # Serialize playlist (without tracks for performance)
                playlist_data = UnifiedSerializationService.serialize_playlist(
                    current_playlist,
                    include_tracks=False,
                    format=UnifiedSerializationService.FORMAT_WEBSOCKET,
                )
                state["active_playlist"] = playlist_data
                state["active_playlist_id"] = current_playlist_id
                state["active_playlist_title"] = playlist_data.get("title", "")
                # Add current track info
                if hasattr(current_playlist, "tracks") and current_playlist.tracks:
                    if 0 <= current_track_index < len(current_playlist.tracks):
                        current_track = current_playlist.tracks[current_track_index]
                        state["active_track"] = UnifiedSerializationService.serialize_track(
                            current_track, format=UnifiedSerializationService.FORMAT_WEBSOCKET
                        )
                        state["active_track_id"] = state["active_track"].get("id")
                        state["active_track_title"] = state["active_track"].get("title", "")
                        state["duration_ms"] = state["active_track"].get("duration_ms", 0)
            else:
                # No active playlist
                state.update(
                    {
                        "active_playlist": None,
                        "active_playlist_id": None,
                        "active_playlist_title": None,
                        "active_track": None,
                        "active_track_id": None,
                        "active_track_title": None,
                        "duration_ms": 0,
                    }
                )
        # Add server sequence if state_manager available
        if state_manager and hasattr(state_manager, "get_global_sequence"):
            state["server_seq"] = state_manager.get_global_sequence()
        # Add playback mode
        state["repeat_mode"] = getattr(audio_controller, "_repeat_mode", "none")
        state["shuffle"] = getattr(audio_controller, "_shuffle", False)
        return state

    @staticmethod
    def serialize_bulk_playlists(
        playlists: List[Any], format: str = "api", include_tracks: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Sérialise une liste de playlists de manière optimisée.

        Args:
            playlists: Liste de playlists
            format: Format de sortie
            include_tracks: Inclure les tracks

        Returns:
            Liste de playlists sérialisées
        """
        return [
            UnifiedSerializationService.serialize_playlist(
                playlist,
                include_tracks=include_tracks,
                format=format,
                calculate_duration=include_tracks,
            )
            for playlist in playlists
        ]

    @staticmethod
    def _format_datetime(dt: Any) -> str:
        """
        Formate une datetime de manière cohérente.

        Args:
            dt: DateTime, string, ou None

        Returns:
            String ISO format or empty string (never None for contract compliance)
        """
        if dt is None:
            return ""  # Return empty string instead of None for contract compliance

        if isinstance(dt, str):
            return dt

        if hasattr(dt, "isoformat"):
            return dt.isoformat()

        return str(dt)

    @staticmethod
    def get_format_for_context(context: str) -> str:
        """
        Détermine le format approprié selon le contexte.

        Args:
            context: Contexte d'utilisation ('route', 'websocket', 'repository', etc.)

        Returns:
            Format approprié
        """
        format_mapping = {
            "route": UnifiedSerializationService.FORMAT_API,
            "api": UnifiedSerializationService.FORMAT_API,
            "websocket": UnifiedSerializationService.FORMAT_WEBSOCKET,
            "socket": UnifiedSerializationService.FORMAT_WEBSOCKET,
            "repository": UnifiedSerializationService.FORMAT_DATABASE,
            "database": UnifiedSerializationService.FORMAT_DATABASE,
            "db": UnifiedSerializationService.FORMAT_DATABASE,
            "internal": UnifiedSerializationService.FORMAT_INTERNAL,
            "domain": UnifiedSerializationService.FORMAT_INTERNAL,
        }

        return format_mapping.get(context.lower(), UnifiedSerializationService.FORMAT_API)

