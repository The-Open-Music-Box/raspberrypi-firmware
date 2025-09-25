# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unit tests for DataApplicationService."""

import pytest
from unittest.mock import AsyncMock

from app.src.application.services.data_application_service import DataApplicationService
from app.src.common.exceptions import BusinessLogicError


class TestDataApplicationService:
    """Test suite for DataApplicationService."""

    @pytest.fixture
    def mock_playlist_service(self):
        """Mock playlist service."""
        service = AsyncMock()
        service.get_playlists.return_value = {'playlists': [], 'total': 0}
        service.get_playlist.return_value = None
        service.create_playlist.return_value = {'id': 'test-id', 'title': 'Test'}
        service.update_playlist.return_value = {'id': 'test-id', 'title': 'Updated'}
        service.delete_playlist.return_value = True
        service.associate_nfc_tag.return_value = True
        service.get_playlist_by_nfc.return_value = None
        service.sync_with_filesystem.return_value = {'playlists_added': 0}
        return service

    @pytest.fixture
    def mock_track_service(self):
        """Mock track service."""
        service = AsyncMock()
        service.get_tracks.return_value = []
        service.add_track.return_value = {'id': 'track-id', 'title': 'Track'}
        service.update_track.return_value = {'id': 'track-id', 'title': 'Updated'}
        service.delete_track.return_value = True
        service.reorder_tracks.return_value = True
        service.get_next_track.return_value = None
        service.get_previous_track.return_value = None
        return service

    @pytest.fixture
    def service(self, mock_playlist_service, mock_track_service):
        """Create DataApplicationService instance with mocked dependencies."""
        return DataApplicationService(mock_playlist_service, mock_track_service)

    @pytest.mark.asyncio
    async def test_get_playlists_use_case_success(self, service, mock_playlist_service):
        """Test successful playlist retrieval."""
        expected_result = {
            'playlists': [{'id': '1', 'title': 'Test'}],
            'total': 1,
            'page': 1,
            'page_size': 50
        }
        mock_playlist_service.get_playlists.return_value = expected_result

        result = await service.get_playlists_use_case(page=1, page_size=50)

        assert result == expected_result
        mock_playlist_service.get_playlists.assert_called_once_with(1, 50)

    @pytest.mark.asyncio
    async def test_get_playlists_use_case_exception(self, service, mock_playlist_service):
        """Test playlist retrieval with exception."""
        mock_playlist_service.get_playlists.side_effect = Exception("Database error")

        with pytest.raises(BusinessLogicError, match="Failed to retrieve playlists"):
            await service.get_playlists_use_case()

    @pytest.mark.asyncio
    async def test_get_playlist_use_case_found(self, service, mock_playlist_service):
        """Test getting a specific playlist that exists."""
        expected_playlist = {'id': 'playlist-1', 'title': 'Test Playlist'}
        mock_playlist_service.get_playlist.return_value = expected_playlist

        result = await service.get_playlist_use_case('playlist-1')

        assert result == expected_playlist

    @pytest.mark.asyncio
    async def test_get_playlist_use_case_not_found(self, service, mock_playlist_service):
        """Test getting a playlist that doesn't exist."""
        mock_playlist_service.get_playlist.return_value = None

        with pytest.raises(BusinessLogicError, match="Playlist playlist-1 not found"):
            await service.get_playlist_use_case('playlist-1')

    @pytest.mark.asyncio
    async def test_create_playlist_use_case_success(self, service, mock_playlist_service):
        """Test successful playlist creation."""
        expected_playlist = {'id': 'new-id', 'title': 'New Playlist'}
        mock_playlist_service.create_playlist.return_value = expected_playlist

        result = await service.create_playlist_use_case('New Playlist', 'Description')

        assert result == expected_playlist
        mock_playlist_service.create_playlist.assert_called_once_with('New Playlist', 'Description')

    @pytest.mark.asyncio
    async def test_create_playlist_use_case_empty_name(self, service, mock_playlist_service):
        """Test creating a playlist with empty name."""
        with pytest.raises(BusinessLogicError, match="Playlist name is required"):
            await service.create_playlist_use_case('')

        with pytest.raises(BusinessLogicError, match="Playlist name is required"):
            await service.create_playlist_use_case('   ')

    @pytest.mark.asyncio
    async def test_update_playlist_use_case_success(self, service, mock_playlist_service):
        """Test successful playlist update."""
        updates = {'title': 'Updated Title'}
        expected_playlist = {'id': 'playlist-1', 'title': 'Updated Title'}
        mock_playlist_service.update_playlist.return_value = expected_playlist

        result = await service.update_playlist_use_case('playlist-1', updates)

        assert result == expected_playlist

    @pytest.mark.asyncio
    async def test_update_playlist_use_case_empty_title(self, service, mock_playlist_service):
        """Test updating a playlist with empty title."""
        updates = {'title': '   '}

        with pytest.raises(BusinessLogicError, match="Playlist title cannot be empty"):
            await service.update_playlist_use_case('playlist-1', updates)

    @pytest.mark.asyncio
    async def test_delete_playlist_use_case_success(self, service, mock_playlist_service):
        """Test successful playlist deletion."""
        mock_playlist_service.delete_playlist.return_value = True

        result = await service.delete_playlist_use_case('playlist-1')

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_playlist_use_case_failure(self, service, mock_playlist_service):
        """Test playlist deletion failure."""
        mock_playlist_service.delete_playlist.return_value = False

        with pytest.raises(BusinessLogicError, match="Failed to delete playlist"):
            await service.delete_playlist_use_case('playlist-1')

    @pytest.mark.asyncio
    async def test_add_track_use_case_success(self, service, mock_track_service):
        """Test successful track addition."""
        track_data = {'title': 'New Track', 'filename': 'track.mp3'}
        expected_track = {'id': 'track-id', 'title': 'New Track'}
        mock_track_service.add_track.return_value = expected_track

        result = await service.add_track_use_case('playlist-1', track_data)

        assert result == expected_track

    @pytest.mark.asyncio
    async def test_add_track_use_case_no_title(self, service, mock_track_service):
        """Test adding a track without title."""
        track_data = {'filename': 'track.mp3'}

        with pytest.raises(BusinessLogicError, match="Track title is required"):
            await service.add_track_use_case('playlist-1', track_data)

    @pytest.mark.asyncio
    async def test_reorder_tracks_use_case_success(self, service, mock_track_service):
        """Test successful track reordering."""
        track_ids = ['track-2', 'track-1', 'track-3']
        mock_track_service.reorder_tracks.return_value = True

        result = await service.reorder_tracks_use_case('playlist-1', track_ids)

        assert result is True

    @pytest.mark.asyncio
    async def test_reorder_tracks_use_case_empty_list(self, service, mock_track_service):
        """Test reordering with empty track list."""
        with pytest.raises(BusinessLogicError, match="Track IDs list cannot be empty"):
            await service.reorder_tracks_use_case('playlist-1', [])

    @pytest.mark.asyncio
    async def test_get_next_track_use_case(self, service, mock_track_service):
        """Test getting next track."""
        expected_track = {'id': 'track-2', 'title': 'Next Track'}
        mock_track_service.get_next_track.return_value = expected_track

        result = await service.get_next_track_use_case('playlist-1', 'track-1')

        assert result == expected_track

    @pytest.mark.asyncio
    async def test_get_previous_track_use_case(self, service, mock_track_service):
        """Test getting previous track."""
        expected_track = {'id': 'track-1', 'title': 'Previous Track'}
        mock_track_service.get_previous_track.return_value = expected_track

        result = await service.get_previous_track_use_case('playlist-1', 'track-2')

        assert result == expected_track

    @pytest.mark.asyncio
    async def test_sync_filesystem_use_case(self, service, mock_playlist_service):
        """Test filesystem synchronization."""
        expected_stats = {
            'playlists_added': 5,
            'tracks_added': 20,
            'playlists_scanned': 10
        }
        mock_playlist_service.sync_with_filesystem.return_value = expected_stats

        result = await service.sync_filesystem_use_case('/uploads')

        assert result == expected_stats

    @pytest.mark.asyncio
    async def test_associate_nfc_tag_use_case(self, service, mock_playlist_service):
        """Test NFC tag association."""
        mock_playlist_service.associate_nfc_tag.return_value = True

        result = await service.associate_nfc_tag_use_case('playlist-1', 'nfc-123')

        assert result is True

    @pytest.mark.asyncio
    async def test_get_playlist_by_nfc_use_case(self, service, mock_playlist_service):
        """Test getting playlist by NFC tag."""
        expected_playlist = {'id': 'playlist-1', 'title': 'NFC Playlist'}
        mock_playlist_service.get_playlist_by_nfc.return_value = expected_playlist

        result = await service.get_playlist_by_nfc_use_case('nfc-123')

        assert result == expected_playlist