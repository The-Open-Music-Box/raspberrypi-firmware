"""
Comprehensive tests for PlaybackController (pure audio controller).

Tests cover:
- Initialization with audio backend
- Async playback controls (play, pause, resume, stop)
- Volume control
- Seek functionality
- Position tracking and updates
- Playback state management
- Playlist context handling
"""

import pytest
from unittest.mock import Mock, AsyncMock
from app.src.application.controllers.playback_controller import PlaybackController, PlaybackState


class TestPlaybackControllerInitialization:
    """Test PlaybackController initialization."""

    def test_create_with_backend(self):
        """Test creating controller with audio backend."""
        backend = Mock()
        controller = PlaybackController(backend)

        assert controller._backend == backend
        assert controller._state is not None
        assert controller._state.is_playing is False
        assert controller._state.volume == 50

    def test_initial_playback_state(self):
        """Test initial playback state values."""
        backend = Mock()
        controller = PlaybackController(backend)

        assert controller._state.is_playing is False
        assert controller._state.current_track_id is None
        assert controller._state.position_ms == 0
        assert controller._state.playlist_id is None


class TestAsyncPlaybackControls:
    """Test async playback control methods."""

    @pytest.fixture
    def backend(self):
        """Create mock async backend."""
        backend = AsyncMock()
        backend.play = AsyncMock(return_value=True)
        backend.pause = AsyncMock(return_value=True)
        backend.resume = AsyncMock(return_value=True)
        backend.stop = AsyncMock(return_value=True)
        return backend

    @pytest.fixture
    def controller(self, backend):
        """Create controller with async backend."""
        return PlaybackController(backend)

    @pytest.mark.asyncio
    async def test_play_track_success(self, controller, backend):
        """Test playing track successfully."""
        success = await controller.play_track("/music/song.mp3", "track-123")

        assert success is True
        assert controller._state.is_playing is True
        assert controller._state.current_track_id == "track-123"
        backend.play.assert_called_with("/music/song.mp3")

    @pytest.mark.asyncio
    async def test_play_track_failure(self, controller, backend):
        """Test play track handles backend failure."""
        backend.play = AsyncMock(return_value=False)

        success = await controller.play_track("/music/song.mp3", "track-123")

        assert success is False

    @pytest.mark.asyncio
    async def test_play_track_exception(self, controller, backend):
        """Test play track handles exceptions."""
        backend.play = AsyncMock(side_effect=Exception("Backend error"))

        success = await controller.play_track("/music/song.mp3", "track-123")

        assert success is False

    @pytest.mark.asyncio
    async def test_pause(self, controller, backend):
        """Test pausing playback."""
        await controller.play_track("/music/song.mp3", "track-123")

        success = await controller.pause()

        assert success is True
        assert controller._state.is_playing is False
        backend.pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_pause_exception(self, controller, backend):
        """Test pause handles exceptions."""
        backend.pause = AsyncMock(side_effect=Exception("Pause error"))

        success = await controller.pause()

        assert success is False

    @pytest.mark.asyncio
    async def test_resume(self, controller, backend):
        """Test resuming playback."""
        await controller.play_track("/music/song.mp3", "track-123")
        await controller.pause()

        success = await controller.resume()

        assert success is True
        assert controller._state.is_playing is True
        backend.resume.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_exception(self, controller, backend):
        """Test resume handles exceptions."""
        backend.resume = AsyncMock(side_effect=Exception("Resume error"))

        success = await controller.resume()

        assert success is False

    @pytest.mark.asyncio
    async def test_stop(self, controller, backend):
        """Test stopping playback."""
        await controller.play_track("/music/song.mp3", "track-123")

        success = await controller.stop()

        assert success is True
        assert controller._state.is_playing is False
        assert controller._state.current_track_id is None
        assert controller._state.position_ms == 0
        backend.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_exception(self, controller, backend):
        """Test stop handles exceptions."""
        backend.stop = AsyncMock(side_effect=Exception("Stop error"))

        success = await controller.stop()

        assert success is False
        # State should still be updated even on error
        assert controller._state.is_playing is False


