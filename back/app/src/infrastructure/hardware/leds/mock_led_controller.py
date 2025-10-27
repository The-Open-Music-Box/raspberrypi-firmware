# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Mock LED Controller (Infrastructure Layer).

Mock implementation for testing and development without hardware.
"""

import logging
from typing import Dict, Any
from threading import Lock

from app.src.domain.protocols.indicator_lights_protocol import IndicatorLightsProtocol
from app.src.domain.models.led import LEDColor, LEDAnimation, LEDColors

logger = logging.getLogger(__name__)


class MockLEDController(IndicatorLightsProtocol):
    """
    Mock LED controller for testing.

    Simulates LED behavior without real hardware, tracking all operations
    for verification in tests.
    """

    def __init__(self):
        """Initialize mock LED controller."""
        self._is_initialized = False
        self._current_color = LEDColors.OFF
        self._current_animation = LEDAnimation.SOLID
        self._animation_speed = 1.0
        self._brightness = 1.0
        self._lock = Lock()

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
        if not self._is_initialized:
            logger.warning("Mock LED not initialized")
            return False

        with self._lock:
            self._current_color = color
            self._current_animation = LEDAnimation.SOLID
            self._operations.append(("set_color", {"color": color.to_tuple()}))
            logger.info(f"🧪 Mock LED color set to RGB{color.to_tuple()}")
            return True

    async def set_animation(
        self,
        color: LEDColor,
        animation: LEDAnimation,
        speed: float = 1.0
    ) -> bool:
        """Set mock LED with animation."""
        if not self._is_initialized:
            logger.warning("Mock LED not initialized")
            return False

        with self._lock:
            self._current_color = color
            self._current_animation = animation
            self._animation_speed = speed
            self._operations.append((
                "set_animation",
                {
                    "color": color.to_tuple(),
                    "animation": animation.value,
                    "speed": speed
                }
            ))
            logger.info(
                f"🧪 Mock LED animation set: {animation.value} at {speed}x speed, "
                f"color RGB{color.to_tuple()}"
            )
            return True

    async def turn_off(self) -> bool:
        """Turn off mock LED."""
        return await self.set_color(LEDColors.OFF)

    async def set_brightness(self, brightness: float) -> bool:
        """Set mock LED brightness level."""
        if not 0.0 <= brightness <= 1.0:
            logger.warning(f"Invalid brightness {brightness}, must be 0.0-1.0")
            return False

        with self._lock:
            self._brightness = brightness
            self._operations.append(("set_brightness", {"brightness": brightness}))
            logger.info(f"🧪 Mock LED brightness set to {brightness:.1%}")
            return True

    def stop_animation(self) -> None:
        """Stop any running mock animation."""
        with self._lock:
            self._operations.append(("stop_animation", {}))
            logger.debug("🧪 Mock LED animation stopped")

    def is_initialized(self) -> bool:
        """Check if mock LED is initialized."""
        return self._is_initialized

    def get_status(self) -> Dict[str, Any]:
        """Get current mock LED status."""
        with self._lock:
            return {
                "initialized": self._is_initialized,
                "mock_mode": True,
                "gpio_available": False,
                "current_color": self._current_color.to_tuple(),
                "current_animation": self._current_animation.value,
                "animation_speed": self._animation_speed,
                "brightness": self._brightness,
                "operations_count": len(self._operations)
            }

    # Test helper methods

    def get_operations(self) -> list:
        """Get list of all operations performed (for testing)."""
        with self._lock:
            return self._operations.copy()

    def clear_operations(self) -> None:
        """Clear operation history (for testing)."""
        with self._lock:
            self._operations.clear()

    def get_current_color(self) -> LEDColor:
        """Get current color (for testing)."""
        return self._current_color

    def get_current_animation(self) -> LEDAnimation:
        """Get current animation (for testing)."""
        return self._current_animation

    def get_brightness(self) -> float:
        """Get current brightness (for testing)."""
        return self._brightness
