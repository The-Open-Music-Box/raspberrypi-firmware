# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Base LED Controller (Infrastructure Layer).

Provides common functionality for LED controller implementations,
extracting duplication between MockLEDController and RGBLEDController.
Follows Context7 principles with proper type safety and DDD architecture.
"""

import logging
from abc import abstractmethod
from threading import Lock
from typing import Any

from app.src.domain.models.led import LEDAnimation, LEDColor, LEDColors
from app.src.domain.protocols.indicator_lights_protocol import IndicatorLightsProtocol

logger = logging.getLogger(__name__)


class BaseLEDController(IndicatorLightsProtocol):
    """
    Base class for LED controller implementations.

    This class provides common functionality for LED controllers, including:
    - State management (_is_initialized, _current_color, _current_animation, _brightness)
    - Thread safety with locking
    - Brightness validation and clamping
    - Common status reporting structure
    - Initialization check patterns

    Subclasses must implement:
    - initialize(): Hardware-specific initialization
    - cleanup(): Hardware-specific cleanup
    - set_color(): Hardware-specific color setting
    - set_animation(): Hardware-specific animation
    - turn_off(): Hardware-specific turn off
    - stop_animation(): Hardware-specific animation stop
    """

    def __init__(self, default_brightness: float = 1.0):
        """Initialize base LED controller state.

        Extracted common initialization from MockLEDController and RGBLEDController.

        Args:
            default_brightness: Initial brightness (0.0-1.0)
        """
        self._is_initialized = False
        self._current_color = LEDColors.OFF
        self._current_animation = LEDAnimation.SOLID
        self._animation_speed = 1.0
        self._brightness = self._clamp_brightness(default_brightness)
        self._lock = Lock()

        logger.debug(f"{self.__class__.__name__}: Base LED controller state initialized")

    def _clamp_brightness(self, brightness: float) -> float:
        """Clamp brightness to valid range (0.0-1.0).

        Extracted helper to eliminate duplication of brightness validation.

        Args:
            brightness: Brightness level to clamp

        Returns:
            float: Clamped brightness level between 0.0 and 1.0
        """
        return max(0.0, min(1.0, brightness))

    def _validate_brightness(self, brightness: float) -> bool:
        """Validate brightness is in acceptable range.

        Extracted helper for brightness validation used in set_brightness methods.

        Args:
            brightness: Brightness value to validate

        Returns:
            bool: True if brightness is valid, False otherwise
        """
        if not 0.0 <= brightness <= 1.0:
            logger.warning(
                f"{self.__class__.__name__}: Invalid brightness {brightness}, "
                f"must be 0.0-1.0"
            )
            return False
        return True

    def _check_initialized(self, operation_name: str = "operation") -> bool:
        """Check if controller is initialized and log warning if not.

        Extracted helper to eliminate duplication of initialization checking.
        This pattern appears in multiple methods across both implementations.

        Args:
            operation_name: Name of the operation being checked (for logging)

        Returns:
            bool: True if initialized, False otherwise
        """
        if not self._is_initialized:
            logger.warning(f"{self.__class__.__name__}: {operation_name} - LED not initialized")
            return False
        return True

    def is_initialized(self) -> bool:
        """Check if LED controller is initialized.

        Common implementation identical in both MockLEDController and RGBLEDController.

        Returns:
            bool: True if initialized, False otherwise
        """
        return self._is_initialized

    def get_brightness(self) -> float:
        """Get current brightness level.

        Common getter method for brightness (used in tests).

        Returns:
            float: Current brightness (0.0-1.0)
        """
        return self._brightness

    def get_current_color(self) -> LEDColor:
        """Get current color.

        Common getter method for current color (used in tests).

        Returns:
            LEDColor: Current LED color
        """
        return self._current_color

    def get_current_animation(self) -> LEDAnimation:
        """Get current animation.

        Common getter method for current animation (used in tests).

        Returns:
            LEDAnimation: Current animation type
        """
        return self._current_animation

    def get_status(self) -> dict[str, Any]:
        """Get current status of LED controller.

        Provides base status information common to all implementations.
        Subclasses can override to add implementation-specific details.

        Returns:
            Dictionary containing common status information
        """
        with self._lock:
            return {
                "initialized": self._is_initialized,
                "current_color": self._current_color.to_tuple(),
                "current_animation": self._current_animation.value,
                "animation_speed": self._animation_speed,
                "brightness": self._brightness,
            }

    async def set_brightness(self, brightness: float) -> bool:
        """Set LED brightness level.

        Common brightness setting logic with validation.
        Extracted from both implementations (nearly identical).

        Args:
            brightness: Brightness level (0.0-1.0)

        Returns:
            bool: True if brightness was set successfully, False otherwise
        """
        if not self._validate_brightness(brightness):
            return False

        with self._lock:
            self._brightness = brightness
            logger.info(f"{self.__class__.__name__}: Brightness set to {brightness:.1%}")
            return True

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize LED hardware.

        Must be implemented by subclasses for hardware-specific initialization.
        - Mock: Simple flag setting and logging
        - RGB: GPIO device initialization and pin setup

        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up LED resources.

        Must be implemented by subclasses for hardware-specific cleanup.
        - Mock: Reset state and clear operations
        - RGB: Stop animations, turn off LEDs, cleanup GPIO
        """
        pass

    @abstractmethod
    async def set_color(self, color: LEDColor) -> bool:
        """Set LED to a solid color.

        Must be implemented by subclasses for hardware-specific color setting.
        - Mock: Track operation and log
        - RGB: Apply color to GPIO PWM pins

        Args:
            color: RGB color to display

        Returns:
            bool: True if color was set successfully, False otherwise
        """
        pass

    @abstractmethod
    async def set_animation(
        self,
        color: LEDColor,
        animation: LEDAnimation,
        speed: float = 1.0
    ) -> bool:
        """Set LED with animation.

        Must be implemented by subclasses for hardware-specific animation.
        - Mock: Track operation and log
        - RGB: Start animation thread with specified pattern

        Args:
            color: RGB color to display
            animation: Animation type to apply
            speed: Animation speed multiplier (1.0 = normal)

        Returns:
            bool: True if animation started successfully, False otherwise
        """
        pass

    @abstractmethod
    async def turn_off(self) -> bool:
        """Turn off LED completely.

        Must be implemented by subclasses for hardware-specific turn off.
        - Mock: Set color to OFF
        - RGB: Set all PWM channels to 0

        Returns:
            bool: True if LED was turned off successfully, False otherwise
        """
        pass

    @abstractmethod
    def stop_animation(self) -> None:
        """Stop any running animation.

        Must be implemented by subclasses for hardware-specific animation stop.
        - Mock: Track operation
        - RGB: Stop animation thread and reset event
        """
        pass
