"""Tests for PlaybackStateManager class."""

import pytest
import time
from unittest.mock import patch
from app.src.domain.services.playback_state_manager import PlaybackStateManager
from app.src.domain.protocols.state_manager_protocol import PlaybackState


class TestPlaybackStateManager:
    """Test suite for PlaybackStateManager class."""

    @pytest.fixture
    def state_manager(self):
        """Create PlaybackStateManager instance."""
        return PlaybackStateManager()

    def test_init(self, state_manager):
        """Test PlaybackStateManager initialization."""
        assert state_manager.get_current_state() == PlaybackState.STOPPED
        assert state_manager.get_state_dict()["track"] == {}
        assert state_manager.get_state_dict()["playlist"] == {}
        assert state_manager.get_position_seconds() == 0.0
        assert state_manager.get_volume() == 50
        assert state_manager.get_last_error() is None
        assert state_manager.get_current_playlist() is None
        assert state_manager.get_current_track_number() is None

    def test_set_and_get_state(self, state_manager):
        """Test setting and getting playback state."""
        with patch('time.time', return_value=1234567890.0):
            state_manager.set_state(PlaybackState.PLAYING)

        assert state_manager.get_current_state() == PlaybackState.PLAYING
        assert state_manager.get_last_updated() == 1234567890.0

    def test_set_same_state_no_update(self, state_manager):
        """Test setting same state doesn't update timestamp."""
        initial_time = state_manager.get_last_updated()

        with patch('time.time', return_value=9999999999.0):
            # Set same state (STOPPED)
            state_manager.set_state(PlaybackState.STOPPED)

        # Timestamp should not change
        assert state_manager.get_last_updated() == initial_time

    def test_get_state_dict(self, state_manager):
        """Test getting complete state dictionary."""
        # Set up some state
        track_info = {"id": "track_123", "title": "Test Track"}
        playlist_info = {"id": "playlist_456", "title": "Test Playlist"}

        state_manager.update_track_info(track_info)
        state_manager.update_playlist_info(playlist_info)
        state_manager.update_position(120.5)
        state_manager.update_volume(75)
        state_manager.set_error("Test error")

        state_dict = state_manager.get_state_dict()

        assert state_dict["state"] == PlaybackState.ERROR.value
        assert state_dict["track"] == track_info
        assert state_dict["playlist"] == playlist_info
        assert state_dict["position"] == 120.5
        assert state_dict["volume"] == 75
        assert state_dict["error"] == "Test error"
        assert "last_updated" in state_dict
        assert "current_playlist" in state_dict
        assert "current_track_number" in state_dict

    def test_update_track_info(self, state_manager):
        """Test updating track information."""
        track_info = {"id": "track_789", "title": "New Track", "artist": "Test Artist"}

        with patch('time.time', return_value=1234567890.0):
            state_manager.update_track_info(track_info)

        state_dict = state_manager.get_state_dict()
        assert state_dict["track"] == track_info
        assert state_manager.get_last_updated() == 1234567890.0

    def test_update_track_info_creates_copy(self, state_manager):
        """Test that update_track_info creates a copy of the input."""
        track_info = {"id": "track_123", "title": "Original Title"}
        state_manager.update_track_info(track_info)

        # Modify original dict
        track_info["title"] = "Modified Title"

        # State should not be affected
        state_dict = state_manager.get_state_dict()
        assert state_dict["track"]["title"] == "Original Title"

    def test_update_playlist_info(self, state_manager):
        """Test updating playlist information."""
        playlist_info = {"id": "playlist_123", "title": "New Playlist", "track_count": 10}

        with patch('time.time', return_value=1234567890.0):
            state_manager.update_playlist_info(playlist_info)

        state_dict = state_manager.get_state_dict()
        assert state_dict["playlist"] == playlist_info
        assert state_manager.get_last_updated() == 1234567890.0

    def test_update_playlist_info_creates_copy(self, state_manager):
        """Test that update_playlist_info creates a copy of the input."""
        playlist_info = {"id": "playlist_123", "title": "Original Title"}
        state_manager.update_playlist_info(playlist_info)

        # Modify original dict
        playlist_info["title"] = "Modified Title"

        # State should not be affected
        state_dict = state_manager.get_state_dict()
        assert state_dict["playlist"]["title"] == "Original Title"

    def test_update_position(self, state_manager):
        """Test updating playback position."""
        state_manager.update_position(45.7)
        assert state_manager.get_position_seconds() == 45.7

        # Test negative position clamping
        state_manager.update_position(-10.0)
        assert state_manager.get_position_seconds() == 0.0

    def test_update_volume(self, state_manager):
        """Test updating volume level."""
        with patch('time.time', return_value=1234567890.0):
            state_manager.update_volume(80)

        assert state_manager.get_volume() == 80
        assert state_manager.get_last_updated() == 1234567890.0

        # Test volume clamping
        state_manager.update_volume(150)  # Above max
        assert state_manager.get_volume() == 100

        state_manager.update_volume(-10)  # Below min
        assert state_manager.get_volume() == 0

    def test_set_error(self, state_manager):
        """Test setting error state."""
        with patch('time.time', return_value=1234567890.0):
            state_manager.set_error("Test error message")

        assert state_manager.get_last_error() == "Test error message"
        assert state_manager.get_current_state() == PlaybackState.ERROR
        assert state_manager.get_last_updated() == 1234567890.0
        assert state_manager.is_error()

    def test_clear_error(self, state_manager):
        """Test clearing error state."""
        # Set error first
        state_manager.set_error("Test error")
        assert state_manager.get_last_error() == "Test error"
        assert state_manager.get_current_state() == PlaybackState.ERROR

        with patch('time.time', return_value=1234567890.0):
            state_manager.clear_error()

        assert state_manager.get_last_error() is None
        assert state_manager.get_current_state() == PlaybackState.STOPPED
        assert state_manager.get_last_updated() == 1234567890.0
        assert not state_manager.is_error()

    def test_clear_error_when_no_error(self, state_manager):
        """Test clearing error when no error exists."""
        initial_time = state_manager.get_last_updated()

        with patch('time.time', return_value=9999999999.0):
            state_manager.clear_error()

        # Should not update timestamp when no error to clear
        assert state_manager.get_last_updated() == initial_time

    def test_clear_error_when_not_in_error_state(self, state_manager):
        """Test clearing error when state is not ERROR."""
        state_manager.set_state(PlaybackState.PLAYING)
        state_manager.set_error("Test error")
        state_manager.set_state(PlaybackState.PAUSED)  # Change state away from ERROR

        state_manager.clear_error()

        # Should clear error but not change state from PAUSED
        assert state_manager.get_last_error() is None
        assert state_manager.get_current_state() == PlaybackState.PAUSED

    def test_get_and_set_current_playlist(self, state_manager):
        """Test current playlist management."""
        playlist = {"id": "playlist_456", "title": "Current Playlist"}

        with patch('time.time', return_value=1234567890.0):
            state_manager.set_current_playlist(playlist)

        assert state_manager.get_current_playlist() == playlist
        assert state_manager.get_last_updated() == 1234567890.0

        # Test setting to None
        state_manager.set_current_playlist(None)
        assert state_manager.get_current_playlist() is None

    def test_get_and_set_current_track_number(self, state_manager):
        """Test current track number management."""
        with patch('time.time', return_value=1234567890.0):
            state_manager.set_current_track_number(3)

        assert state_manager.get_current_track_number() == 3
        assert state_manager.get_last_updated() == 1234567890.0

        # Test setting to None
        state_manager.set_current_track_number(None)
        assert state_manager.get_current_track_number() is None

    def test_is_state_methods(self, state_manager):
        """Test state checking convenience methods."""
        # Initially stopped
        assert state_manager.is_stopped()
        assert not state_manager.is_playing()
        assert not state_manager.is_paused()
        assert not state_manager.is_error()

        # Set to playing
        state_manager.set_state(PlaybackState.PLAYING)
        assert not state_manager.is_stopped()
        assert state_manager.is_playing()
        assert not state_manager.is_paused()
        assert not state_manager.is_error()

        # Set to paused
        state_manager.set_state(PlaybackState.PAUSED)
        assert not state_manager.is_stopped()
        assert not state_manager.is_playing()
        assert state_manager.is_paused()
        assert not state_manager.is_error()

        # Set to error
        state_manager.set_state(PlaybackState.ERROR)
        assert not state_manager.is_stopped()
        assert not state_manager.is_playing()
        assert not state_manager.is_paused()
        assert state_manager.is_error()

    def test_reset_state(self, state_manager):
        """Test state reset functionality."""
        # Set up complex state
        state_manager.set_state(PlaybackState.PLAYING)
        state_manager.update_track_info({"id": "track_123", "title": "Test Track"})
        state_manager.update_playlist_info({"id": "playlist_456", "title": "Test Playlist"})
        state_manager.update_position(120.5)
        state_manager.update_volume(75)
        state_manager.set_error("Test error")
        state_manager.set_current_playlist({"id": "current_playlist"})
        state_manager.set_current_track_number(5)

        with patch('time.time', return_value=1234567890.0):
            state_manager.reset_state()

        # Verify everything is reset
        assert state_manager.get_current_state() == PlaybackState.STOPPED
        assert state_manager.get_state_dict()["track"] == {}
        assert state_manager.get_state_dict()["playlist"] == {}
        assert state_manager.get_position_seconds() == 0.0
        assert state_manager.get_volume() == 50
        assert state_manager.get_last_error() is None
        assert state_manager.get_current_playlist() is None
        assert state_manager.get_current_track_number() is None
        assert state_manager.get_last_updated() == 1234567890.0