# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain events for playlists and tracks."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class PlaylistCreatedEvent:
    """Event raised when a playlist is created."""
    playlist_id: str
    playlist_name: str
    created_at: datetime


@dataclass
class PlaylistUpdatedEvent:
    """Event raised when a playlist is updated."""
    playlist_id: str
    updates: dict[str, Any]
    updated_at: datetime


@dataclass
class PlaylistDeletedEvent:
    """Event raised when a playlist is deleted."""
    playlist_id: str
    playlist_name: str
    deleted_at: datetime


@dataclass
class TrackAddedEvent:
    """Event raised when a track is added to a playlist."""
    track_id: str
    playlist_id: str
    track_name: str
    number: int  # Position in playlist - per OpenAPI contract v3.3.2
    added_at: datetime


@dataclass
class TrackUpdatedEvent:
    """Event raised when a track is updated."""
    track_id: str
    playlist_id: str
    updates: dict[str, Any]
    updated_at: datetime


@dataclass
class TrackDeletedEvent:
    """Event raised when a track is deleted."""
    track_id: str
    playlist_id: str
    track_name: str
    deleted_at: datetime


@dataclass
class TracksReorderedEvent:
    """Event raised when tracks are reordered in a playlist."""
    playlist_id: str
    track_ids: list[str]
    reordered_at: datetime
