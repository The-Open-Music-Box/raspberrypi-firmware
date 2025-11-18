# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Tests for ButtonActionDispatcher."""

import pytest
from unittest.mock import Mock, AsyncMock
from app.src.application.services.button_action_application_service import ButtonActionDispatcher
from app.src.config.button_actions_config import ButtonActionConfig


@pytest.fixture
def mock_coordinator():
    """Create a mock PlaybackCoordinator."""
    coordinator = Mock()
    coordinator.set_volume = AsyncMock(return_value=True)
    coordinator.get_volume = Mock(return_value=50)
    coordinator.get_playback_status = Mock(return_value={
        "is_playing": True,
        "volume": 50,
    })
    coordinator.toggle_pause = Mock(return_value=True)
    coordinator.next_track = Mock(return_value=True)
    coordinator.previous_track = Mock(return_value=True)
    return coordinator


@pytest.fixture
def button_configs():
    """Create test button configurations matching DEFAULT_BUTTON_CONFIGS."""
    return [
        ButtonActionConfig(0, 23, "print_debug"),
        ButtonActionConfig(1, 20, "volume_down"),
        ButtonActionConfig(2, 16, "previous_track"),
        ButtonActionConfig(3, 26, "next_track"),
        ButtonActionConfig(4, 19, "volume_up"),
    ]


class TestButtonActionDispatcher:
    """Tests for ButtonActionDispatcher."""

    def test_dispatcher_initialization(self, button_configs, mock_coordinator):
        """Test dispatcher initializes correctly."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)

        assert dispatcher is not None
        assert len(dispatcher.get_configured_buttons()) == 5

    def test_dispatcher_builds_action_registry(self, button_configs, mock_coordinator):
        """Test that dispatcher builds action registry."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        status = dispatcher.get_status()

        assert "total_actions" in status
        assert status["total_actions"] >= 9  # All our defined actions

    def test_dispatcher_maps_buttons_to_actions(self, button_configs, mock_coordinator):
        """Test that dispatcher maps buttons to actions correctly."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        status = dispatcher.get_status()

        assert "button_mappings" in status
        assert status["button_mappings"][0] == "print_debug"
        assert status["button_mappings"][1] == "volume_down"
        assert status["button_mappings"][2] == "previous_track"
        assert status["button_mappings"][3] == "next_track"
        assert status["button_mappings"][4] == "volume_up"

    @pytest.mark.asyncio
    async def test_dispatch_print_debug_action(self, button_configs, mock_coordinator):
        """Test dispatching print debug action (button 0)."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        result = await dispatcher.dispatch(0)

        assert result is True
        mock_coordinator.get_playback_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_volume_down_action(self, button_configs, mock_coordinator):
        """Test dispatching volume down action (button 1)."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        result = await dispatcher.dispatch(1)

        assert result is True
        mock_coordinator.set_volume.assert_called_once_with(45)  # 50 - 5

    @pytest.mark.asyncio
    async def test_dispatch_previous_track_action(self, button_configs, mock_coordinator):
        """Test dispatching previous track action (button 2)."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        result = await dispatcher.dispatch(2)

        assert result is True
        mock_coordinator.previous_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_next_track_action(self, button_configs, mock_coordinator):
        """Test dispatching next track action (button 3)."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        result = await dispatcher.dispatch(3)

        assert result is True
        mock_coordinator.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_volume_up_action(self, button_configs, mock_coordinator):
        """Test dispatching volume up action (button 4)."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        result = await dispatcher.dispatch(4)

        assert result is True
        mock_coordinator.set_volume.assert_called_once_with(55)  # 50 + 5

    @pytest.mark.asyncio
    async def test_dispatch_unmapped_button(self, button_configs, mock_coordinator):
        """Test dispatching unmapped button returns False."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        result = await dispatcher.dispatch(99)

        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_with_disabled_button(self, mock_coordinator):
        """Test that disabled buttons are not mapped."""
        configs = [
            ButtonActionConfig(0, 23, "play_pause", enabled=False),
            ButtonActionConfig(1, 20, "next_track", enabled=True),
        ]

        dispatcher = ButtonActionDispatcher(configs, mock_coordinator)
        configured = dispatcher.get_configured_buttons()

        # Only button 1 should be configured
        assert 0 not in configured
        assert 1 in configured

    @pytest.mark.asyncio
    async def test_dispatch_with_unknown_action(self, mock_coordinator):
        """Test that unknown actions are ignored."""
        configs = [
            ButtonActionConfig(0, 23, "unknown_action"),  # Will be ignored
            ButtonActionConfig(1, 20, "next_track"),
        ]

        dispatcher = ButtonActionDispatcher(configs, mock_coordinator)
        configured = dispatcher.get_configured_buttons()

        # Only button 1 should be configured
        assert 0 not in configured
        assert 1 in configured

    def test_get_button_action(self, button_configs, mock_coordinator):
        """Test getting action for a button."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        action = dispatcher.get_button_action(0)

        assert action is not None
        assert action.name == "print_debug"

    def test_get_button_action_nonexistent(self, button_configs, mock_coordinator):
        """Test getting action for nonexistent button returns None."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        action = dispatcher.get_button_action(99)

        assert action is None

    def test_get_configured_buttons(self, button_configs, mock_coordinator):
        """Test getting list of configured buttons."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        configured = dispatcher.get_configured_buttons()

        assert sorted(configured) == [0, 1, 2, 3, 4]

    def test_get_status(self, button_configs, mock_coordinator):
        """Test getting dispatcher status."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        status = dispatcher.get_status()

        assert "total_actions" in status
        assert "configured_buttons" in status
        assert "available_actions" in status
        assert "button_mappings" in status
        assert status["configured_buttons"] == 5

    @pytest.mark.asyncio
    async def test_dispatch_sync_success(self, button_configs, mock_coordinator):
        """Test synchronous dispatch wrapper succeeds."""
        import asyncio
        loop = asyncio.get_running_loop()

        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator, main_loop=loop)

        # dispatch_sync should execute without errors
        result = dispatcher.dispatch_sync(3)  # next_track

        # Give async task time to execute
        await asyncio.sleep(0.01)

        assert result is True
        mock_coordinator.next_track.assert_called_once()

    def test_dispatch_sync_unmapped_button(self, button_configs, mock_coordinator):
        """Test synchronous dispatch with unmapped button."""
        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)

        result = dispatcher.dispatch_sync(99)

        assert result is False

    @pytest.mark.asyncio
    async def test_dispatch_action_execution_failure(self, button_configs, mock_coordinator):
        """Test dispatch handles action execution failure gracefully."""
        # Make next_track fail
        mock_coordinator.next_track = Mock(return_value=False)

        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        result = await dispatcher.dispatch(3)

        assert result is False
        mock_coordinator.next_track.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_action_raises_exception(self, button_configs, mock_coordinator):
        """Test dispatch handles exceptions from actions gracefully."""
        # Make next_track raise an exception
        mock_coordinator.next_track = Mock(side_effect=Exception("Hardware failure"))

        dispatcher = ButtonActionDispatcher(button_configs, mock_coordinator)
        result = await dispatcher.dispatch(3)

        assert result is False
        mock_coordinator.next_track.assert_called_once()
