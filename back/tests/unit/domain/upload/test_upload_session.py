"""
Comprehensive tests for UploadSession domain entity.

Tests cover:
- Session creation and validation
- Progress tracking
- Chunk management
- State transitions
- Timeout handling
- Session completion
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.src.domain.upload.entities.upload_session import UploadSession, UploadStatus
from app.src.domain.upload.value_objects.file_chunk import FileChunk


class TestUploadSessionCreation:
    """Test UploadSession creation and validation."""

    def test_create_session(self):
        """Test creating a valid upload session."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=10,
            total_size_bytes=10_000
        )

        assert session.filename == "test.mp3"
        assert session.total_chunks == 10
        assert session.total_size_bytes == 10_000
        assert session.status == UploadStatus.CREATED
        assert len(session.received_chunks) == 0
        assert session.current_size_bytes == 0

    def test_create_session_with_playlist(self):
        """Test creating session with playlist ID."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=5,
            total_size_bytes=5000,
            playlist_id="pl-123"
        )

        assert session.playlist_id == "pl-123"

    def test_session_id_auto_generated(self):
        """Test session ID is automatically generated."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=1000
        )

        assert session.session_id is not None
        assert len(session.session_id) > 0

    def test_empty_filename_raises_error(self):
        """Test empty filename raises error."""
        with pytest.raises(ValueError, match="Filename is required"):
            UploadSession(filename="", total_chunks=1, total_size_bytes=1000)

    def test_zero_chunks_raises_error(self):
        """Test zero chunks raises error."""
        with pytest.raises(ValueError, match="Total chunks must be positive"):
            UploadSession(filename="test.mp3", total_chunks=0, total_size_bytes=1000)

    def test_zero_size_raises_error(self):
        """Test zero size raises error."""
        with pytest.raises(ValueError, match="Total size must be positive"):
            UploadSession(filename="test.mp3", total_chunks=1, total_size_bytes=0)


class TestSessionProgress:
    """Test session progress tracking."""

    def test_progress_percentage_empty(self):
        """Test progress percentage when no chunks received."""
        session = UploadSession(filename="test.mp3", total_chunks=10, total_size_bytes=10_000)

        assert session.progress_percentage == 0.0

    def test_progress_percentage_partial(self):
        """Test progress percentage with partial upload."""
        session = UploadSession(filename="test.mp3", total_chunks=10, total_size_bytes=10_000)
        session.received_chunks = {0, 1, 2}

        assert session.progress_percentage == 30.0

    def test_progress_percentage_complete(self):
        """Test progress percentage when complete."""
        session = UploadSession(filename="test.mp3", total_chunks=5, total_size_bytes=5000)
        session.received_chunks = {0, 1, 2, 3, 4}

        assert session.progress_percentage == 100.0

    def test_size_progress_percentage(self):
        """Test size-based progress."""
        session = UploadSession(filename="test.mp3", total_chunks=10, total_size_bytes=10_000)
        session.current_size_bytes = 5000

        assert session.size_progress_percentage == 50.0


class TestChunkManagement:
    """Test chunk management operations."""

    def test_add_chunk(self):
        """Test adding a chunk."""
        session = UploadSession(filename="test.mp3", total_chunks=3, total_size_bytes=3000)
        chunk = FileChunk.create(index=0, data=b"x" * 1000)

        session.add_chunk(chunk)

        assert 0 in session.received_chunks
        assert session.current_size_bytes == 1000
        assert session.status == UploadStatus.IN_PROGRESS

    def test_add_multiple_chunks(self):
        """Test adding multiple chunks."""
        session = UploadSession(filename="test.mp3", total_chunks=3, total_size_bytes=3000)

        for i in range(3):
            chunk = FileChunk.create(index=i, data=b"x" * 1000)
            session.add_chunk(chunk)

        assert len(session.received_chunks) == 3
        assert session.current_size_bytes == 3000

    def test_add_chunk_out_of_range_raises_error(self):
        """Test adding chunk with invalid index raises error."""
        session = UploadSession(filename="test.mp3", total_chunks=5, total_size_bytes=5000)
        chunk = FileChunk.create(index=10, data=b"test")

        with pytest.raises(ValueError, match="out of range"):
            session.add_chunk(chunk)

    def test_add_duplicate_chunk_raises_error(self):
        """Test adding duplicate chunk raises error."""
        session = UploadSession(filename="test.mp3", total_chunks=5, total_size_bytes=5000)
        chunk = FileChunk.create(index=0, data=b"test")

        session.add_chunk(chunk)

        with pytest.raises(ValueError, match="already received"):
            session.add_chunk(chunk)

    def test_add_chunk_to_inactive_session_raises_error(self):
        """Test adding chunk to inactive session raises error."""
        session = UploadSession(filename="test.mp3", total_chunks=2, total_size_bytes=2000)
        session.status = UploadStatus.COMPLETED

        chunk = FileChunk.create(index=0, data=b"test")

        with pytest.raises(ValueError, match="Cannot add chunk to inactive session"):
            session.add_chunk(chunk)


