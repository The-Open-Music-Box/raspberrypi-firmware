# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
End-to-end integration tests for playlist deletion.

Tests the complete flow from creation to deletion to ensure the bug is fixed.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock
from app.src.dependencies import get_database_manager
from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
from app.src.domain.data.services.playlist_service import PlaylistService


@pytest.mark.asyncio
class TestPlaylistDeletionE2E:
    """End-to-end tests for playlist deletion flow."""

    @pytest.fixture
    async def playlist_service(self):
        """Create a playlist service for testing."""
        db_manager = get_database_manager()
        playlist_repo = PureSQLitePlaylistRepository()
        track_repo = playlist_repo  # Same repo handles both
        return PlaylistService(playlist_repo, track_repo)

    async def test_delete_playlist_complete_flow(self, playlist_service):
        """Test complete playlist deletion flow: create -> delete -> verify gone."""
        # 1. Create a test playlist
        playlist_data = await playlist_service.create_playlist(
            'Test Deletion Flow',
            'Test description for deletion'
        )
        playlist_id = playlist_data['id']

        assert playlist_id is not None
        assert playlist_data.get('title') == 'Test Deletion Flow'

        # 2. Delete the playlist (this is what we're testing the fix for)
        success = await playlist_service.delete_playlist(playlist_id)
        assert success is True, "Deletion should succeed"

        # 3. Verify playlist is gone
        deleted_check = await playlist_service.get_playlist(playlist_id)
        assert deleted_check is None, "Playlist should not exist after deletion"

    async def test_delete_nonexistent_playlist(self, playlist_service):
        """Test deleting a playlist that doesn't exist returns False."""
        fake_id = 'fake-playlist-id-12345'

        success = await playlist_service.delete_playlist(fake_id)
        assert success is False, "Deleting non-existent playlist should return False"

    async def test_delete_playlist_with_tracks(self, playlist_service):
        """Test deleting a playlist that has tracks."""
        # Create playlist
        playlist_data = await playlist_service.create_playlist(
            'Playlist With Tracks',
            'Has tracks to delete'
        )
        playlist_id = playlist_data['id']

        # TODO: Add tracks once track creation is available in the service
        # For now, just verify deletion works even with empty tracks

        # Delete playlist
        success = await playlist_service.delete_playlist(playlist_id)
        assert success is True

        # Verify it's gone
        deleted = await playlist_service.get_playlist(playlist_id)
        assert deleted is None

    async def test_delete_playlist_removes_physical_files(self, playlist_service, tmp_path, monkeypatch):
        """Test that deleting a playlist removes physical audio files from disk."""
        import app.src.domain.data.services.playlist_service as playlist_service_module

        # Setup temporary upload folder
        upload_folder = tmp_path / "uploads"
        upload_folder.mkdir()

        # Mock app config to use temp folder - must patch the imported config in the playlist_service module
        mock_config = MagicMock()
        mock_config.upload_folder = str(upload_folder)
        monkeypatch.setattr(playlist_service_module, 'app_config', mock_config)

        # Create a test playlist
        playlist_data = await playlist_service.create_playlist(
            'Test Physical Deletion',
            'Test description'
        )
        playlist_id = playlist_data['id']

        # Create the physical folder and audio files to simulate uploaded content
        from app.src.utils.path_utils import normalize_folder_name
        playlist_folder_name = normalize_folder_name('Test Physical Deletion')
        playlist_folder = upload_folder / playlist_folder_name
        playlist_folder.mkdir(parents=True, exist_ok=True)

        # Create some fake audio files
        audio_file_1 = playlist_folder / "track1.mp3"
        audio_file_2 = playlist_folder / "track2.mp3"
        audio_file_1.write_text("fake audio data 1")
        audio_file_2.write_text("fake audio data 2")

        # Verify files exist before deletion
        assert playlist_folder.exists(), "Playlist folder should exist before deletion"
        assert audio_file_1.exists(), "Audio file 1 should exist before deletion"
        assert audio_file_2.exists(), "Audio file 2 should exist before deletion"

        # Update the playlist to have the correct path
        await playlist_service.update_playlist(playlist_id, {'path': playlist_folder_name})

        # Delete the playlist
        success = await playlist_service.delete_playlist(playlist_id)
        assert success is True, "Deletion should succeed"

        # Verify playlist is gone from database
        deleted_check = await playlist_service.get_playlist(playlist_id)
        assert deleted_check is None, "Playlist should not exist in database after deletion"

        # CRITICAL CHECK: Verify physical files and folder are deleted
        assert not playlist_folder.exists(), "Playlist folder should be deleted from disk"
        assert not audio_file_1.exists(), "Audio file 1 should be deleted from disk"
        assert not audio_file_2.exists(), "Audio file 2 should be deleted from disk"
