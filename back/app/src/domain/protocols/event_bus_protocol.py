# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Event bus protocol for domain events."""

from typing import Protocol, Any, Callable
from abc import abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AudioEvent:
    """Base class for all audio domain events."""

    def __init__(self, source_component: str):
        self.source_component = source_component
        self.timestamp = datetime.now()


class EventBusProtocol(Protocol):
    """Protocol for event bus operations.

    Handles domain events and notifications.
    """

    @abstractmethod
    async def publish(self, event_type: str, event_data: Any) -> None:
        """Publish an event.

        Args:
            event_type: Type of the event
            event_data: Event payload
        """
        ...

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Event handler function
        """
        ...

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from an event type.

        Args:
            event_type: Type of event to unsubscribe from
            handler: Event handler function to remove
        """
        ...