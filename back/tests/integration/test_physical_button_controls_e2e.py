# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Integration tests for physical button controls end-to-end flow.

Tests the complete button press → action dispatch → playback change flow.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from app.src.application.services.button_action_application_service import ButtonActionDispatcher
from app.src.config.button_actions_config import ButtonActionConfig, DEFAULT_BUTTON_CONFIGS


@pytest.fixture
def mock_playback_coordinator():
    """Create a mock PlaybackCoordinator that implements the protocol."""
    coordinator = Mock()

    # Implement PlaybackCoordinatorProtocol methods
    coordinator.play = Mock(return_value=True)
    coordinator.pause = Mock(return_value=True)
    coordinator.stop = Mock(return_value=True)
    coordinator.toggle_pause = Mock(return_value=True)
    coordinator.next_track = Mock(return_value=True)
    coordinator.previous_track = Mock(return_value=True)
    coordinator.get_volume = Mock(return_value=50)
    coordinator.set_volume = AsyncMock(return_value=True)
    coordinator.get_playback_status = Mock(return_value={
        "is_playing": True,
        "is_paused": False,
        "volume": 50,
        "position_ms": 5000,
        "duration_ms": 180000,
        "active_playlist_title": "Test Playlist",
        "track_index": 0,
        "track_count": 3,
        "active_track": {"title": "Test Track", "duration": 180},
        "repeat_mode": "none",
        "shuffle_enabled": False,
        "auto_advance_enabled": True,
    })

    return coordinator


@pytest.fixture
def button_dispatcher(mock_playback_coordinator):
    """Create a ButtonActionDispatcher with mock coordinator."""
    return ButtonActionDispatcher(DEFAULT_BUTTON_CONFIGS, mock_playback_coordinator)


