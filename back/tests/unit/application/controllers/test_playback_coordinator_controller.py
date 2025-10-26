"""
Comprehensive tests for PlaybackCoordinator controller.

Tests cover:
- Initialization with dependencies
- Playback controls (play, pause, resume, stop, toggle)
- Playlist operations (load, start, navigation)
- Volume and seek controls
- Playback modes (repeat, shuffle, auto-advance)
- State queries and reporting
- NFC integration
- Auto-advance logic
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.src.application.controllers.playback_coordinator_controller import PlaybackCoordinator


class TestPlaybackCoordinatorInitialization:
    """Test PlaybackCoordinator initialization."""

    def test_create_with_required_dependencies(self):
        """Test creating coordinator with required dependencies."""
        audio_backend = Mock()
        playlist_service = Mock()

        coordinator = PlaybackCoordinator(audio_backend, playlist_service)

        assert coordinator._audio_player is not None
        assert coordinator._playlist_controller is not None
        assert coordinator._track_resolver is not None
        assert coordinator._auto_advance_enabled is True

    def test_create_with_optional_socketio(self):
        """Test creating with Socket.IO support."""
        audio_backend = Mock()
        playlist_service = Mock()
        socketio = Mock()

        coordinator = PlaybackCoordinator(audio_backend, playlist_service, socketio=socketio)

        assert coordinator._socketio == socketio

    def test_create_without_playlist_service_raises_error(self):
        """Test creating without playlist service raises ValueError."""
        audio_backend = Mock()

        with pytest.raises(ValueError, match="playlist_service"):
            PlaybackCoordinator(audio_backend, playlist_service=None)


class TestBasicPlaybackControls:
    """Test basic playback control methods."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator for testing."""
        audio_backend = Mock()
        audio_backend.play_file = Mock(return_value=True)
        playlist_service = Mock()

        coord = PlaybackCoordinator(audio_backend, playlist_service)
        coord._audio_player.pause = Mock(return_value=True)
        coord._audio_player.resume = Mock(return_value=True)
        coord._audio_player.stop = Mock(return_value=True)
        return coord

    def test_pause(self, coordinator):
        """Test pause delegates to audio player."""
        success = coordinator.pause()

        assert success is True
        coordinator._audio_player.pause.assert_called_once()

    def test_resume(self, coordinator):
        """Test resume delegates to audio player."""
        success = coordinator.resume()

        assert success is True
        coordinator._audio_player.resume.assert_called_once()

    def test_stop(self, coordinator):
        """Test stop delegates to audio player."""
        success = coordinator.stop()

        assert success is True
        coordinator._audio_player.stop.assert_called_once()

    def test_toggle_pause_when_playing(self, coordinator):
        """Test toggle pause when playing."""
        coordinator._audio_player.is_playing = Mock(return_value=True)
        coordinator._audio_player.is_paused = Mock(return_value=False)
        coordinator._audio_player.toggle_pause = Mock(return_value=True)

        success = coordinator.toggle_pause()

        assert success is True
        coordinator._audio_player.toggle_pause.assert_called_once()

    def test_toggle_pause_when_stopped_starts_playback(self, coordinator):
        """Test toggle when stopped starts playback."""
        coordinator._audio_player.is_playing = Mock(return_value=False)
        coordinator._audio_player.is_paused = Mock(return_value=False)

        # Mock playlist with track
        mock_track = Mock()
        mock_track.file_path = "/music/song.mp3"
        mock_track.duration_ms = 180000
        coordinator._playlist_controller.get_current_track = Mock(return_value=mock_track)
        coordinator._audio_player.play_file = Mock(return_value=True)

        success = coordinator.toggle_pause()

        assert success is True


