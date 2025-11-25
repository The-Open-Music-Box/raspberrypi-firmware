"""Audio domain events."""

from .audio_events import (
    AudioEvent,
    TrackStartedEvent,
    TrackEndedEvent,
    PlaylistLoadedEvent,
    PlaylistFinishedEvent,
    PlaybackStateChangedEvent,
    VolumeChangedEvent,
    ErrorEvent,
)

__all__ = [
    "AudioEvent",
    "TrackStartedEvent",
    "TrackEndedEvent",
    "PlaylistLoadedEvent",
    "PlaylistFinishedEvent",
    "PlaybackStateChangedEvent",
    "VolumeChangedEvent",
    "ErrorEvent",
]
