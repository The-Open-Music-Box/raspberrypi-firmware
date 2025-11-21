"""
Comprehensive tests for PlaylistController.

Tests cover:
- Initialization with dependencies
- Playlist loading (async)
- Data conversion to domain objects
- Track path resolution
- Track validation
- Playlist operations (navigation, state)
- Playback modes
- State queries
"""

import pytest
from unittest.mock import Mock, AsyncMock
from app.src.application.controllers.playlist_controller import PlaylistController
from app.src.application.controllers.playlist_state_manager_controller import Playlist, Track


class TestPlaylistControllerInitialization:
    """Test PlaylistController initialization."""

    def test_create_with_required_dependencies(self):
        """Test creating controller with track resolver and service."""
        track_resolver = Mock()
        playlist_service = Mock()

        controller = PlaylistController(track_resolver, playlist_service)

        assert controller._track_resolver == track_resolver
        assert controller._playlist_service == playlist_service
        assert controller._state_manager is not None

    def test_create_without_service_uses_di(self):
        """Test creating without service uses dependency injection."""
        track_resolver = Mock()

        # DI is now available in test context and should work
        controller = PlaylistController(track_resolver, None)
        assert controller._playlist_service is not None

    def test_state_manager_property(self):
        """Test accessing state manager property."""
        track_resolver = Mock()
        playlist_service = Mock()

        controller = PlaylistController(track_resolver, playlist_service)

        assert controller.state_manager is not None


class TestPlaylistLoading:
    """Test playlist loading operations."""

    @pytest.fixture
    def track_resolver(self):
        """Create mock track resolver."""
        resolver = Mock()
        resolver.resolve_path = Mock(return_value="/music/song.mp3")
        resolver.validate_path = Mock(return_value=True)
        return resolver

    @pytest.fixture
    def playlist_service(self):
        """Create mock playlist service."""
        service = AsyncMock()
        service.get_playlist = AsyncMock(return_value={
            "id": "pl-123",
            "name": "Test Playlist",
            "tracks": [
                {
                    "id": "track-1",
                    "title": "Song 1",
                    "filename": "song1.mp3",
                    "duration_ms": 180000
                },
                {
                    "id": "track-2",
                    "title": "Song 2",
                    "filename": "song2.mp3",
                    "duration_ms": 200000
                }
            ]
        })
        return service

    @pytest.fixture
    def controller(self, track_resolver, playlist_service):
        """Create controller for testing."""
        return PlaylistController(track_resolver, playlist_service)

    @pytest.mark.asyncio
    async def test_load_playlist_success(self, controller, playlist_service):
        """Test successfully loading playlist."""
        success = await controller.load_playlist("pl-123")

        assert success is True
        playlist_service.get_playlist.assert_called_with("pl-123")

    @pytest.mark.asyncio
    async def test_load_playlist_not_found(self, controller, playlist_service):
        """Test loading non-existent playlist."""
        playlist_service.get_playlist = AsyncMock(return_value=None)

        success = await controller.load_playlist("pl-999")

        assert success is False

    @pytest.mark.asyncio
    async def test_load_playlist_resolves_track_paths(self, controller, track_resolver):
        """Test track paths are resolved during load."""
        await controller.load_playlist("pl-123")

        # Should resolve paths for all tracks
        assert track_resolver.resolve_path.call_count == 2

    @pytest.mark.asyncio
    async def test_load_playlist_validates_tracks(self, controller, track_resolver):
        """Test tracks are validated during load."""
        await controller.load_playlist("pl-123")

        # Should validate all resolved paths
        assert track_resolver.validate_path.call_count == 2

    @pytest.mark.asyncio
    async def test_load_playlist_filters_invalid_tracks(self, controller, track_resolver):
        """Test invalid tracks are filtered out."""
        # Make second track invalid
        track_resolver.validate_path = Mock(side_effect=[True, False])

        await controller.load_playlist("pl-123")

        # Should have only 1 valid track
        state = controller.get_state()
        assert len(state["playlist"]["tracks"]) == 1

    @pytest.mark.asyncio
    async def test_load_playlist_fails_if_no_valid_tracks(self, controller, track_resolver):
        """Test load fails if no valid tracks."""
        track_resolver.validate_path = Mock(return_value=False)

        success = await controller.load_playlist("pl-123")

        assert success is False