class TestPlaybackWithTracks:
    """Test playback with tracks."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator with mock track."""
        audio_backend = Mock()
        audio_backend.play_file = Mock(return_value=True)
        playlist_service = Mock()

        coord = PlaybackCoordinator(audio_backend, playlist_service)
        coord._audio_player.is_paused = Mock(return_value=False)
        return coord

    def test_play_current_track(self, coordinator):
        """Test playing current track."""
        mock_track = Mock()
        mock_track.file_path = "/music/song.mp3"
        mock_track.duration_ms = 180000
        mock_track.title = "Test Song"

        coordinator._playlist_controller.get_current_track = Mock(return_value=mock_track)
        # Mock the play_file method
        coordinator._audio_player.play_file = Mock(return_value=True)

        success = coordinator.play()

        assert success is True
        coordinator._audio_player.play_file.assert_called_with("/music/song.mp3", 180000)

    def test_play_specific_track_by_id(self, coordinator):
        """Test playing specific track by ID."""
        # Mock playlist state with tracks
        coordinator._playlist_controller.get_state = Mock(return_value={
            "playlist": {
                "id": "pl-1",
                "name": "Test Playlist",
                "tracks": [
                    {
                        "id": "track-1",
                        "title": "Song 1",
                        "filename": "song1.mp3",
                        "duration_ms": 180000,
                        "file_path": "/music/song1.mp3"
                    }
                ]
            }
        })

        success = coordinator.play("track-1")

        assert success is True

    def test_play_no_track_no_playlist(self, coordinator):
        """Test play fails when no track or playlist."""
        coordinator._playlist_controller.get_current_track = Mock(return_value=None)
        coordinator._playlist_controller.has_playlist = Mock(return_value=False)

        success = coordinator.play()

        assert success is False

    def test_play_track_without_file_path(self, coordinator):
        """Test play fails when track has no file path."""
        mock_track = Mock()
        mock_track.file_path = None

        coordinator._playlist_controller.get_current_track = Mock(return_value=mock_track)

        success = coordinator.play()

        assert success is False

    def test_play_resumes_if_paused(self, coordinator):
        """Test play resumes if audio is paused."""
        coordinator._audio_player.is_paused = Mock(return_value=True)
        coordinator._audio_player.resume = Mock(return_value=True)

        success = coordinator.play()

        assert success is True
        coordinator._audio_player.resume.assert_called_once()


class TestPlaylistOperations:
    """Test playlist loading and management."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator for testing."""
        audio_backend = Mock()
        playlist_service = Mock()
        return PlaybackCoordinator(audio_backend, playlist_service)

    @pytest.mark.asyncio
    async def test_load_playlist(self, coordinator):
        """Test loading playlist."""
        coordinator._playlist_controller.load_playlist = AsyncMock(return_value=True)

        success = await coordinator.load_playlist("pl-123")

        assert success is True
        coordinator._playlist_controller.load_playlist.assert_called_with("pl-123")

    def test_start_playlist_from_track_one(self, coordinator):
        """Test starting playlist from track 1."""
        mock_track = Mock()
        mock_track.file_path = "/music/song1.mp3"
        mock_track.duration_ms = 180000

        coordinator._playlist_controller.has_tracks = Mock(return_value=True)
        coordinator._playlist_controller.goto_track = Mock(return_value=mock_track)
        coordinator._playlist_controller.get_current_track = Mock(return_value=mock_track)
        coordinator._audio_player.play_file = Mock(return_value=True)

        success = coordinator.start_playlist()

        assert success is True
        coordinator._playlist_controller.goto_track.assert_called_with(1)

    def test_start_playlist_from_specific_track(self, coordinator):
        """Test starting playlist from specific track."""
        mock_track = Mock()
        mock_track.file_path = "/music/song3.mp3"
        mock_track.duration_ms = 180000

        coordinator._playlist_controller.has_tracks = Mock(return_value=True)
        coordinator._playlist_controller.goto_track = Mock(return_value=mock_track)
        coordinator._playlist_controller.get_current_track = Mock(return_value=mock_track)
        coordinator._audio_player.play_file = Mock(return_value=True)

        success = coordinator.start_playlist(track_number=3)

        assert success is True
        coordinator._playlist_controller.goto_track.assert_called_with(3)

    def test_start_empty_playlist_fails(self, coordinator):
        """Test starting empty playlist fails."""
        coordinator._playlist_controller.has_tracks = Mock(return_value=False)

        success = coordinator.start_playlist()

        assert success is False


