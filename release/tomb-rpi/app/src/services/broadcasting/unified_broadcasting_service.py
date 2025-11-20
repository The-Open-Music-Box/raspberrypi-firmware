# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unified Broadcasting Service

This service centralizes all Socket.IO broadcasting patterns to eliminate
the 15+ duplicated broadcasting patterns across route handlers.
"""

from typing import Dict, Any, Optional, List
import logging

from app.src.domain.audio.engine.state_manager import StateManager
from app.src.common.socket_events import StateEventType
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = logging.getLogger(__name__)


class UnifiedBroadcastingService:
    """
    Service centralisé pour tous les broadcasts Socket.IO.

    Élimine les patterns répétés de broadcasting dans:
    - 15+ route handlers avec pattern identique
    - Acknowledgment conditionnel répété 20+ fois
    - Broadcasting manuel dans chaque handler
    """

    def __init__(self, state_manager: StateManager):
        """
        Initialize broadcasting service.

        Args:
            state_manager: Instance du StateManager pour les broadcasts
        """
        self.state_manager = state_manager
        self._broadcast_count = 0
        self._acknowledgment_count = 0

    @handle_service_errors("unified_broadcasting")
    async def broadcast_with_acknowledgment(
        self,
        event_type: StateEventType,
        data: Dict[str, Any],
        client_op_id: Optional[str] = None,
        room: Optional[str] = None,
        acknowledge_success: bool = True,
        acknowledge_data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Broadcast avec acknowledgment optionnel.

        Remplace les patterns répétés de:
        - broadcast_state_change
        - send_acknowledgment conditionnel

        Args:
            event_type: Type d'événement à broadcaster
            data: Données à broadcaster
            client_op_id: ID d'opération client pour acknowledgment
            room: Room spécifique pour le broadcast
            acknowledge_success: Status de succès pour acknowledgment
            acknowledge_data: Données spécifiques pour acknowledgment

        Returns:
            True si broadcast réussi
        """
        # Broadcast principal
        await self.state_manager.broadcast_state_change(event_type, data, room)
        self._broadcast_count += 1
        logger.debug(f"Broadcasted {event_type} to room '{room or 'all'}'")
        # Acknowledgment si client_op_id fourni
        if client_op_id:
            ack_data = acknowledge_data if acknowledge_data is not None else data
            await self.state_manager.send_acknowledgment(
                client_op_id, acknowledge_success, ack_data
            )
            self._acknowledgment_count += 1
            logger.debug(f"Sent acknowledgment for operation {client_op_id}")
        return True

    async def broadcast_playlist_change(
        self,
        playlist_id: str,
        change_type: str,
        playlist_data: Optional[Dict[str, Any]] = None,
        client_op_id: Optional[str] = None,
    ) -> bool:
        """
        Broadcast spécifique pour changements de playlist.

        Args:
            playlist_id: ID de la playlist modifiée
            change_type: Type de changement (created, updated, deleted, etc.)
            playlist_data: Données de la playlist
            client_op_id: ID d'opération client

        Returns:
            True si broadcast réussi
        """
        # Prepare broadcast data
        broadcast_data = {
            "playlist_id": playlist_id,
            "change_type": change_type,
            "timestamp": self._get_timestamp(),
        }

        if playlist_data:
            broadcast_data["playlist"] = playlist_data

        # Determine event type based on change
        event_type = StateEventType.PLAYLISTS_SNAPSHOT

        # Broadcast to global playlists room
        success = await self.broadcast_with_acknowledgment(
            event_type=event_type,
            data={"playlists": [playlist_data]} if playlist_data else broadcast_data,
            client_op_id=client_op_id,
            room="playlists",
        )

        # Also broadcast to specific playlist room if exists
        if success and playlist_id:
            await self.state_manager.broadcast_state_change(
                event_type, broadcast_data, room=f"playlist:{playlist_id}"
            )

        return success

    async def broadcast_player_state(
        self,
        state_data: Dict[str, Any],
        client_op_id: Optional[str] = None,
        include_position: bool = True,
    ) -> bool:
        """
        Broadcast spécifique pour l'état du player.

        Args:
            state_data: Données d'état du player
            client_op_id: ID d'opération client
            include_position: Inclure la position actuelle

        Returns:
            True si broadcast réussi
        """
        # Ensure required fields are present
        if "timestamp" not in state_data:
            state_data["timestamp"] = self._get_timestamp()

        # Remove position if not requested (for performance)
        if not include_position and "position_ms" in state_data:
            state_data = state_data.copy()
            state_data.pop("position_ms", None)

        return await self.broadcast_with_acknowledgment(
            event_type=StateEventType.PLAYER_STATE,
            data=state_data,
            client_op_id=client_op_id,
            room="player",
        )

    @handle_service_errors("unified_broadcasting")
    async def broadcast_track_progress(
        self,
        position_ms: int,
        duration_ms: int,
        track_id: Optional[str] = None,
        playlist_id: Optional[str] = None,
    ) -> bool:
        """
        Broadcast de progression de track (optimisé pour fréquence élevée).

        Args:
            position_ms: Position actuelle en ms
            duration_ms: Durée totale en ms
            track_id: ID de la track
            playlist_id: ID de la playlist

        Returns:
            True si broadcast réussi
        """
        # Minimal data for high-frequency updates
        progress_data = {
            "position_ms": position_ms,
            "duration_ms": duration_ms,
            "progress_percentage": (position_ms / duration_ms * 100) if duration_ms > 0 else 0,
        }

        if track_id:
            progress_data["track_id"] = track_id
        if playlist_id:
            progress_data["playlist_id"] = playlist_id

        # Broadcast without acknowledgment for performance
        await self.state_manager.broadcast_state_change(
            StateEventType.POSITION_UPDATE, progress_data, room="player"
        )
        return True

    async def broadcast_nfc_association(
        self,
        association_state: str,
        playlist_id: Optional[str] = None,
        tag_id: Optional[str] = None,
        session_id: Optional[str] = None,
        client_op_id: Optional[str] = None,
        expires_at: Optional[str] = None,
    ) -> bool:
        """
        Broadcast pour associations NFC.

        Args:
            association_state: État de l'association (waiting, detected, completed, error)
            playlist_id: ID de la playlist
            tag_id: ID du tag NFC
            session_id: ID de session d'association
            client_op_id: ID d'opération client
            expires_at: Expiration de la session

        Returns:
            True si broadcast réussi
        """
        nfc_data = {"state": association_state, "timestamp": self._get_timestamp()}

        if playlist_id:
            nfc_data["playlist_id"] = playlist_id
        if tag_id:
            nfc_data["tag_id"] = tag_id
        if session_id:
            nfc_data["session_id"] = session_id
        if expires_at:
            nfc_data["expires_at"] = expires_at

        # CRITICAL: Emit globally (no room) so frontend receives the event
        # The frontend doesn't join specific nfc:session_id rooms
        # See NfcAssociateDialog.vue:289 - "nfc_association_state events are emitted globally"

        # Use SocketEventType.NFC_ASSOCIATION_STATE instead of StateEventType.NFC_ASSOCIATION
        # The frontend listens for 'nfc_association_state', not 'state:nfc_association'
        # We need to emit directly using Socket.IO instead of going through state manager

        # Handle both cases: state_manager with socketio attribute OR direct socketio instance
        socketio_instance = None
        if self.state_manager:
            if hasattr(self.state_manager, 'socketio'):
                # Case 1: Proper StateManager with socketio attribute
                socketio_instance = self.state_manager.socketio
            elif hasattr(self.state_manager, 'emit'):
                # Case 2: Direct socketio instance (from api_routes_state.py:140)
                socketio_instance = self.state_manager

        if socketio_instance:
            from app.src.common.socket_events import SocketEventType
            # Emit globally (no room parameter) so all clients receive it
            await socketio_instance.emit(
                SocketEventType.NFC_ASSOCIATION_STATE.value,
                nfc_data
            )
            self._broadcast_count += 1
            logger.debug(f"Broadcasted NFC association state globally (state={association_state})")

            # Send acknowledgment if client_op_id provided and we have a state manager
            if client_op_id and hasattr(self.state_manager, 'send_acknowledgment'):
                await self.state_manager.send_acknowledgment(
                    client_op_id, True, nfc_data
                )
                self._acknowledgment_count += 1
            return True

        return False

    @handle_service_errors("unified_broadcasting")
    async def broadcast_error(
        self,
        error_message: str,
        error_type: str = "error",
        operation: Optional[str] = None,
        client_op_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Broadcast d'erreur à tous les clients concernés.

        Args:
            error_message: Message d'erreur
            error_type: Type d'erreur
            operation: Opération qui a échoué
            client_op_id: ID d'opération client
            details: Détails additionnels

        Returns:
            True si broadcast réussi
        """
        error_data = {
            "error": error_message,
            "error_type": error_type,
            "timestamp": self._get_timestamp(),
        }

        if operation:
            error_data["operation"] = operation
        if details:
            error_data["details"] = details

        # Send error acknowledgment if client_op_id provided
        if client_op_id:
            await self.state_manager.send_acknowledgment(client_op_id, False, error_data)

        # Also broadcast error to relevant room
        await self.state_manager.broadcast_state_change(
            StateEventType.ERROR, error_data, room="errors"
        )
        return True

    @handle_service_errors("unified_broadcasting")
    async def broadcast_batch(
        self, broadcasts: List[Dict[str, Any]], client_op_id: Optional[str] = None
    ) -> int:
        """
        Effectue plusieurs broadcasts en batch.

        Args:
            broadcasts: Liste de broadcasts à effectuer
            client_op_id: ID d'opération client pour acknowledgment final

        Returns:
            Nombre de broadcasts réussis
        """
        successful_count = 0

        for broadcast in broadcasts:
            event_type = broadcast.get("event_type", StateEventType.GENERAL)
            data = broadcast.get("data", {})
            room = broadcast.get("room")
            await self.state_manager.broadcast_state_change(event_type, data, room)
            successful_count += 1
        # Send final acknowledgment if requested
        if client_op_id:
            await self.state_manager.send_acknowledgment(
                client_op_id,
                successful_count == len(broadcasts),
                {
                    "total": len(broadcasts),
                    "successful": successful_count,
                    "failed": len(broadcasts) - successful_count,
                },
            )

        return successful_count

    def get_statistics(self) -> Dict[str, int]:
        """
        Retourne les statistiques de broadcasting.

        Returns:
            Statistiques d'utilisation
        """
        return {
            "total_broadcasts": self._broadcast_count,
            "total_acknowledgments": self._acknowledgment_count,
            "average_per_minute": self._calculate_average_rate(),
        }

    def _get_timestamp(self) -> float:
        """
        Retourne un timestamp unifié.

        Returns:
            Timestamp actuel
        """
        import time

        return time.time()

    def _calculate_average_rate(self) -> float:
        """
        Calcule le taux moyen de broadcasts.

        Returns:
            Broadcasts par minute
        """
        # This would need actual time tracking for accuracy
        # For now, return a placeholder
        return 0.0
