"""
Comprehensive tests for AudioPlayer controller.

Tests cover:
- Initialization
- Playback controls (play, pause, resume, stop, toggle)
- Volume control
- Seek functionality
- Position and duration queries
- State management
- Track finish detection
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from app.src.application.controllers.audio_player_controller import AudioPlayer, PlaybackState


class TestAudioPlayerInitialization:
    """Test AudioPlayer initialization."""

    def test_create_audio_player(self):
        """Test creating audio player with backend."""
        backend = Mock()
        player = AudioPlayer(backend)

        assert player._backend == backend
        assert player._state == PlaybackState.STOPPED
        assert player._current_file is None
        assert player._volume == 50

    def test_initial_state_is_stopped(self):
        """Test initial playback state is stopped."""
        backend = Mock()
        player = AudioPlayer(backend)

        assert player.is_stopped() is True
        assert player.is_playing() is False
        assert player.is_paused() is False


class TestPlaybackControls:
    """Test playback control operations."""

    @pytest.fixture
    def backend(self):
        """Create mock audio backend."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend.pause_sync = Mock(return_value=True)
        backend.resume_sync = Mock(return_value=True)
        backend.stop_sync = Mock(return_value=True)
        return backend

    @pytest.fixture
    def player(self, backend):
        """Create audio player with mock backend."""
        return AudioPlayer(backend)

    def test_play_file_success(self, player, backend):
        """Test playing a file successfully."""
        success = player.play_file("/music/song.mp3")

        assert success is True
        assert player._state == PlaybackState.PLAYING
        assert player._current_file == "/music/song.mp3"
        backend.play_file.assert_called_once()

    def test_play_file_empty_path(self, player, backend):
        """Test playing with empty path fails."""
        success = player.play_file("")

        assert success is False
        backend.play_file.assert_not_called()

    def test_play_file_with_duration(self, player, backend):
        """Test playing file with duration hint."""
        success = player.play_file("/music/song.mp3", duration_ms=180000)

        assert success is True
        backend.play_file.assert_called_with("/music/song.mp3", duration_ms=180000)

    def test_pause_when_playing(self, player, backend):
        """Test pausing active playback."""
        player.play_file("/music/song.mp3")
        success = player.pause()

        assert success is True
        assert player._state == PlaybackState.PAUSED
        backend.pause_sync.assert_called_once()

    def test_pause_when_not_playing(self, player):
        """Test pausing when not playing fails."""
        success = player.pause()

        assert success is False

    def test_resume_when_paused(self, player, backend):
        """Test resuming paused playback."""
        player.play_file("/music/song.mp3")
        player.pause()
        success = player.resume()

        assert success is True
        assert player._state == PlaybackState.PLAYING
        backend.resume_sync.assert_called_once()

    def test_resume_when_not_paused(self, player):
        """Test resuming when not paused fails."""
        success = player.resume()

        assert success is False

    def test_stop_active_playback(self, player, backend):
        """Test stopping active playback."""
        player.play_file("/music/song.mp3")
        success = player.stop()

        assert success is True
        assert player._state == PlaybackState.STOPPED
        assert player._current_file is None
        backend.stop_sync.assert_called_once()

    def test_stop_already_stopped(self, player):
        """Test stopping when already stopped."""
        success = player.stop()

        assert success is True  # Idempotent

    def test_toggle_pause_when_playing(self, player, backend):
        """Test toggle pauses when playing."""
        player.play_file("/music/song.mp3")
        success = player.toggle_pause()

        assert success is True
        assert player._state == PlaybackState.PAUSED

    def test_toggle_pause_when_paused(self, player, backend):
        """Test toggle resumes when paused."""
        player.play_file("/music/song.mp3")
        player.pause()
        success = player.toggle_pause()

        assert success is True
        assert player._state == PlaybackState.PLAYING

    def test_toggle_pause_when_stopped(self, player):
        """Test toggle fails when stopped."""
        success = player.toggle_pause()

        assert success is False


