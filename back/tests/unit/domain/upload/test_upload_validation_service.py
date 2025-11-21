"""
Comprehensive tests for UploadValidationService domain service.

Tests cover:
- Upload request validation
- Chunk validation
- Session completion validation
- Audio metadata validation
- Filename validation
- Business rules
- Edge cases and error handling
"""

import pytest
from app.src.domain.upload.services.upload_validation_service import UploadValidationService
from app.src.domain.upload.entities.upload_session import UploadSession, UploadStatus
from app.src.domain.upload.value_objects.file_chunk import FileChunk
from app.src.domain.upload.value_objects.file_metadata import FileMetadata


@pytest.fixture
def service():
    """Create upload validation service with default settings."""
    return UploadValidationService()


@pytest.fixture
def custom_service():
    """Create upload validation service with custom settings."""
    return UploadValidationService(
        max_file_size=50 * 1024 * 1024,  # 50MB
        max_chunk_size=512 * 1024,  # 512KB
        allowed_extensions={"mp3", "flac"},
        min_audio_duration=2.0
    )


class TestUploadRequestValidation:
    """Test upload request validation."""

    def test_valid_upload_request(self, service):
        """Test validation of valid upload request."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=5_000_000,
            total_chunks=10,
            playlist_id="playlist-123"
        )

        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["filename"] == "song.mp3"
        assert result["total_size"] == 5_000_000
        assert result["total_chunks"] == 10

    def test_empty_filename(self, service):
        """Test validation fails for empty filename."""
        result = service.validate_upload_request(
            filename="",
            total_size=1000,
            total_chunks=1
        )

        assert result["valid"] is False
        assert any("filename" in err.lower() for err in result["errors"])

    def test_whitespace_filename(self, service):
        """Test validation fails for whitespace-only filename."""
        result = service.validate_upload_request(
            filename="   ",
            total_size=1000,
            total_chunks=1
        )

        assert result["valid"] is False

    def test_zero_file_size(self, service):
        """Test validation fails for zero file size."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=0,
            total_chunks=1
        )

        assert result["valid"] is False
        assert any("size must be positive" in err.lower() for err in result["errors"])

    def test_negative_file_size(self, service):
        """Test validation fails for negative file size."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=-1000,
            total_chunks=1
        )

        assert result["valid"] is False

    def test_file_size_exceeds_maximum(self, service):
        """Test validation fails when file size exceeds maximum."""
        result = service.validate_upload_request(
            filename="huge.mp3",
            total_size=200 * 1024 * 1024,  # 200MB
            total_chunks=100
        )

        assert result["valid"] is False
        assert any("exceeds maximum" in err.lower() for err in result["errors"])

    def test_zero_chunks(self, service):
        """Test validation fails for zero chunks."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=1000,
            total_chunks=0
        )

        assert result["valid"] is False
        assert any("chunk count must be positive" in err.lower() for err in result["errors"])

    def test_negative_chunks(self, service):
        """Test validation fails for negative chunks."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=1000,
            total_chunks=-1
        )

        assert result["valid"] is False

    def test_too_many_chunks(self, service):
        """Test validation fails for excessive chunks."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=1000000,
            total_chunks=10001
        )

        assert result["valid"] is False
        assert any("too many chunks" in err.lower() for err in result["errors"])

    def test_chunk_size_exceeds_maximum(self, service):
        """Test validation fails when average chunk size too large."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=10 * 1024 * 1024,  # 10MB
            total_chunks=5  # Average chunk = 2MB
        )

        assert result["valid"] is False
        assert any("average chunk size" in err.lower() for err in result["errors"])

    def test_unsupported_file_extension(self, service):
        """Test validation fails for unsupported extension."""
        result = service.validate_upload_request(
            filename="document.pdf",
            total_size=1000,
            total_chunks=1
        )

        assert result["valid"] is False
        assert any("not allowed" in err.lower() for err in result["errors"])

    def test_no_file_extension(self, service):
        """Test validation fails for missing extension."""
        result = service.validate_upload_request(
            filename="noextension",
            total_size=1000,
            total_chunks=1
        )

        assert result["valid"] is False
        assert any("must have an extension" in err.lower() for err in result["errors"])

    def test_empty_playlist_id(self, service):
        """Test validation fails for empty playlist ID when provided."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=1000,
            total_chunks=1,
            playlist_id=""
        )

        assert result["valid"] is False
        assert any("playlist id" in err.lower() for err in result["errors"])

    def test_valid_playlist_id_none(self, service):
        """Test validation passes when playlist ID is None."""
        result = service.validate_upload_request(
            filename="song.mp3",
            total_size=1000,
            total_chunks=1,
            playlist_id=None
        )

        assert result["valid"] is True


