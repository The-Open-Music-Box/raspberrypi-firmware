# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Association Session Domain Entity."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.src.domain.base.base_session_entity import BaseSessionEntity

from ..value_objects.tag_identifier import TagIdentifier


class SessionState(Enum):
    """States of an association session."""

    LISTENING = "listening"
    DUPLICATE = "duplicate"
    SUCCESS = "success"
    STOPPED = "stopped"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class AssociationSession(BaseSessionEntity):
    """Domain entity for managing NFC tag-playlist association sessions.

    Handles the lifecycle of associating an NFC tag with a playlist,
    including timeout management and conflict resolution.

    Inherits common session patterns from BaseSessionEntity.
    """

    playlist_id: str = ""
    state: SessionState = SessionState.LISTENING
    timeout_seconds: int = 60  # Override base class default
    detected_tag: TagIdentifier | None = None
    conflict_playlist_id: str | None = None
    error_message: str | None = None
    override_mode: bool = False  # If True, force association even if tag is already associated

    @property
    def started_at(self) -> datetime:
        """Alias for created_at for backwards compatibility."""
        return self.created_at

    def __post_init__(self):
        """Validate session on creation."""
        if not self.playlist_id:
            raise ValueError("Playlist ID is required for association session")

    def is_active(self) -> bool:
        """Check if this session is active.

        A session is active if it's in LISTENING or DUPLICATE state and not expired.
        DUPLICATE state keeps the session active to prevent playback while waiting
        for user decision (override or cancel).
        """
        return self.state in [SessionState.LISTENING, SessionState.DUPLICATE] and not self.is_expired()

    def detect_tag(self, tag_identifier: TagIdentifier) -> None:
        """Record tag detection in this session.

        Args:
            tag_identifier: The detected tag identifier
        """
        if not self.is_active():
            raise ValueError("Cannot detect tag in inactive session")

        self.detected_tag = tag_identifier

    def mark_successful(self) -> None:
        """Mark this session as successfully completed."""
        if self.state != SessionState.LISTENING:
            raise ValueError("Can only mark listening sessions as successful")

        self.state = SessionState.SUCCESS

    def mark_duplicate(self, existing_playlist_id: str) -> None:
        """Mark this session as having a duplicate association conflict.

        Args:
            existing_playlist_id: ID of playlist already associated with the tag
        """
        if self.state != SessionState.LISTENING:
            raise ValueError("Can only mark listening sessions as duplicate")

        self.state = SessionState.DUPLICATE
        self.conflict_playlist_id = existing_playlist_id

    def mark_stopped(self) -> None:
        """Mark this session as manually stopped."""
        if self.state not in [SessionState.LISTENING, SessionState.DUPLICATE]:
            raise ValueError("Can only stop active sessions")

        self.state = SessionState.STOPPED

    def mark_cancelled(self) -> None:
        """Mark this session as cancelled by user."""
        if self.state not in [SessionState.LISTENING, SessionState.DUPLICATE]:
            raise ValueError("Can only cancel active sessions")

        self.state = SessionState.CANCELLED

    def mark_timeout(self) -> None:
        """Mark this session as timed out."""
        if self.state != SessionState.LISTENING:
            raise ValueError("Can only timeout listening sessions")

        self.state = SessionState.TIMEOUT

    def mark_error(self, error_message: str) -> None:
        """Mark this session as having an error.

        Args:
            error_message: Description of the error
        """
        self.state = SessionState.ERROR
        self.error_message = error_message

    def to_dict(self) -> dict:
        """Convert session to dictionary for serialization."""
        # Start with base class common fields
        result = self._base_dict_fields()

        # Add domain-specific fields
        result.update({
            "playlist_id": self.playlist_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),  # For backwards compatibility
            "detected_tag": str(self.detected_tag) if self.detected_tag else None,
            "conflict_playlist_id": self.conflict_playlist_id,
            "error_message": self.error_message,
            "override_mode": self.override_mode,
        })

        return result
