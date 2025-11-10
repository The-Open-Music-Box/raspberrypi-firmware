# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Sync Handlers for WebSocket Events

This module handles state synchronization and connection health:
- Client state synchronization requests
- Connection health monitoring (ping/pong)
- Health check requests
- Full state resynchronization
"""

import time
from typing import Dict, Any, Optional

import socketio

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.domain.audio.engine.state_manager import StateManager

logger = get_logger(__name__)


class SyncHandlers:
    """Handles WebSocket state synchronization and health monitoring events.

    This handler manages:
    - Client synchronization requests (when clients detect they're out of sync)
    - Current player state requests (post-connection sync)
    - Connection health monitoring (ping/pong)
    - System health checks
    """

    def __init__(
        self,
        sio: socketio.AsyncServer,
        state_manager: StateManager,
        playback_coordinator: Any,
        player_state_service: Any,
    ):
        """Initialize the sync handlers.

        Args:
            sio: The Socket.IO server instance for event registration
            state_manager: The state manager for synchronization operations
            playback_coordinator: The playback coordinator for player state
            player_state_service: The player state service for building state
        """
        self.sio = sio
        self.state_manager = state_manager
        self.playback_coordinator = playback_coordinator
        self.player_state_service = player_state_service

    def register(self) -> None:
        """Register all synchronization and health-related event handlers.

        This method registers handlers for:
        - 'sync:request': Client-initiated state synchronization
        - 'client:request_current_state': Post-connection player state sync
        - 'client_ping': Connection health monitoring
        - 'health_check': System health status request
        """

        @self.sio.on("sync:request")
        @handle_http_errors()
        async def handle_sync_request(sid: str, data: Dict[str, Any]) -> None:
            """Handle client request for state synchronization.

            When a client detects it may be out of sync (missed updates, reconnection, etc.),
            it can request a full resync. The server compares sequence numbers and resends
            any state snapshots as needed.

            Args:
                sid: The Socket.IO session identifier for the requesting client
                data: The request payload containing:
                    - last_global_seq: Client's last known global sequence number
                    - last_playlist_seqs: Dict of playlist_id -> last known sequence

            Side Effects:
                - Resends state snapshots for subscribed rooms if client is behind
                - Emits 'sync:complete' acknowledgment with current sequence numbers
                - Logs synchronization at INFO level
            """
            # Get client's last known sequence numbers
            last_global_seq = data.get("last_global_seq", 0)
            last_playlist_seqs = data.get("last_playlist_seqs", {})
            logger.info(f"Sync request from {sid}: global_seq={last_global_seq}")

            # Send current global state if client is behind
            current_global_seq = self.state_manager.get_global_sequence()
            if last_global_seq < current_global_seq:
                # Client needs full resync - send snapshots for subscribed rooms
                subscriptions = self.state_manager.get_client_subscriptions(sid)
                for room in subscriptions:
                    await self.state_manager._send_state_snapshot(sid, room)

            # Send sync acknowledgment
            await self.sio.emit(
                "sync:complete",
                {
                    "current_global_seq": current_global_seq,
                    "synced_rooms": list(
                        self.state_manager.get_client_subscriptions(sid)
                    ),
                },
                room=sid,
            )

        @self.sio.on("client:request_current_state")
        @handle_http_errors()
        async def handle_request_current_state(
            sid: str, data: Optional[Dict[str, Any]] = None
        ) -> None:
            """Handle client request for current player state synchronization.

            This is typically called after initial connection to get the current
            playback state. It builds the full player state and sends it to the
            requesting client.

            Args:
                sid: The Socket.IO session identifier for the requesting client
                data: Optional request payload (currently unused)

            Side Effects:
                - Builds current player state from playback coordinator
                - Emits 'state:player' event with current state
                - Logs synchronization at INFO level
                - Logs warnings/errors if state cannot be retrieved
            """
            logger.info(f"Client {sid} requesting current state sync")

            try:
                if self.playback_coordinator:
                    # Build current player state
                    player_state = await self.player_state_service.build_current_player_state(
                        self.playback_coordinator, self.state_manager
                    )

                    # Extract state data and metadata
                    state_data, server_seq, playlist_title = (
                        self._extract_player_state_info(player_state)
                    )

                    # Send current player state to requesting client
                    await self._emit_player_state(sid, state_data, server_seq)

                    logger.info(
                        f"Sent current player state to client {sid}: {playlist_title}"
                    )
                else:
                    logger.warning(
                        f"No playback coordinator available for state sync to {sid}"
                    )
            except Exception as e:
                logger.error(
                    f"Error getting playback coordinator for state sync to {sid}: {e}"
                )

        @self.sio.on("client_ping")
        @handle_http_errors()
        async def handle_client_ping(sid: str, data: Dict[str, Any]) -> None:
            """Handle client ping for connection health monitoring.

            Clients can periodically send pings to verify the connection is alive
            and measure round-trip latency. The server responds with a pong containing
            timestamps and the current sequence number.

            Args:
                sid: The Socket.IO session identifier for the pinging client
                data: The request payload containing:
                    - timestamp: Client's timestamp when ping was sent

            Side Effects:
                - Emits 'client_pong' response with timestamps and server_seq
            """
            await self.sio.emit(
                "client_pong",
                {
                    "timestamp": data.get("timestamp", time.time()),
                    "server_time": time.time(),
                    "server_seq": self.state_manager.get_global_sequence(),
                },
                room=sid,
            )

        @self.sio.on("health_check")
        @handle_http_errors()
        async def handle_health_check(sid: str, data: Dict[str, Any]) -> None:
            """Handle client health check request.

            Provides comprehensive system health metrics including state manager
            statistics and connection counts.

            Args:
                sid: The Socket.IO session identifier for the requesting client
                data: The request payload (currently unused)

            Side Effects:
                - Retrieves health metrics from state manager
                - Adds connected client count
                - Emits 'health_status' event with all metrics
            """
            health_metrics = await self.state_manager.get_health_metrics()
            health_metrics.update(
                {
                    "connected_clients": len(
                        self.sio.manager.rooms.get("/", {})
                    ),
                    "server_time": time.time(),
                }
            )
            await self.sio.emit("health_status", health_metrics, room=sid)

    def _extract_player_state_info(
        self, player_state: Any
    ) -> tuple[Dict[str, Any], int, str]:
        """Extract state data from PlayerStateModel or dict.

        Args:
            player_state: Either a PlayerStateModel instance or a dict

        Returns:
            Tuple of (state_data_dict, server_seq, playlist_title)
        """
        # Handle both PlayerStateModel and dict returns
        if hasattr(player_state, "server_seq"):
            # PlayerStateModel case
            server_seq = player_state.server_seq
            data = player_state.model_dump()
            playlist_title = getattr(player_state, "active_playlist_title", None)
        else:
            # dict case (fallback scenario)
            server_seq = player_state.get("server_seq", 0)
            data = player_state
            playlist_title = player_state.get("active_playlist_title", "None")

        return data, server_seq, playlist_title or "None"

    async def _emit_player_state(
        self, sid: str, state_data: Dict[str, Any], server_seq: int
    ) -> None:
        """Emit player state event to client.

        Args:
            sid: The client session identifier
            state_data: The player state data dictionary
            server_seq: The current server sequence number

        Side Effects:
            - Emits 'state:player' event with envelope format
        """
        await self.sio.emit(
            "state:player",
            {
                "event_type": "state:player",
                "server_seq": server_seq,
                "data": state_data,
                "timestamp": time.time(),
                "event_id": f"sync_{int(time.time() * 1000)}",
            },
            room=sid,
        )
