# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
File Path Resolution Service

Centralized service for resolving track file paths, eliminating duplication
across AudioController methods and providing consistent path resolution logic.
"""

from pathlib import Path
from typing import List, Optional, Tuple
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = get_logger(__name__)


class FilePathResolver:
    """
    Service for resolving track file paths with fallback strategies.

    Handles path resolution for tracks with various filename formats and
    provides consistent fallback mechanisms when files are not found.
    """

    def __init__(self, uploads_dir: Path):
        """
        Initialize the file path resolver.

        Args:
            uploads_dir: Base directory for uploaded files
        """
        self.uploads_dir = Path(uploads_dir)

    @handle_service_errors("file_path_resolver")
    def resolve_track_path(self, track, playlist_title: str) -> Optional[Path]:
        """
        Resolve the path for a track file using multiple fallback strategies.

        Args:
            track: Track object with filename/path attributes
            playlist_title: Title of the playlist containing the track

        Returns:
            Path to the track file if found, None otherwise
        """
        if not hasattr(track, "filename") or not track.filename:
            logger.warning(f"Track {track.track_number} has no filename")
            return None

        possible_paths = self._generate_possible_paths(track, playlist_title)

        for path_candidate in possible_paths:
            path = Path(path_candidate)
            if path.exists() and path.is_file():
                logger.debug(f"Found track file at: {path}")
                return path
        # Log all attempted paths for debugging
        logger.warning(f"Track file not found. Attempted paths: {[str(p) for p in possible_paths]}",
        )
        return None

    def resolve_multiple_tracks(
        self, tracks, playlist_title: str
    ) -> List[Tuple[object, Optional[Path]]]:
        """
        Resolve paths for multiple tracks efficiently.

        Args:
            tracks: List of track objects
            playlist_title: Title of the playlist

        Returns:
            List of (track, resolved_path) tuples
        """
        results = []
        for track in tracks:
            resolved_path = self.resolve_track_path(track, playlist_title)
            results.append((track, resolved_path))

        return results

    def _generate_possible_paths(self, track, playlist_title: str) -> List[Path]:
        """
        Generate all possible paths for a track file.

        Args:
            track: Track object with filename
            playlist_title: Title of the playlist

        Returns:
            List of possible path candidates in priority order
        """
        filename = track.filename
        filename_only = Path(filename).name

        possible_paths = []

        # Strategy 1: Playlist-specific directory with filename only
        possible_paths.append(self.uploads_dir / playlist_title / filename_only)

        # Strategy 2: Root uploads directory with filename only
        possible_paths.append(self.uploads_dir / filename_only)

        # Strategy 3: Handle legacy path format conversion
        if "/home/admin/tomb/app/data/" in str(filename):
            converted_path = Path(
                str(filename).replace("/home/admin/tomb/app/data/", str(self.uploads_dir) + "/")
            )
            possible_paths.append(converted_path)

        # Strategy 4: Direct filename interpretation
        possible_paths.append(self.uploads_dir / filename)

        # Strategy 5: If filename is already a full path, try it directly
        if Path(filename).is_absolute():
            possible_paths.append(Path(filename))

        # Strategy 6: Try with playlist title as subdirectory of filename path
        if "/" in filename:
            filename_dir = Path(filename).parent
            possible_paths.append(self.uploads_dir / playlist_title / filename_dir / filename_only)

        return possible_paths

    @handle_service_errors("file_path_resolver")
    def validate_track_file(self, path: Path) -> bool:
        """
        Validate that a track file exists and is readable.

        Args:
            path: Path to validate

        Returns:
            True if file is valid, False otherwise
        """
        if not path.exists():
            return False
        if not path.is_file():
            logger.warning(f"Path is not a file: {path}")
            return False
        # Check if file is readable
        if not path.stat().st_size > 0:
            logger.warning(f"File is empty: {path}")
            return False
        return True

    def get_file_stats(self, path: Path) -> Optional[dict]:
        """
        Get file statistics for a track file.

        Args:
            path: Path to the file

        Returns:
            Dictionary with file stats or None if error
        """
        try:
            if not self.validate_track_file(path):
                return None

            stat = path.stat()
            return {
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "exists": True,
                "readable": True,
            }

        except (OSError, ValueError) as e:
            logger.warning(f"Error getting file stats for {path}: {e}")
            return None
