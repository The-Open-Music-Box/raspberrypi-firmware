# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock StateManager for testing.

This module provides a mock implementation of the StateManager
for testing state broadcasting and event handling without WebSocket dependencies.
"""

import asyncio
from typing import Any, Dict, List, Optional, Callable


class MockStateManager:
    """Mock StateManager implementation for testing.

    Simulates state broadcasting and client acknowledgments without actual
    WebSocket connections, enabling comprehensive testing of state management.
    """

    def __init__(self):
        """Initialize the mock state manager."""
        self._global_sequence = 1000
        self._broadcasted_events: List[Dict[str, Any]] = []
        self._acknowledgments: List[Dict[str, Any]] = []
        self._subscribers: List[Callable] = []
        self._client_operations: Dict[str, Dict[str, Any]] = {}
        self._current_playlist: Optional[Dict[str, Any]] = None
        self._current_track_number: Optional[int] = None

    async def broadcast_state_change(self, event_type: str, data: Dict[str, Any]) -> None:
        """Mock state change broadcasting.

        Args:
            event_type: Type of state event
            data: Event data to broadcast
        """
        event = {
            "event_type": event_type,
            "data": data,
            "sequence": self._global_sequence,
            "timestamp": "2025-01-27T12:00:00Z",
        }
        self._broadcasted_events.append(event)
        self._global_sequence += 1

        # Notify subscribers
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(event)
                else:
                    subscriber(event)
            except Exception:
                pass  # Ignore subscriber errors in tests

    async def send_acknowledgment(
        self, client_op_id: str, success: bool, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mock client operation acknowledgment.

        Args:
            client_op_id: Client operation identifier
            success: Whether the operation succeeded
            data: Optional response data
        """
        ack = {
            "client_op_id": client_op_id,
            "success": success,
            "data": data or {},
            "sequence": self._global_sequence,
            "timestamp": "2025-01-27T12:00:00Z",
        }
        self._acknowledgments.append(ack)
        self._client_operations[client_op_id] = ack
        self._global_sequence += 1

    def get_global_sequence(self) -> int:
        """Get the current global sequence number.

        Returns:
            Current global sequence number
        """
        return self._global_sequence

    async def start_cleanup_task(self) -> None:
        """Mock cleanup task start."""
        pass  # No-op for testing

    async def process_outbox(self) -> None:
        """Mock outbox processing - events are processed immediately in mock."""
        # In the real StateManager, this processes the outbox queue
        # In the mock, events are already "processed" when broadcast_state_change is called
        # This method exists to prevent AttributeError in tests
        pass

    def subscribe_to_events(self, callback: Callable) -> None:
        """Subscribe to state events.

        Args:
            callback: Function to call when events are broadcast
        """
        self._subscribers.append(callback)

    def unsubscribe_from_events(self, callback: Callable) -> None:
        """Unsubscribe from state events.

        Args:
            callback: Function to remove from subscribers
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    # Mock-specific testing methods
    def get_broadcasted_events(self) -> List[Dict[str, Any]]:
        """Get all broadcasted events for testing.

        Returns:
            List of all broadcasted events
        """
        return self._broadcasted_events.copy()

    def get_acknowledgments(self) -> List[Dict[str, Any]]:
        """Get all acknowledgments for testing.

        Returns:
            List of all acknowledgments sent
        """
        return self._acknowledgments.copy()

    def get_last_event(self) -> Optional[Dict[str, Any]]:
        """Get the most recent broadcasted event.

        Returns:
            Most recent event or None if no events
        """
        return self._broadcasted_events[-1] if self._broadcasted_events else None

    def get_last_acknowledgment(self) -> Optional[Dict[str, Any]]:
        """Get the most recent acknowledgment.

        Returns:
            Most recent acknowledgment or None if no acknowledgments
        """
        return self._acknowledgments[-1] if self._acknowledgments else None

    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """Get all events of a specific type.

        Args:
            event_type: Type of events to filter by

        Returns:
            List of events matching the type
        """
        return [
            event for event in self._broadcasted_events if event.get("event_type") == event_type
        ]

    def get_client_operation(self, client_op_id: str) -> Optional[Dict[str, Any]]:
        """Get acknowledgment for a specific client operation.

        Args:
            client_op_id: Client operation identifier

        Returns:
            Acknowledgment data or None if not found
        """
        return self._client_operations.get(client_op_id)

    def has_broadcasted_event(
        self, event_type: str, data_contains: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Check if a specific event was broadcasted.

        Args:
            event_type: Type of event to check for
            data_contains: Optional data that should be present in the event

        Returns:
            True if event was found, False otherwise
        """
        for event in self._broadcasted_events:
            if event.get("event_type") == event_type:
                if data_contains is None:
                    return True

                event_data = event.get("data", {})
                if all(
                    key in event_data and event_data[key] == value
                    for key, value in data_contains.items()
                ):
                    return True
        return False

    def clear_events(self):
        """Clear all recorded events and acknowledgments."""
        self._broadcasted_events.clear()
        self._acknowledgments.clear()
        self._client_operations.clear()

    def set_global_sequence(self, sequence: int):
        """Set the global sequence number for testing.

        Args:
            sequence: Sequence number to set
        """
        self._global_sequence = sequence

    def reset(self):
        """Reset the mock state manager to initial state."""
        self._global_sequence = 1000
        self._broadcasted_events.clear()
        self._acknowledgments.clear()
        self._subscribers.clear()
        self._client_operations.clear()
        self._current_playlist = None
        self._current_track_number = None

    def get_current_playlist(self) -> Optional[Dict[str, Any]]:
        """Get current playlist information.

        Returns:
            Current playlist data or None if no playlist is loaded
        """
        return self._current_playlist

    def set_current_playlist(self, playlist: Optional[Dict[str, Any]]) -> None:
        """Set current playlist information.

        Args:
            playlist: Playlist data to set as current
        """
        self._current_playlist = playlist

    def get_current_track_number(self) -> Optional[int]:
        """Get current track number in playlist.

        Returns:
            Current track number (1-based) or None if no track is playing
        """
        return self._current_track_number

    def set_current_track_number(self, track_number: Optional[int]) -> None:
        """Set current track number in playlist.

        Args:
            track_number: Track number to set (1-based)
        """
        self._current_track_number = track_number
