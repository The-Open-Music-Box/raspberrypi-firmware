# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Association Session Domain Entity."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4

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
class AssociationSession:
    """Domain entity for managing NFC tag-playlist association sessions.

    Handles the lifecycle of associating an NFC tag with a playlist,
    including timeout management and conflict resolution.
    """

    playlist_id: str
    session_id: str = field(default_factory=lambda: str(uuid4()))
    state: SessionState = SessionState.LISTENING
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    timeout_seconds: int = 60
    detected_tag: Optional[TagIdentifier] = None
    conflict_playlist_id: Optional[str] = None
    error_message: Optional[str] = None
    override_mode: bool = False  # If True, force association even if tag is already associated

    def __post_init__(self):
        """Validate session on creation."""
        if not self.playlist_id:
            raise ValueError("Playlist ID is required for association session")

    @property
    def timeout_at(self) -> datetime:
        """Calculate when this session times out."""
        return datetime.fromtimestamp(
            self.started_at.timestamp() + self.timeout_seconds, tz=timezone.utc
        )

    def is_expired(self) -> bool:
        """Check if this session has expired."""
        return datetime.now(timezone.utc) > self.timeout_at

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

    def get_remaining_seconds(self) -> int:
        """Get remaining seconds before timeout."""
        if self.is_expired():
            return 0

        remaining = self.timeout_at - datetime.now(timezone.utc)
        return max(0, int(remaining.total_seconds()))

    def to_dict(self) -> dict:
        """Convert session to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "playlist_id": self.playlist_id,
            "state": self.state.value,
            "started_at": self.started_at.isoformat(),
            "timeout_at": self.timeout_at.isoformat(),
            "remaining_seconds": self.get_remaining_seconds(),
            "detected_tag": str(self.detected_tag) if self.detected_tag else None,
            "conflict_playlist_id": self.conflict_playlist_id,
            "error_message": self.error_message,
            "override_mode": self.override_mode,
        }
