# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Upload Validation Domain Service."""

from typing import Dict, List, Set
from pathlib import Path

from ..entities.upload_session import UploadSession
from ..value_objects.file_chunk import FileChunk
from ..value_objects.file_metadata import FileMetadata
import logging

logger = logging.getLogger(__name__)


class UploadValidationService:
    """Domain service for upload validation business logic.

    Handles validation rules for file uploads, chunk consistency,
    and upload session integrity according to business requirements.
    """

    def __init__(
        self,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        max_chunk_size: int = 1024 * 1024,  # 1MB
        allowed_extensions: Set[str] = None,
        min_audio_duration: float = 1.0,  # 1 second minimum
    ):
        """Initialize validation service with business rules.

        Args:
            max_file_size: Maximum allowed file size in bytes
            max_chunk_size: Maximum allowed chunk size in bytes
            allowed_extensions: Set of allowed file extensions
            min_audio_duration: Minimum audio duration in seconds
        """
        self.max_file_size = max_file_size
        self.max_chunk_size = max_chunk_size
        self.allowed_extensions = allowed_extensions or {"mp3", "wav", "flac", "ogg", "m4a", "aac"}
        self.min_audio_duration = min_audio_duration

    def validate_upload_request(
        self, filename: str, total_size: int, total_chunks: int, playlist_id: str = None
    ) -> Dict[str, any]:
        """Validate an upload request before creating session.

        Args:
            filename: Name of file to upload
            total_size: Total file size in bytes
            total_chunks: Number of chunks expected
            playlist_id: Optional playlist ID for association

        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []

        # Validate filename
        if not filename or not filename.strip():
            errors.append("Filename cannot be empty")
        else:
            filename_result = self._validate_filename(filename)
            errors.extend(filename_result.get("errors", []))
            warnings.extend(filename_result.get("warnings", []))

        # Validate file size
        if total_size <= 0:
            errors.append("File size must be positive")
        elif total_size > self.max_file_size:
            errors.append(
                f"File size ({total_size:,} bytes) exceeds maximum allowed size ({self.max_file_size:,} bytes)"
            )

        # Validate chunk count
        if total_chunks <= 0:
            errors.append("Chunk count must be positive")
        elif total_chunks > 10000:  # Reasonable upper limit
            errors.append("Too many chunks (maximum 10,000)")

        # Validate chunk size consistency
        if total_chunks > 0 and total_size > 0:
            avg_chunk_size = total_size / total_chunks
            if avg_chunk_size > self.max_chunk_size:
                errors.append(
                    f"Average chunk size ({avg_chunk_size:,.0f} bytes) exceeds maximum ({self.max_chunk_size:,} bytes)"
                )

        # Validate playlist ID if provided
        if playlist_id is not None and not playlist_id.strip():
            errors.append("Playlist ID cannot be empty if provided")

        is_valid = len(errors) == 0

        (logger.info if is_valid else logger.warning)(
            f"Upload validation for {filename}: {'✅ Valid' if is_valid else '❌ Invalid'}"
        )

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "filename": filename,
            "total_size": total_size,
            "total_chunks": total_chunks,
        }

    def validate_chunk(self, chunk: FileChunk, session: UploadSession) -> Dict[str, any]:
        """Validate a file chunk against session constraints.

        Args:
            chunk: File chunk to validate
            session: Upload session context

        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []

        # Validate chunk index
        if chunk.index < 0:
            errors.append("Chunk index cannot be negative")
        elif chunk.index >= session.total_chunks:
            errors.append(
                f"Chunk index {chunk.index} exceeds session total chunks {session.total_chunks}"
            )

        # Validate chunk size
        if not chunk.is_valid_size(self.max_chunk_size):
            errors.append(f"Chunk size {chunk.size} exceeds maximum {self.max_chunk_size}")

        # Check for duplicate chunks
        if chunk.index in session.received_chunks:
            warnings.append(f"Chunk {chunk.index} was already received (duplicate)")

        # Validate session state
        if not session.is_active():
            errors.append(
                f"Session {session.session_id} is not active (status: {session.status.value})"
            )

        # Check total size consistency
        projected_size = session.current_size_bytes + chunk.size
        if projected_size > session.total_size_bytes:
            errors.append(
                f"Adding chunk would exceed total file size ({projected_size} > {session.total_size_bytes})"
            )

        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "chunk_index": chunk.index,
            "chunk_size": chunk.size,
        }

    def validate_session_completion(self, session: UploadSession) -> Dict[str, any]:
        """Validate that a session is ready for completion.

        Args:
            session: Upload session to validate

        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []

        # Check all chunks received
        if not session.is_complete():
            missing_chunks = session.get_missing_chunks()
            errors.append(
                f"Missing {len(missing_chunks)} chunks: {sorted(list(missing_chunks))[:10]}..."
            )

        # Check size consistency
        if session.current_size_bytes != session.total_size_bytes:
            errors.append(
                f"Size mismatch: received {session.current_size_bytes}, expected {session.total_size_bytes}"
            )

        # Check session not expired
        if session.is_expired():
            errors.append("Session has expired")

        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "progress": session.progress_percentage,
        }

    def validate_audio_metadata(self, metadata: FileMetadata) -> Dict[str, any]:
        """Validate audio file metadata against business rules.

        Args:
            metadata: File metadata to validate

        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []

        # Check if it's an audio file
        if not metadata.is_audio_file():
            errors.append(f"File type {metadata.mime_type} is not an audio format")

        # Check file extension
        if not metadata.is_supported_format(self.allowed_extensions):
            errors.append(f"File extension {metadata.file_extension} is not supported")

        # Check minimum duration
        if metadata.duration_seconds is not None:
            if metadata.duration_seconds < self.min_audio_duration:
                errors.append(
                    f"Audio duration ({metadata.duration_seconds:.1f}s) is too short (minimum {self.min_audio_duration}s)"
                )
        else:
            warnings.append("Audio duration could not be determined")

        # Check for missing essential metadata
        if not metadata.title:
            warnings.append("Audio title is missing")
        if not metadata.artist:
            warnings.append("Audio artist is missing")

        # Check bitrate (if available)
        if metadata.bitrate is not None:
            if metadata.bitrate < 64:  # Very low quality
                warnings.append(f"Audio bitrate ({metadata.bitrate} kbps) is very low")
            elif metadata.bitrate > 320:  # Unusually high
                warnings.append(f"Audio bitrate ({metadata.bitrate} kbps) is unusually high")

        is_valid = len(errors) == 0

        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "has_complete_metadata": metadata.has_complete_metadata(),
        }

    def _validate_filename(self, filename: str) -> Dict[str, List[str]]:
        """Validate filename according to business rules.

        Args:
            filename: Filename to validate

        Returns:
            Dictionary with errors and warnings
        """
        errors = []
        warnings = []

        # Check file extension
        file_path = Path(filename)
        extension = file_path.suffix.lower().lstrip(".")

        if not extension:
            errors.append("File must have an extension")
        elif extension not in self.allowed_extensions:
            errors.append(
                f"File extension '{extension}' is not allowed. Supported: {', '.join(sorted(self.allowed_extensions))}"
            )

        # Check filename length
        if len(filename) > 255:
            errors.append("Filename is too long (maximum 255 characters)")

        # Check for problematic characters
        problematic_chars = ["<", ">", ":", '"', "|", "?", "*"]
        if any(char in filename for char in problematic_chars):
            warnings.append("Filename contains potentially problematic characters")

        # Check for reserved names (Windows)
        reserved_names = {
            "CON",
            "PRN",
            "AUX",
            "NUL",
            "COM1",
            "COM2",
            "COM3",
            "COM4",
            "COM5",
            "COM6",
            "COM7",
            "COM8",
            "COM9",
            "LPT1",
            "LPT2",
            "LPT3",
            "LPT4",
            "LPT5",
            "LPT6",
            "LPT7",
            "LPT8",
            "LPT9",
        }
        if file_path.stem.upper() in reserved_names:
            errors.append(f"'{file_path.stem}' is a reserved filename")

        return {"errors": errors, "warnings": warnings}
