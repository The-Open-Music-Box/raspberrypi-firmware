# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Event Publisher Domain Service."""

import uuid
from typing import List, Callable, Dict, Any, Optional
from datetime import datetime

from ..events.nfc_events import (
    NfcDomainEvent,
    TagDetectedEvent,
    TagAssociatedEvent,
    TagDissociatedEvent,
    TagRemovedEvent,
    AssociationSessionStartedEvent,
    AssociationSessionCompletedEvent,
    AssociationSessionExpiredEvent,
)
from ..value_objects.tag_identifier import TagIdentifier
from app.src.monitoring import get_logger

logger = get_logger(__name__)


class NfcEventPublisher:
    """Domain service for publishing NFC events.

    Follows the domain event pattern to decouple domain logic
    from external concerns like notifications and persistence.
    """

    def __init__(self):
        """Initialize the event publisher."""
        self._event_handlers: Dict[str, List[Callable[[NfcDomainEvent], None]]] = {}
        self._published_events: List[NfcDomainEvent] = []

    def subscribe(self, event_type: str, handler: Callable[[NfcDomainEvent], None]) -> None:
        """Subscribe to a specific event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event is published
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []

        self._event_handlers[event_type].append(handler)
        logger.debug(f"📡 Subscribed handler to {event_type} events")

    def unsubscribe(self, event_type: str, handler: Callable[[NfcDomainEvent], None]) -> bool:
        """Unsubscribe from a specific event type.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove

        Returns:
            True if handler was removed, False if not found
        """
        if event_type not in self._event_handlers:
            return False

        try:
            self._event_handlers[event_type].remove(handler)
            logger.debug(f"📡 Unsubscribed handler from {event_type} events")
            return True
        except ValueError:
            return False

    def publish(self, event: NfcDomainEvent) -> None:
        """Publish a domain event to all subscribers.

        Args:
            event: Domain event to publish
        """
        self._published_events.append(event)

        handlers = self._event_handlers.get(event.event_type, [])
        logger.debug(f"📡 Publishing {event.event_type} event to {len(handlers)} handlers"
        )

        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"❌ Error in event handler for {event.event_type}: {e}"
                )

    def publish_tag_detected(
        self,
        tag_identifier: TagIdentifier,
        detection_count: int = 1,
        previously_associated_playlist_id: Optional[str] = None,
        hardware_metadata: Optional[Dict[str, Any]] = None
    ) -> TagDetectedEvent:
        """Publish a tag detected event.

        Args:
            tag_identifier: Detected tag identifier
            detection_count: Number of times tag has been detected
            previously_associated_playlist_id: Previous playlist association
            hardware_metadata: Hardware-specific metadata

        Returns:
            The published event
        """
        event = TagDetectedEvent.create(
            event_id=str(uuid.uuid4()),
            tag_identifier=tag_identifier,
            detection_count=detection_count,
            previously_associated_playlist_id=previously_associated_playlist_id,
            hardware_metadata=hardware_metadata
        )

        self.publish(event)
        return event

    def publish_tag_associated(
        self,
        tag_identifier: TagIdentifier,
        playlist_id: str,
        session_id: str,
        previous_playlist_id: Optional[str] = None
    ) -> TagAssociatedEvent:
        """Publish a tag associated event.

        Args:
            tag_identifier: Associated tag identifier
            playlist_id: New playlist association
            session_id: Association session ID
            previous_playlist_id: Previous playlist if re-associating

        Returns:
            The published event
        """
        event = TagAssociatedEvent.create(
            event_id=str(uuid.uuid4()),
            tag_identifier=tag_identifier,
            playlist_id=playlist_id,
            session_id=session_id,
            previous_playlist_id=previous_playlist_id
        )

        self.publish(event)
        return event

    def publish_tag_dissociated(
        self,
        tag_identifier: TagIdentifier,
        previous_playlist_id: str,
        reason: str = "manual_dissociation"
    ) -> TagDissociatedEvent:
        """Publish a tag dissociated event.

        Args:
            tag_identifier: Dissociated tag identifier
            previous_playlist_id: Previous playlist association
            reason: Reason for dissociation

        Returns:
            The published event
        """
        event = TagDissociatedEvent.create(
            event_id=str(uuid.uuid4()),
            tag_identifier=tag_identifier,
            previous_playlist_id=previous_playlist_id,
            reason=reason
        )

        self.publish(event)
        return event

    def publish_tag_removed(
        self,
        tag_identifier: Optional[TagIdentifier] = None,
        detection_duration_seconds: Optional[float] = None
    ) -> TagRemovedEvent:
        """Publish a tag removed event.

        Args:
            tag_identifier: Removed tag identifier (if known)
            detection_duration_seconds: How long tag was detected

        Returns:
            The published event
        """
        event = TagRemovedEvent.create(
            event_id=str(uuid.uuid4()),
            tag_identifier=tag_identifier,
            detection_duration_seconds=detection_duration_seconds
        )

        self.publish(event)
        return event

    def publish_association_session_started(
        self,
        session_id: str,
        playlist_id: str,
        timeout_seconds: int = 60
    ) -> AssociationSessionStartedEvent:
        """Publish an association session started event.

        Args:
            session_id: Session identifier
            playlist_id: Target playlist ID
            timeout_seconds: Session timeout

        Returns:
            The published event
        """
        event = AssociationSessionStartedEvent.create(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            playlist_id=playlist_id,
            timeout_seconds=timeout_seconds
        )

        self.publish(event)
        return event

    def publish_association_session_completed(
        self,
        session_id: str,
        playlist_id: str,
        tag_identifier: TagIdentifier,
        duration_seconds: float
    ) -> AssociationSessionCompletedEvent:
        """Publish an association session completed event.

        Args:
            session_id: Session identifier
            playlist_id: Associated playlist ID
            tag_identifier: Associated tag identifier
            duration_seconds: Session duration

        Returns:
            The published event
        """
        event = AssociationSessionCompletedEvent.create(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            playlist_id=playlist_id,
            tag_identifier=tag_identifier,
            duration_seconds=duration_seconds
        )

        self.publish(event)
        return event

    def publish_association_session_expired(
        self,
        session_id: str,
        playlist_id: str,
        timeout_seconds: int,
        tags_detected_during_session: int = 0
    ) -> AssociationSessionExpiredEvent:
        """Publish an association session expired event.

        Args:
            session_id: Session identifier
            playlist_id: Target playlist ID
            timeout_seconds: Session timeout
            tags_detected_during_session: Number of tags detected during session

        Returns:
            The published event
        """
        event = AssociationSessionExpiredEvent.create(
            event_id=str(uuid.uuid4()),
            session_id=session_id,
            playlist_id=playlist_id,
            timeout_seconds=timeout_seconds,
            tags_detected_during_session=tags_detected_during_session
        )

        self.publish(event)
        return event

    def get_published_events(self) -> List[NfcDomainEvent]:
        """Get all published events.

        Returns:
            List of all published events
        """
        return self._published_events.copy()

    def clear_published_events(self) -> None:
        """Clear the published events list."""
        self._published_events.clear()

    def get_subscriber_count(self, event_type: str) -> int:
        """Get number of subscribers for an event type.

        Args:
            event_type: Event type to check

        Returns:
            Number of subscribers
        """
        return len(self._event_handlers.get(event_type, []))