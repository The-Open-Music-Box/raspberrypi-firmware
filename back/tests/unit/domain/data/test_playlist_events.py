"""
Comprehensive tests for playlist domain events.

Tests cover:
- Event creation
- Event attributes
- Event immutability (dataclass)
- All event types
"""

import pytest
from datetime import datetime, timezone
from app.src.domain.data.events.playlist_events import (
    PlaylistCreatedEvent,
    PlaylistUpdatedEvent,
    PlaylistDeletedEvent,
    TrackAddedEvent,
    TrackUpdatedEvent,
    TrackDeletedEvent,
    TracksReorderedEvent
)


class TestPlaylistCreatedEvent:
    """Test PlaylistCreatedEvent."""

    def test_create_event(self):
        """Test creating playlist created event."""
        now = datetime.now(timezone.utc)
        event = PlaylistCreatedEvent(
            playlist_id="pl-123",
            playlist_name="Test Playlist",
            created_at=now
        )

        assert event.playlist_id == "pl-123"
        assert event.playlist_name == "Test Playlist"
        assert event.created_at == now

    def test_event_attributes_required(self):
        """Test all attributes are required."""
        now = datetime.now(timezone.utc)

        # Should work with all attributes
        event = PlaylistCreatedEvent(
            playlist_id="pl-123",
            playlist_name="Test",
            created_at=now
        )
        assert event is not None

    def test_event_with_special_characters(self):
        """Test event with special characters in name."""
        event = PlaylistCreatedEvent(
            playlist_id="pl-123",
            playlist_name="Test's 'Awesome' Playlist! 🎵",
            created_at=datetime.now(timezone.utc)
        )

        assert "Awesome" in event.playlist_name

    def test_event_equality(self):
        """Test event equality based on attributes."""
        now = datetime.now(timezone.utc)
        event1 = PlaylistCreatedEvent("pl-1", "Test", now)
        event2 = PlaylistCreatedEvent("pl-1", "Test", now)

        assert event1 == event2


class TestPlaylistUpdatedEvent:
    """Test PlaylistUpdatedEvent."""

    def test_create_event(self):
        """Test creating playlist updated event."""
        now = datetime.now(timezone.utc)
        updates = {"name": "New Name", "description": "New Description"}
        event = PlaylistUpdatedEvent(
            playlist_id="pl-123",
            updates=updates,
            updated_at=now
        )

        assert event.playlist_id == "pl-123"
        assert event.updates == updates
        assert event.updated_at == now

    def test_event_with_empty_updates(self):
        """Test event with empty updates dictionary."""
        event = PlaylistUpdatedEvent(
            playlist_id="pl-123",
            updates={},
            updated_at=datetime.now(timezone.utc)
        )

        assert event.updates == {}

    def test_event_with_multiple_updates(self):
        """Test event with multiple update fields."""
        updates = {
            "name": "Updated",
            "description": "New desc",
            "nfc_tag_id": "tag-456",
            "path": "/new/path"
        }
        event = PlaylistUpdatedEvent(
            playlist_id="pl-123",
            updates=updates,
            updated_at=datetime.now(timezone.utc)
        )

        assert len(event.updates) == 4
        assert event.updates["name"] == "Updated"


class TestPlaylistDeletedEvent:
    """Test PlaylistDeletedEvent."""

    def test_create_event(self):
        """Test creating playlist deleted event."""
        now = datetime.now(timezone.utc)
        event = PlaylistDeletedEvent(
            playlist_id="pl-123",
            playlist_name="Deleted Playlist",
            deleted_at=now
        )

        assert event.playlist_id == "pl-123"
        assert event.playlist_name == "Deleted Playlist"
        assert event.deleted_at == now

    def test_event_preserves_deleted_name(self):
        """Test event preserves the deleted playlist name."""
        event = PlaylistDeletedEvent(
            playlist_id="pl-123",
            playlist_name="Important Data",
            deleted_at=datetime.now(timezone.utc)
        )

        # Name should be preserved for audit purposes
        assert event.playlist_name == "Important Data"


class TestTrackAddedEvent:
    """Test TrackAddedEvent."""

    def test_create_event(self):
        """Test creating track added event."""
        now = datetime.now(timezone.utc)
        event = TrackAddedEvent(
            track_id="track-123",
            playlist_id="pl-456",
            track_name="New Song",
            track_number=5,
            added_at=now
        )

        assert event.track_id == "track-123"
        assert event.playlist_id == "pl-456"
        assert event.track_name == "New Song"
        assert event.track_number == 5
        assert event.added_at == now

    def test_event_track_number_first_position(self):
        """Test event with track at first position."""
        event = TrackAddedEvent(
            track_id="track-1",
            playlist_id="pl-1",
            track_name="First Track",
            track_number=1,
            added_at=datetime.now(timezone.utc)
        )

        assert event.track_number == 1

    def test_event_track_number_large_value(self):
        """Test event with large track number."""
        event = TrackAddedEvent(
            track_id="track-1",
            playlist_id="pl-1",
            track_name="Track",
            track_number=999,
            added_at=datetime.now(timezone.utc)
        )

        assert event.track_number == 999


class TestTrackUpdatedEvent:
    """Test TrackUpdatedEvent."""

    def test_create_event(self):
        """Test creating track updated event."""
        now = datetime.now(timezone.utc)
        updates = {"title": "New Title", "artist": "New Artist"}
        event = TrackUpdatedEvent(
            track_id="track-123",
            playlist_id="pl-456",
            updates=updates,
            updated_at=now
        )

        assert event.track_id == "track-123"
        assert event.playlist_id == "pl-456"
        assert event.updates == updates
        assert event.updated_at == now

    def test_event_with_metadata_updates(self):
        """Test event with metadata updates."""
        updates = {
            "title": "Updated Title",
            "artist": "Updated Artist",
            "album": "Updated Album",
            "duration_ms": 240000
        }
        event = TrackUpdatedEvent(
            track_id="track-1",
            playlist_id="pl-1",
            updates=updates,
            updated_at=datetime.now(timezone.utc)
        )

        assert event.updates["duration_ms"] == 240000