class TestDataConversion:
    """Test data conversion to domain objects."""

    @pytest.fixture
    def controller(self):
        """Create controller for testing."""
        return PlaylistController(Mock(), Mock())

    def test_convert_playlist_data(self, controller):
        """Test converting playlist data to domain object."""
        playlist_data = {
            "id": "pl-123",
            "name": "Test Playlist",
            "tracks": [
                {
                    "id": "track-1",
                    "title": "Song 1",
                    "filename": "song1.mp3",
                    "duration_ms": 180000
                }
            ]
        }

        playlist = controller._convert_to_domain_playlist(playlist_data)

        assert playlist is not None
        assert playlist.id == "pl-123"
        assert playlist.title == "Test Playlist"
        assert len(playlist.tracks) == 1

    def test_convert_playlist_without_id_fails(self, controller):
        """Test conversion fails without playlist ID."""
        playlist_data = {"name": "Test", "tracks": []}

        playlist = controller._convert_to_domain_playlist(playlist_data)

        assert playlist is None

    def test_convert_playlist_with_default_name(self, controller):
        """Test conversion uses default name if missing."""
        playlist_data = {"id": "pl-123", "tracks": []}

        playlist = controller._convert_to_domain_playlist(playlist_data)

        assert playlist.title == "Playlist pl-123"

    def test_convert_track_data(self, controller):
        """Test converting track data to domain object."""
        track_data = {
            "id": "track-1",
            "title": "Song 1",
            "filename": "song1.mp3",
            "duration_ms": 180000
        }

        track = controller._convert_to_domain_track(track_data)

        assert track is not None
        assert track.id == "track-1"
        assert track.title == "Song 1"
        assert track.filename == "song1.mp3"
        assert track.duration_ms == 180000

    def test_convert_track_without_id_fails(self, controller):
        """Test track conversion fails without ID."""
        track_data = {"title": "Song", "filename": "song.mp3"}

        track = controller._convert_to_domain_track(track_data)

        assert track is None

    def test_convert_track_uses_filename_as_title(self, controller):
        """Test track uses filename as title if missing."""
        track_data = {
            "id": "track-1",
            "filename": "awesome_song.mp3",
            "duration_ms": 180000
        }

        track = controller._convert_to_domain_track(track_data)

        assert track.title == "awesome_song.mp3"


class TestTrackNavigation:
    """Test track navigation methods."""

    @pytest.fixture
    def controller(self):
        """Create controller with loaded playlist."""
        ctrl = PlaylistController(Mock(), Mock())

        # Load test playlist
        playlist = Playlist(
            id="pl-1",
            title="Test",
            tracks=[
                Track(id="t1", title="Song 1", filename="s1.mp3", duration_ms=180000),
                Track(id="t2", title="Song 2", filename="s2.mp3", duration_ms=200000),
                Track(id="t3", title="Song 3", filename="s3.mp3", duration_ms=220000),
            ]
        )
        ctrl._state_manager.set_playlist(playlist)
        return ctrl

    def test_get_current_track(self, controller):
        """Test getting current track."""
        track = controller.get_current_track()

        assert track is not None
        assert track.title == "Song 1"

    def test_next_track(self, controller):
        """Test moving to next track."""
        track = controller.next_track()

        assert track is not None
        assert track.title == "Song 2"

    def test_previous_track(self, controller):
        """Test moving to previous track."""
        controller.next_track()  # Move to track 2
        track = controller.previous_track()

        assert track is not None
        assert track.title == "Song 1"

    def test_goto_track_by_number(self, controller):
        """Test going to specific track by number."""
        track = controller.goto_track(3)

        assert track is not None
        assert track.title == "Song 3"

    def test_goto_invalid_track_number(self, controller):
        """Test going to invalid track number."""
        track = controller.goto_track(10)

        assert track is None

    def test_clear_playlist(self, controller):
        """Test clearing playlist."""
        controller.clear_playlist()

        state = controller.get_state()
        assert state["playlist"] is None