class TestSessionCompletion:
    """Test session completion logic."""

    def test_is_complete_false(self):
        """Test is_complete when chunks missing."""
        session = UploadSession(filename="test.mp3", total_chunks=5, total_size_bytes=5000)
        session.received_chunks = {0, 1, 2}

        assert session.is_complete() is False

    def test_is_complete_true(self):
        """Test is_complete when all chunks received."""
        session = UploadSession(filename="test.mp3", total_chunks=3, total_size_bytes=3000)
        session.received_chunks = {0, 1, 2}

        assert session.is_complete() is True

    def test_mark_completed(self):
        """Test marking session as completed."""
        session = UploadSession(filename="test.mp3", total_chunks=2, total_size_bytes=2000)
        session.received_chunks = {0, 1}

        session.mark_completed()

        assert session.status == UploadStatus.COMPLETED
        assert session.completed_at is not None

    def test_mark_completed_incomplete_raises_error(self):
        """Test marking incomplete session raises error."""
        session = UploadSession(filename="test.mp3", total_chunks=5, total_size_bytes=5000)
        session.received_chunks = {0, 1}

        with pytest.raises(ValueError, match="Cannot mark incomplete"):
            session.mark_completed()

    def test_auto_complete_on_last_chunk(self):
        """Test session auto-completes when last chunk added."""
        session = UploadSession(filename="test.mp3", total_chunks=2, total_size_bytes=2000)

        chunk1 = FileChunk.create(index=0, data=b"x" * 1000)
        chunk2 = FileChunk.create(index=1, data=b"x" * 1000)

        session.add_chunk(chunk1)
        assert session.status == UploadStatus.IN_PROGRESS

        session.add_chunk(chunk2)
        assert session.status == UploadStatus.COMPLETED


class TestSessionState:
    """Test session state management."""

    def test_is_active_created(self):
        """Test session is active when created."""
        session = UploadSession(filename="test.mp3", total_chunks=1, total_size_bytes=1000)

        assert session.is_active() is True

    def test_is_active_in_progress(self):
        """Test session is active when in progress."""
        session = UploadSession(filename="test.mp3", total_chunks=2, total_size_bytes=2000)
        session.status = UploadStatus.IN_PROGRESS

        assert session.is_active() is True

    def test_is_active_completed(self):
        """Test session not active when completed."""
        session = UploadSession(filename="test.mp3", total_chunks=1, total_size_bytes=1000)
        session.status = UploadStatus.COMPLETED

        assert session.is_active() is False

    def test_mark_failed(self):
        """Test marking session as failed."""
        session = UploadSession(filename="test.mp3", total_chunks=1, total_size_bytes=1000)

        session.mark_failed("Upload error")

        assert session.status == UploadStatus.FAILED
        assert session.error_message == "Upload error"
        assert session.completed_at is not None

    def test_mark_cancelled(self):
        """Test marking session as cancelled."""
        session = UploadSession(filename="test.mp3", total_chunks=1, total_size_bytes=1000)

        session.mark_cancelled()

        assert session.status == UploadStatus.CANCELLED
        assert session.completed_at is not None

    def test_mark_expired(self):
        """Test marking session as expired."""
        session = UploadSession(filename="test.mp3", total_chunks=1, total_size_bytes=1000)

        session.mark_expired()

        assert session.status == UploadStatus.EXPIRED
        assert session.completed_at is not None


