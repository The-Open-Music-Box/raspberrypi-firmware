# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unit tests for NFC event publisher."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from app.src.domain.nfc.services.nfc_event_publisher import NfcEventPublisher
from app.src.domain.nfc.events.nfc_events import (
    TagDetectedEvent,
    TagAssociatedEvent,
    TagDissociatedEvent,
    TagRemovedEvent,
    AssociationSessionStartedEvent,
    AssociationSessionCompletedEvent,
    AssociationSessionExpiredEvent,
)
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier


class TestNfcEventPublisher:
    """Test NFC event publisher functionality."""

    def test_publisher_initialization(self):
        """Test publisher initializes correctly."""
        publisher = NfcEventPublisher()

        assert len(publisher._event_handlers) == 0
        assert len(publisher._published_events) == 0

    def test_subscribe_to_event_type(self):
        """Test subscribing to an event type."""
        publisher = NfcEventPublisher()
        handler = Mock()

        publisher.subscribe("tag_detected", handler)

        assert "tag_detected" in publisher._event_handlers
        assert handler in publisher._event_handlers["tag_detected"]
        assert publisher.get_subscriber_count("tag_detected") == 1

    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers to same event type."""
        publisher = NfcEventPublisher()
        handler1 = Mock()
        handler2 = Mock()

        publisher.subscribe("tag_detected", handler1)
        publisher.subscribe("tag_detected", handler2)

        assert len(publisher._event_handlers["tag_detected"]) == 2
        assert publisher.get_subscriber_count("tag_detected") == 2

    def test_unsubscribe_existing_handler(self):
        """Test unsubscribing an existing handler."""
        publisher = NfcEventPublisher()
        handler = Mock()

        publisher.subscribe("tag_detected", handler)
        result = publisher.unsubscribe("tag_detected", handler)

        assert result is True
        assert publisher.get_subscriber_count("tag_detected") == 0

    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing a non-existent handler."""
        publisher = NfcEventPublisher()
        handler = Mock()

        result = publisher.unsubscribe("tag_detected", handler)

        assert result is False

    def test_unsubscribe_nonexistent_event_type(self):
        """Test unsubscribing from non-existent event type."""
        publisher = NfcEventPublisher()
        handler = Mock()

        result = publisher.unsubscribe("nonexistent_event", handler)

        assert result is False

    def test_publish_event_to_subscribers(self):
        """Test publishing event calls all subscribers."""
        publisher = NfcEventPublisher()
        handler1 = Mock()
        handler2 = Mock()

        publisher.subscribe("tag_detected", handler1)
        publisher.subscribe("tag_detected", handler2)

        tag_id = TagIdentifier(uid="abcd1234")
        event = TagDetectedEvent.create("event-123", tag_id)

        publisher.publish(event)

        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)
        assert len(publisher.get_published_events()) == 1

    def test_publish_event_no_subscribers(self):
        """Test publishing event with no subscribers."""
        publisher = NfcEventPublisher()

        tag_id = TagIdentifier(uid="abcd1234")
        event = TagDetectedEvent.create("event-123", tag_id)

        publisher.publish(event)

        assert len(publisher.get_published_events()) == 1

    def test_publish_event_handler_error(self):
        """Test publishing event when handler raises error."""
        publisher = NfcEventPublisher()
        error_handler = Mock(side_effect=Exception("Handler error"))
        good_handler = Mock()

        publisher.subscribe("tag_detected", error_handler)
        publisher.subscribe("tag_detected", good_handler)

        tag_id = TagIdentifier(uid="abcd1234")
        event = TagDetectedEvent.create("event-123", tag_id)

        # Should not raise exception
        publisher.publish(event)

        error_handler.assert_called_once_with(event)
        good_handler.assert_called_once_with(event)

    @patch('uuid.uuid4')
    def test_publish_tag_detected(self, mock_uuid):
        """Test publishing tag detected event."""
        mock_uuid.return_value.return_value = "mock-uuid-123"

        publisher = NfcEventPublisher()
        handler = Mock()
        publisher.subscribe("tag_detected", handler)

        tag_id = TagIdentifier(uid="abcd1234")
        metadata = {"signal": -45}

        event = publisher.publish_tag_detected(
            tag_identifier=tag_id,
            detection_count=3,
            previously_associated_playlist_id="playlist-123",
            hardware_metadata=metadata
        )

        assert isinstance(event, TagDetectedEvent)
        assert event.tag_identifier == tag_id
        assert event.detection_count == 3
        assert event.previously_associated_playlist_id == "playlist-123"
        assert event.hardware_metadata == metadata
        handler.assert_called_once_with(event)

    @patch('uuid.uuid4')
    def test_publish_tag_associated(self, mock_uuid):
        """Test publishing tag associated event."""
        mock_uuid.return_value.return_value = "mock-uuid-123"

        publisher = NfcEventPublisher()
        handler = Mock()
        publisher.subscribe("tag_associated", handler)

        tag_id = TagIdentifier(uid="abcd1234")

        event = publisher.publish_tag_associated(
            tag_identifier=tag_id,
            playlist_id="playlist-456",
            session_id="session-789",
            previous_playlist_id="old-playlist-123"
        )

        assert isinstance(event, TagAssociatedEvent)
        assert event.tag_identifier == tag_id
        assert event.playlist_id == "playlist-456"
        assert event.session_id == "session-789"
        assert event.previous_playlist_id == "old-playlist-123"
        handler.assert_called_once_with(event)

    @patch('uuid.uuid4')
    def test_publish_tag_dissociated(self, mock_uuid):
        """Test publishing tag dissociated event."""
        mock_uuid.return_value.return_value = "mock-uuid-123"

        publisher = NfcEventPublisher()
        handler = Mock()
        publisher.subscribe("tag_dissociated", handler)

        tag_id = TagIdentifier(uid="abcd1234")

        event = publisher.publish_tag_dissociated(
            tag_identifier=tag_id,
            previous_playlist_id="playlist-123",
            reason="playlist_deleted"
        )

        assert isinstance(event, TagDissociatedEvent)
        assert event.tag_identifier == tag_id
        assert event.previous_playlist_id == "playlist-123"
        assert event.reason == "playlist_deleted"
        handler.assert_called_once_with(event)

    @patch('uuid.uuid4')
    def test_publish_tag_removed(self, mock_uuid):
        """Test publishing tag removed event."""
        mock_uuid.return_value.return_value = "mock-uuid-123"

        publisher = NfcEventPublisher()
        handler = Mock()
        publisher.subscribe("tag_removed", handler)

        tag_id = TagIdentifier(uid="abcd1234")

        event = publisher.publish_tag_removed(
            tag_identifier=tag_id,
            detection_duration_seconds=45.7
        )

        assert isinstance(event, TagRemovedEvent)
        assert event.tag_identifier == tag_id
        assert event.detection_duration_seconds == 45.7
        handler.assert_called_once_with(event)

    @patch('uuid.uuid4')
    def test_publish_association_session_started(self, mock_uuid):
        """Test publishing association session started event."""
        mock_uuid.return_value.return_value = "mock-uuid-123"

        publisher = NfcEventPublisher()
        handler = Mock()
        publisher.subscribe("association_session_started", handler)

        event = publisher.publish_association_session_started(
            session_id="session-123",
            playlist_id="playlist-456",
            timeout_seconds=120
        )

        assert isinstance(event, AssociationSessionStartedEvent)
        assert event.session_id == "session-123"
        assert event.playlist_id == "playlist-456"
        assert event.timeout_seconds == 120
        handler.assert_called_once_with(event)

    @patch('uuid.uuid4')
    def test_publish_association_session_completed(self, mock_uuid):
        """Test publishing association session completed event."""
        mock_uuid.return_value.return_value = "mock-uuid-123"

        publisher = NfcEventPublisher()
        handler = Mock()
        publisher.subscribe("association_session_completed", handler)

        tag_id = TagIdentifier(uid="abcd1234")

        event = publisher.publish_association_session_completed(
            session_id="session-123",
            playlist_id="playlist-456",
            tag_identifier=tag_id,
            duration_seconds=25.3
        )

        assert isinstance(event, AssociationSessionCompletedEvent)
        assert event.session_id == "session-123"
        assert event.playlist_id == "playlist-456"
        assert event.tag_identifier == tag_id
        assert event.duration_seconds == 25.3
        handler.assert_called_once_with(event)

    @patch('uuid.uuid4')
    def test_publish_association_session_expired(self, mock_uuid):
        """Test publishing association session expired event."""
        mock_uuid.return_value.return_value = "mock-uuid-123"

        publisher = NfcEventPublisher()
        handler = Mock()
        publisher.subscribe("association_session_expired", handler)

        event = publisher.publish_association_session_expired(
            session_id="session-123",
            playlist_id="playlist-456",
            timeout_seconds=60,
            tags_detected_during_session=2
        )

        assert isinstance(event, AssociationSessionExpiredEvent)
        assert event.session_id == "session-123"
        assert event.playlist_id == "playlist-456"
        assert event.timeout_seconds == 60
        assert event.tags_detected_during_session == 2
        handler.assert_called_once_with(event)

    def test_get_published_events(self):
        """Test getting published events."""
        publisher = NfcEventPublisher()

        tag_id = TagIdentifier(uid="abcd1234")
        event1 = TagDetectedEvent.create("event-1", tag_id)
        event2 = TagDetectedEvent.create("event-2", tag_id)

        publisher.publish(event1)
        publisher.publish(event2)

        events = publisher.get_published_events()

        assert len(events) == 2
        assert event1 in events
        assert event2 in events

    def test_clear_published_events(self):
        """Test clearing published events."""
        publisher = NfcEventPublisher()

        tag_id = TagIdentifier(uid="abcd1234")
        event = TagDetectedEvent.create("event-1", tag_id)

        publisher.publish(event)
        assert len(publisher.get_published_events()) == 1

        publisher.clear_published_events()
        assert len(publisher.get_published_events()) == 0

    def test_get_subscriber_count(self):
        """Test getting subscriber count for event types."""
        publisher = NfcEventPublisher()

        assert publisher.get_subscriber_count("tag_detected") == 0
        assert publisher.get_subscriber_count("nonexistent_event") == 0

        handler1 = Mock()
        handler2 = Mock()

        publisher.subscribe("tag_detected", handler1)
        publisher.subscribe("tag_detected", handler2)
        publisher.subscribe("tag_associated", handler1)

        assert publisher.get_subscriber_count("tag_detected") == 2
        assert publisher.get_subscriber_count("tag_associated") == 1
        assert publisher.get_subscriber_count("nonexistent_event") == 0