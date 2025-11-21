# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Physical Controls Factory.

Factory for creating physical controls implementations based on environment.
"""

import os
from typing import Optional, Any, List
import logging

from app.src.domain.protocols.physical_controls_protocol import PhysicalControlsProtocol
from app.src.config.button_actions_config import ButtonActionConfig

logger = logging.getLogger(__name__)


class PhysicalControlsFactory:
    """Factory for creating physical controls implementations."""

    @staticmethod
    def create_controls(
        hardware_config: Any,
        button_configs: Optional[List[ButtonActionConfig]] = None
    ) -> PhysicalControlsProtocol:
        """Create physical controls implementation based on environment.

        Args:
            hardware_config: Hardware configuration
            button_configs: Optional button configurations (uses DEFAULT_BUTTON_CONFIGS if None)

        Returns:
            PhysicalControlsProtocol implementation
        """
        # Check if mock hardware is requested
        use_mock = (
            os.getenv("USE_MOCK_HARDWARE", "false").lower() == "true" or
            hardware_config.mock_hardware
        )

        if use_mock:
            logger.info("🧪 Creating mock physical controls implementation")
            from app.src.infrastructure.hardware.controls.mock_controls_implementation import MockPhysicalControls
            return MockPhysicalControls(hardware_config, button_configs)
        else:
            logger.info("🔌 Creating GPIO physical controls implementation")
            from app.src.infrastructure.hardware.controls.gpio_controls_implementation import GPIOPhysicalControls
            return GPIOPhysicalControls(hardware_config, button_configs)

    @staticmethod
    def create_mock_controls(
        hardware_config: Any,
        button_configs: Optional[List[ButtonActionConfig]] = None
    ):
        """Create mock controls implementation for testing.

        Args:
            hardware_config: Hardware configuration
            button_configs: Optional button configurations (uses DEFAULT_BUTTON_CONFIGS if None)

        Returns:
            MockPhysicalControls implementation
        """
        logger.info("🧪 Creating mock physical controls for testing")
        from app.src.infrastructure.hardware.controls.mock_controls_implementation import MockPhysicalControls
        return MockPhysicalControls(hardware_config, button_configs)
