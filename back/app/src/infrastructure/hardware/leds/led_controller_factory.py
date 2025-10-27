# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
LED Controller Factory (Infrastructure Layer).

Factory for creating LED controller implementations based on environment.
"""

import os
import logging
from typing import Any

from app.src.domain.protocols.indicator_lights_protocol import IndicatorLightsProtocol
from app.src.infrastructure.hardware.leds.rgb_led_controller import RGBLEDController
from app.src.infrastructure.hardware.leds.mock_led_controller import MockLEDController

logger = logging.getLogger(__name__)


class LEDControllerFactory:
    """
    Factory for creating LED controller implementations.

    Automatically selects appropriate implementation based on:
    - USE_MOCK_HARDWARE environment variable
    - GPIO hardware availability
    """

    @staticmethod
    def create_controller(hardware_config: Any) -> IndicatorLightsProtocol:
        """
        Create LED controller instance based on environment.

        Args:
            hardware_config: Hardware configuration with GPIO pin assignments

        Returns:
            LED controller implementation (real or mock)
        """
        use_mock = os.getenv("USE_MOCK_HARDWARE", "false").lower() == "true"

        if use_mock:
            logger.info("🧪 Creating mock LED controller (USE_MOCK_HARDWARE=true)")
            return MockLEDController()

        # Try to create real GPIO controller
        try:
            # Check if GPIO pins are configured
            if not hasattr(hardware_config, 'gpio_led_red'):
                logger.warning(
                    "⚠️ LED GPIO pins not configured, falling back to mock controller"
                )
                return MockLEDController()

            controller = RGBLEDController(
                red_pin=hardware_config.gpio_led_red,
                green_pin=hardware_config.gpio_led_green,
                blue_pin=hardware_config.gpio_led_blue
            )

            logger.info(
                f"🔌 Creating real RGB LED controller on GPIO "
                f"R:{hardware_config.gpio_led_red} "
                f"G:{hardware_config.gpio_led_green} "
                f"B:{hardware_config.gpio_led_blue}"
            )

            return controller

        except Exception as e:
            logger.warning(
                f"⚠️ Failed to create real LED controller: {e}, "
                f"falling back to mock"
            )
            return MockLEDController()

    @staticmethod
    def create_mock_controller() -> MockLEDController:
        """
        Create mock LED controller for testing.

        Returns:
            Mock LED controller instance
        """
        logger.info("🧪 Creating mock LED controller (explicit)")
        return MockLEDController()

    @staticmethod
    def create_real_controller(
        red_pin: int,
        green_pin: int,
        blue_pin: int
    ) -> RGBLEDController:
        """
        Create real RGB LED controller with specific pins.

        Args:
            red_pin: GPIO pin for red channel
            green_pin: GPIO pin for green channel
            blue_pin: GPIO pin for blue channel

        Returns:
            Real RGB LED controller instance
        """
        logger.info(
            f"🔌 Creating real RGB LED controller on GPIO "
            f"R:{red_pin} G:{green_pin} B:{blue_pin} (explicit)"
        )
        return RGBLEDController(
            red_pin=red_pin,
            green_pin=green_pin,
            blue_pin=blue_pin
        )