class TestSessionTimeout:
    """Test session timeout handling."""

    def test_timeout_at_property(self):
        """Test timeout calculation."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=1000,
            timeout_seconds=3600
        )

        timeout_at = session.timeout_at
        expected = session.created_at + timedelta(seconds=3600)

        assert abs((timeout_at - expected).total_seconds()) < 1

    def test_is_expired_false(self):
        """Test session not expired when within timeout."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=1000,
            timeout_seconds=3600
        )

        assert session.is_expired() is False

    def test_is_expired_true(self):
        """Test session expired when past timeout."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=1000,
            timeout_seconds=1
        )

        # Simulate old session
        old_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        object.__setattr__(session, 'created_at', old_time)

        assert session.is_expired() is True

    def test_get_remaining_seconds(self):
        """Test getting remaining timeout seconds."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=1000,
            timeout_seconds=3600
        )

        remaining = session.get_remaining_seconds()

        assert remaining > 3500  # Should be close to 3600

    def test_get_remaining_seconds_expired(self):
        """Test remaining seconds is zero when expired."""
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=1000,
            timeout_seconds=1
        )

        old_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        object.__setattr__(session, 'created_at', old_time)

        assert session.get_remaining_seconds() == 0


class TestSessionHelpers:
    """Test session helper methods."""

    def test_get_missing_chunks(self):
        """Test getting missing chunks."""
        session = UploadSession(filename="test.mp3", total_chunks=5, total_size_bytes=5000)
        session.received_chunks = {0, 2, 4}

        missing = session.get_missing_chunks()

        assert missing == {1, 3}

    def test_get_missing_chunks_none(self):
        """Test no missing chunks when complete."""
        session = UploadSession(filename="test.mp3", total_chunks=3, total_size_bytes=3000)
        session.received_chunks = {0, 1, 2}

        missing = session.get_missing_chunks()

        assert len(missing) == 0

    def test_validate_chunk_size_consistency_true(self):
        """Test chunk size validation passes."""
        session = UploadSession(filename="test.mp3", total_chunks=2, total_size_bytes=2000)
        session.current_size_bytes = 1500

        assert session.validate_chunk_size_consistency(1500) is True

    def test_validate_chunk_size_consistency_false(self):
        """Test chunk size validation fails."""
        session = UploadSession(filename="test.mp3", total_chunks=2, total_size_bytes=2000)
        session.current_size_bytes = 1500

        assert session.validate_chunk_size_consistency(2000) is False


class TestSessionSerialization:
    """Test session serialization."""

    def test_to_dict(self):
        """Test converting session to dictionary."""
        session = UploadSession(
            filename="test.mp3",
            playlist_id="pl-123",
            total_chunks=5,
            total_size_bytes=5000
        )
        session.received_chunks = {0, 1}
        session.current_size_bytes = 2000

        result = session.to_dict()

        assert result["session_id"] == session.session_id
        assert result["filename"] == "test.mp3"
        assert result["playlist_id"] == "pl-123"
        assert result["status"] == "created"
        assert result["progress_percentage"] == 40.0
        assert result["size_progress_percentage"] == 40.0
        assert result["total_chunks"] == 5
        assert result["received_chunks"] == 2
        assert result["missing_chunks"] == 3
        assert result["total_size_bytes"] == 5000
        assert result["current_size_bytes"] == 2000

    def test_to_dict_with_metadata(self):
        """Test serialization includes metadata."""
        from app.src.domain.upload.value_objects.file_metadata import FileMetadata

        metadata = FileMetadata.create_minimal("test.mp3", 5000, "audio/mpeg")
        session = UploadSession(filename="test.mp3", total_chunks=1, total_size_bytes=1000)
        session.set_metadata(metadata)

        result = session.to_dict()

        assert result["file_metadata"] is not None
        assert result["file_metadata"]["filename"] == "test.mp3"


class TestSessionEdgeCases:
    """Test edge cases and special scenarios."""

    def test_single_chunk_session(self):
        """Test session with single chunk."""
        session = UploadSession(filename="small.mp3", total_chunks=1, total_size_bytes=1000)

        chunk = FileChunk.create(index=0, data=b"x" * 1000)
        session.add_chunk(chunk)

        assert session.is_complete() is True
        assert session.status == UploadStatus.COMPLETED

    def test_large_chunk_count(self):
        """Test session with many chunks."""
        session = UploadSession(filename="large.flac", total_chunks=1000, total_size_bytes=1_000_000)

        assert session.total_chunks == 1000
        assert len(session.get_missing_chunks()) == 1000

    def test_unicode_filename(self):
        """Test session with unicode filename."""
        session = UploadSession(filename="日本語.mp3", total_chunks=1, total_size_bytes=1000)

        assert "日本語" in session.filename
