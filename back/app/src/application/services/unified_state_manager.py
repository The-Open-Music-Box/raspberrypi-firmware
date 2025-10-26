# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified State Manager (DDD Architecture)

Clean coordinator that delegates to single-responsibility components.
Implements StateManagerProtocol while following DDD principles.
"""

import asyncio
import logging
from typing import Any, Dict, Optional, Set

# Direct imports - no more dynamic imports
from app.src.services.error.unified_error_decorator import handle_service_errors
from app.src.domain.protocols.state_manager_protocol import StateManagerProtocol, PlaybackState

# DDD Components - direct imports
from app.src.application.services.state_event_coordinator import (
    StateEventCoordinator,
    StateEventType,
)
from app.src.application.services.state_serialization_application_service import (
    StateSerializationApplicationService,
)
from app.src.application.services.state_snapshot_application_service import (
    StateSnapshotApplicationService,
)
from app.src.domain.services.playback_state_manager import PlaybackStateManager
from app.src.application.services.state_manager_lifecycle_application_service import (
    StateManagerLifecycleApplicationService,
)

# Existing focused components - direct imports
from app.src.services.client_subscription_manager import ClientSubscriptionManager
from app.src.services.operation_tracker import OperationTracker
from app.src.services.sequence_generator import SequenceGenerator
from app.src.services.event_outbox import EventOutbox

logger = logging.getLogger(__name__)


class UnifiedStateManager(StateManagerProtocol):
    """
    Unified state manager following clean DDD architecture.

    Single Responsibility: Coordination and delegation to focused components.

    This class acts as a facade that:
    - Delegates state management to PlaybackStateManager
    - Delegates event coordination to StateEventCoordinator
    - Delegates serialization to StateSerializationService
    - Delegates snapshots to StateSnapshotService
    - Delegates lifecycle to StateManagerLifecycleService
    - Maintains existing API compatibility

    Architecture Benefits:
    - Single Responsibility Principle compliance
    - Clean separation of concerns
    - Testable components
    - Easy to extend and maintain
    """

    def __init__(self, socketio_server=None, data_application_service=None, player_application_service=None):
        """Initialize unified state manager with clean DDD architecture.

        Args:
            socketio_server: Socket.IO server for real-time communication
            data_application_service: Data application service for snapshot functionality (optional)
            player_application_service: Player application service for player state snapshots (optional)
        """
        self.socketio = socketio_server

        # Initialize focused components (already SRP-compliant)
        self.sequences = SequenceGenerator()
        self.outbox = EventOutbox(socketio_server)
        self.subscriptions = ClientSubscriptionManager(socketio_server)
        self.operations = OperationTracker()

        # Initialize new DDD components
        self.state_manager = PlaybackStateManager()
        self.serialization_service = StateSerializationApplicationService(self.sequences)
        self.event_coordinator = StateEventCoordinator(
            socketio_server, self.outbox, self.sequences
        )
        self.snapshot_service = StateSnapshotApplicationService(
            socketio_server, self.serialization_service, self.sequences, data_application_service, player_application_service
        )
        self.lifecycle_service = StateManagerLifecycleApplicationService(
            self.operations, self.outbox
        )

        logger.info("UnifiedStateManager initialized with clean DDD architecture")

    def set_player_application_service(self, player_application_service):
        """Set the player application service for snapshot functionality.

        This allows lazy injection to avoid circular dependencies.

        Args:
            player_application_service: Player application service instance
        """
        self.snapshot_service._player_application_service = player_application_service
        logger.info("✅ Player application service injected into UnifiedStateManager")

    # Client subscription management (delegate to ClientSubscriptionManager)
    async def subscribe_client(self, client_id: str, room: str) -> None:
        """Subscribe a client to a specific room for state updates."""
        await self.subscriptions.subscribe_client(client_id, room)
        # Send current state snapshot to newly subscribed client
        await self.snapshot_service.send_state_snapshot(client_id, room)

    async def unsubscribe_client(self, client_id: str, room: Optional[str] = None) -> None:
        """Unsubscribe a client from a room or all rooms."""
        await self.subscriptions.unsubscribe_client(client_id, room)

    def get_client_subscriptions(self, client_id: str) -> Set[str]:
        """Get all rooms a client is subscribed to."""
        return self.subscriptions.get_client_subscriptions(client_id)

    # Operation tracking (delegate to OperationTracker)
    async def is_operation_processed(self, client_op_id: str) -> bool:
        """Check if a client operation has already been processed."""
        return await self.operations.is_operation_processed(client_op_id)

    async def mark_operation_processed(self, client_op_id: str, result: Any = None) -> None:
        """Mark a client operation as processed with optional result caching."""
        await self.operations.mark_operation_processed(client_op_id, result)

    async def get_operation_result(self, client_op_id: str) -> Optional[Any]:
        """Get cached result for a processed operation."""
        return await self.operations.get_operation_result(client_op_id)

    # Event broadcasting (delegate to StateEventCoordinator)
    @handle_service_errors("unified_state_manager")
    async def broadcast_state_change(
        self,
        event_type: StateEventType,
        data: Dict[str, Any],
        playlist_id: Optional[str] = None,
        room: Optional[str] = None,
        immediate: bool = False,
    ) -> dict:
        """Broadcast a state change to all subscribed clients."""
        return await self.event_coordinator.broadcast_state_change(
            event_type, data, playlist_id, room, immediate
        )

    async def broadcast_position_update(
        self, position_ms: int, track_id: str, is_playing: bool, duration_ms: Optional[int] = None
    ) -> Optional[dict]:
        """Broadcast a lightweight position update with throttling."""
        return await self.event_coordinator.broadcast_position_update(
            position_ms, track_id, is_playing, duration_ms
        )

    async def emit_playlists_index_update(self, updates: list) -> dict:
        """Emit playlists index update events."""
        return await self.event_coordinator.emit_playlists_index_update(updates)

    async def send_acknowledgment(
        self,
        client_op_id: str,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        client_id: Optional[str] = None,
    ) -> None:
        """Send acknowledgment for a client operation."""
        await self.event_coordinator.send_acknowledgment(
            client_op_id, success, data, client_id
        )

    # Sequence management (delegate to SequenceGenerator)
    def get_global_sequence(self) -> int:
        """Get current global sequence number."""
        return self.sequences.get_current_global_seq()

    def get_playlist_sequence(self, playlist_id: str) -> int:
        """Get current sequence number for a playlist."""
        return self.sequences.get_current_playlist_seq(playlist_id)

    # Event outbox management (delegate to EventOutbox)
    async def process_outbox(self) -> None:
        """Process the event outbox for reliable delivery."""
        await self.outbox.process_outbox()

    # Lifecycle management (delegate to StateManagerLifecycleService)
    async def start_cleanup_task(self) -> None:
        """Start a background task to periodically clean up expired operations and outbox events."""
        await self.lifecycle_service.start_lifecycle_management()

    async def stop_cleanup_task(self) -> None:
        """Stop the periodic cleanup task."""
        await self.lifecycle_service.stop_lifecycle_management()

    async def get_health_metrics(self) -> Dict[str, Any]:
        """Get health metrics from all components."""
        base_metrics = await self.lifecycle_service.get_health_metrics()

        # Add additional component metrics
        base_metrics.update({
            "sequences": self.sequences.get_stats(),
            "subscriptions": self.subscriptions.get_stats(),
            "state_manager": {
                "current_state": self.state_manager.get_current_state().value,
                "last_updated": self.state_manager.get_last_updated(),
                "has_error": self.state_manager.is_error(),
            }
        })

        return base_metrics

    # StateManagerProtocol implementation (delegate to PlaybackStateManager)
    def get_current_state(self) -> PlaybackState:
        """Get current playback state."""
        return self.state_manager.get_current_state()

    def set_state(self, state: PlaybackState) -> None:
        """Set current playback state."""
        self.state_manager.set_state(state)

    def get_state_dict(self) -> Dict[str, Any]:
        """Get complete state as dictionary."""
        return self.state_manager.get_state_dict()

    def update_track_info(self, track_info: Dict[str, Any]) -> None:
        """Update current track information."""
        self.state_manager.update_track_info(track_info)

    def update_playlist_info(self, playlist_info: Dict[str, Any]) -> None:
        """Update current playlist information."""
        self.state_manager.update_playlist_info(playlist_info)

    def update_position(self, position_seconds: float) -> None:
        """Update current playback position."""
        self.state_manager.update_position(position_seconds)

    def update_volume(self, volume: int) -> None:
        """Update current volume level."""
        self.state_manager.update_volume(volume)

    def set_error(self, error_message: str) -> None:
        """Set error state with message."""
        self.state_manager.set_error(error_message)

    def clear_error(self) -> None:
        """Clear error state."""
        self.state_manager.clear_error()

    def get_last_error(self) -> Optional[str]:
        """Get last error message."""
        return self.state_manager.get_last_error()

    # Extended state management methods (delegate to PlaybackStateManager)
    def get_current_playlist(self) -> Optional[Dict[str, Any]]:
        """Get current playlist information."""
        return self.state_manager.get_current_playlist()

    def set_current_playlist(self, playlist: Optional[Dict[str, Any]]) -> None:
        """Set current playlist information."""
        self.state_manager.set_current_playlist(playlist)

    def get_current_track_number(self) -> Optional[int]:
        """Get current track number in playlist."""
        return self.state_manager.get_current_track_number()

    def set_current_track_number(self, track_number: Optional[int]) -> None:
        """Set current track number in playlist."""
        self.state_manager.set_current_track_number(track_number)

    # Convenience methods for backward compatibility
    def _serialize_playlist(self, playlist) -> Dict[str, Any]:
        """Serialize a playlist object or dict for transmission."""
        return self.serialization_service.serialize_playlist(playlist)

    def _serialize_track(self, track) -> Dict[str, Any]:
        """Serialize a track object or dict for transmission."""
        return self.serialization_service.serialize_track(track)

    # Legacy compatibility methods for smooth migration
    async def _send_state_snapshot(self, client_id: str, room: str) -> None:
        """Send current state snapshot to a newly subscribed client."""
        await self.snapshot_service.send_state_snapshot(client_id, room)

    async def _send_playlists_snapshot(self, client_id: str) -> None:
        """Send playlists snapshot to client."""
        await self.snapshot_service._send_playlists_snapshot(client_id)

    async def _send_playlist_snapshot(self, client_id: str, playlist_id: str) -> None:
        """Send specific playlist snapshot to client."""
        await self.snapshot_service._send_playlist_snapshot(client_id, playlist_id)