class TestChunkValidation:
    """Test file chunk validation."""

    @pytest.fixture
    def session(self):
        """Create a sample upload session."""
        return UploadSession(
            filename="test.mp3",
            total_chunks=10,
            total_size_bytes=10_000,
            status=UploadStatus.IN_PROGRESS
        )

    def test_valid_chunk(self, service, session):
        """Test validation of valid chunk."""
        chunk = FileChunk.create(index=0, data=b"test data")

        result = service.validate_chunk(chunk, session)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_negative_chunk_index(self, service, session):
        """Test validation fails for negative chunk index."""
        # Chunk creation itself should raise ValueError for negative index
        with pytest.raises(ValueError, match="Chunk index cannot be negative"):
            FileChunk.create(index=-1, data=b"test")

    def test_chunk_index_exceeds_total(self, service, session):
        """Test validation fails when chunk index exceeds total."""
        chunk = FileChunk.create(index=15, data=b"test")

        result = service.validate_chunk(chunk, session)

        assert result["valid"] is False
        assert any("exceeds session total chunks" in err.lower() for err in result["errors"])

    def test_chunk_size_exceeds_maximum(self, service, session):
        """Test validation fails for oversized chunk."""
        large_data = b"x" * (2 * 1024 * 1024)  # 2MB
        chunk = FileChunk.create(index=0, data=large_data)

        result = service.validate_chunk(chunk, session)

        assert result["valid"] is False
        assert any("exceeds maximum" in err.lower() for err in result["errors"])

    def test_duplicate_chunk(self, service, session):
        """Test validation warns about duplicate chunk."""
        chunk = FileChunk.create(index=5, data=b"test")
        session.received_chunks.add(5)

        result = service.validate_chunk(chunk, session)

        assert result["valid"] is True  # Valid but with warning
        assert len(result["warnings"]) > 0
        assert any("already received" in warn.lower() for warn in result["warnings"])

    def test_chunk_for_inactive_session(self, service):
        """Test validation fails for inactive session."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=10,
            total_size_bytes=10_000,
            status=UploadStatus.COMPLETED
        )
        chunk = FileChunk.create(index=0, data=b"test")

        result = service.validate_chunk(chunk, session)

        assert result["valid"] is False
        assert any("not active" in err.lower() for err in result["errors"])

    def test_chunk_would_exceed_total_size(self, service, session):
        """Test validation fails when chunk would exceed total size."""
        session.current_size_bytes = 9_500
        large_chunk = FileChunk.create(index=0, data=b"x" * 1000)

        result = service.validate_chunk(large_chunk, session)

        assert result["valid"] is False
        assert any("exceed total file size" in err.lower() for err in result["errors"])


class TestSessionCompletionValidation:
    """Test upload session completion validation."""

    def test_valid_complete_session(self, service):
        """Test validation of complete session."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=3,
            total_size_bytes=3000
        )
        session.received_chunks = {0, 1, 2}
        session.current_size_bytes = 3000

        result = service.validate_session_completion(session)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_missing_chunks(self, service):
        """Test validation fails when chunks are missing."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=5,
            total_size_bytes=5000
        )
        session.received_chunks = {0, 1, 3}  # Missing 2 and 4

        result = service.validate_session_completion(session)

        assert result["valid"] is False
        assert any("missing" in err.lower() for err in result["errors"])
        assert any("2" in str(err) for err in result["errors"])

    def test_size_mismatch(self, service):
        """Test validation fails for size mismatch."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=3,
            total_size_bytes=3000
        )
        session.received_chunks = {0, 1, 2}
        session.current_size_bytes = 2500  # Mismatch

        result = service.validate_session_completion(session)

        assert result["valid"] is False
        assert any("size mismatch" in err.lower() for err in result["errors"])

    def test_expired_session(self, service):
        """Test validation fails for expired session."""
        from datetime import datetime, timedelta, timezone
        session = UploadSession(
            filename="test.mp3",
            total_chunks=3,
            total_size_bytes=3000,
            timeout_seconds=1
        )
        # Set created_at to past
        object.__setattr__(session, "created_at", datetime.now(timezone.utc) - timedelta(seconds=10))
        session.received_chunks = {0, 1, 2}
        session.current_size_bytes = 3000

        result = service.validate_session_completion(session)

        assert result["valid"] is False
        assert any("expired" in err.lower() for err in result["errors"])


