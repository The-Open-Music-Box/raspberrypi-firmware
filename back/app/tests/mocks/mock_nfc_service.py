# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock NFC service for testing.

This module provides a mock implementation of the NFC service
for testing purposes without requiring actual NFC hardware.
Fully autonomous without legacy interface dependencies.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class MockAssocSession:
    """Mock association session for testing."""

    assoc_id: str
    playlist_id: str
    state: str  # listening | duplicate | success | stopped | timeout | error
    started_at: float
    timeout_at: float
    tag_id: Optional[str] = None
    conflict_playlist_id: Optional[str] = None


class MockNfcService:
    """Mock NFC service implementation for testing.

    Simulates NFC tag reading and writing without actual hardware dependencies,
    enabling comprehensive testing of NFC-related functionality.
    """

    def __init__(self, socketio: Any = None, nfc_handler: Any = None):
        """Initialize the mock NFC service.

        Args:
            socketio: Optional Socket.IO instance (for compatibility)
            nfc_handler: Optional NFC handler (for compatibility)
        """
        # Basic NFC functionality
        self._is_available = True
        self._is_listening = False
        self._simulated_tags: Dict[str, Dict] = {}
        self._last_read_tag: Optional[Dict] = None

        # Association session management
        self._active_assoc_id: Optional[str] = None
        self._assoc_sessions: Dict[str, MockAssocSession] = {}
        self._session_counter = 0

        # Service dependencies (mocked)
        self.socketio = socketio
        self._nfc_handler = nfc_handler
        self._state_manager: Any = None
        self._playlist_mappings: List[Dict[str, Any]] = []

        # State flags
        self.waiting_for_tag = False
        self.current_playlist_id: Optional[str] = None

    def is_available(self) -> bool:
        """Check if the NFC service is available.

        Returns:
            True if NFC service is available, False otherwise
        """
        return self._is_available

    def start_listening(self) -> bool:
        """Start listening for NFC tags.

        Returns:
            True if listening started successfully, False otherwise
        """
        if not self._is_available:
            return False
        self._is_listening = True
        return True

    def stop_listening(self) -> bool:
        """Stop listening for NFC tags.

        Returns:
            True if listening stopped successfully, False otherwise
        """
        self._is_listening = False
        return True

    def is_listening(self) -> bool:
        """Check if the service is currently listening for tags.

        Returns:
            True if listening, False otherwise
        """
        return self._is_listening

    def read_tag(self) -> Optional[Dict]:
        """Read data from an NFC tag.

        Returns:
            Dictionary containing tag data, or None if no tag available
        """
        if not self._is_available or not self._is_listening:
            return None
        return self._last_read_tag

    def write_tag(self, tag_id: str, data: Dict) -> bool:
        """Write data to an NFC tag.

        Args:
            tag_id: Unique identifier for the tag
            data: Data to write to the tag

        Returns:
            True if write was successful, False otherwise
        """
        if not self._is_available:
            return False

        self._simulated_tags[tag_id] = data.copy()
        return True

    def get_tag_info(self, tag_id: str) -> Optional[Dict]:
        """Get information about a specific tag.

        Args:
            tag_id: Unique identifier for the tag

        Returns:
            Dictionary containing tag information, or None if not found
        """
        return self._simulated_tags.get(tag_id)

    # Mock-specific methods for testing
    def set_availability(self, available: bool):
        """Set the availability state for testing.

        Args:
            available: Whether the service should be available
        """
        self._is_available = available

    def simulate_tag_detection(self, tag_id: str, data: Optional[Dict] = None):
        """Simulate detection of an NFC tag.

        Args:
            tag_id: Unique identifier for the simulated tag
            data: Optional data to associate with the tag
        """
        tag_data = {"tag_id": tag_id, "timestamp": "2025-01-27T12:00:00Z"}

        if data:
            tag_data.update(data)

        self._last_read_tag = tag_data

        # Store in simulated tags if not already present
        if tag_id not in self._simulated_tags:
            self._simulated_tags[tag_id] = tag_data

    def simulate_playlist_tag(self, tag_id: str, playlist_id: int):
        """Simulate detection of a playlist-associated tag.

        Args:
            tag_id: Unique identifier for the tag
            playlist_id: ID of the associated playlist
        """
        self.simulate_tag_detection(tag_id, {"playlist_id": playlist_id, "type": "playlist"})

    def get_simulated_tags(self) -> Dict[str, Dict]:
        """Get all simulated tags.

        Returns:
            Dictionary of tag_id -> tag_data mappings
        """
        return self._simulated_tags.copy()

    def clear_simulated_tags(self):
        """Clear all simulated tags."""
        self._simulated_tags.clear()
        self._last_read_tag = None

    def remove_simulated_tag(self, tag_id: str) -> bool:
        """Remove a simulated tag.

        Args:
            tag_id: Unique identifier for the tag to remove

        Returns:
            True if tag was removed, False if not found
        """
        if tag_id in self._simulated_tags:
            del self._simulated_tags[tag_id]
            if self._last_read_tag and self._last_read_tag.get("tag_id") == tag_id:
                self._last_read_tag = None
            return True
        return False

    def get_tag_count(self) -> int:
        """Get the number of simulated tags.

        Returns:
            Number of simulated tags
        """
        return len(self._simulated_tags)

    def reset(self):
        """Reset the mock NFC service to initial state."""
        self._is_available = True
        self._is_listening = False
        self._simulated_tags.clear()
        self._last_read_tag = None
        self._active_assoc_id = None
        self._assoc_sessions.clear()
        self._session_counter = 0
        self.waiting_for_tag = False
        self.current_playlist_id = None

    # Domain Protocol Implementation
    async def start_association(
        self, playlist_id: str, timeout_s: int = 60, override: bool = False
    ) -> Dict[str, Any]:
        """Start an NFC tag association session.

        Args:
            playlist_id: ID of the playlist to associate with NFC tag
            timeout_s: Session timeout in seconds
            override: Whether to override existing associations

        Returns:
            Dictionary containing session details
        """
        self._session_counter += 1
        assoc_id = f"mock_assoc_{self._session_counter}"

        current_time = time.time()
        session = MockAssocSession(
            assoc_id=assoc_id,
            playlist_id=playlist_id,
            state="listening",
            started_at=current_time,
            timeout_at=current_time + timeout_s,
        )

        self._assoc_sessions[assoc_id] = session
        self._active_assoc_id = assoc_id

        return {
            "assoc_id": assoc_id,
            "playlist_id": playlist_id,
            "state": "listening",
            "expires_at": session.timeout_at,
            "started_at": session.started_at,
        }

    async def cancel_association(self, assoc_id: str) -> bool:
        """Cancel an active NFC association session.

        Args:
            assoc_id: Association session ID to cancel

        Returns:
            True if cancellation was successful
        """
        if assoc_id in self._assoc_sessions:
            self._assoc_sessions[assoc_id].state = "stopped"
            if self._active_assoc_id == assoc_id:
                self._active_assoc_id = None
            return True
        return False

    async def cancel_association_by_playlist(self, playlist_id: str) -> bool:
        """Cancel association session by playlist ID.

        Args:
            playlist_id: Playlist ID to cancel association for

        Returns:
            True if cancellation was successful
        """
        for session in self._assoc_sessions.values():
            if session.playlist_id == playlist_id and session.state == "listening":
                session.state = "stopped"
                if self._active_assoc_id == session.assoc_id:
                    self._active_assoc_id = None
                return True
        return False

    async def get_session_status(self, assoc_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of an association session.

        Args:
            assoc_id: Association session ID to query

        Returns:
            Session status dictionary or None if session doesn't exist
        """
        session = self._assoc_sessions.get(assoc_id)
        if not session:
            return None

        return {
            "assoc_id": session.assoc_id,
            "playlist_id": session.playlist_id,
            "state": session.state,
            "started_at": session.started_at,
            "timeout_at": session.timeout_at,
            "tag_id": session.tag_id,
            "conflict_playlist_id": session.conflict_playlist_id,
        }

    async def get_session_snapshot(self, assoc_id: str) -> Optional[Dict[str, Any]]:
        """Get session snapshot for WebSocket clients.

        Args:
            assoc_id: Association session ID

        Returns:
            Session snapshot or None
        """
        return await self.get_session_status(assoc_id)

    async def handle_tag_detected(
        self, tag_id: str, tag_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle detection of an NFC tag.

        Args:
            tag_id: Unique identifier of the detected tag
            tag_data: Optional additional tag data
        """
        # Store the detected tag
        self.simulate_tag_detection(tag_id, tag_data)

        # If there's an active association session, process it
        if self._active_assoc_id:
            session = self._assoc_sessions.get(self._active_assoc_id)
            if session and session.state == "listening":
                # Check if tag is already associated with another playlist
                existing_association = self._find_existing_association(tag_id)
                if existing_association and not session.conflict_playlist_id:
                    session.state = "duplicate"
                    session.tag_id = tag_id
                    session.conflict_playlist_id = existing_association
                else:
                    # Success - associate the tag
                    session.state = "success"
                    session.tag_id = tag_id
                    self._simulated_tags[tag_id] = {
                        "tag_id": tag_id,
                        "playlist_id": session.playlist_id,
                        "type": "playlist",
                        "associated_at": time.time(),
                    }

    def _find_existing_association(self, tag_id: str) -> Optional[str]:
        """Find existing playlist association for a tag.

        Args:
            tag_id: Tag ID to search for

        Returns:
            Playlist ID if association exists, None otherwise
        """
        tag_data = self._simulated_tags.get(tag_id)
        if tag_data and tag_data.get("type") == "playlist":
            return tag_data.get("playlist_id")
        return None

    def set_state_manager(self, state_manager: Any) -> None:
        """Inject the state manager for event broadcasting.

        Args:
            state_manager: StateManager instance
        """
        self._state_manager = state_manager

    def set_socketio(self, socketio: Any) -> None:
        """Set Socket.IO instance for real-time communication.

        Args:
            socketio: Socket.IO server instance
        """
        self.socketio = socketio

    def load_mapping(self, mapping: List[Dict[str, Any]]) -> None:
        """Load playlist mapping data into the service.

        Args:
            mapping: List of playlist dictionaries
        """
        self._playlist_mappings = mapping.copy()

    # Compatibility methods for existing tests
    def get_all_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all association sessions for testing.

        Returns:
            Dictionary of session_id -> session_data
        """
        return {
            assoc_id: {
                "assoc_id": session.assoc_id,
                "playlist_id": session.playlist_id,
                "state": session.state,
                "started_at": session.started_at,
                "timeout_at": session.timeout_at,
                "tag_id": session.tag_id,
                "conflict_playlist_id": session.conflict_playlist_id,
            }
            for assoc_id, session in self._assoc_sessions.items()
        }

    def simulate_successful_association(self, playlist_id: str, tag_id: str) -> str:
        """Simulate a successful NFC association for testing.

        Args:
            playlist_id: Playlist ID to associate
            tag_id: NFC tag ID

        Returns:
            Association session ID
        """
        import asyncio

        # Create association session
        result = asyncio.run(self.start_association(playlist_id))
        assoc_id = result["assoc_id"]

        # Simulate tag detection and success
        asyncio.run(self.handle_tag_detected(tag_id))

        return assoc_id
