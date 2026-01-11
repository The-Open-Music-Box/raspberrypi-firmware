# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Jack Detection Protocol for Domain Layer.

Defines the interface for headphone jack detection hardware
that monitors plug/unplug events to control audio routing.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum


class JackState(Enum):
    """Headphone jack connection states."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    UNKNOWN = "unknown"


class JackDetectionProtocol(ABC):
    """Protocol for headphone jack detection hardware."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize jack detection hardware.

        Returns:
            True if initialization was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up jack detection resources."""
        pass

    @abstractmethod
    def get_state(self) -> JackState:
        """Get current jack connection state.

        Returns:
            Current JackState (CONNECTED, DISCONNECTED, or UNKNOWN).
        """
        pass

    @abstractmethod
    def is_headphone_connected(self) -> bool:
        """Check if headphones are currently connected.

        Returns:
            True if headphones are connected, False otherwise.
        """
        pass

    @abstractmethod
    def set_state_change_handler(
        self, handler: Callable[[JackState], None]
    ) -> None:
        """Set callback handler for jack state changes.

        Args:
            handler: Callback function that receives the new JackState
                     when a plug/unplug event occurs.
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if jack detection is enabled.

        Returns:
            True if jack detection feature is enabled, False otherwise.
        """
        pass

    @abstractmethod
    def get_status(self) -> dict:
        """Get current status of jack detection hardware.

        Returns:
            Dictionary containing status information including:
            - enabled: bool
            - initialized: bool
            - state: JackState value
            - gpio_pin: int (if applicable)
        """
        pass
