# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unit tests for TrackService in data domain."""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from app.src.domain.data.services.track_service import TrackService


class TestTrackService:
    """Test suite for TrackService."""

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
        repo.delete_by_playlist.return_value = 0
        return repo

    @pytest.fixture
    def mock_playlist_repo(self):
        """Mock playlist repository."""
        repo = AsyncMock()
        repo.exists.return_value = True
        return repo

    @pytest.fixture
    def service(self, mock_track_repo, mock_playlist_repo):
        """Create TrackService instance with mocked dependencies."""
        return TrackService(mock_track_repo, mock_playlist_repo)

    @pytest.mark.asyncio
    async def test_get_tracks_success(self, service, mock_track_repo, mock_playlist_repo):
        """Test getting tracks for a playlist."""
        playlist_id = 'playlist-1'
        tracks_data = [
            {'id': 'track-1', 'track_number': 2, 'title': 'Track 2'},
            {'id': 'track-2', 'track_number': 1, 'title': 'Track 1'}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = tracks_data

        result = await service.get_tracks(playlist_id)

        # Should be sorted by track_number
        assert len(result) == 2
        assert result[0]['track_number'] == 1
        assert result[1]['track_number'] == 2

    @pytest.mark.asyncio
    async def test_get_tracks_playlist_not_found(self, service, mock_track_repo, mock_playlist_repo):
        """Test getting tracks for a playlist that doesn't exist."""
        mock_playlist_repo.exists.return_value = False

        with pytest.raises(ValueError, match="Playlist playlist-1 not found"):
            await service.get_tracks('playlist-1')

    @pytest.mark.asyncio
    async def test_add_track_success(self, service, mock_track_repo, mock_playlist_repo):
        """Test adding a track to a playlist."""
        playlist_id = 'playlist-1'
        track_data = {
            'title': 'New Track',
            'filename': 'track.mp3',
            'duration_ms': 180000
        }
        created_track = {
            'id': 'track-id',
            'title': 'New Track',
            'playlist_id': playlist_id
        }

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = []  # No existing tracks
        mock_track_repo.add_to_playlist.return_value = 'track-id'
        mock_track_repo.get_by_id.return_value = created_track

        result = await service.add_track(playlist_id, track_data)

        assert result['title'] == 'New Track'
        mock_track_repo.add_to_playlist.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_track_playlist_not_found(self, service, mock_track_repo, mock_playlist_repo):
        """Test adding a track to a playlist that doesn't exist."""
        mock_playlist_repo.exists.return_value = False

        with pytest.raises(ValueError, match="Playlist playlist-1 not found"):
            await service.add_track('playlist-1', {'title': 'Track'})

    @pytest.mark.asyncio
    async def test_add_track_with_existing_tracks(self, service, mock_track_repo, mock_playlist_repo):
        """Test adding a track when playlist already has tracks."""
        playlist_id = 'playlist-1'
        track_data = {'title': 'New Track'}
        existing_tracks = [
            {'id': 'track-1', 'track_number': 1},
            {'id': 'track-2', 'track_number': 2}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = existing_tracks
        mock_track_repo.add_to_playlist.return_value = 'track-id'
        mock_track_repo.get_by_id.return_value = {'id': 'track-id', 'title': 'New Track'}

        await service.add_track(playlist_id, track_data)

        # Check that track_number is set correctly (should be 3)
        call_args = mock_track_repo.add_to_playlist.call_args[0]
        assert call_args[1]['track_number'] == 3

    @pytest.mark.asyncio
    async def test_update_track_success(self, service, mock_track_repo, mock_playlist_repo):
        """Test updating a track successfully."""
        track_id = 'track-1'
        updates = {'title': 'Updated Track'}
        existing_track = {'id': track_id, 'title': 'Old Track'}
        updated_track = {'id': track_id, 'title': 'Updated Track'}

        mock_track_repo.get_by_id.side_effect = [existing_track, updated_track]
        mock_track_repo.update.return_value = True

        result = await service.update_track(track_id, updates)

        assert result['title'] == 'Updated Track'
        mock_track_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_track_not_found(self, service, mock_track_repo, mock_playlist_repo):
        """Test updating a track that doesn't exist."""
        mock_track_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="Track track-1 not found"):
            await service.update_track('track-1', {'title': 'New Title'})

    @pytest.mark.asyncio
    async def test_delete_track_success(self, service, mock_track_repo, mock_playlist_repo):
        """Test deleting a track successfully."""
        track_id = 'track-1'
        mock_track_repo.delete.return_value = True

        result = await service.delete_track(track_id)

        assert result is True
        mock_track_repo.delete.assert_called_once_with(track_id)

    @pytest.mark.asyncio
    async def test_delete_track_failure(self, service, mock_track_repo, mock_playlist_repo):
        """Test deleting a track that fails."""
        track_id = 'track-1'
        mock_track_repo.delete.return_value = False

        result = await service.delete_track(track_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_reorder_tracks_success(self, service, mock_track_repo, mock_playlist_repo):
        """Test reordering tracks successfully."""
        playlist_id = 'playlist-1'
        track_ids = ['track-2', 'track-1', 'track-3']
        existing_tracks = [
            {'id': 'track-1', 'track_number': 1},
            {'id': 'track-2', 'track_number': 2},
            {'id': 'track-3', 'track_number': 3}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = existing_tracks
        mock_track_repo.reorder.return_value = True

        result = await service.reorder_tracks(playlist_id, track_ids)

        assert result is True
        mock_track_repo.reorder.assert_called_once()

    @pytest.mark.asyncio
    async def test_reorder_tracks_playlist_not_found(self, service, mock_track_repo, mock_playlist_repo):
        """Test reordering tracks for a playlist that doesn't exist."""
        mock_playlist_repo.exists.return_value = False

        with pytest.raises(ValueError, match="Playlist playlist-1 not found"):
            await service.reorder_tracks('playlist-1', ['track-1'])

    @pytest.mark.asyncio
    async def test_reorder_tracks_invalid_track(self, service, mock_track_repo, mock_playlist_repo):
        """Test reordering tracks with a track that doesn't belong to the playlist."""
        playlist_id = 'playlist-1'
        track_ids = ['track-1', 'track-invalid']
        existing_tracks = [{'id': 'track-1', 'track_number': 1}]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = existing_tracks

        with pytest.raises(ValueError, match="Track track-invalid does not belong to playlist"):
            await service.reorder_tracks(playlist_id, track_ids)

    @pytest.mark.asyncio
    async def test_get_next_track_first_track(self, service, mock_track_repo, mock_playlist_repo):
        """Test getting the first track when no current track is specified."""
        playlist_id = 'playlist-1'
        tracks = [
            {'id': 'track-1', 'track_number': 1, 'title': 'Track 1'},
            {'id': 'track-2', 'track_number': 2, 'title': 'Track 2'}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = tracks

        result = await service.get_next_track(playlist_id)

        assert result['id'] == 'track-1'

    @pytest.mark.asyncio
    async def test_get_next_track_middle(self, service, mock_track_repo, mock_playlist_repo):
        """Test getting the next track from the middle of a playlist."""
        playlist_id = 'playlist-1'
        tracks = [
            {'id': 'track-1', 'track_number': 1, 'title': 'Track 1'},
            {'id': 'track-2', 'track_number': 2, 'title': 'Track 2'},
            {'id': 'track-3', 'track_number': 3, 'title': 'Track 3'}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = tracks

        result = await service.get_next_track(playlist_id, 'track-2')

        assert result['id'] == 'track-3'

    @pytest.mark.asyncio
    async def test_get_next_track_last(self, service, mock_track_repo, mock_playlist_repo):
        """Test getting the next track when at the end of a playlist."""
        playlist_id = 'playlist-1'
        tracks = [
            {'id': 'track-1', 'track_number': 1, 'title': 'Track 1'},
            {'id': 'track-2', 'track_number': 2, 'title': 'Track 2'}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = tracks

        result = await service.get_next_track(playlist_id, 'track-2')

        assert result is None

    @pytest.mark.asyncio
    async def test_get_previous_track_last_track(self, service, mock_track_repo, mock_playlist_repo):
        """Test getting the last track when no current track is specified."""
        playlist_id = 'playlist-1'
        tracks = [
            {'id': 'track-1', 'track_number': 1, 'title': 'Track 1'},
            {'id': 'track-2', 'track_number': 2, 'title': 'Track 2'}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = tracks

        result = await service.get_previous_track(playlist_id)

        assert result['id'] == 'track-2'

    @pytest.mark.asyncio
    async def test_get_previous_track_middle(self, service, mock_track_repo, mock_playlist_repo):
        """Test getting the previous track from the middle of a playlist."""
        playlist_id = 'playlist-1'
        tracks = [
            {'id': 'track-1', 'track_number': 1, 'title': 'Track 1'},
            {'id': 'track-2', 'track_number': 2, 'title': 'Track 2'},
            {'id': 'track-3', 'track_number': 3, 'title': 'Track 3'}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = tracks

        result = await service.get_previous_track(playlist_id, 'track-2')

        assert result['id'] == 'track-1'

    @pytest.mark.asyncio
    async def test_get_previous_track_first(self, service, mock_track_repo, mock_playlist_repo):
        """Test getting the previous track when at the beginning of a playlist."""
        playlist_id = 'playlist-1'
        tracks = [
            {'id': 'track-1', 'track_number': 1, 'title': 'Track 1'},
            {'id': 'track-2', 'track_number': 2, 'title': 'Track 2'}
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = tracks

        result = await service.get_previous_track(playlist_id, 'track-1')

        assert result is None