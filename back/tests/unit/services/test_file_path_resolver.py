# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for FilePathResolver

Comprehensive tests for the file path resolution service including
path resolution strategies, validation, and file statistics.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import time

from app.src.services.file_path_resolver import FilePathResolver


class TestFilePathResolver:
    """Test suite for FilePathResolver."""

    @pytest.fixture
    def uploads_dir(self):
        """Mock uploads directory."""
        return Path("/tmp/test_uploads")

    @pytest.fixture
    def file_path_resolver(self, uploads_dir):
        """Create FilePathResolver instance."""
        return FilePathResolver(uploads_dir)

    # ================================================================================
    # Test __init__()
    # ================================================================================

    def test_init_with_path_object(self):
        """Test initialization with Path object."""
        # Arrange
        uploads_dir = Path("/tmp/uploads")

        # Act
        resolver = FilePathResolver(uploads_dir)

        # Assert
        assert resolver.uploads_dir == uploads_dir

    def test_init_with_string_path(self):
        """Test initialization with string path."""
        # Arrange
        uploads_dir = "/tmp/uploads"

        # Act
        resolver = FilePathResolver(uploads_dir)

        # Assert
        assert resolver.uploads_dir == Path(uploads_dir)

    # ================================================================================
    # Test resolve_track_path()
    # ================================================================================

    def test_resolve_track_path_success_playlist_dir(self, file_path_resolver):
        """Test successful path resolution in playlist directory."""
        # Arrange
        track = Mock()
        track.filename = "song.mp3"
        track.track_number = 1
        playlist_title = "My Playlist"

        expected_path = file_path_resolver.uploads_dir / playlist_title / "song.mp3"

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True):

            # Act
            result = file_path_resolver.resolve_track_path(track, playlist_title)

            # Assert
            assert result == expected_path

    def test_resolve_track_path_success_root_dir(self, file_path_resolver):
        """Test path resolution falling back to root uploads directory."""
        # Arrange
        track = Mock()
        track.filename = "song.mp3"
        track.track_number = 1
        playlist_title = "My Playlist"

        expected_path = file_path_resolver.uploads_dir / "song.mp3"

        def mock_exists(self):
            # Only root path exists
            return str(self) == str(expected_path)

        with patch.object(Path, 'exists', mock_exists), \
             patch.object(Path, 'is_file', return_value=True):

            # Act
            result = file_path_resolver.resolve_track_path(track, playlist_title)

            # Assert
            assert result == expected_path

    def test_resolve_track_path_no_filename(self, file_path_resolver):
        """Test path resolution when track has no filename."""
        # Arrange
        track = Mock()
        track.track_number = 1
        track.filename = None
        playlist_title = "My Playlist"

        # Act
        result = file_path_resolver.resolve_track_path(track, playlist_title)

        # Assert
        assert result is None

    def test_resolve_track_path_file_not_found(self, file_path_resolver):
        """Test path resolution when file doesn't exist."""
        # Arrange
        track = Mock()
        track.filename = "missing.mp3"
        track.track_number = 1
        playlist_title = "My Playlist"

        with patch.object(Path, 'exists', return_value=False):

            # Act
            result = file_path_resolver.resolve_track_path(track, playlist_title)

            # Assert
            assert result is None

    def test_resolve_track_path_legacy_format(self, file_path_resolver):
        """Test path resolution with legacy path format."""
        # Arrange
        track = Mock()
        track.filename = "/home/admin/tomb/app/data/uploads/music/song.mp3"
        track.track_number = 1
        playlist_title = "Music"

        expected_path = file_path_resolver.uploads_dir / "uploads/music/song.mp3"

        def mock_exists(self):
            return str(self) == str(expected_path)

        with patch.object(Path, 'exists', mock_exists), \
             patch.object(Path, 'is_file', return_value=True):

            # Act
            result = file_path_resolver.resolve_track_path(track, playlist_title)

            # Assert
            assert result == expected_path

    def test_resolve_track_path_absolute_path(self, file_path_resolver):
        """Test path resolution with absolute path."""
        # Arrange
        track = Mock()
        track.filename = "/absolute/path/to/song.mp3"
        track.track_number = 1
        playlist_title = "Music"

        expected_path = Path("/absolute/path/to/song.mp3")

        def mock_exists(self):
            return str(self) == str(expected_path)

        with patch.object(Path, 'exists', mock_exists), \
             patch.object(Path, 'is_file', return_value=True):

            # Act
            result = file_path_resolver.resolve_track_path(track, playlist_title)

            # Assert
            assert result == expected_path

    def test_resolve_track_path_with_subdirectory(self, file_path_resolver):
        """Test path resolution with filename containing subdirectory."""
        # Arrange
        track = Mock()
        track.filename = "subfolder/song.mp3"
        track.track_number = 1
        playlist_title = "My Playlist"

        expected_path = file_path_resolver.uploads_dir / "My Playlist" / "subfolder" / "song.mp3"

        def mock_exists(self):
            return str(self) == str(expected_path)

        with patch.object(Path, 'exists', mock_exists), \
             patch.object(Path, 'is_file', return_value=True):

            # Act
            result = file_path_resolver.resolve_track_path(track, playlist_title)

            # Assert
            assert result == expected_path

    # ================================================================================
    # Test resolve_multiple_tracks()
    # ================================================================================

    def test_resolve_multiple_tracks_success(self, file_path_resolver):
        """Test resolving multiple tracks successfully."""
        # Arrange
        track1 = Mock()
        track1.filename = "song1.mp3"
        track1.track_number = 1

        track2 = Mock()
        track2.filename = "song2.mp3"
        track2.track_number = 2

        tracks = [track1, track2]
        playlist_title = "My Playlist"

        path1 = file_path_resolver.uploads_dir / playlist_title / "song1.mp3"
        path2 = file_path_resolver.uploads_dir / playlist_title / "song2.mp3"

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True):

            # Act
            results = file_path_resolver.resolve_multiple_tracks(tracks, playlist_title)

            # Assert
            assert len(results) == 2
            assert results[0][0] == track1
            assert results[0][1] == path1
            assert results[1][0] == track2
            assert results[1][1] == path2

    def test_resolve_multiple_tracks_mixed_success(self, file_path_resolver):
        """Test resolving multiple tracks with some failures."""
        # Arrange
        track1 = Mock()
        track1.filename = "found.mp3"
        track1.track_number = 1

        track2 = Mock()
        track2.filename = None  # Will fail
        track2.track_number = 2

        tracks = [track1, track2]
        playlist_title = "My Playlist"

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True):

            # Act
            results = file_path_resolver.resolve_multiple_tracks(tracks, playlist_title)

            # Assert
            assert len(results) == 2
            assert results[0][0] == track1
            assert results[0][1] is not None  # First track resolved
            assert results[1][0] == track2
            assert results[1][1] is None  # Second track failed

    def test_resolve_multiple_tracks_empty_list(self, file_path_resolver):
        """Test resolving empty track list."""
        # Arrange
        tracks = []
        playlist_title = "My Playlist"

        # Act
        results = file_path_resolver.resolve_multiple_tracks(tracks, playlist_title)

        # Assert
        assert results == []

    # ================================================================================
    # Test _generate_possible_paths()
    # ================================================================================

    def test_generate_possible_paths_simple_filename(self, file_path_resolver):
        """Test path generation for simple filename."""
        # Arrange
        track = Mock()
        track.filename = "song.mp3"
        playlist_title = "My Playlist"

        # Act
        paths = file_path_resolver._generate_possible_paths(track, playlist_title)

        # Assert
        assert len(paths) >= 3
        assert file_path_resolver.uploads_dir / "My Playlist" / "song.mp3" in paths
        assert file_path_resolver.uploads_dir / "song.mp3" in paths

    def test_generate_possible_paths_legacy_format(self, file_path_resolver):
        """Test path generation includes legacy format conversion."""
        # Arrange
        track = Mock()
        track.filename = "/home/admin/tomb/app/data/music/song.mp3"
        playlist_title = "Music"

        # Act
        paths = file_path_resolver._generate_possible_paths(track, playlist_title)

        # Assert
        legacy_converted = file_path_resolver.uploads_dir / "music/song.mp3"
        assert legacy_converted in paths

    def test_generate_possible_paths_absolute_path(self, file_path_resolver):
        """Test path generation includes absolute path."""
        # Arrange
        track = Mock()
        track.filename = "/absolute/path/to/song.mp3"
        playlist_title = "Music"

        # Act
        paths = file_path_resolver._generate_possible_paths(track, playlist_title)

        # Assert
        assert Path("/absolute/path/to/song.mp3") in paths

    def test_generate_possible_paths_with_subdirectory(self, file_path_resolver):
        """Test path generation for filename with subdirectory."""
        # Arrange
        track = Mock()
        track.filename = "subfolder/song.mp3"
        playlist_title = "My Playlist"

        # Act
        paths = file_path_resolver._generate_possible_paths(track, playlist_title)

        # Assert
        assert file_path_resolver.uploads_dir / "My Playlist" / "subfolder" / "song.mp3" in paths

    # ================================================================================
    # Test validate_track_file()
    # ================================================================================

    def test_validate_track_file_success(self, file_path_resolver):
        """Test successful file validation."""
        # Arrange
        file_path = Path("/tmp/test.mp3")

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'stat') as mock_stat:

            mock_stat.return_value.st_size = 1024  # Non-empty file

            # Act
            result = file_path_resolver.validate_track_file(file_path)

            # Assert
            assert result is True

    def test_validate_track_file_not_exists(self, file_path_resolver):
        """Test validation when file doesn't exist."""
        # Arrange
        file_path = Path("/tmp/missing.mp3")

        with patch.object(Path, 'exists', return_value=False):

            # Act
            result = file_path_resolver.validate_track_file(file_path)

            # Assert
            assert result is False

    def test_validate_track_file_not_a_file(self, file_path_resolver):
        """Test validation when path is not a file (e.g., directory)."""
        # Arrange
        file_path = Path("/tmp/directory")

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=False):

            # Act
            result = file_path_resolver.validate_track_file(file_path)

            # Assert
            assert result is False

    def test_validate_track_file_empty(self, file_path_resolver):
        """Test validation when file is empty."""
        # Arrange
        file_path = Path("/tmp/empty.mp3")

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'stat') as mock_stat:

            mock_stat.return_value.st_size = 0  # Empty file

            # Act
            result = file_path_resolver.validate_track_file(file_path)

            # Assert
            assert result is False

    # ================================================================================
    # Test get_file_stats()
    # ================================================================================

    def test_get_file_stats_success(self, file_path_resolver):
        """Test getting file statistics successfully."""
        # Arrange
        file_path = Path("/tmp/test.mp3")
        mock_time = time.time()

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'stat') as mock_stat:

            mock_stat.return_value.st_size = 2048
            mock_stat.return_value.st_mtime = mock_time

            # Act
            result = file_path_resolver.get_file_stats(file_path)

            # Assert
            assert result is not None
            assert result["size"] == 2048
            assert result["modified"] == mock_time
            assert result["exists"] is True
            assert result["readable"] is True

    def test_get_file_stats_invalid_file(self, file_path_resolver):
        """Test getting stats for invalid file."""
        # Arrange
        file_path = Path("/tmp/missing.mp3")

        with patch.object(Path, 'exists', return_value=False):

            # Act
            result = file_path_resolver.get_file_stats(file_path)

            # Assert
            assert result is None

    def test_get_file_stats_os_error(self, file_path_resolver):
        """Test getting stats when OSError occurs."""
        # Arrange
        file_path = Path("/tmp/test.mp3")

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'stat', side_effect=OSError("Permission denied")):

            # Act
            result = file_path_resolver.get_file_stats(file_path)

            # Assert
            assert result is None

    def test_get_file_stats_value_error(self, file_path_resolver):
        """Test getting stats when ValueError occurs."""
        # Arrange
        file_path = Path("/tmp/test.mp3")

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_file', return_value=True), \
             patch.object(Path, 'stat', side_effect=ValueError("Invalid path")):

            # Act
            result = file_path_resolver.get_file_stats(file_path)

            # Assert
            assert result is None

    # ================================================================================
    # Test edge cases and integration
    # ================================================================================

    def test_track_without_filename_attribute(self, file_path_resolver):
        """Test resolving track that doesn't have filename attribute."""
        # Arrange
        track = Mock(spec=[])  # Empty spec, no attributes
        playlist_title = "My Playlist"

        # Act
        result = file_path_resolver.resolve_track_path(track, playlist_title)

        # Assert (AttributeError is caught by decorator)
        assert result["status"] == "error"
        assert "attributeerror" in result["error_type"].lower()

    def test_empty_filename(self, file_path_resolver):
        """Test resolving track with empty filename."""
        # Arrange
        track = Mock()
        track.filename = ""
        track.track_number = 1
        playlist_title = "My Playlist"

        # Act
        result = file_path_resolver.resolve_track_path(track, playlist_title)

        # Assert
        assert result is None

    def test_path_resolution_priority_order(self, file_path_resolver):
        """Test that path resolution tries strategies in correct priority order."""
        # Arrange
        track = Mock()
        track.filename = "song.mp3"
        track.track_number = 1
        playlist_title = "My Playlist"

        # Mock: only second strategy (root dir) exists
        expected_path = file_path_resolver.uploads_dir / "song.mp3"
        attempted_paths = []

        def mock_exists(self):
            attempted_paths.append(str(self))
            return str(self) == str(expected_path)

        with patch.object(Path, 'exists', mock_exists), \
             patch.object(Path, 'is_file', return_value=True):

            # Act
            result = file_path_resolver.resolve_track_path(track, playlist_title)

            # Assert
            assert result == expected_path
            # Should have tried playlist dir first, then root dir
            assert len(attempted_paths) >= 2
            playlist_dir_path = str(file_path_resolver.uploads_dir / playlist_title / "song.mp3")
            assert attempted_paths[0] == playlist_dir_path
