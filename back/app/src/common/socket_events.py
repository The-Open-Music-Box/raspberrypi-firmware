# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Standardized Socket.IO event system for TheOpenMusicBox.

This module defines consistent event structures, naming conventions,
and envelope formats for all WebSocket communications.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum
import time
import uuid


class SocketEventType(str, Enum):
    """Canonical Socket.IO event types following standardized naming convention."""

    # Connection management
    CONNECTION_STATUS = "connection_status"

    # Room subscription management
    JOIN_PLAYLISTS = "join:playlists"
    LEAVE_PLAYLISTS = "leave:playlists"
    JOIN_PLAYLIST = "join:playlist"
    LEAVE_PLAYLIST = "leave:playlist"
    JOIN_NFC = "join:nfc"
    ACK_JOIN = "ack:join"
    ACK_LEAVE = "ack:leave"

    # State synchronization events (canonical state:* pattern)
    STATE_PLAYLISTS = "state:playlists"
    STATE_PLAYLISTS_INDEX_UPDATE = "state:playlists_index_update"
    STATE_PLAYLIST = "state:playlist"
    STATE_PLAYER = "state:player"
    STATE_TRACK_PROGRESS = "state:track_progress"
    STATE_TRACK_POSITION = "state:track_position"  # Lightweight position-only updates
    STATE_TRACK = "state:track"

    # Playlist-specific action events
    STATE_PLAYLIST_CREATED = "state:playlist_created"
    STATE_PLAYLIST_UPDATED = "state:playlist_updated"
    STATE_PLAYLIST_DELETED = "state:playlist_deleted"
    STATE_TRACK_ADDED = "state:track_added"
    STATE_TRACK_DELETED = "state:track_deleted"

    # Operation acknowledgments
    ACK_OPERATION = "ack:op"
    ERROR_OPERATION = "err:op"

    # Synchronization protocol
    SYNC_REQUEST = "sync:request"
    SYNC_COMPLETE = "sync:complete"
    SYNC_ERROR = "sync:error"

    # Upload progress events
    UPLOAD_PROGRESS = "upload:progress"
    UPLOAD_COMPLETE = "upload:complete"
    UPLOAD_ERROR = "upload:error"

    # NFC events
    NFC_STATUS = "nfc_status"
    NFC_ASSOCIATION_STATE = "nfc_association_state"

    # YouTube events
    YOUTUBE_PROGRESS = "youtube:progress"
    YOUTUBE_COMPLETE = "youtube:complete"
    YOUTUBE_ERROR = "youtube:error"


class StateEventType(Enum):
    """Types of state events that can be broadcast per API Contract v2.0."""

    PLAYLISTS_SNAPSHOT = "state:playlists"
    PLAYLISTS_INDEX_UPDATE = "state:playlists_index_update"
    PLAYLIST_SNAPSHOT = "state:playlist"
    TRACK_SNAPSHOT = "state:track"
    PLAYER_STATE = "state:player"
    TRACK_PROGRESS = "state:track_progress"
    TRACK_POSITION = "state:track_position"

    PLAYLIST_DELETED = "state:playlist_deleted"
    PLAYLIST_CREATED = "state:playlist_created"
    PLAYLIST_UPDATED = "state:playlist_updated"
    TRACK_DELETED = "state:track_deleted"
    TRACK_ADDED = "state:track_added"

    VOLUME_CHANGED = "state:volume_changed"
    NFC_STATE = "state:nfc_state"

    # Additional event types for DDD broadcasting service
    TRACKS_DELETED = "state:tracks_deleted"
    TRACKS_REORDERED = "state:tracks_reordered"
    PLAYLIST_STARTED = "state:playlist_started"
    NFC_ASSOCIATED = "state:nfc_associated"
    NFC_DISASSOCIATED = "state:nfc_disassociated"

    # Legacy aliases
    GENERAL = "state:general"
    ERROR = "state:error"
    NFC_ASSOCIATION = "state:nfc_association"
    POSITION_UPDATE = "state:position_update"


class StateEventEnvelope(BaseModel):
    """
    Standardized envelope for all state:* events.

    This ensures consistent event structure across all state changes
    and provides necessary metadata for client synchronization.
    """

    event_type: SocketEventType = Field(..., description="Type of state event")
    server_seq: int = Field(..., description="Global server sequence number")
    data: Dict[str, Any] = Field(..., description="Event payload data")
    timestamp: int = Field(
        default_factory=lambda: int(time.time() * 1000),
        description="Event timestamp in milliseconds",
    )
    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8], description="Unique event identifier"
    )

    # Optional fields for specific event types
    playlist_id: Optional[str] = Field(None, description="Playlist ID for playlist-specific events")
    playlist_seq: Optional[int] = Field(None, description="Playlist-specific sequence number")


