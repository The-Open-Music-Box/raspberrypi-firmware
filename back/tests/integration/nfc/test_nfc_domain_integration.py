# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Integration tests for NFC domain components."""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timezone

from app.src.domain.nfc import (
    NfcTag,
    TagIdentifier,
    NfcAssociationService,
    NfcEventPublisher,
    AssociationSession,
    SessionState,
    NfcRepositoryProtocol,
)
from app.src.domain.nfc.events.nfc_events import (
    TagDetectedEvent,
    TagAssociatedEvent,
    AssociationSessionStartedEvent,
    AssociationSessionCompletedEvent,
)


class MockNfcRepository:
    """Mock NFC repository for testing."""

    def __init__(self):
        """Initialize mock repository."""
        self._tags = {}

    async def save_tag(self, tag: NfcTag) -> None:
        """Save a tag."""
        self._tags[str(tag.identifier)] = tag

    async def find_by_identifier(self, identifier: TagIdentifier) -> NfcTag:
        """Find tag by identifier."""
        return self._tags.get(str(identifier))

    async def find_by_playlist_id(self, playlist_id: str) -> NfcTag:
        """Find tag by playlist ID."""
        for tag in self._tags.values():
            if tag.get_associated_playlist_id() == playlist_id:
                return tag
        return None

    async def delete_tag(self, identifier: TagIdentifier) -> bool:
        """Delete a tag."""
        tag_key = str(identifier)
        if tag_key in self._tags:
            del self._tags[tag_key]
            return True
        return False


class MockPlaylistRepository:
    """Mock playlist repository for testing."""

    def __init__(self):
        """Initialize mock repository."""
        self._playlists = {}

    async def find_by_nfc_tag(self, nfc_tag_id: str):
        """Find playlist by NFC tag ID."""
        # Return playlist if found, None otherwise
        for playlist in self._playlists.values():
            if hasattr(playlist, 'nfc_tag_id') and playlist.nfc_tag_id == nfc_tag_id:
                return playlist
        return None

    async def update_nfc_tag_association(self, playlist_id: str, tag_id: str) -> bool:
        """Update NFC tag association."""
        # Simulate successful update
        return True


