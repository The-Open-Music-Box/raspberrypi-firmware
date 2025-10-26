# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Audio File Domain Entity."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..value_objects.file_metadata import FileMetadata


@dataclass
class AudioFile:
    """Domain entity representing an uploaded audio file.

    Encapsulates audio file business logic and validation rules.
    """

    file_path: Path
    metadata: FileMetadata
    playlist_id: Optional[str] = None
    is_processed: bool = False
    processing_error: Optional[str] = None

    def __post_init__(self):
        """Validate audio file on creation."""
        if not self.file_path:
            raise ValueError("File path is required")
        if not self.metadata:
            raise ValueError("File metadata is required")
        if not self.metadata.is_audio_file():
            raise ValueError("File must be an audio file")

    @property
    def filename(self) -> str:
        """Get filename from path."""
        return self.file_path.name

    @property
    def file_exists(self) -> bool:
        """Check if file exists on filesystem."""
        return self.file_path.exists()

    @property
    def file_size_matches_metadata(self) -> bool:
        """Check if actual file size matches metadata."""
        if not self.file_exists:
            return False

        actual_size = self.file_path.stat().st_size
        return actual_size == self.metadata.size_bytes

    def mark_processed(self) -> None:
        """Mark this file as processed successfully."""
        self.is_processed = True
        self.processing_error = None

    def mark_processing_failed(self, error_message: str) -> None:
        """Mark this file as failed to process.

        Args:
            error_message: Description of processing error
        """
        self.is_processed = False
        self.processing_error = error_message

    def set_playlist(self, playlist_id: str) -> None:
        """Associate this file with a playlist.

        Args:
            playlist_id: ID of playlist to associate with

        Raises:
            ValueError: If playlist_id is invalid
        """
        if not playlist_id or not playlist_id.strip():
            raise ValueError("Playlist ID cannot be empty")

        self.playlist_id = playlist_id

    def is_valid_for_playlist(self) -> bool:
        """Check if file is valid for adding to playlist."""
        return (
            self.file_exists
            and self.file_size_matches_metadata
            and self.metadata.has_complete_metadata()
            and not self.processing_error
        )

    def get_track_info(self) -> dict:
        """Get track information for playlist integration."""
        return {
            "title": self.metadata.title or self.metadata.display_name,
            "artist": self.metadata.artist,
            "album": self.metadata.album,
            "filename": self.filename,
            "file_path": str(self.file_path),
            "duration_ms": (
                int(self.metadata.duration_seconds * 1000)
                if self.metadata.duration_seconds
                else None
            ),
            "size_bytes": self.metadata.size_bytes,
        }

    def validate_integrity(self) -> bool:
        """Validate file integrity and consistency.

        Returns:
            True if file is valid and consistent
        """
        checks = [self.file_exists, self.file_size_matches_metadata, self.metadata.is_audio_file()]

        return all(checks)

    def __str__(self) -> str:
        """String representation of audio file."""
        return f"AudioFile({self.filename}, {self.metadata.size_mb:.1f}MB)"
