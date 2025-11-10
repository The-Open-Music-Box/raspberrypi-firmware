# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
NFC Handlers for WebSocket Events

This module handles NFC association operations:
- Starting new NFC associations
- Canceling active associations
- Overriding existing tag associations
"""

import time
from typing import Dict, Any, Optional
from datetime import datetime

import socketio

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.domain.audio.engine.state_manager import StateManager
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier

logger = get_logger(__name__)


class NFCHandlers:
    """Handles WebSocket events for NFC tag association operations.

    This handler manages:
    - Starting NFC association sessions
    - Canceling active association sessions
    - Overriding existing tag associations with new playlists
    """

    def __init__(
        self,
        sio: socketio.AsyncServer,
        state_manager: StateManager,
        nfc_service: Any,
    ):
        """Initialize the NFC handlers.

        Args:
            sio: The Socket.IO server instance for event registration
            state_manager: The state manager for sequence numbers and acknowledgments
            nfc_service: The NFC application service for tag operations
        """
        self.sio = sio
        self.state_manager = state_manager
        self.nfc_service = nfc_service

    def register(self) -> None:
        """Register all NFC-related event handlers.

        This method registers handlers for:
        - 'start_nfc_link': Start a new NFC association session
        - 'stop_nfc_link': Cancel an active association session
        - 'override_nfc_tag': Override an existing tag association
        """

        @self.sio.on("start_nfc_link")
        @handle_http_errors()
        async def handle_start_nfc_link(sid: str, data: Dict[str, Any]) -> None:
            """Handle NFC association start via WebSocket.

            Initiates a new NFC association session for a playlist. The client
            can then scan an NFC tag to link it to the playlist.

            Args:
                sid: The Socket.IO session identifier for the requesting client
                data: The request payload containing:
                    - playlist_id (required): The playlist to associate
                    - client_op_id (optional): Client operation ID for acknowledgment

            Raises:
                ValueError: If 'playlist_id' is not provided
                Exception: If NFC service is not available

            Side Effects:
                - Starts an NFC association session
                - Emits 'nfc_association_state' with 'activated' state
                - Sends operation acknowledgment if client_op_id provided
                - Logs operation at INFO level
            """
            try:
                playlist_id = data.get("playlist_id")
                client_op_id = data.get("client_op_id")
                if not playlist_id:
                    raise ValueError("playlist_id is required")

                logger.info(
                    f"Starting NFC association for playlist {playlist_id} from client {sid}"
                )

                # Start association using the service
                result = await self.nfc_service.start_association_use_case(playlist_id)

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

                logger.info(
                    f"NFC association started successfully for playlist {playlist_id}"
                )
            except Exception as e:
                logger.error(
                    f"Error in handle_start_nfc_link: {str(e)}",
                    extra={
                        "sid": sid,
                        "client_op_id": data.get("client_op_id") if isinstance(data, dict) else None,
                        "playlist_id": data.get("playlist_id") if isinstance(data, dict) else None,
                        "operation": "start_nfc_link",
                    },
                    exc_info=True
                )
                raise

        @self.sio.on("stop_nfc_link")
        @handle_http_errors()
        async def handle_stop_nfc_link(sid: str, data: Dict[str, Any]) -> None:
            """Handle NFC association cancellation via WebSocket.

            Cancels an active NFC association session for a playlist.

            Args:
                sid: The Socket.IO session identifier for the requesting client
                data: The request payload containing:
                    - playlist_id (required): The playlist whose association to cancel
                    - client_op_id (optional): Client operation ID for acknowledgment

            Raises:
                ValueError: If 'playlist_id' is not provided
                Exception: If NFC service is not available

            Side Effects:
                - Cancels the active association session
                - Emits 'nfc_association_state' with 'cancelled' state
                - Sends operation acknowledgment if client_op_id provided
                - Logs operation at INFO level
            """
            try:
                playlist_id = data.get("playlist_id")
                client_op_id = data.get("client_op_id")
                if not playlist_id:
                    raise ValueError("playlist_id is required")

                logger.info(
                    f"Stopping NFC association for playlist {playlist_id} from client {sid}"
                )

                # Cancel association - need to find the association ID
                # For now, we'll use a simplified approach
                result = await self.nfc_service.cancel_association_by_playlist(playlist_id)

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
                        client_op_id,
                        True,
                        {"playlist_id": playlist_id, "status": "cancelled"},
                    )

                logger.info(f"NFC association cancelled for playlist {playlist_id}")
            except Exception as e:
                logger.error(
                    f"Error in handle_stop_nfc_link: {str(e)}",
                    extra={
                        "sid": sid,
                        "client_op_id": data.get("client_op_id") if isinstance(data, dict) else None,
                        "playlist_id": data.get("playlist_id") if isinstance(data, dict) else None,
                        "operation": "stop_nfc_link",
                    },
                    exc_info=True
                )
                raise

        @self.sio.on("override_nfc_tag")
        @handle_http_errors()
        async def handle_override_nfc_tag(sid: str, data: Dict[str, Any]) -> None:
            """Handle NFC tag override via WebSocket.

            Starts a new association session in override mode and immediately processes
            the tag if tag_id is provided (no need to scan again). This allows
            re-associating an already-linked NFC tag with a different playlist.

            Args:
                sid: The Socket.IO session identifier for the requesting client
                data: The request payload containing:
                    - playlist_id (required): The new playlist to associate
                    - tag_id (optional): The tag ID from duplicate detection
                    - client_op_id (optional): Client operation ID for acknowledgment

            Raises:
                ValueError: If 'playlist_id' is not provided
                Exception: If NFC service is not available

            Side Effects:
                - Starts an NFC association session in override mode
                - If tag_id provided: Immediately processes the tag association
                - If no tag_id: Emits 'nfc_association_state' with 'waiting' state
                - Sends operation acknowledgment if client_op_id provided
                - Logs operation at INFO level
            """
            try:
                playlist_id = data.get("playlist_id")
                tag_id = data.get("tag_id")  # Get the tag_id from duplicate detection
                client_op_id = data.get("client_op_id")
                if not playlist_id:
                    raise ValueError("playlist_id is required")

                logger.info(
                    f"Overriding NFC tag {tag_id} for playlist {playlist_id} from client {sid}"
                )

                # Start override session and process tag if provided
                session_id = await self._start_override_session(
                    playlist_id, tag_id, sid, client_op_id
                )

                logger.info(
                    f"NFC tag override started for playlist {playlist_id} (session: {session_id})"
                )
            except Exception as e:
                logger.error(
                    f"Error in handle_override_nfc_tag: {str(e)}",
                    extra={
                        "sid": sid,
                        "client_op_id": data.get("client_op_id") if isinstance(data, dict) else None,
                        "playlist_id": data.get("playlist_id") if isinstance(data, dict) else None,
                        "tag_id": data.get("tag_id") if isinstance(data, dict) else None,
                        "operation": "override_nfc_tag",
                    },
                    exc_info=True
                )
                raise

    async def _start_override_session(
        self,
        playlist_id: str,
        tag_id: Optional[str],
        sid: str,
        client_op_id: Optional[str],
    ) -> str:
        """Start an NFC override session and optionally process a tag immediately.

        Args:
            playlist_id: The playlist to associate
            tag_id: Optional tag identifier to process immediately
            sid: The client session identifier
            client_op_id: Optional client operation ID for acknowledgment

        Returns:
            The session ID of the created override session

        Side Effects:
            - Starts an NFC association session in override mode
            - If tag_id provided: Processes the tag immediately
            - If no tag_id: Emits waiting state to client
            - Sends acknowledgment if client_op_id provided
        """
        # Start association in override mode
        result = await self.nfc_service.start_association_use_case(
            playlist_id,
            timeout_seconds=60,
            override_mode=True,  # Force association even if tag already associated
        )

        # Get session info
        session = result.get("session", {})
        session_id = session.get("session_id")
        timeout_at = session.get("timeout_at")

        # Calculate expires_at timestamp for frontend countdown
        expires_at = self._calculate_expires_at(timeout_at)

        # If tag_id is provided, immediately process it (no need to scan again)
        if tag_id:
            await self._process_tag_override(tag_id, sid)
        else:
            # No tag_id provided, emit waiting state (old behavior)
            await self._emit_waiting_state(
                sid, playlist_id, session_id, expires_at
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

        return session_id

    def _calculate_expires_at(self, timeout_at: Optional[str]) -> float:
        """Calculate expiration timestamp for frontend countdown.

        Args:
            timeout_at: ISO format timestamp string, or None

        Returns:
            Unix timestamp for expiration (current time + 60s if timeout_at is None)
        """
        if timeout_at:
            return datetime.fromisoformat(
                timeout_at.replace("Z", "+00:00")
            ).timestamp()
        else:
            return time.time() + 60

    async def _process_tag_override(
        self, tag_id: str, sid: str
    ) -> None:
        """Process an immediate tag override without requiring a scan.

        Args:
            tag_id: The tag identifier to process
            sid: The client session identifier for logging

        Side Effects:
            - Processes the tag detection through NFC service
            - Logs the operation at INFO level
        """
        logger.info(f"Processing saved tag {tag_id} immediately for override")

        # Create tag identifier from saved tag_id
        tag_identifier = TagIdentifier(uid=tag_id)

        # Process the tag immediately for this override session
        await self.nfc_service._handle_tag_detection(tag_identifier)

        logger.info(f"Override completed automatically for tag {tag_id}")

    async def _emit_waiting_state(
        self,
        sid: str,
        playlist_id: str,
        session_id: str,
        expires_at: float,
    ) -> None:
        """Emit waiting state for tag scan during override.

        Args:
            sid: The client session identifier
            playlist_id: The playlist being associated
            session_id: The association session identifier
            expires_at: Unix timestamp when the session expires

        Side Effects:
            - Emits 'nfc_association_state' event with 'waiting' state
        """
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
