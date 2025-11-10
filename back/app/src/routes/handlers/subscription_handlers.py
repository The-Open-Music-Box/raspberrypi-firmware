# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Subscription Handlers for WebSocket Events

This module handles client subscription management for:
- Global playlists room
- Individual playlist rooms
- NFC association session rooms
"""

from typing import Dict, Any

import socketio

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.domain.audio.engine.state_manager import StateManager
from app.src.common.socket_rooms import SocketRooms

logger = get_logger(__name__)


class SubscriptionHandlers:
    """Handles WebSocket room subscription and unsubscription events.

    This handler manages client subscriptions to various rooms:
    - 'playlists': Global playlist list updates
    - 'playlist:{id}': Individual playlist state updates
    - 'nfc:{assoc_id}': NFC association session updates

    Each subscription includes sending an initial state snapshot to ensure
    clients have current data immediately upon joining.
    """

    def __init__(
        self,
        sio: socketio.AsyncServer,
        state_manager: StateManager,
        nfc_service: Any,
    ):
        """Initialize the subscription handlers.

        Args:
            sio: The Socket.IO server instance for event registration
            state_manager: The state manager for room subscriptions and snapshots
            nfc_service: The NFC application service for session snapshots
        """
        self.sio = sio
        self.state_manager = state_manager
        self.nfc_service = nfc_service

    def register(self) -> None:
        """Register all subscription-related event handlers.

        This method registers handlers for:
        - 'join:playlists': Subscribe to global playlist updates
        - 'join:playlist': Subscribe to specific playlist updates
        - 'leave:playlists': Unsubscribe from global playlist updates
        - 'leave:playlist': Unsubscribe from specific playlist updates
        - 'join:nfc': Subscribe to NFC association session updates
        """

        @self.sio.on("join:playlists")
        @handle_http_errors()
        async def handle_join_playlists(sid: str, data: Dict[str, Any]) -> None:
            """Subscribe client to global playlists state updates.

            When a client joins the 'playlists' room, they receive:
            1. An initial snapshot of all playlists
            2. Subsequent updates when playlists are created/deleted/modified
            3. An acknowledgment with the current server sequence number

            Args:
                sid: The Socket.IO session identifier for the subscribing client
                data: The request payload (currently unused for playlists subscription)

            Side Effects:
                - Adds client to 'playlists' room
                - Sends initial state snapshot via StateManager
                - Emits 'ack:join' acknowledgment to client
                - Logs subscription at INFO level
            """
            logger.info(f"Client {sid} joining playlists room")
            await self.state_manager.subscribe_client(sid, SocketRooms.PLAYLISTS)

            # Snapshot is sent by StateManager.subscribe_client via _send_state_snapshot
            # Send acknowledgment
            await self.sio.emit(
                "ack:join",
                {
                    "room": SocketRooms.PLAYLISTS,
                    "success": True,
                    "server_seq": self.state_manager.get_global_sequence(),
                },
                room=sid,
            )
            logger.info(
                f"Client {sid} subscribed to playlists; snapshot will be sent by StateManager"
            )

        @self.sio.on("join:playlist")
        @handle_http_errors()
        async def handle_join_playlist(sid: str, data: Dict[str, Any]) -> None:
            """Subscribe client to specific playlist state updates.

            When a client joins a playlist-specific room, they receive:
            1. An initial snapshot of the playlist state
            2. Subsequent updates when the playlist is modified
            3. An acknowledgment with the playlist sequence number

            Args:
                sid: The Socket.IO session identifier for the subscribing client
                data: The request payload containing 'playlist_id'

            Raises:
                ValueError: If 'playlist_id' is not provided in data

            Side Effects:
                - Adds client to 'playlist:{playlist_id}' room
                - Sends initial state snapshot via StateManager
                - Emits 'ack:join' acknowledgment to client
                - Logs subscription at INFO level
            """
            playlist_id = data.get("playlist_id")
            if not playlist_id:
                raise ValueError("playlist_id is required")

            room = SocketRooms.playlist(playlist_id)
            logger.info(f"Client {sid} joining playlist room: {room}")
            await self.state_manager.subscribe_client(sid, room)

            # Send acknowledgment
            await self.sio.emit(
                "ack:join",
                {
                    "room": room,
                    "playlist_id": playlist_id,
                    "success": True,
                    "playlist_seq": self.state_manager.get_playlist_sequence(
                        playlist_id
                    ),
                },
                room=sid,
            )

        @self.sio.on("leave:playlists")
        @handle_http_errors()
        async def handle_leave_playlists(sid: str, data: Dict[str, Any]) -> None:
            """Unsubscribe client from global playlists updates.

            Args:
                sid: The Socket.IO session identifier for the unsubscribing client
                data: The request payload (currently unused)

            Side Effects:
                - Removes client from 'playlists' room
                - Emits 'ack:leave' acknowledgment to client
                - Logs unsubscription at INFO level
            """
            logger.info(f"Client {sid} leaving playlists room")
            await self.state_manager.unsubscribe_client(sid, SocketRooms.PLAYLISTS)
            await self.sio.emit(
                "ack:leave", {"room": SocketRooms.PLAYLISTS, "success": True}, room=sid
            )

        @self.sio.on("leave:playlist")
        @handle_http_errors()
        async def handle_leave_playlist(sid: str, data: Dict[str, Any]) -> None:
            """Unsubscribe client from specific playlist updates.

            Args:
                sid: The Socket.IO session identifier for the unsubscribing client
                data: The request payload containing 'playlist_id'

            Raises:
                ValueError: If 'playlist_id' is not provided in data

            Side Effects:
                - Removes client from 'playlist:{playlist_id}' room
                - Emits 'ack:leave' acknowledgment to client
                - Logs unsubscription at INFO level
            """
            playlist_id = data.get("playlist_id")
            if not playlist_id:
                raise ValueError("playlist_id is required")

            room = SocketRooms.playlist(playlist_id)
            logger.info(f"Client {sid} leaving playlist room: {room}")
            await self.state_manager.unsubscribe_client(sid, room)
            await self.sio.emit(
                "ack:leave",
                {"room": room, "playlist_id": playlist_id, "success": True},
                room=sid,
            )

        @self.sio.on("join:nfc")
        @handle_http_errors()
        async def handle_join_nfc(sid: str, data: Dict[str, Any]) -> None:
            """Subscribe client to NFC association session room and send snapshot.

            When a client joins an NFC association session room, they receive:
            1. An initial snapshot of the association session state
            2. Subsequent updates as the NFC association progresses
            3. An acknowledgment with the current server sequence number

            Args:
                sid: The Socket.IO session identifier for the subscribing client
                data: The request payload containing 'assoc_id' (association ID)

            Raises:
                ValueError: If 'assoc_id' is not provided in data

            Side Effects:
                - Adds client to 'nfc:{assoc_id}' room
                - Fetches and emits current NFC session snapshot if available
                - Emits 'ack:join' acknowledgment to client
                - Logs subscription at INFO level
            """
            assoc_id = data.get("assoc_id")
            if not assoc_id:
                raise ValueError("assoc_id is required")

            room = SocketRooms.nfc(assoc_id)
            logger.info(f"Client {sid} joining NFC room: {room}")
            await self.state_manager.subscribe_client(sid, room)

            # Send current snapshot
            if self.nfc_service and hasattr(self.nfc_service, "get_session_snapshot"):
                snapshot = await self.nfc_service.get_session_snapshot(assoc_id)
                if snapshot:
                    # Ensure server_seq is included in snapshot
                    if "server_seq" not in snapshot:
                        snapshot["server_seq"] = (
                            self.state_manager.get_global_sequence()
                        )
                    await self.sio.emit("nfc_status", snapshot, room=sid)

            # Ack join - add server_seq to acknowledgment
            await self.sio.emit(
                "ack:join",
                {
                    "room": room,
                    "success": True,
                    "server_seq": self.state_manager.get_global_sequence(),
                },
                room=sid,
            )
