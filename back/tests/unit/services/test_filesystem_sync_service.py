# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for FilesystemSyncService

Comprehensive tests for filesystem synchronization including playlist creation,
track updates, filesystem scanning, and synchronization operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

from app.src.services.filesystem_sync_service import FilesystemSyncService


class TestFilesystemSyncService:
    """Test suite for FilesystemSyncService."""

    @pytest.fixture
    def mock_config(self):
        """Mock application config."""
        config = Mock()
        config.upload_folder = "/tmp/test_uploads"
        return config

    @pytest.fixture
    def mock_repository(self):
        """Mock playlist repository."""
        return AsyncMock()

    @pytest.fixture
    def sync_service(self, mock_config, mock_repository):
        """Create FilesystemSyncService instance."""
        with patch('app.src.dependencies.get_playlist_repository_adapter', return_value=mock_repository):
            service = FilesystemSyncService(mock_config)
            return service

    # ================================================================================
    # Test __init__()
    # ================================================================================

    def test_init_with_config(self, mock_config, mock_repository):
        """Test initialization with config object."""
        # Arrange & Act
        with patch('app.src.dependencies.get_playlist_repository_adapter', return_value=mock_repository):
            service = FilesystemSyncService(mock_config)

        # Assert
        assert service.config == mock_config
        assert service.upload_folder == Path("/tmp/test_uploads")
        assert service.repository == mock_repository

    def test_init_without_config_uses_global(self, mock_repository):
        """Test initialization without config uses global config."""
        # Arrange
        with patch('app.src.dependencies.get_playlist_repository_adapter', return_value=mock_repository), \
             patch('app.src.config.config') as mock_global_config:
            mock_global_config.upload_folder = "/global/uploads"

            # Act
            service = FilesystemSyncService()

            # Assert
            assert service.config == mock_global_config
            assert service.upload_folder == Path("/global/uploads")

    def test_init_creates_sync_lock(self, sync_service):
        """Test initialization creates threading lock."""
        # Assert
        assert hasattr(sync_service, '_sync_lock')
        assert sync_service._sync_lock is not None

    # ================================================================================
    # Test create_playlist_from_folder()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_create_playlist_from_folder_success(self, sync_service, mock_repository):
        """Test successful playlist creation from folder."""
        # Arrange
        folder_path = Path("/tmp/test_uploads/test_playlist")
        mock_repository.create_playlist.return_value = "playlist-123"

        # Mock Path operations
        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'iterdir') as mock_iterdir, \
             patch('app.src.services.filesystem_sync_service.UploadService') as mock_upload_service_class, \
             patch('builtins.sorted', side_effect=lambda x: list(x)):  # Keep original order

            # Create mock audio files
            mock_file1 = MagicMock(spec=Path)
            mock_file1.is_file.return_value = True
            mock_file1.suffix = ".mp3"
            mock_file1.name = "song1.mp3"
            mock_file1.stem = "song1"

            mock_file2 = MagicMock(spec=Path)
            mock_file2.is_file.return_value = True
            mock_file2.suffix = ".flac"
            mock_file2.name = "song2.flac"
            mock_file2.stem = "song2"

            mock_iterdir.return_value = [mock_file1, mock_file2]

            # Mock UploadService
            mock_upload_service = Mock()
            mock_upload_service.extract_metadata.side_effect = [
                {"title": "Song 1", "duration": 180, "artist": "Artist 1", "album": "Album 1"},
                {"title": "Song 2", "duration": 240, "artist": "Artist 2", "album": "Album 2"}
            ]
            mock_upload_service_class.return_value = mock_upload_service

            # Act
            playlist_id = await sync_service.create_playlist_from_folder(folder_path, "Test Playlist")

            # Assert
            assert playlist_id == "playlist-123"
            mock_repository.create_playlist.assert_called_once()
            playlist_data = mock_repository.create_playlist.call_args[0][0]
            assert playlist_data["title"] == "Test Playlist"
            assert len(playlist_data["tracks"]) == 2
            assert playlist_data["tracks"][0]["title"] == "Song 1"
            assert playlist_data["tracks"][0]["duration"] == 180000  # Converted to ms
            assert playlist_data["tracks"][1]["title"] == "Song 2"

    @pytest.mark.asyncio
    async def test_create_playlist_from_folder_folder_not_exists(self, sync_service):
        """Test playlist creation when folder doesn't exist."""
        # Arrange
        folder_path = Path("/tmp/missing_folder")

        with patch.object(Path, 'exists', return_value=False):
            # Act
            result = await sync_service.create_playlist_from_folder(folder_path)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_create_playlist_from_folder_not_a_directory(self, sync_service):
        """Test playlist creation when path is not a directory."""
        # Arrange
        folder_path = Path("/tmp/file.mp3")

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_dir', return_value=False):
            # Act
            result = await sync_service.create_playlist_from_folder(folder_path)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_create_playlist_from_folder_no_audio_files(self, sync_service):
        """Test playlist creation when folder has no audio files."""
        # Arrange
        folder_path = Path("/tmp/test_uploads/empty_folder")

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'iterdir') as mock_iterdir:

            # Mock non-audio files
            mock_file = MagicMock(spec=Path)
            mock_file.is_file.return_value = True
            mock_file.suffix = ".txt"
            mock_iterdir.return_value = [mock_file]

            # Act
            result = await sync_service.create_playlist_from_folder(folder_path)

            # Assert
            assert result is None

    @pytest.mark.asyncio
    async def test_create_playlist_from_folder_uses_folder_name_when_no_title(self, sync_service, mock_repository):
        """Test playlist uses folder name when no title provided."""
        # Arrange
        folder_path = Path("/tmp/test_uploads/My Music")
        mock_repository.create_playlist.return_value = "playlist-456"

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'iterdir') as mock_iterdir, \
             patch('app.src.services.filesystem_sync_service.UploadService') as mock_upload_service_class, \
             patch('builtins.sorted', side_effect=lambda x: list(x)):

            mock_file = MagicMock(spec=Path)
            mock_file.is_file.return_value = True
            mock_file.suffix = ".mp3"
            mock_file.name = "song.mp3"
            mock_file.stem = "song"
            mock_iterdir.return_value = [mock_file]

            mock_upload_service = Mock()
            mock_upload_service.extract_metadata.return_value = {"title": "Song", "duration": 180}
            mock_upload_service_class.return_value = mock_upload_service

            # Act
            playlist_id = await sync_service.create_playlist_from_folder(folder_path)

            # Assert
            playlist_data = mock_repository.create_playlist.call_args[0][0]
            assert playlist_data["title"] == "My Music"

    # ================================================================================
    # Test update_playlist_tracks()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_update_playlist_tracks_add_new_tracks(self, sync_service, mock_repository):
        """Test updating playlist with new tracks added."""
        # Arrange
        playlist_id = "playlist-123"
        folder_path = Path("/tmp/test_uploads/playlist")

        existing_playlist = {
            "id": playlist_id,
            "tracks": [
                {"track_number": 1, "filename": "existing.mp3", "title": "Existing"}
            ]
        }
        mock_repository.get_playlist_by_id.return_value = existing_playlist
        mock_repository.replace_tracks.return_value = True

        with patch.object(Path, 'iterdir') as mock_iterdir:
            # Existing file + new file
            mock_file1 = MagicMock(spec=Path)
            mock_file1.is_file.return_value = True
            mock_file1.suffix = ".mp3"
            mock_file1.name = "existing.mp3"
            mock_file1.stem = "existing"

            mock_file2 = MagicMock(spec=Path)
            mock_file2.is_file.return_value = True
            mock_file2.suffix = ".mp3"
            mock_file2.name = "new.mp3"
            mock_file2.stem = "new"

            mock_iterdir.return_value = [mock_file1, mock_file2]

            # Act
            success, stats = await sync_service.update_playlist_tracks(playlist_id, folder_path)

            # Assert
            assert success is True
            assert stats["added"] == 1
            assert stats["removed"] == 0
            mock_repository.replace_tracks.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_playlist_tracks_remove_missing_tracks(self, sync_service, mock_repository):
        """Test updating playlist removes tracks for missing files."""
        # Arrange
        playlist_id = "playlist-123"
        folder_path = Path("/tmp/test_uploads/playlist")

        existing_playlist = {
            "id": playlist_id,
            "tracks": [
                {"track_number": 1, "filename": "existing.mp3", "title": "Existing"},
                {"track_number": 2, "filename": "removed.mp3", "title": "Removed"}
            ]
        }
        mock_repository.get_playlist_by_id.return_value = existing_playlist
        mock_repository.replace_tracks.return_value = True

        with patch.object(Path, 'iterdir') as mock_iterdir:
            # Only existing file
            mock_file = MagicMock(spec=Path)
            mock_file.is_file.return_value = True
            mock_file.suffix = ".mp3"
            mock_file.name = "existing.mp3"
            mock_iterdir.return_value = [mock_file]

            # Act
            success, stats = await sync_service.update_playlist_tracks(playlist_id, folder_path)

            # Assert
            assert success is True
            assert stats["added"] == 0
            assert stats["removed"] == 1

    @pytest.mark.asyncio
    async def test_update_playlist_tracks_playlist_not_found(self, sync_service, mock_repository):
        """Test updating non-existent playlist."""
        # Arrange
        playlist_id = "missing-playlist"
        folder_path = Path("/tmp/test_uploads/playlist")
        mock_repository.get_playlist_by_id.return_value = None

        # Act
        success, stats = await sync_service.update_playlist_tracks(playlist_id, folder_path)

        # Assert
        assert success is False
        assert stats["added"] == 0
        assert stats["removed"] == 0

    # ================================================================================
    # Test _scan_filesystem_with_timeout()
    # ================================================================================

    def test_scan_filesystem_finds_audio_folders(self, sync_service):
        """Test filesystem scanning finds folders with audio files."""
        # Arrange
        with patch.object(Path, 'iterdir') as mock_iterdir_root:
            # Create mock folder
            mock_folder = MagicMock(spec=Path)
            mock_folder.is_dir.return_value = True
            mock_folder.name = "playlist1"

            # Create mock audio file
            mock_audio = MagicMock(spec=Path)
            mock_audio.is_file.return_value = True
            mock_audio.suffix = ".mp3"

            mock_folder.iterdir.return_value = [mock_audio]
            mock_folder.relative_to.return_value = Path("uploads/playlist1")
            mock_iterdir_root.return_value = [mock_folder]

            with patch('time.time', return_value=1000.0):
                # Act
                result = sync_service._scan_filesystem_with_timeout()

                # Assert
                assert len(result) > 0
                assert "uploads/playlist1" in result

    def test_scan_filesystem_skips_empty_folders(self, sync_service):
        """Test filesystem scanning skips folders without audio files."""
        # Arrange
        with patch.object(Path, 'iterdir') as mock_iterdir_root:
            mock_folder = MagicMock(spec=Path)
            mock_folder.is_dir.return_value = True
            mock_folder.iterdir.return_value = []  # Empty folder
            mock_iterdir_root.return_value = [mock_folder]

            with patch('time.time', return_value=1000.0):
                # Act
                result = sync_service._scan_filesystem_with_timeout()

                # Assert
                assert len(result) == 0

    def test_scan_filesystem_skips_non_audio_files(self, sync_service):
        """Test filesystem scanning skips non-audio files."""
        # Arrange
        with patch.object(Path, 'iterdir') as mock_iterdir_root:
            mock_folder = MagicMock(spec=Path)
            mock_folder.is_dir.return_value = True

            mock_file = MagicMock(spec=Path)
            mock_file.is_file.return_value = True
            mock_file.suffix = ".txt"  # Not an audio file

            mock_folder.iterdir.return_value = [mock_file]
            mock_iterdir_root.return_value = [mock_folder]

            with patch('time.time', return_value=1000.0):
                # Act
                result = sync_service._scan_filesystem_with_timeout()

                # Assert
                assert len(result) == 0

    def test_scan_filesystem_handles_multiple_folders(self, sync_service):
        """Test filesystem scanning handles multiple folders correctly."""
        # Arrange
        with patch.object(Path, 'iterdir') as mock_iterdir_root:
            # Create multiple folders with audio files
            folders = []
            for i in range(3):
                mock_folder = MagicMock(spec=Path)
                mock_folder.is_dir.return_value = True
                mock_folder.name = f"folder{i}"
                mock_folder.relative_to.return_value = Path(f"uploads/folder{i}")

                # Add an audio file
                mock_audio = MagicMock(spec=Path)
                mock_audio.is_file.return_value = True
                mock_audio.suffix = ".mp3"
                mock_folder.iterdir.return_value = [mock_audio]

                folders.append(mock_folder)

            mock_iterdir_root.return_value = folders

            with patch('time.time', return_value=1000.0):
                # Act
                result = sync_service._scan_filesystem_with_timeout()

                # Assert - all folders processed
                assert len(result) == 3

    # ================================================================================
    # Test sync_with_filesystem()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_sync_with_filesystem_creates_upload_folder(self, sync_service, mock_repository):
        """Test sync creates upload folder if it doesn't exist."""
        # Arrange
        mock_repository.get_all_playlists.return_value = []

        with patch.object(Path, 'exists', return_value=False), \
             patch.object(Path, 'mkdir') as mock_mkdir, \
             patch.object(sync_service, '_scan_filesystem_with_timeout', return_value={}), \
             patch('time.time', return_value=1000.0):

            # Act
            stats = await sync_service.sync_with_filesystem()

            # Assert
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @pytest.mark.asyncio
    async def test_sync_with_filesystem_returns_stats(self, sync_service, mock_repository):
        """Test sync returns statistics."""
        # Arrange
        mock_repository.get_all_playlists.return_value = []

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(sync_service, '_scan_filesystem_with_timeout', return_value={}), \
             patch('time.time', return_value=1000.0):

            # Act
            stats = await sync_service.sync_with_filesystem()

            # Assert
            assert "playlists_scanned" in stats
            assert "playlists_added" in stats
            assert "playlists_updated" in stats
            assert "tracks_added" in stats
            assert "tracks_removed" in stats

    @pytest.mark.asyncio
    async def test_sync_with_filesystem_uses_lock(self, sync_service, mock_repository):
        """Test sync uses lock to prevent concurrent execution."""
        # Arrange
        mock_repository.get_all_playlists.return_value = []
        mock_lock = MagicMock()
        sync_service._sync_lock = mock_lock

        with patch.object(Path, 'exists', return_value=True), \
             patch.object(sync_service, '_scan_filesystem_with_timeout', return_value={}), \
             patch('time.time', return_value=1000.0):

            # Act
            stats = await sync_service.sync_with_filesystem()

            # Assert
            mock_lock.__enter__.assert_called_once()
            mock_lock.__exit__.assert_called_once()

    # ================================================================================
    # Test _update_existing_playlists()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_update_existing_playlists_updates_matching(self, sync_service, mock_repository):
        """Test updating existing playlists that match disk folders."""
        # Arrange
        db_playlists = [
            {"id": "playlist-1", "path": "uploads/folder1", "title": "Playlist 1"}
        ]
        disk_playlists = {
            "uploads/folder1": [Path("/tmp/test_uploads/folder1/song.mp3")]
        }
        stats = {"playlists_scanned": 0, "playlists_updated": 0, "tracks_added": 0, "tracks_removed": 0}

        mock_repository.get_playlist_by_id.return_value = {
            "id": "playlist-1",
            "tracks": [{"filename": "song.mp3"}]
        }
        mock_repository.replace_tracks.return_value = True

        with patch.object(sync_service, 'update_playlist_tracks', return_value=(True, {"added": 0, "removed": 0})) as mock_update, \
             patch('time.time', return_value=1000.0):

            # Act
            await sync_service._update_existing_playlists(db_playlists, disk_playlists, stats)

            # Assert
            assert stats["playlists_scanned"] == 1
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_existing_playlists_skips_missing_folders(self, sync_service):
        """Test updating skips playlists whose folders no longer exist."""
        # Arrange
        db_playlists = [
            {"id": "playlist-1", "path": "uploads/missing_folder", "title": "Playlist 1"}
        ]
        disk_playlists = {}  # Folder doesn't exist on disk
        stats = {"playlists_scanned": 0, "playlists_updated": 0, "tracks_added": 0, "tracks_removed": 0}

        with patch('time.time', return_value=1000.0):
            # Act
            await sync_service._update_existing_playlists(db_playlists, disk_playlists, stats)

            # Assert
            assert stats["playlists_scanned"] == 1
            assert stats["playlists_updated"] == 0

    # ================================================================================
    # Test _add_new_playlists()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_add_new_playlists_creates_new(self, sync_service, mock_repository):
        """Test adding new playlists from disk folders."""
        # Arrange
        disk_playlists = {
            "uploads/new_playlist": [Path("/tmp/test_uploads/new_playlist/song.mp3")]
        }
        db_playlists_by_path = {}
        db_playlists_by_title = {}
        stats = {"playlists_added": 0, "tracks_added": 0}

        with patch.object(sync_service, 'create_playlist_from_folder', return_value="new-playlist-id") as mock_create, \
             patch('time.time', return_value=1000.0):

            # Act
            await sync_service._add_new_playlists(disk_playlists, db_playlists_by_path, db_playlists_by_title, stats)

            # Assert
            assert stats["playlists_added"] == 1
            assert stats["tracks_added"] == 1
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_new_playlists_skips_existing_by_path(self, sync_service):
        """Test adding skips playlists that already exist by path."""
        # Arrange
        disk_playlists = {
            "uploads/existing": [Path("/tmp/test_uploads/existing/song.mp3")]
        }
        db_playlists_by_path = {
            "uploads/existing": {"id": "existing-id", "title": "Existing"}
        }
        db_playlists_by_title = {}
        stats = {"playlists_added": 0, "tracks_added": 0}

        with patch('time.time', return_value=1000.0):
            # Act
            await sync_service._add_new_playlists(disk_playlists, db_playlists_by_path, db_playlists_by_title, stats)

            # Assert
            assert stats["playlists_added"] == 0

    @pytest.mark.asyncio
    async def test_add_new_playlists_skips_existing_by_title(self, sync_service):
        """Test adding skips playlists that already exist by folder name."""
        # Arrange
        disk_playlists = {
            "uploads/My Playlist": [Path("/tmp/test_uploads/My Playlist/song.mp3")]
        }
        db_playlists_by_path = {}
        db_playlists_by_title = {
            "my playlist": {"id": "existing-id", "title": "My Playlist"}
        }
        stats = {"playlists_added": 0, "tracks_added": 0}

        with patch('time.time', return_value=1000.0):
            # Act
            await sync_service._add_new_playlists(disk_playlists, db_playlists_by_path, db_playlists_by_title, stats)

            # Assert
            assert stats["playlists_added"] == 0

    @pytest.mark.asyncio
    async def test_add_new_playlists_handles_errors(self, sync_service):
        """Test adding handles errors gracefully."""
        # Arrange
        disk_playlists = {
            "uploads/error_playlist": [Path("/tmp/test_uploads/error_playlist/song.mp3")]
        }
        db_playlists_by_path = {}
        db_playlists_by_title = {}
        stats = {"playlists_added": 0, "tracks_added": 0}

        with patch.object(sync_service, 'create_playlist_from_folder', side_effect=OSError("Disk error")), \
             patch('time.time', return_value=1000.0):

            # Act (should not raise exception)
            await sync_service._add_new_playlists(disk_playlists, db_playlists_by_path, db_playlists_by_title, stats)

            # Assert
            assert stats["playlists_added"] == 0

    # ================================================================================
    # Test edge cases and integration
    # ================================================================================

    def test_supported_audio_extensions(self):
        """Test class has correct supported audio extensions."""
        # Assert
        expected = {".mp3", ".ogg", ".wav", ".m4a", ".flac", ".aac"}
        assert FilesystemSyncService.SUPPORTED_AUDIO_EXTENSIONS == expected

    def test_timeout_constants(self):
        """Test class has timeout constants defined."""
        # Assert
        assert FilesystemSyncService.SYNC_TOTAL_TIMEOUT == 120.0
        assert FilesystemSyncService.SYNC_FOLDER_TIMEOUT == 30.0
        assert FilesystemSyncService.SYNC_OPERATION_TIMEOUT == 10.0
