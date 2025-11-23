"""Audio domain events."""

from .audio_events import (
    AudioEvent,
    ErrorEvent,
    PlaybackStateChangedEvent,
    PlaylistFinishedEvent,
    PlaylistLoadedEvent,
    TrackEndedEvent,
    TrackStartedEvent,
    VolumeChangedEvent,
)

__all__ = [
    "AudioEvent",
    "ErrorEvent",
    "PlaybackStateChangedEvent",
    "PlaylistFinishedEvent",
    "PlaylistLoadedEvent",
    "TrackEndedEvent",
    "TrackStartedEvent",
    "VolumeChangedEvent",
]
