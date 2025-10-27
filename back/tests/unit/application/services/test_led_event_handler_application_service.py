# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Comprehensive tests for LED Event Handler Application Service.

Tests all event handler methods for:
- System lifecycle events (startup, ready, shutdown)
- NFC events (scanning, detection, association, errors)
- Playback state events (playing, paused, stopped)
- Error events (boot errors, playback errors, crashes)
- Volume events
- Manual control methods
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, call
import logging

from app.src.application.services.led_event_handler_application_service import LEDEventHandler
from app.src.domain.models.led import LEDState
from app.src.common.data_models import PlaybackState


# MARK: - Fixtures

@pytest.fixture
def mock_led_manager():
    """Create mock LED state manager."""
    manager = MagicMock()
    manager.set_state = AsyncMock(return_value=True)
    manager.clear_state = AsyncMock(return_value=True)
    manager.set_brightness = AsyncMock(return_value=True)
    manager.get_status = MagicMock(return_value={"active_states": [], "initialized": True})
    return manager


@pytest.fixture
def led_event_handler(mock_led_manager):
    """Create LED event handler with mock manager."""
    return LEDEventHandler(mock_led_manager)


@pytest.fixture
async def initialized_handler(led_event_handler):
    """Create and initialize LED event handler."""
    await led_event_handler.initialize()
    return led_event_handler


# MARK: - Initialization Tests

class TestLEDEventHandlerInitialization:
    """Test LED event handler initialization and cleanup."""

    @pytest.mark.asyncio
    async def test_initialization_success(self, led_event_handler):
        """Test successful initialization."""
        result = await led_event_handler.initialize()

        assert result is True
        assert led_event_handler._is_initialized is True

    @pytest.mark.asyncio
    async def test_initialization_already_initialized(self, initialized_handler):
        """Test initialization when already initialized."""
        # Initialize again
        result = await initialized_handler.initialize()

        # Should still return True
        assert result is True

    @pytest.mark.asyncio
    async def test_cleanup(self, initialized_handler):
        """Test cleanup."""
        await initialized_handler.cleanup()

        assert initialized_handler._is_initialized is False

    @pytest.mark.asyncio
    async def test_cleanup_not_initialized(self, led_event_handler):
        """Test cleanup when not initialized."""
        await led_event_handler.cleanup()

        # Should not raise error
        assert led_event_handler._is_initialized is False

    def test_get_status(self, initialized_handler, mock_led_manager):
        """Test get_status returns correct information."""
        status = initialized_handler.get_status()

        assert status["initialized"] is True
        assert "led_manager_status" in status
        mock_led_manager.get_status.assert_called_once()


# MARK: - System Lifecycle Event Tests

class TestSystemLifecycleEvents:
    """Test system lifecycle event handlers."""

    @pytest.mark.asyncio
    async def test_on_system_starting(self, initialized_handler, mock_led_manager):
        """Test system starting event sets STARTING state."""
        await initialized_handler.on_system_starting()

        mock_led_manager.set_state.assert_called_once_with(LEDState.STARTING)

    @pytest.mark.asyncio
    async def test_on_system_ready(self, initialized_handler, mock_led_manager):
        """Test system ready event clears STARTING and sets IDLE."""
        await initialized_handler.on_system_ready()

        # Should clear STARTING state first
        mock_led_manager.clear_state.assert_called_once_with(LEDState.STARTING)
        # Then set IDLE state
        mock_led_manager.set_state.assert_called_once_with(LEDState.IDLE)

    @pytest.mark.asyncio
    async def test_system_starting_error_handling(self, initialized_handler, mock_led_manager):
        """Test error handling during system start event."""
        mock_led_manager.set_state.side_effect = Exception("LED hardware error")

        # Should not raise exception
        await initialized_handler.on_system_starting()

        # Should have attempted to set state
        mock_led_manager.set_state.assert_called_once_with(LEDState.STARTING)


# MARK: - NFC Event Tests

