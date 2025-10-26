# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
PlaylistController - Single responsibility for playlist management.

This controller manages ONLY playlist operations:
- Loading playlists from database
- Converting playlist data to domain objects
- Validation of playlist data

NO audio control, NO file path resolution.
"""

from typing import Optional, Dict, Any, List
import logging
from .playlist_state_manager_controller import PlaylistStateManager, Playlist, Track
from .track_resolver_controller import TrackResolver

logger = logging.getLogger(__name__)


class PlaylistController:
    """
    Controller for playlist operations.

    Responsibilities:
    - Load playlists from data services
    - Convert data to domain objects
    - Validate playlist data
    - Maintain playlist state

    NOT responsible for:
    - Audio playback
    - File path resolution (delegates to TrackResolver)
    - Direct file operations
    """

    def __init__(self, track_resolver: TrackResolver, playlist_service=None):
        """
        Initialize the playlist controller.

        Args:
            track_resolver: Service for resolving track file paths
            playlist_service: Domain playlist service for data access (auto-injected if None)
        """
        self._state_manager = PlaylistStateManager()
        self._track_resolver = track_resolver

        # Use domain service from DI if not provided
        if playlist_service is None:
            from app.src.dependencies import get_data_playlist_service
            playlist_service = get_data_playlist_service()
            logger.info("✅ Auto-injected domain playlist service")

        self._playlist_service = playlist_service
        logger.info("✅ PlaylistController initialized with domain service")

    @property
    def state_manager(self) -> PlaylistStateManager:
        """Get the playlist state manager."""
        return self._state_manager

    # --- Playlist Loading ---

    async def load_playlist(self, playlist_id: str) -> bool:
        """
        Load a playlist by ID (async).

        Args:
            playlist_id: ID of the playlist to load

        Returns:
            bool: True if playlist loaded successfully
        """
        try:
            # Get playlist data from domain service (async)
            playlist_data = await self._get_playlist_data(playlist_id)
            if not playlist_data:
                logger.error(f"Playlist {playlist_id} not found")
                return False

            # Convert to domain objects
            playlist = self._convert_to_domain_playlist(playlist_data)
            if not playlist:
                logger.error(f"Failed to convert playlist {playlist_id}")
                return False

            # Resolve track file paths
            self._resolve_track_paths(playlist)

            # Validate playlist
            valid_tracks = self._validate_tracks(playlist.tracks)
            if not valid_tracks:
                logger.error(f"No valid tracks in playlist {playlist_id}")
                return False

            # Update playlist with valid tracks only
            playlist.tracks = valid_tracks

            # Set in state manager
            success = self._state_manager.set_playlist(playlist)
            if success:
                logger.info(
                    f"✅ Playlist '{playlist.title}' loaded with {len(valid_tracks)} valid tracks"
                )

            return success

        except Exception as e:
            logger.error(f"Error loading playlist {playlist_id}: {e}")
            return False

    async def _get_playlist_data(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """
        Get playlist data from domain service (async).

        Args:
            playlist_id: ID of the playlist

        Returns:
            Optional[Dict[str, Any]]: Playlist data or None
        """
        try:
            # Domain service returns data directly (no wrapper dict)
            playlist_data = await self._playlist_service.get_playlist(playlist_id)
            return playlist_data
        except Exception as e:
            logger.error(f"Error getting playlist data from domain service: {e}")
            return None

    def _convert_to_domain_playlist(self, playlist_data: Dict[str, Any]) -> Optional[Playlist]:
        """
        Convert playlist data to domain object.

        Args:
            playlist_data: Raw playlist data

        Returns:
            Optional[Playlist]: Domain playlist object or None
        """
        try:
            playlist_id = playlist_data.get("id")
            # Support both 'title' and 'name' for backward compatibility during data conversion
            playlist_title = playlist_data.get("title") or playlist_data.get("name", f"Playlist {playlist_id}")
            tracks_data = playlist_data.get("tracks", [])

            if not playlist_id:
                logger.error("Playlist missing ID")
                return None

            # Convert tracks
            tracks = []
            for track_data in tracks_data:
                track = self._convert_to_domain_track(track_data)
                if track:
                    tracks.append(track)

            return Playlist(
                id=str(playlist_id),
                title=playlist_title,
                tracks=tracks
            )

        except Exception as e:
            logger.error(f"Error converting playlist data: {e}")
            return None

    def _convert_to_domain_track(self, track_data: Dict[str, Any]) -> Optional[Track]:
        """
        Convert track data to domain object.

        Args:
            track_data: Raw track data

        Returns:
            Optional[Track]: Domain track object or None
        """
        try:
            track_id = track_data.get("id")
            title = track_data.get("title", track_data.get("filename", "Unknown"))
            filename = track_data.get("filename")
            duration_ms = track_data.get("duration_ms")

            if not track_id or not filename:
                logger.warning(f"Track missing required data: {track_data}")
                return None

            return Track(
                id=str(track_id),
                title=title,
                filename=filename,
                duration_ms=duration_ms
            )

        except Exception as e:
            logger.error(f"Error converting track data: {e}")
            return None

    def _resolve_track_paths(self, playlist: Playlist) -> None:
        """
        Resolve file paths for all tracks in playlist.

        Args:
            playlist: Playlist to resolve paths for
        """
        for track in playlist.tracks:
            file_path = self._track_resolver.resolve_path(track.filename)
            track.file_path = file_path

    def _validate_tracks(self, tracks: List[Track]) -> List[Track]:
        """
        Validate tracks and return only valid ones.

        Args:
            tracks: List of tracks to validate

        Returns:
            List[Track]: List of valid tracks
        """
        valid_tracks = []

        for track in tracks:
            if track.file_path and self._track_resolver.validate_path(track.file_path):
                valid_tracks.append(track)
                logger.debug(f"✅ Valid track: {track.title}")
            else:
                logger.warning(f"❌ Invalid track: {track.title} ({track.filename})")

        return valid_tracks

    # --- Current Playlist Operations ---

    def get_current_track(self) -> Optional[Track]:
        """Get the current track."""
        return self._state_manager.get_current_track()

    def next_track(self) -> Optional[Track]:
        """Move to next track."""
        return self._state_manager.move_to_next()

    def previous_track(self) -> Optional[Track]:
        """Move to previous track."""
        return self._state_manager.move_to_previous()

    def goto_track(self, track_number: int) -> Optional[Track]:
        """
        Go to specific track by number (1-based).

        Args:
            track_number: Track number (1-based)

        Returns:
            Optional[Track]: The track or None
        """
        track_index = track_number - 1  # Convert to 0-based
        return self._state_manager.move_to_track(track_index)

    def clear_playlist(self) -> None:
        """Clear current playlist."""
        self._state_manager.clear_playlist()

    # --- Playback Modes ---

    def set_repeat_mode(self, mode: str) -> bool:
        """
        Set repeat mode.

        Args:
            mode: "none", "one", or "all"

        Returns:
            bool: True if mode set successfully
        """
        if mode in ["none", "one", "all"]:
            self._state_manager.set_repeat_mode(mode)
            return True
        return False

    def set_shuffle(self, enabled: bool) -> bool:
        """
        Set shuffle mode.

        Args:
            enabled: True to enable shuffle

        Returns:
            bool: True if mode set successfully
        """
        self._state_manager.set_shuffle(enabled)
        return True

    # --- State Queries ---

    def get_state(self) -> Dict[str, Any]:
        """
        Get complete playlist state.

        Returns:
            Dict[str, Any]: Playlist state
        """
        return self._state_manager.get_state()

    def get_playlist_info(self) -> Dict[str, Any]:
        """
        Get current playlist information for API responses.

        Returns:
            Dict[str, Any]: Playlist information
        """
        state = self._state_manager.get_state()

        return {
            "playlist_id": state["playlist"]["id"] if state["playlist"] else None,
            # Return as 'playlist_name' for API backward compatibility
            "playlist_name": state["playlist"]["title"] if state["playlist"] else None,
            "current_track": state["current_track"],
            "current_track_number": state["current_track_number"],
            "total_tracks": state["total_tracks"],
            "can_next": state["can_next"],
            "can_previous": state["can_previous"],
            "repeat_mode": state["repeat_mode"],
            "shuffle_enabled": state["shuffle_enabled"]
        }

    def has_playlist(self) -> bool:
        """Check if a playlist is currently loaded."""
        return self._state_manager.get_state()["playlist"] is not None

    def has_tracks(self) -> bool:
        """Check if current playlist has tracks."""
        state = self._state_manager.get_state()
        return state["total_tracks"] > 0

    def load_playlist_data(self, playlist: Playlist) -> bool:
        """
        Load playlist data directly (useful for testing).

        Args:
            playlist: Playlist domain object to load

        Returns:
            bool: True if playlist loaded successfully
        """
        try:
            return self._state_manager.set_playlist(playlist)
        except Exception as e:
            logger.error(f"Error loading playlist data: {e}")
            return False
