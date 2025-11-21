# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain specific exceptions."""


class DataDomainError(Exception):
    """Base exception for data domain errors."""
    pass


class PlaylistNotFoundError(DataDomainError):
    """Raised when a playlist is not found."""

    def __init__(self, playlist_id: str):
        self.playlist_id = playlist_id
        super().__init__(f"Playlist not found: {playlist_id}")


class TrackNotFoundError(DataDomainError):
    """Raised when a track is not found."""

    def __init__(self, track_id: str):
        self.track_id = track_id
        super().__init__(f"Track not found: {track_id}")


class PlaylistValidationError(DataDomainError):
    """Raised when playlist validation fails."""

    def __init__(self, message: str):
        super().__init__(f"Playlist validation error: {message}")


class TrackValidationError(DataDomainError):
    """Raised when track validation fails."""

    def __init__(self, message: str):
        super().__init__(f"Track validation error: {message}")