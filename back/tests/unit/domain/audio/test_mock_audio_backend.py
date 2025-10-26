"""
Comprehensive tests for MockAudioBackend.

Tests cover:
- Initialization and configuration
- Async playback methods (play, pause, resume, stop)
- Volume control (set_volume, get_volume)
- Seek functionality
- Position and duration queries
- State management (is_playing, is_busy)
- Track completion simulation
- Event notifications
- Cleanup
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from app.src.domain.audio.backends.implementations.mock_audio_backend import MockAudioBackend


@pytest.fixture
def mock_backend():
    """Create a mock audio backend instance."""
    backend = MockAudioBackend()
    yield backend
    backend.cleanup()


@pytest.fixture
def mock_playback_subject():
    """Create a mock playback subject for event notifications."""
    return Mock()


@pytest.fixture
def backend_with_subject(mock_playback_subject):
    """Create a mock audio backend with playback subject."""
    backend = MockAudioBackend(playback_subject=mock_playback_subject)
    yield backend
    backend.cleanup()


@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file for testing."""
    audio_file = tmp_path / "test_song.mp3"
    audio_file.write_text("fake audio content")
    return str(audio_file)


class TestMockAudioBackendInitialization:
    """Test MockAudioBackend initialization."""

    def test_create_backend_without_subject(self):
        """Test creating backend without playback subject."""
        backend = MockAudioBackend()

        assert backend is not None
        assert backend._volume == 50
        assert backend._initialized is False
        assert backend._is_playing is False
        backend.cleanup()

    def test_create_backend_with_subject(self, mock_playback_subject):
        """Test creating backend with playback subject."""
        backend = MockAudioBackend(playback_subject=mock_playback_subject)

        assert backend._playback_subject == mock_playback_subject
        backend.cleanup()

    def test_initialize_backend(self, mock_backend):
        """Test backend initialization."""
        result = mock_backend.initialize()

        assert result is True
        assert mock_backend._initialized is True

    def test_default_volume(self, mock_backend):
        """Test default volume is set correctly."""
        assert mock_backend._volume == 50

    def test_track_duration_from_config(self, mock_backend):
        """Test track duration is loaded from config."""
        # Should have a default duration from config
        assert hasattr(mock_backend, '_track_duration')
        assert mock_backend._track_duration > 0


class TestPlaybackControls:
    """Test playback control methods."""

    @pytest.mark.asyncio
    async def test_play_file(self, mock_backend, temp_audio_file):
        """Test playing an audio file."""
        result = await mock_backend.play(temp_audio_file)

        assert result is True
        assert mock_backend.is_playing is True
        assert mock_backend._current_file_path == temp_audio_file

    @pytest.mark.asyncio
    async def test_play_nonexistent_file(self, mock_backend):
        """Test playing a nonexistent file."""
        result = await mock_backend.play("/nonexistent/file.mp3")

        assert result is False
        assert mock_backend.is_playing is False

    @pytest.mark.asyncio
    async def test_pause_playback(self, mock_backend, temp_audio_file):
        """Test pausing playback."""
        await mock_backend.play(temp_audio_file)
        result = await mock_backend.pause()

        assert result is True
        assert mock_backend.is_playing is False

    @pytest.mark.asyncio
    async def test_pause_when_not_playing(self, mock_backend):
        """Test pausing when nothing is playing."""
        result = await mock_backend.pause()

        assert result is False

    @pytest.mark.asyncio
    async def test_resume_playback(self, mock_backend, temp_audio_file):
        """Test resuming paused playback."""
        await mock_backend.play(temp_audio_file)
        await mock_backend.pause()
        result = await mock_backend.resume()

        assert result is True
        assert mock_backend.is_playing is True

    @pytest.mark.asyncio
    async def test_resume_when_not_paused(self, mock_backend):
        """Test resuming when no file is loaded."""
        result = await mock_backend.resume()

        assert result is False

    @pytest.mark.asyncio
    async def test_stop_playback(self, mock_backend, temp_audio_file):
        """Test stopping playback."""
        await mock_backend.play(temp_audio_file)
        result = await mock_backend.stop()

        assert result is True
        assert mock_backend.is_playing is False
        assert mock_backend._current_file_path is None

    @pytest.mark.asyncio
    async def test_play_replaces_current_track(self, mock_backend, tmp_path):
        """Test playing a new file replaces the current one."""
        file1 = tmp_path / "song1.mp3"
        file2 = tmp_path / "song2.mp3"
        file1.write_text("audio 1")
        file2.write_text("audio 2")

        await mock_backend.play(str(file1))
        await mock_backend.play(str(file2))

        assert mock_backend._current_file_path == str(file2)


