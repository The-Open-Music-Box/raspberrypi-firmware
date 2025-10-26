# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
TrackResolver - Responsible for resolving track file paths.

Single responsibility: Convert track filenames to valid file paths.
"""

import os
from pathlib import Path
from typing import Optional, List
import logging
from app.src.config import config

logger = logging.getLogger(__name__)


class TrackResolver:
    """
    Resolves track file paths from filenames.

    This class is responsible for:
    - Finding track files in the upload directory
    - Validating file existence
    - Resolving relative paths to absolute paths
    """

    def __init__(self, upload_folder: Optional[str] = None):
        """
        Initialize the track resolver.

        Args:
            upload_folder: Base folder for track files (defaults to config)
        """
        self.upload_folder = upload_folder or config.upload_folder
        logger.info(f"✅ TrackResolver initialized with folder: {self.upload_folder}")

    def resolve_path(self, filename: str) -> Optional[str]:
        """
        Resolve a track filename to its full path.

        Args:
            filename: The filename to resolve

        Returns:
            Optional[str]: Full path to the file, or None if not found
        """
        if not filename:
            logger.warning("Cannot resolve empty filename")
            return None

        # If it's already an absolute path and exists, return it
        if os.path.isabs(filename):
            if os.path.exists(filename):
                logger.debug(f"Using absolute path: {filename}")
                return filename
            else:
                logger.warning(f"Absolute path not found: {filename}")
                return None

        # Try to resolve relative to upload folder
        full_path = os.path.join(self.upload_folder, filename)

        if os.path.exists(full_path):
            logger.debug(f"Resolved '{filename}' to: {full_path}")
            return full_path

        # Try with 'tracks' subdirectory
        tracks_path = os.path.join(self.upload_folder, "tracks", filename)
        if os.path.exists(tracks_path):
            logger.debug(f"Resolved '{filename}' to: {tracks_path}")
            return tracks_path

        # Try recursive search in subdirectories
        recursive_path = self._search_recursive(filename)
        if recursive_path:
            logger.debug(f"Resolved '{filename}' recursively to: {recursive_path}")
            return recursive_path

        # Try without extension
        base_name = os.path.splitext(filename)[0]
        for ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']:
            test_path = os.path.join(self.upload_folder, base_name + ext)
            if os.path.exists(test_path):
                logger.debug(f"Resolved '{filename}' to: {test_path}")
                return test_path

        logger.warning(f"Could not resolve path for: {filename}")
        return None

    def validate_path(self, file_path: str) -> bool:
        """
        Validate that a file path exists and is readable.

        Args:
            file_path: Path to validate

        Returns:
            bool: True if path is valid and readable
        """
        if not file_path:
            return False

        if not os.path.exists(file_path):
            logger.debug(f"Path does not exist: {file_path}")
            return False

        if not os.path.isfile(file_path):
            logger.debug(f"Path is not a file: {file_path}")
            return False

        if not os.access(file_path, os.R_OK):
            logger.warning(f"File is not readable: {file_path}")
            return False

        return True

    def _search_recursive(self, filename: str) -> Optional[str]:
        """
        Search for a filename recursively in upload folder subdirectories.

        Args:
            filename: The filename to search for

        Returns:
            Optional[str]: Full path if found, None otherwise
        """
        try:
            upload_path = Path(self.upload_folder)

            # Search recursively for the exact filename
            for file_path in upload_path.rglob(filename):
                if file_path.is_file():
                    logger.debug(f"Found '{filename}' at: {file_path}")
                    return str(file_path)

            # If not found, try searching without case sensitivity
            filename_lower = filename.lower()
            for file_path in upload_path.rglob("*"):
                if file_path.is_file() and file_path.name.lower() == filename_lower:
                    logger.debug(f"Found '{filename}' (case-insensitive) at: {file_path}")
                    return str(file_path)

        except Exception as e:
            logger.warning(f"Error during recursive search for '{filename}': {e}")

        return None

    def resolve_multiple(self, filenames: List[str]) -> List[Optional[str]]:
        """
        Resolve multiple track filenames.

        Args:
            filenames: List of filenames to resolve

        Returns:
            List[Optional[str]]: List of resolved paths (None for unresolved)
        """
        return [self.resolve_path(filename) for filename in filenames]

    def find_tracks_in_directory(self, directory: Optional[str] = None) -> List[str]:
        """
        Find all audio track files in a directory.

        Args:
            directory: Directory to search (defaults to upload folder)

        Returns:
            List[str]: List of found track file paths
        """
        search_dir = directory or self.upload_folder
        supported_extensions = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
        tracks = []

        try:
            for root, _, files in os.walk(search_dir):
                for file in files:
                    if Path(file).suffix.lower() in supported_extensions:
                        full_path = os.path.join(root, file)
                        tracks.append(full_path)

            logger.info(f"Found {len(tracks)} tracks in {search_dir}")
            return tracks

        except Exception as e:
            logger.error(f"Error scanning directory: {e}")
            return []

    def get_relative_path(self, full_path: str) -> str:
        """
        Get relative path from upload folder.

        Args:
            full_path: Full path to convert

        Returns:
            str: Relative path from upload folder
        """
        try:
            return os.path.relpath(full_path, self.upload_folder)
        except ValueError:
            # Paths on different drives (Windows) or other issues
            return full_path
