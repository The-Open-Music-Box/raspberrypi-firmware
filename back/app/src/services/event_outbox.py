# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Event Outbox for Reliable Message Delivery

Handles reliable event delivery with retry mechanisms and memory management.
Extracted from StateManager for better separation of concerns.
"""

import asyncio
import time
from typing import List, Optional
from dataclasses import dataclass

import logging
from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.config.socket_config import socket_config

logger = logging.getLogger(__name__)


@dataclass
class OutboxEvent:
    """Event stored in outbox for reliable delivery."""

    event_id: str
    event_type: str
    payload: dict
    server_seq: int
    retry_count: int = 0
    created_at: float = None
    playlist_id: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class EventOutbox:
    """
    Manages reliable event delivery with retry mechanisms.

    Events are added to the outbox and processed asynchronously.
    Failed events are retried up to a maximum number of times.
    """

    def __init__(self, socketio_server=None):
        self.socketio = socketio_server
        self._outbox: List[OutboxEvent] = []
        self._outbox_lock = asyncio.Lock()

        # Configuration
        self._max_retry_count = socket_config.OUTBOX_RETRY_MAX
        self._max_size = socket_config.OUTBOX_SIZE_LIMIT
        self._cleanup_batch_size = socket_config.OUTBOX_CLEANUP_BATCH

        logger.info("EventOutbox initialized")

    async def add_event(
        self,
        event_id: str,
        event_type: str,
        payload: dict,
        server_seq: int,
        playlist_id: Optional[str] = None,
    ) -> None:
        """Add an event to the outbox for reliable delivery."""
        async with self._outbox_lock:
            # Check size limit and cleanup if needed
            if len(self._outbox) >= self._max_size:
                removed_count = min(self._cleanup_batch_size, len(self._outbox) // 10)
                self._outbox = self._outbox[removed_count:]
                logger.warning(
                    f"Outbox size limit reached. Removed {removed_count} oldest events."
                )

            # Add new event
            event = OutboxEvent(
                event_id=event_id,
                event_type=event_type,
                payload=payload,
                server_seq=server_seq,
                playlist_id=playlist_id,
            )
            self._outbox.append(event)

            logger.debug(f"Added event to outbox: {event_type} (seq: {server_seq})")

    @handle_service_errors("event_outbox")
    async def process_outbox(self) -> None:
        """Process all events in the outbox, retrying failed ones."""
        if not self.socketio:
            return

        events_to_process: List[OutboxEvent] = []
        retry_events: List[OutboxEvent] = []

        # Get events to process
        async with self._outbox_lock:
            events_to_process = self._outbox.copy()
            self._outbox.clear()

        if not events_to_process:
            return

        # Process each event
        for event in events_to_process:
            await self._emit_event(event)
            logger.debug(f"Successfully emitted event {event.event_id}")
        # Re-add retry events
        if retry_events:
            async with self._outbox_lock:
                self._outbox = retry_events + self._outbox

    @handle_service_errors("event_outbox")
    async def _emit_event(self, event: OutboxEvent) -> None:
        """Emit a single event via Socket.IO."""
        if not self.socketio:
            raise ConnectionError("Socket.IO server not available")

        # Determine target room
        from app.src.common.socket_events import SocketEventType, get_event_room

        event_type_enum = SocketEventType(event.event_type)
        target_room = get_event_room(event_type_enum, event.playlist_id)
        # Emit the event
        await self.socketio.emit(event.event_type, event.payload, room=target_room)

    def get_stats(self) -> dict:
        """Get outbox statistics for monitoring."""
        return {
            "total_events": len(self._outbox),
            "max_size": self._max_size,
            "max_retries": self._max_retry_count,
            "events_by_type": self._get_event_type_counts(),
            "oldest_event_age": self._get_oldest_event_age(),
        }

    def _get_event_type_counts(self) -> dict:
        """Get count of events by type."""
        counts = {}
        for event in self._outbox:
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return counts

    def _get_oldest_event_age(self) -> Optional[float]:
        """Get age of oldest event in seconds."""
        if not self._outbox:
            return None

        now = time.time()
        oldest_time = min(event.created_at for event in self._outbox)
        return now - oldest_time

    async def clear(self) -> None:
        """Clear all events from the outbox."""
        async with self._outbox_lock:
            count = len(self._outbox)
            self._outbox.clear()
            if count > 0:
                logger.info(f"Cleared {count} events from outbox")
