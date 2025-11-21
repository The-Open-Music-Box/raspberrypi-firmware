# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain events for playlists and tracks."""

from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime


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
    updates: Dict[str, Any]
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
    track_number: int
    added_at: datetime


@dataclass
class TrackUpdatedEvent:
    """Event raised when a track is updated."""
    track_id: str
    playlist_id: str
    updates: Dict[str, Any]
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
    track_ids: List[str]
    reordered_at: datetime