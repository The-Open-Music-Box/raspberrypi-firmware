# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Mock Jack Detection Implementation.

Mock implementation for testing and development without hardware.
"""

from app.src.domain.protocols.jack_detection_protocol import JackState
from app.src.monitoring import get_logger

from .base_jack_detection import BaseJackDetection

logger = get_logger(__name__)


class MockJackDetection(BaseJackDetection):
    """Mock jack detection for testing and development.

    Provides a simulated jack detection interface that can be
    programmatically controlled for testing purposes.
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialize mock jack detection.

        Args:
            enabled: Whether jack detection is enabled.
        """
        super().__init__(enabled=enabled)
        self._simulated_connected = False

    async def initialize(self) -> bool:
        """Initialize mock jack detection.

        Returns:
            True (always succeeds for mock).
        """
        self._initialized = True
        self._state = JackState.DISCONNECTED
        logger.info("Mock jack detection initialized")
        return True

    async def cleanup(self) -> None:
        """Clean up mock jack detection resources."""
        self._initialized = False
        self._state = JackState.UNKNOWN
        logger.debug("Mock jack detection cleaned up")

    def simulate_connect(self) -> None:
        """Simulate headphone connection (for testing).

        This method allows tests to simulate a headphone plug event.
        """
        if not self._enabled:
            logger.warning("Cannot simulate connect: jack detection disabled")
            return

        self._simulated_connected = True
        self._update_state(JackState.CONNECTED)
        logger.debug("Mock: Simulated headphone connection")

    def simulate_disconnect(self) -> None:
        """Simulate headphone disconnection (for testing).

        This method allows tests to simulate a headphone unplug event.
        """
        if not self._enabled:
            logger.warning("Cannot simulate disconnect: jack detection disabled")
            return

        self._simulated_connected = False
        self._update_state(JackState.DISCONNECTED)
        logger.debug("Mock: Simulated headphone disconnection")

    def get_status(self) -> dict:
        """Get current status of mock jack detection.

        Returns:
            Dictionary containing status information.
        """
        status = super().get_status()
        status.update({
            "implementation": "mock",
            "simulated_connected": self._simulated_connected,
        })
        return status
