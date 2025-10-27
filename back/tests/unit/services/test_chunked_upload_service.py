# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for ChunkedUploadService

Comprehensive tests for the chunked upload service including session management,
chunk processing, file assembly, and cleanup operations.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, mock_open
from pathlib import Path
from datetime import datetime, timedelta
import uuid

from app.src.services.chunked_upload_service import ChunkedUploadService
from app.src.infrastructure.error_handling.unified_error_handler import InvalidFileError


class TestChunkedUploadService:
    """Test suite for ChunkedUploadService."""

    @pytest.fixture
    def mock_config(self):
        """Mock application config."""
        config = Mock()
        config.upload_folder = "/tmp/test_uploads"
        config.upload_max_size = 100 * 1024 * 1024  # 100MB
        config.upload_allowed_extensions = ["mp3", "wav", "flac", "m4a"]
        return config

    @pytest.fixture
    def mock_upload_service(self):
        """Mock upload service."""
        service = Mock()
        service.upload_folder = "/tmp/test_uploads"
        service.extract_metadata = Mock(return_value={
            "title": "Test Track",
            "artist": "Test Artist",
            "duration": 180
        })
        return service

    @pytest.fixture
    def chunked_upload_service(self, mock_config, mock_upload_service):
        """Create ChunkedUploadService instance."""
        with patch('pathlib.Path.mkdir'):
            service = ChunkedUploadService(mock_config, mock_upload_service)
            return service

    # ================================================================================
    # Test create_session()
    # ================================================================================

    def test_create_session_success(self, chunked_upload_service):
        """Test successful upload session creation."""
        # Arrange
        filename = "test_audio.mp3"
        total_chunks = 10
        total_size = 50 * 1024 * 1024  # 50MB
        playlist_id = "test-playlist"

        with patch('pathlib.Path.mkdir'):
            # Act
            session_id = chunked_upload_service.create_session(
                filename, total_chunks, total_size, playlist_id
            )

            # Assert
            assert session_id is not None
            assert session_id in chunked_upload_service.active_uploads
            session = chunked_upload_service.active_uploads[session_id]
            assert session["filename"] == filename
            assert session["total_chunks"] == total_chunks
            assert session["total_size"] == total_size
            assert session["playlist_id"] == playlist_id
            assert session["complete"] is False
            assert len(session["received_chunks"]) == 0

    def test_create_session_invalid_file_type(self, chunked_upload_service):
        """Test session creation with invalid file type."""
        # Arrange
        filename = "test_file.txt"  # Not an allowed audio type
        total_chunks = 5
        total_size = 10 * 1024 * 1024
        playlist_id = "test-playlist"

        # Act & Assert
        with pytest.raises(InvalidFileError) as exc_info:
            chunked_upload_service.create_session(
                filename, total_chunks, total_size, playlist_id
            )
        assert "not allowed" in str(exc_info.value).lower()

    def test_create_session_file_too_large(self, chunked_upload_service):
        """Test session creation with file size exceeding limit."""
        # Arrange
        filename = "huge_audio.mp3"
        total_chunks = 1000
        total_size = 200 * 1024 * 1024  # 200MB (exceeds 100MB limit)
        playlist_id = "test-playlist"

        # Act & Assert
        with pytest.raises(InvalidFileError) as exc_info:
            chunked_upload_service.create_session(
                filename, total_chunks, total_size, playlist_id
            )
        assert "too large" in str(exc_info.value).lower()

    def test_create_session_generates_unique_ids(self, chunked_upload_service):
        """Test that create_session generates unique session IDs."""
        # Arrange
        filename = "test_audio.mp3"
        total_chunks = 5
        total_size = 10 * 1024 * 1024
        playlist_id = "test-playlist"

        with patch('pathlib.Path.mkdir'):
            # Act
            session_id_1 = chunked_upload_service.create_session(
                filename, total_chunks, total_size, playlist_id
            )
            session_id_2 = chunked_upload_service.create_session(
                filename, total_chunks, total_size, playlist_id
            )

            # Assert
            assert session_id_1 != session_id_2
            assert session_id_1 in chunked_upload_service.active_uploads
            assert session_id_2 in chunked_upload_service.active_uploads

    # ================================================================================
    # Test process_chunk()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_process_chunk_success(self, chunked_upload_service):
        """Test successful chunk processing."""
        # Arrange
        session_id = str(uuid.uuid4())
        session_dir = Path("/tmp/test_session")
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 5,
            "total_size": 10 * 1024 * 1024,
            "received_chunks": set(),
            "current_size": 0,
            "session_dir": session_dir,
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now(),
        }
        chunk_index = 0
        chunk_data = b"test chunk data"
        chunk_size = len(chunk_data)

        with patch("builtins.open", mock_open()) as mock_file:
            # Act
            result = await chunked_upload_service.process_chunk(
                session_id, chunk_index, chunk_data, chunk_size
            )

            # Assert
            assert result["status"] == "success"
            assert result["chunk_index"] == chunk_index
            assert result["progress"] == 20.0  # 1/5 = 20%
            assert result["complete"] is False
            assert chunk_index in chunked_upload_service.active_uploads[session_id]["received_chunks"]
            mock_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_chunk_session_not_found(self, chunked_upload_service):
        """Test chunk processing for non-existent session."""
        # Arrange
        session_id = "non-existent-session"
        chunk_index = 0
        chunk_data = b"test data"
        chunk_size = len(chunk_data)

        # Act
        result = await chunked_upload_service.process_chunk(
            session_id, chunk_index, chunk_data, chunk_size
        )

        # Assert (decorator transforms exception to error response)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_chunk_duplicate(self, chunked_upload_service):
        """Test processing of duplicate chunk."""
        # Arrange
        session_id = str(uuid.uuid4())
        session_dir = Path("/tmp/test_session")
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 5,
            "total_size": 10 * 1024 * 1024,
            "received_chunks": {0},  # Chunk 0 already received
            "current_size": 100,
            "session_dir": session_dir,
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now(),
        }
        chunk_index = 0
        chunk_data = b"test chunk data"
        chunk_size = len(chunk_data)

        # Act
        result = await chunked_upload_service.process_chunk(
            session_id, chunk_index, chunk_data, chunk_size
        )

        # Assert
        assert result["status"] == "duplicate"
        assert "already received" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_chunk_exceeds_max_size(self, chunked_upload_service):
        """Test chunk processing when it would exceed max file size."""
        # Arrange
        session_id = str(uuid.uuid4())
        session_dir = Path("/tmp/test_session")
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 5,
            "total_size": 10 * 1024 * 1024,
            "received_chunks": set(),
            "current_size": 99 * 1024 * 1024,  # Already at 99MB
            "session_dir": session_dir,
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now(),
        }
        chunk_index = 0
        chunk_data = b"x" * (2 * 1024 * 1024)  # 2MB chunk would exceed 100MB limit
        chunk_size = len(chunk_data)

        # Act
        result = await chunked_upload_service.process_chunk(
            session_id, chunk_index, chunk_data, chunk_size
        )

        # Assert (decorator transforms exception to error response)
        assert result["status"] == "error"
        assert "too large" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_process_chunk_marks_complete_when_all_received(self, chunked_upload_service):
        """Test that session is marked complete when all chunks are received."""
        # Arrange
        session_id = str(uuid.uuid4())
        session_dir = Path("/tmp/test_session")
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 3,
            "total_size": 10 * 1024 * 1024,
            "received_chunks": {0, 1},  # 2/3 chunks already received
            "current_size": 1000,
            "session_dir": session_dir,
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now(),
        }
        chunk_index = 2  # Last chunk
        chunk_data = b"final chunk"
        chunk_size = len(chunk_data)

        with patch("builtins.open", mock_open()):
            # Act
            result = await chunked_upload_service.process_chunk(
                session_id, chunk_index, chunk_data, chunk_size
            )

            # Assert
            assert result["status"] == "success"
            assert result["complete"] is True
            assert result["progress"] == 100.0
            assert chunked_upload_service.active_uploads[session_id]["complete"] is True

    # ================================================================================
    # Test finalize_upload()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_finalize_upload_success(self, chunked_upload_service, mock_upload_service):
        """Test successful upload finalization."""
        # Arrange
        session_id = str(uuid.uuid4())
        session_dir = Path("/tmp/test_session")
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 3,
            "total_size": 1000,
            "received_chunks": {0, 1, 2},
            "current_size": 1000,
            "session_dir": session_dir,
            "complete": True,
            "playlist_id": "test-playlist",
            "created_at": datetime.now(),
        }
        playlist_path = "test-playlist"

        with patch("builtins.open", mock_open(read_data=b"chunk_data")), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('shutil.rmtree'):

            # Act
            filename, metadata = await chunked_upload_service.finalize_upload(
                session_id, playlist_path
            )

            # Assert
            assert filename == "test.mp3"
            assert metadata is not None
            assert "title" in metadata
            assert session_id not in chunked_upload_service.active_uploads

    @pytest.mark.asyncio
    async def test_finalize_upload_session_not_found(self, chunked_upload_service):
        """Test finalization for non-existent session."""
        # Arrange
        session_id = "non-existent"
        playlist_path = "test-playlist"

        # Act
        result = await chunked_upload_service.finalize_upload(session_id, playlist_path)

        # Assert (decorator transforms exception to error response)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_finalize_upload_incomplete(self, chunked_upload_service):
        """Test finalization of incomplete upload."""
        # Arrange
        session_id = str(uuid.uuid4())
        session_dir = Path("/tmp/test_session")
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 5,
            "total_size": 1000,
            "received_chunks": {0, 1, 2},  # Missing chunks 3 and 4
            "current_size": 600,
            "session_dir": session_dir,
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now(),
        }
        playlist_path = "test-playlist"

        # Act
        result = await chunked_upload_service.finalize_upload(session_id, playlist_path)

        # Assert (decorator transforms exception to error response)
        assert result["status"] == "error"
        assert "incomplete" in result["message"].lower()

    # ================================================================================
    # Test get_session_status()
    # ================================================================================

    def test_get_session_status_success(self, chunked_upload_service):
        """Test successful session status retrieval."""
        # Arrange
        session_id = str(uuid.uuid4())
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 10,
            "total_size": 5 * 1024 * 1024,
            "received_chunks": {0, 1, 2, 3, 4},  # 5/10 chunks
            "current_size": 2.5 * 1024 * 1024,
            "session_dir": Path("/tmp/test"),
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now(),
        }

        # Act
        status = chunked_upload_service.get_session_status(session_id)

        # Assert
        assert status["filename"] == "test.mp3"
        assert status["total_chunks"] == 10
        assert status["received_chunks"] == 5
        assert status["progress"] == 50.0
        assert status["complete"] is False

    def test_get_session_status_not_found(self, chunked_upload_service):
        """Test status retrieval for non-existent session."""
        # Arrange
        session_id = "non-existent"

        # Act & Assert
        with pytest.raises(InvalidFileError) as exc_info:
            chunked_upload_service.get_session_status(session_id)
        assert "not found" in str(exc_info.value).lower()

    # ================================================================================
    # Test _cleanup_session()
    # ================================================================================

    def test_cleanup_session_success(self, chunked_upload_service):
        """Test successful session cleanup."""
        # Arrange
        session_id = str(uuid.uuid4())
        session_dir = Path("/tmp/test_session")
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 5,
            "total_size": 1000,
            "received_chunks": set(),
            "current_size": 0,
            "session_dir": session_dir,
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now(),
        }

        with patch('pathlib.Path.exists', return_value=True), \
             patch('shutil.rmtree') as mock_rmtree:

            # Act
            chunked_upload_service._cleanup_session(session_id)

            # Assert
            assert session_id not in chunked_upload_service.active_uploads
            mock_rmtree.assert_called_once_with(session_dir)

    def test_cleanup_session_non_existent(self, chunked_upload_service):
        """Test cleanup of non-existent session (should not raise error)."""
        # Arrange
        session_id = "non-existent"

        # Act & Assert (should not raise error)
        chunked_upload_service._cleanup_session(session_id)

    # ================================================================================
    # Test cleanup_expired_sessions()
    # ================================================================================

    def test_cleanup_expired_sessions_removes_old_sessions(self, chunked_upload_service):
        """Test that expired sessions are removed."""
        # Arrange
        old_session_id = str(uuid.uuid4())
        recent_session_id = str(uuid.uuid4())
        session_dir = Path("/tmp/test_session")

        # Old session (created 25 hours ago)
        chunked_upload_service.active_uploads[old_session_id] = {
            "filename": "old.mp3",
            "total_chunks": 5,
            "total_size": 1000,
            "received_chunks": set(),
            "current_size": 0,
            "session_dir": session_dir,
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now() - timedelta(hours=25),
        }

        # Recent session (created 1 hour ago)
        chunked_upload_service.active_uploads[recent_session_id] = {
            "filename": "recent.mp3",
            "total_chunks": 5,
            "total_size": 1000,
            "received_chunks": set(),
            "current_size": 0,
            "session_dir": session_dir,
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now() - timedelta(hours=1),
        }

        with patch('pathlib.Path.exists', return_value=True), \
             patch('shutil.rmtree'):

            # Act
            removed_count = chunked_upload_service.cleanup_expired_sessions(max_age_hours=24)

            # Assert
            assert removed_count == 1
            assert old_session_id not in chunked_upload_service.active_uploads
            assert recent_session_id in chunked_upload_service.active_uploads

    def test_cleanup_expired_sessions_no_expired_sessions(self, chunked_upload_service):
        """Test cleanup when no sessions are expired."""
        # Arrange
        session_id = str(uuid.uuid4())
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 5,
            "total_size": 1000,
            "received_chunks": set(),
            "current_size": 0,
            "session_dir": Path("/tmp/test"),
            "complete": False,
            "playlist_id": "test-playlist",
            "created_at": datetime.now() - timedelta(hours=1),  # Only 1 hour old
        }

        # Act
        removed_count = chunked_upload_service.cleanup_expired_sessions(max_age_hours=24)

        # Assert
        assert removed_count == 0
        assert session_id in chunked_upload_service.active_uploads

    def test_cleanup_expired_sessions_handles_missing_created_at(self, chunked_upload_service):
        """Test cleanup handles sessions without created_at field."""
        # Arrange
        session_id = str(uuid.uuid4())
        chunked_upload_service.active_uploads[session_id] = {
            "filename": "test.mp3",
            "total_chunks": 5,
            "total_size": 1000,
            "received_chunks": set(),
            "current_size": 0,
            "session_dir": Path("/tmp/test"),
            "complete": False,
            "playlist_id": "test-playlist",
            # No created_at field
        }

        # Act (should not raise error)
        removed_count = chunked_upload_service.cleanup_expired_sessions(max_age_hours=24)

        # Assert
        assert removed_count == 0
        assert session_id in chunked_upload_service.active_uploads

    # ================================================================================
    # Test _allowed_file()
    # ================================================================================

    def test_allowed_file_valid_extensions(self, chunked_upload_service):
        """Test file extension validation for allowed types."""
        # Arrange & Act & Assert
        assert chunked_upload_service._allowed_file("test.mp3") is True
        assert chunked_upload_service._allowed_file("test.wav") is True
        assert chunked_upload_service._allowed_file("test.flac") is True
        assert chunked_upload_service._allowed_file("test.m4a") is True
        assert chunked_upload_service._allowed_file("TEST.MP3") is True  # Case insensitive

    def test_allowed_file_invalid_extensions(self, chunked_upload_service):
        """Test file extension validation for disallowed types."""
        # Arrange & Act & Assert
        assert chunked_upload_service._allowed_file("test.txt") is False
        assert chunked_upload_service._allowed_file("test.exe") is False
        assert chunked_upload_service._allowed_file("test.jpg") is False
        assert chunked_upload_service._allowed_file("test") is False  # No extension

    # ================================================================================
    # Test _check_file_size()
    # ================================================================================

    def test_check_file_size_within_limit(self, chunked_upload_service):
        """Test file size check when within limit."""
        # Arrange
        current_size = 50 * 1024 * 1024  # 50MB
        chunk_size = 10 * 1024 * 1024    # 10MB

        # Act
        result = chunked_upload_service._check_file_size(current_size, chunk_size)

        # Assert
        assert result is True  # 60MB < 100MB limit

    def test_check_file_size_exceeds_limit(self, chunked_upload_service):
        """Test file size check when exceeding limit."""
        # Arrange
        current_size = 95 * 1024 * 1024  # 95MB
        chunk_size = 10 * 1024 * 1024    # 10MB

        # Act
        result = chunked_upload_service._check_file_size(current_size, chunk_size)

        # Assert
        assert result is False  # 105MB > 100MB limit

    def test_check_file_size_exactly_at_limit(self, chunked_upload_service):
        """Test file size check when exactly at limit."""
        # Arrange
        current_size = 90 * 1024 * 1024  # 90MB
        chunk_size = 10 * 1024 * 1024    # 10MB

        # Act
        result = chunked_upload_service._check_file_size(current_size, chunk_size)

        # Assert
        assert result is True  # Exactly 100MB should be allowed
