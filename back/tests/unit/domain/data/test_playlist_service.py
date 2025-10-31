# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unit tests for PlaylistService in data domain."""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
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
        mock_track_repo.get_tracks_by_playlist.return_value = []

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
        mock_track_repo.get_tracks_by_playlist.return_value = []

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
        mock_track_repo.get_tracks_by_playlist.return_value = []

        result = await service.create_playlist('New Playlist', 'Test description')

        assert result['title'] == 'New Playlist'
        assert result['description'] == 'Test description'
        assert result['track_count'] == 0
        mock_playlist_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_playlist_success(self, mock_track_repo):
        """Test updating a playlist successfully."""
        # Create fresh mocks for this test
        fresh_playlist_repo = AsyncMock()
        playlist_id = 'playlist-1'
        updates = {'title': 'Updated Title'}

        # Create playlist entities
        existing_entity = Playlist(title="Old Title", tracks=[], id=playlist_id)
        updated_entity = Playlist(title="Updated Title", tracks=[], id=playlist_id)

        # Track call count to return different values
        call_count = {'count': 0}

        async def mock_find_by_id(pid):
            """Mock that returns different values on subsequent calls."""
            call_count['count'] += 1
            if call_count['count'] == 1:
                # First call in update_playlist - return existing entity
                return existing_entity
            else:
                # Second call in get_playlist - return updated entity
                return updated_entity

        # Configure mocks
        fresh_playlist_repo.find_by_id = mock_find_by_id
        fresh_playlist_repo.update = AsyncMock(return_value=updated_entity)

        # Create service with fresh mocks
        fresh_service = PlaylistService(fresh_playlist_repo, mock_track_repo)

        result = await fresh_service.update_playlist(playlist_id, updates)

        # Verify the result contains the updated data
        assert result['title'] == 'Updated Title'
        assert result['id'] == playlist_id
        assert result['track_count'] == 0
        # Verify update was called with the updated entity
        assert fresh_playlist_repo.update.called

    @pytest.mark.asyncio
    async def test_update_playlist_not_found(self, service, mock_playlist_repo, mock_track_repo):
        """Test updating a playlist that doesn't exist."""
        mock_playlist_repo.find_by_id.return_value = None

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

    @pytest.mark.asyncio
    async def test_update_playlist_with_title_change_triggers_folder_rename(self, service, mock_playlist_repo, mock_track_repo, tmp_path, monkeypatch):
        """Test that updating playlist title triggers folder rename."""
        from pathlib import Path
        import app.src.config

        # Setup temporary upload folder
        upload_folder = tmp_path / "uploads"
        upload_folder.mkdir()
        old_folder = upload_folder / "Old_Title"
        old_folder.mkdir()

        # Mock app config to use temp folder
        mock_config = MagicMock()
        mock_config.upload_folder = str(upload_folder)
        monkeypatch.setattr('app.src.domain.data.services.playlist_service.app_config', mock_config)

        # Create test playlist entity
        playlist_id = 'playlist-1'
        old_entity = Playlist(
            id=playlist_id,
            title='Old Title',
            path='Old_Title',
            tracks=[]
        )
        updated_entity = Playlist(
            id=playlist_id,
            title='New Title',
            path='Old_Title',  # Path not yet updated
            tracks=[]
        )

        # Setup mocks
        mock_playlist_repo.find_by_id.return_value = old_entity
        mock_playlist_repo.update.return_value = updated_entity
        mock_track_repo.get_tracks_by_playlist.return_value = []

        # Perform update
        updates = {'title': 'New Title'}
        result = await service.update_playlist(playlist_id, updates)

        # Verify folder was renamed
        new_folder = upload_folder / "New_Title"
        assert new_folder.exists(), "New folder should exist after rename"
        assert not old_folder.exists(), "Old folder should not exist after rename"
        assert result['title'] == 'New Title'

    @pytest.mark.asyncio
    async def test_rename_playlist_folder_when_old_folder_not_found(self, service, tmp_path, monkeypatch):
        """Test _rename_playlist_folder when old folder doesn't exist."""
        upload_folder = tmp_path / "uploads"
        upload_folder.mkdir()

        mock_config = MagicMock()
        mock_config.upload_folder = str(upload_folder)
        monkeypatch.setattr('app.src.domain.data.services.playlist_service.app_config', mock_config)

        playlist = Playlist(
            id='playlist-1',
            title='New Title',
            path='nonexistent_folder',
            tracks=[]
        )

        # Should not raise error, just log warning
        await service._rename_playlist_folder(playlist, 'Old Title', 'nonexistent_folder')

        # Verify no folder was created
        new_folder = upload_folder / "New_Title"
        assert not new_folder.exists()

    @pytest.mark.asyncio
    async def test_rename_playlist_folder_when_target_exists(self, service, tmp_path, monkeypatch):
        """Test _rename_playlist_folder when target folder already exists."""
        upload_folder = tmp_path / "uploads"
        upload_folder.mkdir()
        old_folder = upload_folder / "Old_Title"
        old_folder.mkdir()
        target_folder = upload_folder / "New_Title"
        target_folder.mkdir()

        mock_config = MagicMock()
        mock_config.upload_folder = str(upload_folder)
        monkeypatch.setattr('app.src.domain.data.services.playlist_service.app_config', mock_config)

        playlist = Playlist(
            id='playlist-1',
            title='New Title',
            path='Old_Title',
            tracks=[]
        )

        # Should not raise error or rename when target exists
        await service._rename_playlist_folder(playlist, 'Old Title', 'Old_Title')

        # Both folders should still exist
        assert old_folder.exists()
        assert target_folder.exists()

    @pytest.mark.asyncio
    async def test_update_track_file_paths_after_rename(self, service, mock_playlist_repo, mock_track_repo, tmp_path):
        """Test _update_track_file_paths updates track paths correctly."""
        from pathlib import Path

        playlist_id = 'playlist-1'
        old_folder = tmp_path / "Old_Title"
        new_folder = tmp_path / "New_Title"

        # Create mock tracks with old paths
        tracks = [
            Track(
                id='track-1',
                track_number=1,
                title='Track 1',
                filename='track1.mp3',
                file_path=str(old_folder / 'track1.mp3')
            ),
            Track(
                id='track-2',
                track_number=2,
                title='Track 2',
                filename='track2.mp3',
                file_path=str(old_folder / 'track2.mp3')
            )
        ]

        mock_track_repo.get_by_playlist.return_value = tracks
        mock_track_repo.update.return_value = True

        # Call the method
        await service._update_track_file_paths(playlist_id, old_folder, new_folder)

        # Verify update was called for each track with new path
        assert mock_track_repo.update.call_count == 2

        # Verify the updated paths
        calls = mock_track_repo.update.call_args_list
        assert str(new_folder / 'track1.mp3') in str(calls[0])
        assert str(new_folder / 'track2.mp3') in str(calls[1])

    @pytest.mark.asyncio
    async def test_update_track_file_paths_handles_dict_tracks(self, service, mock_track_repo, tmp_path):
        """Test _update_track_file_paths handles dict-based tracks."""
        playlist_id = 'playlist-1'
        old_folder = tmp_path / "Old_Title"
        new_folder = tmp_path / "New_Title"

        # Create dict-based tracks
        tracks = [
            {
                'id': 'track-1',
                'track_number': 1,
                'title': 'Track 1',
                'filename': 'track1.mp3',
                'file_path': str(old_folder / 'track1.mp3')
            }
        ]

        mock_track_repo.get_by_playlist.return_value = tracks
        mock_track_repo.update.return_value = True

        await service._update_track_file_paths(playlist_id, old_folder, new_folder)

        # Verify update was called
        mock_track_repo.update.assert_called_once()

    # Note: delete_playlist with folder cleanup is tested via test_cleanup_playlist_folder_with_multiple_possible_paths

    @pytest.mark.asyncio
    async def test_cleanup_playlist_folder_with_multiple_possible_paths(self, service, tmp_path, monkeypatch):
        """Test _cleanup_playlist_folder tries multiple folder name formats."""
        upload_folder = tmp_path / "uploads"
        upload_folder.mkdir()

        # Create folder with normalized name
        playlist_folder = upload_folder / "My_Cool_Playlist"
        playlist_folder.mkdir()

        mock_config = MagicMock()
        mock_config.upload_folder = str(upload_folder)
        monkeypatch.setattr('app.src.domain.data.services.playlist_service.app_config', mock_config)

        playlist = Playlist(
            id='playlist-1',
            title='My Cool Playlist',  # Original title with spaces
            path='My_Cool_Playlist',   # Normalized path
            tracks=[]
        )

        await service._cleanup_playlist_folder(playlist)

        assert not playlist_folder.exists(), "Playlist folder should be cleaned up"

    @pytest.mark.asyncio
    async def test_cleanup_playlist_folder_fallback_to_id(self, service, tmp_path, monkeypatch):
        """Test _cleanup_playlist_folder falls back to ID when title-based folders not found."""
        upload_folder = tmp_path / "uploads"
        upload_folder.mkdir()

        # Create folder using playlist ID
        playlist_id = 'unique-playlist-id'
        id_folder = upload_folder / playlist_id
        id_folder.mkdir()

        mock_config = MagicMock()
        mock_config.upload_folder = str(upload_folder)
        monkeypatch.setattr('app.src.domain.data.services.playlist_service.app_config', mock_config)

        playlist = Playlist(
            id=playlist_id,
            title='Some Title',
            path=None,  # No path stored
            tracks=[]
        )

        await service._cleanup_playlist_folder(playlist)

        assert not id_folder.exists(), "ID-based folder should be cleaned up"

    @pytest.mark.asyncio
    async def test_sync_with_filesystem_with_directories(self, service, mock_playlist_repo, mock_track_repo, tmp_path):
        """Test sync_with_filesystem with actual directories and files."""
        upload_folder = tmp_path / "uploads"
        upload_folder.mkdir()

        # Create playlist directories
        playlist1_dir = upload_folder / "Playlist 1"
        playlist1_dir.mkdir()
        (playlist1_dir / "track1.mp3").write_text("audio data 1")
        (playlist1_dir / "track2.mp3").write_text("audio data 2")

        playlist2_dir = upload_folder / "Playlist 2"
        playlist2_dir.mkdir()
        (playlist2_dir / "song.flac").write_text("audio data 3")

        # Mock repository responses
        mock_playlist_repo.get_all.return_value = []
        mock_track_repo.get_tracks_by_playlist.return_value = []

        # Mock create_playlist to return playlist data
        created_count = {'count': 0}
        async def mock_create(name, description):
            created_count['count'] += 1
            return {
                'id': f'playlist-{created_count["count"]}',
                'title': name,
                'description': description,
                'tracks': []
            }

        service.create_playlist = mock_create

        result = await service.sync_with_filesystem(str(upload_folder))

        assert result['playlists_scanned'] == 2
        assert result['playlists_added'] == 2
        assert result['tracks_added'] == 3

    @pytest.mark.asyncio
    async def test_sync_playlist_tracks_adds_new_tracks(self, service, mock_track_repo, tmp_path):
        """Test _sync_playlist_tracks adds new audio files."""
        playlist_id = 'playlist-1'
        playlist_dir = tmp_path / "Test_Playlist"
        playlist_dir.mkdir()

        # Create audio files
        (playlist_dir / "track1.mp3").write_text("audio 1")
        (playlist_dir / "track2.flac").write_text("audio 2")
        (playlist_dir / "readme.txt").write_text("not audio")  # Should be ignored

        # No existing tracks
        mock_track_repo.get_tracks_by_playlist.return_value = []
        mock_track_repo.add_track_to_playlist.return_value = True

        stats = {
            'tracks_added': 0,
            'tracks_removed': 0
        }

        await service._sync_playlist_tracks(playlist_id, playlist_dir, stats)

        assert stats['tracks_added'] == 2
        assert mock_track_repo.add_track_to_playlist.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_playlist_tracks_removes_deleted_tracks(self, service, mock_track_repo, tmp_path):
        """Test _sync_playlist_tracks removes tracks for deleted files."""
        playlist_id = 'playlist-1'
        playlist_dir = tmp_path / "Test_Playlist"
        playlist_dir.mkdir()

        # Only one file exists now
        (playlist_dir / "track1.mp3").write_text("audio 1")

        # Mock existing tracks - track2 no longer exists on disk
        from app.src.domain.data.models.track import Track
        existing_tracks = [
            Track(id='track-1', track_number=1, title='Track 1', filename='track1.mp3', file_path='/tmp/track1.mp3'),
            Track(id='track-2', track_number=2, title='Track 2', filename='track2.mp3', file_path='/tmp/track2.mp3')  # File deleted
        ]
        mock_track_repo.get_tracks_by_playlist.return_value = existing_tracks
        mock_track_repo.delete_track.return_value = True

        stats = {
            'tracks_added': 0,
            'tracks_removed': 0
        }

        await service._sync_playlist_tracks(playlist_id, playlist_dir, stats)

        assert stats['tracks_removed'] == 1
        mock_track_repo.delete_track.assert_called_once_with('track-2')

    @pytest.mark.asyncio
    async def test_get_playlists_pagination_edge_cases(self, service, mock_playlist_repo, mock_track_repo):
        """Test pagination edge cases in get_playlists."""
        # Create 5 test playlists
        all_playlists = [
            Playlist(id=f"playlist-{i}", title=f"Playlist {i}", tracks=[])
            for i in range(1, 6)
        ]

        # Test page 1 with page_size 2
        mock_playlist_repo.find_all.return_value = all_playlists[:2]
        mock_playlist_repo.count.return_value = 5

        result = await service.get_playlists(page=1, page_size=2)

        assert len(result['playlists']) == 2
        assert result['total'] == 5
        assert result['page'] == 1
        assert result['page_size'] == 2
        assert result['total_pages'] == 3
        mock_playlist_repo.find_all.assert_called_with(offset=0, limit=2)

        # Test page 3 (last page with 1 item)
        mock_playlist_repo.find_all.return_value = all_playlists[4:5]
        result = await service.get_playlists(page=3, page_size=2)

        assert len(result['playlists']) == 1
        assert result['page'] == 3
        mock_playlist_repo.find_all.assert_called_with(offset=4, limit=2)

    @pytest.mark.asyncio
    async def test_get_playlists_handles_none_entities(self, service, mock_playlist_repo, mock_track_repo):
        """Test get_playlists filters out None entities."""
        playlists_with_none = [
            Playlist(id="playlist-1", title="Valid Playlist", tracks=[]),
            None,
            Playlist(id="playlist-2", title="Another Valid", tracks=[])
        ]

        mock_playlist_repo.find_all.return_value = playlists_with_none
        mock_playlist_repo.count.return_value = 2

        result = await service.get_playlists()

        assert len(result['playlists']) == 2
        assert all(p is not None for p in result['playlists'])

    @pytest.mark.asyncio
    async def test_get_playlists_adds_title_field_compatibility(self, service, mock_playlist_repo, mock_track_repo):
        """Test get_playlists ensures title field exists for API compatibility."""
        # Create playlist entity (uses 'title' field)
        playlist = Playlist(id="playlist-1", title="Test Playlist", tracks=[])

        mock_playlist_repo.find_all.return_value = [playlist]
        mock_playlist_repo.count.return_value = 1

        result = await service.get_playlists()

        assert result['playlists'][0]['title'] == 'Test Playlist'

    @pytest.mark.asyncio
    async def test_update_playlist_update_fails(self, service, mock_playlist_repo, mock_track_repo):
        """Test update_playlist handles repository update failure."""
        playlist_id = 'playlist-1'
        existing_entity = Playlist(id=playlist_id, title="Old Title", tracks=[])

        mock_playlist_repo.find_by_id.return_value = existing_entity
        mock_playlist_repo.update.return_value = None  # Update failed

        with pytest.raises(RuntimeError, match=f"Failed to update playlist {playlist_id}"):
            await service.update_playlist(playlist_id, {'title': 'New Title'})