# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Socket.IO Room Constants

Centralized constants for Socket.IO room names to eliminate magic strings
and ensure consistency across the codebase.

This follows DRY principles and makes room name changes easier to manage.
"""

from typing import Optional


class SocketRooms:
    """
    Centralized Socket.IO room name constants and utilities.

    This class provides:
    - Constant room names for global subscriptions
    - Factory methods for dynamic room names (playlist-specific, NFC-specific)
    - Type-safe room name generation

    Usage:
        # Global rooms
        room = SocketRooms.PLAYLISTS

        # Dynamic rooms
        playlist_room = SocketRooms.playlist("abc123")
        nfc_room = SocketRooms.nfc("assoc_456")
    """

    # Global room names
    PLAYLISTS = "playlists"

    @staticmethod
    def playlist(playlist_id: str) -> str:
        """
        Generate a playlist-specific room name.

        Args:
            playlist_id: The unique identifier of the playlist

        Returns:
            Room name in format "playlist:{playlist_id}"

        Example:
            >>> SocketRooms.playlist("abc123")
            "playlist:abc123"
        """
        return f"playlist:{playlist_id}"

    @staticmethod
    def nfc(assoc_id: str) -> str:
        """
        Generate an NFC association-specific room name.

        Args:
            assoc_id: The unique identifier of the NFC association

        Returns:
            Room name in format "nfc:{assoc_id}"

        Example:
            >>> SocketRooms.nfc("assoc_456")
            "nfc:assoc_456"
        """
        return f"nfc:{assoc_id}"

    @staticmethod
    def validate_room_name(room_name: str) -> bool:
        """
        Validate that a room name follows expected patterns.

        Args:
            room_name: The room name to validate

        Returns:
            True if valid, False otherwise

        Valid patterns:
            - "playlists"
            - "playlist:{id}"
            - "nfc:{id}"
        """
        if room_name == SocketRooms.PLAYLISTS:
            return True
        if room_name.startswith("playlist:") and len(room_name) > len("playlist:"):
            return True
        if room_name.startswith("nfc:") and len(room_name) > len("nfc:"):
            return True
        return False

    @staticmethod
    def extract_playlist_id(room_name: str) -> Optional[str]:
        """
        Extract playlist ID from a playlist room name.

        Args:
            room_name: Room name in format "playlist:{id}"

        Returns:
            The playlist ID if valid format, None otherwise

        Example:
            >>> SocketRooms.extract_playlist_id("playlist:abc123")
            "abc123"
            >>> SocketRooms.extract_playlist_id("playlists")
            None
        """
        if room_name.startswith("playlist:"):
            return room_name[len("playlist:"):]
        return None

    @staticmethod
    def extract_nfc_id(room_name: str) -> Optional[str]:
        """
        Extract NFC association ID from an NFC room name.

        Args:
            room_name: Room name in format "nfc:{id}"

        Returns:
            The NFC association ID if valid format, None otherwise

        Example:
            >>> SocketRooms.extract_nfc_id("nfc:assoc_456")
            "assoc_456"
        """
        if room_name.startswith("nfc:"):
            return room_name[len("nfc:"):]
        return None
