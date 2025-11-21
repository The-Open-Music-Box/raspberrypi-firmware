# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
State Snapshot Service (DDD Architecture)

Single responsibility: Manages state snapshots for newly connected clients.
Clean separation following Domain-Driven Design principles.
"""

import time
import uuid
from typing import Any, Dict, Optional
import logging

from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.application.services.state_serialization_application_service import StateSerializationApplicationService
from app.src.application.services.state_event_coordinator import StateEventType
from app.src.services.sequence_generator import SequenceGenerator

logger = logging.getLogger(__name__)


class StateSnapshotApplicationService:
    """
    Handles state snapshots for newly connected clients.

    Single Responsibility: Providing current state snapshots to clients joining rooms.

    Responsibilities:
    - Playlist snapshot generation and delivery
    - Individual playlist snapshot delivery
    - Client-specific snapshot sending via Socket.IO

    Does NOT handle:
    - Event broadcasting (delegated to StateEventCoordinator)
    - Serialization logic (delegated to StateSerializationService)
    - Business logic (handled by application services)
    """

    def __init__(
        self,
        socketio_server=None,
        serialization_service: StateSerializationApplicationService = None,
        sequences: SequenceGenerator = None,
        data_application_service=None,
        player_application_service=None,
    ):
        """Initialize state snapshot service.

        Args:
            socketio_server: Socket.IO server for client communication
            serialization_service: Service for serializing domain objects
            sequences: Sequence generator for consistent ordering
            data_application_service: Data application service for playlist operations
            player_application_service: Player application service for player state
        """
        self.socketio = socketio_server
        self.serialization_service = serialization_service or StateSerializationApplicationService(sequences)
        self.sequences = sequences or SequenceGenerator()
        self._data_application_service = data_application_service
        self._player_application_service = player_application_service

        logger.info("StateSnapshotService initialized with clean DDD architecture")

    @handle_service_errors("state_snapshot_service")
    async def send_state_snapshot(self, client_id: str, room: str) -> None:
        """
        Send current state snapshot to a newly subscribed client.

        Args:
            client_id: Socket.IO client identifier
            room: Room identifier (e.g., 'playlists' or 'playlist:123')
        """
        if not self.socketio:
            logger.warning("No Socket.IO server available for snapshot delivery")
            return

        if room == "playlists":
            await self._send_playlists_snapshot(client_id)
        elif room.startswith("playlist:"):
            playlist_id = room.split(":", 1)[1]
            await self._send_playlist_snapshot(client_id, playlist_id)
        else:
            logger.warning(f"Unknown room type for snapshot: {room}")

    @handle_service_errors("state_snapshot_service")
    async def _send_playlists_snapshot(self, client_id: str) -> None:
        """
        Send playlists snapshot to client.

        Args:
            client_id: Socket.IO client identifier
        """
        # Use injected DDD application service to get playlists
        playlists = []
        if self._data_application_service:
            try:
                # Get all playlists via injected application service
                playlists_result = await self._data_application_service.get_playlists_use_case()

                # The DDD service returns data directly with 'playlists' key
                playlists = playlists_result.get("playlists", [])

            except Exception as e:
                logger.error(f"Error getting playlists for snapshot: {e}")
        else:
            logger.warning("No data application service available for playlists snapshot")

        # Serialize playlists using clean serialization service
        playlists_data = self.serialization_service.serialize_playlists_collection(playlists)

        # Create and send snapshot event
        snapshot_event = {
            "event_type": StateEventType.PLAYLISTS_SNAPSHOT.value,
            "server_seq": self.sequences.get_current_global_seq(),
            "data": {"playlists": playlists_data},
            "timestamp": int(time.time() * 1000),
            "event_id": str(uuid.uuid4())[:8],  # Contract-required field
        }

        await self.socketio.emit(
            StateEventType.PLAYLISTS_SNAPSHOT.value,
            snapshot_event,
            room=client_id,
        )

        logger.info(
            f"Playlists snapshot sent to client {client_id}: {len(playlists_data)} playlists"
        )

        # CRITICAL FIX: Also send current player state when joining playlists room
        # This ensures clients always have the current playback state
        await self._send_player_state_snapshot(client_id)

    @handle_service_errors("state_snapshot_service")
    async def _send_playlist_snapshot(self, client_id: str, playlist_id: str) -> None:
        """
        Send specific playlist snapshot to client.

        Args:
            client_id: Socket.IO client identifier
            playlist_id: Playlist identifier to send snapshot for
        """
        # Use injected DDD application service to get specific playlist
        playlist = None
        if self._data_application_service:
            try:
                # Get specific playlist via injected application service
                playlist = await self._data_application_service.get_playlist_use_case(playlist_id)

            except Exception as e:
                logger.error(f"Error getting playlist {playlist_id} for snapshot: {e}")
        else:
            logger.warning(f"No data application service available for playlist {playlist_id} snapshot")

        if not playlist:
            logger.warning(f"Playlist {playlist_id} not found for snapshot")
            return

        # Serialize playlist using clean serialization service
        playlist_data = self.serialization_service.serialize_playlist(playlist, include_tracks=True)

        # Create and send snapshot event
        snapshot_event = {
            "event_type": StateEventType.PLAYLIST_SNAPSHOT.value,
            "server_seq": self.sequences.get_current_global_seq(),
            "playlist_id": playlist_id,
            "playlist_seq": self.sequences.get_current_playlist_seq(playlist_id),
            "data": playlist_data,
            "timestamp": int(time.time() * 1000),
            "event_id": str(uuid.uuid4())[:8],  # Contract-required field
        }

        await self.socketio.emit(
            StateEventType.PLAYLIST_SNAPSHOT.value,
            snapshot_event,
            room=client_id,
        )

        logger.info(
            f"Playlist snapshot sent to client {client_id}: playlist {playlist_id}"
        )

    @handle_service_errors("state_snapshot_service")
    async def _send_player_state_snapshot(self, client_id: str) -> None:
        """
        Send current player state snapshot to client.

        Args:
            client_id: Socket.IO client identifier
        """
        # Get current player state via injected player application service
        if not self._player_application_service:
            logger.warning("No player application service available for player state snapshot")
            return

        try:
            # Get current player status
            status_result = await self._player_application_service.get_status_use_case()

            # Defensive: handle None or missing fields
            if status_result is None:
                logger.warning("Player status service returned None")
                return

            # Check both "success" and "status" keys for robustness
            if not status_result.get("success") and status_result.get("status") == "error":
                logger.warning(f"Failed to get player status for snapshot: {status_result.get('message')}")
                return

            player_state = status_result.get("status", {})

            # Create and send player state snapshot event
            player_state_event = {
                "event_type": StateEventType.PLAYER_STATE.value,
                "server_seq": self.sequences.get_current_global_seq(),
                "data": player_state,
                "timestamp": int(time.time() * 1000),
                "event_id": str(uuid.uuid4())[:8],
            }

            await self.socketio.emit(
                StateEventType.PLAYER_STATE.value,
                player_state_event,
                room=client_id,
            )

            # Safe logging with None-safe nested gets
            active_track = player_state.get('active_track') or {}
            track_title = active_track.get('title', 'none') if isinstance(active_track, dict) else 'none'

            logger.info(
                f"✅ Player state snapshot sent to client {client_id}: playing={player_state.get('is_playing', False)}, "
                f"track={track_title}"
            )

        except Exception as e:
            logger.error(f"❌ Error getting player state for snapshot: {e}")