class ConnectionStatusPayload(BaseModel):
    """Payload for connection_status events."""

    status: str = Field("connected", description="Connection status")
    sid: str = Field(..., description="Socket session ID")
    server_seq: int = Field(..., description="Current server sequence number")
    server_time: int = Field(
        default_factory=lambda: int(time.time() * 1000), description="Server timestamp"
    )


class RoomAcknowledgmentPayload(BaseModel):
    """Payload for room join/leave acknowledgments."""

    room: str = Field(..., description="Room name that was joined/left")
    success: bool = Field(..., description="Whether operation was successful")
    server_seq: Optional[int] = Field(None, description="Current server sequence number")
    playlist_seq: Optional[int] = Field(
        None, description="Playlist sequence if joining playlist room"
    )
    message: Optional[str] = Field(None, description="Optional status message")


class OperationAcknowledgmentPayload(BaseModel):
    """Payload for operation acknowledgments (ack:op/err:op)."""

    client_op_id: str = Field(..., description="Client operation identifier")
    success: bool = Field(..., description="Whether operation succeeded")
    server_seq: int = Field(..., description="Current server sequence number")
    data: Optional[Dict[str, Any]] = Field(None, description="Operation result data")
    message: Optional[str] = Field(None, description="Success/error message")


class SyncRequestPayload(BaseModel):
    """Payload for sync:request events from clients."""

    last_global_seq: Optional[int] = Field(None, description="Last known global sequence number")
    last_playlist_seqs: Optional[Dict[str, int]] = Field(
        None, description="Last known playlist sequence numbers"
    )
    requested_rooms: Optional[list[str]] = Field(None, description="Rooms client wants to sync")


class UploadProgressPayload(BaseModel):
    """Payload for upload progress events."""

    playlist_id: str = Field(..., description="Target playlist ID")
    session_id: str = Field(..., description="Upload session ID")
    chunk_index: Optional[int] = Field(None, description="Current chunk index")
    progress: float = Field(..., ge=0.0, le=100.0, description="Upload progress percentage")
    complete: bool = Field(False, description="Whether upload is complete")
    filename: Optional[str] = Field(None, description="Filename being uploaded")
    error: Optional[str] = Field(None, description="Error message if upload failed")


class NFCStatusPayload(BaseModel):
    """Payload for NFC status events."""

    assoc_id: str = Field(..., description="Association session ID")
    state: str = Field(..., description="Association state")
    playlist_id: str = Field(..., description="Target playlist ID")
    tag_id: Optional[str] = Field(None, description="Detected NFC tag ID")
    conflict_playlist_id: Optional[str] = Field(
        None, description="Conflicting playlist ID if duplicate"
    )
    started_at: str = Field(..., description="Session start time")
    timeout_at: str = Field(..., description="Session timeout time")
    server_seq: int = Field(..., description="Server sequence number")


class NFCAssociationStatePayload(BaseModel):
    """Frontend-friendly NFC association payload."""

    state: str = Field(..., description="Association state")
    playlist_id: str = Field(..., description="Target playlist ID")
    tag_id: Optional[str] = Field(None, description="NFC tag ID")
    message: Optional[str] = Field(None, description="User-friendly message")
    expires_at: Optional[str] = Field(None, description="Session expiration time")
    existing_playlist: Optional[Dict[str, str]] = Field(
        None, description="Existing playlist info if conflict"
    )
    server_seq: int = Field(..., description="Server sequence number")


