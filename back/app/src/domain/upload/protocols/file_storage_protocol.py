# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""File Storage Protocol Interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List

from ..value_objects.file_chunk import FileChunk
from ..entities.upload_session import UploadSession


class FileStorageProtocol(ABC):
    """Protocol for file storage operations.

    Defines the contract for file storage adapters, allowing different
    implementations (local filesystem, cloud storage, etc.).
    """

    @abstractmethod
    async def create_session_directory(self, session_id: str) -> Path:
        """Create directory for upload session.

        Args:
            session_id: Unique session identifier

        Returns:
            Path to created directory

        Raises:
            StorageError: If directory cannot be created
        """
        pass

    @abstractmethod
    async def store_chunk(self, session_id: str, chunk: FileChunk) -> None:
        """Store a file chunk.

        Args:
            session_id: Session identifier
            chunk: File chunk to store

        Raises:
            StorageError: If chunk cannot be stored
        """
        pass

    @abstractmethod
    async def assemble_file(self, session: UploadSession, output_path: Path) -> Path:
        """Assemble chunks into final file.

        Args:
            session: Upload session with chunk information
            output_path: Destination path for assembled file

        Returns:
            Path to assembled file

        Raises:
            StorageError: If assembly fails
        """
        pass

    @abstractmethod
    async def cleanup_session(self, session_id: str) -> None:
        """Clean up session temporary files.

        Args:
            session_id: Session to clean up
        """
        pass

    @abstractmethod
    async def get_chunk_info(self, session_id: str, chunk_index: int) -> Optional[dict]:
        """Get information about a stored chunk.

        Args:
            session_id: Session identifier
            chunk_index: Chunk index

        Returns:
            Chunk info dictionary or None if not found
        """
        pass

    @abstractmethod
    async def verify_file_integrity(self, file_path: Path, expected_size: int) -> bool:
        """Verify file integrity after assembly.

        Args:
            file_path: Path to file to verify
            expected_size: Expected file size in bytes

        Returns:
            True if file is valid
        """
        pass


class MetadataExtractionProtocol(ABC):
    """Protocol for audio metadata extraction."""

    @abstractmethod
    async def extract_metadata(self, file_path: Path) -> "FileMetadata":
        """Extract metadata from audio file.

        Args:
            file_path: Path to audio file

        Returns:
            Extracted file metadata

        Raises:
            MetadataExtractionError: If extraction fails
        """
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats.

        Returns:
            List of supported file extensions
        """
        pass

    @abstractmethod
    async def validate_audio_file(self, file_path: Path) -> bool:
        """Validate that file is a proper audio file.

        Args:
            file_path: Path to file to validate

        Returns:
            True if file is valid audio
        """
        pass
