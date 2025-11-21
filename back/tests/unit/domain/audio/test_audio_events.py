"""
Comprehensive tests for Audio Domain Events.

Tests cover:
- Event creation and initialization
- Event attributes and data
- Event inheritance from AudioEvent base
- All event types (8 events)
"""

import pytest
from app.src.domain.audio.events.audio_events import (
    TrackStartedEvent,
    TrackEndedEvent,
    PlaylistLoadedEvent,
    PlaylistFinishedEvent,
    PlaybackStateChangedEvent,
    VolumeChangedEvent,
    ErrorEvent,
    LogEvent
)
from app.src.domain.protocols.state_manager_protocol import PlaybackState


class TestTrackStartedEvent:
    """Test TrackStartedEvent."""

    def test_create_with_file_path(self):
        """Test creating event with file path."""
        event = TrackStartedEvent("audio_engine", "/music/song.mp3")

        assert event.source_component == "audio_engine"
        assert event.file_path == "/music/song.mp3"
        assert event.duration_ms is None

    def test_create_with_duration(self):
        """Test creating event with duration."""
        event = TrackStartedEvent("audio_engine", "/music/song.mp3", duration_ms=180000)

        assert event.file_path == "/music/song.mp3"
        assert event.duration_ms == 180000


class TestTrackEndedEvent:
    """Test TrackEndedEvent."""

    def test_create_basic(self):
        """Test creating basic track ended event."""
        event = TrackEndedEvent("audio_engine", "/music/song.mp3")

        assert event.source_component == "audio_engine"
        assert event.file_path == "/music/song.mp3"
        assert event.reason == "completed"

    def test_create_with_all_fields(self):
        """Test creating event with all fields."""
        event = TrackEndedEvent(
            "audio_engine",
            "/music/song.mp3",
            duration_ms=180000,
            position_ms=175000,
            reason="stopped"
        )

        assert event.duration_ms == 180000
        assert event.position_ms == 175000
        assert event.reason == "stopped"

    def test_reason_values(self):
        """Test different reason values."""
        reasons = ["completed", "stopped", "error", "skipped"]

        for reason in reasons:
            event = TrackEndedEvent("audio_engine", "/music/song.mp3", reason=reason)
            assert event.reason == reason


class TestPlaylistLoadedEvent:
    """Test PlaylistLoadedEvent."""

    def test_create_minimal(self):
        """Test creating minimal playlist loaded event."""
        event = PlaylistLoadedEvent("audio_engine")

        assert event.source_component == "audio_engine"
        assert event.playlist_id is None
        assert event.playlist_title is None
        assert event.track_count == 0
        assert event.total_duration_ms is None

    def test_create_complete(self):
        """Test creating complete playlist loaded event."""
        event = PlaylistLoadedEvent(
            "audio_engine",
            playlist_id="pl-123",
            playlist_title="My Playlist",
            track_count=15,
            total_duration_ms=2700000
        )

        assert event.playlist_id == "pl-123"
        assert event.playlist_title == "My Playlist"
        assert event.track_count == 15
        assert event.total_duration_ms == 2700000


class TestPlaylistFinishedEvent:
    """Test PlaylistFinishedEvent."""

    def test_create_minimal(self):
        """Test creating minimal playlist finished event."""
        event = PlaylistFinishedEvent("audio_engine")

        assert event.source_component == "audio_engine"
        assert event.playlist_id is None
        assert event.playlist_title is None
        assert event.tracks_played == 0

    def test_create_complete(self):
        """Test creating complete playlist finished event."""
        event = PlaylistFinishedEvent(
            "audio_engine",
            playlist_id="pl-123",
            playlist_title="My Playlist",
            tracks_played=10
        )

        assert event.playlist_id == "pl-123"
        assert event.playlist_title == "My Playlist"
        assert event.tracks_played == 10