class TestNFCEvents:
    """Test NFC-related event handlers."""

    @pytest.mark.asyncio
    async def test_on_nfc_scan_success(self, initialized_handler, mock_led_manager):
        """Test NFC scan success event sets NFC_SUCCESS state."""
        await initialized_handler.on_nfc_scan_success()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_SUCCESS)

    @pytest.mark.asyncio
    async def test_on_nfc_scan_error(self, initialized_handler, mock_led_manager):
        """Test NFC scan error event sets NFC_ERROR state."""
        await initialized_handler.on_nfc_scan_error()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_ERROR)

    @pytest.mark.asyncio
    async def test_on_nfc_tag_unassociated(self, initialized_handler, mock_led_manager):
        """Test NFC tag unassociated event sets NFC_TAG_UNASSOCIATED state."""
        await initialized_handler.on_nfc_tag_unassociated()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_TAG_UNASSOCIATED)

    @pytest.mark.asyncio
    async def test_on_nfc_association_mode_started(self, initialized_handler, mock_led_manager):
        """Test NFC association mode started event (NEW - will fail until implemented)."""
        await initialized_handler.on_nfc_association_mode_started()

        mock_led_manager.set_state.assert_called_once_with(LEDState.NFC_ASSOCIATION_MODE)

    @pytest.mark.asyncio
    async def test_nfc_error_handling(self, initialized_handler, mock_led_manager):
        """Test error handling in NFC events."""
        mock_led_manager.set_state.side_effect = Exception("LED error")

        # Should not raise exception
        await initialized_handler.on_nfc_scan_error()

        # Should have attempted to set state
        mock_led_manager.set_state.assert_called_once()


# MARK: - Playback State Event Tests

class TestPlaybackStateEvents:
    """Test playback state change event handlers."""

    @pytest.mark.asyncio
    async def test_on_playback_state_playing(self, initialized_handler, mock_led_manager):
        """Test playback state change to PLAYING."""
        await initialized_handler.on_playback_state_changed(PlaybackState.PLAYING)

        mock_led_manager.set_state.assert_called_once_with(LEDState.PLAYING)

    @pytest.mark.asyncio
    async def test_on_playback_state_paused(self, initialized_handler, mock_led_manager):
        """Test playback state change to PAUSED."""
        await initialized_handler.on_playback_state_changed(PlaybackState.PAUSED)

        mock_led_manager.set_state.assert_called_once_with(LEDState.PAUSED)

    @pytest.mark.asyncio
    async def test_on_playback_state_stopped(self, initialized_handler, mock_led_manager):
        """Test playback state change to STOPPED (should revert to IDLE)."""
        await initialized_handler.on_playback_state_changed(PlaybackState.STOPPED)

        # When stopped, should clear PLAYING/PAUSED states and set IDLE
        mock_led_manager.clear_state.assert_any_call(LEDState.PLAYING)
        mock_led_manager.clear_state.assert_any_call(LEDState.PAUSED)
        mock_led_manager.set_state.assert_called_with(LEDState.IDLE)

    @pytest.mark.asyncio
    async def test_on_playback_state_unknown(self, initialized_handler, mock_led_manager):
        """Test playback state change to unknown state (should not set LED)."""
        # Create a mock state that's not in the mapping
        unknown_state = MagicMock()
        unknown_state.value = "UNKNOWN"

        await initialized_handler.on_playback_state_changed(unknown_state)

        # Should not call set_state for unknown state
        mock_led_manager.set_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_track_changed(self, initialized_handler, mock_led_manager):
        """Test track change event (maintains current state)."""
        await initialized_handler.on_track_changed()

        # Should not change LED state for track changes
        mock_led_manager.set_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_playback_state_error_handling(self, initialized_handler, mock_led_manager):
        """Test error handling during playback state change."""
        mock_led_manager.set_state.side_effect = Exception("LED error")

        # Should not raise exception
        await initialized_handler.on_playback_state_changed(PlaybackState.PLAYING)

        # Should have attempted to set state
        mock_led_manager.set_state.assert_called_once()


# MARK: - Error Event Tests

