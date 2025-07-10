# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

from pathlib import Path
from typing import Dict, Tuple

from mutagen import File as MutagenFile
from mutagen.easyid3 import EasyID3
from werkzeug.utils import secure_filename

from app.src.helpers.exceptions import InvalidFileError, ProcessingError
from app.src.monitoring.improved_logger import ImprovedLogger, LogLevel

logger = ImprovedLogger(__name__)


class UploadService:
    """Service for handling audio file uploads and metadata extraction."""

    def __init__(self, config):
        """Initialize the UploadService with application config."""
        self.upload_folder = Path(config.upload_folder)
        self.allowed_extensions = set(config.upload_allowed_extensions)
        self.max_file_size = config.upload_max_size

    def _allowed_file(self, filename: str) -> bool:
        """Return True if the filename is an allowed audio type."""
        return (
            "." in filename
            and filename.rsplit(".", 1)[1].lower() in self.allowed_extensions
        )

    async def _check_file_size(self, file) -> bool:
        """Return True if the file size is within the allowed maximum."""
        # FastAPI UploadFile objects don't support seeking with whence parameter
        # We need to read the file content to determine its size
        content = await file.read()
        size = len(content)
        # Reset the file pointer for further processing
        await file.seek(0)
        return size <= self.max_file_size

    def extract_metadata(self, file_path: Path) -> Dict:
        """Extract metadata from an audio file.

        Args:
            file_path: Path to the audio file.

        Returns:
            Dictionary with metadata fields: title, artist, album, duration.
        """
        try:
            audio = MutagenFile(str(file_path), easy=True)
            if audio is None:
                audio = EasyID3(str(file_path))

            metadata = {
                "title": audio.get("title", [Path(file_path).stem])[0],
                "artist": audio.get("artist", ["Unknown"])[0],
                "album": audio.get("album", ["Unknown"])[0],
                "duration": audio.info.length if hasattr(audio.info, "length") else 0,
            }
            return metadata

        except Exception as e:
            logger.log(
                LogLevel.WARNING,
                f"Could not extract metadata from {file_path}: {str(e)}",
            )
            return {
                "title": Path(file_path).stem,
                "artist": "Unknown",
                "album": "Unknown",
                "duration": 0,
            }

    async def process_upload(self, file, playlist_path: str) -> Tuple[str, Dict]:
        """Process an uploaded file and extract its metadata.

        Args:
            file: The uploaded file object.
            playlist_path: Path to the playlist folder.

        Returns:
            Tuple of (filename, metadata dictionary).

        Raises:
            InvalidFileError: If the file is invalid or not allowed.
            ProcessingError: If there is an error during processing.
        """
        if not file or not file.filename:
            raise InvalidFileError("No file provided")

        if not self._allowed_file(file.filename):
            raise InvalidFileError(
                f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}"
            )

        if not await self._check_file_size(file):
            raise InvalidFileError(
                f"File too large. Maximum size: {self.max_file_size/1024/1024}MB"
            )

        # Secure the filename
        filename = secure_filename(file.filename)

        # Create the playlist folder if necessary
        upload_path = self.upload_folder / playlist_path
        try:
            upload_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.log(
                LogLevel.ERROR, f"Error creating directory {upload_path}: {str(e)}"
            )

        # Save the file
        file_path = upload_path / filename
        try:
            logger.log(LogLevel.INFO, f"Saving file to {file_path}")
            await file.seek(0)
            content = await file.read()
            with open(str(file_path), "wb") as f:
                f.write(content)

            logger.log(LogLevel.INFO, f"File saved successfully: {file_path}")
            metadata = self.extract_metadata(file_path)

            return filename, metadata

        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise ProcessingError(f"Error processing file: {str(e)}") from e

    def cleanup_failed_upload(self, playlist_path: str, filename: str):
        """Clean up files in case of failure.

        Args:
            playlist_path: Path to the playlist folder.
            filename: Name of the file to remove.
        """
        try:
            file_path = self.upload_folder / playlist_path / filename
            if file_path.exists():
                file_path.unlink()
        except OSError as e:
            logger.log(LogLevel.ERROR, f"Error cleaning up failed upload: {str(e)}")
