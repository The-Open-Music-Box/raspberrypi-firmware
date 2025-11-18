# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for button actions (domain layer)."""

import pytest
from unittest.mock import Mock, AsyncMock
from app.src.domain.actions.button_actions import (
    PlayAction,
    PauseAction,
    PlayPauseAction,
    StopAction,
    NextTrackAction,
    PreviousTrackAction,
    VolumeUpAction,
    VolumeDownAction,
    PrintDebugAction,
)


@pytest.fixture
def mock_coordinator():
    """Create a mock PlaybackCoordinator."""
    coordinator = Mock()
    # Setup async methods
    coordinator.set_volume = AsyncMock(return_value=True)
    coordinator.get_volume = Mock(return_value=50)
    coordinator.get_playback_status = Mock(return_value={
        "is_playing": True,
        "is_paused": False,
        "volume": 50,
        "position_ms": 1000,
        "duration_ms": 5000,
        "active_playlist_title": "Test Playlist",
        "active_track": {"title": "Test Track"},
        "track_index": 1,
        "track_count": 10,
        "repeat_mode": "none",
        "shuffle_enabled": False,
        "auto_advance_enabled": True,
    })
    # Setup sync methods
    coordinator.play = Mock(return_value=True)
    coordinator.pause = Mock(return_value=True)
    coordinator.toggle_pause = Mock(return_value=True)
    coordinator.stop = Mock(return_value=True)
    coordinator.next_track = Mock(return_value=True)
    coordinator.previous_track = Mock(return_value=True)

    return coordinator


class TestPlayAction:
    """Tests for PlayAction."""

    @pytest.mark.asyncio
    async def test_play_action_name(self):
        """Test that play action has correct name."""
        action = PlayAction()
        assert action.name == "play"

    @pytest.mark.asyncio
    async def test_play_action_execute(self, mock_coordinator):
        """Test that play action calls coordinator.play()."""
        action = PlayAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.play.assert_called_once()

    @pytest.mark.asyncio
    async def test_play_action_execute_failure(self, mock_coordinator):
        """Test play action when coordinator returns False."""
        mock_coordinator.play.return_value = False
        action = PlayAction()
        result = await action.execute(mock_coordinator)

        assert result is False


class TestPauseAction:
    """Tests for PauseAction."""

    @pytest.mark.asyncio
    async def test_pause_action_name(self):
        """Test that pause action has correct name."""
        action = PauseAction()
        assert action.name == "pause"

    @pytest.mark.asyncio
    async def test_pause_action_execute(self, mock_coordinator):
        """Test that pause action calls coordinator.pause()."""
        action = PauseAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.pause.assert_called_once()


class TestPlayPauseAction:
    """Tests for PlayPauseAction."""

    @pytest.mark.asyncio
    async def test_play_pause_action_name(self):
        """Test that play/pause action has correct name."""
        action = PlayPauseAction()
        assert action.name == "play_pause"

    @pytest.mark.asyncio
    async def test_play_pause_action_execute(self, mock_coordinator):
        """Test that play/pause action calls coordinator.toggle_pause()."""
        action = PlayPauseAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.toggle_pause.assert_called_once()


class TestStopAction:
    """Tests for StopAction."""

    @pytest.mark.asyncio
    async def test_stop_action_name(self):
        """Test that stop action has correct name."""
        action = StopAction()
        assert action.name == "stop"

    @pytest.mark.asyncio
    async def test_stop_action_execute(self, mock_coordinator):
        """Test that stop action calls coordinator.stop()."""
        action = StopAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.stop.assert_called_once()


class TestNextTrackAction:
    """Tests for NextTrackAction."""

    @pytest.mark.asyncio
    async def test_next_track_action_name(self):
        """Test that next track action has correct name."""
        action = NextTrackAction()
        assert action.name == "next_track"

    @pytest.mark.asyncio
    async def test_next_track_action_execute(self, mock_coordinator):
        """Test that next track action calls coordinator.next_track()."""
        action = NextTrackAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.next_track.assert_called_once()


class TestPreviousTrackAction:
    """Tests for PreviousTrackAction."""

    @pytest.mark.asyncio
    async def test_previous_track_action_name(self):
        """Test that previous track action has correct name."""
        action = PreviousTrackAction()
        assert action.name == "previous_track"

    @pytest.mark.asyncio
    async def test_previous_track_action_execute(self, mock_coordinator):
        """Test that previous track action calls coordinator.previous_track()."""
        action = PreviousTrackAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.previous_track.assert_called_once()


class TestVolumeUpAction:
    """Tests for VolumeUpAction."""

    @pytest.mark.asyncio
    async def test_volume_up_action_name(self):
        """Test that volume up action has correct name."""
        action = VolumeUpAction()
        assert action.name == "volume_up"

    @pytest.mark.asyncio
    async def test_volume_up_action_execute(self, mock_coordinator):
        """Test that volume up increases volume by 5%."""
        mock_coordinator.get_volume.return_value = 50
        action = VolumeUpAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.set_volume.assert_called_once_with(55)

    @pytest.mark.asyncio
    async def test_volume_up_at_maximum(self, mock_coordinator):
        """Test that volume up caps at 100%."""
        mock_coordinator.get_volume.return_value = 99
        action = VolumeUpAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.set_volume.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_volume_up_already_at_maximum(self, mock_coordinator):
        """Test that volume up when already at 100% returns True."""
        mock_coordinator.get_volume.return_value = 100
        action = VolumeUpAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        # Should not call set_volume since already at max
        mock_coordinator.set_volume.assert_not_called()


class TestVolumeDownAction:
    """Tests for VolumeDownAction."""

    @pytest.mark.asyncio
    async def test_volume_down_action_name(self):
        """Test that volume down action has correct name."""
        action = VolumeDownAction()
        assert action.name == "volume_down"

    @pytest.mark.asyncio
    async def test_volume_down_action_execute(self, mock_coordinator):
        """Test that volume down decreases volume by 5%."""
        mock_coordinator.get_volume.return_value = 50
        action = VolumeDownAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.set_volume.assert_called_once_with(45)

    @pytest.mark.asyncio
    async def test_volume_down_at_minimum(self, mock_coordinator):
        """Test that volume down caps at 0%."""
        mock_coordinator.get_volume.return_value = 3
        action = VolumeDownAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.set_volume.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_volume_down_already_at_minimum(self, mock_coordinator):
        """Test that volume down when already at 0% returns True."""
        mock_coordinator.get_volume.return_value = 0
        action = VolumeDownAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        # Should not call set_volume since already at min
        mock_coordinator.set_volume.assert_not_called()


class TestPrintDebugAction:
    """Tests for PrintDebugAction."""

    @pytest.mark.asyncio
    async def test_print_debug_action_name(self):
        """Test that print debug action has correct name."""
        action = PrintDebugAction()
        assert action.name == "print_debug"

    @pytest.mark.asyncio
    async def test_print_debug_action_execute(self, mock_coordinator):
        """Test that print debug action gets playback status."""
        action = PrintDebugAction()
        result = await action.execute(mock_coordinator)

        assert result is True
        mock_coordinator.get_playback_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_print_debug_action_handles_exceptions(self, mock_coordinator):
        """Test that print debug action handles exceptions gracefully."""
        mock_coordinator.get_playback_status.side_effect = Exception("Test error")
        action = PrintDebugAction()
        result = await action.execute(mock_coordinator)

        assert result is False