@pytest.mark.integration
class TestPhysicalButtonControlsE2E:
    """Integration tests for complete button control flow."""

    @pytest.mark.asyncio
    async def test_volume_actions_with_custom_config(self, mock_playback_coordinator):
        """Test volume actions with custom button configuration."""
        # Create custom config with volume buttons
        volume_configs = [
            ButtonActionConfig(0, 23, "volume_up"),
            ButtonActionConfig(1, 27, "volume_down"),
        ]

        volume_dispatcher = ButtonActionDispatcher(volume_configs, mock_playback_coordinator)

        # Test volume up
        mock_playback_coordinator.get_volume = Mock(return_value=50)
        result = await volume_dispatcher.dispatch(0)
        assert result is True
        mock_playback_coordinator.set_volume.assert_called_once_with(55)  # 50 + 5

        # Test volume down
        mock_playback_coordinator.reset_mock()
        mock_playback_coordinator.get_volume = Mock(return_value=50)
        mock_playback_coordinator.set_volume = AsyncMock(return_value=True)
        result = await volume_dispatcher.dispatch(1)
        assert result is True
        mock_playback_coordinator.set_volume.assert_called_once_with(45)  # 50 - 5

    @pytest.mark.asyncio
    async def test_volume_boundaries_are_respected(self, mock_playback_coordinator):
        """Test that volume stays within 0-100% bounds."""
        # Create custom config with volume buttons
        volume_configs = [
            ButtonActionConfig(0, 23, "volume_up"),
            ButtonActionConfig(1, 27, "volume_down"),
        ]

        volume_dispatcher = ButtonActionDispatcher(volume_configs, mock_playback_coordinator)

        # Test upper boundary
        mock_playback_coordinator.get_volume = Mock(return_value=98)
        result = await volume_dispatcher.dispatch(0)  # volume_up
        assert result is True
        mock_playback_coordinator.set_volume.assert_called_with(100)  # Clamped to 100

        # Test lower boundary
        mock_playback_coordinator.reset_mock()
        mock_playback_coordinator.get_volume = Mock(return_value=3)
        mock_playback_coordinator.set_volume = AsyncMock(return_value=True)
        result = await volume_dispatcher.dispatch(1)  # volume_down
        assert result is True
        mock_playback_coordinator.set_volume.assert_called_with(0)  # Clamped to 0

    @pytest.mark.asyncio
    async def test_next_track_button_triggers_navigation(self, button_dispatcher, mock_playback_coordinator):
        """Test that pressing next track button navigates to next track."""
        # Button 4 is next_track in DEFAULT_BUTTON_CONFIGS
        result = await button_dispatcher.dispatch(4)

        assert result is True
        mock_playback_coordinator.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_previous_track_button_triggers_navigation(self, button_dispatcher, mock_playback_coordinator):
        """Test that pressing previous track button navigates to previous track."""
        # Button 1 is previous_track in DEFAULT_BUTTON_CONFIGS
        result = await button_dispatcher.dispatch(1)

        assert result is True
        mock_playback_coordinator.previous_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_print_debug_button_logs_status(self, button_dispatcher, mock_playback_coordinator):
        """Test that pressing print debug button logs playback status."""
        # Button 0 is print_debug in DEFAULT_BUTTON_CONFIGS
        result = await button_dispatcher.dispatch(0)

        assert result is True
        # Debug action should call get_playback_status
        mock_playback_coordinator.get_playback_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_button_presses_in_sequence(self, button_dispatcher, mock_playback_coordinator):
        """Test multiple button presses work correctly in sequence."""
        # Press next track twice
        await button_dispatcher.dispatch(4)  # next_track
        assert mock_playback_coordinator.next_track.call_count == 1

        await button_dispatcher.dispatch(4)  # next_track
        assert mock_playback_coordinator.next_track.call_count == 2

        # Press previous track once
        await button_dispatcher.dispatch(1)  # previous_track
        assert mock_playback_coordinator.previous_track.call_count == 1

    @pytest.mark.asyncio
    async def test_button_press_with_coordinator_failure(self, button_dispatcher, mock_playback_coordinator):
        """Test button press when coordinator operation fails."""
        # Make next_track fail
        mock_playback_coordinator.next_track = Mock(return_value=False)

        # Try to press next track (button 4)
        result = await button_dispatcher.dispatch(4)

        # Should return False since operation failed
        assert result is False

    @pytest.mark.asyncio
    async def test_unmapped_button_returns_false(self, button_dispatcher):
        """Test that pressing an unmapped button returns False."""
        result = await button_dispatcher.dispatch(99)

        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_sync_wrapper_works(self, button_dispatcher, mock_playback_coordinator):
        """Test that synchronous dispatch wrapper works for GPIO callbacks."""
        import asyncio

        # Set main event loop for dispatcher
        button_dispatcher._main_loop = asyncio.get_running_loop()

        # This simulates a GPIO callback calling dispatch_sync for next track
        result = button_dispatcher.dispatch_sync(4)

        # Give async task time to execute
        await asyncio.sleep(0.01)

        assert result is True
        mock_playback_coordinator.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_button_configuration(self, mock_playback_coordinator):
        """Test that custom button configurations work correctly."""
        # Create custom config: button 0 → next_track
        custom_configs = [
            ButtonActionConfig(0, 23, "next_track"),
        ]

        custom_dispatcher = ButtonActionDispatcher(custom_configs, mock_playback_coordinator)

        # Button 0 should trigger next_track
        result = await custom_dispatcher.dispatch(0)

        assert result is True
        mock_playback_coordinator.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_disabled_button_is_not_triggered(self, mock_playback_coordinator):
        """Test that disabled buttons are ignored."""
        disabled_configs = [
            ButtonActionConfig(0, 23, "next_track", enabled=False),
            ButtonActionConfig(1, 20, "volume_up", enabled=True),
        ]

        dispatcher = ButtonActionDispatcher(disabled_configs, mock_playback_coordinator)

        # Button 0 is disabled, should not be in configured buttons
        configured = dispatcher.get_configured_buttons()
        assert 0 not in configured
        assert 1 in configured

        # Trying to dispatch button 0 should fail
        result = await dispatcher.dispatch(0)
        assert result is False
