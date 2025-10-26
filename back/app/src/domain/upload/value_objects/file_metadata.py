# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""File Metadata Value Object."""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass(frozen=True)
class FileMetadata:
    """Value object representing audio file metadata.

    Immutable representation of extracted audio file information.
    """

    filename: str
    size_bytes: int
    mime_type: str
    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    duration_seconds: Optional[float] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    extra_attributes: Dict[str, Any] = None

    def __post_init__(self):
        """Validate metadata on creation."""
        if not self.filename:
            raise ValueError("Filename cannot be empty")
        if self.size_bytes < 0:
            raise ValueError("File size cannot be negative")
        if not self.mime_type:
            raise ValueError("MIME type is required")

        # Set default for mutable field
        if self.extra_attributes is None:
            object.__setattr__(self, "extra_attributes", {})

    @property
    def file_extension(self) -> str:
        """Get file extension from filename."""
        return Path(self.filename).suffix.lower()

    @property
    def display_name(self) -> str:
        """Get display name for UI (title or filename)."""
        return self.title or Path(self.filename).stem

    @property
    def size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.size_bytes / (1024 * 1024)

    @property
    def duration_formatted(self) -> str:
        """Get formatted duration string (MM:SS)."""
        if not self.duration_seconds:
            return "Unknown"

        minutes = int(self.duration_seconds // 60)
        seconds = int(self.duration_seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def is_audio_file(self) -> bool:
        """Check if this is an audio file based on MIME type."""
        return self.mime_type.startswith("audio/")

    def is_supported_format(self, supported_extensions: set) -> bool:
        """Check if file format is supported.

        Args:
            supported_extensions: Set of supported file extensions

        Returns:
            True if format is supported
        """
        return self.file_extension.lstrip(".") in supported_extensions

    def has_complete_metadata(self) -> bool:
        """Check if metadata has all basic audio information."""
        return all([self.title, self.artist, self.duration_seconds is not None])

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization."""
        return {
            "filename": self.filename,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_mb, 2),
            "mime_type": self.mime_type,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration_seconds": self.duration_seconds,
            "duration_formatted": self.duration_formatted,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "file_extension": self.file_extension,
            "display_name": self.display_name,
            "extra_attributes": dict(self.extra_attributes),
        }

    @classmethod
    def create_minimal(cls, filename: str, size_bytes: int, mime_type: str) -> "FileMetadata":
        """Create minimal metadata for basic file info.

        Args:
            filename: Name of the file
            size_bytes: Size in bytes
            mime_type: MIME type

        Returns:
            FileMetadata with minimal information
        """
        return cls(filename=filename, size_bytes=size_bytes, mime_type=mime_type)
