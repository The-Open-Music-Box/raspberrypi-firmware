# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playlist Broadcasting Service (DDD Architecture)

Single Responsibility: Real-time state broadcasting for playlist operations.
"""

from typing import Dict, Any, List, Optional
import logging
from app.src.application.services.unified_state_manager import UnifiedStateManager
from app.src.common.socket_events import StateEventType
from app.src.services.error.unified_error_decorator import handle_service_errors

logger = logging.getLogger(__name__)


class PlaylistBroadcastingService:
    """
    Service responsible for broadcasting playlist state changes.

    Single Responsibility: WebSocket state broadcasting for playlist events.

    Responsibilities:
    - Broadcast playlist creation/updates/deletion
    - Broadcast track operations (add/remove/reorder)
    - Broadcast playback state changes
    - Manage WebSocket event types

    Does NOT handle:
    - HTTP request/response (delegated to API routes)
    - Business logic (delegated to application services)
    - Data persistence (delegated to repositories)
    """

    def __init__(self, state_manager: UnifiedStateManager, repository_adapter=None):
        """Initialize playlist broadcasting service.

        Args:
            state_manager: UnifiedStateManager instance for WebSocket broadcasting
            repository_adapter: Optional repository adapter for fetching full playlist data
        """
        self._state_manager = state_manager
        self._repository_adapter = repository_adapter

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_playlist_created(self, playlist_id: str, playlist_data: Dict[str, Any]):
        """Broadcast playlist creation event.

        Args:
            playlist_id: ID of the created playlist
            playlist_data: Serialized playlist data
        """
        try:
            event_data = {
                "playlist_id": playlist_id,
                "playlist": playlist_data,
                "operation": "create"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.PLAYLIST_CREATED,
                event_data
            )

            logger.info(f"✅ Broadcasted playlist creation: {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast playlist creation: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_playlist_updated(self, playlist_id: str, updates: Dict[str, Any]):
        """Broadcast playlist update event with FULL playlist data.

        CRITICAL FIX: Frontend expects full playlist object in data.playlist,
        not just partial updates. This ensures all clients see the complete
        updated state immediately.

        Args:
            playlist_id: ID of the updated playlist
            updates: Dictionary of updated fields (kept for backward compatibility)
        """
        try:
            # Fetch full playlist data if repository is available
            playlist_data = None
            if self._repository_adapter:
                playlist_data = await self._get_full_playlist_data(playlist_id)

            if playlist_data:
                # CRITICAL: Send full playlist object so frontend handler works correctly
                event_data = {
                    "playlist_id": playlist_id,
                    "playlist": playlist_data,  # ✅ Full playlist data for frontend
                    "updates": updates,  # Keep for backward compatibility
                    "operation": "update"
                }
                logger.debug(f"Broadcasting full playlist data for update: {playlist_id}")
            else:
                # Fallback to partial updates if repository not available
                event_data = {
                    "playlist_id": playlist_id,
                    "updates": updates,
                    "operation": "update"
                }
                logger.warning(f"No repository available - broadcasting partial updates only for {playlist_id}")

            await self._state_manager.broadcast_state_change(
                StateEventType.PLAYLIST_UPDATED,
                event_data
            )

            logger.info(f"✅ Broadcasted playlist update: {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast playlist update: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_playlist_deleted(self, playlist_id: str):
        """Broadcast playlist deletion event.

        Args:
            playlist_id: ID of the deleted playlist
        """
        try:
            event_data = {
                "playlist_id": playlist_id,
                "operation": "delete"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.PLAYLIST_DELETED,
                event_data
            )

            logger.info(f"✅ Broadcasted playlist deletion: {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast playlist deletion: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_track_added(self, playlist_id: str, track_data: Dict[str, Any]):
        """Broadcast track addition event.

        Args:
            playlist_id: ID of the playlist
            track_data: Serialized track data
        """
        try:
            event_data = {
                "playlist_id": playlist_id,
                "track": track_data,
                "operation": "add_track"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.TRACK_ADDED,
                event_data
            )

            logger.info(f"✅ Broadcasted track addition to playlist: {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast track addition: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_tracks_deleted(self, playlist_id: str, track_numbers: List[int]):
        """Broadcast track deletion event.

        Args:
            playlist_id: ID of the playlist
            track_numbers: List of deleted track numbers
        """
        try:
            event_data = {
                "playlist_id": playlist_id,
                "track_numbers": track_numbers,
                "operation": "delete_tracks"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.TRACKS_DELETED,
                event_data
            )

            logger.info(f"✅ Broadcasted tracks deletion from playlist: {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast tracks deletion: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_tracks_reordered(self, playlist_id: str, track_order: List[int]):
        """Broadcast track reordering with FULL playlist data.

        CRITICAL FIX: Frontend removed dedicated state:tracks_reordered listener
        and now relies on state:playlists snapshot updates. We broadcast the
        full updated playlist to ensure all clients see the new track order.

        Args:
            playlist_id: ID of the playlist
            track_order: New track order (for reference)
        """
        try:
            # Fetch full playlist with reordered tracks if repository available
            playlist_data = None
            if self._repository_adapter:
                playlist_data = await self._get_full_playlist_data(playlist_id)

            if playlist_data:
                # Broadcast as PLAYLISTS_SNAPSHOT so frontend state:playlists listener picks it up
                event_data = {
                    "playlists": [playlist_data],  # Array format for state:playlists
                    "operation": "reorder_tracks"
                }

                await self._state_manager.broadcast_state_change(
                    StateEventType.PLAYLISTS_SNAPSHOT,  # Use snapshot event for compatibility
                    event_data
                )

                logger.info(f"✅ Broadcasted track reorder as playlists snapshot: {playlist_id}")
            else:
                # Fallback to old event type if repository not available
                event_data = {
                    "playlist_id": playlist_id,
                    "track_order": track_order,
                    "operation": "reorder_tracks"
                }

                await self._state_manager.broadcast_state_change(
                    StateEventType.TRACKS_REORDERED,
                    event_data
                )

                logger.warning(f"No repository - using old tracks_reordered event for {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast tracks reordering: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_playlist_started(self, playlist_id: str, track_data: Dict[str, Any] = None):
        """Broadcast playlist playback started event.

        Args:
            playlist_id: ID of the started playlist
            track_data: Current track data (optional)
        """
        try:
            event_data = {
                "playlist_id": playlist_id,
                "operation": "start_playlist"
            }

            if track_data:
                event_data["current_track"] = track_data

            await self._state_manager.broadcast_state_change(
                StateEventType.PLAYLIST_STARTED,
                event_data
            )

            logger.info(f"✅ Broadcasted playlist started: {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast playlist started: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_nfc_associated(self, playlist_id: str, nfc_tag_id: str):
        """Broadcast NFC association event.

        Args:
            playlist_id: ID of the playlist
            nfc_tag_id: NFC tag identifier
        """
        try:
            event_data = {
                "playlist_id": playlist_id,
                "nfc_tag_id": nfc_tag_id,
                "operation": "nfc_associate"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.NFC_ASSOCIATED,
                event_data
            )

            logger.info(f"✅ Broadcasted NFC association: {playlist_id} -> {nfc_tag_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast NFC association: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_nfc_disassociated(self, playlist_id: str):
        """Broadcast NFC disassociation event.

        Args:
            playlist_id: ID of the playlist
        """
        try:
            event_data = {
                "playlist_id": playlist_id,
                "operation": "nfc_disassociate"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.NFC_DISASSOCIATED,
                event_data
            )

            logger.info(f"✅ Broadcasted NFC disassociation: {playlist_id}")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast NFC disassociation: {str(e)}")

    @handle_service_errors("playlist_broadcasting")
    async def broadcast_playlists_synced(self, playlists_data: List[Dict[str, Any]]):
        """Broadcast playlists synchronization event.

        Args:
            playlists_data: List of serialized playlist data
        """
        try:
            event_data = {
                "playlists": playlists_data,
                "operation": "sync"
            }

            await self._state_manager.broadcast_state_change(
                StateEventType.PLAYLISTS_SNAPSHOT,
                event_data
            )

            logger.info(f"✅ Broadcasted playlists sync: {len(playlists_data)} playlists")

        except Exception as e:
            logger.error(f"❌ Failed to broadcast playlists sync: {str(e)}")

    async def _get_full_playlist_data(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full playlist data from repository.

        Args:
            playlist_id: ID of the playlist to fetch

        Returns:
            Full playlist data dict or None if not found/available
        """
        if not self._repository_adapter:
            return None

        try:
            playlist_dict = await self._repository_adapter.get_playlist_by_id(playlist_id)
            if not playlist_dict:
                logger.warning(f"Playlist {playlist_id} not found in repository")
                return None

            # Ensure playlist has all required fields
            return playlist_dict

        except Exception as e:
            logger.error(f"Failed to fetch full playlist data for {playlist_id}: {str(e)}")
            return None

    def get_global_sequence(self) -> int:
        """Get the current global sequence number for state synchronization.

        Returns:
            Current global sequence number
        """
        return self._state_manager.get_global_sequence()
