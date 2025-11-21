# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Mock LED Controller (Infrastructure Layer).

Mock implementation for testing and development without hardware.
"""

import logging
from typing import Dict, Any

from .base_led_controller import BaseLEDController
from app.src.domain.models.led import LEDColor, LEDAnimation, LEDColors

logger = logging.getLogger(__name__)


class MockLEDController(BaseLEDController):
    """
    Mock LED controller for testing.

    Simulates LED behavior without real hardware, tracking all operations
    for verification in tests.

    Inherits common LED functionality from BaseLEDController.
    """

    def __init__(self, default_brightness: float = 1.0):
        """Initialize mock LED controller.

        Args:
            default_brightness: Initial brightness (0.0-1.0)
        """
        super().__init__(default_brightness)

        # Operation tracking for tests
        self._operations: list = []

    async def initialize(self) -> bool:
        """Initialize mock LED hardware."""
        with self._lock:
            if self._is_initialized:
                logger.warning("Mock LED already initialized")
                return True

            self._is_initialized = True
            self._operations.append(("initialize", {}))
            logger.info("🧪 Mock LED controller initialized")
            return True

    async def cleanup(self) -> None:
        """Clean up mock LED resources."""
        with self._lock:
            if not self._is_initialized:
                return

            self._current_color = LEDColors.OFF
            self._current_animation = LEDAnimation.SOLID
            self._is_initialized = False
            self._operations.append(("cleanup", {}))
            logger.info("🧪 Mock LED controller cleaned up")

    async def set_color(self, color: LEDColor) -> bool:
        """Set mock LED to solid color."""
        if not self._check_initialized("set_color"):
            return False

        with self._lock:
            self._current_color = color
            self._current_animation = LEDAnimation.SOLID
            # Apply brightness scaling for realistic simulation
            scaled = color.scaled(self._brightness)
            self._operations.append(("set_color", {
                "color": color.to_tuple(),
                "scaled_color": scaled.to_tuple(),
                "brightness": self._brightness
            }))
            logger.info(
                f"🧪 Mock LED color set to RGB{color.to_tuple()} "
                f"(scaled to RGB{scaled.to_tuple()} at {self._brightness:.1%} brightness)"
            )
            return True

    async def set_animation(
        self,
        color: LEDColor,
        animation: LEDAnimation,
        speed: float = 1.0
    ) -> bool:
        """Set mock LED with animation."""
        if not self._check_initialized("set_animation"):
            return False

        with self._lock:
            self._current_color = color
            self._current_animation = animation
            self._animation_speed = speed
            # Apply brightness scaling for realistic simulation
            scaled = color.scaled(self._brightness)
            self._operations.append((
                "set_animation",
                {
                    "color": color.to_tuple(),
                    "scaled_color": scaled.to_tuple(),
                    "animation": animation.value,
                    "speed": speed,
                    "brightness": self._brightness
                }
            ))
            logger.info(
                f"🧪 Mock LED animation set: {animation.value} at {speed}x speed, "
                f"color RGB{color.to_tuple()} "
                f"(scaled to RGB{scaled.to_tuple()} at {self._brightness:.1%} brightness)"
            )
            return True

    async def turn_off(self) -> bool:
        """Turn off mock LED."""
        return await self.set_color(LEDColors.OFF)

    async def set_brightness(self, brightness: float) -> bool:
        """Set mock LED brightness level.

        Extends base class to track operation for testing.
        """
        # Call base class for validation and setting
        result = await super().set_brightness(brightness)

        if result:
            with self._lock:
                self._operations.append(("set_brightness", {"brightness": brightness}))

        return result

    def stop_animation(self) -> None:
        """Stop any running mock animation."""
        with self._lock:
            self._operations.append(("stop_animation", {}))
            logger.debug("🧪 Mock LED animation stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get current mock LED status.

        Extends base class status with mock-specific information.
        """
        # Get base status
        status = super().get_status()

        # Add mock-specific fields
        with self._lock:
            status.update({
                "mock_mode": True,
                "gpio_available": False,
                "operations_count": len(self._operations)
            })

        return status

    # Test helper methods

    def get_operations(self) -> list:
        """Get list of all operations performed (for testing)."""
        with self._lock:
            return self._operations.copy()

    def clear_operations(self) -> None:
        """Clear operation history (for testing)."""
        with self._lock:
            self._operations.clear()

    # Note: get_current_color(), get_current_animation(), and get_brightness()
    # are now inherited from BaseLEDController
