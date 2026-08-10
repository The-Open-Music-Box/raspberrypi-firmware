# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Jack Detection Factory.

Factory for creating jack detection implementations based on configuration.
"""

import os

from app.src.config.hardware_config import HardwareConfig
from app.src.domain.protocols.jack_detection_protocol import JackDetectionProtocol
from app.src.monitoring import get_logger

from .gpio_jack_detection import GPIOJackDetection
from .mock_jack_detection import MockJackDetection

logger = get_logger(__name__)


class JackDetectionFactory:
    """Factory for creating jack detection implementations."""

    @staticmethod
    def create(hardware_config: HardwareConfig) -> JackDetectionProtocol:
        """Create appropriate jack detection implementation.

        Args:
            hardware_config: Hardware configuration.

        Returns:
            JackDetectionProtocol implementation (GPIO or Mock).
        """
        # Check if mock hardware is requested
        use_mock = (
            hardware_config.mock_hardware
            or os.getenv("USE_MOCK_HARDWARE", "false").lower() == "true"
        )

        # Check if jack detection is disabled
        if not hardware_config.headphone_detect_enabled:
            logger.info("Jack detection disabled in configuration, using mock")
            return MockJackDetection(enabled=False)

        if use_mock:
            logger.info("Using mock jack detection (mock hardware mode)")
            return MockJackDetection(enabled=True)

        logger.info("Using GPIO jack detection")
        return GPIOJackDetection(hardware_config)
