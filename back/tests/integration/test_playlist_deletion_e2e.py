# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
End-to-end integration tests for playlist deletion.

Tests the complete flow from creation to deletion to ensure the bug is fixed.
"""

import pytest
import asyncio
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
