"""
Comprehensive tests for AudioEngine.

Tests cover:
- Initialization and validation
- Engine lifecycle (start/stop)
- Playback operations (play, pause, resume, stop)
- Playlist operations
- Volume control
- Event publishing
- State management integration
- Error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from app.src.domain.protocols.state_manager_protocol import PlaybackState


@pytest.fixture
def mock_backend():
    """Create a mock audio backend."""
    backend = Mock()
    backend.play = AsyncMock(return_value=True)
    backend.play_file = Mock(return_value=True)
    backend.pause = Mock(return_value=True)
    backend.resume = Mock(return_value=True)
    backend.stop = Mock(return_value=True)
    backend.set_volume = Mock(return_value=True)
    backend.get_volume = Mock(return_value=50)
    backend.seek = AsyncMock(return_value=True)
    backend.is_playing = Mock(return_value=False)
    backend.cleanup = Mock()
    return backend


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus."""
    bus = Mock()
    bus.publish = AsyncMock()
    bus.get_statistics = Mock(return_value={})
    return bus


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    manager = Mock()
    manager.set_state = Mock()
    manager.get_current_state = Mock(return_value=PlaybackState.STOPPED)
    manager.update_playlist_info = Mock()
    manager.update_track_info = Mock()
    manager.update_volume = Mock()
    manager.update_position = Mock()
    manager.get_state_dict = Mock(return_value={"state": "STOPPED"})
    return manager


@pytest.fixture
def audio_engine(mock_backend, mock_event_bus, mock_state_manager):
    """Create an audio engine instance."""
    from app.src.domain.audio.engine.audio_engine import AudioEngine

    engine = AudioEngine(mock_backend, mock_event_bus, mock_state_manager)
    return engine


@pytest.fixture
def mock_playlist():
    """Create a mock playlist."""
    playlist = Mock()
    playlist.id = "pl-123"
    playlist.title = "Test Playlist"
    playlist.title = "Test Playlist"

    track1 = Mock()
    track1.file_path = "/music/song1.mp3"
    track1.title = "Song 1"
    track1.artist = "Artist 1"
    track1.album = "Album 1"
    track1.duration_ms = 180000

    track2 = Mock()
    track2.file_path = "/music/song2.mp3"
    track2.title = "Song 2"

    playlist.tracks = [track1, track2]
    return playlist


class TestAudioEngineInitialization:
    """Test AudioEngine initialization."""

    def test_create_engine(self, audio_engine):
        """Test creating audio engine."""
        assert audio_engine is not None
        assert audio_engine._is_running is False

    def test_validates_state_manager(self, mock_backend, mock_event_bus):
        """Test validates state manager has required methods."""
        from app.src.domain.audio.engine.audio_engine import AudioEngine

        invalid_manager = Mock(spec=[])  # No set_state method

        with pytest.raises(ValueError):
            AudioEngine(mock_backend, mock_event_bus, invalid_manager)

    def test_stores_dependencies(self, audio_engine, mock_backend, mock_event_bus, mock_state_manager):
        """Test stores all dependencies."""
        assert audio_engine._backend == mock_backend
        assert audio_engine._event_bus == mock_event_bus
        assert audio_engine._state_manager == mock_state_manager


class TestEngineLifecycle:
    """Test engine lifecycle management."""

    @pytest.mark.asyncio
    async def test_start_engine(self, audio_engine, mock_state_manager):
        """Test starting engine."""
        await audio_engine.start()

        assert audio_engine.is_running is True
        assert audio_engine._startup_time is not None
        assert mock_state_manager.set_state.called

    @pytest.mark.asyncio
    async def test_start_already_running(self, audio_engine):
        """Test starting engine that's already running."""
        await audio_engine.start()
        first_startup_time = audio_engine._startup_time

        await audio_engine.start()

        # Should not change startup time
        assert audio_engine._startup_time == first_startup_time

    @pytest.mark.asyncio
    async def test_stop_engine(self, audio_engine, mock_backend):
        """Test stopping engine."""
        await audio_engine.start()
        await audio_engine.stop()

        assert audio_engine.is_running is False
        mock_backend.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, audio_engine):
        """Test stopping engine that's not running."""
        await audio_engine.stop()

        # Should not raise error
        assert audio_engine.is_running is False