class TestAudioMetadataValidation:
    """Test audio metadata validation."""

    def test_valid_audio_metadata(self, service):
        """Test validation of valid audio metadata."""
        metadata = FileMetadata(
            filename="song.mp3",
            size_bytes=5_000_000,
            mime_type="audio/mpeg",
            title="Test Song",
            artist="Test Artist",
            duration_seconds=180.0,
            bitrate=192
        )

        result = service.validate_audio_metadata(metadata)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_non_audio_mime_type(self, service):
        """Test validation fails for non-audio MIME type."""
        metadata = FileMetadata(
            filename="document.pdf",
            size_bytes=1000,
            mime_type="application/pdf"
        )

        result = service.validate_audio_metadata(metadata)

        assert result["valid"] is False
        assert any("not an audio format" in err.lower() for err in result["errors"])

    def test_unsupported_format(self, custom_service):
        """Test validation fails for unsupported format."""
        metadata = FileMetadata(
            filename="song.ogg",
            size_bytes=1000,
            mime_type="audio/ogg"
        )

        result = custom_service.validate_audio_metadata(metadata)

        assert result["valid"] is False
        assert any("not supported" in err.lower() for err in result["errors"])

    def test_duration_too_short(self, service):
        """Test validation fails for too short duration."""
        metadata = FileMetadata(
            filename="short.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            duration_seconds=0.5  # Too short
        )

        result = service.validate_audio_metadata(metadata)

        assert result["valid"] is False
        assert any("too short" in err.lower() for err in result["errors"])

    def test_missing_duration_warning(self, service):
        """Test warning when duration is missing."""
        metadata = FileMetadata(
            filename="song.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            duration_seconds=None
        )

        result = service.validate_audio_metadata(metadata)

        assert result["valid"] is True  # Still valid
        assert len(result["warnings"]) > 0
        assert any("duration could not be determined" in warn.lower() for warn in result["warnings"])

    def test_missing_title_warning(self, service):
        """Test warning when title is missing."""
        metadata = FileMetadata(
            filename="song.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            title=None
        )

        result = service.validate_audio_metadata(metadata)

        assert len(result["warnings"]) > 0
        assert any("title is missing" in warn.lower() for warn in result["warnings"])

    def test_missing_artist_warning(self, service):
        """Test warning when artist is missing."""
        metadata = FileMetadata(
            filename="song.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            artist=None
        )

        result = service.validate_audio_metadata(metadata)

        assert len(result["warnings"]) > 0
        assert any("artist is missing" in warn.lower() for warn in result["warnings"])

    def test_low_bitrate_warning(self, service):
        """Test warning for very low bitrate."""
        metadata = FileMetadata(
            filename="song.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            bitrate=32  # Very low
        )

        result = service.validate_audio_metadata(metadata)

        assert len(result["warnings"]) > 0
        assert any("very low" in warn.lower() for warn in result["warnings"])

    def test_high_bitrate_warning(self, service):
        """Test warning for unusually high bitrate."""
        metadata = FileMetadata(
            filename="song.flac",
            size_bytes=50_000_000,
            mime_type="audio/flac",
            bitrate=500  # Very high
        )

        result = service.validate_audio_metadata(metadata)

        assert len(result["warnings"]) > 0
        assert any("unusually high" in warn.lower() for warn in result["warnings"])


