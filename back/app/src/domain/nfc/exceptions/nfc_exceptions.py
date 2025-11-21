# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Domain Exceptions."""

from typing import Optional


class NfcDomainError(Exception):
    """Base exception for all NFC domain errors."""

    def __init__(self, message: str, error_code: Optional[str] = None):
        """Initialize NFC domain error.

        Args:
            message: Human-readable error message
            error_code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class TagIdentifierError(NfcDomainError):
    """Exception raised when tag identifier is invalid."""

    def __init__(self, tag_id: str, reason: str):
        """Initialize tag identifier error.

        Args:
            tag_id: The invalid tag identifier
            reason: Reason why the identifier is invalid
        """
        message = f"Invalid tag identifier '{tag_id}': {reason}"
        super().__init__(message, "INVALID_TAG_ID")
        self.tag_id = tag_id
        self.reason = reason


class AssociationError(NfcDomainError):
    """Exception raised when tag association fails."""

    def __init__(self, tag_id: str, playlist_id: str, reason: str):
        """Initialize association error.

        Args:
            tag_id: Tag identifier
            playlist_id: Playlist identifier
            reason: Reason for association failure
        """
        message = f"Cannot associate tag '{tag_id}' with playlist '{playlist_id}': {reason}"
        super().__init__(message, "ASSOCIATION_FAILED")
        self.tag_id = tag_id
        self.playlist_id = playlist_id
        self.reason = reason


class DuplicateAssociationError(AssociationError):
    """Exception raised when attempting to associate an already associated tag."""

    def __init__(self, tag_id: str, current_playlist_id: str, requested_playlist_id: str):
        """Initialize duplicate association error.

        Args:
            tag_id: Tag identifier
            current_playlist_id: Currently associated playlist
            requested_playlist_id: Requested new playlist
        """
        reason = f"Tag is already associated with playlist '{current_playlist_id}'"
        super().__init__(tag_id, requested_playlist_id, reason)
        self.current_playlist_id = current_playlist_id
        self.error_code = "DUPLICATE_ASSOCIATION"


class SessionError(NfcDomainError):
    """Exception raised for session-related errors."""

    def __init__(self, session_id: str, message: str):
        """Initialize session error.

        Args:
            session_id: Association session identifier
            message: Error message
        """
        super().__init__(f"Session '{session_id}': {message}", "SESSION_ERROR")
        self.session_id = session_id


class SessionTimeoutError(SessionError):
    """Exception raised when an association session times out."""

    def __init__(self, session_id: str, timeout_seconds: int):
        """Initialize session timeout error.

        Args:
            session_id: Session identifier
            timeout_seconds: Session timeout duration
        """
        message = f"Session timed out after {timeout_seconds} seconds"
        super().__init__(session_id, message)
        self.timeout_seconds = timeout_seconds
        self.error_code = "SESSION_TIMEOUT"


class HardwareError(NfcDomainError):
    """Exception raised for NFC hardware-related errors."""

    def __init__(self, operation: str, hardware_message: str):
        """Initialize hardware error.

        Args:
            operation: Operation that failed
            hardware_message: Hardware-specific error message
        """
        message = f"NFC hardware error during '{operation}': {hardware_message}"
        super().__init__(message, "HARDWARE_ERROR")
        self.operation = operation
        self.hardware_message = hardware_message


class NfcHardwareUnavailableError(HardwareError):
    """Exception raised when NFC hardware is unavailable."""

    def __init__(self, reason: str = "Hardware not available"):
        """Initialize hardware unavailable error.

        Args:
            reason: Reason why hardware is unavailable
        """
        super().__init__("hardware_initialization", reason)
        self.error_code = "HARDWARE_UNAVAILABLE"


class InvalidTagError(NfcDomainError):
    """Exception raised when an NFC tag is invalid or corrupted."""

    def __init__(self, tag_id: str, validation_error: str):
        """Initialize invalid tag error.

        Args:
            tag_id: Tag identifier
            validation_error: Specific validation failure
        """
        message = f"Invalid NFC tag '{tag_id}': {validation_error}"
        super().__init__(message, "INVALID_TAG")
        self.tag_id = tag_id
        self.validation_error = validation_error