class TestVolumeControl:
    """Test volume control operations."""

    @pytest.fixture
    def backend(self):
        """Create mock backend with async volume support."""
        backend = Mock()
        backend.set_volume = AsyncMock(return_value=True)
        backend.play_file = Mock(return_value=True)
        return backend

    @pytest.fixture
    def player(self, backend):
        """Create audio player."""
        return AudioPlayer(backend)

    @pytest.mark.asyncio
    async def test_set_volume_valid(self, player, backend):
        """Test setting valid volume."""
        success = await player.set_volume(75)

        assert success is True
        assert player._volume == 75
        backend.set_volume.assert_called_with(75)

    @pytest.mark.asyncio
    async def test_set_volume_minimum(self, player, backend):
        """Test setting volume to 0."""
        success = await player.set_volume(0)

        assert success is True
        assert player._volume == 0

    @pytest.mark.asyncio
    async def test_set_volume_maximum(self, player, backend):
        """Test setting volume to 100."""
        success = await player.set_volume(100)

        assert success is True
        assert player._volume == 100

    @pytest.mark.asyncio
    async def test_set_volume_below_minimum(self, player, backend):
        """Test setting volume below 0 fails."""
        success = await player.set_volume(-10)

        assert success is False
        backend.set_volume.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_volume_above_maximum(self, player, backend):
        """Test setting volume above 100 fails."""
        success = await player.set_volume(150)

        assert success is False
        backend.set_volume.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_volume(self, player):
        """Test getting current volume."""
        await player.set_volume(80)
        volume = player.get_volume()

        assert volume == 80

    def test_default_volume(self, player):
        """Test default volume is 50."""
        volume = player.get_volume()

        assert volume == 50


class TestPositionAndDuration:
    """Test position and duration queries."""

    @pytest.fixture
    def backend(self):
        """Create mock backend."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend.get_position_sync = Mock(return_value=45.5)
        backend.get_duration = Mock(return_value=180.0)
        return backend

    @pytest.fixture
    def player(self, backend):
        """Create audio player."""
        return AudioPlayer(backend)

    def test_get_position_when_playing(self, player, backend):
        """Test getting position when playing."""
        player.play_file("/music/song.mp3")
        position = player.get_position()

        assert position == 45.5
        backend.get_position_sync.assert_called_once()

    def test_get_position_when_stopped(self, player):
        """Test position is 0 when stopped."""
        position = player.get_position()

        assert position == 0.0

    def test_get_duration_when_loaded(self, player, backend):
        """Test getting duration of loaded track."""
        player.play_file("/music/song.mp3")
        duration = player.get_duration()

        assert duration == 180.0
        backend.get_duration.assert_called_once()

    def test_get_duration_when_no_file(self, player):
        """Test duration is 0 when no file loaded."""
        duration = player.get_duration()

        assert duration == 0.0


class TestSeekFunctionality:
    """Test seek operations."""

    @pytest.fixture
    def backend(self):
        """Create mock backend with seek support."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend.seek = Mock(return_value=True)
        return backend

    @pytest.fixture
    def player(self, backend):
        """Create audio player."""
        return AudioPlayer(backend)

    def test_seek_when_playing(self, player, backend):
        """Test seeking during playback."""
        player.play_file("/music/song.mp3")
        success = player.seek(60.0)

        assert success is True
        backend.seek.assert_called_with(60000)  # Converted to milliseconds

    def test_seek_when_stopped(self, player, backend):
        """Test seeking when stopped fails."""
        success = player.seek(30.0)

        assert success is False
        backend.seek.assert_not_called()

    def test_seek_to_beginning(self, player, backend):
        """Test seeking to beginning."""
        player.play_file("/music/song.mp3")
        success = player.seek(0.0)

        assert success is True
        backend.seek.assert_called_with(0)


