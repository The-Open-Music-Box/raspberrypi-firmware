# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Server-Authoritative WebSocket Handlers

This module implements WebSocket event handlers for the server-authoritative
state management system. Clients can subscribe to state updates and send
commands, but never maintain authoritative state.
"""

import time

import socketio

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.domain.audio.engine.state_manager import StateManager

logger = get_logger(__name__)


class WebSocketStateHandlers:
    """WebSocket handlers for server-authoritative state management."""

    def __init__(self, sio: socketio.AsyncServer, app, state_manager: StateManager):
        self.sio = sio
        self.app = app
        self.state_manager = state_manager

        # Set the Socket.IO server in state manager
        self.state_manager.socketio = sio

        logger.info("WebSocketStateHandlers initialized with server-authoritative architecture",
        )

    def register(self):
        """Register all server-authoritative WebSocket event handlers."""

        @self.sio.event
        @handle_http_errors()
        async def connect(sid, environ):
            """Handle client connection and initial state sync."""
            logger.info(f"Client connected: {sid}")

            # Send connection acknowledgment with proper error handling
            await self.sio.emit(
                "connection_status",
                {
                    "status": "connected",
                    "sid": sid,
                    "server_seq": self.state_manager.get_global_sequence(),
                },
                room=sid,
            )

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection and cleanup subscriptions."""
            logger.info(f"Client disconnected: {sid}")

            # Unsubscribe client from all rooms
            await self.state_manager.unsubscribe_client(sid)

        @self.sio.on("join:playlists")
        @handle_http_errors()
        async def handle_join_playlists(sid, data):
            """Subscribe client to global playlists state updates."""
            logger.info(f"Client {sid} joining playlists room")
            await self.state_manager.subscribe_client(sid, "playlists")
            # Snapshot is sent by StateManager.subscribe_client via _send_state_snapshot
            # Send acknowledgment
            await self.sio.emit(
                "ack:join",
                {
                    "room": "playlists",
                    "success": True,
                    "server_seq": self.state_manager.get_global_sequence(),
                },
                room=sid,
            )
            logger.info(f"Client {sid} subscribed to playlists; snapshot will be sent by StateManager",
            )

        @self.sio.on("join:playlist")
        @handle_http_errors()
        async def handle_join_playlist(sid, data):
            """Subscribe client to specific playlist state updates."""
            playlist_id = data.get("playlist_id")
            if not playlist_id:
                raise ValueError("playlist_id is required")
            room = f"playlist:{playlist_id}"
            logger.info(f"Client {sid} joining playlist room: {room}")
            await self.state_manager.subscribe_client(sid, room)
            # Send acknowledgment
            await self.sio.emit(
                "ack:join",
                {
                    "room": room,
                    "playlist_id": playlist_id,
                    "success": True,
                    "playlist_seq": self.state_manager.get_playlist_sequence(playlist_id),
                },
                room=sid,
            )

        @self.sio.on("leave:playlists")
        @handle_http_errors()
        async def handle_leave_playlists(sid, data):
            """Unsubscribe client from global playlists updates."""
            logger.info(f"Client {sid} leaving playlists room")
            await self.state_manager.unsubscribe_client(sid, "playlists")
            await self.sio.emit("ack:leave", {"room": "playlists", "success": True}, room=sid)

        @self.sio.on("leave:playlist")
        @handle_http_errors()
        async def handle_leave_playlist(sid, data):
            """Unsubscribe client from specific playlist updates."""
            playlist_id = data.get("playlist_id")
            if not playlist_id:
                raise ValueError("playlist_id is required")
            room = f"playlist:{playlist_id}"
            logger.info(f"Client {sid} leaving playlist room: {room}")
            await self.state_manager.unsubscribe_client(sid, room)
            await self.sio.emit(
                "ack:leave", {"room": room, "playlist_id": playlist_id, "success": True}, room=sid
            )

        @self.sio.on("join:nfc")
        @handle_http_errors()
        async def handle_join_nfc(sid, data):
            """Subscribe client to NFC association session room and send snapshot."""
            assoc_id = data.get("assoc_id")
            if not assoc_id:
                raise ValueError("assoc_id is required")
            room = f"nfc:{assoc_id}"
            logger.info(f"Client {sid} joining NFC room: {room}")
            await self.state_manager.subscribe_client(sid, room)
            # Send current snapshot
            container = getattr(self.app, "container", None)
            nfc_service = getattr(container, "nfc", None) if container else None
            if nfc_service and hasattr(nfc_service, "get_session_snapshot"):
                snapshot = await nfc_service.get_session_snapshot(assoc_id)
                if snapshot:
                    await self.sio.emit("nfc_status", snapshot, room=sid)
            # Ack join
            await self.sio.emit("ack:join", {"room": room, "success": True}, room=sid)

        @self.sio.on("sync:request")
        @handle_http_errors()
        async def handle_sync_request(sid, data):
            """Handle client request for state synchronization."""
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
                    "synced_rooms": list(self.state_manager.get_client_subscriptions(sid)),
                },
                room=sid,
            )

        # WebSocket commands removed per API Contract v2.0
        # All commands now use HTTP endpoints only
        # State updates are broadcast via canonical events
        # NFC Association WebSocket Handlers
        @self.sio.on("start_nfc_link")
        @handle_http_errors()
        async def handle_start_nfc_link(sid, data):
            """Handle NFC association start via WebSocket."""
            playlist_id = data.get("playlist_id")
            client_op_id = data.get("client_op_id")
            if not playlist_id:
                raise ValueError("playlist_id is required")
            logger.info(f"Starting NFC association for playlist {playlist_id} from client {sid}",
            )
            # Get NFC service from container
            container = getattr(self.app, "container", None)
            nfc_service = getattr(container, "nfc", None) if container else None
            if not nfc_service:
                raise Exception("NFC service not available")
            # Start association using the service
            result = await nfc_service.start_association_use_case(playlist_id)
            # Emit state update to client
            await self.sio.emit(
                "nfc_association_state",
                {
                    "state": "activated",
                    "playlist_id": playlist_id,
                    "expires_at": result.get("expires_at"),
                    "server_seq": self.state_manager.get_global_sequence(),
                },
                room=sid,
            )
            # Send acknowledgment if client_op_id provided
            if client_op_id:
                await self.state_manager.send_acknowledgment(
                    client_op_id,
                    True,
                    {"assoc_id": result.get("assoc_id"), "playlist_id": playlist_id},
                )
            logger.info(f"NFC association started successfully for playlist {playlist_id}"
            )

        @self.sio.on("stop_nfc_link")
        @handle_http_errors()
        async def handle_stop_nfc_link(sid, data):
            """Handle NFC association cancellation via WebSocket."""
            playlist_id = data.get("playlist_id")
            client_op_id = data.get("client_op_id")
            if not playlist_id:
                raise ValueError("playlist_id is required")
            logger.info(f"Stopping NFC association for playlist {playlist_id} from client {sid}",
            )
            # Get NFC service from container
            container = getattr(self.app, "container", None)
            nfc_service = getattr(container, "nfc", None) if container else None
            if not nfc_service:
                raise Exception("NFC service not available")
            # Cancel association - need to find the association ID
            # For now, we'll use a simplified approach
            result = await nfc_service.cancel_association_by_playlist(playlist_id)
            # Emit cancelled state
            await self.sio.emit(
                "nfc_association_state",
                {
                    "state": "cancelled",
                    "playlist_id": playlist_id,
                    "message": "Association cancelled by user",
                    "server_seq": self.state_manager.get_global_sequence(),
                },
                room=sid,
            )
            # Send acknowledgment
            if client_op_id:
                await self.state_manager.send_acknowledgment(
                    client_op_id, True, {"playlist_id": playlist_id, "status": "cancelled"}
                )
            logger.info(f"NFC association cancelled for playlist {playlist_id}")

        @self.sio.on("override_nfc_tag")
        @handle_http_errors()
        async def handle_override_nfc_tag(sid, data):
            """Handle NFC tag override via WebSocket.

            Starts a new association session in override mode and immediately processes
            the tag if tag_id is provided (no need to scan again).
            """
            playlist_id = data.get("playlist_id")
            tag_id = data.get("tag_id")  # Get the tag_id from duplicate detection
            client_op_id = data.get("client_op_id")
            if not playlist_id:
                raise ValueError("playlist_id is required")

            logger.info(f"🔄 Overriding NFC tag {tag_id} for playlist {playlist_id} from client {sid}")

            # Get NFC service from application (correct path: app.application._nfc_app_service)
            application = getattr(self.app, "application", None)
            if not application:
                raise Exception("Domain application not available")
            nfc_service = getattr(application, "_nfc_app_service", None)
            if not nfc_service:
                raise Exception("NFC service not available")

            # Start association in override mode (NEW: pass override_mode=True)
            result = await nfc_service.start_association_use_case(
                playlist_id,
                timeout_seconds=60,
                override_mode=True  # Force association even if tag already associated
            )

            # Get session info
            session = result.get("session", {})
            session_id = session.get("session_id")
            timeout_at = session.get("timeout_at")

            # Calculate expires_at timestamp for frontend countdown
            import time
            from datetime import datetime, timezone
            if timeout_at:
                expires_at = datetime.fromisoformat(timeout_at.replace('Z', '+00:00')).timestamp()
            else:
                expires_at = time.time() + 60

            # If tag_id is provided, immediately process it (no need to scan again)
            if tag_id:
                logger.info(f"✅ Processing saved tag {tag_id} immediately for override")
                from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier

                # Create tag identifier from saved tag_id
                tag_identifier = TagIdentifier(uid=tag_id)

                # Process the tag immediately for this override session
                await nfc_service._handle_tag_detection(tag_identifier)

                logger.info(f"✅ Override completed automatically for tag {tag_id}")
            else:
                # No tag_id provided, emit waiting state (old behavior)
                await self.sio.emit(
                    "nfc_association_state",
                    {
                        "state": "waiting",
                        "playlist_id": playlist_id,
                        "session_id": session_id,
                        "expires_at": expires_at,
                        "override_mode": True,
                        "message": "Place NFC tag to override existing association",
                        "server_seq": self.state_manager.get_global_sequence(),
                    },
                    room=sid,
                )

            # Send acknowledgment
            if client_op_id:
                await self.state_manager.send_acknowledgment(
                    client_op_id,
                    True,
                    {
                        "session_id": session_id,
                        "playlist_id": playlist_id,
                        "override": True,
                        "tag_id": tag_id,
                        "auto_processed": tag_id is not None,
                    },
                )

            logger.info(f"✅ NFC tag override started for playlist {playlist_id} (session: {session_id})")

        # Connection health monitoring
        @self.sio.on("client_ping")
        @handle_http_errors()
        async def handle_client_ping(sid, data):
            """Handle client ping for connection health monitoring."""
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
        async def handle_health_check(sid, data):
            """Handle client health check request."""
            health_metrics = await self.state_manager.get_health_metrics()
            health_metrics.update(
                {
                    "connected_clients": len(self.sio.manager.rooms.get("/", {})),
                    "server_time": time.time(),
                }
            )
            await self.sio.emit("health_status", health_metrics, room=sid)

        # Post-connection state synchronization
        @self.sio.on("client:request_current_state")
        @handle_http_errors()
        async def handle_request_current_state(sid, data=None):
            """Handle client request for current state synchronization."""
            logger.info(f"🔄 Client {sid} requesting current state sync")
            # Get current player state and broadcast to specific client
            from app.src.dependencies import get_playback_coordinator, get_player_state_service

            # Get playback coordinator using DDD architecture
            try:
                playback_coordinator = get_playback_coordinator()
                player_state_service = get_player_state_service()
                if playback_coordinator:
                    # Build current player state
                    player_state = await player_state_service.build_current_player_state(
                        playback_coordinator, self.state_manager
                    )

                    # Handle both PlayerStateModel and dict returns
                    if hasattr(player_state, 'server_seq'):
                        # PlayerStateModel case
                        server_seq = player_state.server_seq
                        data = player_state.model_dump()
                        playlist_title = getattr(player_state, 'active_playlist_title', None)
                    else:
                        # dict case (fallback scenario)
                        server_seq = player_state.get('server_seq', 0)
                        data = player_state
                        playlist_title = player_state.get('active_playlist_title', 'None')

                    # Send current player state to requesting client
                    await self.sio.emit(
                        "state:player",
                        {
                            "event_type": "state:player",
                            "server_seq": server_seq,
                            "data": data,
                            "timestamp": time.time(),
                            "event_id": f"sync_{int(time.time() * 1000)}",
                        },
                        room=sid,
                    )
                    logger.info(f"✅ Sent current player state to client {sid}: {playlist_title}",
                    )
                else:
                    logger.warning(f"⚠️ No playback coordinator available for state sync to {sid}"
                    )
            except Exception as e:
                logger.error(f"❌ Error getting playback coordinator for state sync to {sid}: {e}"
                )

        logger.info("Server-authoritative WebSocket handlers registered successfully")
