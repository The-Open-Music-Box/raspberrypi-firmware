# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock controls manager for testing.

This module provides a mock implementation of the physical controls manager
for testing purposes without requiring actual hardware components.
"""

from typing import Callable, Dict, List

from app.src.enums.control_event_type import ControlEventType


class MockControlsManager:
    """Mock physical controls manager implementation for testing.

    Simulates physical control events without actual hardware dependencies,
    enabling comprehensive testing of control-related functionality.
    """

    def __init__(self):
        """Initialize the mock controls manager."""
        self._is_initialized = False
        self._event_handlers: Dict[ControlEventType, List[Callable]] = {}
        self._simulated_events: List[ControlEventType] = []

    def initialize(self) -> bool:
        """Initialize the controls manager.

        Returns:
            True if initialization was successful, False otherwise
        """
        self._is_initialized = True
        return True

    def subscribe_to_event(self, event_type: ControlEventType, handler: Callable):
        """Subscribe to a control event type.

        Args:
            event_type: Type of control event to subscribe to
            handler: Callback function to handle the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    def unsubscribe_from_event(self, event_type: ControlEventType, handler: Callable):
        """Unsubscribe from a control event type.

        Args:
            event_type: Type of control event to unsubscribe from
            handler: Callback function to remove
        """
        if event_type in self._event_handlers:
            try:
                self._event_handlers[event_type].remove(handler)
            except ValueError:
                pass  # Handler not found

    def is_initialized(self) -> bool:
        """Check if the controls manager is initialized.

        Returns:
            True if initialized, False otherwise
        """
        return self._is_initialized

    def cleanup(self):
        """Clean up resources and stop monitoring."""
        self._is_initialized = False
        self._event_handlers.clear()
        self._simulated_events.clear()

    # Mock-specific methods for testing
    def simulate_event(self, event_type: ControlEventType):
        """Simulate a control event for testing.

        Args:
            event_type: Type of control event to simulate
        """
        self._simulated_events.append(event_type)

        # Trigger registered handlers
        if event_type in self._event_handlers:
            for handler in self._event_handlers[event_type]:
                try:
                    handler(event_type)
                except Exception:
                    pass  # Ignore handler errors in mock

    def simulate_volume_up(self):
        """Simulate a volume up event."""
        self.simulate_event(ControlEventType.VOLUME_UP)

    def simulate_volume_down(self):
        """Simulate a volume down event."""
        self.simulate_event(ControlEventType.VOLUME_DOWN)

    def simulate_play_pause(self):
        """Simulate a play/pause event."""
        self.simulate_event(ControlEventType.PLAY_PAUSE)

    def simulate_next_track(self):
        """Simulate a next track event."""
        self.simulate_event(ControlEventType.NEXT_TRACK)

    def simulate_previous_track(self):
        """Simulate a previous track event."""
        self.simulate_event(ControlEventType.PREVIOUS_TRACK)

    def get_simulated_events(self) -> List[ControlEventType]:
        """Get the list of simulated events.

        Returns:
            List of simulated control events
        """
        return self._simulated_events.copy()

    def clear_simulated_events(self):
        """Clear the list of simulated events."""
        self._simulated_events.clear()

    def get_event_handler_count(self, event_type: ControlEventType) -> int:
        """Get the number of handlers for an event type.

        Args:
            event_type: Type of control event

        Returns:
            Number of registered handlers
        """
        return len(self._event_handlers.get(event_type, []))

    def has_handlers(self) -> bool:
        """Check if any event handlers are registered.

        Returns:
            True if handlers are registered, False otherwise
        """
        return any(handlers for handlers in self._event_handlers.values())

    def reset(self):
        """Reset the mock controls manager to initial state."""
        self._is_initialized = False
        self._event_handlers.clear()
        self._simulated_events.clear()
