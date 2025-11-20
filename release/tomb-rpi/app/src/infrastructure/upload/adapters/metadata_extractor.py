# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Metadata Extraction Adapter Implementation."""

import mimetypes
from pathlib import Path
from typing import List, Optional

from mutagen import File as MutagenFile
from mutagen.id3 import ID3NoHeaderError

from app.src.domain.upload.protocols.file_storage_protocol import MetadataExtractionProtocol
from app.src.domain.upload.value_objects.file_metadata import FileMetadata
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors

logger = get_logger(__name__)


class MutagenMetadataExtractor(MetadataExtractionProtocol):
    """Metadata extraction using Mutagen library.

    Extracts audio metadata from various audio formats using Mutagen.
    """

    def __init__(self):
        """Initialize metadata extractor."""
        self._supported_formats = {"mp3", "wav", "flac", "ogg", "oga", "m4a", "aac", "wma"}

    @handle_errors("extract_metadata")
    async def extract_metadata(self, file_path: Path) -> FileMetadata:
        """Extract metadata from audio file.

        Args:
            file_path: Path to audio file

        Returns:
            Extracted file metadata
        """
        # Get basic file info
        stat = file_path.stat()
        mime_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        # Create minimal metadata first
        metadata = FileMetadata.create_minimal(
            filename=file_path.name, size_bytes=stat.st_size, mime_type=mime_type
        )
        # Try to extract audio metadata
        try:
            audio_file = MutagenFile(str(file_path))
            if audio_file is not None:
                metadata = self._extract_audio_metadata(audio_file, metadata)
            else:
                logger.warning(f"⚠️ Could not read audio metadata from {file_path}")
        except (ID3NoHeaderError, Exception) as e:
            logger.warning(f"⚠️ Error extracting metadata from {file_path}: {e}")

        return metadata

    def _extract_audio_metadata(
        self, audio_file: MutagenFile, base_metadata: FileMetadata
    ) -> FileMetadata:
        """Extract audio-specific metadata from Mutagen file.

        Args:
            audio_file: Mutagen audio file object
            base_metadata: Base metadata to enhance

        Returns:
            Enhanced metadata with audio information
        """
        # Extract basic audio info
        duration_seconds = getattr(audio_file, "info", None)
        if duration_seconds:
            duration_seconds = getattr(duration_seconds, "length", None)

        bitrate = None
        sample_rate = None
        if hasattr(audio_file, "info"):
            bitrate = getattr(audio_file.info, "bitrate", None)
            sample_rate = getattr(audio_file.info, "sample_rate", None)

        # Extract tags
        title = self._get_tag_value(audio_file, ["TIT2", "TITLE", "\\xa9nam"])
        artist = self._get_tag_value(audio_file, ["TPE1", "ARTIST", "\\xa9ART"])
        album = self._get_tag_value(audio_file, ["TALB", "ALBUM", "\\xa9alb"])

        # Get extra attributes
        extra_attributes = {}
        if hasattr(audio_file, "tags") and audio_file.tags:
            for key, value in audio_file.tags.items():
                if isinstance(value, list) and len(value) == 1:
                    extra_attributes[str(key)] = str(value[0])
                else:
                    extra_attributes[str(key)] = str(value)

        # Create enhanced metadata
        return FileMetadata(
            filename=base_metadata.filename,
            size_bytes=base_metadata.size_bytes,
            mime_type=base_metadata.mime_type,
            title=title,
            artist=artist,
            album=album,
            duration_seconds=duration_seconds,
            bitrate=bitrate,
            sample_rate=sample_rate,
            extra_attributes=extra_attributes,
        )

    def _get_tag_value(self, audio_file: MutagenFile, tag_keys: List[str]) -> Optional[str]:
        """Get tag value trying multiple possible keys.

        Args:
            audio_file: Mutagen audio file object
            tag_keys: List of possible tag keys to try

        Returns:
            Tag value if found, None otherwise
        """
        if not hasattr(audio_file, "tags") or not audio_file.tags:
            return None

        for tag_key in tag_keys:
            try:
                value = audio_file.tags.get(tag_key)
                if value:
                    if isinstance(value, list):
                        return str(value[0]) if value else None
                    return str(value)
            except (KeyError, AttributeError):
                continue

        return None

    def get_supported_formats(self) -> List[str]:
        """Get list of supported audio formats.

        Returns:
            List of supported file extensions
        """
        return sorted(list(self._supported_formats))

    @handle_errors("validate_audio_file")
    async def validate_audio_file(self, file_path: Path) -> bool:
        """Validate that file is a proper audio file.

        Args:
            file_path: Path to file to validate

        Returns:
            True if file is valid audio
        """
        # Check file extension
        extension = file_path.suffix.lower().lstrip(".")
        if extension not in self._supported_formats:
            return False
        # Try to load with Mutagen
        audio_file = MutagenFile(str(file_path))
        if audio_file is None:
            return False
        # Check if it has audio info
        if not hasattr(audio_file, "info"):
            return False
        # Check duration is reasonable (> 0)
        duration = getattr(audio_file.info, "length", 0)
        if duration <= 0:
            return False
        logger.debug(f"✅ Audio file validation passed: {file_path.name}")
        return True


class MockMetadataExtractor(MetadataExtractionProtocol):
    """Mock metadata extractor for testing."""

    def __init__(self):
        """Initialize mock extractor."""
        self._supported_formats = ["mp3", "wav", "flac"]

    async def extract_metadata(self, file_path: Path) -> FileMetadata:
        """Extract mock metadata."""
        try:
            stat = file_path.stat()
            size_bytes = stat.st_size
        except Exception:
            size_bytes = 1024  # Mock size

        return FileMetadata(
            filename=file_path.name,
            size_bytes=size_bytes,
            mime_type="audio/mpeg",
            title=f"Mock Title for {file_path.stem}",
            artist="Mock Artist",
            album="Mock Album",
            duration_seconds=180.0,  # 3 minutes
            bitrate=192,
            sample_rate=44100,
        )

    def get_supported_formats(self) -> List[str]:
        """Get mock supported formats."""
        return self._supported_formats.copy()

    async def validate_audio_file(self, file_path: Path) -> bool:
        """Mock validation - always returns True."""
        extension = file_path.suffix.lower().lstrip(".")
        return extension in self._supported_formats