class TestTrackNavigation:
    """Test track navigation methods."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator for testing."""
        audio_backend = Mock()
        playlist_service = Mock()

        coord = PlaybackCoordinator(audio_backend, playlist_service)
        coord._audio_player.play_file = Mock(return_value=True)
        return coord

    def test_next_track(self, coordinator):
        """Test moving to next track."""
        next_track = Mock()
        next_track.file_path = "/music/next.mp3"
        next_track.duration_ms = 180000

        coordinator._playlist_controller.next_track = Mock(return_value=next_track)
        coordinator._playlist_controller.get_current_track = Mock(return_value=next_track)

        success = coordinator.next_track()

        assert success is True
        coordinator._audio_player.play_file.assert_called_once()

    def test_next_track_at_end_stops(self, coordinator):
        """Test next track at end stops playback."""
        coordinator._playlist_controller.next_track = Mock(return_value=None)
        coordinator._audio_player.stop = Mock(return_value=True)

        success = coordinator.next_track()

        assert success is False
        coordinator._audio_player.stop.assert_called_once()

    def test_previous_track(self, coordinator):
        """Test moving to previous track."""
        prev_track = Mock()
        prev_track.file_path = "/music/prev.mp3"
        prev_track.duration_ms = 180000

        coordinator._playlist_controller.previous_track = Mock(return_value=prev_track)
        coordinator._playlist_controller.get_current_track = Mock(return_value=prev_track)

        success = coordinator.previous_track()

        assert success is True
        coordinator._audio_player.play_file.assert_called_once()

    def test_previous_track_at_beginning(self, coordinator):
        """Test previous track at beginning."""
        coordinator._playlist_controller.previous_track = Mock(return_value=None)

        success = coordinator.previous_track()

        assert success is False

    def test_goto_track(self, coordinator):
        """Test going to specific track."""
        track = Mock()
        track.file_path = "/music/track5.mp3"
        track.duration_ms = 180000

        coordinator._playlist_controller.goto_track = Mock(return_value=track)
        coordinator._playlist_controller.get_current_track = Mock(return_value=track)

        success = coordinator.goto_track(5)

        assert success is True
        coordinator._playlist_controller.goto_track.assert_called_with(5)


class TestVolumeAndSeek:
    """Test volume and seek controls."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator for testing."""
        audio_backend = Mock()
        playlist_service = Mock()
        return PlaybackCoordinator(audio_backend, playlist_service)

    def test_set_volume(self, coordinator):
        """Test setting volume."""
        coordinator._audio_player.set_volume = Mock(return_value=True)

        success = coordinator.set_volume(75)

        assert success is True
        coordinator._audio_player.set_volume.assert_called_with(75)

    def test_get_volume(self, coordinator):
        """Test getting volume."""
        coordinator._audio_player.get_volume = Mock(return_value=80)

        volume = coordinator.get_volume()

        assert volume == 80

    def test_seek(self, coordinator):
        """Test seeking to position."""
        coordinator._audio_player.seek = Mock(return_value=True)

        success = coordinator.seek(45.5)

        assert success is True
        coordinator._audio_player.seek.assert_called_with(45.5)

    def test_seek_to_position_ms(self, coordinator):
        """Test seeking with milliseconds."""
        coordinator._audio_player.seek = Mock(return_value=True)

        success = coordinator.seek_to_position(30000)

        assert success is True
        coordinator._audio_player.seek.assert_called_with(30.0)


class TestPlaybackModes:
    """Test playback mode settings."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator for testing."""
        audio_backend = Mock()
        playlist_service = Mock()
        return PlaybackCoordinator(audio_backend, playlist_service)

    def test_set_repeat_mode(self, coordinator):
        """Test setting repeat mode."""
        coordinator._playlist_controller.set_repeat_mode = Mock(return_value=True)

        success = coordinator.set_repeat_mode("all")

        assert success is True
        coordinator._playlist_controller.set_repeat_mode.assert_called_with("all")

    def test_set_shuffle(self, coordinator):
        """Test setting shuffle mode."""
        coordinator._playlist_controller.set_shuffle = Mock(return_value=True)

        success = coordinator.set_shuffle(True)

        assert success is True
        coordinator._playlist_controller.set_shuffle.assert_called_with(True)

    def test_set_auto_advance(self, coordinator):
        """Test setting auto-advance."""
        coordinator.set_auto_advance(False)

        assert coordinator._auto_advance_enabled is False


class TestStateQueries:
    """Test state query methods."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator for testing."""
        audio_backend = Mock()
        playlist_service = Mock()

        coord = PlaybackCoordinator(audio_backend, playlist_service)

        # Mock audio state
        coord._audio_player.get_state = Mock(return_value={
            "is_playing": True,
            "is_paused": False,
            "position": 30.5,
            "duration": 180.0,
            "volume": 75
        })

        # Mock playlist info
        coord._playlist_controller.get_playlist_info = Mock(return_value={
            "playlist_id": "pl-123",
            "playlist_name": "Test Playlist",
            "current_track": {"id": "track-1", "title": "Song 1"},
            "current_track_number": 1,
            "total_tracks": 10,
            "can_next": True,
            "can_previous": False,
            "repeat_mode": "all",
            "shuffle_enabled": False
        })

        return coord

    def test_get_playback_status(self, coordinator):
        """Test getting complete playback status."""
        status = coordinator.get_playback_status()

        assert status["is_playing"] is True
        assert status["is_paused"] is False
        assert status["position_ms"] == 30500
        assert status["duration_ms"] == 180000
        assert status["volume"] == 75
        # Frontend-expected field names
        assert status["active_playlist_id"] == "pl-123"
        assert status["active_playlist_title"] == "Test Playlist"
        assert status["track_index"] == 1
        assert status["track_count"] == 10
        assert status["auto_advance_enabled"] is True

    def test_get_current_track(self, coordinator):
        """Test getting current track."""
        mock_track = Mock()
        mock_track.to_dict = Mock(return_value={"id": "track-1", "title": "Song 1"})

        coordinator._playlist_controller.get_current_track = Mock(return_value=mock_track)

        track = coordinator.get_current_track()

        assert track == {"id": "track-1", "title": "Song 1"}


