# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Playlist domain entity following Domain-Driven Design principles."""

from dataclasses import dataclass, field
from typing import List, Optional

from .track import Track


@dataclass
class Playlist:
    """Domain entity representing a playlist of audio tracks.

    This is a core domain entity that encapsulates the business logic
    and rules related to playlists according to Domain-Driven Design principles.

    Attributes:
        title: Title of the playlist (contract-compliant field name)
        tracks: List of tracks in the playlist
        description: Optional description of the playlist
        id: Optional unique identifier
        nfc_tag_id: Optional NFC tag associated with the playlist
    """

    title: str
    tracks: List[Track] = field(default_factory=list)
    description: Optional[str] = None
    id: Optional[str] = None
    nfc_tag_id: Optional[str] = None
    path: Optional[str] = None

    @classmethod
    def from_api_data(cls, title: Optional[str] = None, name: Optional[str] = None, **kwargs) -> "Playlist":
        """Domain factory method: Create a playlist from API data.

        Args:
            title: Playlist title (contract-compliant field name)
            name: Legacy parameter for backward compatibility (maps to title)
            **kwargs: Additional attributes to set on the playlist

        Returns:
            A new Playlist domain entity

        Raises:
            ValueError: If neither title nor name is provided
        """
        # Contract compliance: prefer 'title', but accept 'name' for backward compatibility
        playlist_title = title or name
        if not playlist_title or not playlist_title.strip():
            raise ValueError("Either title or name must be provided")

        return cls(title=playlist_title, **kwargs)

    @classmethod
    def from_files(cls, title: str, file_paths: List[str], **kwargs) -> "Playlist":
        """Domain factory method: Create a playlist from a list of file paths.

        Args:
            title: Title of the playlist
            file_paths: List of file paths to create tracks from
            **kwargs: Additional attributes to set on the playlist

        Returns:
            A new Playlist domain entity
        """
        tracks = [Track.from_file(file_path, idx + 1) for idx, file_path in enumerate(file_paths)]
        return cls(title=title, tracks=tracks, **kwargs)

    def get_track(self, number: int) -> Optional[Track]:
        """Domain service: Get track by number (1-based index).

        Args:
            number: Track number to retrieve

        Returns:
            The track or None if not found
        """
        try:
            return next(t for t in self.tracks if t.track_number == number)
        except StopIteration:
            return None

    def add_track(self, track: Track) -> None:
        """Domain behavior: Add a track to the playlist.

        Business rule: Auto-assign track number if not set and maintain order.

        Args:
            track: Track to add
        """
        # Domain business rule: Auto-assign track number if not set
        if track.track_number <= 0:
            max_number = max([t.track_number for t in self.tracks], default=0)
            track.track_number = max_number + 1

        self.tracks.append(track)
        # Domain business rule: Sort tracks by number
        self.tracks.sort(key=lambda t: t.track_number)

    def remove_track(self, track_number: int) -> Optional[Track]:
        """Domain behavior: Remove a track by number and return it.

        Business rule: Reindex remaining tracks after removal.

        Args:
            track_number: Number of the track to remove

        Returns:
            The removed track or None if not found
        """
        track = self.get_track(track_number)
        if track:
            self.tracks.remove(track)
            # Domain business rule: Reindex remaining tracks
            for i, t in enumerate(sorted(self.tracks, key=lambda x: x.track_number), 1):
                t.track_number = i
        return track

    def __len__(self) -> int:
        """Return the number of tracks in the playlist."""
        return len(self.tracks)

    def get_first_track(self) -> Optional[Track]:
        """Domain service: Get the first track in the playlist.

        This method returns the track at position 0 in the sorted track list,
        regardless of its track_number value. Handles non-sequential numbering.

        Returns:
            The first track or None if playlist is empty
        """
        if not self.tracks:
            return None
        # Sort tracks by track number and return the first one
        sorted_tracks = sorted(self.tracks, key=lambda t: t.track_number)
        return sorted_tracks[0]

    def get_track_by_position(self, position: int) -> Optional[Track]:
        """Domain service: Get track by position (0-based index) in sorted track list.

        Args:
            position: 0-based position in the sorted track list

        Returns:
            The track at that position or None if out of bounds
        """
        if not self.tracks or position < 0 or position >= len(self.tracks):
            return None
        sorted_tracks = sorted(self.tracks, key=lambda t: t.track_number)
        return sorted_tracks[position]

    def get_track_numbers(self) -> List[int]:
        """Domain service: Get all track numbers in sorted order.

        Returns:
            List of track numbers sorted in ascending order
        """
        return sorted([t.track_number for t in self.tracks])

    def has_track_number(self, number: int) -> bool:
        """Domain query: Check if a track with the given number exists.

        Args:
            number: Track number to check

        Returns:
            True if track exists, False otherwise
        """
        return self.get_track(number) is not None

    def normalize_track_numbers(self) -> None:
        """Domain behavior: Normalize track numbers to start from 1 and be sequential.

        Business rule: Reorder all tracks to have sequential numbers starting from 1,
        preserving the original track order based on their current track_number.
        """
        if not self.tracks:
            return

        # Sort tracks by current track number and assign new sequential numbers
        sorted_tracks = sorted(self.tracks, key=lambda t: t.track_number)
        for i, track in enumerate(sorted_tracks, 1):
            track.track_number = i

    def get_min_track_number(self) -> Optional[int]:
        """Domain query: Get the minimum track number in the playlist.

        Returns:
            The minimum track number or None if playlist is empty
        """
        if not self.tracks:
            return None
        return min(t.track_number for t in self.tracks)

    def get_max_track_number(self) -> Optional[int]:
        """Domain query: Get the maximum track number in the playlist.

        Returns:
            The maximum track number or None if playlist is empty
        """
        if not self.tracks:
            return None
        return max(t.track_number for t in self.tracks)

    def is_empty(self) -> bool:
        """Domain query: Check if playlist has no tracks.

        Returns:
            True if playlist is empty, False otherwise
        """
        return len(self.tracks) == 0

    def is_valid(self) -> bool:
        """Domain business rule: Check if playlist is valid.

        Returns:
            True if playlist has valid data, False otherwise
        """
        return bool(self.title.strip()) and all(track.is_valid() for track in self.tracks)

    def get_total_duration_ms(self) -> Optional[int]:
        """Domain service: Calculate total duration of all tracks.

        Returns:
            Total duration in milliseconds, None if any track duration is unknown
        """
        durations = [track.duration_ms for track in self.tracks if track.duration_ms is not None]
        if len(durations) != len(self.tracks):
            return None  # Some tracks have unknown duration
        return sum(durations)

    def get_display_name(self) -> str:
        """Domain service: Get formatted display title.

        Returns:
            Formatted title for display purposes
        """
        track_count = len(self.tracks)
        if track_count == 0:
            return f"{self.title} (empty)"
        return f"{self.title} ({track_count} tracks)"
