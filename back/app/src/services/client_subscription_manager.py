# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Client Subscription Manager

Manages client subscriptions to Socket.IO rooms and handles room-based message routing.
Extracted from StateManager for better separation of concerns.
"""

from typing import Dict, Set, Optional

from app.src.monitoring import get_logger

logger = get_logger(__name__)


class ClientSubscriptionManager:
    """
    Manages client subscriptions to Socket.IO rooms.

    Tracks which clients are subscribed to which rooms and provides
    utilities for subscription management and room operations.
    """

    def __init__(self, socketio_server=None):
        self.socketio = socketio_server
        self._client_subscriptions: Dict[str, Set[str]] = {}  # client_id -> {room_names}

        logger.info("ClientSubscriptionManager initialized")

    async def subscribe_client(self, client_id: str, room: str) -> None:
        """Subscribe a client to a specific room."""
        if client_id not in self._client_subscriptions:
            self._client_subscriptions[client_id] = set()

        self._client_subscriptions[client_id].add(room)

        if self.socketio:
            await self.socketio.enter_room(client_id, room)
            logger.info(f"Client {client_id} subscribed to room: {room}")

        return True

    async def unsubscribe_client(self, client_id: str, room: Optional[str] = None) -> None:
        """Unsubscribe a client from a room or all rooms."""
        if client_id not in self._client_subscriptions:
            return

        if room:
            # Unsubscribe from specific room
            self._client_subscriptions[client_id].discard(room)
            if self.socketio:
                await self.socketio.leave_room(client_id, room)
                logger.info(f"Client {client_id} unsubscribed from room: {room}")
        else:
            # Unsubscribe from all rooms
            for room_name in self._client_subscriptions[client_id].copy():
                if self.socketio:
                    await self.socketio.leave_room(client_id, room_name)
            self._client_subscriptions[client_id].clear()
            logger.info(f"Client {client_id} unsubscribed from all rooms")

    def get_client_subscriptions(self, client_id: str) -> Set[str]:
        """Get all rooms a client is subscribed to."""
        return self._client_subscriptions.get(client_id, set()).copy()

    def get_room_clients(self, room: str) -> Set[str]:
        """Get all clients subscribed to a specific room."""
        clients = set()
        for client_id, rooms in self._client_subscriptions.items():
            if room in rooms:
                clients.add(client_id)
        return clients

    def get_total_clients(self) -> int:
        """Get total number of clients with subscriptions."""
        return len(self._client_subscriptions)

    def get_total_subscriptions(self) -> int:
        """Get total number of room subscriptions across all clients."""
        return sum(len(rooms) for rooms in self._client_subscriptions.values())

    def is_client_subscribed(self, client_id: str, room: str) -> bool:
        """Check if a client is subscribed to a specific room."""
        return room in self._client_subscriptions.get(client_id, set())

    def cleanup_client(self, client_id: str) -> None:
        """Remove all subscriptions for a client (called on disconnect)."""
        if client_id in self._client_subscriptions:
            room_count = len(self._client_subscriptions[client_id])
            del self._client_subscriptions[client_id]
            logger.info(f"Cleaned up {room_count} subscriptions for client {client_id}"
            )

    def get_stats(self) -> dict:
        """Get subscription statistics for monitoring."""
        room_counts = {}
        for client_id, rooms in self._client_subscriptions.items():
            for room in rooms:
                room_counts[room] = room_counts.get(room, 0) + 1

        return {
            "total_clients": self.get_total_clients(),
            "total_subscriptions": self.get_total_subscriptions(),
            "room_client_counts": room_counts,
            "rooms": list(room_counts.keys()),
            "clients_with_subscriptions": list(self._client_subscriptions.keys()),
        }

    def get_room_list(self) -> Set[str]:
        """Get list of all active rooms."""
        rooms = set()
        for room_set in self._client_subscriptions.values():
            rooms.update(room_set)
        return rooms