class TestErrorEvents:
    """Test error-related event handlers."""

    @pytest.mark.asyncio
    async def test_on_playback_error(self, initialized_handler, mock_led_manager):
        """Test playback error event sets ERROR_PLAYBACK state."""
        error_msg = "Failed to play track"
        await initialized_handler.on_playback_error(error_msg)

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_PLAYBACK)

    @pytest.mark.asyncio
    async def test_on_critical_error(self, initialized_handler, mock_led_manager):
        """Test critical error event sets ERROR_CRITICAL state."""
        error_msg = "System crash"
        await initialized_handler.on_critical_error(error_msg)

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_CRITICAL)

    @pytest.mark.asyncio
    async def test_on_boot_error(self, initialized_handler, mock_led_manager):
        """Test boot error event (NEW - will fail until implemented)."""
        error_msg = "Audio card not found"
        await initialized_handler.on_boot_error(error_msg)

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_BOOT_HARDWARE)

    @pytest.mark.asyncio
    async def test_on_crash_error(self, initialized_handler, mock_led_manager):
        """Test crash error event (NEW - will fail until implemented)."""
        error_msg = "Application crash"
        await initialized_handler.on_crash_error(error_msg)

        mock_led_manager.set_state.assert_called_once_with(LEDState.ERROR_CRASH)

    @pytest.mark.asyncio
    async def test_on_error_cleared(self, initialized_handler, mock_led_manager):
        """Test error cleared event clears error states."""
        await initialized_handler.on_error_cleared()

        # Should clear both error states
        assert mock_led_manager.clear_state.call_count == 2
        calls = mock_led_manager.clear_state.call_args_list
        assert call(LEDState.ERROR_PLAYBACK) in calls
        assert call(LEDState.ERROR_CRITICAL) in calls

    @pytest.mark.asyncio
    async def test_error_event_error_handling(self, initialized_handler, mock_led_manager):
        """Test error handling in error events (meta!)."""
        mock_led_manager.set_state.side_effect = Exception("LED error")

        # Should not raise exception
        await initialized_handler.on_critical_error("Test error")

        # Should have attempted to set state
        mock_led_manager.set_state.assert_called_once()


# MARK: - Volume Event Tests

class TestVolumeEvents:
    """Test volume-related event handlers."""

    @pytest.mark.asyncio
    async def test_on_volume_changed(self, initialized_handler, mock_led_manager):
        """Test volume change event (maintains current state)."""
        await initialized_handler.on_volume_changed(50)

        # Should not change LED state for volume changes
        mock_led_manager.set_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_volume_changed_various_levels(self, initialized_handler, mock_led_manager):
        """Test volume change with various volume levels."""
        volumes = [0, 25, 50, 75, 100]

        for volume in volumes:
            await initialized_handler.on_volume_changed(volume)

        # Should not change LED state for any volume changes
        mock_led_manager.set_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_volume_error_handling(self, initialized_handler):
        """Test error handling in volume events."""
        # Should not raise exception even with invalid volume
        await initialized_handler.on_volume_changed(-1)
        await initialized_handler.on_volume_changed(150)


# MARK: - Manual Control Tests

class TestManualControl:
    """Test manual LED control methods."""

    @pytest.mark.asyncio
    async def test_set_led_state_manually(self, initialized_handler, mock_led_manager):
        """Test manual LED state setting."""
        result = await initialized_handler.set_led_state(LEDState.PLAYING)

        assert result is True
        mock_led_manager.set_state.assert_called_once_with(LEDState.PLAYING)

    @pytest.mark.asyncio
    async def test_clear_led_state_manually(self, initialized_handler, mock_led_manager):
        """Test manual LED state clearing."""
        result = await initialized_handler.clear_led_state(LEDState.ERROR_PLAYBACK)

        assert result is True
        mock_led_manager.clear_state.assert_called_once_with(LEDState.ERROR_PLAYBACK)

    @pytest.mark.asyncio
    async def test_set_brightness_manually(self, initialized_handler, mock_led_manager):
        """Test manual brightness setting."""
        result = await initialized_handler.set_brightness(0.5)

        assert result is True
        mock_led_manager.set_brightness.assert_called_once_with(0.5)

    @pytest.mark.asyncio
    async def test_manual_control_error_handling(self, initialized_handler, mock_led_manager):
        """Test error handling in manual control methods."""
        mock_led_manager.set_state.side_effect = Exception("LED error")

        result = await initialized_handler.set_led_state(LEDState.IDLE)

        assert result is False
        mock_led_manager.set_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_state_error_handling(self, initialized_handler, mock_led_manager):
        """Test error handling when clearing state."""
        mock_led_manager.clear_state.side_effect = Exception("LED error")

        result = await initialized_handler.clear_led_state(LEDState.PLAYING)

        assert result is False
        mock_led_manager.clear_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_brightness_error_handling(self, initialized_handler, mock_led_manager):
        """Test error handling when setting brightness."""
        mock_led_manager.set_brightness.side_effect = Exception("LED error")

        result = await initialized_handler.set_brightness(0.8)

        assert result is False
        mock_led_manager.set_brightness.assert_called_once()


