# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Audio domain events."""

from dataclasses import dataclass
from typing import Optional

from app.src.domain.protocols.event_bus_protocol import AudioEvent
from app.src.domain.protocols.state_manager_protocol import PlaybackState


@dataclass
class TrackStartedEvent(AudioEvent):
    """Event fired when a track starts playing."""

    def __init__(self, source_component: str, file_path: str, duration_ms: Optional[int] = None):
        super().__init__(source_component)
        self.file_path = file_path
        self.duration_ms = duration_ms


@dataclass
class TrackEndedEvent(AudioEvent):
    """Event fired when a track ends."""

    def __init__(
        self,
        source_component: str,
        file_path: str,
        duration_ms: Optional[int] = None,
        position_ms: Optional[int] = None,
        reason: str = "completed",
    ):
        super().__init__(source_component)
        self.file_path = file_path
        self.duration_ms = duration_ms
        self.position_ms = position_ms
        self.reason = reason  # "completed", "stopped", "error", "skipped"


@dataclass
class PlaylistLoadedEvent(AudioEvent):
    """Event fired when a playlist is loaded."""

    def __init__(
        self,
        source_component: str,
        playlist_id: Optional[str] = None,
        playlist_title: Optional[str] = None,
        track_count: int = 0,
        total_duration_ms: Optional[int] = None,
    ):
        super().__init__(source_component)
        self.playlist_id = playlist_id
        self.playlist_title = playlist_title
        self.track_count = track_count
        self.total_duration_ms = total_duration_ms


@dataclass
class PlaylistFinishedEvent(AudioEvent):
    """Event fired when a playlist finishes."""

    def __init__(
        self,
        source_component: str,
        playlist_id: Optional[str] = None,
        playlist_title: Optional[str] = None,
        tracks_played: int = 0,
    ):
        super().__init__(source_component)
        self.playlist_id = playlist_id
        self.playlist_title = playlist_title
        self.tracks_played = tracks_played


@dataclass
class PlaybackStateChangedEvent(AudioEvent):
    """Event fired when playback state changes."""

    def __init__(self, source_component: str, old_state: PlaybackState, new_state: PlaybackState):
        super().__init__(source_component)
        self.old_state = old_state
        self.new_state = new_state


@dataclass
class VolumeChangedEvent(AudioEvent):
    """Event fired when volume changes."""

    def __init__(self, source_component: str, old_volume: int, new_volume: int):
        super().__init__(source_component)
        self.old_volume = old_volume
        self.new_volume = new_volume


@dataclass
class ErrorEvent(AudioEvent):
    """Event fired when an error occurs."""

    def __init__(
        self, source_component: str, error_message: str, error_context: Optional[dict] = None
    ):
        super().__init__(source_component)
        self.error_message = error_message
        self.error_context = error_context or {}


@dataclass
class LogEvent(AudioEvent):
    """Event fired for logging monitoring."""

    def __init__(
        self,
        source_component: str,
        logger_name: str,
        level: str,
        message: str,
        timestamp: float
    ):
        super().__init__(source_component)
        self.logger_name = logger_name
        self.level = level
        self.message = message
        self.timestamp = timestamp
