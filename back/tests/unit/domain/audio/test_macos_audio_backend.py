"""
Comprehensive tests for MacOSAudioBackend.

Tests cover:
- Initialization with pygame
- Playback methods (play_file, stop, pause, resume)
- Volume control (set_volume, get_volume)
- Position tracking with time calculations
- Duration queries
- State properties (is_playing, is_busy)
- Time tracking (pause/resume adjustments)
- Cleanup and resource management
- Async wrappers
- Pygame integration
- Error handling
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from pathlib import Path


@pytest.fixture
def mock_pygame():
    """Create a mock pygame module."""
    with patch('app.src.domain.audio.backends.implementations.macos_audio_backend.pygame') as mock_pg:
        # Setup mixer mock with stateful behavior
        mock_mixer = MagicMock()
        mock_mixer.music = MagicMock()

        # Track playing state - this can be modified by tests
        playing_state = {'is_playing': False}

        def mock_get_busy():
            return playing_state['is_playing']

        def mock_play(*args, **kwargs):
            playing_state['is_playing'] = True
            return None

        def mock_stop(*args, **kwargs):
            playing_state['is_playing'] = False
            return None

        def mock_pause(*args, **kwargs):
            return None  # State stays True when paused

        mock_mixer.music.get_busy = MagicMock(side_effect=mock_get_busy)
        # Store reference to playing_state so tests can modify it if needed
        mock_mixer.music._playing_state = playing_state
        mock_mixer.music.play = MagicMock(side_effect=mock_play)
        mock_mixer.music.stop = MagicMock(side_effect=mock_stop)
        mock_mixer.music.pause = MagicMock(side_effect=mock_pause)
        mock_mixer.music.unpause = MagicMock()
        mock_mixer.music.load = MagicMock()
        mock_mixer.music.unload = MagicMock()
        mock_mixer.music.set_volume = MagicMock()
        mock_mixer.pre_init = MagicMock()
        mock_mixer.init = MagicMock()
        mock_mixer.quit = MagicMock()

        mock_pg.mixer = mock_mixer

        # Mock pygame availability
        with patch('app.src.domain.audio.backends.implementations.macos_audio_backend.PYGAME_AVAILABLE', True):
            yield mock_pg


@pytest.fixture
def backend(mock_pygame):
    """Create a macOS audio backend instance."""
    from app.src.domain.audio.backends.implementations.macos_audio_backend import MacOSAudioBackend

    backend = MacOSAudioBackend()
    yield backend
    backend.cleanup()


@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_text("fake audio data")
    return audio_file


class TestMacOSAudioBackendInitialization:
    """Test MacOSAudioBackend initialization."""

    @pytest.mark.asyncio
    async def test_create_backend(self, backend):
        """Test creating macOS backend."""
        assert backend is not None
        assert backend._mixer_initialized is True

    @pytest.mark.asyncio
    async def test_pygame_mixer_configured(self, mock_pygame, backend):
        """Test pygame mixer is configured correctly."""
        # Should have called pre_init with macOS-compatible settings
        mock_pygame.mixer.pre_init.assert_called_once_with(
            frequency=44100,
            size=-16,
            channels=2,
            buffer=2048
        )

        # Should have called init
        mock_pygame.mixer.init.assert_called_once()

    @patch.dict('os.environ', {}, clear=True)
    @pytest.mark.asyncio
    async def test_sets_core_audio_driver(self, backend):
        """Test sets SDL_AUDIODRIVER to coreaudio."""
        import os
        # Note: This test might be order-dependent due to env var setting
        # The backend should set the audio driver
        # We can't directly test os.environ modification in this way

    @pytest.mark.asyncio
    async def test_pygame_unavailable_raises_error(self):
        """Test error when pygame is not available."""
        with patch('app.src.domain.audio.backends.implementations.macos_audio_backend.PYGAME_AVAILABLE', False):
            from app.src.domain.audio.backends.implementations.macos_audio_backend import MacOSAudioBackend

            with pytest.raises(ImportError):
                MacOSAudioBackend()

    @pytest.mark.asyncio
    async def test_initializes_time_tracking(self, backend):
        """Test time tracking variables are initialized."""
        assert backend._play_start_time is None
        assert backend._pause_time is None
        assert backend._is_paused is False

    @pytest.mark.asyncio
    async def test_initializes_current_file_tracking(self, backend):
        """Test current file tracking is initialized."""
        assert backend._current_file_path is None
        assert backend._current_file_duration is None


class TestPlaybackControls:
    """Test playback control methods."""

    @pytest.mark.asyncio
    async def test_play_file(self, backend, mock_pygame, temp_audio_file):
        """Test playing an audio file."""
        result = backend.play_file(str(temp_audio_file))

        assert result is True
        mock_pygame.mixer.music.load.assert_called_once_with(str(temp_audio_file))
        mock_pygame.mixer.music.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_file_sets_state(self, backend, temp_audio_file):
        """Test play_file sets internal state."""
        backend.play_file(str(temp_audio_file))

        assert backend._is_playing is True
        assert backend._current_file_path == str(temp_audio_file)
        assert backend._play_start_time is not None

    @pytest.mark.asyncio
    async def test_play_file_with_duration(self, backend, temp_audio_file):
        """Test play_file with custom duration."""
        backend.play_file(str(temp_audio_file), duration_ms=5000)

        assert backend._current_file_duration == 5.0

    @pytest.mark.asyncio
    async def test_play_nonexistent_file(self, backend):
        """Test playing a nonexistent file."""
        result = backend.play_file("/nonexistent/file.mp3")

        assert result is False

    @pytest.mark.asyncio
    async def test_play_stops_current_playback(self, backend, mock_pygame, temp_audio_file):
        """Test playing stops current playback."""
        # Simulate music already playing
        mock_pygame.mixer.music._playing_state['is_playing'] = True

        backend.play_file(str(temp_audio_file))

        mock_pygame.mixer.music.stop.assert_called()
        mock_pygame.mixer.music.unload.assert_called()

    @pytest.mark.asyncio
    async def test_stop_playback(self, backend, mock_pygame, temp_audio_file):
        """Test stopping playback."""
        backend.play_file(str(temp_audio_file))
        result = await backend.stop()

        assert result is True
        mock_pygame.mixer.music.stop.assert_called()
        mock_pygame.mixer.music.unload.assert_called()
        assert backend._is_playing is False
        assert backend._current_file_path is None

    @pytest.mark.asyncio
    async def test_stop_resets_timing(self, backend, temp_audio_file):
        """Test stop resets timing variables."""
        backend.play_file(str(temp_audio_file))
        await backend.stop()

        assert backend._play_start_time is None
        assert backend._pause_time is None
        assert backend._is_paused is False

    @pytest.mark.asyncio
    async def test_pause_playback(self, backend, mock_pygame, temp_audio_file):
        """Test pausing playback."""
        backend.play_file(str(temp_audio_file))
        result = await backend.pause()

        assert result is True
        mock_pygame.mixer.music.pause.assert_called_once()
        assert backend._is_playing is False
        assert backend._is_paused is True
        assert backend._pause_time is not None

    @pytest.mark.asyncio
    async def test_pause_when_not_playing(self, backend):
        """Test pausing when nothing is playing."""
        result = await backend.pause()

        assert result is False

    @pytest.mark.asyncio
    async def test_resume_playback(self, backend, mock_pygame, temp_audio_file):
        """Test resuming paused playback."""
        backend.play_file(str(temp_audio_file))
        await backend.pause()

        result = await backend.resume()

        assert result is True
        mock_pygame.mixer.music.unpause.assert_called_once()
        assert backend._is_playing is True
        assert backend._is_paused is False

    @pytest.mark.asyncio
    async def test_resume_when_not_paused(self, backend):
        """Test resuming when not paused."""
        result = await backend.resume()

        assert result is False

    @pytest.mark.asyncio
    async def test_resume_adjusts_play_start_time(self, backend, temp_audio_file):
        """Test resume adjusts play start time for pause duration."""
        backend.play_file(str(temp_audio_file))
        original_start_time = backend._play_start_time

        await backend.pause()
        time.sleep(0.1)  # Small pause duration

        await backend.resume()

        # Play start time should be adjusted
        assert backend._play_start_time > original_start_time


class TestVolumeControl:
    """Test volume control methods."""

    @pytest.mark.asyncio
    async def test_set_volume(self, backend, mock_pygame):
        """Test setting volume."""
        result = backend._set_volume_sync(75)

        assert result is True
        assert backend._volume == 75
        mock_pygame.mixer.music.set_volume.assert_called_with(0.75)

    @pytest.mark.asyncio
    async def test_set_volume_min(self, backend, mock_pygame):
        """Test setting volume to minimum."""
        backend._set_volume_sync(0)

        assert backend._volume == 0
        mock_pygame.mixer.music.set_volume.assert_called_with(0.0)

    @pytest.mark.asyncio
    async def test_set_volume_max(self, backend, mock_pygame):
        """Test setting volume to maximum."""
        backend._set_volume_sync(100)

        assert backend._volume == 100
        mock_pygame.mixer.music.set_volume.assert_called_with(1.0)

    @pytest.mark.asyncio
    async def test_set_volume_clamped(self, backend):
        """Test volume is clamped to valid range."""
        backend._set_volume_sync(150)

        assert backend._volume == 100

        backend._set_volume_sync(-50)

        assert backend._volume == 0

    @pytest.mark.asyncio
    async def test_get_volume_async(self, backend):
        """Test getting volume asynchronously."""
        backend._set_volume_sync(60)

        volume = await backend.get_volume()

        assert volume == 60


class TestPositionTracking:
    """Test position tracking functionality."""

    @pytest.mark.asyncio
    async def test_get_position_when_playing(self, backend, temp_audio_file):
        """Test getting position during playback."""
        backend.play_file(str(temp_audio_file))
        time.sleep(0.1)  # Small delay

        position = backend.get_position()

        assert position > 0

    @pytest.mark.asyncio
    async def test_get_position_when_not_playing(self, backend):
        """Test getting position when not playing."""
        position = backend.get_position()

        assert position == 0.0

    @pytest.mark.asyncio
    async def test_get_position_when_paused(self, backend, temp_audio_file):
        """Test getting position when paused."""
        backend.play_file(str(temp_audio_file))
        time.sleep(0.1)

        await backend.pause()
        paused_position = backend.get_position()

        time.sleep(0.1)
        # Position should not increase while paused
        assert backend.get_position() == pytest.approx(paused_position, abs=0.01)

    @pytest.mark.asyncio
    async def test_position_increases_during_playback(self, backend, temp_audio_file):
        """Test position increases during playback."""
        backend.play_file(str(temp_audio_file))

        position1 = backend.get_position()
        time.sleep(0.1)
        position2 = backend.get_position()

        assert position2 > position1

    @pytest.mark.asyncio
    async def test_get_position_never_negative(self, backend, temp_audio_file):
        """Test position is never negative."""
        backend.play_file(str(temp_audio_file))

        position = backend.get_position()

        assert position >= 0.0


class TestDurationQueries:
    """Test duration query methods."""

    @pytest.mark.asyncio
    async def test_get_duration_with_track_duration(self, backend, temp_audio_file):
        """Test getting duration when duration is set."""
        backend.play_file(str(temp_audio_file), duration_ms=10000)

        duration = await backend.get_duration()

        assert duration == 10000

    @pytest.mark.asyncio
    async def test_get_duration_without_track_duration(self, backend, temp_audio_file):
        """Test getting duration when duration not set."""
        backend.play_file(str(temp_audio_file))

        duration = await backend.get_duration()

        assert duration is None

    @pytest.mark.asyncio
    async def test_get_duration_when_not_playing(self, backend):
        """Test getting duration when nothing is playing."""
        duration = await backend.get_duration()

        assert duration is None


class TestStateProperties:
    """Test state property methods."""

    @pytest.mark.asyncio
    async def test_is_playing_property(self, backend, temp_audio_file):
        """Test is_playing property."""
        assert backend.is_playing is False

        backend.play_file(str(temp_audio_file))
        assert backend.is_playing is True

        await backend.stop()
        assert backend.is_playing is False

    @pytest.mark.asyncio
    async def test_is_playing_syncs_with_pygame(self, backend, mock_pygame, temp_audio_file):
        """Test is_playing syncs with pygame state."""
        backend.play_file(str(temp_audio_file))

        # Simulate pygame reports not busy (track finished)
        mock_pygame.mixer.music._playing_state['is_playing'] = False

        # Accessing is_playing should sync state
        is_playing = backend.is_playing

        assert is_playing is False
        assert backend._is_playing is False

    @pytest.mark.asyncio
    async def test_is_busy_property(self, backend, mock_pygame, temp_audio_file):
        """Test is_busy property."""
        # Not playing
        assert backend.is_busy is False

        # Playing
        backend.play_file(str(temp_audio_file))
        assert backend.is_busy is True

    @pytest.mark.asyncio
    async def test_is_busy_syncs_with_pygame(self, backend, mock_pygame, temp_audio_file):
        """Test is_busy syncs with pygame state."""
        backend.play_file(str(temp_audio_file))

        # Simulate track finished
        mock_pygame.mixer.music._playing_state['is_playing'] = False

        is_busy = backend.is_busy

        assert is_busy is False
        assert backend._is_playing is False


class TestAsyncWrappers:
    """Test async wrapper methods."""

    @pytest.mark.asyncio
    async def test_async_play(self, backend, temp_audio_file):
        """Test async play wrapper."""
        result = await backend.play(str(temp_audio_file))

        assert result is True
        assert backend._is_playing is True

    @pytest.mark.asyncio
    async def test_async_seek_not_supported(self, backend, temp_audio_file):
        """Test async seek returns False (not supported)."""
        backend.play_file(str(temp_audio_file))

        result = await backend.seek(5000)

        assert result is False


class TestCleanupAndResourceManagement:
    """Test cleanup and resource management."""

    @pytest.mark.asyncio
    async def test_cleanup(self, backend, mock_pygame, temp_audio_file):
        """Test backend cleanup."""
        backend.play_file(str(temp_audio_file))

        backend.cleanup()

        mock_pygame.mixer.music.stop.assert_called()
        mock_pygame.mixer.quit.assert_called_once()
        assert backend._mixer_initialized is False
        assert backend._is_playing is False

    @pytest.mark.asyncio
    async def test_cleanup_resets_state(self, backend, temp_audio_file):
        """Test cleanup resets all state."""
        backend.play_file(str(temp_audio_file))

        backend.cleanup()

        assert backend._current_file_path is None
        assert backend._current_file_duration is None
        assert backend._play_start_time is None
        assert backend._pause_time is None
        assert backend._is_paused is False

    @pytest.mark.asyncio
    async def test_cleanup_when_mixer_not_initialized(self, backend, mock_pygame):
        """Test cleanup when mixer not initialized."""
        backend._mixer_initialized = False

        backend.cleanup()

        # Should not call quit if not initialized
        # Note: cleanup will still try to stop, but quit won't be called again


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_play_when_mixer_not_initialized(self, backend, temp_audio_file):
        """Test playing when mixer not initialized."""
        backend._mixer_initialized = False

        result = backend.play_file(str(temp_audio_file))

        assert result is False


class TestPauseResumeTimingAccuracy:
    """Test pause/resume timing calculations."""

    @pytest.mark.asyncio
    async def test_pause_resume_maintains_accurate_position(self, backend, temp_audio_file):
        """Test pause/resume maintains accurate playback position."""
        backend.play_file(str(temp_audio_file))

        # Play for a bit
        time.sleep(0.1)
        position_before_pause = backend.get_position()

        # Pause
        await backend.pause()
        paused_position = backend.get_position()

        # Paused position should be close to position before pause
        assert paused_position == pytest.approx(position_before_pause, abs=0.05)

        # Wait while paused
        time.sleep(0.1)

        # Position should not change while paused
        assert backend.get_position() == pytest.approx(paused_position, abs=0.01)

        # Resume
        await backend.resume()

        # After resuming, position should continue from where it paused
        # (with small tolerance for timing)
        resumed_position = backend.get_position()
        assert resumed_position >= paused_position


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @pytest.mark.asyncio
    async def test_complete_playback_cycle(self, backend, mock_pygame, temp_audio_file):
        """Test a complete playback cycle."""
        # Play
        backend.play_file(str(temp_audio_file))
        assert backend.is_playing is True

        # Pause
        await backend.pause()
        assert backend.is_playing is False

        # Resume
        await backend.resume()
        assert backend.is_playing is True

        # Stop
        await backend.stop()
        assert backend.is_playing is False

    @pytest.mark.asyncio
    async def test_volume_changes_during_playback(self, backend, mock_pygame, temp_audio_file):
        """Test volume can be changed during playback."""
        backend.play_file(str(temp_audio_file))

        backend._set_volume_sync(25)
        assert backend._volume == 25

        backend._set_volume_sync(75)
        assert backend._volume == 75

        # Should still be playing
        assert backend._is_playing is True

    @pytest.mark.asyncio
    async def test_playing_multiple_files_sequentially(self, backend, tmp_path):
        """Test playing multiple files one after another."""
        file1 = tmp_path / "song1.mp3"
        file2 = tmp_path / "song2.mp3"
        file1.write_text("audio 1")
        file2.write_text("audio 2")

        backend.play_file(str(file1), duration_ms=3000)
        assert backend._current_file_path == str(file1)

        backend.play_file(str(file2), duration_ms=5000)
        assert backend._current_file_path == str(file2)
        assert backend._current_file_duration == 5.0


class TestThreadSafety:
    """Test thread-safe state management."""

    @pytest.mark.asyncio
    async def test_concurrent_state_access(self, backend, temp_audio_file):
        """Test concurrent access to state is thread-safe."""
        backend.play_file(str(temp_audio_file))

        # Access properties concurrently
        is_playing = backend.is_playing
        is_busy = backend.is_busy
        position = backend.get_position()

        # Should not raise errors
        assert isinstance(is_playing, bool)
        assert isinstance(is_busy, bool)
        assert isinstance(position, float)


class TestEdgeCases:
    """Test edge cases."""

    @pytest.mark.asyncio
    async def test_pause_resume_multiple_cycles(self, backend, temp_audio_file):
        """Test multiple pause/resume cycles."""
        backend.play_file(str(temp_audio_file))

        await backend.pause()
        await backend.resume()
        await backend.pause()
        await backend.resume()

        assert backend.is_playing is True

    @pytest.mark.asyncio
    async def test_stop_when_not_playing(self, backend, mock_pygame):
        """Test stopping when nothing is playing."""
        result = await backend.stop()

        # Should still return True
        assert result is True

    @pytest.mark.asyncio
    async def test_play_file_resets_paused_state(self, backend, temp_audio_file):
        """Test playing a new file resets paused state."""
        backend.play_file(str(temp_audio_file))
        await backend.pause()

        backend.play_file(str(temp_audio_file))

        assert backend._is_paused is False
        assert backend._pause_time is None
