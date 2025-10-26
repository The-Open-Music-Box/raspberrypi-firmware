"""
Comprehensive tests for Track domain entity.

Tests cover:
- Track construction
- Factory methods
- Property aliases
- Domain validation
- File system operations
- Edge cases
"""

import pytest
from pathlib import Path
from app.src.domain.data.models.track import Track


class TestTrackConstruction:
    """Test track construction and initialization."""

    def test_create_track_minimal(self):
        """Test creating track with minimal required fields."""
        track = Track(
            track_number=1,
            title="Test Song",
            filename="test.mp3",
            file_path="/music/test.mp3"
        )

        assert track.track_number == 1
        assert track.title == "Test Song"
        assert track.filename == "test.mp3"
        assert track.file_path == "/music/test.mp3"
        assert track.duration_ms is None
        assert track.artist is None
        assert track.album is None
        assert track.id is None

    def test_create_track_full(self):
        """Test creating track with all fields."""
        track = Track(
            track_number=5,
            title="Complete Song",
            filename="complete.flac",
            file_path="/music/albums/complete.flac",
            duration_ms=240000,
            artist="Test Artist",
            album="Test Album",
            id="track-123"
        )

        assert track.track_number == 5
        assert track.title == "Complete Song"
        assert track.filename == "complete.flac"
        assert track.file_path == "/music/albums/complete.flac"
        assert track.duration_ms == 240000
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.id == "track-123"


class TestTrackFactoryMethods:
    """Test track factory methods."""

    def test_from_file_defaults(self):
        """Test creating track from file with defaults."""
        track = Track.from_file("/music/my_song.mp3")

        assert track.track_number == 1
        assert track.title == "my_song"
        assert track.filename == "my_song.mp3"
        assert track.file_path == "/music/my_song.mp3"

    def test_from_file_with_track_number(self):
        """Test creating track from file with custom track number."""
        track = Track.from_file("/music/song.mp3", track_number=10)

        assert track.track_number == 10

    def test_from_file_complex_path(self):
        """Test creating track from complex file path."""
        track = Track.from_file("/home/user/Music/Artists/Album Name/03 - Track Title.flac", 3)

        assert track.track_number == 3
        assert track.title == "03 - Track Title"
        assert track.filename == "03 - Track Title.flac"
        assert "Album Name" in track.file_path

    def test_from_file_windows_path(self):
        """Test creating track from Windows-style path."""
        track = Track.from_file("C:\\Music\\song.mp3")

        # On Unix systems, backslashes aren't path separators
        # so this entire string becomes the filename
        assert "song.mp3" in track.filename
        assert "song" in track.title


class TestTrackPropertyAliases:
    """Test track property aliases for API compatibility."""

    def test_number_property_getter(self):
        """Test number property returns track_number."""
        track = Track.from_file("/song.mp3", 5)

        assert track.number == 5
        assert track.number == track.track_number

    def test_number_property_setter(self):
        """Test number property setter updates track_number."""
        track = Track.from_file("/song.mp3", 1)
        track.number = 10

        assert track.track_number == 10
        assert track.number == 10

    def test_path_property_returns_pathlib_path(self):
        """Test path property returns pathlib Path object."""
        track = Track.from_file("/music/test.mp3")

        assert isinstance(track.path, Path)
        assert str(track.path) == "/music/test.mp3"

    def test_duration_property_converts_to_seconds(self):
        """Test duration property converts milliseconds to seconds."""
        track = Track.from_file("/song.mp3")
        track.duration_ms = 180000  # 3 minutes

        assert track.duration == 180.0
        assert track.duration == track.duration_ms / 1000.0

    def test_duration_property_none_handling(self):
        """Test duration property when duration_ms is None."""
        track = Track.from_file("/song.mp3")
        track.duration_ms = None

        assert track.duration is None

    def test_exists_property_false(self):
        """Test exists property for non-existent file."""
        track = Track.from_file("/nonexistent/file.mp3")

        assert track.exists is False

    def test_exists_property_true(self, tmp_path):
        """Test exists property for existing file."""
        # Create a temporary file
        test_file = tmp_path / "test_song.mp3"
        test_file.write_text("fake audio data")

        track = Track.from_file(str(test_file))

        assert track.exists is True


class TestTrackValidation:
    """Test track validation business rules."""

    def test_is_valid_true(self):
        """Test valid track."""
        track = Track(
            track_number=1,
            title="Valid Song",
            filename="valid.mp3",
            file_path="/music/valid.mp3"
        )

        assert track.is_valid() is True

    def test_is_valid_zero_track_number(self):
        """Test track with zero track number is invalid."""
        track = Track(
            track_number=0,
            title="Invalid",
            filename="invalid.mp3",
            file_path="/music/invalid.mp3"
        )

        assert track.is_valid() is False

    def test_is_valid_negative_track_number(self):
        """Test track with negative track number is invalid."""
        track = Track(
            track_number=-1,
            title="Invalid",
            filename="invalid.mp3",
            file_path="/music/invalid.mp3"
        )

        assert track.is_valid() is False

    def test_is_valid_empty_title(self):
        """Test track with empty title is invalid."""
        track = Track(
            track_number=1,
            title="",
            filename="file.mp3",
            file_path="/music/file.mp3"
        )

        assert track.is_valid() is False

    def test_is_valid_whitespace_title(self):
        """Test track with whitespace-only title is invalid."""
        track = Track(
            track_number=1,
            title="   ",
            filename="file.mp3",
            file_path="/music/file.mp3"
        )

        assert track.is_valid() is False

    def test_is_valid_empty_filename(self):
        """Test track with empty filename is invalid."""
        track = Track(
            track_number=1,
            title="Title",
            filename="",
            file_path="/music/file.mp3"
        )

        assert track.is_valid() is False

    def test_is_valid_empty_file_path(self):
        """Test track with empty file path is invalid."""
        track = Track(
            track_number=1,
            title="Title",
            filename="file.mp3",
            file_path=""
        )

        assert track.is_valid() is False

    def test_is_valid_all_fields_valid_but_optional_missing(self):
        """Test track is valid even without optional fields."""
        track = Track(
            track_number=1,
            title="Title",
            filename="file.mp3",
            file_path="/music/file.mp3",
            duration_ms=None,
            artist=None,
            album=None,
            id=None
        )

        assert track.is_valid() is True


