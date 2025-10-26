# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unit tests for NFC domain events."""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock

from app.src.domain.nfc.events.nfc_events import (
    NfcDomainEvent,
    TagDetectedEvent,
    TagAssociatedEvent,
    TagDissociatedEvent,
    TagRemovedEvent,
    AssociationSessionStartedEvent,
    AssociationSessionCompletedEvent,
    AssociationSessionExpiredEvent,
)
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier


class TestNfcDomainEvent:
    """Test the base NFC domain event."""

    def test_event_creation(self):
        """Test basic event creation."""
        event_id = "test-event-123"
        occurred_at = datetime.now(timezone.utc)
        event_type = "test_event"

        event = NfcDomainEvent(
            event_id=event_id,
            occurred_at=occurred_at,
            event_type=event_type
        )

        assert event.event_id == event_id
        assert event.occurred_at == occurred_at
        assert event.event_type == event_type

    def test_timezone_handling(self):
        """Test that timezone-naive datetimes are converted to UTC."""
        naive_datetime = datetime.now()  # No timezone

        event = NfcDomainEvent(
            event_id="test-123",
            occurred_at=naive_datetime,
            event_type="test"
        )

        assert event.occurred_at.tzinfo == timezone.utc

    def test_immutability(self):
        """Test that events are immutable."""
        event = NfcDomainEvent(
            event_id="test-123",
            occurred_at=datetime.now(timezone.utc),
            event_type="test"
        )

        with pytest.raises(AttributeError):
            event.event_id = "modified"


class TestTagDetectedEvent:
    """Test tag detected event."""

    def test_create_basic_event(self):
        """Test creating a basic tag detected event."""
        tag_id = TagIdentifier(uid="abcd1234")

        event = TagDetectedEvent.create(
            event_id="event-123",
            tag_identifier=tag_id,
            detection_count=1
        )

        assert event.event_type == "tag_detected"
        assert event.tag_identifier == tag_id
        assert event.detection_count == 1
        assert event.previously_associated_playlist_id is None
        assert event.hardware_metadata == {}

    def test_create_with_previous_association(self):
        """Test creating event with previous playlist association."""
        tag_id = TagIdentifier(uid="abcd1234")
        playlist_id = "playlist-456"

        event = TagDetectedEvent.create(
            event_id="event-123",
            tag_identifier=tag_id,
            detection_count=5,
            previously_associated_playlist_id=playlist_id
        )

        assert event.previously_associated_playlist_id == playlist_id
        assert event.detection_count == 5

    def test_create_with_hardware_metadata(self):
        """Test creating event with hardware metadata."""
        tag_id = TagIdentifier(uid="abcd1234")
        metadata = {"signal_strength": -45, "read_time_ms": 123}

        event = TagDetectedEvent.create(
            event_id="event-123",
            tag_identifier=tag_id,
            hardware_metadata=metadata
        )

        assert event.hardware_metadata == metadata


class TestTagAssociatedEvent:
    """Test tag associated event."""

    def test_create_association_event(self):
        """Test creating a tag association event."""
        tag_id = TagIdentifier(uid="abcd1234")
        playlist_id = "playlist-456"
        session_id = "session-789"

        event = TagAssociatedEvent.create(
            event_id="event-123",
            tag_identifier=tag_id,
            playlist_id=playlist_id,
            session_id=session_id
        )

        assert event.event_type == "tag_associated"
        assert event.tag_identifier == tag_id
        assert event.playlist_id == playlist_id
        assert event.session_id == session_id
        assert event.previous_playlist_id is None

    def test_create_reassociation_event(self):
        """Test creating a tag re-association event."""
        tag_id = TagIdentifier(uid="abcd1234")
        new_playlist_id = "new-playlist-456"
        old_playlist_id = "old-playlist-789"
        session_id = "session-abc"

        event = TagAssociatedEvent.create(
            event_id="event-123",
            tag_identifier=tag_id,
            playlist_id=new_playlist_id,
            session_id=session_id,
            previous_playlist_id=old_playlist_id
        )

        assert event.playlist_id == new_playlist_id
        assert event.previous_playlist_id == old_playlist_id


class TestTagDissociatedEvent:
    """Test tag dissociated event."""

    def test_create_dissociation_event(self):
        """Test creating a tag dissociation event."""
        tag_id = TagIdentifier(uid="abcd1234")
        playlist_id = "playlist-456"

        event = TagDissociatedEvent.create(
            event_id="event-123",
            tag_identifier=tag_id,
            previous_playlist_id=playlist_id
        )

        assert event.event_type == "tag_dissociated"
        assert event.tag_identifier == tag_id
        assert event.previous_playlist_id == playlist_id
        assert event.reason == "manual_dissociation"

    def test_create_with_custom_reason(self):
        """Test creating dissociation event with custom reason."""
        tag_id = TagIdentifier(uid="abcd1234")
        playlist_id = "playlist-456"
        reason = "playlist_deleted"

        event = TagDissociatedEvent.create(
            event_id="event-123",
            tag_identifier=tag_id,
            previous_playlist_id=playlist_id,
            reason=reason
        )

        assert event.reason == reason


class TestTagRemovedEvent:
    """Test tag removed event."""

    def test_create_basic_removal_event(self):
        """Test creating a basic tag removal event."""
        event = TagRemovedEvent.create(
            event_id="event-123"
        )

        assert event.event_type == "tag_removed"
        assert event.tag_identifier is None
        assert event.detection_duration_seconds is None

    def test_create_with_tag_info(self):
        """Test creating removal event with tag information."""
        tag_id = TagIdentifier(uid="abcd1234")
        duration = 45.7

        event = TagRemovedEvent.create(
            event_id="event-123",
            tag_identifier=tag_id,
            detection_duration_seconds=duration
        )

        assert event.tag_identifier == tag_id
        assert event.detection_duration_seconds == duration


class TestAssociationSessionEvents:
    """Test association session events."""

    def test_session_started_event(self):
        """Test association session started event."""
        session_id = "session-123"
        playlist_id = "playlist-456"
        timeout = 120

        event = AssociationSessionStartedEvent.create(
            event_id="event-123",
            session_id=session_id,
            playlist_id=playlist_id,
            timeout_seconds=timeout
        )

        assert event.event_type == "association_session_started"
        assert event.session_id == session_id
        assert event.playlist_id == playlist_id
        assert event.timeout_seconds == timeout

    def test_session_completed_event(self):
        """Test association session completed event."""
        session_id = "session-123"
        playlist_id = "playlist-456"
        tag_id = TagIdentifier(uid="cafe9abc")
        duration = 12.5

        event = AssociationSessionCompletedEvent.create(
            event_id="event-123",
            session_id=session_id,
            playlist_id=playlist_id,
            tag_identifier=tag_id,
            duration_seconds=duration
        )

        assert event.event_type == "association_session_completed"
        assert event.session_id == session_id
        assert event.playlist_id == playlist_id
        assert event.tag_identifier == tag_id
        assert event.duration_seconds == duration

    def test_session_expired_event(self):
        """Test association session expired event."""
        session_id = "session-123"
        playlist_id = "playlist-456"
        timeout = 60
        tags_detected = 3

        event = AssociationSessionExpiredEvent.create(
            event_id="event-123",
            session_id=session_id,
            playlist_id=playlist_id,
            timeout_seconds=timeout,
            tags_detected_during_session=tags_detected
        )

        assert event.event_type == "association_session_expired"
        assert event.session_id == session_id
        assert event.playlist_id == playlist_id
        assert event.timeout_seconds == timeout
        assert event.tags_detected_during_session == tags_detected