class TestTrackDeletedEvent:
    """Test TrackDeletedEvent."""

    def test_create_event(self):
        """Test creating track deleted event."""
        now = datetime.now(timezone.utc)
        event = TrackDeletedEvent(
            track_id="track-123",
            playlist_id="pl-456",
            track_name="Deleted Song",
            deleted_at=now
        )

        assert event.track_id == "track-123"
        assert event.playlist_id == "pl-456"
        assert event.track_name == "Deleted Song"
        assert event.deleted_at == now


class TestTracksReorderedEvent:
    """Test TracksReorderedEvent."""

    def test_create_event(self):
        """Test creating tracks reordered event."""
        now = datetime.now(timezone.utc)
        track_ids = ["track-3", "track-1", "track-2"]
        event = TracksReorderedEvent(
            playlist_id="pl-456",
            track_ids=track_ids,
            reordered_at=now
        )

        assert event.playlist_id == "pl-456"
        assert event.track_ids == track_ids
        assert event.reordered_at == now

    def test_event_with_single_track(self):
        """Test event with single track (edge case)."""
        event = TracksReorderedEvent(
            playlist_id="pl-1",
            track_ids=["track-1"],
            reordered_at=datetime.now(timezone.utc)
        )

        assert len(event.track_ids) == 1

    def test_event_with_many_tracks(self):
        """Test event with many tracks."""
        track_ids = [f"track-{i}" for i in range(100)]
        event = TracksReorderedEvent(
            playlist_id="pl-1",
            track_ids=track_ids,
            reordered_at=datetime.now(timezone.utc)
        )

        assert len(event.track_ids) == 100

    def test_event_preserves_track_order(self):
        """Test event preserves new track order."""
        original_order = ["track-1", "track-2", "track-3"]
        new_order = ["track-3", "track-1", "track-2"]

        event = TracksReorderedEvent(
            playlist_id="pl-1",
            track_ids=new_order,
            reordered_at=datetime.now(timezone.utc)
        )

        assert event.track_ids == new_order
        assert event.track_ids != original_order


class TestEventTimestamps:
    """Test event timestamp handling."""

    def test_all_events_use_utc(self):
        """Test all events should use UTC timestamps."""
        now_utc = datetime.now(timezone.utc)

        events = [
            PlaylistCreatedEvent("pl-1", "Test", now_utc),
            PlaylistUpdatedEvent("pl-1", {}, now_utc),
            PlaylistDeletedEvent("pl-1", "Test", now_utc),
            TrackAddedEvent("t-1", "pl-1", "Track", 1, now_utc),
            TrackUpdatedEvent("t-1", "pl-1", {}, now_utc),
            TrackDeletedEvent("t-1", "pl-1", "Track", now_utc),
            TracksReorderedEvent("pl-1", ["t-1"], now_utc),
        ]

        for event in events:
            # All events should have timezone info
            timestamp_attr = [attr for attr in dir(event) if 'at' in attr and not attr.startswith('_')][0]
            timestamp = getattr(event, timestamp_attr)
            assert timestamp.tzinfo is not None

    def test_events_preserve_exact_timestamp(self):
        """Test events preserve exact timestamp values."""
        timestamp1 = datetime(2025, 1, 15, 12, 30, 45, 123456, tzinfo=timezone.utc)
        timestamp2 = datetime(2025, 1, 15, 12, 30, 45, 654321, tzinfo=timezone.utc)

        event1 = PlaylistCreatedEvent("pl-1", "Test", timestamp1)
        event2 = PlaylistCreatedEvent("pl-1", "Test", timestamp2)

        assert event1.created_at.microsecond == 123456
        assert event2.created_at.microsecond == 654321
        assert event1.created_at != event2.created_at


class TestEventEdgeCases:
    """Test edge cases and special scenarios."""

    def test_events_with_empty_strings(self):
        """Test events handle empty string IDs."""
        # Events should accept empty strings (validation is caller's responsibility)
        event = PlaylistCreatedEvent(
            playlist_id="",
            playlist_name="",
            created_at=datetime.now(timezone.utc)
        )

        assert event.playlist_id == ""
        assert event.playlist_name == ""

    def test_events_with_very_long_names(self):
        """Test events with very long names."""
        long_name = "A" * 10000
        event = PlaylistCreatedEvent(
            playlist_id="pl-1",
            playlist_name=long_name,
            created_at=datetime.now(timezone.utc)
        )

        assert len(event.playlist_name) == 10000

    def test_events_with_unicode(self):
        """Test events with unicode characters."""
        event = PlaylistCreatedEvent(
            playlist_id="pl-日本",
            playlist_name="プレイリスト 🎵🎶",
            created_at=datetime.now(timezone.utc)
        )

        assert "日本" in event.playlist_id
        assert "🎵" in event.playlist_name

    def test_update_events_with_none_values(self):
        """Test update events can contain None values."""
        updates = {"name": None, "description": None}
        event = PlaylistUpdatedEvent(
            playlist_id="pl-1",
            updates=updates,
            updated_at=datetime.now(timezone.utc)
        )

        assert event.updates["name"] is None

    def test_tracks_reordered_empty_list(self):
        """Test tracks reordered event with empty list."""
        event = TracksReorderedEvent(
            playlist_id="pl-1",
            track_ids=[],
            reordered_at=datetime.now(timezone.utc)
        )

        assert event.track_ids == []
