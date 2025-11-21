# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unit tests for PureSQLitePlaylistRepository."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
from app.src.domain.data.models.track import Track


class TestPureSQLitePlaylistRepository:
    """Test suite for PureSQLitePlaylistRepository."""

    @pytest.fixture
    def mock_db_service(self):
        """Mock database service."""
        db_service = Mock()
        db_service.execute_query = Mock()
        db_service.execute_command = Mock()
        return db_service

    @pytest.fixture
    def repository(self, mock_db_service):
        """Create repository instance with mocked database service."""
        with patch('app.src.infrastructure.repositories.pure_sqlite_playlist_repository.get_database_manager') as mock_get_db_manager:
            mock_db_manager = Mock()
            mock_db_manager.database_service = mock_db_service
            mock_get_db_manager.return_value = mock_db_manager

            repo = PureSQLitePlaylistRepository()
            return repo

    @pytest.mark.asyncio
    async def test_get_tracks_by_playlist_success(self, repository, mock_db_service):
        """Test getting tracks by playlist ID."""
        playlist_id = 'playlist-1'
        track_rows = [
            {
                'id': 'track-1',
                'playlist_id': playlist_id,
                'track_number': 1,
                'title': 'Track 1',
                'filename': 'track1.mp3',
                'file_path': '/path/track1.mp3',
                'duration_ms': 180000,
                'artist': 'Artist 1',
                'album': 'Album 1'
            },
            {
                'id': 'track-2',
                'playlist_id': playlist_id,
                'track_number': 2,
                'title': 'Track 2',
                'filename': 'track2.mp3',
                'file_path': '/path/track2.mp3',
                'duration_ms': 240000,
                'artist': 'Artist 2',
                'album': 'Album 2'
            }
        ]

        mock_db_service.execute_query.return_value = track_rows

        result = await repository.get_tracks_by_playlist(playlist_id)

        # Verify returns Track objects
        assert len(result) == 2
        assert all(isinstance(track, Track) for track in result)

        # Verify track data
        assert result[0].id == 'track-1'
        assert result[0].title == 'Track 1'
        assert result[0].track_number == 1

        assert result[1].id == 'track-2'
        assert result[1].title == 'Track 2'
        assert result[1].track_number == 2

        # Verify database query
        mock_db_service.execute_query.assert_called_once()
        query_call = mock_db_service.execute_query.call_args
        assert 'SELECT * FROM tracks' in query_call[0][0]
        assert query_call[0][1] == (playlist_id,)

    @pytest.mark.asyncio
    async def test_get_tracks_by_playlist_empty(self, repository, mock_db_service):
        """Test getting tracks when playlist has no tracks."""
        playlist_id = 'empty-playlist'
        mock_db_service.execute_query.return_value = []

        result = await repository.get_tracks_by_playlist(playlist_id)

        assert result == []
        mock_db_service.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_tracks_by_playlist_handles_missing_fields(self, repository, mock_db_service):
        """Test getting tracks handles missing optional fields gracefully."""
        playlist_id = 'playlist-1'
        track_rows = [
            {
                'id': 'track-1',
                'playlist_id': playlist_id,
                'track_number': 1,
                'title': 'Track 1',
                'filename': 'track1.mp3',
                'file_path': '/path/track1.mp3',
                'duration_ms': None,  # Optional field
                'artist': None,  # Optional field
                'album': None  # Optional field
            }
        ]

        mock_db_service.execute_query.return_value = track_rows

        result = await repository.get_tracks_by_playlist(playlist_id)

        assert len(result) == 1
        assert isinstance(result[0], Track)
        assert result[0].duration_ms is None
        assert result[0].artist is None
        assert result[0].album is None

    @pytest.mark.asyncio
    async def test_delete_tracks_by_playlist_success(self, repository, mock_db_service):
        """Test deleting all tracks for a playlist."""
        playlist_id = 'playlist-1'
        mock_db_service.execute_command.return_value = 5  # 5 tracks deleted

        result = await repository.delete_tracks_by_playlist(playlist_id)

        assert result is True

        # Verify database command
        mock_db_service.execute_command.assert_called_once()
        command_call = mock_db_service.execute_command.call_args
        assert 'DELETE FROM tracks WHERE playlist_id = ?' in command_call[0][0]
        assert command_call[0][1] == (playlist_id,)

    @pytest.mark.asyncio
    async def test_delete_tracks_by_playlist_no_tracks(self, repository, mock_db_service):
        """Test deleting tracks when playlist has no tracks."""
        playlist_id = 'empty-playlist'
        mock_db_service.execute_command.return_value = 0  # No tracks deleted

        result = await repository.delete_tracks_by_playlist(playlist_id)

        assert result is True  # Still returns True even if no tracks deleted
        mock_db_service.execute_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_repository_methods_handle_database_errors(self, repository, mock_db_service):
        """Test that repository methods handle database errors gracefully."""
        playlist_id = 'playlist-1'

        # Test get_tracks_by_playlist with database error
        mock_db_service.execute_query.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await repository.get_tracks_by_playlist(playlist_id)

        # Test delete_tracks_by_playlist with database error
        mock_db_service.execute_command.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await repository.delete_tracks_by_playlist(playlist_id)

    def test_track_object_subscriptable_compatibility(self):
        """Test that Track objects work with both attribute and dictionary access patterns."""
        track = Track(
            id='track-1',
            track_number=1,
            title='Test Track',
            filename='test.mp3',
            file_path='/path/test.mp3',
            duration_ms=180000
        )

        # Test attribute access
        assert track.id == 'track-1'
        assert track.track_number == 1
        assert track.title == 'Test Track'

        # Test hasattr works
        assert hasattr(track, 'id')
        assert hasattr(track, 'track_number')
        assert hasattr(track, 'title')

        # Verify that track is NOT subscriptable (as expected)
        with pytest.raises(TypeError):
            _ = track['id']

    @pytest.mark.asyncio
    async def test_find_by_nfc_tag_success(self, repository, mock_db_service):
        """Test finding playlist by NFC tag.

        This test verifies the critical NFC lookup functionality that enables
        playlist playback when an NFC tag is scanned.
        """
        nfc_tag_id = 'test-nfc-123'
        playlist_row = {
            'id': 'playlist-1',
            'title': 'NFC Playlist',
            'description': 'Test playlist',
            'nfc_tag_id': nfc_tag_id,
            'path': '/path/to/playlist',
            'type': 'album'
        }
        track_rows = [
            {
                'id': 'track-1',
                'playlist_id': 'playlist-1',
                'track_number': 1,
                'title': 'Track 1',
                'filename': 'track1.mp3',
                'file_path': '/path/track1.mp3',
                'duration_ms': 180000,
                'artist': 'Artist 1',
                'album': 'Album 1'
            }
        ]

        # Mock database calls
        mock_db_service.execute_single.return_value = playlist_row
        mock_db_service.execute_query.return_value = track_rows

        result = await repository.find_by_nfc_tag(nfc_tag_id)

        # Verify result
        assert result is not None
        assert result.id == 'playlist-1'
        assert result.title == 'NFC Playlist'
        assert result.nfc_tag_id == nfc_tag_id
        assert len(result.tracks) == 1
        assert result.tracks[0].title == 'Track 1'

        # Verify database query
        mock_db_service.execute_single.assert_called_once()
        query_call = mock_db_service.execute_single.call_args
        assert 'SELECT * FROM playlists WHERE nfc_tag_id = ?' in query_call[0][0]
        assert query_call[0][1] == (nfc_tag_id,)

    @pytest.mark.asyncio
    async def test_find_by_nfc_tag_not_found(self, repository, mock_db_service):
        """Test finding playlist by NFC tag when no playlist is associated."""
        nfc_tag_id = 'nonexistent-nfc'
        mock_db_service.execute_single.return_value = None

        result = await repository.find_by_nfc_tag(nfc_tag_id)

        assert result is None
        mock_db_service.execute_single.assert_called_once()

    def test_repository_has_interface_method(self, repository):
        """Test that repository implements the correct interface method name.

        This test catches the bug where the service was calling get_by_nfc_tag
        but the repository only had find_by_nfc_tag.
        """
        # Verify repository has find_by_nfc_tag (interface method)
        assert hasattr(repository, 'find_by_nfc_tag'), \
            "Repository must implement find_by_nfc_tag method from PlaylistRepositoryProtocol"

        # Verify method is callable
        assert callable(repository.find_by_nfc_tag), \
            "find_by_nfc_tag must be callable"

        # Verify repository does NOT have the old wrong method name
        # (This would have prevented the original bug)
        # Note: We're not asserting this doesn't exist because it was never there,
        # but we verify the correct one exists