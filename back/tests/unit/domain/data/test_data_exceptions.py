"""
Comprehensive tests for data domain exceptions.

Tests cover:
- Exception inheritance
- Exception messages
- Exception attributes
- All exception types
"""

import pytest
from app.src.domain.data.exceptions.data_exceptions import (
    DataDomainError,
    PlaylistNotFoundError,
    TrackNotFoundError,
    PlaylistValidationError,
    TrackValidationError
)


class TestDataDomainError:
    """Test DataDomainError base exception."""

    def test_is_exception(self):
        """Test DataDomainError is an Exception."""
        error = DataDomainError("Test error")

        assert isinstance(error, Exception)

    def test_can_raise_and_catch(self):
        """Test can raise and catch DataDomainError."""
        with pytest.raises(DataDomainError):
            raise DataDomainError("Test error")

    def test_error_message(self):
        """Test error message is preserved."""
        error = DataDomainError("Custom error message")

        assert str(error) == "Custom error message"

    def test_can_catch_derived_exceptions(self):
        """Test can catch derived exceptions as DataDomainError."""
        with pytest.raises(DataDomainError):
            raise PlaylistNotFoundError("pl-123")


class TestPlaylistNotFoundError:
    """Test PlaylistNotFoundError."""

    def test_inherits_from_data_domain_error(self):
        """Test inheritance chain."""
        error = PlaylistNotFoundError("pl-123")

        assert isinstance(error, DataDomainError)
        assert isinstance(error, Exception)

    def test_stores_playlist_id(self):
        """Test playlist ID is stored as attribute."""
        error = PlaylistNotFoundError("pl-123")

        assert error.playlist_id == "pl-123"

    def test_error_message_includes_id(self):
        """Test error message includes playlist ID."""
        error = PlaylistNotFoundError("pl-456")

        assert "pl-456" in str(error)
        assert "Playlist not found" in str(error)

    def test_can_raise_and_catch(self):
        """Test can raise and catch PlaylistNotFoundError."""
        with pytest.raises(PlaylistNotFoundError) as exc_info:
            raise PlaylistNotFoundError("pl-123")

        assert exc_info.value.playlist_id == "pl-123"

    def test_catch_as_base_exception(self):
        """Test can catch as DataDomainError."""
        with pytest.raises(DataDomainError) as exc_info:
            raise PlaylistNotFoundError("pl-123")

        assert isinstance(exc_info.value, PlaylistNotFoundError)

    def test_with_different_id_formats(self):
        """Test with various ID formats."""
        ids = ["123", "pl-abc-def", "playlist_with_underscores", "プレイリスト"]

        for playlist_id in ids:
            error = PlaylistNotFoundError(playlist_id)
            assert error.playlist_id == playlist_id
            assert playlist_id in str(error)

    def test_with_empty_id(self):
        """Test with empty playlist ID."""
        error = PlaylistNotFoundError("")

        assert error.playlist_id == ""
        assert "Playlist not found:" in str(error)


class TestTrackNotFoundError:
    """Test TrackNotFoundError."""

    def test_inherits_from_data_domain_error(self):
        """Test inheritance chain."""
        error = TrackNotFoundError("track-123")

        assert isinstance(error, DataDomainError)
        assert isinstance(error, Exception)

    def test_stores_track_id(self):
        """Test track ID is stored as attribute."""
        error = TrackNotFoundError("track-789")

        assert error.track_id == "track-789"

    def test_error_message_includes_id(self):
        """Test error message includes track ID."""
        error = TrackNotFoundError("track-456")

        assert "track-456" in str(error)
        assert "Track not found" in str(error)

    def test_can_raise_and_catch(self):
        """Test can raise and catch TrackNotFoundError."""
        with pytest.raises(TrackNotFoundError) as exc_info:
            raise TrackNotFoundError("track-123")

        assert exc_info.value.track_id == "track-123"

    def test_with_different_id_formats(self):
        """Test with various ID formats."""
        ids = ["123", "track-abc-def", "track_with_underscores", "トラック"]

        for track_id in ids:
            error = TrackNotFoundError(track_id)
            assert error.track_id == track_id
            assert track_id in str(error)


class TestPlaylistValidationError:
    """Test PlaylistValidationError."""

    def test_inherits_from_data_domain_error(self):
        """Test inheritance chain."""
        error = PlaylistValidationError("Invalid playlist")

        assert isinstance(error, DataDomainError)
        assert isinstance(error, Exception)

    def test_error_message_format(self):
        """Test error message format."""
        error = PlaylistValidationError("Name cannot be empty")

        assert "Playlist validation error" in str(error)
        assert "Name cannot be empty" in str(error)

    def test_can_raise_and_catch(self):
        """Test can raise and catch PlaylistValidationError."""
        with pytest.raises(PlaylistValidationError) as exc_info:
            raise PlaylistValidationError("Invalid name")

        assert "Invalid name" in str(exc_info.value)

    def test_with_detailed_validation_message(self):
        """Test with detailed validation message."""
        message = "Playlist must have at least one track"
        error = PlaylistValidationError(message)

        assert message in str(error)

    def test_with_multiple_validation_errors(self):
        """Test with multiple validation errors in message."""
        message = "Multiple errors: empty name, no tracks, invalid ID"
        error = PlaylistValidationError(message)

        assert message in str(error)


