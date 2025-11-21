# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
NFC Service Protocol for Domain-Driven Architecture.

This module defines the protocol interface for NFC services,
promoting loose coupling and testability in the domain layer.
"""

from typing import Protocol, Dict, Any, Optional, List
from abc import abstractmethod


class NFCServiceProtocol(Protocol):
    """Protocol defining the NFC service interface for domain architecture.

    This protocol ensures that any NFC service implementation provides
    the necessary methods for NFC tag detection, association management,
    and integration with the playlist system.
    """

    @abstractmethod
    async def start_association(
        self, playlist_id: str, timeout_s: int = 60, override: bool = False
    ) -> Dict[str, Any]:
        """Start an NFC tag association session.

        Args:
            playlist_id: ID of the playlist to associate with NFC tag
            timeout_s: Session timeout in seconds
            override: Whether to override existing associations

        Returns:
            Dictionary containing session details (assoc_id, expires_at, etc.)
        """
        ...

    @abstractmethod
    async def cancel_association(self, assoc_id: str) -> bool:
        """Cancel an active NFC association session.

        Args:
            assoc_id: Association session ID to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        ...

    @abstractmethod
    async def get_session_status(self, assoc_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of an association session.

        Args:
            assoc_id: Association session ID to query

        Returns:
            Session status dictionary or None if session doesn't exist
        """
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the NFC service is available and functional.

        Returns:
            True if NFC service is available, False otherwise
        """
        ...

    @abstractmethod
    async def handle_tag_detected(
        self, tag_id: str, tag_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle detection of an NFC tag.

        Args:
            tag_id: Unique identifier of the detected tag
            tag_data: Optional additional tag data
        """
        ...

    @abstractmethod
    def set_state_manager(self, state_manager: Any) -> None:
        """Inject the state manager for event broadcasting.

        Args:
            state_manager: StateManager instance for broadcasting events
        """
        ...

    @abstractmethod
    def set_socketio(self, socketio: Any) -> None:
        """Set Socket.IO instance for real-time communication.

        Args:
            socketio: Socket.IO server instance
        """
        ...

    @abstractmethod
    def load_mapping(self, mapping: List[Dict[str, Any]]) -> None:
        """Load playlist mapping data into the service.

        Args:
            mapping: List of playlist dictionaries for NFC associations
        """
        ...


class NFCHardwareProtocol(Protocol):
    """Protocol for NFC hardware interface implementations."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if NFC hardware is available.

        Returns:
            True if hardware is available, False otherwise
        """
        ...

    @abstractmethod
    async def start_listening(self) -> bool:
        """Start listening for NFC tags.

        Returns:
            True if listening started successfully, False otherwise
        """
        ...

    @abstractmethod
    async def stop_listening(self) -> bool:
        """Stop listening for NFC tags.

        Returns:
            True if listening stopped successfully, False otherwise
        """
        ...

    @abstractmethod
    def is_listening(self) -> bool:
        """Check if currently listening for tags.

        Returns:
            True if listening, False otherwise
        """
        ...

    @abstractmethod
    async def read_tag(self) -> Optional[Dict[str, Any]]:
        """Read data from an NFC tag.

        Returns:
            Dictionary containing tag data, or None if no tag available
        """
        ...

    @abstractmethod
    async def write_tag(self, tag_id: str, data: Dict[str, Any]) -> bool:
        """Write data to an NFC tag.

        Args:
            tag_id: Unique identifier for the tag
            data: Data to write to the tag

        Returns:
            True if write was successful, False otherwise
        """
        ...


# Type aliases for convenience
NFCService = NFCServiceProtocol
NFCHardware = NFCHardwareProtocol
