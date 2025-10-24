# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
LED Event Handler (Application Layer).

Bridges application events to LED state changes.
"""

import logging
from typing import Optional

from app.src.application.services.led_state_manager_application_service import LEDStateManager
from app.src.domain.models.led import LEDState
from app.src.common.data_models import PlaybackState

logger = logging.getLogger(__name__)


class LEDEventHandler:
    """
    Handles application events and updates LED states accordingly.

    Responsibilities:
    - Listen to playback state changes
    - Listen to NFC events
    - Listen to system error events
    - Translate events to appropriate LED states
    """

    def __init__(self, led_state_manager: LEDStateManager):
        """
        Initialize LED event handler.

        Args:
            led_state_manager: LED state manager instance
        """
        self._led_manager = led_state_manager
        self._is_initialized = False

    async def initialize(self) -> bool:
        """
        Initialize LED event handler.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._is_initialized = True
            logger.info("✅ LED event handler initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to initialize LED event handler: {e}")
            return False

    async def cleanup(self) -> None:
        """Clean up event handler resources."""
        try:
            self._is_initialized = False
            logger.info("✅ LED event handler cleaned up")
        except Exception as e:
            logger.error(f"❌ Error during LED event handler cleanup: {e}")

    # Playback state event handlers

    async def on_playback_state_changed(self, new_state: PlaybackState) -> None:
        """
        Handle playback state changes.

        Args:
            new_state: New playback state
        """
        try:
            led_state_mapping = {
                PlaybackState.PLAYING: LEDState.PLAYING,
                PlaybackState.PAUSED: LEDState.PAUSED,
                PlaybackState.STOPPED: LEDState.STOPPED,
            }

            led_state = led_state_mapping.get(new_state)
            if led_state:
                await self._led_manager.set_state(led_state)
                logger.debug(f"LED updated for playback state: {new_state.value} → {led_state.value}")
            else:
                logger.debug(f"No LED mapping for playback state: {new_state.value}")

        except Exception as e:
            logger.error(f"❌ Error handling playback state change: {e}")

    async def on_track_changed(self) -> None:
        """
        Handle track change events.

        Shows brief flash to indicate track change.
        """
        try:
            # Could show a brief flash or color change
            # For now, just log it
            logger.debug("Track changed - LED maintained current playback state")
        except Exception as e:
            logger.error(f"❌ Error handling track change: {e}")

    # NFC event handlers

    async def on_nfc_scan_started(self) -> None:
        """Handle NFC scan start event."""
        try:
            await self._led_manager.set_state(LEDState.NFC_SCANNING)
            logger.debug("LED updated: NFC scanning started")
        except Exception as e:
            logger.error(f"❌ Error handling NFC scan start: {e}")

    async def on_nfc_scan_success(self) -> None:
        """Handle successful NFC scan event."""
        try:
            await self._led_manager.set_state(LEDState.NFC_SUCCESS)
            logger.debug("LED updated: NFC scan successful")
        except Exception as e:
            logger.error(f"❌ Error handling NFC scan success: {e}")

    async def on_nfc_scan_error(self) -> None:
        """Handle NFC scan error event."""
        try:
            await self._led_manager.set_state(LEDState.NFC_ERROR)
            logger.debug("LED updated: NFC scan error")
        except Exception as e:
            logger.error(f"❌ Error handling NFC scan error: {e}")

    # System event handlers

    async def on_system_starting(self) -> None:
        """Handle system startup event."""
        try:
            logger.info("💡 Setting LED state: STARTING (white blinking)")
            await self._led_manager.set_state(LEDState.STARTING)
            logger.info("✅ LED state set to STARTING")
        except Exception as e:
            logger.error(f"❌ Error handling system start: {e}", exc_info=True)

    async def on_system_ready(self) -> None:
        """Handle system ready event."""
        try:
            logger.info("💡 Clearing STARTING state and setting IDLE (solid white)")
            # Clear STARTING state and transition to IDLE
            await self._led_manager.clear_state(LEDState.STARTING)
            await self._led_manager.set_state(LEDState.IDLE)
            logger.info("✅ LED state set to IDLE")
        except Exception as e:
            logger.error(f"❌ Error handling system ready: {e}", exc_info=True)

    async def on_system_shutting_down(self) -> None:
        """Handle system shutdown event."""
        try:
            await self._led_manager.set_state(LEDState.SHUTTING_DOWN)
            logger.debug("LED updated: System shutting down")
        except Exception as e:
            logger.error(f"❌ Error handling system shutdown: {e}")

    # Error event handlers

    async def on_playback_error(self, error_message: str) -> None:
        """
        Handle playback error event.

        Args:
            error_message: Error description
        """
        try:
            await self._led_manager.set_state(LEDState.ERROR_PLAYBACK)
            logger.warning(f"LED updated: Playback error - {error_message}")
        except Exception as e:
            logger.error(f"❌ Error handling playback error: {e}")

    async def on_critical_error(self, error_message: str) -> None:
        """
        Handle critical system error event.

        Args:
            error_message: Error description
        """
        try:
            await self._led_manager.set_state(LEDState.ERROR_CRITICAL)
            logger.error(f"LED updated: Critical error - {error_message}")
        except Exception as e:
            logger.error(f"❌ Error handling critical error: {e}")

    async def on_error_cleared(self) -> None:
        """Handle error cleared event."""
        try:
            # Clear error states
            await self._led_manager.clear_state(LEDState.ERROR_PLAYBACK)
            await self._led_manager.clear_state(LEDState.ERROR_CRITICAL)
            logger.debug("LED updated: Errors cleared")
        except Exception as e:
            logger.error(f"❌ Error handling error cleared: {e}")

    # Volume event handlers

    async def on_volume_changed(self, new_volume: int) -> None:
        """
        Handle volume change event.

        Args:
            new_volume: New volume level (0-100)
        """
        try:
            # Could show brief brightness change or pulse
            # For now, just maintain current state
            logger.debug(f"Volume changed to {new_volume}% - LED maintained current state")
        except Exception as e:
            logger.error(f"❌ Error handling volume change: {e}")

    # Manual LED control methods

    async def set_led_state(self, state: LEDState) -> bool:
        """
        Manually set LED state (for testing or special cases).

        Args:
            state: LED state to set

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._led_manager.set_state(state)
        except Exception as e:
            logger.error(f"❌ Error setting LED state manually: {e}")
            return False

    async def clear_led_state(self, state: LEDState) -> bool:
        """
        Manually clear LED state.

        Args:
            state: LED state to clear

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._led_manager.clear_state(state)
        except Exception as e:
            logger.error(f"❌ Error clearing LED state manually: {e}")
            return False

    async def set_brightness(self, brightness: float) -> bool:
        """
        Set LED brightness.

        Args:
            brightness: Brightness level (0.0-1.0)

        Returns:
            True if successful, False otherwise
        """
        try:
            return await self._led_manager.set_brightness(brightness)
        except Exception as e:
            logger.error(f"❌ Error setting brightness: {e}")
            return False

    def get_status(self) -> dict:
        """
        Get current status of LED event handler.

        Returns:
            Status dictionary
        """
        return {
            "initialized": self._is_initialized,
            "led_manager_status": self._led_manager.get_status()
        }
