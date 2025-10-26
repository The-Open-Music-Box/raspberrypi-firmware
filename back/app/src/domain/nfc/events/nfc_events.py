# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Domain Events."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..value_objects.tag_identifier import TagIdentifier


@dataclass(frozen=True)
class NfcDomainEvent:
    """Base class for all NFC domain events."""

    event_id: str
    occurred_at: datetime
    event_type: str

    def __post_init__(self):
        """Ensure occurred_at is timezone-aware."""
        if self.occurred_at.tzinfo is None:
            object.__setattr__(self, 'occurred_at', self.occurred_at.replace(tzinfo=timezone.utc))


@dataclass(frozen=True)
class TagDetectedEvent(NfcDomainEvent):
    """Event fired when an NFC tag is detected."""

    tag_identifier: TagIdentifier
    detection_count: int
    previously_associated_playlist_id: Optional[str] = None
    hardware_metadata: Dict[str, Any] = None

    @classmethod
    def create(
        cls,
        event_id: str,
        tag_identifier: TagIdentifier,
        detection_count: int = 1,
        previously_associated_playlist_id: Optional[str] = None,
        hardware_metadata: Optional[Dict[str, Any]] = None
    ) -> "TagDetectedEvent":
        """Create a new tag detected event."""
        return cls(
            event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
            event_type="tag_detected",
            tag_identifier=tag_identifier,
            detection_count=detection_count,
            previously_associated_playlist_id=previously_associated_playlist_id,
            hardware_metadata=hardware_metadata or {}
        )


@dataclass(frozen=True)
class TagAssociatedEvent(NfcDomainEvent):
    """Event fired when an NFC tag is associated with a playlist."""

    tag_identifier: TagIdentifier
    playlist_id: str
    session_id: str
    previous_playlist_id: Optional[str] = None

    @classmethod
    def create(
        cls,
        event_id: str,
        tag_identifier: TagIdentifier,
        playlist_id: str,
        session_id: str,
        previous_playlist_id: Optional[str] = None
    ) -> "TagAssociatedEvent":
        """Create a new tag associated event."""
        return cls(
            event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
            event_type="tag_associated",
            tag_identifier=tag_identifier,
            playlist_id=playlist_id,
            session_id=session_id,
            previous_playlist_id=previous_playlist_id
        )


@dataclass(frozen=True)
class TagDissociatedEvent(NfcDomainEvent):
    """Event fired when an NFC tag is dissociated from a playlist."""

    tag_identifier: TagIdentifier
    previous_playlist_id: str
    reason: str = "manual_dissociation"

    @classmethod
    def create(
        cls,
        event_id: str,
        tag_identifier: TagIdentifier,
        previous_playlist_id: str,
        reason: str = "manual_dissociation"
    ) -> "TagDissociatedEvent":
        """Create a new tag dissociated event."""
        return cls(
            event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
            event_type="tag_dissociated",
            tag_identifier=tag_identifier,
            previous_playlist_id=previous_playlist_id,
            reason=reason
        )


@dataclass(frozen=True)
class TagRemovedEvent(NfcDomainEvent):
    """Event fired when an NFC tag is removed from the reader."""

    tag_identifier: Optional[TagIdentifier]
    detection_duration_seconds: Optional[float] = None

    @classmethod
    def create(
        cls,
        event_id: str,
        tag_identifier: Optional[TagIdentifier] = None,
        detection_duration_seconds: Optional[float] = None
    ) -> "TagRemovedEvent":
        """Create a new tag removed event."""
        return cls(
            event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
            event_type="tag_removed",
            tag_identifier=tag_identifier,
            detection_duration_seconds=detection_duration_seconds
        )


@dataclass(frozen=True)
class AssociationSessionStartedEvent(NfcDomainEvent):
    """Event fired when an association session is started."""

    session_id: str
    playlist_id: str
    timeout_seconds: int

    @classmethod
    def create(
        cls,
        event_id: str,
        session_id: str,
        playlist_id: str,
        timeout_seconds: int = 60
    ) -> "AssociationSessionStartedEvent":
        """Create a new association session started event."""
        return cls(
            event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
            event_type="association_session_started",
            session_id=session_id,
            playlist_id=playlist_id,
            timeout_seconds=timeout_seconds
        )


@dataclass(frozen=True)
class AssociationSessionCompletedEvent(NfcDomainEvent):
    """Event fired when an association session is completed successfully."""

    session_id: str
    playlist_id: str
    tag_identifier: TagIdentifier
    duration_seconds: float

    @classmethod
    def create(
        cls,
        event_id: str,
        session_id: str,
        playlist_id: str,
        tag_identifier: TagIdentifier,
        duration_seconds: float
    ) -> "AssociationSessionCompletedEvent":
        """Create a new association session completed event."""
        return cls(
            event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
            event_type="association_session_completed",
            session_id=session_id,
            playlist_id=playlist_id,
            tag_identifier=tag_identifier,
            duration_seconds=duration_seconds
        )


@dataclass(frozen=True)
class AssociationSessionExpiredEvent(NfcDomainEvent):
    """Event fired when an association session expires without completion."""

    session_id: str
    playlist_id: str
    timeout_seconds: int
    tags_detected_during_session: int = 0

    @classmethod
    def create(
        cls,
        event_id: str,
        session_id: str,
        playlist_id: str,
        timeout_seconds: int,
        tags_detected_during_session: int = 0
    ) -> "AssociationSessionExpiredEvent":
        """Create a new association session expired event."""
        return cls(
            event_id=event_id,
            occurred_at=datetime.now(timezone.utc),
            event_type="association_session_expired",
            session_id=session_id,
            playlist_id=playlist_id,
            timeout_seconds=timeout_seconds,
            tags_detected_during_session=tags_detected_during_session
        )