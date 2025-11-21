"""
Comprehensive tests for AudioFile domain entity.

Tests cover:
- Entity construction and validation
- File existence checking
- File size validation
- Processing state management
- Playlist association
- Track info generation
- Integrity validation
"""

import pytest
from pathlib import Path
from app.src.domain.upload.entities.audio_file import AudioFile
from app.src.domain.upload.value_objects.file_metadata import FileMetadata


@pytest.fixture
def sample_metadata():
    """Create sample file metadata."""
    return FileMetadata(
        filename="test_song.mp3",
        size_bytes=5_000_000,
        mime_type="audio/mpeg",
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
        duration_seconds=180.0,
        bitrate=192
    )


class TestAudioFileConstruction:
    """Test audio file construction and validation."""

    def test_create_audio_file(self, sample_metadata, tmp_path):
        """Test creating audio file."""
        file_path = tmp_path / "test.mp3"
        file_path.write_bytes(b"fake audio data")

        audio_file = AudioFile(
            file_path=file_path,
            metadata=sample_metadata
        )

        assert audio_file.file_path == file_path
        assert audio_file.metadata == sample_metadata
        assert audio_file.playlist_id is None
        assert audio_file.is_processed is False
        assert audio_file.processing_error is None

    def test_create_with_playlist_id(self, sample_metadata, tmp_path):
        """Test creating audio file with playlist ID."""
        file_path = tmp_path / "test.mp3"
        file_path.write_text("data")

        audio_file = AudioFile(
            file_path=file_path,
            metadata=sample_metadata,
            playlist_id="pl-123"
        )

        assert audio_file.playlist_id == "pl-123"

    def test_create_without_file_path_raises_error(self, sample_metadata):
        """Test creating without file path raises error."""
        with pytest.raises(ValueError, match="File path is required"):
            AudioFile(file_path=None, metadata=sample_metadata)

    def test_create_without_metadata_raises_error(self, tmp_path):
        """Test creating without metadata raises error."""
        file_path = tmp_path / "test.mp3"

        with pytest.raises(ValueError, match="File metadata is required"):
            AudioFile(file_path=file_path, metadata=None)

    def test_create_with_non_audio_metadata_raises_error(self, tmp_path):
        """Test creating with non-audio metadata raises error."""
        non_audio_metadata = FileMetadata(
            filename="document.pdf",
            size_bytes=1000,
            mime_type="application/pdf"
        )

        with pytest.raises(ValueError, match="must be an audio file"):
            AudioFile(file_path=tmp_path / "file.pdf", metadata=non_audio_metadata)


class TestAudioFileProperties:
    """Test audio file properties."""

    def test_filename_property(self, sample_metadata, tmp_path):
        """Test filename property."""
        file_path = tmp_path / "my_song.mp3"
        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        assert audio_file.filename == "my_song.mp3"

    def test_file_exists_true(self, sample_metadata, tmp_path):
        """Test file_exists when file exists."""
        file_path = tmp_path / "exists.mp3"
        file_path.write_bytes(b"data")

        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        assert audio_file.file_exists is True

    def test_file_exists_false(self, sample_metadata, tmp_path):
        """Test file_exists when file doesn't exist."""
        file_path = tmp_path / "nonexistent.mp3"

        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        assert audio_file.file_exists is False

    def test_file_size_matches_metadata_true(self, tmp_path):
        """Test file size matches metadata."""
        file_path = tmp_path / "test.mp3"
        file_data = b"x" * 1000
        file_path.write_bytes(file_data)

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,  # Matches actual size
            mime_type="audio/mpeg"
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert audio_file.file_size_matches_metadata is True

    def test_file_size_matches_metadata_false(self, tmp_path):
        """Test file size doesn't match metadata."""
        file_path = tmp_path / "test.mp3"
        file_path.write_bytes(b"x" * 1000)

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=500,  # Doesn't match actual size
            mime_type="audio/mpeg"
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert audio_file.file_size_matches_metadata is False

    def test_file_size_matches_metadata_file_not_exists(self, sample_metadata, tmp_path):
        """Test file size check when file doesn't exist."""
        file_path = tmp_path / "nonexistent.mp3"

        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        assert audio_file.file_size_matches_metadata is False


class TestProcessingState:
    """Test processing state management."""

    def test_mark_processed(self, sample_metadata, tmp_path):
        """Test marking file as processed."""
        file_path = tmp_path / "test.mp3"
        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        audio_file.mark_processed()

        assert audio_file.is_processed is True
        assert audio_file.processing_error is None

    def test_mark_processing_failed(self, sample_metadata, tmp_path):
        """Test marking file as failed to process."""
        file_path = tmp_path / "test.mp3"
        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        audio_file.mark_processing_failed("Metadata extraction failed")

        assert audio_file.is_processed is False
        assert audio_file.processing_error == "Metadata extraction failed"

    def test_mark_processed_clears_error(self, sample_metadata, tmp_path):
        """Test marking processed clears previous error."""
        file_path = tmp_path / "test.mp3"
        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        audio_file.mark_processing_failed("Error")
        audio_file.mark_processed()

        assert audio_file.is_processed is True
        assert audio_file.processing_error is None


class TestPlaylistAssociation:
    """Test playlist association."""

    def test_set_playlist(self, sample_metadata, tmp_path):
        """Test setting playlist ID."""
        file_path = tmp_path / "test.mp3"
        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        audio_file.set_playlist("pl-123")

        assert audio_file.playlist_id == "pl-123"

    def test_set_playlist_empty_raises_error(self, sample_metadata, tmp_path):
        """Test setting empty playlist ID raises error."""
        file_path = tmp_path / "test.mp3"
        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        with pytest.raises(ValueError, match="Playlist ID cannot be empty"):
            audio_file.set_playlist("")

    def test_set_playlist_whitespace_raises_error(self, sample_metadata, tmp_path):
        """Test setting whitespace playlist ID raises error."""
        file_path = tmp_path / "test.mp3"
        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        with pytest.raises(ValueError, match="Playlist ID cannot be empty"):
            audio_file.set_playlist("   ")


