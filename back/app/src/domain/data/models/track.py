# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Track domain entity following Domain-Driven Design principles."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Track:
    """Domain entity representing an audio track in a playlist.

    This is a core domain entity that encapsulates the business logic
    and rules related to audio tracks.

    Attributes:
        track_number: Position in the playlist (1-based) - per OpenAPI contract v4.0.0
        title: Title of the track
        filename: Filename of the track
        file_path: String path to the track file - aligned with frontend
        duration_ms: Optional duration in milliseconds
        artist: Optional artist name
        album: Optional album name
        id: Optional unique identifier
    """

    track_number: int  # Position in playlist - per OpenAPI contract v4.0.0
    title: str
    filename: str
    file_path: str  # Changed from Path to string to align with frontend
    duration_ms: int | None = None  # Duration in milliseconds
    artist: str | None = None
    album: str | None = None
    id: str | None = None

    @property
    def path(self) -> Path:
        """API compatibility property for file system operations."""
        return Path(self.file_path)

    @property
    def exists(self) -> bool:
        """Domain business rule: Check if the track file exists."""
        return self.path.exists()

    @classmethod
    def from_file(cls, file_path: str, number: int = 1) -> "Track":
        """Domain factory method: Create a track from a file path.

        Args:
            file_path: Path to the audio file
            number: Position in the playlist (default: 1)

        Returns:
            A new Track domain entity
        """
        path = Path(file_path)
        return cls(
            track_number=number, title=path.stem, filename=path.name, file_path=str(path)
        )

    def __str__(self) -> str:
        """Domain representation of the track."""
        return f"{self.track_number}. {self.title}"

    def is_valid(self) -> bool:
        """Domain business rule: Check if track has valid data."""
        return (
            self.track_number > 0
            and bool(self.title.strip())
            and bool(self.filename.strip())
            and bool(self.file_path.strip())
        )

    def get_display_name(self) -> str:
        """Domain service: Get formatted display name."""
        if self.artist:
            return f"{self.artist} - {self.title}"
        return self.title
