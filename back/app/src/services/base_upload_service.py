# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Base upload service with common functionality.

Extracted to eliminate duplication between UploadService and ChunkedUploadService.
"""



class BaseUploadService:
    """Base class for upload services with common file validation logic.

    Extracted to eliminate duplication of file validation logic between
    UploadService and ChunkedUploadService.
    """

    def __init__(self, allowed_extensions: set[str]):
        """Initialize base upload service.

        Args:
            allowed_extensions: Set of allowed file extensions (e.g., {'mp3', 'wav'})
        """
        self.allowed_extensions = allowed_extensions

    def _allowed_file(self, filename: str) -> bool:
        """Return True if the filename is an allowed audio type.

        Extracted helper to eliminate duplication across upload services.

        Args:
            filename: Name of the file to check

        Returns:
            True if file extension is in allowed_extensions, False otherwise
        """
        return "." in filename and filename.rsplit(".", 1)[1].lower() in self.allowed_extensions