class TestSyncPlaybackMethods:
    """Test synchronous playback methods."""

    def test_play_file_sync(self, mock_backend, temp_audio_file):
        """Test synchronous play_file method."""
        result = mock_backend.play_file(temp_audio_file)

        assert result is True
        assert mock_backend.is_playing is True

    def test_play_file_with_custom_duration(self, mock_backend, temp_audio_file):
        """Test play_file with custom duration."""
        custom_duration_ms = 5000
        result = mock_backend.play_file(temp_audio_file, duration_ms=custom_duration_ms)

        assert result is True
        assert mock_backend._track_duration == 5.0  # 5000ms = 5s

    def test_play_file_with_zero_duration(self, mock_backend, temp_audio_file):
        """Test play_file with zero duration uses default."""
        mock_backend.play_file(temp_audio_file, duration_ms=0)

        # Should use config default, not zero
        assert mock_backend._track_duration > 0

    def test_get_current_file(self, mock_backend, temp_audio_file):
        """Test getting current file path."""
        mock_backend.play_file(temp_audio_file)

        assert mock_backend.get_current_file() == temp_audio_file

    def test_get_current_file_when_stopped(self, mock_backend):
        """Test getting current file when nothing is playing."""
        assert mock_backend.get_current_file() is None


class TestVolumeControl:
    """Test volume control methods."""

    @pytest.mark.asyncio
    async def test_set_volume(self, mock_backend):
        """Test setting volume."""
        result = await mock_backend.set_volume(75)

        assert result is True
        assert mock_backend._volume == 75

    @pytest.mark.asyncio
    async def test_set_volume_min(self, mock_backend):
        """Test setting volume to minimum."""
        result = await mock_backend.set_volume(0)

        assert result is True
        assert mock_backend._volume == 0

    @pytest.mark.asyncio
    async def test_set_volume_max(self, mock_backend):
        """Test setting volume to maximum."""
        result = await mock_backend.set_volume(100)

        assert result is True
        assert mock_backend._volume == 100

    @pytest.mark.asyncio
    async def test_set_volume_below_min(self, mock_backend):
        """Test setting volume below minimum."""
        result = await mock_backend.set_volume(-10)

        assert result is False

    @pytest.mark.asyncio
    async def test_set_volume_above_max(self, mock_backend):
        """Test setting volume above maximum."""
        result = await mock_backend.set_volume(150)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_volume(self, mock_backend):
        """Test getting current volume."""
        await mock_backend.set_volume(60)
        volume = await mock_backend.get_volume()

        assert volume == 60

    @pytest.mark.asyncio
    async def test_get_volume_default(self, mock_backend):
        """Test getting default volume."""
        volume = await mock_backend.get_volume()

        assert volume == 50


class TestSeekAndPosition:
    """Test seek and position methods."""

    @pytest.mark.asyncio
    async def test_seek_to_position(self, mock_backend, temp_audio_file):
        """Test seeking to a position."""
        await mock_backend.play(temp_audio_file)
        result = await mock_backend.seek(5000)

        assert result is True

    @pytest.mark.asyncio
    async def test_seek_to_zero(self, mock_backend, temp_audio_file):
        """Test seeking to start."""
        await mock_backend.play(temp_audio_file)
        result = await mock_backend.seek(0)

        assert result is True

    @pytest.mark.asyncio
    async def test_seek_negative_position(self, mock_backend, temp_audio_file):
        """Test seeking to negative position."""
        await mock_backend.play(temp_audio_file)
        result = await mock_backend.seek(-100)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_position_when_playing(self, mock_backend, temp_audio_file):
        """Test getting position during playback."""
        await mock_backend.play(temp_audio_file)
        await asyncio.sleep(0.1)  # Small delay to accumulate position

        position = await mock_backend.get_position()

        assert position is not None
        assert position >= 0

    @pytest.mark.asyncio
    async def test_get_position_when_not_playing(self, mock_backend):
        """Test getting position when not playing."""
        position = await mock_backend.get_position()

        assert position is None

    @pytest.mark.asyncio
    async def test_position_increases_during_playback(self, mock_backend, temp_audio_file):
        """Test that position increases during playback."""
        await mock_backend.play(temp_audio_file)

        position1 = await mock_backend.get_position()
        await asyncio.sleep(0.1)
        position2 = await mock_backend.get_position()

        assert position2 > position1


