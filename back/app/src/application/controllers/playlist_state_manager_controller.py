# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
PlaylistStateManager - Single source of truth for playlist state.

This manager is responsible for maintaining the current state of playlists
and tracks, ensuring consistency across the application.
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class Track:
    """Represents a single track in a playlist."""
    id: str
    title: str
    filename: str
    duration_ms: Optional[int] = None
    file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert track to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "filename": self.filename,
            "duration_ms": self.duration_ms,
            "file_path": self.file_path
        }


@dataclass
class Playlist:
    """Represents a playlist."""
    id: str
    title: str
    tracks: List[Track] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert playlist to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "tracks": [track.to_dict() for track in self.tracks],
            "total_tracks": len(self.tracks)
        }


class PlaylistStateManager:
    """
    Manages the state of playlists and current playback position.

    This is the SINGLE SOURCE OF TRUTH for playlist state.
    All playlist-related queries should go through this manager.
    """

    def __init__(self):
        """Initialize the playlist state manager."""
        self._current_playlist: Optional[Playlist] = None
        self._current_track_index: int = 0
        self._repeat_mode: str = "none"  # none, one, all
        self._shuffle_enabled: bool = False
        self._shuffle_order: List[int] = []

        logger.info("✅ PlaylistStateManager initialized")

    # --- Playlist Management ---

    def set_playlist(self, playlist: Playlist, start_index: int = 0) -> bool:
        """
        Set the current playlist.

        Args:
            playlist: The playlist to set
            start_index: Starting track index

        Returns:
            bool: True if playlist was set successfully
        """
        if not playlist or not playlist.tracks:
            logger.warning("Cannot set empty playlist")
            return False

        self._current_playlist = playlist
        self._current_track_index = max(0, min(start_index, len(playlist.tracks) - 1))

        # Reset shuffle order
        if self._shuffle_enabled:
            self._generate_shuffle_order()

        logger.info(
            f"Playlist '{playlist.title}' set with {len(playlist.tracks)} tracks, starting at index {self._current_track_index}"
        )
        return True

    def clear_playlist(self) -> None:
        """Clear the current playlist."""
        self._current_playlist = None
        self._current_track_index = 0
        self._shuffle_order = []
        logger.info("Playlist cleared")

    # --- Track Navigation ---

    def get_current_track(self) -> Optional[Track]:
        """
        Get the current track.

        Returns:
            Optional[Track]: Current track or None
        """
        if not self._current_playlist or not self._current_playlist.tracks:
            return None

        if 0 <= self._current_track_index < len(self._current_playlist.tracks):
            return self._current_playlist.tracks[self._current_track_index]

        return None

    def move_to_next(self) -> Optional[Track]:
        """
        Move to the next track.

        Returns:
            Optional[Track]: Next track or None if at end
        """
        if not self._current_playlist or not self._current_playlist.tracks:
            return None

        total_tracks = len(self._current_playlist.tracks)

        # Handle repeat one
        if self._repeat_mode == "one":
            return self.get_current_track()

        # Calculate next index
        if self._shuffle_enabled and self._shuffle_order:
            current_shuffle_pos = self._shuffle_order.index(self._current_track_index)
            next_shuffle_pos = current_shuffle_pos + 1

            if next_shuffle_pos < len(self._shuffle_order):
                self._current_track_index = self._shuffle_order[next_shuffle_pos]
            elif self._repeat_mode == "all":
                self._current_track_index = self._shuffle_order[0]
            else:
                return None  # End of playlist
        else:
            next_index = self._current_track_index + 1

            if next_index < total_tracks:
                self._current_track_index = next_index
            elif self._repeat_mode == "all":
                self._current_track_index = 0
            else:
                return None  # End of playlist

        track = self.get_current_track()
        if track:
            logger.info(f"Moved to next track: {track.title} (index {self._current_track_index})")

        return track

    def move_to_previous(self) -> Optional[Track]:
        """
        Move to the previous track.

        Returns:
            Optional[Track]: Previous track or None if at beginning
        """
        if not self._current_playlist or not self._current_playlist.tracks:
            return None

        total_tracks = len(self._current_playlist.tracks)

        # Handle repeat one
        if self._repeat_mode == "one":
            return self.get_current_track()

        # Calculate previous index
        if self._shuffle_enabled and self._shuffle_order:
            current_shuffle_pos = self._shuffle_order.index(self._current_track_index)
            prev_shuffle_pos = current_shuffle_pos - 1

            if prev_shuffle_pos >= 0:
                self._current_track_index = self._shuffle_order[prev_shuffle_pos]
            elif self._repeat_mode == "all":
                self._current_track_index = self._shuffle_order[-1]
            else:
                return None  # Beginning of playlist
        else:
            prev_index = self._current_track_index - 1

            if prev_index >= 0:
                self._current_track_index = prev_index
            elif self._repeat_mode == "all":
                self._current_track_index = total_tracks - 1
            else:
                return None  # Beginning of playlist

        track = self.get_current_track()
        if track:
            logger.info(f"Moved to previous track: {track.title} (index {self._current_track_index})")

        return track

    def move_to_track(self, track_index: int) -> Optional[Track]:
        """
        Move to a specific track by index.

        Args:
            track_index: Index of the track (0-based)

        Returns:
            Optional[Track]: The track at the index or None
        """
        if not self._current_playlist or not self._current_playlist.tracks:
            return None

        if 0 <= track_index < len(self._current_playlist.tracks):
            self._current_track_index = track_index
            track = self.get_current_track()
            if track:
                logger.info(f"Moved to track {track_index}: {track.title}")
            return track

        logger.warning(f"Invalid track index: {track_index}")
        return None

    # --- State Queries ---

    def get_state(self) -> Dict[str, Any]:
        """
        Get the complete playlist state.

        Returns:
            Dict[str, Any]: Current state
        """
        current_track = self.get_current_track()

        return {
            "playlist": self._current_playlist.to_dict() if self._current_playlist else None,
            "current_track": current_track.to_dict() if current_track else None,
            "current_track_index": self._current_track_index,
            "current_track_number": self._current_track_index + 1 if current_track else 0,
            "total_tracks": len(self._current_playlist.tracks) if self._current_playlist else 0,
            "can_next": self.can_go_next(),
            "can_previous": self.can_go_previous(),
            "repeat_mode": self._repeat_mode,
            "shuffle_enabled": self._shuffle_enabled
        }

    def can_go_next(self) -> bool:
        """Check if can move to next track."""
        if not self._current_playlist or not self._current_playlist.tracks:
            return False

        if self._repeat_mode in ["one", "all"]:
            return True

        return self._current_track_index < len(self._current_playlist.tracks) - 1

    def can_go_previous(self) -> bool:
        """Check if can move to previous track."""
        if not self._current_playlist or not self._current_playlist.tracks:
            return False

        if self._repeat_mode in ["one", "all"]:
            return True

        return self._current_track_index > 0

    # --- Playback Modes ---

    def set_repeat_mode(self, mode: str) -> None:
        """
        Set repeat mode.

        Args:
            mode: "none", "one", or "all"
        """
        if mode in ["none", "one", "all"]:
            self._repeat_mode = mode
            logger.info(f"Repeat mode set to: {mode}")

    def set_shuffle(self, enabled: bool) -> None:
        """
        Enable/disable shuffle mode.

        Args:
            enabled: True to enable shuffle
        """
        self._shuffle_enabled = enabled
        if enabled and self._current_playlist:
            self._generate_shuffle_order()
        else:
            self._shuffle_order = []

        logger.info(f"Shuffle {'enabled' if enabled else 'disabled'}")

    def _generate_shuffle_order(self) -> None:
        """Generate a random shuffle order for tracks."""
        if not self._current_playlist:
            return

        import random
        indices = list(range(len(self._current_playlist.tracks)))

        # Keep current track as first in shuffle
        if self._current_track_index < len(indices):
            indices.remove(self._current_track_index)
            random.shuffle(indices)
            self._shuffle_order = [self._current_track_index] + indices
        else:
            random.shuffle(indices)
            self._shuffle_order = indices
