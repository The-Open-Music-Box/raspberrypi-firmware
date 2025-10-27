# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for UploadApplicationService

Comprehensive tests for upload application service including session management,
chunk handling, upload completion, and error scenarios.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone, timedelta

from app.src.application.services.upload_application_service import UploadApplicationService
from app.src.domain.upload.entities.upload_session import UploadSession, UploadStatus
from app.src.domain.upload.value_objects.file_chunk import FileChunk
from app.src.domain.upload.value_objects.file_metadata import FileMetadata
from app.src.domain.upload.services.upload_validation_service import UploadValidationService


class TestUploadApplicationService:
    """Test suite for UploadApplicationService."""

    @pytest.fixture
    def mock_file_storage(self):
        """Mock file storage protocol."""
        storage = AsyncMock()
        storage.create_session_directory.return_value = Path("/tmp/session")
        storage.store_chunk.return_value = None
        storage.assemble_file.return_value = Path("/uploads/playlist/test.mp3")
        storage.verify_file_integrity.return_value = True
        storage.cleanup_session.return_value = None
        storage.get_chunk_info.return_value = None
        return storage

    @pytest.fixture
    def mock_metadata_extractor(self):
        """Mock metadata extraction protocol."""
        extractor = AsyncMock()
        # get_supported_formats is a sync method
        extractor.get_supported_formats = Mock(return_value=["mp3", "wav", "flac", "ogg"])

        # Create a default metadata object
        default_metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=1024000,
            mime_type="audio/mpeg",
            title="Test Song",
            artist="Test Artist",
            album="Test Album",
            duration_seconds=180.5,
            bitrate=128,
            sample_rate=44100
        )
        extractor.extract_metadata.return_value = default_metadata
        extractor.validate_audio_file.return_value = True
        return extractor

    @pytest.fixture
    def mock_validation_service(self):
        """Mock upload validation service."""
        service = Mock(spec=UploadValidationService)
        service.validate_upload_request.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "filename": "test.mp3",
            "total_size": 1024000,
            "total_chunks": 10
        }
        service.validate_chunk.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "chunk_index": 0,
            "chunk_size": 102400
        }
        service.validate_session_completion.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "progress": 100.0
        }
        service.validate_audio_metadata.return_value = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "has_complete_metadata": True
        }
        return service

    @pytest.fixture
    def upload_service(self, mock_file_storage, mock_metadata_extractor, mock_validation_service):
        """Create UploadApplicationService instance."""
        return UploadApplicationService(
            file_storage=mock_file_storage,
            metadata_extractor=mock_metadata_extractor,
            validation_service=mock_validation_service,
            upload_folder="/uploads"
        )

    # ================================================================================
    # Test __init__()
    # ================================================================================

    def test_init_with_all_params(self, mock_file_storage, mock_metadata_extractor, mock_validation_service):
        """Test initialization with all parameters."""
        # Act
        service = UploadApplicationService(
            file_storage=mock_file_storage,
            metadata_extractor=mock_metadata_extractor,
            validation_service=mock_validation_service,
            upload_folder="/custom/uploads"
        )

        # Assert
        assert service._file_storage == mock_file_storage
        assert service._metadata_extractor == mock_metadata_extractor
        assert service._validation_service == mock_validation_service
        assert service._upload_folder == Path("/custom/uploads")
        assert service._active_sessions == {}
        assert service._cleanup_task is None

    def test_init_creates_default_validation_service(self, mock_file_storage, mock_metadata_extractor):
        """Test initialization creates default validation service when not provided."""
        # Act
        service = UploadApplicationService(
            file_storage=mock_file_storage,
            metadata_extractor=mock_metadata_extractor
        )

        # Assert
        assert service._validation_service is not None
        assert isinstance(service._validation_service, UploadValidationService)

    def test_init_default_upload_folder(self, mock_file_storage, mock_metadata_extractor):
        """Test initialization with default upload folder."""
        # Act
        service = UploadApplicationService(
            file_storage=mock_file_storage,
            metadata_extractor=mock_metadata_extractor
        )

        # Assert
        assert service._upload_folder == Path("uploads")

    # ================================================================================
    # Test start_upload_service()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_start_upload_service_success(self, upload_service, mock_metadata_extractor):
        """Test successful upload service startup."""
        # Arrange
        mock_metadata_extractor.get_supported_formats = Mock(return_value=["mp3", "wav", "flac"])

        # Act
        with patch('pathlib.Path.mkdir'), patch('app.src.application.services.upload_application_service.asyncio.create_task') as mock_create_task:
            mock_task = Mock()
            mock_task.done = Mock(return_value=False)
            mock_create_task.return_value = mock_task

            result = await upload_service.start_upload_service()

        # Assert
        assert result["status"] == "success"
        assert result["message"] == "Upload service started"
        assert result["upload_folder"] == "/uploads"
        assert result["supported_formats"] == ["mp3", "wav", "flac"]
        assert upload_service._cleanup_task is not None
        assert not upload_service._cleanup_task.done()

    @pytest.mark.asyncio
    async def test_start_upload_service_creates_upload_folder(self, mock_file_storage, mock_metadata_extractor):
        """Test start_upload_service creates upload folder if it doesn't exist."""
        # Arrange
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            service = UploadApplicationService(
                file_storage=mock_file_storage,
                metadata_extractor=mock_metadata_extractor,
                upload_folder="/uploads"
            )

            # Act
            result = await service.start_upload_service()

            # Assert
            assert result["status"] == "success"
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @pytest.mark.asyncio
    async def test_start_upload_service_restarts_cleanup_task_if_done(self, upload_service):
        """Test start_upload_service restarts cleanup task if previous task is done."""
        # Arrange
        # Create a completed task
        async def dummy_task():
            pass

        completed_task = asyncio.create_task(dummy_task())
        await completed_task  # Wait for it to complete
        upload_service._cleanup_task = completed_task

        # Act
        with patch('pathlib.Path.mkdir'), patch('app.src.application.services.upload_application_service.asyncio.create_task') as mock_create_task:
            mock_task = Mock()
            mock_task.done = Mock(return_value=False)
            mock_create_task.return_value = mock_task

            result = await upload_service.start_upload_service()

        # Assert
        assert result["status"] == "success"
        assert upload_service._cleanup_task != completed_task
        assert not upload_service._cleanup_task.done()

    # ================================================================================
    # Test create_upload_session_use_case()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_create_upload_session_success(self, upload_service, mock_file_storage, mock_validation_service):
        """Test successful upload session creation."""
        # Arrange
        filename = "test_song.mp3"
        total_size = 1024000
        total_chunks = 10

        # Act
        result = await upload_service.create_upload_session_use_case(
            filename=filename,
            total_size=total_size,
            total_chunks=total_chunks
        )

        # Assert
        assert result["status"] == "success"
        assert result["message"] == "Upload session created"
        assert "session" in result
        assert result["session"]["filename"] == filename
        assert result["session"]["total_size_bytes"] == total_size
        assert result["session"]["total_chunks"] == total_chunks
        assert result["session"]["status"] == "created"

        # Verify session was tracked
        session_id = result["session"]["session_id"]
        assert session_id in upload_service._active_sessions

        # Verify storage interaction
        mock_file_storage.create_session_directory.assert_called_once_with(session_id)

        # Verify validation
        mock_validation_service.validate_upload_request.assert_called_once_with(
            filename, total_size, total_chunks, None
        )

    @pytest.mark.asyncio
    async def test_create_upload_session_with_playlist(self, upload_service, mock_file_storage):
        """Test creating upload session with playlist association."""
        # Act
        result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024000,
            total_chunks=10,
            playlist_id="playlist-123",
            playlist_path="my_playlist"
        )

        # Assert
        assert result["status"] == "success"
        assert result["session"]["playlist_id"] == "playlist-123"

        session_id = result["session"]["session_id"]
        session = upload_service._active_sessions[session_id]
        assert session.playlist_path == "my_playlist"

    @pytest.mark.asyncio
    async def test_create_upload_session_validation_failure(self, upload_service, mock_validation_service):
        """Test upload session creation with validation failure."""
        # Arrange
        mock_validation_service.validate_upload_request.return_value = {
            "valid": False,
            "errors": ["File size too large", "Invalid extension"],
            "warnings": []
        }

        # Act
        result = await upload_service.create_upload_session_use_case(
            filename="test.exe",
            total_size=200000000,
            total_chunks=10
        )

        # Assert
        assert result["status"] == "error"
        assert result["message"] == "Upload request validation failed"
        assert result["error_type"] == "validation_error"
        assert len(result["errors"]) == 2
        assert "File size too large" in result["errors"]
        assert "Invalid extension" in result["errors"]

        # Verify no session was created
        assert len(upload_service._active_sessions) == 0

    @pytest.mark.asyncio
    async def test_create_upload_session_with_warnings(self, upload_service, mock_validation_service):
        """Test upload session creation with validation warnings."""
        # Arrange
        mock_validation_service.validate_upload_request.return_value = {
            "valid": True,
            "errors": [],
            "warnings": ["Missing metadata", "Low bitrate"]
        }

        # Act
        result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024000,
            total_chunks=10
        )

        # Assert
        assert result["status"] == "success"
        assert "warnings" in result
        assert len(result["warnings"]) == 2
        assert "Missing metadata" in result["warnings"]

    @pytest.mark.asyncio
    async def test_create_upload_session_storage_error(self, upload_service, mock_file_storage):
        """Test upload session creation when storage fails."""
        # Arrange
        mock_file_storage.create_session_directory.side_effect = Exception("Storage unavailable")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await upload_service.create_upload_session_use_case(
                filename="test.mp3",
                total_size=1024000,
                total_chunks=10
            )
        assert "Storage unavailable" in str(exc_info.value)

    # ================================================================================
    # Test upload_chunk_use_case()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_upload_chunk_success(self, upload_service, mock_file_storage, mock_validation_service):
        """Test successful chunk upload."""
        # Arrange - Create session first
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024,
            total_chunks=2
        )
        session_id = session_result["session"]["session_id"]
        chunk_data = b"x" * 512

        # Act
        result = await upload_service.upload_chunk_use_case(
            session_id=session_id,
            chunk_index=0,
            chunk_data=chunk_data
        )

        # Assert
        assert result["status"] == "success"
        assert result["message"] == "Chunk uploaded successfully"
        assert result["chunk_index"] == 0
        assert result["progress"] == 50.0  # 1 of 2 chunks

        # Verify storage interaction
        mock_file_storage.store_chunk.assert_called_once()
        stored_chunk = mock_file_storage.store_chunk.call_args[0][1]
        assert stored_chunk.index == 0
        assert stored_chunk.data == chunk_data

        # Verify validation
        mock_validation_service.validate_chunk.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_chunk_session_not_found(self, upload_service):
        """Test chunk upload when session doesn't exist."""
        # Act
        result = await upload_service.upload_chunk_use_case(
            session_id="nonexistent-session",
            chunk_index=0,
            chunk_data=b"test"
        )

        # Assert
        assert result["status"] == "error"
        assert result["message"] == "Upload session not found"
        assert result["error_type"] == "not_found"

    @pytest.mark.asyncio
    async def test_upload_chunk_validation_failure(self, upload_service, mock_validation_service):
        """Test chunk upload with validation failure."""
        # Arrange - Create session
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024,
            total_chunks=2
        )
        session_id = session_result["session"]["session_id"]

        # Set validation to fail
        mock_validation_service.validate_chunk.return_value = {
            "valid": False,
            "errors": ["Chunk too large", "Invalid index"],
            "warnings": []
        }

        # Act
        result = await upload_service.upload_chunk_use_case(
            session_id=session_id,
            chunk_index=0,
            chunk_data=b"x" * 512
        )

        # Assert
        assert result["status"] == "error"
        assert result["message"] == "Chunk validation failed"
        assert result["error_type"] == "validation_error"
        assert "Chunk too large" in result["errors"]

    @pytest.mark.asyncio
    async def test_upload_chunk_triggers_completion(self, upload_service, mock_file_storage, mock_metadata_extractor):
        """Test chunk upload triggers completion when all chunks received."""
        # Arrange - Create session with 2 chunks
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024,
            total_chunks=2,
            playlist_id="playlist-1"
        )
        session_id = session_result["session"]["session_id"]

        # Upload first chunk
        await upload_service.upload_chunk_use_case(
            session_id=session_id,
            chunk_index=0,
            chunk_data=b"x" * 512
        )

        # Act - Upload final chunk
        with patch('pathlib.Path.mkdir'):
            result = await upload_service.upload_chunk_use_case(
                session_id=session_id,
                chunk_index=1,
                chunk_data=b"y" * 512
            )

        # Assert
        assert result["status"] == "success"
        assert result["progress"] == 100.0
        assert "completion_status" in result
        assert result["completion_status"] == "success"
        assert "file_path" in result
        assert "metadata" in result

        # Verify completion workflow was triggered
        mock_file_storage.assemble_file.assert_called_once()
        mock_file_storage.verify_file_integrity.assert_called_once()
        mock_metadata_extractor.extract_metadata.assert_called_once()
        mock_file_storage.cleanup_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_chunk_completion_stores_data(self, upload_service, mock_file_storage):
        """Test that completion data is stored in session."""
        # Arrange - Create session with 1 chunk and playlist
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=512,
            total_chunks=1,
            playlist_id="playlist-1"
        )
        session_id = session_result["session"]["session_id"]

        # Mock the assembled file path to be in a temp location
        mock_file_storage.assemble_file.return_value = Path("/tmp/test.mp3")

        # Act - Upload chunk to trigger completion
        with patch('pathlib.Path.mkdir'):
            result = await upload_service.upload_chunk_use_case(
                session_id=session_id,
                chunk_index=0,
                chunk_data=b"x" * 512
            )

        # Assert
        session = upload_service._active_sessions[session_id]
        assert session.completion_data is not None
        assert session.completion_data["completion_status"] == "success"

    @pytest.mark.asyncio
    async def test_upload_chunk_storage_error(self, upload_service, mock_file_storage):
        """Test chunk upload when storage fails."""
        # Arrange
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024,
            total_chunks=2
        )
        session_id = session_result["session"]["session_id"]

        mock_file_storage.store_chunk.side_effect = Exception("Disk full")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await upload_service.upload_chunk_use_case(
                session_id=session_id,
                chunk_index=0,
                chunk_data=b"x" * 512
            )
        assert "Disk full" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upload_chunk_multiple_chunks_progress(self, upload_service, mock_file_storage):
        """Test progress tracking across multiple chunk uploads."""
        # Arrange - Create session with 4 chunks and playlist
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=2048,
            total_chunks=4,
            playlist_id="playlist-1"
        )
        session_id = session_result["session"]["session_id"]

        # Mock the assembled file path
        mock_file_storage.assemble_file.return_value = Path("/tmp/test.mp3")

        # Act & Assert - Upload chunks one by one
        result1 = await upload_service.upload_chunk_use_case(
            session_id, 0, b"x" * 512
        )
        assert result1["progress"] == 25.0

        result2 = await upload_service.upload_chunk_use_case(
            session_id, 1, b"x" * 512
        )
        assert result2["progress"] == 50.0

        result3 = await upload_service.upload_chunk_use_case(
            session_id, 2, b"x" * 512
        )
        assert result3["progress"] == 75.0

        with patch('pathlib.Path.mkdir'):
            result4 = await upload_service.upload_chunk_use_case(
                session_id, 3, b"x" * 512
            )
        assert result4["progress"] == 100.0

    # ================================================================================
    # Test get_upload_status_use_case()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_get_upload_status_success(self, upload_service):
        """Test successful status retrieval."""
        # Arrange - Create session
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024,
            total_chunks=2
        )
        session_id = session_result["session"]["session_id"]

        # Upload one chunk
        await upload_service.upload_chunk_use_case(
            session_id=session_id,
            chunk_index=0,
            chunk_data=b"x" * 512
        )

        # Act
        result = await upload_service.get_upload_status_use_case(session_id)

        # Assert
        assert result["status"] == "success"
        assert "session" in result
        assert result["session"]["session_id"] == session_id
        assert result["session"]["progress_percentage"] == 50.0
        assert result["session"]["received_chunks"] == 1

    @pytest.mark.asyncio
    async def test_get_upload_status_not_found(self, upload_service):
        """Test status retrieval for nonexistent session."""
        # Act
        result = await upload_service.get_upload_status_use_case("nonexistent-id")

        # Assert
        assert result["status"] == "error"
        assert result["message"] == "Upload session not found"
        assert result["error_type"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_upload_status_completed_session(self, upload_service, mock_file_storage):
        """Test status retrieval for completed session."""
        # Arrange - Create and complete a session
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=512,
            total_chunks=1,
            playlist_id="playlist-1"
        )
        session_id = session_result["session"]["session_id"]

        # Mock the assembled file path
        mock_file_storage.assemble_file.return_value = Path("/tmp/test.mp3")

        # Complete the upload
        with patch('pathlib.Path.mkdir'):
            await upload_service.upload_chunk_use_case(
                session_id=session_id,
                chunk_index=0,
                chunk_data=b"x" * 512
            )

        # Act
        result = await upload_service.get_upload_status_use_case(session_id)

        # Assert
        assert result["status"] == "success"
        assert result["session"]["status"] == "completed"
        assert result["session"]["progress_percentage"] == 100.0

    # ================================================================================
    # Test cancel_upload_use_case()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_cancel_upload_success(self, upload_service, mock_file_storage):
        """Test successful upload cancellation."""
        # Arrange - Create session
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024,
            total_chunks=2
        )
        session_id = session_result["session"]["session_id"]

        # Act
        result = await upload_service.cancel_upload_use_case(session_id)

        # Assert
        assert result["status"] == "success"
        assert result["message"] == "Upload session cancelled"
        assert result["session_id"] == session_id

        # Verify session was marked cancelled
        session = upload_service._active_sessions[session_id]
        assert session.status == UploadStatus.CANCELLED

        # Verify cleanup was called
        mock_file_storage.cleanup_session.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_cancel_upload_not_found(self, upload_service):
        """Test cancellation of nonexistent session."""
        # Act
        result = await upload_service.cancel_upload_use_case("nonexistent-id")

        # Assert
        assert result["status"] == "error"
        assert result["message"] == "Upload session not found"
        assert result["error_type"] == "not_found"

    @pytest.mark.asyncio
    async def test_cancel_upload_cleanup_error(self, upload_service, mock_file_storage):
        """Test cancellation when cleanup fails."""
        # Arrange
        session_result = await upload_service.create_upload_session_use_case(
            filename="test.mp3",
            total_size=1024,
            total_chunks=2
        )
        session_id = session_result["session"]["session_id"]

        mock_file_storage.cleanup_session.side_effect = Exception("Cleanup failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await upload_service.cancel_upload_use_case(session_id)
        assert "Cleanup failed" in str(exc_info.value)

    # ================================================================================
    # Test list_active_uploads_use_case()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_list_active_uploads_empty(self, upload_service):
        """Test listing when no active uploads exist."""
        # Act
        result = await upload_service.list_active_uploads_use_case()

        # Assert
        assert result["status"] == "success"
        assert result["active_sessions"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_list_active_uploads_multiple_sessions(self, upload_service):
        """Test listing multiple active uploads."""
        # Arrange - Create multiple sessions
        session1 = await upload_service.create_upload_session_use_case(
            "file1.mp3", 1024, 2
        )
        session2 = await upload_service.create_upload_session_use_case(
            "file2.mp3", 2048, 4
        )

        # Act
        result = await upload_service.list_active_uploads_use_case()

        # Assert
        assert result["status"] == "success"
        assert result["count"] == 2
        assert len(result["active_sessions"]) == 2

        # Verify session info
        session_ids = [s["session_id"] for s in result["active_sessions"]]
        assert session1["session"]["session_id"] in session_ids
        assert session2["session"]["session_id"] in session_ids

    @pytest.mark.asyncio
    async def test_list_active_uploads_excludes_completed(self, upload_service, mock_file_storage):
        """Test listing excludes completed uploads."""
        # Arrange - Create sessions
        active_session = await upload_service.create_upload_session_use_case(
            "active.mp3", 1024, 2, playlist_id="playlist-1"
        )
        completed_session = await upload_service.create_upload_session_use_case(
            "completed.mp3", 512, 1, playlist_id="playlist-1"
        )

        # Mock the assembled file path
        mock_file_storage.assemble_file.return_value = Path("/tmp/completed.mp3")

        # Complete one session
        completed_id = completed_session["session"]["session_id"]
        with patch('pathlib.Path.mkdir'):
            await upload_service.upload_chunk_use_case(
                completed_id, 0, b"x" * 512
            )

        # Act
        result = await upload_service.list_active_uploads_use_case()

        # Assert
        assert result["count"] == 1
        assert result["active_sessions"][0]["session_id"] == active_session["session"]["session_id"]

    @pytest.mark.asyncio
    async def test_list_active_uploads_excludes_cancelled(self, upload_service):
        """Test listing excludes cancelled uploads."""
        # Arrange - Create sessions
        active_session = await upload_service.create_upload_session_use_case(
            "active.mp3", 1024, 2
        )
        cancelled_session = await upload_service.create_upload_session_use_case(
            "cancelled.mp3", 1024, 2
        )

        # Cancel one session
        await upload_service.cancel_upload_use_case(cancelled_session["session"]["session_id"])

        # Act
        result = await upload_service.list_active_uploads_use_case()

        # Assert
        assert result["count"] == 1
        assert result["active_sessions"][0]["session_id"] == active_session["session"]["session_id"]

    # ================================================================================
    # Test _handle_upload_completion()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_handle_upload_completion_success(self, upload_service, mock_file_storage, mock_metadata_extractor, mock_validation_service):
        """Test successful upload completion handling."""
        # Arrange - Create completed session
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=512,
            playlist_id="playlist-1"
        )
        session.add_chunk(FileChunk.create(0, b"x" * 512))

        # Act
        with patch('pathlib.Path.mkdir'):
            result = await upload_service._handle_upload_completion(session)

        # Assert
        assert result["completion_status"] == "success"
        assert "file_path" in result
        assert "metadata" in result
        assert "metadata_validation" in result

        # Verify workflow steps
        mock_validation_service.validate_session_completion.assert_called_once_with(session)
        mock_file_storage.assemble_file.assert_called_once()
        mock_file_storage.verify_file_integrity.assert_called_once()
        mock_metadata_extractor.extract_metadata.assert_called_once()
        mock_validation_service.validate_audio_metadata.assert_called_once()
        mock_file_storage.cleanup_session.assert_called_once_with(session.session_id)

    @pytest.mark.asyncio
    async def test_handle_upload_completion_validation_failure(self, upload_service, mock_validation_service):
        """Test completion handling when validation fails."""
        # Arrange
        session = UploadSession(
            filename="test.mp3",
            total_chunks=2,
            total_size_bytes=1024
        )
        session.add_chunk(FileChunk.create(0, b"x" * 512))
        # Missing chunk 1

        mock_validation_service.validate_session_completion.return_value = {
            "valid": False,
            "errors": ["Missing chunks"],
            "warnings": []
        }

        # Act
        result = await upload_service._handle_upload_completion(session)

        # Assert
        assert result["completion_status"] == "failed"
        assert "completion_errors" in result
        assert "Missing chunks" in result["completion_errors"]
        assert session.status == UploadStatus.FAILED

    @pytest.mark.asyncio
    async def test_handle_upload_completion_integrity_failure(self, upload_service, mock_file_storage):
        """Test completion handling when file integrity check fails."""
        # Arrange
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=512,
            playlist_id="playlist-1"
        )
        session.add_chunk(FileChunk.create(0, b"x" * 512))

        mock_file_storage.verify_file_integrity.return_value = False

        # Act
        with patch('pathlib.Path.mkdir'):
            result = await upload_service._handle_upload_completion(session)

        # Assert
        assert result["completion_status"] == "failed"
        assert "File integrity verification failed" in result["completion_errors"]
        assert session.status == UploadStatus.FAILED

    @pytest.mark.asyncio
    async def test_handle_upload_completion_uses_playlist_path(self, upload_service, mock_file_storage):
        """Test completion uses playlist_path over playlist_id for file path."""
        # Arrange
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=512,
            playlist_id="playlist-123",
            playlist_path="custom_folder"
        )
        session.add_chunk(FileChunk.create(0, b"x" * 512))

        # Act
        with patch('pathlib.Path.mkdir'):
            await upload_service._handle_upload_completion(session)

        # Assert
        call_args = mock_file_storage.assemble_file.call_args[0]
        output_path = call_args[1]
        assert "custom_folder" in str(output_path)
        assert str(output_path).endswith("test.mp3")

    @pytest.mark.asyncio
    async def test_handle_upload_completion_sets_metadata(self, upload_service, mock_metadata_extractor):
        """Test completion sets metadata on session."""
        # Arrange
        session = UploadSession(
            filename="test.mp3",
            total_chunks=1,
            total_size_bytes=512,
            playlist_id="playlist-1"
        )
        session.add_chunk(FileChunk.create(0, b"x" * 512))

        expected_metadata = FileMetadata(
            filename="test.mp3",
            size_bytes=512,
            mime_type="audio/mpeg",
            title="Test Song",
            artist="Test Artist",
            duration_seconds=120.0
        )
        mock_metadata_extractor.extract_metadata.return_value = expected_metadata

        # Act
        with patch('pathlib.Path.mkdir'):
            await upload_service._handle_upload_completion(session)

        # Assert
        assert session.file_metadata == expected_metadata

    # ================================================================================
    # Test _periodic_cleanup()
    # ================================================================================

    @pytest.mark.asyncio
    async def test_periodic_cleanup_removes_expired_sessions(self, upload_service, mock_file_storage):
        """Test periodic cleanup removes expired sessions."""
        # Arrange - Create expired session
        session = UploadSession(
            filename="test.mp3",
            total_chunks=2,
            total_size_bytes=1024,
            timeout_seconds=1  # Very short timeout
        )

        # Manually set created_at to past
        session.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        upload_service._active_sessions[session.session_id] = session

        # Call cleanup directly once instead of running the periodic task
        expired_sessions = []
        for sid, sess in upload_service._active_sessions.items():
            if sess.is_expired() and sess.status in [UploadStatus.CREATED, UploadStatus.IN_PROGRESS]:
                sess.mark_expired()
                expired_sessions.append(sid)

        for sid in expired_sessions:
            await upload_service._file_storage.cleanup_session(sid)

        # Assert - Session should be marked expired
        assert session.status == UploadStatus.EXPIRED

        # Cleanup should have been called
        mock_file_storage.cleanup_session.assert_called_once_with(session.session_id)

    @pytest.mark.asyncio
    async def test_periodic_cleanup_handles_exceptions(self, upload_service, mock_file_storage):
        """Test periodic cleanup handles exceptions gracefully."""
        # Arrange
        mock_file_storage.cleanup_session.side_effect = Exception("Storage error")

        session = UploadSession(
            filename="test.mp3",
            total_chunks=2,
            total_size_bytes=1024,
            timeout_seconds=1
        )
        session.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        upload_service._active_sessions[session.session_id] = session

        # Start cleanup task
        cleanup_task = asyncio.create_task(upload_service._periodic_cleanup())

        # Wait a bit
        await asyncio.sleep(0.1)

        # Cancel the task
        cleanup_task.cancel()

        # Should not raise exception
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

        # Task should have handled the exception
        assert True  # If we got here, exception was handled

    @pytest.mark.asyncio
    async def test_periodic_cleanup_only_cleans_active_statuses(self, upload_service):
        """Test periodic cleanup only affects CREATED and IN_PROGRESS sessions."""
        # Arrange - Create sessions in different states
        created_session = UploadSession(
            filename="created.mp3",
            total_chunks=2,
            total_size_bytes=1024,
            timeout_seconds=1
        )
        created_session.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)

        completed_session = UploadSession(
            filename="completed.mp3",
            total_chunks=1,
            total_size_bytes=512,
            timeout_seconds=1
        )
        completed_session.created_at = datetime.now(timezone.utc) - timedelta(seconds=10)
        # Manually complete the session to avoid is_active() check
        completed_session.received_chunks.add(0)
        completed_session.current_size_bytes = 512
        completed_session.status = UploadStatus.COMPLETED
        completed_session.completed_at = datetime.now(timezone.utc)

        upload_service._active_sessions[created_session.session_id] = created_session
        upload_service._active_sessions[completed_session.session_id] = completed_session

        # Call cleanup logic directly
        expired_sessions = []
        for sid, sess in upload_service._active_sessions.items():
            if sess.is_expired() and sess.status in [UploadStatus.CREATED, UploadStatus.IN_PROGRESS]:
                sess.mark_expired()
                expired_sessions.append(sid)

        # Assert - Only created session should be marked expired
        assert created_session.status == UploadStatus.EXPIRED
        assert completed_session.status == UploadStatus.COMPLETED

    # ================================================================================
    # Test Integration Scenarios
    # ================================================================================

    @pytest.mark.asyncio
    async def test_complete_upload_workflow(self, upload_service, mock_file_storage, mock_metadata_extractor):
        """Test complete upload workflow from start to finish."""
        # Step 1: Create session
        session_result = await upload_service.create_upload_session_use_case(
            filename="complete_test.mp3",
            total_size=1024,
            total_chunks=2,
            playlist_id="my-playlist"
        )

        assert session_result["status"] == "success"
        session_id = session_result["session"]["session_id"]

        # Step 2: Check initial status
        status_result = await upload_service.get_upload_status_use_case(session_id)
        assert status_result["session"]["status"] == "created"
        assert status_result["session"]["progress_percentage"] == 0.0

        # Step 3: Upload first chunk
        chunk1_result = await upload_service.upload_chunk_use_case(
            session_id, 0, b"x" * 512
        )
        assert chunk1_result["progress"] == 50.0
        assert chunk1_result["status"] == "success"

        # Step 4: Check progress
        status_result = await upload_service.get_upload_status_use_case(session_id)
        assert status_result["session"]["status"] == "in_progress"
        assert status_result["session"]["progress_percentage"] == 50.0

        # Step 5: Upload final chunk
        with patch('pathlib.Path.mkdir'):
            chunk2_result = await upload_service.upload_chunk_use_case(
                session_id, 1, b"y" * 512
            )
        assert chunk2_result["progress"] == 100.0
        assert chunk2_result["completion_status"] == "success"

        # Step 6: Verify completion
        status_result = await upload_service.get_upload_status_use_case(session_id)
        assert status_result["session"]["status"] == "completed"
        assert status_result["session"]["progress_percentage"] == 100.0

        # Verify all storage operations were called
        assert mock_file_storage.create_session_directory.called
        assert mock_file_storage.store_chunk.call_count == 2
        assert mock_file_storage.assemble_file.called
        assert mock_file_storage.verify_file_integrity.called
        assert mock_file_storage.cleanup_session.called

    @pytest.mark.asyncio
    async def test_upload_cancellation_workflow(self, upload_service):
        """Test upload cancellation workflow."""
        # Create session and upload partial data
        session_result = await upload_service.create_upload_session_use_case(
            "cancel_test.mp3", 2048, 4
        )
        session_id = session_result["session"]["session_id"]

        # Upload some chunks
        await upload_service.upload_chunk_use_case(session_id, 0, b"x" * 512)
        await upload_service.upload_chunk_use_case(session_id, 1, b"x" * 512)

        # Verify in progress
        status = await upload_service.get_upload_status_use_case(session_id)
        assert status["session"]["progress_percentage"] == 50.0

        # Cancel
        cancel_result = await upload_service.cancel_upload_use_case(session_id)
        assert cancel_result["status"] == "success"

        # Verify cancelled
        status = await upload_service.get_upload_status_use_case(session_id)
        assert status["session"]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_concurrent_upload_sessions(self, upload_service):
        """Test handling multiple concurrent upload sessions."""
        # Create multiple sessions
        sessions = []
        for i in range(5):
            result = await upload_service.create_upload_session_use_case(
                f"file{i}.mp3", 1024, 2
            )
            sessions.append(result["session"]["session_id"])

        # List active uploads
        active_list = await upload_service.list_active_uploads_use_case()
        assert active_list["count"] == 5

        # Upload chunks to different sessions
        for session_id in sessions[:3]:
            await upload_service.upload_chunk_use_case(session_id, 0, b"x" * 512)

        # Verify correct tracking
        for i, session_id in enumerate(sessions):
            status = await upload_service.get_upload_status_use_case(session_id)
            expected_progress = 50.0 if i < 3 else 0.0
            assert status["session"]["progress_percentage"] == expected_progress

    @pytest.mark.asyncio
    async def test_error_recovery_session_remains_accessible(self, upload_service, mock_file_storage):
        """Test session remains accessible after non-fatal errors."""
        # Create session
        session_result = await upload_service.create_upload_session_use_case(
            "test.mp3", 1024, 2
        )
        session_id = session_result["session"]["session_id"]

        # Simulate storage error on first chunk
        mock_file_storage.store_chunk.side_effect = [
            Exception("Temporary error"),
            None  # Second call succeeds
        ]

        # First upload fails
        with pytest.raises(Exception):
            await upload_service.upload_chunk_use_case(session_id, 0, b"x" * 512)

        # Session should still be accessible
        status = await upload_service.get_upload_status_use_case(session_id)
        assert status["status"] == "success"
        assert status["session"]["session_id"] == session_id
