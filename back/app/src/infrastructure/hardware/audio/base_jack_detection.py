# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Base Jack Detection Implementation.

Provides common functionality for jack detection implementations.
"""

from collections.abc import Callable
from threading import Lock

from app.src.domain.protocols.jack_detection_protocol import (
    JackDetectionProtocol,
    JackState,
)
from app.src.monitoring import get_logger

logger = get_logger(__name__)


class BaseJackDetection(JackDetectionProtocol):
    """Base class for jack detection implementations.

    Provides common state management and callback handling.
    """

    def __init__(self, enabled: bool = True) -> None:
        """Initialize base jack detection.

        Args:
            enabled: Whether jack detection is enabled.
        """
        self._enabled = enabled
        self._initialized = False
        self._state = JackState.UNKNOWN
        self._state_change_handler: Callable[[JackState], None] | None = None
        self._lock = Lock()

    def is_enabled(self) -> bool:
        """Check if jack detection is enabled.

        Returns:
            True if jack detection feature is enabled.
        """
        return self._enabled

    def get_state(self) -> JackState:
        """Get current jack connection state.

        Returns:
            Current JackState.
        """
        with self._lock:
            return self._state

    def is_headphone_connected(self) -> bool:
        """Check if headphones are currently connected.

        Returns:
            True if headphones are connected.
        """
        return self.get_state() == JackState.CONNECTED

    def set_state_change_handler(
        self, handler: Callable[[JackState], None]
    ) -> None:
        """Set callback handler for jack state changes.

        Args:
            handler: Callback function that receives the new JackState.
        """
        with self._lock:
            self._state_change_handler = handler
            logger.debug("Jack detection state change handler registered")

    def _update_state(self, new_state: JackState) -> None:
        """Update jack state and notify handler if changed.

        Args:
            new_state: The new jack state.
        """
        with self._lock:
            if self._state != new_state:
                old_state = self._state
                self._state = new_state
                logger.info(
                    f"Jack state changed: {old_state.value} -> {new_state.value}"
                )

                # Call handler outside lock to prevent deadlocks
                handler = self._state_change_handler

        # Notify handler if state changed
        if handler is not None and old_state != new_state:
            try:
                handler(new_state)
            except Exception as e:
                logger.error(f"Error in jack state change handler: {e}")

    def get_status(self) -> dict:
        """Get current status of jack detection.

        Returns:
            Dictionary containing status information.
        """
        with self._lock:
            return {
                "enabled": self._enabled,
                "initialized": self._initialized,
                "state": self._state.value,
                "has_handler": self._state_change_handler is not None,
            }

    async def initialize(self) -> bool:
        """Initialize jack detection (to be overridden).

        Returns:
            True if initialization was successful.
        """
        raise NotImplementedError("Subclasses must implement initialize()")

    async def cleanup(self) -> None:
        """Clean up jack detection resources (to be overridden)."""
        raise NotImplementedError("Subclasses must implement cleanup()")
