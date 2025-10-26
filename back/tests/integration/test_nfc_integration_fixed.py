# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Integration test to verify NFC functionality is properly fixed."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.src.application.controllers.playback_coordinator_controller import PlaybackCoordinator
from app.src.infrastructure.nfc.adapters.nfc_hardware_adapter import MockNfcHardwareAdapter


class TestNfcIntegration:
    """Test suite for NFC integration after fixes."""

    @pytest.mark.asyncio
    async def test_nfc_adapter_initialization(self):
        """Test that MockNfcHardwareAdapter properly initializes with start/stop methods."""
        adapter = MockNfcHardwareAdapter()

        # Verify start and stop methods exist
        assert hasattr(adapter, 'start')
        assert hasattr(adapter, 'stop')
        assert hasattr(adapter, 'start_detection')
        assert hasattr(adapter, 'stop_detection')

        # Test start method (legacy compatibility)
        await adapter.start()

        # Test stop method (legacy compatibility)
        await adapter.stop()

    @pytest.mark.asyncio
    async def test_playback_coordinator_handles_nfc_tag(self):
        """Test that PlaybackCoordinator properly handles NFC tag scans."""
        # Setup mocks
        mock_audio_backend = Mock()
        mock_playlist_service = Mock()
        mock_upload_folder = '/tmp/test'

        # Mock the data application service
        mock_data_service = AsyncMock()
        # The service now returns the playlist dict directly (not wrapped in status/playlist)
        mock_data_service.get_playlist_by_nfc_use_case = AsyncMock(return_value={
            "id": "playlist-123",
            "title": "Test Playlist",
            "name": "Test Playlist"
        })

        coordinator = PlaybackCoordinator(
            audio_backend=mock_audio_backend,
            playlist_service=mock_playlist_service,
            upload_folder=mock_upload_folder,
            data_application_service=mock_data_service
        )

        # Verify handle_tag_scanned method exists
        assert hasattr(coordinator, 'handle_tag_scanned')

        # Mock the load_playlist and start_playlist methods
        coordinator.load_playlist = AsyncMock(return_value=True)
        coordinator.start_playlist = Mock(return_value=True)

        # Test NFC tag scan handling
        await coordinator.handle_tag_scanned("tag-123")

        # Verify the service was called correctly
        mock_data_service.get_playlist_by_nfc_use_case.assert_called_once_with("tag-123")

        # Verify playlist loading was attempted
        coordinator.load_playlist.assert_called_once_with("playlist-123")
        coordinator.start_playlist.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_repository_track_methods_return_track_objects(self):
        """Test that repository methods return Track objects as expected."""
        from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
        from app.src.domain.data.models.track import Track

        with patch('app.src.infrastructure.repositories.pure_sqlite_playlist_repository.get_database_manager') as mock_get_db_manager:
            mock_db_service = Mock()
            mock_db_service.execute_query = Mock(return_value=[
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
            ])

            mock_db_manager = Mock()
            mock_db_manager.database_service = mock_db_service
            mock_get_db_manager.return_value = mock_db_manager

            repository = PureSQLitePlaylistRepository()

            # Test get_tracks_by_playlist returns Track objects
            tracks = await repository.get_tracks_by_playlist('playlist-1')

            assert len(tracks) == 1
            assert isinstance(tracks[0], Track)
            assert tracks[0].id == 'track-1'
            assert tracks[0].title == 'Track 1'

    @pytest.mark.asyncio
    async def test_track_service_handles_both_objects_and_dicts(self):
        """Test that TrackService handles both Track objects and dictionaries."""
        from app.src.domain.data.services.track_service import TrackService
        from app.src.domain.data.models.track import Track

        # Setup mocks
        mock_track_repo = AsyncMock()
        mock_playlist_repo = AsyncMock()

        service = TrackService(mock_track_repo, mock_playlist_repo)

        # Test with Track objects (as returned by new repository methods)
        track_objects = [
            Track(
                id='track-1',
                track_number=1,
                title='Track 1',
                filename='track1.mp3',
                file_path='/path/track1.mp3'
            ),
            Track(
                id='track-2',
                track_number=2,
                title='Track 2',
                filename='track2.mp3',
                file_path='/path/track2.mp3'
            )
        ]

        mock_playlist_repo.exists.return_value = True
        mock_track_repo.get_by_playlist.return_value = track_objects
        mock_track_repo.reorder.return_value = True

        # Test reorder_tracks with Track objects
        result = await service.reorder_tracks('playlist-1', ['track-1', 'track-2'])
        assert result is True

        # Test with dictionary objects (for backward compatibility)
        dict_tracks = [
            {'id': 'track-1', 'track_number': 1},
            {'id': 'track-2', 'track_number': 2}
        ]

        mock_track_repo.get_by_playlist.return_value = dict_tracks

        result = await service.reorder_tracks('playlist-1', ['track-1', 'track-2'])
        assert result is True

    def test_toggle_pause_starts_playback_when_inactive(self):
        """Test that toggle_pause starts playback when no audio is active."""
        # Setup mocks
        mock_audio_backend = Mock()
        mock_playlist_service = Mock()
        mock_upload_folder = '/tmp/test'

        coordinator = PlaybackCoordinator(
            audio_backend=mock_audio_backend,
            playlist_service=mock_playlist_service,
            upload_folder=mock_upload_folder
        )

        # Mock audio player state - no active audio
        coordinator._audio_player.is_playing = Mock(return_value=False)
        coordinator._audio_player.is_paused = Mock(return_value=False)
        coordinator._audio_player.play_file = Mock(return_value=True)

        # Mock current track
        mock_track = Mock()
        mock_track.file_path = '/test/track.mp3'
        mock_track.title = 'Test Track'
        mock_track.duration_ms = 180000

        coordinator._playlist_controller.get_current_track = Mock(return_value=mock_track)

        # Test toggle_pause - should start playback
        result = coordinator.toggle_pause()

        # Verify it attempted to start playback rather than toggle
        coordinator._audio_player.is_playing.assert_called()
        coordinator._audio_player.is_paused.assert_called()
        coordinator._playlist_controller.get_current_track.assert_called()
        coordinator._audio_player.play_file.assert_called_once_with('/test/track.mp3', 180000)

        assert result is True

    def test_toggle_pause_toggles_when_audio_active(self):
        """Test that toggle_pause toggles audio when there's active playback."""
        # Setup mocks
        mock_audio_backend = Mock()
        mock_playlist_service = Mock()
        mock_upload_folder = '/tmp/test'

        coordinator = PlaybackCoordinator(
            audio_backend=mock_audio_backend,
            playlist_service=mock_playlist_service,
            upload_folder=mock_upload_folder
        )

        # Mock audio player state - audio is playing
        coordinator._audio_player.is_playing = Mock(return_value=True)
        coordinator._audio_player.is_paused = Mock(return_value=False)
        coordinator._audio_player.toggle_pause = Mock(return_value=True)

        # Test toggle_pause - should call audio player's toggle_pause
        result = coordinator.toggle_pause()

        # Verify it called the audio player's toggle method
        coordinator._audio_player.is_playing.assert_called()
        coordinator._audio_player.toggle_pause.assert_called_once()

        assert result is True