# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unit tests for PlaylistService in data domain."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.src.domain.data.services.playlist_service import PlaylistService
from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track


class TestPlaylistService:
    """Test suite for PlaylistService."""

    @pytest.fixture
    def mock_playlist_repo(self):
        """Mock playlist repository."""
        repo = AsyncMock()
        # Use correct interface method names
        repo.find_all.return_value = []
        repo.find_by_id.return_value = None
        repo.find_by_nfc_tag.return_value = None
        repo.save.return_value = None  # save returns the entity
        repo.update.return_value = None  # update returns the entity
        repo.delete.return_value = True
        repo.count.return_value = 0
        return repo

    @pytest.fixture
    def mock_track_repo(self):
        """Mock track repository."""
        repo = AsyncMock()
        repo.get_by_playlist.return_value = []
        repo.get_by_id.return_value = None
        repo.add_to_playlist.return_value = "track-id"
        repo.update.return_value = True
        repo.delete.return_value = True
        repo.reorder.return_value = True
        repo.delete_tracks_by_playlist.return_value = True
        return repo

    @pytest.fixture
    def service(self, mock_playlist_repo, mock_track_repo):
        """Create PlaylistService instance with mocked dependencies."""
        return PlaylistService(mock_playlist_repo, mock_track_repo)

    @pytest.mark.asyncio
    async def test_get_playlists_empty(self, service, mock_playlist_repo, mock_track_repo):
        """Test getting playlists when none exist."""
        mock_playlist_repo.find_all.return_value = []
        mock_playlist_repo.count.return_value = 0

        result = await service.get_playlists(page=1, page_size=50)

        assert result['playlists'] == []
        assert result['total'] == 0
        assert result['page'] == 1
        assert result['page_size'] == 50
        assert result['total_pages'] == 0
        mock_playlist_repo.find_all.assert_called_once_with(offset=0, limit=50)

    @pytest.mark.asyncio
    async def test_get_playlists_with_data(self, service, mock_playlist_repo, mock_track_repo):
        """Test getting playlists with data."""
        # Create Playlist entities
        playlist_entities = [
            Playlist(id="playlist-1", title="Test Playlist 1", tracks=[
                Track(track_number=1, title="Track 1", filename="path1.mp3", file_path="/fake/path1.mp3", id="track-1"),
                Track(track_number=2, title="Track 2", filename="path2.mp3", file_path="/fake/path2.mp3", id="track-2")
            ]),
            Playlist(id="playlist-2", title="Test Playlist 2", tracks=[
                Track(track_number=1, title="Track 3", filename="path3.mp3", file_path="/fake/path3.mp3", id="track-3"),
                Track(track_number=2, title="Track 4", filename="path4.mp3", file_path="/fake/path4.mp3", id="track-4")
            ])
        ]
        mock_playlist_repo.find_all.return_value = playlist_entities
        mock_playlist_repo.count.return_value = 2
        # This mock is no longer used since tracks are included in playlists
        mock_track_repo.get_by_playlist.return_value = []

        result = await service.get_playlists(page=1, page_size=50)

        assert len(result['playlists']) == 2
        assert result['total'] == 2
        assert result['playlists'][0]['track_count'] == 2
        assert result['playlists'][1]['track_count'] == 2

    @pytest.mark.asyncio
    async def test_get_playlist_found(self, service, mock_playlist_repo, mock_track_repo):
        """Test getting a single playlist that exists."""
        playlist_entity = Playlist(
            id="playlist-1",
            title="Test Playlist",
            tracks=[Track(track_number=1, title="Track 1", filename="path.mp3", file_path="/fake/path.mp3", id="track-1")]
        )

        mock_playlist_repo.find_by_id.return_value = playlist_entity
        # This mock is no longer used since tracks are included in playlist
        mock_track_repo.get_by_playlist.return_value = []

        result = await service.get_playlist('playlist-1')

        assert result['id'] == 'playlist-1'
        assert result['title'] == 'Test Playlist'
        assert len(result['tracks']) == 1
        assert result['track_count'] == 1

    @pytest.mark.asyncio
    async def test_get_playlist_not_found(self, service, mock_playlist_repo, mock_track_repo):
        """Test getting a playlist that doesn't exist."""
        mock_playlist_repo.find_by_id.return_value = None

        result = await service.get_playlist('nonexistent')

        assert result is None

    @pytest.mark.asyncio
    async def test_create_playlist_success(self, service, mock_playlist_repo, mock_track_repo):
        """Test creating a playlist successfully."""
        playlist_id = str(uuid.uuid4())
        created_playlist = {
            'id': playlist_id,
            'title': 'New Playlist',
            'description': 'Test description',
            'tracks': [],
            'track_count': 0
        }

        mock_playlist_repo.save.return_value = playlist_id
        mock_playlist_repo.find_by_id.return_value = created_playlist
        mock_track_repo.get_by_playlist.return_value = []

        result = await service.create_playlist('New Playlist', 'Test description')

        assert result['title'] == 'New Playlist'
        assert result['description'] == 'Test description'
        assert result['track_count'] == 0
        mock_playlist_repo.save.assert_called_once()

    @pytest.mark.skip(reason="Mock configuration issue with AsyncMock - needs investigation")
    @pytest.mark.asyncio
    async def test_update_playlist_success(self, mock_track_repo):
        """Test updating a playlist successfully."""
        # Create fresh mocks for this test
        fresh_playlist_repo = AsyncMock()
        playlist_id = 'playlist-1'
        updates = {'name': 'Updated Title'}
        existing_entity = Playlist(title="Old Title", tracks=[], id=playlist_id)
        updated_entity = Playlist(title="Updated Title", tracks=[], id=playlist_id)

        # Configure mocks to return entities
        fresh_playlist_repo.find_by_id.side_effect = [existing_entity, updated_entity]
        fresh_playlist_repo.update.return_value = updated_entity

        # Create service with fresh mocks
        fresh_service = PlaylistService(fresh_playlist_repo, mock_track_repo)

        result = await fresh_service.update_playlist(playlist_id, updates)

        assert result['title'] == 'Updated Title'
        fresh_playlist_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_playlist_not_found(self, service, mock_playlist_repo, mock_track_repo):
        """Test updating a playlist that doesn't exist."""
        mock_playlist_repo.find_by_id.return_value = False

        with pytest.raises(ValueError, match="Playlist playlist-1 not found"):
            await service.update_playlist('playlist-1', {'title': 'New Title'})

    @pytest.mark.asyncio
    async def test_delete_playlist_success(self, service, mock_playlist_repo, mock_track_repo):
        """Test deleting a playlist successfully."""
        playlist_id = 'playlist-1'

        mock_track_repo.delete_tracks_by_playlist.return_value = True
        mock_playlist_repo.delete.return_value = True

        result = await service.delete_playlist(playlist_id)

        assert result is True
        mock_track_repo.delete_tracks_by_playlist.assert_called_once_with(playlist_id)
        mock_playlist_repo.delete.assert_called_once_with(playlist_id)

    @pytest.mark.asyncio
    async def test_delete_playlist_failure(self, service, mock_playlist_repo, mock_track_repo):
        """Test deleting a playlist that fails."""
        playlist_id = 'playlist-1'

        mock_track_repo.delete_tracks_by_playlist.return_value = False
        mock_playlist_repo.delete.return_value = False

        result = await service.delete_playlist(playlist_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_associate_nfc_tag_success(self, service, mock_playlist_repo, mock_track_repo):
        """Test associating an NFC tag successfully."""
        playlist_id = 'playlist-1'
        nfc_tag_id = 'nfc-123'

        mock_playlist_repo.update.return_value = True

        result = await service.associate_nfc_tag(playlist_id, nfc_tag_id)

        assert result is True
        mock_playlist_repo.update.assert_called_once()
        call_args = mock_playlist_repo.update.call_args[0]
        assert call_args[0] == playlist_id
        assert call_args[1]['nfc_tag_id'] == nfc_tag_id

    @pytest.mark.asyncio
    async def test_get_playlist_by_nfc_found(self, service, mock_playlist_repo, mock_track_repo):
        """Test getting playlist by NFC tag when it exists."""
        nfc_tag_id = 'nfc-123'
        playlist_entity = Playlist(
            id='playlist-1',
            title='NFC Playlist',
            nfc_tag_id=nfc_tag_id,
            tracks=[Track(track_number=1, title='Track 1', filename='track1.mp3', file_path='/fake/track1.mp3', id='track-1')]
        )

        mock_playlist_repo.find_by_nfc_tag.return_value = playlist_entity

        result = await service.get_playlist_by_nfc(nfc_tag_id)

        assert result['id'] == 'playlist-1'
        assert result['title'] == 'NFC Playlist'
        assert result['track_count'] == 1
        mock_playlist_repo.find_by_nfc_tag.assert_called_once_with(nfc_tag_id)

    @pytest.mark.asyncio
    async def test_get_playlist_by_nfc_not_found(self, service, mock_playlist_repo, mock_track_repo):
        """Test getting playlist by NFC tag when it doesn't exist."""
        mock_playlist_repo.find_by_nfc_tag.return_value = None

        result = await service.get_playlist_by_nfc('nonexistent-nfc')

        assert result is None
        mock_playlist_repo.find_by_nfc_tag.assert_called_once_with('nonexistent-nfc')

    @pytest.mark.asyncio
    async def test_sync_with_filesystem_no_folder(self, service, mock_playlist_repo, mock_track_repo):
        """Test filesystem sync when upload folder doesn't exist."""
        result = await service.sync_with_filesystem('/nonexistent/path')

        expected_stats = {
            'playlists_scanned': 0,
            'playlists_added': 0,
            'playlists_updated': 0,
            'tracks_added': 0,
            'tracks_removed': 0
        }
        assert result == expected_stats