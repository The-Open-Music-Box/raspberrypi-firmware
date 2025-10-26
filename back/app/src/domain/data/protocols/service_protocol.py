# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Service protocols for the data domain."""

from typing import Protocol, List, Optional, Dict, Any
from abc import abstractmethod


class PlaylistServiceProtocol(Protocol):
    """Protocol for playlist service operations."""

    @abstractmethod
    async def get_playlists(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Get paginated playlists."""
        ...

    @abstractmethod
    async def get_playlist(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get a single playlist with its tracks."""
        ...

    @abstractmethod
    async def create_playlist(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new playlist."""
        ...

    @abstractmethod
    async def update_playlist(self, playlist_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update playlist metadata."""
        ...

    @abstractmethod
    async def delete_playlist(self, playlist_id: str) -> bool:
        """Delete a playlist and all its tracks."""
        ...

    @abstractmethod
    async def associate_nfc_tag(self, playlist_id: str, nfc_tag_id: str) -> bool:
        """Associate an NFC tag with a playlist."""
        ...

    @abstractmethod
    async def get_playlist_by_nfc(self, nfc_tag_id: str) -> Optional[Dict[str, Any]]:
        """Get playlist associated with an NFC tag."""
        ...

    @abstractmethod
    async def sync_with_filesystem(self, upload_folder: str) -> Dict[str, Any]:
        """Synchronize playlists with filesystem."""
        ...


class TrackServiceProtocol(Protocol):
    """Protocol for track service operations."""

    @abstractmethod
    async def get_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get all tracks for a playlist."""
        ...

    @abstractmethod
    async def add_track(self, playlist_id: str, track_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a track to a playlist."""
        ...

    @abstractmethod
    async def update_track(self, track_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update track metadata."""
        ...

    @abstractmethod
    async def delete_track(self, track_id: str) -> bool:
        """Delete a track."""
        ...

    @abstractmethod
    async def reorder_tracks(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Reorder tracks in a playlist."""
        ...

    @abstractmethod
    async def get_next_track(self, playlist_id: str, current_track_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the next track in a playlist."""
        ...

    @abstractmethod
    async def get_previous_track(self, playlist_id: str, current_track_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the previous track in a playlist."""
        ...