class TestTrackDisplayMethods:
    """Test track display and formatting methods."""

    def test_str_representation(self):
        """Test string representation of track."""
        track = Track.from_file("/music/song.mp3", 5)

        result = str(track)

        assert result == "5. song"

    def test_str_representation_with_custom_title(self):
        """Test string representation with custom title."""
        track = Track(
            track_number=3,
            title="Custom Title",
            filename="file.mp3",
            file_path="/music/file.mp3"
        )

        result = str(track)

        assert result == "3. Custom Title"

    def test_get_display_name_no_artist(self):
        """Test display name without artist."""
        track = Track.from_file("/music/song.mp3")
        track.title = "My Song"

        display_name = track.get_display_name()

        assert display_name == "My Song"

    def test_get_display_name_with_artist(self):
        """Test display name with artist."""
        track = Track.from_file("/music/song.mp3")
        track.title = "My Song"
        track.artist = "The Artist"

        display_name = track.get_display_name()

        assert display_name == "The Artist - My Song"

    def test_get_display_name_empty_artist(self):
        """Test display name with empty artist string."""
        track = Track.from_file("/music/song.mp3")
        track.title = "My Song"
        track.artist = ""

        display_name = track.get_display_name()

        assert display_name == "My Song"


class TestTrackDurationHandling:
    """Test track duration handling and conversions."""

    def test_duration_ms_to_seconds(self):
        """Test duration conversion from milliseconds to seconds."""
        track = Track.from_file("/song.mp3")
        track.duration_ms = 3500

        assert track.duration == 3.5

    def test_duration_zero(self):
        """Test zero duration."""
        track = Track.from_file("/song.mp3")
        track.duration_ms = 0

        assert track.duration == 0.0

    def test_duration_very_long(self):
        """Test very long duration (e.g., audiobook)."""
        track = Track.from_file("/audiobook.mp3")
        track.duration_ms = 36000000  # 10 hours

        assert track.duration == 36000.0

    def test_duration_fractional_seconds(self):
        """Test fractional seconds in duration."""
        track = Track.from_file("/song.mp3")
        track.duration_ms = 123456  # 123.456 seconds

        assert track.duration == 123.456


class TestTrackEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_unicode_title(self):
        """Test track with unicode characters in title."""
        track = Track(
            track_number=1,
            title="日本語のタイトル 🎵",
            filename="japanese.mp3",
            file_path="/music/japanese.mp3"
        )

        assert track.title == "日本語のタイトル 🎵"
        assert track.is_valid() is True

    def test_very_long_title(self):
        """Test track with very long title."""
        long_title = "A" * 1000
        track = Track(
            track_number=1,
            title=long_title,
            filename="long.mp3",
            file_path="/music/long.mp3"
        )

        assert len(track.title) == 1000
        assert track.is_valid() is True

    def test_special_characters_in_filename(self):
        """Test track with special characters in filename."""
        track = Track.from_file("/music/song's & friend's (remix).mp3")

        assert "song's" in track.title
        assert track.is_valid() is True

    def test_relative_file_path(self):
        """Test track with relative file path."""
        track = Track(
            track_number=1,
            title="Relative",
            filename="song.mp3",
            file_path="./music/song.mp3"
        )

        assert track.file_path == "./music/song.mp3"
        assert track.is_valid() is True

    def test_file_path_without_extension(self):
        """Test track with file path without extension."""
        track = Track.from_file("/music/noextension")

        assert track.filename == "noextension"
        assert track.title == "noextension"

    def test_track_number_very_large(self):
        """Test track with very large track number."""
        track = Track.from_file("/song.mp3", track_number=999999)

        assert track.track_number == 999999
        assert track.is_valid() is True

    def test_all_audio_formats(self):
        """Test track creation with various audio formats."""
        formats = ["mp3", "flac", "wav", "ogg", "m4a", "aac", "opus"]

        for fmt in formats:
            track = Track.from_file(f"/music/song.{fmt}")
            assert track.filename == f"song.{fmt}"
            assert track.title == "song"
            assert track.is_valid() is True

    def test_metadata_fields_optional(self):
        """Test that metadata fields are truly optional."""
        track = Track(
            track_number=1,
            title="Minimal",
            filename="minimal.mp3",
            file_path="/minimal.mp3"
        )

        # Should be valid without artist, album, duration
        assert track.artist is None
        assert track.album is None
        assert track.duration_ms is None
        assert track.id is None
        assert track.is_valid() is True

    def test_immutable_path_property(self):
        """Test that path property creates new Path each time."""
        track = Track.from_file("/music/song.mp3")

        path1 = track.path
        path2 = track.path

        # Should return equivalent paths
        assert path1 == path2
        assert str(path1) == str(path2)
