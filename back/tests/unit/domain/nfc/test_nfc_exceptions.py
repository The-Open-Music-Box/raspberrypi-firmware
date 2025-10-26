# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Unit tests for NFC domain exceptions."""

import pytest

from app.src.domain.nfc.exceptions.nfc_exceptions import (
    NfcDomainError,
    TagIdentifierError,
    AssociationError,
    DuplicateAssociationError,
    SessionError,
    SessionTimeoutError,
    HardwareError,
    NfcHardwareUnavailableError,
    InvalidTagError,
)


class TestNfcDomainError:
    """Test base NFC domain error."""

    def test_basic_error_creation(self):
        """Test creating basic domain error."""
        message = "Test error message"
        error = NfcDomainError(message)

        assert str(error) == message
        assert error.message == message
        assert error.error_code is None

    def test_error_with_code(self):
        """Test creating error with code."""
        message = "Test error message"
        code = "TEST_ERROR"
        error = NfcDomainError(message, code)

        assert error.message == message
        assert error.error_code == code

    def test_error_inheritance(self):
        """Test that domain error inherits from Exception."""
        error = NfcDomainError("test")
        assert isinstance(error, Exception)


class TestTagIdentifierError:
    """Test tag identifier error."""

    def test_tag_identifier_error_creation(self):
        """Test creating tag identifier error."""
        tag_id = "invalid-tag"
        reason = "Invalid format"

        error = TagIdentifierError(tag_id, reason)

        assert error.tag_id == tag_id
        assert error.reason == reason
        assert error.error_code == "INVALID_TAG_ID"
        assert "Invalid tag identifier 'invalid-tag': Invalid format" in str(error)

    def test_tag_identifier_error_inheritance(self):
        """Test that tag identifier error inherits from NfcDomainError."""
        error = TagIdentifierError("tag", "reason")
        assert isinstance(error, NfcDomainError)


class TestAssociationError:
    """Test association error."""

    def test_association_error_creation(self):
        """Test creating association error."""
        tag_id = "test-tag"
        playlist_id = "test-playlist"
        reason = "Playlist not found"

        error = AssociationError(tag_id, playlist_id, reason)

        assert error.tag_id == tag_id
        assert error.playlist_id == playlist_id
        assert error.reason == reason
        assert error.error_code == "ASSOCIATION_FAILED"
        expected_message = "Cannot associate tag 'test-tag' with playlist 'test-playlist': Playlist not found"
        assert str(error) == expected_message

    def test_association_error_inheritance(self):
        """Test that association error inherits from NfcDomainError."""
        error = AssociationError("tag", "playlist", "reason")
        assert isinstance(error, NfcDomainError)


class TestDuplicateAssociationError:
    """Test duplicate association error."""

    def test_duplicate_association_error_creation(self):
        """Test creating duplicate association error."""
        tag_id = "test-tag"
        current_playlist = "current-playlist"
        requested_playlist = "requested-playlist"

        error = DuplicateAssociationError(tag_id, current_playlist, requested_playlist)

        assert error.tag_id == tag_id
        assert error.current_playlist_id == current_playlist
        assert error.playlist_id == requested_playlist
        assert error.error_code == "DUPLICATE_ASSOCIATION"
        assert "already associated with playlist 'current-playlist'" in str(error)

    def test_duplicate_association_error_inheritance(self):
        """Test that duplicate association error inherits from AssociationError."""
        error = DuplicateAssociationError("tag", "current", "requested")
        assert isinstance(error, AssociationError)
        assert isinstance(error, NfcDomainError)


class TestSessionError:
    """Test session error."""

    def test_session_error_creation(self):
        """Test creating session error."""
        session_id = "session-123"
        message = "Session is invalid"

        error = SessionError(session_id, message)

        assert error.session_id == session_id
        assert error.error_code == "SESSION_ERROR"
        assert "Session 'session-123': Session is invalid" in str(error)

    def test_session_error_inheritance(self):
        """Test that session error inherits from NfcDomainError."""
        error = SessionError("session", "message")
        assert isinstance(error, NfcDomainError)


