"""
Comprehensive tests for FileMetadata value object.

Tests cover:
- Value object creation
- Immutability
- Validation rules
- Properties
- Audio file detection
- Format support checking
- Metadata completeness
"""

import pytest
from app.src.domain.upload.value_objects.file_metadata import FileMetadata


class TestFileMetadataCreation:
    """Test FileMetadata creation and validation."""

    def test_create_minimal_metadata(self):
        """Test creating metadata with minimal fields."""
        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg"
        )

        assert metadata.filename == "test.mp3"
        assert metadata.size_bytes == 1000
        assert metadata.mime_type == "audio/mpeg"
        assert metadata.title is None
        assert metadata.artist is None
        assert metadata.album is None

    def test_create_complete_metadata(self):
        """Test creating metadata with all fields."""
        metadata = FileMetadata(
            filename="song.flac",
            size_bytes=50_000_000,
            mime_type="audio/flac",
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            duration_seconds=240.5,
            bitrate=320,
            sample_rate=44100
        )

        assert metadata.title == "Test Song"
        assert metadata.artist == "Test Artist"
        assert metadata.album == "Test Album"
        assert metadata.duration_seconds == 240.5
        assert metadata.bitrate == 320
        assert metadata.sample_rate == 44100

    def test_create_minimal_factory(self):
        """Test factory method for minimal metadata."""
        metadata = FileMetadata.create_minimal(
            filename="test.mp3",
            size_bytes=5000,
            mime_type="audio/mpeg"
        )

        assert metadata.filename == "test.mp3"
        assert metadata.size_bytes == 5000
        assert metadata.mime_type == "audio/mpeg"


class TestFileMetadataValidation:
    """Test FileMetadata validation rules."""

    def test_empty_filename_raises_error(self):
        """Test empty filename raises ValueError."""
        with pytest.raises(ValueError, match="Filename cannot be empty"):
            FileMetadata(filename="", size_bytes=1000, mime_type="audio/mpeg")

    def test_negative_size_raises_error(self):
        """Test negative size raises ValueError."""
        with pytest.raises(ValueError, match="size cannot be negative"):
            FileMetadata(filename="test.mp3", size_bytes=-1, mime_type="audio/mpeg")

    def test_empty_mime_type_raises_error(self):
        """Test empty MIME type raises ValueError."""
        with pytest.raises(ValueError, match="MIME type is required"):
            FileMetadata(filename="test.mp3", size_bytes=1000, mime_type="")


class TestFileMetadataProperties:
    """Test FileMetadata properties."""

    def test_file_extension_property(self):
        """Test file extension extraction."""
        metadata = FileMetadata.create_minimal("song.mp3", 1000, "audio/mpeg")

        assert metadata.file_extension == ".mp3"

    def test_file_extension_lowercase(self):
        """Test file extension is lowercase."""
        metadata = FileMetadata.create_minimal("SONG.MP3", 1000, "audio/mpeg")

        assert metadata.file_extension == ".mp3"

    def test_display_name_with_title(self):
        """Test display name uses title when available."""
        metadata = FileMetadata(
            filename="file.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            title="My Song"
        )

        assert metadata.display_name == "My Song"

    def test_display_name_without_title(self):
        """Test display name uses filename stem when no title."""
        metadata = FileMetadata.create_minimal("my_song.mp3", 1000, "audio/mpeg")

        assert metadata.display_name == "my_song"

    def test_size_mb_property(self):
        """Test size in megabytes."""
        metadata = FileMetadata.create_minimal("test.mp3", 5_242_880, "audio/mpeg")

        assert metadata.size_mb == 5.0

    def test_duration_formatted_minutes_seconds(self):
        """Test formatted duration."""
        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            duration_seconds=185.0
        )

        assert metadata.duration_formatted == "03:05"

    def test_duration_formatted_no_duration(self):
        """Test formatted duration when None."""
        metadata = FileMetadata.create_minimal("test.mp3", 1000, "audio/mpeg")

        assert metadata.duration_formatted == "Unknown"

    def test_duration_formatted_zero(self):
        """Test formatted duration for zero."""
        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            duration_seconds=0.0
        )

        # Zero duration is treated as "no duration"
        assert metadata.duration_formatted == "Unknown"


class TestAudioFileDetection:
    """Test audio file detection."""

    def test_is_audio_file_true(self):
        """Test audio MIME type detected."""
        metadata = FileMetadata.create_minimal("test.mp3", 1000, "audio/mpeg")

        assert metadata.is_audio_file() is True

    def test_is_audio_file_various_formats(self):
        """Test various audio MIME types."""
        audio_types = [
            "audio/mpeg",
            "audio/wav",
            "audio/flac",
            "audio/ogg",
            "audio/mp4",
            "audio/aac"
        ]

        for mime_type in audio_types:
            metadata = FileMetadata.create_minimal("test", 1000, mime_type)
            assert metadata.is_audio_file() is True

    def test_is_audio_file_false(self):
        """Test non-audio MIME type."""
        metadata = FileMetadata.create_minimal("doc.pdf", 1000, "application/pdf")

        assert metadata.is_audio_file() is False