class TestPlaybackOperations:
    """Test playback operations."""

    @pytest.mark.asyncio
    async def test_play_file(self, audio_engine, mock_backend, mock_event_bus):
        """Test playing a file."""
        await audio_engine.start()

        result = await audio_engine.play_file("/music/test.mp3")

        assert result is True
        mock_backend.play_file.assert_called_once_with("/music/test.mp3")
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_play_file_when_not_running(self, audio_engine):
        """Test playing file when engine not running."""
        result = await audio_engine.play_file("/music/test.mp3")

        assert result is False

    @pytest.mark.asyncio
    async def test_pause_playback(self, audio_engine, mock_backend, mock_event_bus):
        """Test pausing playback."""
        await audio_engine.start()

        result = await audio_engine.pause_playback()

        assert result is True
        mock_backend.pause.assert_called_once()
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_resume_playback(self, audio_engine, mock_backend, mock_event_bus):
        """Test resuming playback."""
        await audio_engine.start()

        result = await audio_engine.resume_playback()

        assert result is True
        mock_backend.resume.assert_called_once()
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_stop_playback(self, audio_engine, mock_backend, mock_event_bus):
        """Test stopping playback."""
        await audio_engine.start()

        result = await audio_engine.stop_playback()

        assert result is True
        mock_backend.stop.assert_called_once()
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_play_track_by_path(self, audio_engine, mock_backend, mock_event_bus):
        """Test playing track by path."""
        await audio_engine.start()

        result = await audio_engine.play_track_by_path("/music/song.mp3", track_id="t1")

        assert result is True
        mock_backend.play.assert_called_once_with("/music/song.mp3")
        assert mock_event_bus.publish.called


class TestPlaylistOperations:
    """Test playlist operations."""

    @pytest.mark.asyncio
    async def test_load_playlist(self, audio_engine, mock_event_bus, mock_playlist):
        """Test loading a playlist."""
        await audio_engine.start()

        result = await audio_engine.load_playlist(mock_playlist)

        assert result is True
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_load_empty_playlist(self, audio_engine):
        """Test loading empty playlist."""
        await audio_engine.start()

        empty_playlist = Mock()
        empty_playlist.tracks = []

        result = await audio_engine.load_playlist(empty_playlist)

        assert result is False

    @pytest.mark.asyncio
    async def test_play_playlist(self, audio_engine, mock_backend, mock_playlist):
        """Test playing a playlist."""
        await audio_engine.start()

        result = await audio_engine.play_playlist(mock_playlist)

        assert result is True
        mock_backend.play_file.assert_called()

    @pytest.mark.asyncio
    async def test_play_empty_playlist(self, audio_engine):
        """Test playing empty playlist."""
        await audio_engine.start()

        empty_playlist = Mock()
        empty_playlist.tracks = []

        result = await audio_engine.play_playlist(empty_playlist)

        assert result is False

    def test_set_playlist_sync(self, audio_engine, mock_backend, mock_playlist):
        """Test synchronous set_playlist."""
        audio_engine._is_running = True

        result = audio_engine.set_playlist(mock_playlist)

        assert result is True


class TestVolumeControl:
    """Test volume control."""

    @pytest.mark.asyncio
    async def test_set_volume(self, audio_engine, mock_backend, mock_event_bus, mock_state_manager):
        """Test setting volume."""
        await audio_engine.start()

        result = await audio_engine.set_volume(75)

        assert result is True
        mock_backend.set_volume.assert_called_once_with(75)
        mock_state_manager.update_volume.assert_called_once_with(75)
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_set_volume_when_not_running(self, audio_engine):
        """Test setting volume when engine not running."""
        result = await audio_engine.set_volume(75)

        assert result is False


class TestSeekOperations:
    """Test seek operations."""

    @pytest.mark.asyncio
    async def test_seek_to_position(self, audio_engine, mock_backend):
        """Test seeking to position."""
        await audio_engine.start()

        result = await audio_engine.seek_to_position(5000)

        assert result is True
        mock_backend.seek.assert_called_once_with(5000)


