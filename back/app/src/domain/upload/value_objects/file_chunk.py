# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""File Chunk Value Object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FileChunk:
    """Value object representing a chunk of file data.

    Immutable representation of a file chunk with validation.
    """

    index: int
    data: bytes
    size: int
    checksum: str = ""

    def __post_init__(self):
        """Validate chunk on creation."""
        if self.index < 0:
            raise ValueError("Chunk index cannot be negative")
        if self.size < 0:
            raise ValueError("Chunk size cannot be negative")
        if self.size != len(self.data):
            raise ValueError("Chunk size does not match data length")
        if self.size == 0:
            raise ValueError("Chunk cannot be empty")

    @classmethod
    def create(cls, index: int, data: bytes, checksum: str = "") -> "FileChunk":
        """Create a file chunk with automatic size calculation.

        Args:
            index: Chunk index in sequence
            data: Chunk data bytes
            checksum: Optional checksum for validation

        Returns:
            FileChunk instance
        """
        return cls(index=index, data=data, size=len(data), checksum=checksum)

    def is_valid_size(self, max_chunk_size: int) -> bool:
        """Check if chunk size is within limits.

        Args:
            max_chunk_size: Maximum allowed chunk size

        Returns:
            True if chunk size is valid
        """
        return 0 < self.size <= max_chunk_size

    def get_data_preview(self, preview_length: int = 32) -> str:
        """Get a hex preview of chunk data for debugging.

        Args:
            preview_length: Number of bytes to preview

        Returns:
            Hex string representation of data preview
        """
        preview_data = self.data[:preview_length]
        return preview_data.hex()

    def __str__(self) -> str:
        """String representation of chunk."""
        return f"Chunk({self.index}, {self.size} bytes)"
