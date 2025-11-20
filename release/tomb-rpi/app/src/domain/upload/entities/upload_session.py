# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Upload Session Domain Entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Set, Optional, Dict, Any
from uuid import uuid4

from ..value_objects.file_chunk import FileChunk
from ..value_objects.file_metadata import FileMetadata


class UploadStatus(Enum):
    """Status of an upload session."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class UploadSession:
    """Domain entity for managing file upload sessions.

    Handles the lifecycle of chunked file uploads, tracking progress,
    validation, and completion status.
    """

    session_id: str = field(default_factory=lambda: str(uuid4()))
    filename: str = ""
    playlist_id: Optional[str] = None
    playlist_path: Optional[str] = None
    total_chunks: int = 0
    total_size_bytes: int = 0
    status: UploadStatus = UploadStatus.CREATED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    received_chunks: Set[int] = field(default_factory=set)
    current_size_bytes: int = 0
    file_metadata: Optional[FileMetadata] = None
    error_message: Optional[str] = None
    timeout_seconds: int = 3600  # 1 hour default
    completion_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate session on creation."""
        if not self.filename:
            raise ValueError("Filename is required for upload session")
        if self.total_chunks <= 0:
            raise ValueError("Total chunks must be positive")
        if self.total_size_bytes <= 0:
            raise ValueError("Total size must be positive")

    @property
    def timeout_at(self) -> datetime:
        """Calculate when this session expires."""
        return datetime.fromtimestamp(
            self.created_at.timestamp() + self.timeout_seconds, tz=timezone.utc
        )

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

    def is_expired(self) -> bool:
        """Check if this session has expired."""
        return datetime.now(timezone.utc) > self.timeout_at

    def is_active(self) -> bool:
        """Check if this session is active (not completed/failed/expired)."""
        return (
            self.status in [UploadStatus.CREATED, UploadStatus.IN_PROGRESS]
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
        if self.status == UploadStatus.CREATED:
            self.status = UploadStatus.IN_PROGRESS

        # Check if complete
        if self.is_complete():
            self.mark_completed()

    def mark_completed(self) -> None:
        """Mark this session as completed."""
        if not self.is_complete():
            raise ValueError("Cannot mark incomplete session as completed")

        self.status = UploadStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(self, error_message: str) -> None:
        """Mark this session as failed.

        Args:
            error_message: Description of the failure
        """
        self.status = UploadStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        """Mark this session as cancelled."""
        self.status = UploadStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)

    def mark_expired(self) -> None:
        """Mark this session as expired."""
        self.status = UploadStatus.EXPIRED
        self.completed_at = datetime.now(timezone.utc)

    def set_metadata(self, metadata: FileMetadata) -> None:
        """Set file metadata for this session.

        Args:
            metadata: File metadata
        """
        self.file_metadata = metadata

    def get_missing_chunks(self) -> Set[int]:
        """Get set of missing chunk indices."""
        all_chunks = set(range(self.total_chunks))
        return all_chunks - self.received_chunks

    def get_remaining_seconds(self) -> int:
        """Get remaining seconds before timeout."""
        if self.is_expired():
            return 0

        remaining = self.timeout_at - datetime.now(timezone.utc)
        return max(0, int(remaining.total_seconds()))

    def validate_chunk_size_consistency(self, expected_size: int) -> bool:
        """Validate that current size matches expected size.

        Args:
            expected_size: Expected total size based on chunks

        Returns:
            True if sizes match
        """
        return self.current_size_bytes == expected_size

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
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
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "remaining_seconds": self.get_remaining_seconds(),
            "file_metadata": self.file_metadata.to_dict() if self.file_metadata else None,
            "error_message": self.error_message,
            "completion_data": self.completion_data,
        }