class TestVolumeControl:
    """Test volume control operations."""

    @pytest.fixture
    def backend(self):
        """Create mock backend with volume support."""
        backend = AsyncMock()
        backend.set_volume = AsyncMock(return_value=True)
        return backend

    @pytest.fixture
    def controller(self, backend):
        """Create controller for testing."""
        return PlaybackController(backend)

    @pytest.mark.asyncio
    async def test_set_volume(self, controller, backend):
        """Test setting volume."""
        success = await controller.set_volume(75)

        assert success is True
        assert controller._state.volume == 75
        backend.set_volume.assert_called_with(75)

    @pytest.mark.asyncio
    async def test_set_volume_clamps_to_minimum(self, controller, backend):
        """Test volume is clamped to 0."""
        success = await controller.set_volume(-10)

        assert success is True
        backend.set_volume.assert_called_with(0)

    @pytest.mark.asyncio
    async def test_set_volume_clamps_to_maximum(self, controller, backend):
        """Test volume is clamped to 100."""
        success = await controller.set_volume(150)

        assert success is True
        backend.set_volume.assert_called_with(100)

    @pytest.mark.asyncio
    async def test_set_volume_exception(self, controller, backend):
        """Test set volume handles exceptions."""
        backend.set_volume = AsyncMock(side_effect=Exception("Volume error"))

        success = await controller.set_volume(50)

        assert success is False


class TestSeekFunctionality:
    """Test seek operations."""

    @pytest.fixture
    def backend(self):
        """Create mock backend with seek support."""
        backend = AsyncMock()
        backend.seek = AsyncMock(return_value=True)
        return backend

    @pytest.fixture
    def controller(self, backend):
        """Create controller for testing."""
        return PlaybackController(backend)

    @pytest.mark.asyncio
    async def test_seek(self, controller, backend):
        """Test seeking to position."""
        success = await controller.seek(30000)

        assert success is True
        assert controller._state.position_ms == 30000
        backend.seek.assert_called_with(30000)

    @pytest.mark.asyncio
    async def test_seek_to_beginning(self, controller, backend):
        """Test seeking to beginning."""
        success = await controller.seek(0)

        assert success is True
        assert controller._state.position_ms == 0

    @pytest.mark.asyncio
    async def test_seek_exception(self, controller, backend):
        """Test seek handles exceptions."""
        backend.seek = AsyncMock(side_effect=Exception("Seek error"))

        success = await controller.seek(30000)

        assert success is False


class TestPlaybackState:
    """Test playback state management."""

    @pytest.fixture
    def controller(self):
        """Create controller for testing."""
        backend = AsyncMock()
        backend.play = AsyncMock(return_value=True)
        backend.pause = AsyncMock(return_value=True)
        return PlaybackController(backend)

    @pytest.mark.asyncio
    async def test_get_playback_state_stopped(self, controller):
        """Test getting state when stopped."""
        state = controller.get_playback_state()

        assert state["is_playing"] is False
        assert state["current_track_id"] is None
        assert state["position_ms"] == 0
        assert state["volume"] == 50
        assert state["playlist_id"] is None

    @pytest.mark.asyncio
    async def test_get_playback_state_playing(self, controller):
        """Test getting state when playing."""
        await controller.play_track("/music/song.mp3", "track-123")

        state = controller.get_playback_state()

        assert state["is_playing"] is True
        assert state["current_track_id"] == "track-123"

    @pytest.mark.asyncio
    async def test_get_playback_state_paused(self, controller):
        """Test getting state when paused."""
        await controller.play_track("/music/song.mp3", "track-123")
        await controller.pause()

        state = controller.get_playback_state()

        assert state["is_playing"] is False
        assert state["current_track_id"] == "track-123"  # Track ID retained


class TestPositionTracking:
    """Test position tracking and updates."""

    @pytest.fixture
    def backend(self):
        """Create mock backend with position support."""
        backend = AsyncMock()
        backend.play = AsyncMock(return_value=True)
        backend.get_position = AsyncMock(return_value=45000)
        return backend

    @pytest.fixture
    def controller(self, backend):
        """Create controller for testing."""
        return PlaybackController(backend)

    @pytest.mark.asyncio
    async def test_update_position_when_playing(self, controller, backend):
        """Test updating position when playing."""
        await controller.play_track("/music/song.mp3", "track-123")

        position = await controller.update_position()

        assert position == 45000
        assert controller._state.position_ms == 45000
        backend.get_position.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_position_when_stopped(self, controller):
        """Test updating position when stopped returns None."""
        position = await controller.update_position()

        assert position is None

    @pytest.mark.asyncio
    async def test_update_position_exception(self, controller, backend):
        """Test update position handles exceptions."""
        await controller.play_track("/music/song.mp3", "track-123")
        backend.get_position = AsyncMock(side_effect=Exception("Position error"))

        position = await controller.update_position()

        assert position is None


