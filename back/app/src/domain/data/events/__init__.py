# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain events."""

from .playlist_events import (
    PlaylistCreatedEvent,
    PlaylistDeletedEvent,
    PlaylistUpdatedEvent,
    TrackAddedEvent,
    TrackDeletedEvent,
    TracksReorderedEvent,
    TrackUpdatedEvent,
)

__all__ = [
    'PlaylistCreatedEvent',
    'PlaylistDeletedEvent',
    'PlaylistUpdatedEvent',
    'TrackAddedEvent',
    'TrackDeletedEvent',
    'TrackUpdatedEvent',
    'TracksReorderedEvent'
]
