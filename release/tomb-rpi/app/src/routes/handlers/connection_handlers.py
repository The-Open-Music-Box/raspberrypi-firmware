# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Connection Handlers for WebSocket Events

This module handles client connection lifecycle events including:
- Initial connection establishment
- Connection acknowledgment
- Disconnection and cleanup
"""

import time
from typing import Dict, Any

import socketio

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.domain.audio.engine.state_manager import StateManager

logger = get_logger(__name__)


class ConnectionHandlers:
    """Handles WebSocket client connection lifecycle events.

    This handler is responsible for:
    - Sending connection acknowledgments with server state
    - Cleaning up subscriptions on disconnection
    - Maintaining connection health
    """

    def __init__(self, sio: socketio.AsyncServer, state_manager: StateManager):
        """Initialize the connection handlers.

        Args:
            sio: The Socket.IO server instance for event registration
            state_manager: The state manager for tracking global sequence numbers
        """
        self.sio = sio
        self.state_manager = state_manager

    def register(self) -> None:
        """Register all connection-related event handlers.

        This method registers handlers for:
        - 'connect': Initial client connection
        - 'disconnect': Client disconnection and cleanup
        """

        @self.sio.event
        @handle_http_errors()
        async def connect(sid: str, environ: Dict[str, Any]) -> None:
            """Handle client connection and send initial state sync.

            When a client connects, this handler:
            1. Logs the connection event
            2. Sends a connection_status acknowledgment with server metadata
            3. Includes current server sequence number for state synchronization

            Args:
                sid: The Socket.IO session identifier for the connected client
                environ: The WSGI environment dictionary containing connection metadata

            Side Effects:
                - Emits 'connection_status' event to the connected client
                - Logs connection event at INFO level
            """
            logger.info(f"Client connected: {sid}")

            # Send connection acknowledgment with proper error handling
            await self.sio.emit(
                "connection_status",
                {
                    "status": "connected",
                    "sid": sid,
                    "server_seq": self.state_manager.get_global_sequence(),
                    "server_time": time.time(),
                },
                room=sid,
            )

        @self.sio.event
        async def disconnect(sid: str) -> None:
            """Handle client disconnection and cleanup subscriptions.

            When a client disconnects (intentionally or due to network issues), this handler:
            1. Logs the disconnection event
            2. Unsubscribes the client from all rooms
            3. Performs any necessary cleanup

            Args:
                sid: The Socket.IO session identifier for the disconnected client

            Side Effects:
                - Removes client from all subscribed rooms
                - Cleans up state manager's client tracking
                - Logs disconnection event at INFO level
            """
            logger.info(f"Client disconnected: {sid}")

            # Unsubscribe client from all rooms
            await self.state_manager.unsubscribe_client(sid)