class TestNfcDomainIntegration:
    """Test integration between NFC domain components."""

    @pytest.fixture
    def nfc_repository(self):
        """Create mock NFC repository."""
        return MockNfcRepository()

    @pytest.fixture
    def playlist_repository(self):
        """Create mock playlist repository."""
        return MockPlaylistRepository()

    @pytest.fixture
    def event_publisher(self):
        """Create event publisher."""
        return NfcEventPublisher()

    @pytest.fixture
    def association_service(self, nfc_repository, playlist_repository):
        """Create association service."""
        return NfcAssociationService(nfc_repository, playlist_repository)

    @pytest.mark.asyncio
    async def test_complete_association_workflow(
        self, association_service, event_publisher, nfc_repository
    ):
        """Test complete tag association workflow."""
        # Setup event tracking
        events_received = []

        def track_events(event):
            events_received.append(event)

        event_publisher.subscribe("association_session_started", track_events)
        event_publisher.subscribe("tag_detected", track_events)
        event_publisher.subscribe("tag_associated", track_events)
        event_publisher.subscribe("association_session_completed", track_events)

        # Start association session
        playlist_id = "test-playlist-123"
        session = await association_service.start_association_session(playlist_id, 60)

        assert session.playlist_id == playlist_id
        assert session.state == SessionState.LISTENING

        # Publish session started event
        event_publisher.publish_association_session_started(
            session.session_id, playlist_id, 60
        )

        # Simulate tag detection
        tag_id = TagIdentifier(uid="efab5678")

        # Publish tag detected event
        event_publisher.publish_tag_detected(tag_id, detection_count=1)

        # Process tag detection through association service
        result = await association_service.process_tag_detection(tag_id, session.session_id)

        # Verify association result
        assert result["action"] == "association_success"
        assert result["playlist_id"] == playlist_id
        assert result["tag_id"] == str(tag_id)
        assert result["session_id"] == session.session_id

        # Verify tag was saved in repository
        saved_tag = await nfc_repository.find_by_identifier(tag_id)
        assert saved_tag is not None
        assert saved_tag.get_associated_playlist_id() == playlist_id
        assert saved_tag.detection_count == 1

        # Publish association event
        event_publisher.publish_tag_associated(
            tag_id, playlist_id, session.session_id
        )

        # Verify events were published
        assert len(events_received) >= 3

        # Check for session started event
        session_started_events = [e for e in events_received if isinstance(e, AssociationSessionStartedEvent)]
        assert len(session_started_events) == 1
        assert session_started_events[0].session_id == session.session_id

        # Check for tag detected event
        tag_detected_events = [e for e in events_received if isinstance(e, TagDetectedEvent)]
        assert len(tag_detected_events) == 1
        assert tag_detected_events[0].tag_identifier == tag_id

        # Check for tag associated event
        tag_associated_events = [e for e in events_received if isinstance(e, TagAssociatedEvent)]
        assert len(tag_associated_events) == 1
        assert tag_associated_events[0].tag_identifier == tag_id
        assert tag_associated_events[0].playlist_id == playlist_id

    @pytest.mark.asyncio
    async def test_duplicate_association_handling(
        self, association_service, event_publisher, nfc_repository
    ):
        """Test handling of duplicate association attempts."""
        # Create an already associated tag
        tag_id = TagIdentifier(uid="deadbeef")
        existing_tag = NfcTag(identifier=tag_id)
        existing_tag.associate_with_playlist("existing-playlist-123")
        await nfc_repository.save_tag(existing_tag)

        # Start new association session
        new_playlist_id = "new-playlist-456"
        session = await association_service.start_association_session(new_playlist_id, 60)

        # Attempt to associate already associated tag
        result = await association_service.process_tag_detection(tag_id, session.session_id)

        # Verify duplicate association is detected
        assert result["action"] == "duplicate_association"
        assert result["existing_playlist_id"] == "existing-playlist-123"
        assert result["session_state"] == SessionState.DUPLICATE.value

        # Verify tag association didn't change
        saved_tag = await nfc_repository.find_by_identifier(tag_id)
        assert saved_tag.get_associated_playlist_id() == "existing-playlist-123"

    @pytest.mark.asyncio
    async def test_session_timeout_handling(self, association_service, event_publisher):
        """Test session timeout handling."""
        # Start association session with short timeout
        playlist_id = "test-playlist-789"
        timeout_seconds = 1
        session = await association_service.start_association_session(playlist_id, timeout_seconds)

        # Wait for session to expire
        await asyncio.sleep(timeout_seconds + 0.1)

        # Clean up expired sessions
        expired_count = await association_service.cleanup_expired_sessions()

        assert expired_count == 1

        # Verify session is now in timeout state
        retrieved_session = await association_service.get_association_session(session.session_id)
        assert retrieved_session.state == SessionState.TIMEOUT

        # Publish session expired event
        event_publisher.publish_association_session_expired(
            session.session_id, playlist_id, timeout_seconds, 0
        )

        # Verify event was published
        events = event_publisher.get_published_events()
        expired_events = [e for e in events if e.event_type == "association_session_expired"]
        assert len(expired_events) == 1

    @pytest.mark.asyncio
    async def test_tag_dissociation_workflow(
        self, association_service, event_publisher, nfc_repository
    ):
        """Test tag dissociation workflow."""
        # Create and save associated tag
        tag_id = TagIdentifier(uid="cafe1234")
        tag = NfcTag(identifier=tag_id)
        tag.associate_with_playlist("playlist-to-remove")
        await nfc_repository.save_tag(tag)

        # Track dissociation events
        dissociation_events = []

        def track_dissociation(event):
            dissociation_events.append(event)

        event_publisher.subscribe("tag_dissociated", track_dissociation)

        # Dissociate tag
        result = await association_service.dissociate_tag(tag_id)

        assert result is True

        # Verify tag is dissociated
        updated_tag = await nfc_repository.find_by_identifier(tag_id)
        assert updated_tag.get_associated_playlist_id() is None

        # Publish dissociation event
        event_publisher.publish_tag_dissociated(
            tag_id, "playlist-to-remove", "manual_dissociation"
        )

        # Verify event was published
        assert len(dissociation_events) == 1
        assert dissociation_events[0].tag_identifier == tag_id
        assert dissociation_events[0].previous_playlist_id == "playlist-to-remove"

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions(self, association_service):
        """Test handling multiple concurrent association sessions."""
        # Start multiple sessions for different playlists
        playlist1 = "playlist-1"
        playlist2 = "playlist-2"
        playlist3 = "playlist-3"

        session1 = await association_service.start_association_session(playlist1, 60)
        session2 = await association_service.start_association_session(playlist2, 60)
        session3 = await association_service.start_association_session(playlist3, 60)

        # Verify all sessions are active
        active_sessions = association_service.get_active_sessions()
        assert len(active_sessions) == 3

        session_ids = {s.session_id for s in active_sessions}
        assert session1.session_id in session_ids
        assert session2.session_id in session_ids
        assert session3.session_id in session_ids

        # Stop one session
        result = await association_service.stop_association_session(session2.session_id)
        assert result is True

        # Verify session was cancelled (updated behavior)
        updated_session2 = await association_service.get_association_session(session2.session_id)
        assert updated_session2.state == SessionState.CANCELLED

    @pytest.mark.asyncio
    async def test_event_publisher_integration(self, event_publisher):
        """Test event publisher integration with domain workflow."""
        # Track all event types
        all_events = []

        def track_all(event):
            all_events.append(event)

        # Subscribe to multiple event types
        event_types = [
            "tag_detected",
            "tag_associated",
            "tag_dissociated",
            "tag_removed",
            "association_session_started",
            "association_session_completed",
            "association_session_expired",
        ]

        for event_type in event_types:
            event_publisher.subscribe(event_type, track_all)

        # Simulate complete workflow
        tag_id = TagIdentifier(uid="fade5678")
        session_id = "workflow-session"
        playlist_id = "workflow-playlist"

        # Publish sequence of events
        event_publisher.publish_association_session_started(session_id, playlist_id, 60)
        event_publisher.publish_tag_detected(tag_id, 1)
        event_publisher.publish_tag_associated(tag_id, playlist_id, session_id)
        event_publisher.publish_association_session_completed(session_id, playlist_id, tag_id, 15.5)
        event_publisher.publish_tag_removed(tag_id, 120.0)
        event_publisher.publish_tag_dissociated(tag_id, playlist_id, "test_workflow")

        # Verify all events were received
        assert len(all_events) == 6

        # Verify event types
        event_types_received = [event.event_type for event in all_events]
        expected_types = [
            "association_session_started",
            "tag_detected",
            "tag_associated",
            "association_session_completed",
            "tag_removed",
            "tag_dissociated",
        ]
        assert event_types_received == expected_types

        # Verify events contain correct data
        session_started = all_events[0]
        assert session_started.session_id == session_id
        assert session_started.playlist_id == playlist_id

        tag_detected = all_events[1]
        assert tag_detected.tag_identifier == tag_id

        tag_associated = all_events[2]
        assert tag_associated.tag_identifier == tag_id
        assert tag_associated.playlist_id == playlist_id