class TestValidationForPlaylist:
    """Test validation for playlist addition."""

    def test_is_valid_for_playlist_true(self, tmp_path):
        """Test file is valid for playlist."""
        file_path = tmp_path / "test.mp3"
        file_path.write_bytes(b"x" * 1000)

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            title="Song",
            artist="Artist",
            duration_seconds=180.0
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert audio_file.is_valid_for_playlist() is True

    def test_is_valid_for_playlist_file_not_exists(self, sample_metadata, tmp_path):
        """Test invalid when file doesn't exist."""
        file_path = tmp_path / "nonexistent.mp3"

        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        assert audio_file.is_valid_for_playlist() is False

    def test_is_valid_for_playlist_size_mismatch(self, tmp_path):
        """Test invalid when file size doesn't match."""
        file_path = tmp_path / "test.mp3"
        file_path.write_bytes(b"x" * 1000)

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=500,  # Wrong size
            mime_type="audio/mpeg",
            title="Song",
            artist="Artist",
            duration_seconds=180.0
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert audio_file.is_valid_for_playlist() is False

    def test_is_valid_for_playlist_incomplete_metadata(self, tmp_path):
        """Test invalid when metadata is incomplete."""
        file_path = tmp_path / "test.mp3"
        file_path.write_bytes(b"x" * 1000)

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg"
            # Missing title, artist, duration
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert audio_file.is_valid_for_playlist() is False

    def test_is_valid_for_playlist_processing_error(self, tmp_path):
        """Test invalid when has processing error."""
        file_path = tmp_path / "test.mp3"
        file_path.write_bytes(b"x" * 1000)

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            title="Song",
            artist="Artist",
            duration_seconds=180.0
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)
        audio_file.mark_processing_failed("Error")

        assert audio_file.is_valid_for_playlist() is False


class TestGetTrackInfo:
    """Test track info generation."""

    def test_get_track_info_complete_metadata(self, tmp_path):
        """Test getting track info with complete metadata."""
        file_path = tmp_path / "test.mp3"

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=5_000_000,
            mime_type="audio/mpeg",
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            duration_seconds=180.5
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        track_info = audio_file.get_track_info()

        assert track_info["title"] == "Test Song"
        assert track_info["artist"] == "Test Artist"
        assert track_info["album"] == "Test Album"
        assert track_info["filename"] == "test.mp3"
        assert track_info["file_path"] == str(file_path)
        assert track_info["duration_ms"] == 180500
        assert track_info["size_bytes"] == 5_000_000

    def test_get_track_info_missing_title_uses_display_name(self, tmp_path):
        """Test uses display name when title is missing."""
        file_path = tmp_path / "my_song.mp3"

        metadata = FileMetadata(
            filename="my_song.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            title=None  # No title
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        track_info = audio_file.get_track_info()

        assert track_info["title"] == "my_song"  # Uses display_name

    def test_get_track_info_none_duration(self, tmp_path):
        """Test track info with None duration."""
        file_path = tmp_path / "test.mp3"

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            duration_seconds=None
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        track_info = audio_file.get_track_info()

        assert track_info["duration_ms"] is None


class TestValidateIntegrity:
    """Test file integrity validation."""

    def test_validate_integrity_valid(self, tmp_path):
        """Test integrity validation passes."""
        file_path = tmp_path / "test.mp3"
        file_path.write_bytes(b"x" * 1000)

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg"
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert audio_file.validate_integrity() is True

    def test_validate_integrity_file_missing(self, sample_metadata, tmp_path):
        """Test integrity validation fails when file missing."""
        file_path = tmp_path / "missing.mp3"

        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        assert audio_file.validate_integrity() is False

    def test_validate_integrity_size_mismatch(self, tmp_path):
        """Test integrity validation fails on size mismatch."""
        file_path = tmp_path / "test.mp3"
        file_path.write_bytes(b"x" * 1000)

        metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=500,  # Wrong
            mime_type="audio/mpeg"
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert audio_file.validate_integrity() is False


class TestStringRepresentation:
    """Test string representation."""

    def test_str_representation(self, sample_metadata, tmp_path):
        """Test string representation of audio file."""
        file_path = tmp_path / "my_song.mp3"

        audio_file = AudioFile(file_path=file_path, metadata=sample_metadata)

        str_repr = str(audio_file)

        assert "my_song.mp3" in str_repr
        assert "MB" in str_repr


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_very_large_file(self, tmp_path):
        """Test with very large file size in metadata."""
        file_path = tmp_path / "large.flac"

        metadata = FileMetadata(
            filename="large.flac",
            size_bytes=1_000_000_000,  # 1GB
            mime_type="audio/flac"
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert audio_file.metadata.size_bytes == 1_000_000_000

    def test_unicode_filename(self, tmp_path):
        """Test with unicode filename."""
        file_path = tmp_path / "日本語の曲.mp3"

        metadata = FileMetadata(
            filename="日本語の曲.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg"
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert "日本語" in audio_file.filename

    def test_special_characters_in_path(self, tmp_path):
        """Test with special characters in path."""
        file_path = tmp_path / "song's & friend's (remix).mp3"

        metadata = FileMetadata(
            filename="song's & friend's (remix).mp3",
            size_bytes=1000,
            mime_type="audio/mpeg"
        )

        audio_file = AudioFile(file_path=file_path, metadata=metadata)

        assert "remix" in audio_file.filename
