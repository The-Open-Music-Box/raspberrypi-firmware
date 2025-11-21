"""
Comprehensive tests for UploadController.

Tests cover:
- Initialization with dependencies
- Upload session initialization
- Chunk uploading and progress tracking
- Session status queries
- Upload finalization
- Metadata handling
- Socket.IO event emission
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from math import ceil
from pathlib import Path
from app.src.application.controllers.upload_controller import UploadController


@pytest.fixture
def mock_data_service():
    """Create mock data application service."""
    service = Mock()
    service.get_playlist_use_case = AsyncMock(return_value={"id": 1, "name": "Test"})
    service.add_track_to_playlist_use_case = AsyncMock(return_value={"track_id": 1})
    return service


class TestUploadControllerInitialization:
    """Test UploadController initialization."""

    def test_create_with_config(self, mock_data_service):
        """Test creating controller with config."""
        config = Mock()
        config.upload_folder = "/uploads"

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService'):
                    controller = UploadController(config, mock_data_service)

                    assert controller.config == config
                    assert controller.socketio is None
                    assert controller.file_storage is not None
                    assert controller.metadata_extractor is not None

    def test_create_with_socketio(self, mock_data_service):
        """Test creating with Socket.IO support."""
        config = Mock()
        config.upload_folder = "/uploads"
        socketio = Mock()

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService'):
                    controller = UploadController(config, mock_data_service, socketio)

                    assert controller.socketio == socketio

    def test_initializes_upload_app_service(self, mock_data_service):
        """Test upload application service is initialized."""
        config = Mock()
        config.upload_folder = "/uploads"

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService'):
                    controller = UploadController(config, mock_data_service)

                    assert controller.upload_app_service is not None

    def test_initializes_playlist_app_service(self, mock_data_service):
        """Test playlist application service is injected correctly."""
        config = Mock()
        config.upload_folder = "/uploads"

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService'):
                    controller = UploadController(config, mock_data_service)

                    assert controller.playlist_app_service is mock_data_service


class TestSessionInitialization:
    """Test upload session initialization."""

    @pytest.fixture
    def controller(self, tmp_path):
        """Create controller for testing."""
        config = Mock()
        config.upload_folder = tmp_path / "uploads"

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter') as mock_storage:
            mock_storage.return_value = Mock(_base_temp_path=tmp_path)
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService') as mock_upload:
                    mock_upload_instance = Mock()
                    mock_upload_instance.create_upload_session_use_case = AsyncMock()
                    mock_upload_instance.get_upload_status_use_case = AsyncMock()
                    mock_upload.return_value = mock_upload_instance

                    controller = UploadController(config, mock_data_service)
                    # Set up playlist service mock
                    controller.playlist_app_service = Mock()
                    controller.playlist_app_service.get_playlist_use_case = AsyncMock()
                    yield controller

    @pytest.mark.asyncio
    async def test_init_upload_session_success(self, controller):
        """Test successfully initializing upload session."""
        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value={
            "id": "pl-123",
            "path": "playlist_123"
        })

        controller.upload_app_service.create_upload_session_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {"session_id": "session-abc"}
        })

        result = await controller.init_upload_session(
            playlist_id="pl-123",
            filename="song.mp3",
            file_size=10_000_000,
            chunk_size=1_048_576
        )

        assert result["session_id"] == "session-abc"
        assert result["chunk_size"] == 1_048_576
        assert result["total_chunks"] == 10  # ceil(10_000_000 / 1_048_576)

    @pytest.mark.asyncio
    async def test_init_session_calculates_total_chunks(self, controller):
        """Test total chunks calculation."""
        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value={
            "id": "pl-123"
        })

        controller.upload_app_service.create_upload_session_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {"session_id": "session-abc"}
        })

        result = await controller.init_upload_session(
            playlist_id="pl-123",
            filename="song.mp3",
            file_size=5_000_000,
            chunk_size=1_000_000
        )

        assert result["total_chunks"] == ceil(5_000_000 / 1_000_000)

    @pytest.mark.asyncio
    async def test_init_session_with_playlist_not_found(self, controller):
        """Test init session when playlist not found."""
        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value=None)

        controller.upload_app_service.create_upload_session_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {"session_id": "session-abc"}
        })

        # Should still work, playlist_path will be None
        result = await controller.init_upload_session(
            playlist_id="pl-999",
            filename="song.mp3",
            file_size=1_000_000,
            chunk_size=100_000
        )

        assert "session_id" in result

    @pytest.mark.asyncio
    async def test_init_session_creation_fails(self, controller):
        """Test init when session creation fails."""
        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value={
            "id": "pl-123"
        })

        controller.upload_app_service.create_upload_session_use_case = AsyncMock(return_value={
            "status": "error",
            "message": "Session creation failed"
        })

        result = await controller.init_upload_session(
            playlist_id="pl-123",
            filename="song.mp3",
            file_size=1_000_000,
            chunk_size=100_000
        )

        assert "error" in result
        assert result["error"] == "Session creation failed"


class TestChunkUpload:
    """Test chunk upload operations."""

    @pytest.fixture
    def controller(self, tmp_path):
        """Create controller with Socket.IO."""
        config = Mock()
        config.upload_folder = tmp_path / "uploads"
        socketio = AsyncMock()

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService') as mock_upload:
                    mock_upload_instance = Mock()
                    mock_upload_instance.upload_chunk_use_case = AsyncMock()
                    mock_upload.return_value = mock_upload_instance

                    controller = UploadController(config, mock_data_service, socketio)
                    yield controller

    @pytest.mark.asyncio
    async def test_upload_chunk_success(self, controller):
        """Test successfully uploading a chunk."""
        controller.upload_app_service.upload_chunk_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {"status": "in_progress"},
            "progress": 50
        })

        result = await controller.upload_chunk(
            playlist_id="pl-123",
            session_id="session-abc",
            chunk_index=0,
            chunk_data=b"chunk data"
        )

        assert result["status"] == "success"
        assert result["progress"] == 50

    @pytest.mark.asyncio
    async def test_upload_chunk_emits_progress_event(self, controller):
        """Test chunk upload emits progress event."""
        controller.upload_app_service.upload_chunk_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {"status": "in_progress"},
            "progress": 30
        })

        await controller.upload_chunk(
            playlist_id="pl-123",
            session_id="session-abc",
            chunk_index=2,
            chunk_data=b"data"
        )

        controller.socketio.emit.assert_called_once()
        call_args = controller.socketio.emit.call_args

        assert call_args[0][0] == "upload:progress"
        assert call_args[0][1]["progress"] == 30
        assert call_args[0][1]["chunk_index"] == 2
        assert call_args[0][1]["complete"] is False

    @pytest.mark.asyncio
    async def test_upload_chunk_completion_event(self, controller):
        """Test chunk upload emits completion flag."""
        controller.upload_app_service.upload_chunk_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {"status": "completed"},
            "progress": 100
        })

        await controller.upload_chunk(
            playlist_id="pl-123",
            session_id="session-abc",
            chunk_index=9,
            chunk_data=b"final chunk"
        )

        call_args = controller.socketio.emit.call_args
        assert call_args[0][1]["complete"] is True

    @pytest.mark.asyncio
    async def test_upload_chunk_without_socketio(self, tmp_path):
        """Test chunk upload without Socket.IO."""
        config = Mock()
        config.upload_folder = tmp_path / "uploads"

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService') as mock_upload:
                    mock_upload_instance = Mock()
                    mock_upload_instance.upload_chunk_use_case = AsyncMock(return_value={
                        "status": "success",
                        "session": {"status": "in_progress"},
                        "progress": 50
                    })
                    mock_upload.return_value = mock_upload_instance

                    controller = UploadController(config, mock_data_service)  # No socketio

                    # Should not raise exception
                    result = await controller.upload_chunk(
                        playlist_id="pl-123",
                        session_id="session-abc",
                        chunk_index=0,
                        chunk_data=b"data"
                    )

                    assert result["status"] == "success"


class TestSessionStatus:
    """Test session status queries."""

    @pytest.fixture
    def controller(self, tmp_path):
        """Create controller for testing."""
        config = Mock()
        config.upload_folder = tmp_path / "uploads"

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService') as mock_upload:
                    mock_upload_instance = Mock()
                    mock_upload_instance.get_upload_status_use_case = AsyncMock()
                    mock_upload.return_value = mock_upload_instance

                    controller = UploadController(config, mock_data_service)
                    yield controller

    @pytest.mark.asyncio
    async def test_get_session_status_success(self, controller):
        """Test getting session status."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {
                "session_id": "session-abc",
                "progress": 75,
                "status": "in_progress"
            }
        })

        result = await controller.get_session_status("session-abc")

        assert result["session_id"] == "session-abc"
        assert result["progress"] == 75

    @pytest.mark.asyncio
    async def test_get_session_status_not_found(self, controller):
        """Test getting status for non-existent session."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "error",
            "message": "Session not found"
        })

        result = await controller.get_session_status("session-999")

        assert "error" in result
        assert result["error"] == "Session not found"


class TestUploadFinalization:
    """Test upload finalization."""

    @pytest.fixture
    def controller(self, tmp_path):
        """Create controller with Socket.IO."""
        config = Mock()
        config.upload_folder = tmp_path / "uploads"
        socketio = AsyncMock()

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService') as mock_upload:
                    mock_upload_instance = Mock()
                    mock_upload_instance.get_upload_status_use_case = AsyncMock()
                    mock_upload.return_value = mock_upload_instance

                    controller = UploadController(config, mock_data_service, socketio)
                    controller.playlist_app_service = Mock()
                    controller.playlist_app_service.get_playlist_use_case = AsyncMock()
                    yield controller

    @pytest.mark.asyncio
    async def test_finalize_upload_success(self, controller):
        """Test successfully finalizing upload."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {
                "status": "completed",
                "completion_data": {
                    "completion_status": "success",
                    "file_path": "/uploads/playlist_123/song.mp3",
                    "metadata": {
                        "title": "Test Song",
                        "artist": "Test Artist",
                        "duration": 180000,
                        "file_size": 5_000_000
                    }
                }
            }
        })

        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value={
            "id": "pl-123",
            "tracks": [{"track_number": 1}]
        })

        result = await controller.finalize_upload(
            playlist_id="pl-123",
            session_id="session-abc"
        )

        assert result["status"] == "success"
        assert "track" in result
        assert result["track"]["track_number"] == 2  # After existing track

    @pytest.mark.asyncio
    async def test_finalize_with_metadata_override(self, controller):
        """Test finalization with metadata override."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {
                "status": "completed",
                "completion_data": {
                    "completion_status": "success",
                    "file_path": "/uploads/song.mp3",
                    "metadata": {
                        "title": "Original Title",
                        "duration": 180000
                    }
                }
            }
        })

        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value={
            "id": "pl-123",
            "tracks": []
        })

        result = await controller.finalize_upload(
            playlist_id="pl-123",
            session_id="session-abc",
            metadata_override={"title": "New Title", "artist": "New Artist"}
        )

        assert result["track"]["title"] == "New Title"
        assert result["track"]["artist"] == "New Artist"

    @pytest.mark.asyncio
    async def test_finalize_session_not_found(self, controller):
        """Test finalization when session not found."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "error",
            "message": "Session not found"
        })

        result = await controller.finalize_upload(
            playlist_id="pl-123",
            session_id="session-999"
        )

        assert result["status"] == "error"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_finalize_upload_not_completed(self, controller):
        """Test finalization when upload not completed."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {
                "status": "in_progress"
            }
        })

        result = await controller.finalize_upload(
            playlist_id="pl-123",
            session_id="session-abc"
        )

        assert result["status"] == "error"
        assert "not completed" in result["message"]

    @pytest.mark.asyncio
    async def test_finalize_playlist_not_found(self, controller):
        """Test finalization when playlist not found."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {
                "status": "completed",
                "completion_data": {
                    "completion_status": "success",
                    "file_path": "/uploads/song.mp3",
                    "metadata": {"duration": 180000}
                }
            }
        })

        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value=None)

        result = await controller.finalize_upload(
            playlist_id="pl-999",
            session_id="session-abc"
        )

        assert result["status"] == "error"
        assert "Playlist not found" in result["message"]

    @pytest.mark.asyncio
    async def test_finalize_emits_complete_event(self, controller):
        """Test finalization emits complete event."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {
                "status": "completed",
                "completion_data": {
                    "completion_status": "success",
                    "file_path": "/uploads/song.mp3",
                    "metadata": {"title": "Song", "duration": 180000}
                }
            }
        })

        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value={
            "id": "pl-123",
            "tracks": []
        })

        await controller.finalize_upload("pl-123", "session-abc")

        # Check upload:complete event was emitted
        calls = [call for call in controller.socketio.emit.call_args_list
                 if call[0][0] == "upload:complete"]
        assert len(calls) == 1


class TestMetadataHandling:
    """Test metadata extraction and handling."""

    @pytest.fixture
    def controller(self, tmp_path):
        """Create controller for testing."""
        config = Mock()
        config.upload_folder = tmp_path / "uploads"
        socketio = AsyncMock()

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService') as mock_upload:
                    mock_upload_instance = Mock()
                    mock_upload_instance.get_upload_status_use_case = AsyncMock()
                    mock_upload.return_value = mock_upload_instance

                    controller = UploadController(config, mock_data_service, socketio)
                    controller.playlist_app_service = Mock()
                    controller.playlist_app_service.get_playlist_use_case = AsyncMock()
                    yield controller

    @pytest.mark.asyncio
    async def test_uses_metadata_title(self, controller):
        """Test uses metadata title when available."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {
                "status": "completed",
                "completion_data": {
                    "completion_status": "success",
                    "file_path": "/uploads/filename.mp3",
                    "metadata": {
                        "title": "Metadata Title",
                        "duration": 180000
                    }
                }
            }
        })

        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value={
            "id": "pl-123",
            "tracks": []
        })

        result = await controller.finalize_upload("pl-123", "session-abc")

        assert result["track"]["title"] == "Metadata Title"

    @pytest.mark.asyncio
    async def test_uses_filename_when_no_title(self, controller):
        """Test uses filename stem when no title in metadata."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(return_value={
            "status": "success",
            "session": {
                "status": "completed",
                "completion_data": {
                    "completion_status": "success",
                    "file_path": "/uploads/awesome_song.mp3",
                    "metadata": {"duration": 180000}
                }
            }
        })

        controller.playlist_app_service.get_playlist_use_case = AsyncMock(return_value={
            "id": "pl-123",
            "tracks": []
        })

        result = await controller.finalize_upload("pl-123", "session-abc")

        assert result["track"]["title"] == "awesome_song"


class TestErrorHandling:
    """Test error handling in upload controller."""

    @pytest.fixture
    def controller(self, tmp_path):
        """Create controller with Socket.IO."""
        config = Mock()
        config.upload_folder = tmp_path / "uploads"
        socketio = AsyncMock()

        with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter'):
            with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor'):
                with patch('app.src.application.controllers.upload_controller.UploadApplicationService') as mock_upload:
                    mock_upload_instance = Mock()
                    mock_upload_instance.get_upload_status_use_case = AsyncMock()
                    mock_upload.return_value = mock_upload_instance

                    controller = UploadController(config, mock_data_service, socketio)
                    controller.playlist_app_service = Mock()
                    controller.playlist_app_service.get_playlist_use_case = AsyncMock()
                    yield controller

    @pytest.mark.asyncio
    async def test_finalize_handles_exceptions(self, controller):
        """Test finalization handles exceptions."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        result = await controller.finalize_upload("pl-123", "session-abc")

        assert result["status"] == "error"
        assert "Unexpected error" in result["message"]

    @pytest.mark.asyncio
    async def test_finalize_emits_error_event(self, controller):
        """Test finalization emits error event on failure."""
        controller.upload_app_service.get_upload_status_use_case = AsyncMock(
            side_effect=Exception("Upload error")
        )

        await controller.finalize_upload("pl-123", "session-abc")

        # Check upload:error event was emitted
        calls = [call for call in controller.socketio.emit.call_args_list
                 if call[0][0] == "upload:error"]
        assert len(calls) == 1
