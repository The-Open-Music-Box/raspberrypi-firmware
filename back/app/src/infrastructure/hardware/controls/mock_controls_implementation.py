# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Mock Physical Controls Implementation.

Mock implementation for testing and development without real hardware.
"""

from typing import Callable, Dict, Any
import asyncio
import logging

from app.src.domain.protocols.physical_controls_protocol import (
    PhysicalControlsProtocol,
    PhysicalControlEvent,
)
logger = logging.getLogger(__name__)


class MockPhysicalControls(PhysicalControlsProtocol):
    """Mock implementation of physical controls for testing."""

    def __init__(self, hardware_config: Any):
        """Initialize mock physical controls.

        Args:
            hardware_config: Hardware configuration (for compatibility)
        """
        self.config = hardware_config
        self._is_initialized = False
        self._event_handlers: Dict[PhysicalControlEvent, Callable[[], None]] = {}

    async def initialize(self) -> bool:
        """Initialize mock controls."""
        logger.info("🧪 Initializing mock physical controls...")
        self._is_initialized = True
        logger.info("✅ Mock physical controls initialized")
        return True

    async def cleanup(self) -> None:
        """Clean up mock controls."""
        logger.info("🧹 Cleaning up mock physical controls...")
        self._is_initialized = False
        self._event_handlers.clear()
        logger.info("✅ Mock physical controls cleanup completed")

    def set_event_handler(self, event_type: PhysicalControlEvent, handler: Callable[[], None]) -> None:
        """Set event handler for a specific control event."""
        self._event_handlers[event_type] = handler
        logger.debug(f"Mock event handler set for: {event_type}")

    def is_initialized(self) -> bool:
        """Check if mock controls are initialized."""
        return self._is_initialized

    def get_status(self) -> dict:
        """Get current status of mock controls."""
        return {
            "initialized": self._is_initialized,
            "mock_mode": True,
            "event_handlers_count": len(self._event_handlers),
            "mock_pin_assignments": {
                "next_button": self.config.gpio_next_track_button,
                "previous_button": self.config.gpio_previous_track_button,
                "play_pause_button": self.config.gpio_volume_encoder_sw,
                "volume_encoder_clk": self.config.gpio_volume_encoder_clk,
                "volume_encoder_dt": self.config.gpio_volume_encoder_dt,
            }
        }

    async def simulate_button_press(self, event_type: PhysicalControlEvent) -> None:
        """Simulate a button press for testing.

        Args:
            event_type: Type of control event to simulate
        """
        if not self._is_initialized:
            logger.warning("Cannot simulate button press - mock controls not initialized")
            return

        handler = self._event_handlers.get(event_type)
        if handler:
            logger.info(f"🧪 Simulating control event: {event_type}")
            try:
                handler()
            except Exception as e:
                logger.error(f"❌ Error in simulated event handler for {event_type}: {e}")
        else:
            logger.warning(f"No handler registered for simulated event: {event_type}")

    async def simulate_next_track(self) -> None:
        """Simulate next track button press."""
        await self.simulate_button_press(PhysicalControlEvent.BUTTON_NEXT_TRACK)

    async def simulate_previous_track(self) -> None:
        """Simulate previous track button press."""
        await self.simulate_button_press(PhysicalControlEvent.BUTTON_PREVIOUS_TRACK)

    async def simulate_play_pause(self) -> None:
        """Simulate play/pause button press."""
        await self.simulate_button_press(PhysicalControlEvent.BUTTON_PLAY_PAUSE)

    async def simulate_volume_up(self) -> None:
        """Simulate volume up encoder rotation."""
        await self.simulate_button_press(PhysicalControlEvent.ENCODER_VOLUME_UP)

    async def simulate_volume_down(self) -> None:
        """Simulate volume down encoder rotation."""
        await self.simulate_button_press(PhysicalControlEvent.ENCODER_VOLUME_DOWN)
