"""Tests for AudioController class (DDD clean architecture implementation)."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from app.src.application.controllers.audio_controller import AudioController
from app.src.application.controllers.audio_player_controller import PlaybackState


class TestAudioController:
    """Test suite for AudioController class (DDD clean architecture)."""

    @pytest.fixture
    def mock_audio_service(self):
        """Mock audio service with backend architecture."""
        # Create the backend mock
        mock_backend = Mock()
        mock_backend.is_available.return_value = True
        mock_backend.play_file.return_value = True
        mock_backend.play.return_value = True
        mock_backend.pause.return_value = True
        mock_backend.stop.return_value = True
        mock_backend.resume.return_value = True
        mock_backend.set_volume.return_value = True
        mock_backend.get_volume.return_value = 0.5
        mock_backend.seek_to.return_value = True
        mock_backend.is_playing.return_value = False
        mock_backend.get_current_position.return_value = 0.0
        mock_backend.get_duration.return_value = 180.0

        # Create the audio service mock with the backend
        mock_service = Mock()
        mock_service._backend = mock_backend

        return mock_service

    @pytest.fixture
    def adapter(self, mock_audio_service):
        """Create AudioController instance with mock service."""
        with patch('app.src.application.controllers.audio_controller.AudioPlayer') as mock_audio_player_class:
            mock_audio_player = Mock()
            mock_audio_player.play_file.return_value = True
            mock_audio_player.pause.return_value = True
            mock_audio_player.resume.return_value = True
            mock_audio_player.stop.return_value = True
            mock_audio_player.set_volume.return_value = True
            mock_audio_player.get_volume.return_value = 50
            mock_audio_player.seek.return_value = True
            mock_audio_player.is_playing.return_value = False
            mock_audio_player.get_position.return_value = 0.0
            mock_audio_player.get_duration.return_value = 180.0
            mock_audio_player.get_state.return_value = PlaybackState.STOPPED
            mock_audio_player.get_current_file.return_value = None

            mock_audio_player_class.return_value = mock_audio_player

            adapter_instance = AudioController(mock_audio_service)
            return adapter_instance

    def test_init(self, mock_audio_service):
        """Test AudioController initialization."""
        adapter = AudioController(mock_audio_service)
        assert adapter._audio_service == mock_audio_service
        assert adapter._backend == mock_audio_service._backend
        assert adapter._current_volume == 50
        assert adapter._audio_player is not None

    def test_init_with_defaults(self):
        """Test AudioController initialization with default values."""
        adapter = AudioController()
        assert adapter._audio_service is None
        assert adapter._backend is None
        assert adapter._current_volume == 50
        assert adapter._audio_player is None

    def test_init_with_service_no_backend(self):
        """Test initialization with service that has no _backend attribute."""
        mock_service = Mock()
        # Remove _backend attribute
        del mock_service._backend

        adapter = AudioController(mock_service)
        assert adapter._backend == mock_service  # Should use service directly
        assert adapter._audio_player is not None

    def test_audio_service_property(self, adapter, mock_audio_service):
        """Test audio_service property."""
        assert adapter.audio_service == mock_audio_service

    def test_is_available_true(self, adapter):
        """Test is_available when backend is available."""
        assert adapter.is_available() is True

    def test_is_available_false_no_backend(self):
        """Test is_available when no backend."""
        adapter = AudioController()
        assert adapter.is_available() is False

    def test_is_available_false_backend_unavailable(self, mock_audio_service):
        """Test is_available when backend reports unavailable."""
        mock_audio_service._backend.is_available.return_value = False
        adapter = AudioController(mock_audio_service)
        assert adapter.is_available() is False

    def test_play_success(self, adapter, mock_audio_service):
        """Test successful audio playback."""
        track_path = "/path/to/track.mp3"
        result = adapter.play(track_path)

        assert result is True
        adapter._audio_player.play_file.assert_called_once_with(track_path)

    def test_play_no_path(self, adapter):
        """Test play with no track path."""
        result = adapter.play(None)
        assert result is False

    def test_play_no_player(self):
        """Test play with no audio player."""
        adapter = AudioController()
        result = adapter.play("/path/to/track.mp3")
        assert result is False

    def test_pause_success(self, adapter):
        """Test successful pause."""
        # Set up audio player to be in playing state
        adapter._audio_player.get_state.return_value = PlaybackState.PLAYING
        adapter._audio_player.pause.return_value = True

        result = adapter.pause()
        assert result is True
        adapter._audio_player.pause.assert_called_once()

    def test_pause_no_player(self):
        """Test pause with no audio player."""
        adapter = AudioController()
        result = adapter.pause()
        assert result is False

    def test_resume_success(self, adapter):
        """Test successful resume."""
        adapter._audio_player.get_state.return_value = PlaybackState.PAUSED
        adapter._audio_player.resume.return_value = True

        result = adapter.resume()
        assert result is True
        adapter._audio_player.resume.assert_called_once()

    def test_resume_no_player(self):
        """Test resume with no audio player."""
        adapter = AudioController()
        result = adapter.resume()
        assert result is False

    def test_stop_success(self, adapter):
        """Test successful stop."""
        adapter._audio_player.stop.return_value = True

        result = adapter.stop()
        assert result is True
        adapter._audio_player.stop.assert_called_once()

    def test_stop_no_player(self):
        """Test stop with no audio player."""
        adapter = AudioController()
        result = adapter.stop()
        assert result is False

    def test_toggle_play_pause_from_playing(self, adapter):
        """Test toggle from playing to paused."""
        adapter._audio_player.get_state.return_value = PlaybackState.PLAYING
        adapter._audio_player.pause.return_value = True

        result = adapter.toggle_play_pause()
        assert result is True
        adapter._audio_player.pause.assert_called_once()

    def test_toggle_play_pause_from_paused(self, adapter):
        """Test toggle from paused to playing."""
        adapter._audio_player.get_state.return_value = PlaybackState.PAUSED
        adapter._audio_player.resume.return_value = True

        result = adapter.toggle_play_pause()
        assert result is True
        adapter._audio_player.resume.assert_called_once()

    def test_toggle_play_pause_from_stopped(self, adapter):
        """Test toggle from stopped state."""
        adapter._audio_player.get_state.return_value = PlaybackState.STOPPED

        result = adapter.toggle_play_pause()
        assert result is False

    def test_toggle_playback_alias(self, adapter):
        """Test toggle_playback alias method."""
        adapter._audio_player.get_state.return_value = PlaybackState.PLAYING
        adapter._audio_player.pause.return_value = True

        result = adapter.toggle_playback()
        assert result is True
        adapter._audio_player.pause.assert_called_once()

    def test_seek_to_success(self, adapter):
        """Test successful seek."""
        adapter._audio_player.seek.return_value = True

        result = adapter.seek_to(30000)  # 30 seconds in ms
        assert result is True
        adapter._audio_player.seek.assert_called_once_with(30.0)

    def test_seek_to_no_player(self):
        """Test seek with no audio player."""
        adapter = AudioController()
        result = adapter.seek_to(30000)
        assert result is False

    def test_is_playing_true(self, adapter):
        """Test is_playing when audio is playing."""
        adapter._audio_player.is_playing.return_value = True
        assert adapter.is_playing() is True

    def test_is_playing_false_no_player(self):
        """Test is_playing with no audio player."""
        adapter = AudioController()
        assert adapter.is_playing() is False

    def test_get_playback_state(self, adapter):
        """Test get_playback_state method."""
        adapter._audio_player.get_state.return_value = PlaybackState.PLAYING
        assert adapter.get_playback_state() == "playing"

    def test_get_playback_state_no_player(self):
        """Test get_playback_state with no audio player."""
        adapter = AudioController()
        assert adapter.get_playback_state() == "stopped"

    def test_set_volume_success(self, adapter):
        """Test successful volume setting."""
        adapter._audio_player.set_volume.return_value = True

        result = adapter.set_volume(75)
        assert result is True
        assert adapter._current_volume == 75
        adapter._audio_player.set_volume.assert_called_once_with(75)

    def test_set_volume_clamp_high(self, adapter):
        """Test volume clamping for high values."""
        adapter._audio_player.set_volume.return_value = True

        result = adapter.set_volume(150)
        assert result is True
        assert adapter._current_volume == 100
        adapter._audio_player.set_volume.assert_called_once_with(100)

    def test_set_volume_clamp_low(self, adapter):
        """Test volume clamping for low values."""
        adapter._audio_player.set_volume.return_value = True

        result = adapter.set_volume(-10)
        assert result is True
        assert adapter._current_volume == 0
        adapter._audio_player.set_volume.assert_called_once_with(0)

    def test_set_volume_no_player(self):
        """Test set volume with no audio player."""
        adapter = AudioController()
        result = adapter.set_volume(75)
        assert result is True
        assert adapter._current_volume == 75

    def test_get_current_volume_from_player(self, adapter):
        """Test get volume from audio player."""
        adapter._audio_player.get_volume.return_value = 80
        assert adapter.get_current_volume() == 80

    def test_get_current_volume_no_player(self):
        """Test get volume with no audio player."""
        adapter = AudioController()
        adapter._current_volume = 60
        assert adapter.get_current_volume() == 60

    def test_get_volume_alias(self, adapter):
        """Test get_volume alias method."""
        adapter._audio_player.get_volume.return_value = 80
        assert adapter.get_volume() == 80

    def test_volume_up(self, adapter):
        """Test volume up functionality."""
        adapter._audio_player.get_volume.return_value = 50
        adapter._audio_player.set_volume.return_value = True

        result = adapter.volume_up(10)
        assert result is True
        adapter._audio_player.set_volume.assert_called_once_with(60)

    def test_volume_up_max_clamp(self, adapter):
        """Test volume up with clamping at maximum."""
        adapter._audio_player.get_volume.return_value = 95
        adapter._audio_player.set_volume.return_value = True

        result = adapter.volume_up(10)
        assert result is True
        adapter._audio_player.set_volume.assert_called_once_with(100)

    def test_increase_volume_alias(self, adapter):
        """Test increase_volume alias method."""
        adapter._audio_player.get_volume.return_value = 50
        adapter._audio_player.set_volume.return_value = True

        result = adapter.increase_volume(10)
        assert result is True
        adapter._audio_player.set_volume.assert_called_once_with(60)

    def test_volume_down(self, adapter):
        """Test volume down functionality."""
        adapter._audio_player.get_volume.return_value = 50
        adapter._audio_player.set_volume.return_value = True

        result = adapter.volume_down(10)
        assert result is True
        adapter._audio_player.set_volume.assert_called_once_with(40)

    def test_volume_down_min_clamp(self, adapter):
        """Test volume down with clamping at minimum."""
        adapter._audio_player.get_volume.return_value = 5
        adapter._audio_player.set_volume.return_value = True

        result = adapter.volume_down(10)
        assert result is True
        adapter._audio_player.set_volume.assert_called_once_with(0)

    def test_decrease_volume_alias(self, adapter):
        """Test decrease_volume alias method."""
        adapter._audio_player.get_volume.return_value = 50
        adapter._audio_player.set_volume.return_value = True

        result = adapter.decrease_volume(10)
        assert result is True
        adapter._audio_player.set_volume.assert_called_once_with(40)

    def test_get_current_position(self, adapter):
        """Test get current position."""
        adapter._audio_player.get_position.return_value = 45.5
        assert adapter.get_current_position() == 45.5

    def test_get_current_position_no_player(self):
        """Test get current position with no audio player."""
        adapter = AudioController()
        assert adapter.get_current_position() == 0.0

    def test_get_duration(self, adapter):
        """Test get duration."""
        adapter._audio_player.get_duration.return_value = 180.0
        assert adapter.get_duration() == 180.0

    def test_get_duration_no_player(self):
        """Test get duration with no audio player."""
        adapter = AudioController()
        assert adapter.get_duration() == 0.0

    @pytest.mark.asyncio
    async def test_get_playback_status_success(self, adapter):
        """Test get comprehensive playback status."""
        adapter._audio_player.get_position.return_value = 30.0
        adapter._audio_player.get_duration.return_value = 180.0
        adapter._audio_player.is_playing.return_value = True
        adapter._audio_player.get_state.return_value = PlaybackState.PLAYING
        adapter._audio_player.get_volume.return_value = 75

        status = await adapter.get_playback_status()

        assert status["is_playing"] is True
        assert status["state"] == "playing"
        assert status["position"] == 30.0
        assert status["duration"] == 180.0
        assert status["volume"] == 75
        assert status["backend_available"] is True
        assert status["controller_type"] == "AudioController"
        assert status["supports_seek"] is True
        assert status["supports_volume"] is True

    @pytest.mark.asyncio
    async def test_get_playback_status_no_player(self):
        """Test get playback status with no audio player."""
        adapter = AudioController()

        status = await adapter.get_playback_status()

        assert status["is_playing"] is False
        assert status["state"] == "stopped"
        assert status["position"] == 0.0
        assert status["duration"] == 0.0
        assert status["volume"] == 50
        assert status["backend_available"] is False
        assert status["supports_seek"] is False
        assert status["supports_volume"] is False

    def test_get_state(self, adapter):
        """Test get_state method."""
        adapter._audio_player.get_state.return_value = PlaybackState.PAUSED
        assert adapter.get_state() == PlaybackState.PAUSED

    def test_get_state_no_player(self):
        """Test get_state with no audio player."""
        adapter = AudioController()
        assert adapter.get_state() == PlaybackState.STOPPED

    def test_get_current_file(self, adapter):
        """Test get_current_file method."""
        adapter._audio_player.get_current_file.return_value = "/path/to/track.mp3"
        assert adapter.get_current_file() == "/path/to/track.mp3"

    def test_get_current_file_no_player(self):
        """Test get_current_file with no audio player."""
        adapter = AudioController()
        assert adapter.get_current_file() is None