class TestPlaylistContext:
    """Test playlist context management."""

    @pytest.fixture
    def controller(self):
        """Create controller for testing."""
        return PlaybackController(AsyncMock())

    def test_set_playlist_context(self, controller):
        """Test setting playlist context."""
        controller.set_playlist_context("pl-123")

        assert controller._state.playlist_id == "pl-123"

    def test_clear_playlist_context(self, controller):
        """Test clearing playlist context."""
        controller.set_playlist_context("pl-123")
        controller.clear_playlist_context()

        assert controller._state.playlist_id is None


class TestPlaybackStateDataclass:
    """Test PlaybackState dataclass."""

    def test_create_default_state(self):
        """Test creating default playback state."""
        state = PlaybackState()

        assert state.is_playing is False
        assert state.current_track_id is None
        assert state.position_ms == 0
        assert state.volume == 50
        assert state.playlist_id is None

    def test_create_state_with_values(self):
        """Test creating state with custom values."""
        state = PlaybackState(
            is_playing=True,
            current_track_id="track-1",
            position_ms=30000,
            volume=75,
            playlist_id="pl-1"
        )

        assert state.is_playing is True
        assert state.current_track_id == "track-1"
        assert state.position_ms == 30000
        assert state.volume == 75
        assert state.playlist_id == "pl-1"


class TestErrorHandling:
    """Test error handling with decorators."""

    @pytest.fixture
    def controller(self):
        """Create controller for testing."""
        backend = AsyncMock()
        return PlaybackController(backend)

    @pytest.mark.asyncio
    async def test_play_with_backend_exception(self, controller):
        """Test play handles backend exceptions gracefully."""
        controller._backend.play = AsyncMock(side_effect=RuntimeError("Fatal error"))

        success = await controller.play_track("/music/song.mp3", "track-123")

        # Error should be handled, not propagated
        assert success is False

    @pytest.mark.asyncio
    async def test_volume_with_backend_exception(self, controller):
        """Test volume handles backend exceptions gracefully."""
        controller._backend.set_volume = AsyncMock(side_effect=RuntimeError("Volume failure"))

        success = await controller.set_volume(80)

        # Error should be handled, not propagated
        assert success is False


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""

    @pytest.fixture
    def backend(self):
        """Create full-featured mock backend."""
        backend = AsyncMock()
        backend.play = AsyncMock(return_value=True)
        backend.pause = AsyncMock(return_value=True)
        backend.resume = AsyncMock(return_value=True)
        backend.stop = AsyncMock(return_value=True)
        backend.set_volume = AsyncMock(return_value=True)
        backend.seek = AsyncMock(return_value=True)
        backend.get_position = AsyncMock(return_value=15000)
        return backend

    @pytest.fixture
    def controller(self, backend):
        """Create controller for integration tests."""
        return PlaybackController(backend)

    @pytest.mark.asyncio
    async def test_typical_playback_flow(self, controller):
        """Test typical playback session."""
        # Set playlist context
        controller.set_playlist_context("pl-123")

        # Play track
        await controller.play_track("/music/song1.mp3", "track-1")
        assert controller._state.is_playing is True

        # Adjust volume
        await controller.set_volume(80)
        assert controller._state.volume == 80

        # Seek to position
        await controller.seek(30000)
        assert controller._state.position_ms == 30000

        # Pause
        await controller.pause()
        assert controller._state.is_playing is False

        # Resume
        await controller.resume()
        assert controller._state.is_playing is True

        # Stop
        await controller.stop()
        assert controller._state.is_playing is False
        assert controller._state.current_track_id is None

    @pytest.mark.asyncio
    async def test_track_switching(self, controller):
        """Test switching between tracks."""
        # Play first track
        await controller.play_track("/music/song1.mp3", "track-1")
        assert controller._state.current_track_id == "track-1"

        # Play second track (should update state)
        await controller.play_track("/music/song2.mp3", "track-2")
        assert controller._state.current_track_id == "track-2"