class TestFormatSupport:
    """Test format support checking."""

    def test_is_supported_format_true(self):
        """Test supported format check."""
        metadata = FileMetadata.create_minimal("test.mp3", 1000, "audio/mpeg")
        supported = {"mp3", "flac", "wav"}

        assert metadata.is_supported_format(supported) is True

    def test_is_supported_format_false(self):
        """Test unsupported format check."""
        metadata = FileMetadata.create_minimal("test.ogg", 1000, "audio/ogg")
        supported = {"mp3", "flac"}

        assert metadata.is_supported_format(supported) is False

    def test_is_supported_format_case_insensitive(self):
        """Test format check is case insensitive."""
        metadata = FileMetadata.create_minimal("TEST.MP3", 1000, "audio/mpeg")
        supported = {"mp3"}

        assert metadata.is_supported_format(supported) is True


class TestMetadataCompleteness:
    """Test metadata completeness checking."""

    def test_has_complete_metadata_true(self):
        """Test complete metadata detection."""
        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            title="Song",
            artist="Artist",
            duration_seconds=180.0
        )

        assert metadata.has_complete_metadata() is True

    def test_has_complete_metadata_missing_title(self):
        """Test incomplete without title."""
        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            artist="Artist",
            duration_seconds=180.0
        )

        assert metadata.has_complete_metadata() is False

    def test_has_complete_metadata_missing_artist(self):
        """Test incomplete without artist."""
        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            title="Song",
            duration_seconds=180.0
        )

        assert metadata.has_complete_metadata() is False

    def test_has_complete_metadata_missing_duration(self):
        """Test incomplete without duration."""
        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            title="Song",
            artist="Artist"
        )

        assert metadata.has_complete_metadata() is False


class TestToDictSerialization:
    """Test dictionary serialization."""

    def test_to_dict_complete(self):
        """Test serialization with complete metadata."""
        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=5_000_000,
            mime_type="audio/mpeg",
            title="Song",
            artist="Artist",
            album="Album",
            duration_seconds=180.5,
            bitrate=192,
            sample_rate=44100
        )

        result = metadata.to_dict()

        assert result["filename"] == "test.mp3"
        assert result["size_bytes"] == 5_000_000
        assert result["size_mb"] == 4.77
        assert result["mime_type"] == "audio/mpeg"
        assert result["title"] == "Song"
        assert result["artist"] == "Artist"
        assert result["album"] == "Album"
        assert result["duration_seconds"] == 180.5
        assert result["duration_formatted"] == "03:00"
        assert result["bitrate"] == 192
        assert result["sample_rate"] == 44100
        assert result["file_extension"] == ".mp3"
        assert result["display_name"] == "Song"

    def test_to_dict_minimal(self):
        """Test serialization with minimal metadata."""
        metadata = FileMetadata.create_minimal("test.mp3", 1000, "audio/mpeg")

        result = metadata.to_dict()

        assert result["filename"] == "test.mp3"
        assert result["title"] is None
        assert result["artist"] is None
        assert result["album"] is None


class TestFileMetadataImmutability:
    """Test FileMetadata immutability."""

    def test_cannot_modify_filename(self):
        """Test cannot modify filename."""
        metadata = FileMetadata.create_minimal("test.mp3", 1000, "audio/mpeg")

        with pytest.raises(AttributeError):
            metadata.filename = "new.mp3"

    def test_cannot_modify_size(self):
        """Test cannot modify size."""
        metadata = FileMetadata.create_minimal("test.mp3", 1000, "audio/mpeg")

        with pytest.raises(AttributeError):
            metadata.size_bytes = 2000


class TestFileMetadataEdgeCases:
    """Test edge cases and special scenarios."""

    def test_very_large_file(self):
        """Test metadata for very large file."""
        metadata = FileMetadata.create_minimal("large.flac", 1_000_000_000, "audio/flac")

        # 1GB = 1000000000 bytes / (1024*1024) = 953.674...
        assert abs(metadata.size_mb - 953.67) < 0.01

    def test_zero_size_file(self):
        """Test metadata for zero size file."""
        metadata = FileMetadata.create_minimal("empty.mp3", 0, "audio/mpeg")

        assert metadata.size_bytes == 0
        assert metadata.size_mb == 0.0

    def test_unicode_filename(self):
        """Test metadata with unicode filename."""
        metadata = FileMetadata.create_minimal("日本語.mp3", 1000, "audio/mpeg")

        assert "日本語" in metadata.filename

    def test_very_long_duration(self):
        """Test metadata with very long duration."""
        metadata = FileMetadata(
            filename="audiobook.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            duration_seconds=36000.0  # 10 hours
        )

        assert metadata.duration_formatted == "600:00"

    def test_extra_attributes_empty_by_default(self):
        """Test extra_attributes defaults to empty dict."""
        metadata = FileMetadata.create_minimal("test.mp3", 1000, "audio/mpeg")

        assert metadata.extra_attributes == {}
        assert isinstance(metadata.extra_attributes, dict)
