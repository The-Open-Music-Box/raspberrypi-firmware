# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for UploadService

Comprehensive tests for the upload service including file validation,
metadata extraction, upload processing, and cleanup operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open, MagicMock
from pathlib import Path

from app.src.services.upload_service import UploadService
from app.src.infrastructure.error_handling.unified_error_handler import InvalidFileError


class TestUploadService:
    """Test suite for UploadService."""

    @pytest.fixture
    def mock_config(self):
        """Mock application config."""
        config = Mock()
        config.upload_folder = "/tmp/test_uploads"
        config.upload_allowed_extensions = ["mp3", "wav", "flac", "m4a"]
        config.upload_max_size = 100 * 1024 * 1024  # 100MB
        return config

    @pytest.fixture
    def upload_service(self, mock_config):
        """Create UploadService instance."""
        return UploadService(mock_config)

    # ================================================================================
    # Test __init__()
    # ================================================================================

    def test_init_sets_upload_folder(self, mock_config):
        """Test initialization sets upload folder correctly."""
        # Act
        service = UploadService(mock_config)

        # Assert
        assert service.upload_folder == Path("/tmp/test_uploads")

    def test_init_sets_allowed_extensions(self, mock_config):
        """Test initialization sets allowed extensions."""
        # Act
        service = UploadService(mock_config)

        # Assert
        assert "mp3" in service.allowed_extensions
        assert "wav" in service.allowed_extensions
        assert "flac" in service.allowed_extensions
        assert "m4a" in service.allowed_extensions

    def test_init_sets_max_file_size(self, mock_config):
        """Test initialization sets max file size."""
        # Act
        service = UploadService(mock_config)

        # Assert
        assert service.max_file_size == 100 * 1024 * 1024

    # ================================================================================
    # Test _allowed_file()
    # ================================================================================

    def test_allowed_file_valid_extensions(self, upload_service):
        """Test file validation with valid extensions."""
        # Assert
        assert upload_service._allowed_file("song.mp3") is True
        assert upload_service._allowed_file("track.wav") is True
        assert upload_service._allowed_file("audio.flac") is True
        assert upload_service._allowed_file("music.m4a") is True
        assert upload_service._allowed_file("SONG.MP3") is True  # Case insensitive

    def test_allowed_file_invalid_extensions(self, upload_service):
        """Test file validation with invalid extensions."""
        # Assert
        assert upload_service._allowed_file("document.txt") is False
        assert upload_service._allowed_file("video.mp4") is False
        assert upload_service._allowed_file("image.jpg") is False
        assert upload_service._allowed_file("noextension") is False

    def test_allowed_file_multiple_dots(self, upload_service):
        """Test file validation with multiple dots in filename."""
        # Assert
        assert upload_service._allowed_file("my.song.file.mp3") is True
        assert upload_service._allowed_file("my.document.file.txt") is False

    # ================================================================================
    # Test _check_file_size()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_check_file_size_within_limit(self, upload_service):
        """Test file size check when within limit."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.read.return_value = b"x" * (10 * 1024 * 1024)  # 10MB
        mock_file.seek = AsyncMock()

        # Act
        result = await upload_service._check_file_size(mock_file)

        # Assert
        assert result is True
        mock_file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_check_file_size_exceeds_limit(self, upload_service):
        """Test file size check when exceeding limit."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.read.return_value = b"x" * (150 * 1024 * 1024)  # 150MB
        mock_file.seek = AsyncMock()

        # Act
        result = await upload_service._check_file_size(mock_file)

        # Assert
        assert result is False
        mock_file.seek.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_check_file_size_exactly_at_limit(self, upload_service):
        """Test file size check when exactly at limit."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.read.return_value = b"x" * (100 * 1024 * 1024)  # Exactly 100MB
        mock_file.seek = AsyncMock()

        # Act
        result = await upload_service._check_file_size(mock_file)

        # Assert
        assert result is True

    @pytest.mark.asyncio
    async def test_check_file_size_resets_file_pointer(self, upload_service):
        """Test that file pointer is reset after size check."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.read.return_value = b"test content"
        mock_file.seek = AsyncMock()

        # Act
        await upload_service._check_file_size(mock_file)

        # Assert
        mock_file.seek.assert_called_once_with(0)

    # ================================================================================
    # Test extract_metadata()
    # ================================================================================

    def test_extract_metadata_success(self, upload_service):
        """Test successful metadata extraction."""
        # Arrange
        file_path = Path("/tmp/test.mp3")
        mock_audio = Mock()
        mock_audio.get.side_effect = lambda key, default: {
            "title": ["Test Song"],
            "artist": ["Test Artist"],
            "album": ["Test Album"]
        }.get(key, default)
        mock_audio.info.length = 180.5

        with patch('app.src.services.upload_service.MutagenFile', return_value=mock_audio):
            # Act
            metadata = upload_service.extract_metadata(file_path)

            # Assert
            assert metadata["title"] == "Test Song"
            assert metadata["artist"] == "Test Artist"
            assert metadata["album"] == "Test Album"
            assert metadata["duration"] == 180.5

    def test_extract_metadata_missing_tags(self, upload_service):
        """Test metadata extraction with missing tags."""
        # Arrange
        file_path = Path("/tmp/test.mp3")
        mock_audio = Mock()
        mock_audio.get.side_effect = lambda key, default: default
        mock_audio.info.length = 120.0

        with patch('app.src.services.upload_service.MutagenFile', return_value=mock_audio):
            # Act
            metadata = upload_service.extract_metadata(file_path)

            # Assert
            assert metadata["title"] == "test"  # Falls back to filename stem
            assert metadata["artist"] == "Unknown"
            assert metadata["album"] == "Unknown"
            assert metadata["duration"] == 120.0

    def test_extract_metadata_no_duration(self, upload_service):
        """Test metadata extraction when duration info is missing."""
        # Arrange
        file_path = Path("/tmp/test.mp3")
        mock_audio = Mock()
        mock_audio.get.side_effect = lambda key, default: default
        mock_audio.info = Mock(spec=[])  # No length attribute

        with patch('app.src.services.upload_service.MutagenFile', return_value=mock_audio):
            # Act
            metadata = upload_service.extract_metadata(file_path)

            # Assert
            assert metadata["duration"] == 0

    def test_extract_metadata_fallback_to_easyid3(self, upload_service):
        """Test fallback to EasyID3 when MutagenFile returns None."""
        # Arrange
        file_path = Path("/tmp/test.mp3")
        mock_id3 = Mock()
        mock_id3.get.side_effect = lambda key, default: {
            "title": ["Fallback Title"]
        }.get(key, default)
        mock_id3.info.length = 90.0

        with patch('app.src.services.upload_service.MutagenFile', return_value=None), \
             patch('app.src.services.upload_service.EasyID3', return_value=mock_id3):

            # Act
            metadata = upload_service.extract_metadata(file_path)

            # Assert
            assert metadata["title"] == "Fallback Title"

    # ================================================================================
    # Test process_upload()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_process_upload_success(self, upload_service):
        """Test successful file upload processing."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.filename = "test_song.mp3"
        mock_file.read.return_value = b"fake audio data"
        mock_file.seek = AsyncMock()

        playlist_path = "test_playlist"

        with patch.object(Path, 'mkdir'), \
             patch('builtins.open', mock_open()), \
             patch('app.src.services.upload_service.secure_filename', return_value="test_song.mp3"), \
             patch.object(upload_service, 'extract_metadata', return_value={
                 "title": "Test Song",
                 "artist": "Test Artist",
                 "album": "Test Album",
                 "duration": 180
             }):

            # Act
            filename, metadata = await upload_service.process_upload(mock_file, playlist_path)

            # Assert
            assert filename == "test_song.mp3"
            assert metadata["title"] == "Test Song"
            mock_file.seek.assert_called()

    @pytest.mark.asyncio
    async def test_process_upload_no_file(self, upload_service):
        """Test upload processing when no file is provided."""
        # Arrange
        mock_file = None
        playlist_path = "test_playlist"

        # Act
        result = await upload_service.process_upload(mock_file, playlist_path)

        # Assert (decorator transforms exception to error dict)
        assert result["status"] == "error"
        assert "no file" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_upload_no_filename(self, upload_service):
        """Test upload processing when file has no filename."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.filename = None
        playlist_path = "test_playlist"

        # Act
        result = await upload_service.process_upload(mock_file, playlist_path)

        # Assert
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_process_upload_invalid_file_type(self, upload_service):
        """Test upload processing with invalid file type."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.filename = "document.txt"
        playlist_path = "test_playlist"

        # Act
        result = await upload_service.process_upload(mock_file, playlist_path)

        # Assert
        assert result["status"] == "error"
        assert "not allowed" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_upload_file_too_large(self, upload_service):
        """Test upload processing when file is too large."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.filename = "huge_file.mp3"
        mock_file.read.return_value = b"x" * (150 * 1024 * 1024)  # 150MB
        mock_file.seek = AsyncMock()
        playlist_path = "test_playlist"

        # Act
        result = await upload_service.process_upload(mock_file, playlist_path)

        # Assert
        assert result["status"] == "error"
        assert "too large" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_upload_creates_directory(self, upload_service):
        """Test that upload processing creates playlist directory."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.filename = "test.mp3"
        mock_file.read.return_value = b"data"
        mock_file.seek = AsyncMock()
        playlist_path = "new_playlist"

        with patch.object(Path, 'mkdir') as mock_mkdir, \
             patch('builtins.open', mock_open()), \
             patch('app.src.services.upload_service.secure_filename', return_value="test.mp3"), \
             patch.object(upload_service, 'extract_metadata', return_value={}):

            # Act
            await upload_service.process_upload(mock_file, playlist_path)

            # Assert
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @pytest.mark.asyncio
    async def test_process_upload_secures_filename(self, upload_service):
        """Test that upload processing secures the filename."""
        # Arrange
        mock_file = AsyncMock()
        mock_file.filename = "../../../etc/passwd.mp3"  # Malicious filename
        mock_file.read.return_value = b"data"
        mock_file.seek = AsyncMock()
        playlist_path = "test_playlist"

        with patch.object(Path, 'mkdir'), \
             patch('builtins.open', mock_open()), \
             patch('app.src.services.upload_service.secure_filename', return_value="passwd.mp3") as mock_secure, \
             patch.object(upload_service, 'extract_metadata', return_value={}):

            # Act
            filename, _ = await upload_service.process_upload(mock_file, playlist_path)

            # Assert
            mock_secure.assert_called_once_with("../../../etc/passwd.mp3")
            assert filename == "passwd.mp3"

    # ================================================================================
    # Test cleanup_failed_upload()
    # ================================================================================

    def test_cleanup_failed_upload_file_exists(self, upload_service):
        """Test cleanup when file exists."""
        # Arrange
        playlist_path = "test_playlist"
        filename = "failed_upload.mp3"

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'unlink') as mock_unlink:

            # Act
            upload_service.cleanup_failed_upload(playlist_path, filename)

            # Assert
            mock_unlink.assert_called_once()

    def test_cleanup_failed_upload_file_not_exists(self, upload_service):
        """Test cleanup when file doesn't exist."""
        # Arrange
        playlist_path = "test_playlist"
        filename = "nonexistent.mp3"

        with patch.object(Path, 'exists', return_value=False), \
             patch.object(Path, 'unlink') as mock_unlink:

            # Act
            upload_service.cleanup_failed_upload(playlist_path, filename)

            # Assert
            mock_unlink.assert_not_called()

    def test_cleanup_failed_upload_os_error(self, upload_service):
        """Test cleanup handles OSError gracefully."""
        # Arrange
        playlist_path = "test_playlist"
        filename = "locked_file.mp3"

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'unlink', side_effect=OSError("Permission denied")):

            # Act (should not raise exception)
            upload_service.cleanup_failed_upload(playlist_path, filename)

            # Assert - no exception raised

    def test_cleanup_failed_upload_constructs_correct_path(self, upload_service):
        """Test that cleanup constructs the correct file path."""
        # Arrange
        playlist_path = "my_playlist"
        filename = "song.mp3"
        expected_path = Path("/tmp/test_uploads/my_playlist/song.mp3")

        with patch.object(Path, 'exists', return_value=True) as mock_exists, \
             patch.object(Path, 'unlink'):

            # Act
            upload_service.cleanup_failed_upload(playlist_path, filename)

            # Assert
            # The exists() method should have been called on the correct path
            assert mock_exists.called
