# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Upload Factory for creating configured upload services."""

from typing import Optional

from app.src.domain.upload.services.upload_validation_service import UploadValidationService
# UploadApplicationService moved to Application layer - use ApplicationContainer
from .adapters.file_storage_adapter import LocalFileStorageAdapter
from .adapters.metadata_extractor import MutagenMetadataExtractor, MockMetadataExtractor


class UploadFactory:
    """Factory for creating upload services with proper dependency injection."""

    @staticmethod
    def create_upload_infrastructure_components(
        upload_folder: str = "uploads",
        temp_folder: str = "temp_uploads",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        use_mock_metadata: bool = False,
    ) -> tuple:
        """Create infrastructure components for upload services.

        Args:
            upload_folder: Folder for final uploaded files
            temp_folder: Folder for temporary upload chunks
            max_file_size: Maximum file size in bytes
            use_mock_metadata: Use mock metadata extractor for testing

        Returns:
            Tuple of (file_storage, metadata_extractor, validation_service, upload_folder)
        """
        # Create file storage adapter
        file_storage = LocalFileStorageAdapter(temp_folder)

        # Create metadata extractor
        if use_mock_metadata:
            metadata_extractor = MockMetadataExtractor()
        else:
            metadata_extractor = MutagenMetadataExtractor()

        # Create validation service
        validation_service = UploadValidationService(
            max_file_size=max_file_size,
            allowed_extensions=set(metadata_extractor.get_supported_formats()),
        )

        return file_storage, metadata_extractor, validation_service, upload_folder

    @staticmethod
    def create_mock_upload_components() -> tuple:
        """Create upload infrastructure components with mock implementations for testing.

        Returns:
            Upload infrastructure components with mock implementations
        """
        return UploadFactory.create_upload_infrastructure_components(
            upload_folder="test_uploads", temp_folder="test_temp", use_mock_metadata=True
        )