class TestPlaybackModes:
    """Test playback mode settings."""

    @pytest.fixture
    def controller(self):
        """Create controller for testing."""
        return PlaylistController(Mock(), Mock())

    def test_set_repeat_mode_none(self, controller):
        """Test setting repeat mode to none."""
        success = controller.set_repeat_mode("none")

        assert success is True

    def test_set_repeat_mode_one(self, controller):
        """Test setting repeat mode to one."""
        success = controller.set_repeat_mode("one")

        assert success is True

    def test_set_repeat_mode_all(self, controller):
        """Test setting repeat mode to all."""
        success = controller.set_repeat_mode("all")

        assert success is True

    def test_set_invalid_repeat_mode(self, controller):
        """Test setting invalid repeat mode fails."""
        success = controller.set_repeat_mode("invalid")

        assert success is False

    def test_set_shuffle_enabled(self, controller):
        """Test enabling shuffle."""
        success = controller.set_shuffle(True)

        assert success is True

    def test_set_shuffle_disabled(self, controller):
        """Test disabling shuffle."""
        success = controller.set_shuffle(False)

        assert success is True


class TestStateQueries:
    """Test state query methods."""

    @pytest.fixture
    def controller(self):
        """Create controller with loaded playlist."""
        ctrl = PlaylistController(Mock(), Mock())

        playlist = Playlist(
            id="pl-1",
            title="Test Playlist",
            tracks=[
                Track(id="t1", title="Song 1", filename="s1.mp3", duration_ms=180000),
                Track(id="t2", title="Song 2", filename="s2.mp3", duration_ms=200000),
            ]
        )
        ctrl._state_manager.set_playlist(playlist)
        return ctrl

    def test_get_state(self, controller):
        """Test getting complete state."""
        state = controller.get_state()

        assert state["playlist"] is not None
        assert state["playlist"]["id"] == "pl-1"
        assert state["total_tracks"] == 2

    def test_get_playlist_info(self, controller):
        """Test getting playlist info for API."""
        info = controller.get_playlist_info()

        assert info["playlist_id"] == "pl-1"
        assert info["playlist_name"] == "Test Playlist"
        assert info["total_tracks"] == 2
        assert "current_track" in info
        assert "can_next" in info
        assert "can_previous" in info

    def test_has_playlist_true(self, controller):
        """Test has_playlist when playlist loaded."""
        assert controller.has_playlist() is True

    def test_has_playlist_false(self):
        """Test has_playlist when no playlist."""
        controller = PlaylistController(Mock(), Mock())

        assert controller.has_playlist() is False

    def test_has_tracks_true(self, controller):
        """Test has_tracks when playlist has tracks."""
        assert controller.has_tracks() is True

    def test_has_tracks_false(self):
        """Test has_tracks when playlist is empty."""
        ctrl = PlaylistController(Mock(), Mock())
        playlist = Playlist(id="pl-1", title="Empty", tracks=[])
        ctrl._state_manager.set_playlist(playlist)

        assert ctrl.has_tracks() is False


class TestDirectPlaylistLoading:
    """Test direct playlist loading for testing."""

    def test_load_playlist_data_directly(self):
        """Test loading playlist object directly."""
        controller = PlaylistController(Mock(), Mock())

        playlist = Playlist(
            id="pl-test",
            title="Direct Load",
            tracks=[Track(id="t1", title="Song", filename="song.mp3", duration_ms=180000)]
        )

        success = controller.load_playlist_data(playlist)

        assert success is True

        state = controller.get_state()
        assert state["playlist"]["id"] == "pl-test"


class TestErrorHandling:
    """Test error handling in playlist controller."""

    @pytest.mark.asyncio
    async def test_load_playlist_service_error(self):
        """Test load handles service errors."""
        track_resolver = Mock()
        playlist_service = AsyncMock()
        playlist_service.get_playlist = AsyncMock(side_effect=Exception("Service error"))

        controller = PlaylistController(track_resolver, playlist_service)

        success = await controller.load_playlist("pl-123")

        assert success is False

    def test_convert_playlist_with_exception(self):
        """Test conversion handles exceptions."""
        controller = PlaylistController(Mock(), Mock())

        # Invalid data that causes exception
        playlist = controller._convert_to_domain_playlist({"id": None})

        # Should return None on error

    def test_load_direct_playlist_with_error(self):
        """Test direct load handles errors."""
        controller = PlaylistController(Mock(), Mock())
        controller._state_manager.set_playlist = Mock(side_effect=Exception("Error"))

        playlist = Playlist(id="pl-1", title="Test", tracks=[])
        success = controller.load_playlist_data(playlist)

        assert success is False
