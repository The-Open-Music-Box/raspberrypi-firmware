# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Custom exception hierarchy for track management operations.

This module defines specific exceptions for track management operations,
providing better error handling and debugging capabilities.
"""


class TrackManagementError(Exception):
    """Base exception for track management operations."""

    def __init__(self, message: str, playlist_id: str = None, track_numbers: list = None):
        super().__init__(message)
        self.playlist_id = playlist_id
        self.track_numbers = track_numbers
        self.message = message


class PlaylistNotFoundError(TrackManagementError):
    """Raised when a playlist is not found."""

    def __init__(self, playlist_id: str):
        message = f"Playlist '{playlist_id}' not found"
        super().__init__(message, playlist_id=playlist_id)


class TrackNotFoundError(TrackManagementError):
    """Raised when specified track numbers are not found in playlist."""

    def __init__(self, playlist_id: str, track_numbers: list):
        message = f"Track numbers {track_numbers} not found in playlist '{playlist_id}'"
        super().__init__(message, playlist_id=playlist_id, track_numbers=track_numbers)


class FileOperationError(TrackManagementError):
    """Raised when file system operations fail."""

    def __init__(self, message: str, file_path: str = None, playlist_id: str = None):
        super().__init__(message, playlist_id=playlist_id)
        self.file_path = file_path


class DatabaseOperationError(TrackManagementError):
    """Raised when database operations fail."""

    def __init__(self, message: str, playlist_id: str = None, operation: str = None):
        super().__init__(message, playlist_id=playlist_id)
        self.operation = operation


class InvalidTrackOrderError(TrackManagementError):
    """Raised when track order is invalid."""

    def __init__(self, playlist_id: str, provided_order: list, expected_order: list):
        message = f"Invalid track order for playlist '{playlist_id}': provided {provided_order}, expected {expected_order}"
        super().__init__(message, playlist_id=playlist_id)
        self.provided_order = provided_order
        self.expected_order = expected_order


class TrackValidationError(TrackManagementError):
    """Raised when track validation fails."""

    def __init__(self, message: str, playlist_id: str = None, track_number: int = None):
        super().__init__(message, playlist_id=playlist_id)
        self.track_number = track_number
