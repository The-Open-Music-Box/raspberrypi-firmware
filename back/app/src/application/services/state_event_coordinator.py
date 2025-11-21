# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
State Event Coordinator (DDD Architecture)

Single responsibility: Coordinates event broadcasting between domain events and Socket.IO transport.
Clean separation of concerns following DDD principles.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict, Optional
from enum import Enum
import logging

from app.src.common.socket_events import SocketEventType, get_event_room, SocketEventBuilder, StateEventType
from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.config.socket_config import socket_config
from app.src.services.event_outbox import EventOutbox
from app.src.services.sequence_generator import SequenceGenerator

logger = logging.getLogger(__name__)


class StateEventCoordinator:
    """
    Coordinates state event broadcasting using clean DDD architecture.

    Single Responsibility: Event coordination between domain and transport layers.

    Responsibilities:
    - Event envelope creation with proper sequencing
    - Socket.IO transport coordination
    - Position update throttling
    - Event conversion between domain and transport formats

    Does NOT handle:
    - State storage (delegated to PlaybackStateManager)
    - Serialization (delegated to StateSerializationService)
    - Client subscriptions (delegated to ClientSubscriptionManager)
    - Operation tracking (delegated to OperationTracker)
    """

    def __init__(self, socketio_server=None, outbox: EventOutbox = None, sequences: SequenceGenerator = None):
        """Initialize state event coordinator.

        Args:
            socketio_server: Socket.IO server for real-time transport
            outbox: Event outbox for reliable delivery
            sequences: Sequence generator for event ordering
        """
        self.socketio = socketio_server
        self.outbox = outbox or EventOutbox(socketio_server)
        self.sequences = sequences or SequenceGenerator()

        # Position update throttling
        self._last_position_emit_time = 0

        # Logging state
        self._position_state_logged = False
        self._first_position_logged = False
        self._position_log_counter = 0

        logger.info("StateEventCoordinator initialized with clean DDD architecture")

    @handle_service_errors("state_event_coordinator")
    async def broadcast_state_change(
        self,
        event_type: StateEventType,
        data: Dict[str, Any],
        playlist_id: Optional[str] = None,
        room: Optional[str] = None,
        immediate: bool = False,
    ) -> dict:
        """
        Broadcast a state change to all subscribed clients.

        Args:
            event_type: Type of state event
            data: Event data to broadcast
            playlist_id: Optional playlist ID for playlist-specific events
            room: Optional specific room to broadcast to
            immediate: If True, process outbox immediately for real-time delivery

        Returns:
            The created event envelope
        """
        # Get sequence numbers
        server_seq = await self.sequences.get_next_global_seq()
        if playlist_id:
            data["playlist_seq"] = await self.sequences.get_next_playlist_seq(playlist_id)

        # Convert to SocketEventType
        socket_event_type = self._convert_state_event_type_to_socket_event_type(event_type)

        # Create standardized event envelope
        envelope = {
            "event_type": event_type.value,
            "server_seq": server_seq,
            "data": data,
            "timestamp": int(time.time() * 1000),
            "event_id": str(uuid.uuid4())[:8],
        }

        if playlist_id:
            envelope["playlist_id"] = playlist_id
            envelope["playlist_seq"] = data.get("playlist_seq")

        # Add to outbox for reliable delivery
        await self.outbox.add_event(
            event_id=envelope["event_id"],
            event_type=envelope["event_type"],
            payload=envelope,
            server_seq=server_seq,
            playlist_id=playlist_id,
        )

        # Broadcast immediately if Socket.IO is available
        if self.socketio:
            await self._broadcast_event(envelope, room, socket_event_type, playlist_id)

        # Process outbox immediately if requested
        if immediate:
            await self.outbox.process_outbox()

        # Log state changes except frequent position updates
        if event_type != StateEventType.TRACK_POSITION:
            logger.info(f"State change broadcasted: {event_type.value} (seq: {server_seq})")
        elif not self._position_state_logged:
            logger.info(f"📡 FIRST position state change broadcasted (seq: {server_seq})")
            self._position_state_logged = True

        return envelope

    async def broadcast_position_update(
        self, position_ms: int, track_id: str, is_playing: bool, duration_ms: Optional[int] = None
    ) -> Optional[dict]:
        """
        Broadcast a lightweight position update with throttling.

        Args:
            position_ms: Current playback position in milliseconds
            track_id: ID of the currently playing track
            is_playing: Whether playback is active
            duration_ms: Optional track duration

        Returns:
            Event envelope if broadcasted, None if throttled
        """
        # Throttle position updates
        current_time = time.time()
        if (
            current_time - self._last_position_emit_time
            < socket_config.POSITION_THROTTLE_MIN_MS / 1000
        ):
            return None

        self._last_position_emit_time = current_time

        # Log every 10 seconds (10 events at 1000ms interval)
        self._position_log_counter += 1

        if self._position_log_counter % 10 == 0:
            logger.debug(
                f"Broadcasting position update #{self._position_log_counter}: {position_ms}ms, playing={is_playing}"
            )

        # Create minimal payload
        data = {"position_ms": position_ms, "track_id": track_id, "is_playing": is_playing}

        if duration_ms is not None:
            data["duration_ms"] = duration_ms

        # Broadcast with immediate processing for real-time updates
        return await self.broadcast_state_change(
            StateEventType.TRACK_POSITION, data, immediate=True
        )

    async def emit_playlists_index_update(self, updates: list) -> dict:
        """
        Emit playlists index update events.

        Args:
            updates: List of update operations with format:
                     [{"type": "upsert", "item": {...}}, {"type": "delete", "id": "..."}]

        Returns:
            The created event envelope
        """
        data = {"updates": updates}

        return await self.broadcast_state_change(
            StateEventType.PLAYLISTS_INDEX_UPDATE, data, immediate=True
        )

    @handle_service_errors("state_event_coordinator")
    async def send_acknowledgment(
        self,
        client_op_id: str,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None,
    ) -> None:
        """Send acknowledgment for a client operation."""
        if not self.socketio:
            return

        payload = SocketEventBuilder.create_operation_ack_event(
            client_op_id=client_op_id,
            success=success,
            server_seq=self.sequences.get_current_global_seq(),
            data=data,
            message=None if success else "Operation failed",
        )

        event = "ack:op" if success else "err:op"
        if client_id:
            await self.socketio.emit(event, payload, room=client_id)
        else:
            await self.socketio.emit(event, payload, room="playlists")

    async def process_outbox(self) -> None:
        """Process the event outbox for reliable delivery."""
        await self.outbox.process_outbox()

    # Getters for compatibility
    def get_global_sequence(self) -> int:
        """Get current global sequence number."""
        return self.sequences.get_current_global_seq()

    def get_playlist_sequence(self, playlist_id: str) -> int:
        """Get current sequence number for a playlist."""
        return self.sequences.get_current_playlist_seq(playlist_id)

    @handle_service_errors("state_event_coordinator")
    async def _broadcast_event(
        self,
        envelope: dict,
        room: Optional[str],
        socket_event_type: SocketEventType,
        playlist_id: Optional[str],
    ) -> None:
        """Broadcast a state event to clients using standardized envelope format."""
        if not self.socketio:
            return

        # Validate envelope is JSON serializable
        json.dumps(envelope)

        if room:
            # Broadcast to specific room
            await self.socketio.emit(envelope["event_type"], envelope, room=room)
        else:
            # Use standardized room routing
            target_room = get_event_room(socket_event_type, playlist_id)
            await self.socketio.emit(envelope["event_type"], envelope, room=target_room)

            # Log first position event and all other events
            if socket_event_type == SocketEventType.STATE_TRACK_POSITION:
                if not self._first_position_logged:
                    logger.info(
                        f"🎯 FIRST state:track_position broadcasted to '{target_room}' (seq: {envelope['server_seq']})"
                    )
                    self._first_position_logged = True
            elif socket_event_type != SocketEventType.STATE_TRACK_PROGRESS:
                logger.info(
                    f"Broadcasted {envelope['event_type']} to room '{target_room}' (seq: {envelope['server_seq']})"
                )

    @handle_service_errors("state_event_coordinator")
    def _convert_state_event_type_to_socket_event_type(
        self, state_event_type: StateEventType,
    ) -> SocketEventType:
        """Convert StateEventType to SocketEventType for compatibility."""
        conversion_map = {
            "state:playlists": SocketEventType.STATE_PLAYLISTS,
            "state:playlists_index_update": SocketEventType.STATE_PLAYLISTS_INDEX_UPDATE,
            "state:playlist": SocketEventType.STATE_PLAYLIST,
            "state:player": SocketEventType.STATE_PLAYER,
            "state:track_progress": SocketEventType.STATE_TRACK_PROGRESS,
            "state:track_position": SocketEventType.STATE_TRACK_POSITION,
            "state:track": SocketEventType.STATE_TRACK,
            "state:playlist_created": SocketEventType.STATE_PLAYLIST_CREATED,
            "state:playlist_updated": SocketEventType.STATE_PLAYLIST_UPDATED,
            "state:playlist_deleted": SocketEventType.STATE_PLAYLIST_DELETED,
            "state:track_added": SocketEventType.STATE_TRACK_ADDED,
            "state:track_deleted": SocketEventType.STATE_TRACK_DELETED,
        }

        socket_event_type = conversion_map.get(state_event_type.value)
        if socket_event_type is None:
            # For unknown event types, create a mock object that has the expected interface
            class MockSocketEventType:
                def __init__(self, value):
                    self.value = value
            return MockSocketEventType(state_event_type.value)
        return socket_event_type