class TestSessionTimeoutError:
    """Test session timeout error."""

    def test_session_timeout_error_creation(self):
        """Test creating session timeout error."""
        session_id = "session-123"
        timeout_seconds = 60

        error = SessionTimeoutError(session_id, timeout_seconds)

        assert error.session_id == session_id
        assert error.timeout_seconds == timeout_seconds
        assert error.error_code == "SESSION_TIMEOUT"
        assert "timed out after 60 seconds" in str(error)

    def test_session_timeout_error_inheritance(self):
        """Test that session timeout error inherits from SessionError."""
        error = SessionTimeoutError("session", 60)
        assert isinstance(error, SessionError)
        assert isinstance(error, NfcDomainError)


class TestHardwareError:
    """Test hardware error."""

    def test_hardware_error_creation(self):
        """Test creating hardware error."""
        operation = "read_tag"
        hardware_message = "I2C communication failed"

        error = HardwareError(operation, hardware_message)

        assert error.operation == operation
        assert error.hardware_message == hardware_message
        assert error.error_code == "HARDWARE_ERROR"
        expected_message = "NFC hardware error during 'read_tag': I2C communication failed"
        assert str(error) == expected_message

    def test_hardware_error_inheritance(self):
        """Test that hardware error inherits from NfcDomainError."""
        error = HardwareError("operation", "message")
        assert isinstance(error, NfcDomainError)


class TestNfcHardwareUnavailableError:
    """Test NFC hardware unavailable error."""

    def test_hardware_unavailable_error_default(self):
        """Test creating hardware unavailable error with default reason."""
        error = NfcHardwareUnavailableError()

        assert error.operation == "hardware_initialization"
        assert error.hardware_message == "Hardware not available"
        assert error.error_code == "HARDWARE_UNAVAILABLE"

    def test_hardware_unavailable_error_custom_reason(self):
        """Test creating hardware unavailable error with custom reason."""
        reason = "Device not connected"
        error = NfcHardwareUnavailableError(reason)

        assert error.hardware_message == reason

    def test_hardware_unavailable_error_inheritance(self):
        """Test that hardware unavailable error inherits from HardwareError."""
        error = NfcHardwareUnavailableError()
        assert isinstance(error, HardwareError)
        assert isinstance(error, NfcDomainError)


class TestInvalidTagError:
    """Test invalid tag error."""

    def test_invalid_tag_error_creation(self):
        """Test creating invalid tag error."""
        tag_id = "corrupt-tag"
        validation_error = "Checksum mismatch"

        error = InvalidTagError(tag_id, validation_error)

        assert error.tag_id == tag_id
        assert error.validation_error == validation_error
        assert error.error_code == "INVALID_TAG"
        expected_message = "Invalid NFC tag 'corrupt-tag': Checksum mismatch"
        assert str(error) == expected_message

    def test_invalid_tag_error_inheritance(self):
        """Test that invalid tag error inherits from NfcDomainError."""
        error = InvalidTagError("tag", "validation error")
        assert isinstance(error, NfcDomainError)


class TestExceptionHierarchy:
    """Test exception hierarchy and relationships."""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all NFC exceptions inherit from NfcDomainError."""
        exceptions = [
            TagIdentifierError("tag", "reason"),
            AssociationError("tag", "playlist", "reason"),
            DuplicateAssociationError("tag", "current", "requested"),
            SessionError("session", "message"),
            SessionTimeoutError("session", 60),
            HardwareError("operation", "message"),
            NfcHardwareUnavailableError(),
            InvalidTagError("tag", "validation"),
        ]

        for exception in exceptions:
            assert isinstance(exception, NfcDomainError)
            assert isinstance(exception, Exception)

    def test_specialized_exception_inheritance(self):
        """Test specialized exception inheritance chains."""
        # DuplicateAssociationError -> AssociationError -> NfcDomainError
        duplicate_error = DuplicateAssociationError("tag", "current", "requested")
        assert isinstance(duplicate_error, AssociationError)
        assert isinstance(duplicate_error, NfcDomainError)

        # SessionTimeoutError -> SessionError -> NfcDomainError
        timeout_error = SessionTimeoutError("session", 60)
        assert isinstance(timeout_error, SessionError)
        assert isinstance(timeout_error, NfcDomainError)

        # NfcHardwareUnavailableError -> HardwareError -> NfcDomainError
        unavailable_error = NfcHardwareUnavailableError()
        assert isinstance(unavailable_error, HardwareError)
        assert isinstance(unavailable_error, NfcDomainError)