class YouTubeProgressPayload(BaseModel):
    """Payload for YouTube download progress events."""

    task_id: str = Field(..., description="Download task ID")
    status: str = Field(..., description="Download status")
    progress_percent: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="Progress percentage"
    )
    current_step: Optional[str] = Field(None, description="Current processing step")
    estimated_time_remaining: Optional[int] = Field(None, description="ETA in seconds")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SocketEventBuilder:
    """
    Builder class for creating standardized Socket.IO events.

    This ensures all events follow consistent formatting and include
    required metadata for proper client synchronization.
    """

    @staticmethod
    def create_state_event(
        event_type: SocketEventType,
        data: Dict[str, Any],
        server_seq: int,
        playlist_id: Optional[str] = None,
        playlist_seq: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Create a standardized state event with envelope.

        Args:
            event_type: Type of state event
            data: Event payload data
            server_seq: Global server sequence number
            playlist_id: Optional playlist ID for playlist-specific events
            playlist_seq: Optional playlist sequence number

        Returns:
            Complete event data ready for Socket.IO emission
        """
        envelope = StateEventEnvelope(
            event_type=event_type,
            server_seq=server_seq,
            data=data,
            playlist_id=playlist_id,
            playlist_seq=playlist_seq,
        )

        return envelope.model_dump(exclude_none=True)

    @staticmethod
    def create_connection_status_event(sid: str, server_seq: int) -> Dict[str, Any]:
        """Create connection status event."""
        payload = ConnectionStatusPayload(sid=sid, server_seq=server_seq)
        return payload.model_dump()

    @staticmethod
    def create_room_ack_event(
        room: str,
        success: bool,
        server_seq: Optional[int] = None,
        playlist_seq: Optional[int] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create room acknowledgment event."""
        payload = RoomAcknowledgmentPayload(
            room=room,
            success=success,
            server_seq=server_seq,
            playlist_seq=playlist_seq,
            message=message,
        )
        return payload.model_dump(exclude_none=True)

    @staticmethod
    def create_operation_ack_event(
        client_op_id: str,
        success: bool,
        server_seq: int,
        data: Optional[Dict[str, Any]] = None,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create operation acknowledgment event."""
        payload = OperationAcknowledgmentPayload(
            client_op_id=client_op_id,
            success=success,
            server_seq=server_seq,
            data=data,
            message=message,
        )
        return payload.model_dump(exclude_none=True)

    @staticmethod
    def create_upload_progress_event(
        playlist_id: str,
        session_id: str,
        progress: float,
        complete: bool = False,
        chunk_index: Optional[int] = None,
        filename: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create upload progress event."""
        payload = UploadProgressPayload(
            playlist_id=playlist_id,
            session_id=session_id,
            progress=progress,
            complete=complete,
            chunk_index=chunk_index,
            filename=filename,
            error=error,
        )
        return payload.model_dump(exclude_none=True)


# Event routing configuration
EVENT_ROOM_MAPPING = {
    SocketEventType.STATE_PLAYLISTS: "playlists",
    SocketEventType.STATE_PLAYLISTS_INDEX_UPDATE: "playlists",
    SocketEventType.STATE_PLAYER: "playlists",
    SocketEventType.STATE_TRACK_PROGRESS: "playlists",
    SocketEventType.STATE_TRACK_POSITION: "playlists",  # Lightweight position updates to all
    SocketEventType.STATE_PLAYLIST: "playlist:{playlist_id}",
    SocketEventType.STATE_TRACK: "playlist:{playlist_id}",
    SocketEventType.STATE_PLAYLIST_CREATED: "playlists",
    SocketEventType.STATE_PLAYLIST_UPDATED: "playlists",
    SocketEventType.STATE_PLAYLIST_DELETED: "playlists",
    SocketEventType.STATE_TRACK_ADDED: "playlist:{playlist_id}",
    SocketEventType.STATE_TRACK_DELETED: "playlist:{playlist_id}",
    SocketEventType.NFC_STATUS: "nfc",
    SocketEventType.NFC_ASSOCIATION_STATE: "nfc",
    SocketEventType.UPLOAD_PROGRESS: "playlist:{playlist_id}",
    SocketEventType.UPLOAD_COMPLETE: "playlist:{playlist_id}",
    SocketEventType.UPLOAD_ERROR: "playlist:{playlist_id}",
    SocketEventType.YOUTUBE_PROGRESS: "playlists",
    SocketEventType.YOUTUBE_COMPLETE: "playlists",
    SocketEventType.YOUTUBE_ERROR: "playlists",
}


def get_event_room(event_type: SocketEventType, playlist_id: Optional[str] = None) -> str:
    """
    Get the appropriate room for an event type.

    Args:
        event_type: Type of Socket.IO event
        playlist_id: Optional playlist ID for playlist-specific events

    Returns:
        Room name where event should be emitted

    Raises:
        ValueError: If playlist_id is required but not provided
    """
    room_template = EVENT_ROOM_MAPPING.get(event_type)
    if not room_template:
        raise ValueError(f"No room mapping defined for event type: {event_type}")

    if "{playlist_id}" in room_template:
        if not playlist_id:
            raise ValueError(f"playlist_id required for event type: {event_type}")
        return room_template.format(playlist_id=playlist_id)

    return room_template