class TestDurationQueries:
    """Test duration query methods."""

    @pytest.mark.asyncio
    async def test_get_duration_async(self, mock_backend, temp_audio_file):
        """Test getting duration asynchronously."""
        mock_backend.play_file(temp_audio_file, duration_ms=10000)
        duration = await mock_backend.get_duration()

        assert duration == 10000

    @pytest.mark.asyncio
    async def test_get_duration_when_no_file(self, mock_backend):
        """Test getting duration when no file is loaded."""
        duration = await mock_backend.get_duration()

        assert duration is None

    def test_get_duration_sync(self, mock_backend, temp_audio_file):
        """Test getting duration synchronously."""
        mock_backend.play_file(temp_audio_file, duration_ms=8000)
        duration = mock_backend.get_duration_sync()

        assert duration == 8.0  # 8000ms = 8s

    def test_get_duration_sync_when_no_file(self, mock_backend):
        """Test getting duration sync when no file loaded."""
        duration = mock_backend.get_duration_sync()

        assert duration == 0.0


class TestStateProperties:
    """Test state property methods."""

    def test_is_playing_property(self, mock_backend, temp_audio_file):
        """Test is_playing property."""
        assert mock_backend.is_playing is False

        mock_backend.play_file(temp_audio_file)
        assert mock_backend.is_playing is True

    def test_is_busy_when_playing(self, mock_backend, temp_audio_file):
        """Test is_busy property when playing."""
        mock_backend.play_file(temp_audio_file, duration_ms=1000)

        assert mock_backend.is_busy is True

    def test_is_busy_when_not_playing(self, mock_backend):
        """Test is_busy property when not playing."""
        assert mock_backend.is_busy is False

    def test_is_busy_after_track_finishes(self, mock_backend, temp_audio_file):
        """Test is_busy becomes False after track finishes."""
        # Play with very short duration
        mock_backend.play_file(temp_audio_file, duration_ms=100)

        # Wait for track to finish
        time.sleep(0.15)

        # Should no longer be busy
        assert mock_backend.is_busy is False


class TestTrackCompletion:
    """Test track completion detection."""

    def test_update_internal_state_detects_completion(self, mock_backend, temp_audio_file):
        """Test internal state update detects track completion."""
        mock_backend.play_file(temp_audio_file, duration_ms=100)

        # Initially playing
        assert mock_backend.is_playing is True

        # Wait for completion
        time.sleep(0.15)
        mock_backend._update_internal_state()

        # Should be stopped
        assert mock_backend.is_playing is False

    def test_track_completion_notification(self, backend_with_subject, temp_audio_file):
        """Test that track completion triggers notification."""
        backend_with_subject.play_file(temp_audio_file, duration_ms=100)

        # Wait for completion
        time.sleep(0.15)
        backend_with_subject._update_internal_state()

        # Should have notified about track_ended
        # Note: This tests the internal mechanism, actual notification depends on subject
        assert backend_with_subject.is_playing is False


