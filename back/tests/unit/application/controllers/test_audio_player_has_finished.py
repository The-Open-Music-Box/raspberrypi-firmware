"""Tests for AudioPlayer.has_finished() state synchronization fix.

This test verifies the critical fix for the playlist auto-advance bug where
AudioPlayer.has_finished() was not correctly detecting track completion due to
state synchronization issues between AudioPlayer and the backend.
"""

import pytest
from unittest.mock import Mock, PropertyMock

from app.src.application.controllers.audio_player_controller import AudioPlayer, PlaybackState


class TestAudioPlayerHasFinished:
    """Test suite for AudioPlayer.has_finished() method."""

    @pytest.fixture
    def mock_backend_busy(self):
        """Create mock backend that reports as busy (track still playing)."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend._volume = 50

        # Use PropertyMock for is_busy
        type(backend).is_busy = PropertyMock(return_value=True)

        return backend

    @pytest.fixture
    def mock_backend_finished(self):
        """Create mock backend that reports as not busy (track finished)."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend._volume = 50

        # Use PropertyMock for is_busy - track has finished
        type(backend).is_busy = PropertyMock(return_value=False)

        return backend

    @pytest.fixture
    def audio_player_busy(self, mock_backend_busy):
        """Create AudioPlayer with backend that's busy."""
        player = AudioPlayer(mock_backend_busy)
        # Simulate that a track is playing
        player._state = PlaybackState.PLAYING
        player._current_file = "/path/to/track.mp3"
        return player

    @pytest.fixture
    def audio_player_finished(self, mock_backend_finished):
        """Create AudioPlayer with backend that has finished."""
        player = AudioPlayer(mock_backend_finished)
        # Simulate that a track is playing
        player._state = PlaybackState.PLAYING
        player._current_file = "/path/to/track.mp3"
        return player

    def test_has_finished_returns_false_when_backend_busy(self, audio_player_busy):
        """Test that has_finished returns False when backend is still busy."""
        assert audio_player_busy.has_finished() is False
        # State should still be PLAYING
        assert audio_player_busy._state == PlaybackState.PLAYING

    def test_has_finished_returns_true_and_updates_state_when_backend_finished(
        self, audio_player_finished
    ):
        """Test that has_finished returns True and updates state when backend finishes.

        This is the critical fix: when the backend reports not busy, has_finished
        should return True AND update the internal state to STOPPED.
        """
        # Initially playing
        assert audio_player_finished._state == PlaybackState.PLAYING

        # Check if finished
        result = audio_player_finished.has_finished()

        # Should return True
        assert result is True

        # CRITICAL: State should be updated to STOPPED
        assert audio_player_finished._state == PlaybackState.STOPPED

    def test_has_finished_returns_false_when_not_playing(self, mock_backend_busy):
        """Test that has_finished returns False when player is not in PLAYING state."""
        player = AudioPlayer(mock_backend_busy)
        player._state = PlaybackState.STOPPED

        assert player.has_finished() is False

    def test_has_finished_returns_false_when_paused(self, mock_backend_busy):
        """Test that has_finished returns False when player is paused."""
        player = AudioPlayer(mock_backend_busy)
        player._state = PlaybackState.PAUSED
        player._current_file = "/path/to/track.mp3"

        assert player.has_finished() is False

    def test_has_finished_uses_position_fallback_when_is_busy_not_available(self):
        """Test fallback to position/duration comparison when is_busy not available."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend._volume = 50
        # Don't set is_busy attribute
        del backend.is_busy

        player = AudioPlayer(backend)
        player._state = PlaybackState.PLAYING
        player._current_file = "/path/to/track.mp3"

        # Mock get_position and get_duration for fallback logic
        player.get_position = Mock(return_value=180.5)  # 180.5 seconds
        player.get_duration = Mock(return_value=180.0)   # 180 seconds

        # Should return True because position >= duration
        result = player.has_finished()
        assert result is True

        # State should be updated to STOPPED
        assert player._state == PlaybackState.STOPPED

    def test_has_finished_fallback_returns_false_when_position_less_than_duration(self):
        """Test fallback returns False when position < duration."""
        backend = Mock()
        backend.play_file = Mock(return_value=True)
        backend._volume = 50
        del backend.is_busy

        player = AudioPlayer(backend)
        player._state = PlaybackState.PLAYING
        player._current_file = "/path/to/track.mp3"

        # Mock get_position and get_duration
        player.get_position = Mock(return_value=90.0)  # 90 seconds
        player.get_duration = Mock(return_value=180.0)  # 180 seconds

        # Should return False because track still has time left
        assert player.has_finished() is False

        # State should remain PLAYING
        assert player._state == PlaybackState.PLAYING