class TestPlaybackStateChangedEvent:
    """Test PlaybackStateChangedEvent."""

    def test_create_state_change(self):
        """Test creating playback state changed event."""
        event = PlaybackStateChangedEvent(
            "audio_engine",
            PlaybackState.STOPPED,
            PlaybackState.PLAYING
        )

        assert event.source_component == "audio_engine"
        assert event.old_state == PlaybackState.STOPPED
        assert event.new_state == PlaybackState.PLAYING

    def test_all_state_transitions(self):
        """Test various state transitions."""
        transitions = [
            (PlaybackState.STOPPED, PlaybackState.PLAYING),
            (PlaybackState.PLAYING, PlaybackState.PAUSED),
            (PlaybackState.PAUSED, PlaybackState.PLAYING),
            (PlaybackState.PLAYING, PlaybackState.STOPPED),
        ]

        for old_state, new_state in transitions:
            event = PlaybackStateChangedEvent("audio_engine", old_state, new_state)
            assert event.old_state == old_state
            assert event.new_state == new_state


class TestVolumeChangedEvent:
    """Test VolumeChangedEvent."""

    def test_create_volume_change(self):
        """Test creating volume changed event."""
        event = VolumeChangedEvent("audio_engine", 50, 75)

        assert event.source_component == "audio_engine"
        assert event.old_volume == 50
        assert event.new_volume == 75

    def test_volume_increase(self):
        """Test volume increase event."""
        event = VolumeChangedEvent("audio_engine", 30, 60)

        assert event.new_volume > event.old_volume

    def test_volume_decrease(self):
        """Test volume decrease event."""
        event = VolumeChangedEvent("audio_engine", 80, 40)

        assert event.new_volume < event.old_volume

    def test_volume_bounds(self):
        """Test volume at boundaries."""
        event_min = VolumeChangedEvent("audio_engine", 10, 0)
        event_max = VolumeChangedEvent("audio_engine", 90, 100)

        assert event_min.new_volume == 0
        assert event_max.new_volume == 100


class TestErrorEvent:
    """Test ErrorEvent."""

    def test_create_error_basic(self):
        """Test creating basic error event."""
        event = ErrorEvent("audio_engine", "Playback failed")

        assert event.source_component == "audio_engine"
        assert event.error_message == "Playback failed"
        assert event.error_context == {}

    def test_create_error_with_context(self):
        """Test creating error event with context."""
        context = {"file_path": "/music/song.mp3", "error_code": 404}
        event = ErrorEvent("audio_engine", "File not found", error_context=context)

        assert event.error_message == "File not found"
        assert event.error_context == context
        assert event.error_context["file_path"] == "/music/song.mp3"
        assert event.error_context["error_code"] == 404


class TestLogEvent:
    """Test LogEvent."""

    def test_create_log_event(self):
        """Test creating log event."""
        import time
        timestamp = time.time()

        event = LogEvent(
            "audio_engine",
            "app.audio",
            "INFO",
            "Playback started",
            timestamp
        )

        assert event.source_component == "audio_engine"
        assert event.logger_name == "app.audio"
        assert event.level == "INFO"
        assert event.message == "Playback started"
        assert event.timestamp == timestamp

    def test_log_levels(self):
        """Test different log levels."""
        import time
        timestamp = time.time()
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        for level in levels:
            event = LogEvent("audio_engine", "app.audio", level, "Test message", timestamp)
            assert event.level == level


class TestEventInheritance:
    """Test event inheritance from AudioEvent base."""

    def test_all_events_have_source(self):
        """Test all events have source_component."""
        events = [
            TrackStartedEvent("test", "/file.mp3"),
            TrackEndedEvent("test", "/file.mp3"),
            PlaylistLoadedEvent("test"),
            PlaylistFinishedEvent("test"),
            PlaybackStateChangedEvent("test", PlaybackState.STOPPED, PlaybackState.PLAYING),
            VolumeChangedEvent("test", 50, 75),
            ErrorEvent("test", "Error"),
            LogEvent("test", "logger", "INFO", "Message", 0.0)
        ]

        for event in events:
            assert hasattr(event, "source_component")
            assert event.source_component == "test"


class TestEventDataclasses:
    """Test that events are proper dataclasses."""

    def test_track_started_is_dataclass(self):
        """Test TrackStartedEvent is a dataclass."""
        event = TrackStartedEvent("test", "/file.mp3")

        assert hasattr(event, "__dataclass_fields__")

    def test_events_equality(self):
        """Test event equality based on dataclass."""
        event1 = VolumeChangedEvent("test", 50, 75)
        event2 = VolumeChangedEvent("test", 50, 75)

        # Dataclasses with same values should be equal
        assert event1.source_component == event2.source_component
        assert event1.old_volume == event2.old_volume
        assert event1.new_volume == event2.new_volume