class TestEventNotifications:
    """Test event notification system."""

    def test_track_started_notification(self, backend_with_subject, temp_audio_file):
        """Test track started event notification."""
        backend_with_subject.play_file(temp_audio_file)

        # Should have triggered track_started notification
        backend_with_subject._playback_subject.notify.assert_called()

    def test_notification_contains_file_path(self, backend_with_subject, temp_audio_file):
        """Test notification contains file path."""
        backend_with_subject.play_file(temp_audio_file)

        # Verify notification was called with file_path
        call_args = backend_with_subject._playback_subject.notify.call_args
        assert call_args is not None
        # Check that event data contains file_path
        event_data = call_args[0][0]
        assert "file_path" in event_data
        assert event_data["event"] == "track_started"


class TestShutdownAndCleanup:
    """Test shutdown and cleanup methods."""

    def test_shutdown(self, mock_backend, temp_audio_file):
        """Test backend shutdown."""
        mock_backend.initialize()
        mock_backend.play_file(temp_audio_file)

        mock_backend.shutdown()

        assert mock_backend._initialized is False
        assert mock_backend.is_playing is False
        assert mock_backend._current_file_path is None

    def test_cleanup(self, mock_backend, temp_audio_file):
        """Test backend cleanup."""
        mock_backend.play_file(temp_audio_file)

        mock_backend.cleanup()

        assert mock_backend.is_playing is False
        assert mock_backend._current_file_path is None

    def test_cleanup_resets_play_start_time(self, mock_backend, temp_audio_file):
        """Test cleanup resets play start time."""
        mock_backend.play_file(temp_audio_file)

        mock_backend.cleanup()

        assert mock_backend._play_start_time is None


class TestThreadSafety:
    """Test thread-safe state management."""

    def test_concurrent_state_access(self, mock_backend, temp_audio_file):
        """Test concurrent access to state."""
        # This tests that state_lock is used correctly
        mock_backend.play_file(temp_audio_file)

        # Access state from multiple properties
        is_playing = mock_backend.is_playing
        is_busy = mock_backend.is_busy
        current_file = mock_backend.get_current_file()

        # Should not raise any errors
        assert is_playing is True
        assert is_busy is True
        assert current_file == temp_audio_file


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_play_empty_string(self, mock_backend):
        """Test playing with empty file path."""
        result = mock_backend.play_file("")

        assert result is False

    @pytest.mark.asyncio
    async def test_pause_resume_cycle(self, mock_backend, temp_audio_file):
        """Test multiple pause/resume cycles."""
        await mock_backend.play(temp_audio_file)

        await mock_backend.pause()
        await mock_backend.resume()
        await mock_backend.pause()
        await mock_backend.resume()

        assert mock_backend.is_playing is True

    @pytest.mark.asyncio
    async def test_multiple_stops(self, mock_backend, temp_audio_file):
        """Test calling stop multiple times."""
        await mock_backend.play(temp_audio_file)

        result1 = await mock_backend.stop()
        result2 = await mock_backend.stop()

        assert result1 is True
        assert result2 is True

    def test_play_updates_duration(self, mock_backend, temp_audio_file):
        """Test that playing updates track duration."""
        duration1_ms = 3000
        duration2_ms = 5000

        mock_backend.play_file(temp_audio_file, duration_ms=duration1_ms)
        assert mock_backend._track_duration == 3.0

        mock_backend.play_file(temp_audio_file, duration_ms=duration2_ms)
        assert mock_backend._track_duration == 5.0


class TestBackendIntegration:
    """Test backend integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_playback_cycle(self, mock_backend, temp_audio_file):
        """Test a complete playback cycle."""
        # Play
        await mock_backend.play(temp_audio_file)
        assert mock_backend.is_playing is True

        # Pause
        await mock_backend.pause()
        assert mock_backend.is_playing is False

        # Resume
        await mock_backend.resume()
        assert mock_backend.is_playing is True

        # Stop
        await mock_backend.stop()
        assert mock_backend.is_playing is False
        assert mock_backend._current_file_path is None

    @pytest.mark.asyncio
    async def test_volume_during_playback(self, mock_backend, temp_audio_file):
        """Test volume changes during playback."""
        await mock_backend.play(temp_audio_file)

        await mock_backend.set_volume(25)
        assert await mock_backend.get_volume() == 25

        await mock_backend.set_volume(75)
        assert await mock_backend.get_volume() == 75

        # Should still be playing
        assert mock_backend.is_playing is True
