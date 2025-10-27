# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Indicator Lights Protocol (Domain Layer).

Defines the interface for LED indicator control, following the same pattern
as PhysicalControlsProtocol for consistency.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
from app.src.domain.models.led import LEDColor, LEDAnimation


class IndicatorLightsProtocol(ABC):
    """
    Protocol for LED indicator light management.

    Provides abstract interface for controlling RGB LED indicators,
    allowing multiple implementations (real GPIO, mock, etc.).
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize LED hardware.

        Returns:
            True if initialization was successful, False otherwise
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up LED resources and turn off lights."""
        pass

    @abstractmethod
    async def set_color(self, color: LEDColor) -> bool:
        """
        Set LED to a solid color.

        Args:
            color: RGB color to display

        Returns:
            True if color was set successfully, False otherwise
        """
        pass

    @abstractmethod
    async def set_animation(
        self,
        color: LEDColor,
        animation: LEDAnimation,
        speed: float = 1.0
    ) -> bool:
        """
        Set LED color with animation.

        Args:
            color: RGB color to display
            animation: Animation type to apply
            speed: Animation speed multiplier (1.0 = normal)

        Returns:
            True if animation was started successfully, False otherwise
        """
        pass

    @abstractmethod
    async def turn_off(self) -> bool:
        """
        Turn off LED completely.

        Returns:
            True if LED was turned off successfully, False otherwise
        """
        pass

    @abstractmethod
    async def set_brightness(self, brightness: float) -> bool:
        """
        Set global brightness level.

        Args:
            brightness: Brightness level (0.0-1.0)

        Returns:
            True if brightness was set successfully, False otherwise
        """
        pass

    @abstractmethod
    def is_initialized(self) -> bool:
        """
        Check if LED controller is initialized.

        Returns:
            True if initialized and ready, False otherwise
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of LED controller.

        Returns:
            Dictionary containing status information including:
            - initialized: bool
            - current_color: tuple (r, g, b)
            - current_animation: str
            - brightness: float
            - gpio_pins: dict (if applicable)
        """
        pass

    @abstractmethod
    def stop_animation(self) -> None:
        """Stop any running animation immediately."""
        pass