class TestStateQueries:
    """Test state query methods."""

    @pytest.fixture
    def backend(self):
        """Create mock backend."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend.set_volume = AsyncMock(return_value=True)
        backend.get_position_sync = Mock(return_value=30.0)
        backend.get_duration = Mock(return_value=180.0)
        return backend

    @pytest.fixture
    def player(self, backend):
        """Create audio player."""
        return AudioPlayer(backend)

    def test_get_state_when_stopped(self, player):
        """Test state when stopped."""
        state = player.get_state()

        assert state["state"] == "stopped"
        assert state["is_playing"] is False
        assert state["is_paused"] is False
        assert state["current_file"] is None
        assert state["volume"] == 50

    @pytest.mark.asyncio
    async def test_get_state_when_playing(self, player, backend):
        """Test state when playing."""
        player.play_file("/music/song.mp3")
        await player.set_volume(75)
        state = player.get_state()

        assert state["state"] == "playing"
        assert state["is_playing"] is True
        assert state["is_paused"] is False
        assert state["current_file"] == "/music/song.mp3"
        assert state["volume"] == 75
        assert state["position"] == 30.0
        assert state["duration"] == 180.0

    def test_is_playing(self, player, backend):
        """Test is_playing query."""
        assert player.is_playing() is False

        player.play_file("/music/song.mp3")
        assert player.is_playing() is True

    def test_is_paused(self, player, backend):
        """Test is_paused query."""
        backend.pause_sync = Mock(return_value=True)

        assert player.is_paused() is False

        player.play_file("/music/song.mp3")
        player.pause()
        assert player.is_paused() is True

    def test_is_stopped(self, player, backend):
        """Test is_stopped query."""
        assert player.is_stopped() is True

        player.play_file("/music/song.mp3")
        assert player.is_stopped() is False


class TestTrackFinishDetection:
    """Test track finish detection."""

    @pytest.fixture
    def backend(self):
        """Create mock backend."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend.is_busy = True
        return backend

    @pytest.fixture
    def player(self, backend):
        """Create audio player."""
        return AudioPlayer(backend)

    def test_has_finished_when_not_playing(self, player):
        """Test finished detection when not playing."""
        assert player.has_finished() is False

    def test_has_finished_backend_busy(self, player, backend):
        """Test not finished when backend is busy."""
        player.play_file("/music/song.mp3")
        backend.is_busy = True

        assert player.has_finished() is False

    def test_has_finished_backend_not_busy(self, player, backend):
        """Test finished when backend is not busy."""
        player.play_file("/music/song.mp3")
        backend.is_busy = False

        assert player.has_finished() is True
        assert player._state == PlaybackState.STOPPED

    def test_has_finished_position_equals_duration(self, player, backend):
        """Test finished when position equals duration."""
        del backend.is_busy  # Remove is_busy attribute
        backend.get_position_sync = Mock(return_value=180.0)
        backend.get_duration = Mock(return_value=180.0)

        player.play_file("/music/song.mp3")
        finished = player.has_finished()

        assert finished is True
        assert player._state == PlaybackState.STOPPED


class TestErrorHandling:
    """Test error handling in audio player."""

    def test_play_file_backend_error(self):
        """Test play handles backend errors."""
        backend = Mock()
        backend.play_file = Mock(side_effect=Exception("Backend error"))

        player = AudioPlayer(backend)
        success = player.play_file("/music/song.mp3")

        assert success is False

    @pytest.mark.asyncio
    async def test_volume_backend_error(self):
        """Test volume handles backend errors."""
        backend = Mock()
        backend.set_volume = AsyncMock(side_effect=Exception("Volume error"))

        player = AudioPlayer(backend)
        success = await player.set_volume(50)

        assert success is False

    def test_seek_backend_error(self):
        """Test seek handles backend errors."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend.seek = Mock(side_effect=Exception("Seek error"))

        player = AudioPlayer(backend)
        player.play_file("/music/song.mp3")
        success = player.seek(30.0)

        assert success is False


class TestAsyncBackendSupport:
    """Test async backend compatibility."""

    def test_play_with_async_backend(self):
        """Test playing with async backend method."""
        backend = Mock()
        async_play = AsyncMock(return_value=True)
        backend.play = async_play
        delattr(backend, "play_file")  # Remove sync method

        player = AudioPlayer(backend)

        with patch("asyncio.new_event_loop") as mock_loop:
            loop_instance = Mock()
            mock_loop.return_value = loop_instance
            loop_instance.run_until_complete = Mock(return_value=True)

            success = player.play_file("/music/song.mp3")

            assert success is True

    @pytest.mark.asyncio
    async def test_volume_with_async_backend(self):
        """Test volume with async backend (proper async/await pattern)."""
        backend = Mock()
        backend.set_volume = AsyncMock(return_value=True)

        player = AudioPlayer(backend)
        success = await player.set_volume(75)

        assert success is True
        assert player._volume == 75
        backend.set_volume.assert_called_with(75)
