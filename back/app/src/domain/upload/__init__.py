# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Upload Domain Module.

Contains all domain entities, value objects, services and interfaces
for file upload management according to Domain-Driven Design principles.
"""

from .entities.audio_file import AudioFile
from .entities.upload_session import UploadSession, UploadStatus
from .protocols.file_storage_protocol import (
    FileStorageProtocol,
    MetadataExtractionProtocol,
)
from .services.upload_validation_service import UploadValidationService
from .value_objects.file_chunk import FileChunk
from .value_objects.file_metadata import FileMetadata

__all__ = [
    "AudioFile",
    "FileChunk",
    "FileMetadata",
    "FileStorageProtocol",
    "MetadataExtractionProtocol",
    "UploadSession",
    "UploadStatus",
    "UploadValidationService",
]
