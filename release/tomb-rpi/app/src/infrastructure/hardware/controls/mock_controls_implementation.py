# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Mock Physical Controls Implementation.

Mock implementation for testing and development without real hardware.
"""

from typing import Dict, Any, List, Optional
import logging

from .base_controls_implementation import BaseControlsImplementation
from app.src.domain.protocols.physical_controls_protocol import PhysicalControlEvent
from app.src.config.button_actions_config import ButtonActionConfig

logger = logging.getLogger(__name__)


class MockPhysicalControls(BaseControlsImplementation):
    """Mock implementation of physical controls for testing.

    Inherits common controls functionality from BaseControlsImplementation.
    """

    def __init__(
        self,
        hardware_config: Any,
        button_configs: Optional[List[ButtonActionConfig]] = None
    ):
        """Initialize mock physical controls.

        Args:
            hardware_config: Hardware configuration (for compatibility)
            button_configs: Optional button configurations
        """
        super().__init__(hardware_config, button_configs)

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

    def get_status(self) -> Dict[str, Any]:
        """Get current status of mock controls.

        Uses base class helper for button info.
        """
        # Get button info from base class helper
        button_info = self._build_button_info()

        return {
            "initialized": self._is_initialized,
            "mock_mode": True,
            "event_handlers_count": len(self._event_handlers),
            "configurable_buttons": button_info,
            "encoder": {
                "play_pause_button": self.config.gpio_volume_encoder_sw,
                "volume_encoder_clk": self.config.gpio_volume_encoder_clk,
                "volume_encoder_dt": self.config.gpio_volume_encoder_dt,
            }
        }

    # Note: set_event_handler() and is_initialized() are now inherited from BaseControlsImplementation

    async def simulate_button_press(self, event_type: PhysicalControlEvent) -> None:
        """Simulate a button press for testing.

        Uses base class _invoke_event_handler() for consistent event handling.

        Args:
            event_type: Type of control event to simulate
        """
        if not self._is_initialized:
            logger.warning("Cannot simulate button press - mock controls not initialized")
            return

        logger.info(f"🧪 Simulating control event: {event_type}")
        self._invoke_event_handler(event_type, "simulated")

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
