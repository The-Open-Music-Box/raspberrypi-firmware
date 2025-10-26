# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Simple event bus implementation."""

import asyncio
from collections import defaultdict
from typing import Dict, List, Callable, Any, Type, TypeVar

from app.src.monitoring import get_logger
from app.src.domain.protocols.event_bus_protocol import EventBusProtocol, AudioEvent
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors

EventType = TypeVar("EventType", bound=AudioEvent)
logger = get_logger(__name__)


class EventBus(EventBusProtocol):
    """Simple event bus implementation for audio events."""

    def __init__(self):
        self._subscribers: Dict[Type, List[Callable]] = defaultdict(list)
        self._stats = {"events_published": 0, "events_handled": 0, "errors": 0}

    def subscribe(self, event_type: Type[EventType], handler: Callable[[EventType], Any]) -> None:
        """Subscribe to an event type."""
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type.__name__}: {handler.__name__}")

    def unsubscribe(self, event_type: Type[EventType], handler: Callable[[EventType], Any]) -> None:
        """Unsubscribe from an event type."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed from {event_type.__name__}: {handler.__name__}"
            )

    @handle_errors("publish")
    async def publish(self, event: EventType) -> None:
        """Publish an event to all subscribers."""
        event_type = type(event)
        subscribers = self._subscribers.get(event_type, [])

        if not subscribers:
            logger.debug(f"No subscribers for {event_type.__name__}")
            return

        self._stats["events_published"] += 1

        # Handle each subscriber
        for handler in subscribers:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
            self._stats["events_handled"] += 1
        logger.debug(f"Published {event_type.__name__} to {len(subscribers)} subscribers"
        )

    def get_subscriber_count(self, event_type: Type[EventType]) -> int:
        """Get number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics."""
        return {
            **self._stats,
            "subscriber_counts": {
                event_type.__name__: len(handlers)
                for event_type, handlers in self._subscribers.items()
            },
        }