class TestFilenameValidation:
    """Test filename validation."""

    def test_valid_filename(self, service):
        """Test validation of valid filename."""
        result = service._validate_filename("normal_song.mp3")

        assert len(result["errors"]) == 0

    def test_filename_no_extension(self, service):
        """Test validation fails for filename without extension."""
        result = service._validate_filename("noextension")

        assert len(result["errors"]) > 0
        assert any("must have an extension" in err.lower() for err in result["errors"])

    def test_filename_unsupported_extension(self, service):
        """Test validation fails for unsupported extension."""
        result = service._validate_filename("document.txt")

        assert len(result["errors"]) > 0
        assert any("not allowed" in err.lower() for err in result["errors"])

    def test_filename_too_long(self, service):
        """Test validation fails for filename over 255 characters."""
        long_name = "a" * 256  # More than 255
        result = service._validate_filename(long_name)

        assert len(result["errors"]) > 0
        assert any("too long" in err.lower() for err in result["errors"])

    def test_filename_problematic_characters(self, service):
        """Test warning for problematic characters."""
        result = service._validate_filename('song:with|bad*chars.mp3')

        assert len(result["warnings"]) > 0
        assert any("problematic characters" in warn.lower() for warn in result["warnings"])

    def test_filename_reserved_windows_names(self, service):
        """Test validation fails for Windows reserved names."""
        reserved_names = ["CON.mp3", "PRN.mp3", "AUX.mp3", "NUL.mp3"]

        for name in reserved_names:
            result = service._validate_filename(name)
            assert len(result["errors"]) > 0
            assert any("reserved filename" in err.lower() for err in result["errors"])

    def test_filename_case_insensitive_extension(self, service):
        """Test extension validation is case-insensitive."""
        result = service._validate_filename("song.MP3")

        assert len(result["errors"]) == 0

    def test_filename_multiple_dots(self, service):
        """Test filename with multiple dots."""
        result = service._validate_filename("my.awesome.song.mp3")

        assert len(result["errors"]) == 0


class TestCustomConfiguration:
    """Test custom service configuration."""

    def test_custom_max_file_size(self, custom_service):
        """Test custom maximum file size."""
        result = custom_service.validate_upload_request(
            filename="large.mp3",
            total_size=75 * 1024 * 1024,  # 75MB (exceeds custom 50MB)
            total_chunks=100
        )

        assert result["valid"] is False

    def test_custom_allowed_extensions(self, custom_service):
        """Test custom allowed extensions."""
        # WAV not in custom allowed list
        result = custom_service.validate_upload_request(
            filename="song.wav",
            total_size=1000,
            total_chunks=1
        )

        assert result["valid"] is False

        # MP3 is in custom allowed list
        result = custom_service.validate_upload_request(
            filename="song.mp3",
            total_size=1000,
            total_chunks=1
        )

        assert result["valid"] is True

    def test_custom_min_duration(self, custom_service):
        """Test custom minimum audio duration."""
        metadata = FileMetadata(
            filename="short.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            duration_seconds=1.5  # Less than custom 2.0 minimum
        )

        result = custom_service.validate_audio_metadata(metadata)

        assert result["valid"] is False
        assert any("too short" in err.lower() for err in result["errors"])


class TestEdgeCases:
    """Test edge cases and corner scenarios."""

    def test_very_small_file(self, service):
        """Test validation of very small file."""
        result = service.validate_upload_request(
            filename="tiny.mp3",
            total_size=1,
            total_chunks=1
        )

        assert result["valid"] is True

    def test_exactly_max_file_size(self, service):
        """Test file exactly at maximum size."""
        result = service.validate_upload_request(
            filename="max.mp3",
            total_size=100 * 1024 * 1024,  # Exactly 100MB
            total_chunks=100
        )

        assert result["valid"] is True

    def test_unicode_filename(self, service):
        """Test filename with unicode characters."""
        result = service.validate_upload_request(
            filename="日本語の曲.mp3",
            total_size=1000,
            total_chunks=1
        )

        assert result["valid"] is True

    def test_all_supported_formats(self, service):
        """Test all default supported audio formats."""
        formats = ["mp3", "wav", "flac", "ogg", "m4a", "aac"]

        for fmt in formats:
            result = service.validate_upload_request(
                filename=f"song.{fmt}",
                total_size=1000,
                total_chunks=1
            )
            assert result["valid"] is True, f"Format {fmt} should be valid"

    def test_zero_duration_audio(self, service):
        """Test audio with zero duration."""
        metadata = FileMetadata(
            filename="zero.mp3",
            size_bytes=1000,
            mime_type="audio/mpeg",
            duration_seconds=0.0
        )

        result = service.validate_audio_metadata(metadata)

        assert result["valid"] is False

    def test_very_long_audio(self, service):
        """Test very long audio file (e.g., audiobook)."""
        metadata = FileMetadata(
            filename="audiobook.mp3",
            size_bytes=500_000_000,
            mime_type="audio/mpeg",
            duration_seconds=36000.0  # 10 hours
        )

        # Should be valid as long as it meets minimum duration
        result = service.validate_audio_metadata(metadata)

        # May have size warnings but should be valid
        assert result["valid"] is True