# MARK: - Event Sequencing Tests

class TestEventSequencing:
    """Test correct sequencing of multiple events."""

    @pytest.mark.asyncio
    async def test_startup_sequence(self, initialized_handler, mock_led_manager):
        """Test complete startup sequence: STARTING → READY."""
        # System starting
        await initialized_handler.on_system_starting()
        mock_led_manager.set_state.assert_called_with(LEDState.STARTING)

        # System ready
        await initialized_handler.on_system_ready()
        mock_led_manager.clear_state.assert_called_with(LEDState.STARTING)

        # Get all set_state calls
        set_calls = [call[0][0] for call in mock_led_manager.set_state.call_args_list]
        assert LEDState.STARTING in set_calls
        assert LEDState.IDLE in set_calls

    @pytest.mark.asyncio
    async def test_nfc_scan_sequence(self, initialized_handler, mock_led_manager):
        """Test NFC scan sequence: ASSOCIATION_MODE → SUCCESS."""
        # Start association mode
        await initialized_handler.on_nfc_association_mode_started()
        mock_led_manager.set_state.assert_called_with(LEDState.NFC_ASSOCIATION_MODE)

        # Success
        await initialized_handler.on_nfc_scan_success()
        mock_led_manager.set_state.assert_called_with(LEDState.NFC_SUCCESS)

    @pytest.mark.asyncio
    async def test_playback_sequence(self, initialized_handler, mock_led_manager):
        """Test playback sequence: PLAYING → PAUSED → PLAYING → STOPPED (reverts to IDLE)."""
        # Start playing
        await initialized_handler.on_playback_state_changed(PlaybackState.PLAYING)
        mock_led_manager.set_state.assert_called_with(LEDState.PLAYING)

        # Pause
        await initialized_handler.on_playback_state_changed(PlaybackState.PAUSED)
        mock_led_manager.set_state.assert_called_with(LEDState.PAUSED)

        # Resume
        await initialized_handler.on_playback_state_changed(PlaybackState.PLAYING)

        # Stop - should clear playback states and revert to IDLE
        await initialized_handler.on_playback_state_changed(PlaybackState.STOPPED)
        mock_led_manager.clear_state.assert_any_call(LEDState.PLAYING)
        mock_led_manager.clear_state.assert_any_call(LEDState.PAUSED)
        mock_led_manager.set_state.assert_called_with(LEDState.IDLE)

    @pytest.mark.asyncio
    async def test_error_and_recovery_sequence(self, initialized_handler, mock_led_manager):
        """Test error occurrence and recovery sequence."""
        # Error occurs
        await initialized_handler.on_playback_error("Test error")
        mock_led_manager.set_state.assert_called_with(LEDState.ERROR_PLAYBACK)

        # Error cleared
        await initialized_handler.on_error_cleared()
        mock_led_manager.clear_state.assert_any_call(LEDState.ERROR_PLAYBACK)

    @pytest.mark.asyncio
    async def test_shutdown_sequence(self, initialized_handler, mock_led_manager):
        """Test shutdown sequence."""
        # Cleanup (no shutting_down state anymore)
        await initialized_handler.cleanup()
        assert initialized_handler._is_initialized is False