class TestTrackValidationError:
    """Test TrackValidationError."""

    def test_inherits_from_data_domain_error(self):
        """Test inheritance chain."""
        error = TrackValidationError("Invalid track")

        assert isinstance(error, DataDomainError)
        assert isinstance(error, Exception)

    def test_error_message_format(self):
        """Test error message format."""
        error = TrackValidationError("Track number must be positive")

        assert "Track validation error" in str(error)
        assert "Track number must be positive" in str(error)

    def test_can_raise_and_catch(self):
        """Test can raise and catch TrackValidationError."""
        with pytest.raises(TrackValidationError) as exc_info:
            raise TrackValidationError("Invalid file path")

        assert "Invalid file path" in str(exc_info.value)

    def test_with_field_specific_message(self):
        """Test with field-specific validation message."""
        message = "Field 'duration_ms' must be a positive integer"
        error = TrackValidationError(message)

        assert message in str(error)


class TestExceptionHierarchy:
    """Test exception hierarchy and catching."""

    def test_catch_all_data_exceptions(self):
        """Test catching all data domain exceptions."""
        exceptions = [
            PlaylistNotFoundError("pl-1"),
            TrackNotFoundError("track-1"),
            PlaylistValidationError("Invalid"),
            TrackValidationError("Invalid")
        ]

        for exc in exceptions:
            with pytest.raises(DataDomainError):
                raise exc

    def test_catch_specific_exception_type(self):
        """Test catching specific exception type."""
        with pytest.raises(PlaylistNotFoundError):
            raise PlaylistNotFoundError("pl-123")

        # Should not catch other types
        with pytest.raises(TrackNotFoundError):
            raise TrackNotFoundError("track-123")

    def test_exception_type_checking(self):
        """Test exception type checking."""
        playlist_error = PlaylistNotFoundError("pl-1")
        track_error = TrackNotFoundError("track-1")
        validation_error = PlaylistValidationError("Invalid")

        assert isinstance(playlist_error, PlaylistNotFoundError)
        assert not isinstance(playlist_error, TrackNotFoundError)
        assert not isinstance(playlist_error, PlaylistValidationError)

        assert isinstance(track_error, TrackNotFoundError)
        assert not isinstance(track_error, PlaylistNotFoundError)

        assert isinstance(validation_error, PlaylistValidationError)


class TestExceptionUsageScenarios:
    """Test common exception usage scenarios."""

    def test_not_found_in_repository_lookup(self):
        """Test using not found exception in repository pattern."""
        def get_playlist(playlist_id: str):
            # Simulate repository lookup
            playlists = {}
            if playlist_id not in playlists:
                raise PlaylistNotFoundError(playlist_id)
            return playlists[playlist_id]

        with pytest.raises(PlaylistNotFoundError) as exc_info:
            get_playlist("nonexistent")

        assert exc_info.value.playlist_id == "nonexistent"

    def test_validation_in_domain_service(self):
        """Test using validation exception in domain service."""
        def validate_playlist_name(name: str):
            if not name or not name.strip():
                raise PlaylistValidationError("Playlist name cannot be empty")
            if len(name) > 255:
                raise PlaylistValidationError("Playlist name too long (max 255 chars)")

        with pytest.raises(PlaylistValidationError) as exc_info:
            validate_playlist_name("")

        assert "cannot be empty" in str(exc_info.value)

    def test_chained_exception_handling(self):
        """Test exception handling with multiple layers."""
        def inner_function():
            raise TrackNotFoundError("track-123")

        def outer_function():
            try:
                inner_function()
            except TrackNotFoundError as e:
                # Re-raise with additional context
                raise TrackValidationError(f"Cannot validate: {str(e)}")

        with pytest.raises(TrackValidationError) as exc_info:
            outer_function()

        assert "track-123" in str(exc_info.value)


class TestExceptionEdgeCases:
    """Test edge cases and special scenarios."""

    def test_exception_with_unicode_message(self):
        """Test exception with unicode in message."""
        error = PlaylistValidationError("プレイリスト名が無効です")

        assert "プレイリスト名が無効です" in str(error)

    def test_exception_with_very_long_message(self):
        """Test exception with very long message."""
        long_message = "A" * 10000
        error = PlaylistValidationError(long_message)

        assert len(str(error)) > 10000

    def test_exception_with_special_characters(self):
        """Test exception with special characters in message."""
        message = "Invalid chars: <>:\"|?*\\"
        error = TrackValidationError(message)

        assert message in str(error)

    def test_exception_equality(self):
        """Test exception equality is based on message."""
        error1 = PlaylistNotFoundError("pl-123")
        error2 = PlaylistNotFoundError("pl-123")

        # Exceptions are not equal by default (different instances)
        assert error1 is not error2
        # But have same message and playlist_id
        assert str(error1) == str(error2)
        assert error1.playlist_id == error2.playlist_id

    def test_exception_repr(self):
        """Test exception string representation."""
        error = PlaylistNotFoundError("pl-123")

        error_str = str(error)
        assert "pl-123" in error_str
        assert "Playlist not found" in error_str