class TestStateManagement:
    """Test state management integration."""

    def test_get_playback_state(self, audio_engine, mock_backend):
        """Test getting playback state."""
        state = audio_engine.get_playback_state()

        assert "is_playing" in state
        assert "volume" in state
        assert "backend_type" in state

    @pytest.mark.asyncio
    async def test_get_state_dict(self, audio_engine):
        """Test getting state dictionary."""
        await audio_engine.start()

        state = audio_engine.get_state_dict()

        assert "engine_running" in state
        assert "backend_type" in state

    @pytest.mark.asyncio
    async def test_get_engine_statistics(self, audio_engine):
        """Test getting engine statistics."""
        await audio_engine.start()

        stats = audio_engine.get_engine_statistics()

        assert "engine" in stats
        assert "event_bus" in stats
        assert "current_state" in stats


class TestEventPublishing:
    """Test event publishing."""

    @pytest.mark.asyncio
    async def test_publishes_track_started_event(self, audio_engine, mock_event_bus):
        """Test publishes track started event."""
        await audio_engine.start()
        await audio_engine.play_file("/music/test.mp3")

        # Should have published TrackStartedEvent
        assert mock_event_bus.publish.call_count >= 1

    @pytest.mark.asyncio
    async def test_publishes_state_changed_event(self, audio_engine, mock_event_bus):
        """Test publishes playback state changed event."""
        await audio_engine.start()
        await audio_engine.play_file("/music/test.mp3")

        # Should have published PlaybackStateChangedEvent
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_publishes_volume_changed_event(self, audio_engine, mock_event_bus):
        """Test publishes volume changed event."""
        await audio_engine.start()
        await audio_engine.set_volume(75)

        # Should have published VolumeChangedEvent
        assert mock_event_bus.publish.called

    @pytest.mark.asyncio
    async def test_publishes_error_event_on_failure(self, audio_engine, mock_backend, mock_event_bus):
        """Test publishes error event on failure."""
        await audio_engine.start()
        mock_backend.play_file.side_effect = Exception("Test error")

        await audio_engine.play_file("/music/test.mp3")

        # Should have published ErrorEvent
        assert mock_event_bus.publish.called


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.asyncio
    async def test_handles_backend_play_error(self, audio_engine, mock_backend):
        """Test handles backend play error."""
        await audio_engine.start()
        mock_backend.play_file.side_effect = Exception("Backend error")

        result = await audio_engine.play_file("/music/test.mp3")

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_backend_pause_error(self, audio_engine, mock_backend):
        """Test handles backend pause error."""
        await audio_engine.start()
        mock_backend.pause.side_effect = Exception("Pause error")

        result = await audio_engine.pause_playback()

        assert result is False

    @pytest.mark.asyncio
    async def test_handles_volume_error(self, audio_engine, mock_backend):
        """Test handles volume set error."""
        await audio_engine.start()
        mock_backend.set_volume.side_effect = Exception("Volume error")

        result = await audio_engine.set_volume(75)

        assert result is False


class TestProperties:
    """Test engine properties."""

    @pytest.mark.asyncio
    async def test_is_running_property(self, audio_engine):
        """Test is_running property."""
        assert audio_engine.is_running is False

        await audio_engine.start()
        assert audio_engine.is_running is True

    def test_event_bus_property(self, audio_engine, mock_event_bus):
        """Test event_bus property."""
        assert audio_engine.event_bus == mock_event_bus

    def test_state_manager_property(self, audio_engine, mock_state_manager):
        """Test state_manager property."""
        assert audio_engine.state_manager == mock_state_manager


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_playback_cycle(self, audio_engine):
        """Test complete playback cycle."""
        await audio_engine.start()
        await audio_engine.play_file("/music/test.mp3")
        await audio_engine.pause_playback()
        await audio_engine.resume_playback()
        await audio_engine.stop_playback()
        await audio_engine.stop()

        assert audio_engine.is_running is False

    @pytest.mark.asyncio
    async def test_playlist_and_volume_control(self, audio_engine, mock_playlist):
        """Test playlist playback with volume control."""
        await audio_engine.start()
        await audio_engine.load_playlist(mock_playlist)
        await audio_engine.set_volume(75)
        await audio_engine.play_playlist(mock_playlist)

        # Should have completed without errors
        assert audio_engine.is_running is True
