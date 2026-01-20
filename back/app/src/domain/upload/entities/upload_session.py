# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Upload Session Domain Entity."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.src.domain.base.base_session_entity import BaseSessionEntity

from ..value_objects.file_chunk import FileChunk
from ..value_objects.file_metadata import FileMetadata


class UploadStatus(Enum):
    """Status of an upload session."""

    PENDING = "pending"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class UploadSession(BaseSessionEntity):
    """Domain entity for managing file upload sessions.

    Handles the lifecycle of chunked file uploads, tracking progress,
    validation, and completion status.

    Inherits common session patterns from BaseSessionEntity.
    """

    filename: str = ""
    playlist_id: str | None = None
    playlist_path: str | None = None
    total_chunks: int = 0
    total_size_bytes: int = 0
    chunk_size: int = 0
    file_hash: str | None = None
    status: UploadStatus = UploadStatus.PENDING
    completed_at: datetime | None = None
    received_chunks: set[int] = field(default_factory=set)
    current_size_bytes: int = 0
    file_metadata: FileMetadata | None = None
    error_message: str | None = None
    timeout_seconds: int = 3600  # 1 hour default (override base class)
    completion_data: dict[str, Any] | None = None

    def __post_init__(self):
        """Validate session on creation."""
        if not self.filename:
            raise ValueError("Filename is required for upload session")
        if self.total_chunks <= 0:
            raise ValueError("Total chunks must be positive")
        if self.total_size_bytes <= 0:
            raise ValueError("Total size must be positive")

    @property
    def progress_percentage(self) -> float:
        """Calculate upload progress as percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (len(self.received_chunks) / self.total_chunks) * 100.0

    @property
    def size_progress_percentage(self) -> float:
        """Calculate size-based progress as percentage."""
        if self.total_size_bytes == 0:
            return 0.0
        return (self.current_size_bytes / self.total_size_bytes) * 100.0

    def is_active(self) -> bool:
        """Check if this session is active (not completed/failed/expired)."""
        return (
            self.status in [UploadStatus.PENDING, UploadStatus.UPLOADING]
            and not self.is_expired()
        )

    def is_complete(self) -> bool:
        """Check if all chunks have been received."""
        return len(self.received_chunks) == self.total_chunks

    def add_chunk(self, chunk: FileChunk) -> None:
        """Add a chunk to this session.

        Args:
            chunk: File chunk to add

        Raises:
            ValueError: If session is not active or chunk is invalid
        """
        if not self.is_active():
            raise ValueError("Cannot add chunk to inactive session")

        if chunk.index < 0 or chunk.index >= self.total_chunks:
            raise ValueError(f"Chunk index {chunk.index} out of range")

        if chunk.index in self.received_chunks:
            raise ValueError(f"Chunk {chunk.index} already received")

        # Update session state
        self.received_chunks.add(chunk.index)
        self.current_size_bytes += chunk.size

        # Update status
        if self.status == UploadStatus.PENDING:
            self.status = UploadStatus.UPLOADING

        # Check if complete
        if self.is_complete():
            self.mark_completed()

    def mark_completed(self) -> None:
        """Mark this session as completed."""
        if not self.is_complete():
            raise ValueError("Cannot mark incomplete session as completed")

        self.status = UploadStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def mark_failed(self, error_message: str) -> None:
        """Mark this session as failed.

        Args:
            error_message: Description of the failure
        """
        self.status = UploadStatus.ERROR
        self.error_message = error_message
        self.completed_at = datetime.now(UTC)

    def set_metadata(self, metadata: FileMetadata) -> None:
        """Set file metadata for this session.

        Args:
            metadata: File metadata
        """
        self.file_metadata = metadata

    def get_missing_chunks(self) -> set[int]:
        """Get set of missing chunk indices."""
        all_chunks = set(range(self.total_chunks))
        return all_chunks - self.received_chunks

    def validate_chunk_size_consistency(self, expected_size: int) -> bool:
        """Validate that current size matches expected size.

        Args:
            expected_size: Expected total size based on chunks

        Returns:
            True if sizes match
        """
        return self.current_size_bytes == expected_size

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary for serialization."""
        # Start with base class common fields
        result = self._base_dict_fields()

        # Add domain-specific fields
        result.update({
            "filename": self.filename,
            "playlist_id": self.playlist_id,
            "status": self.status.value,
            "progress_percentage": round(self.progress_percentage, 2),
            "size_progress_percentage": round(self.size_progress_percentage, 2),
            "total_chunks": self.total_chunks,
            "received_chunks": len(self.received_chunks),
            "missing_chunks": len(self.get_missing_chunks()),
            "total_size_bytes": self.total_size_bytes,
            "current_size_bytes": self.current_size_bytes,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "file_metadata": self.file_metadata.to_dict() if self.file_metadata else None,
            "error_message": self.error_message,
            "completion_data": self.completion_data,
        })

        return result