class TestAutoAdvance:
    """Test auto-advance functionality."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator for testing."""
        audio_backend = Mock()
        playlist_service = Mock()
        return PlaybackCoordinator(audio_backend, playlist_service)

    def test_auto_advance_when_track_finishes(self, coordinator):
        """Test auto-advance to next track when current finishes."""
        coordinator._audio_player.is_playing = Mock(return_value=True)
        coordinator._audio_player.has_finished = Mock(return_value=True)

        next_track = Mock()
        next_track.file_path = "/music/next.mp3"
        next_track.duration_ms = 180000

        coordinator._playlist_controller.next_track = Mock(return_value=next_track)
        coordinator._playlist_controller.get_current_track = Mock(return_value=next_track)
        coordinator._audio_player.play_file = Mock(return_value=True)

        coordinator.update_auto_advance()

        coordinator._audio_player.play_file.assert_called_once()

    def test_no_auto_advance_when_disabled(self, coordinator):
        """Test no auto-advance when disabled."""
        coordinator._auto_advance_enabled = False
        coordinator._audio_player.is_playing = Mock(return_value=True)
        coordinator._audio_player.has_finished = Mock(return_value=True)

        coordinator.update_auto_advance()

        # Should not attempt to play next track

    def test_auto_advance_stops_at_end_of_playlist(self, coordinator):
        """Test auto-advance stops at end of playlist."""
        coordinator._audio_player.is_playing = Mock(return_value=True)
        coordinator._audio_player.has_finished = Mock(return_value=True)
        coordinator._playlist_controller.next_track = Mock(return_value=None)
        coordinator._audio_player.stop = Mock(return_value=True)

        coordinator.update_auto_advance()

        # Stop is called twice: once in next_track() and once in _handle_auto_advance()
        assert coordinator._audio_player.stop.call_count == 2


class TestNFCIntegration:
    """Test NFC tag handling."""

    @pytest.fixture
    def coordinator(self):
        """Create coordinator with data service."""
        audio_backend = Mock()
        playlist_service = Mock()
        data_service = AsyncMock()
        socketio = Mock()

        coord = PlaybackCoordinator(
            audio_backend,
            playlist_service,
            data_application_service=data_service,
            socketio=socketio
        )
        return coord

    @pytest.mark.asyncio
    async def test_handle_tag_scanned_loads_playlist(self, coordinator):
        """Test NFC tag loads associated playlist."""
        coordinator._data_application_service.get_playlist_by_nfc_use_case = AsyncMock(
            return_value={"id": "pl-123", "title": "NFC Playlist"}
        )
        coordinator.load_playlist = AsyncMock(return_value=True)
        coordinator.start_playlist = Mock(return_value=True)

        await coordinator.handle_tag_scanned("nfc-123")

        coordinator._data_application_service.get_playlist_by_nfc_use_case.assert_called_with("nfc-123")
        coordinator.load_playlist.assert_called_with("pl-123")
        coordinator.start_playlist.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_handle_tag_scanned_no_playlist_found(self, coordinator):
        """Test NFC tag with no associated playlist."""
        coordinator._data_application_service.get_playlist_by_nfc_use_case = AsyncMock(return_value=None)

        # Should not raise exception
        await coordinator.handle_tag_scanned("nfc-unknown")

    @pytest.mark.asyncio
    async def test_handle_tag_without_data_service(self, coordinator):
        """Test NFC handling without data service."""
        coordinator._data_application_service = None

        # Should not raise exception
        await coordinator.handle_tag_scanned("nfc-123")


class TestCleanup:
    """Test cleanup operations."""

    def test_cleanup_stops_playback(self):
        """Test cleanup stops playback."""
        audio_backend = Mock()
        playlist_service = Mock()

        coordinator = PlaybackCoordinator(audio_backend, playlist_service)
        coordinator._audio_player.stop = Mock(return_value=True)

        coordinator.cleanup()

        coordinator._audio_player.stop.assert_called_once()
