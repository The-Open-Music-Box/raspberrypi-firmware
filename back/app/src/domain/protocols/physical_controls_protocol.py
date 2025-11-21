# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Physical Controls Protocol for Domain Layer.

Defines the interface for physical control devices (buttons, encoders)
that can trigger audio control actions.
"""

from abc import ABC, abstractmethod
from typing import Callable, Optional
from enum import Enum


class PhysicalControlEvent(Enum):
    """Types of physical control events."""
    BUTTON_NEXT_TRACK = "button_next_track"
    BUTTON_PREVIOUS_TRACK = "button_previous_track"
    BUTTON_PLAY_PAUSE = "button_play_pause"
    ENCODER_VOLUME_UP = "encoder_volume_up"
    ENCODER_VOLUME_DOWN = "encoder_volume_down"


class PhysicalControlsProtocol(ABC):
    """Protocol for physical control device management."""

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize physical control devices.

        Returns:
            True if initialization was successful, False otherwise.
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up physical control resources."""
        pass

    @abstractmethod
    def set_event_handler(self, event_type: PhysicalControlEvent, handler: Callable[[], None]) -> None:
        """Set event handler for a specific control event.

        Args:
            event_type: Type of control event
            handler: Callback function to handle the event
        """
        pass

    @abstractmethod
    def is_initialized(self) -> bool:
        """Check if physical controls are initialized and ready.

        Returns:
            True if controls are ready, False otherwise.
        """
        pass

    @abstractmethod
    def get_status(self) -> dict:
        """Get current status of physical controls.

        Returns:
            Dictionary containing status information.
        """
        pass