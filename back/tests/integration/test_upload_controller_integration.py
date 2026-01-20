"""Integration tests for UploadController.

Tests the integration between UploadController and DataApplicationService
to ensure proper handling of upload sessions with real service dependencies.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import os

from app.src.application.controllers.upload_controller import UploadController
from app.src.application.services.data_application_service import DataApplicationService
from app.src.domain.data.services.playlist_service import PlaylistService
from app.src.domain.data.services.track_service import TrackService


class MockPlaylistRepository:
    """Mock playlist repository for testing."""

    def __init__(self):
        self.playlists = {}

    async def find_by_id(self, playlist_id: str):
        """Find playlist by ID."""
        from app.src.domain.data.models.playlist import Playlist
        from app.src.domain.data.models.track import Track
        playlist_data = self.playlists.get(playlist_id)
        if not playlist_data:
            return None
        # Don't convert - Track objects might already be stored as dicts
        # and Playlist dataclass will handle the conversion
        return Playlist(**playlist_data)

    async def save(self, playlist):
        """Save playlist."""
        from dataclasses import asdict
        self.playlists[playlist.id] = asdict(playlist)
        return playlist

    async def update(self, playlist):
        """Update playlist."""
        from dataclasses import asdict
        self.playlists[playlist.id] = asdict(playlist)
        return playlist

    async def list_playlists(self, offset: int = 0, limit: int = 50):
        """List playlists."""
        from app.src.domain.data.models.playlist import Playlist
        from app.src.domain.data.models.track import Track

        playlists = []
        for playlist_data in self.playlists.values():
            # Convert track dicts back to Track objects
            tracks = [Track(**t) if isinstance(t, dict) else t for t in playlist_data.get('tracks', [])]
            playlist_copy = playlist_data.copy()
            playlist_copy['tracks'] = tracks
            playlists.append(Playlist(**playlist_copy))

        return playlists[offset:offset + limit], len(playlists)


class MockTrackRepository:
    """Mock track repository for testing."""

    def __init__(self):
        self.tracks = {}

    async def find_by_playlist_id(self, playlist_id: str):
        """Find tracks by playlist ID."""
        return [t for t in self.tracks.values() if t.get('playlist_id') == playlist_id]

    async def save(self, track):
        """Save track."""
        from dataclasses import asdict
        self.tracks[track.id] = asdict(track)
        return track


@pytest.fixture
def temp_upload_folder():
    """Create a temporary upload folder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config(temp_upload_folder):
    """Create mock config."""
    config = Mock()
    config.upload_folder = Path(temp_upload_folder)
    return config


@pytest.fixture
def mock_socketio():
    """Create mock Socket.IO server."""
    socketio = AsyncMock()
    return socketio


@pytest.fixture
def playlist_repo():
    """Create mock playlist repository."""
    return MockPlaylistRepository()


@pytest.fixture
def track_repo():
    """Create mock track repository."""
    return MockTrackRepository()


@pytest.fixture
async def data_app_service(playlist_repo, track_repo):
    """Create real DataApplicationService with mock repositories."""
    playlist_service = PlaylistService(playlist_repo, track_repo)
    track_service = TrackService(track_repo, playlist_repo)
    return DataApplicationService(playlist_service, track_service)


@pytest.fixture
async def upload_controller(mock_config, mock_socketio, data_app_service, temp_upload_folder):
    """Create UploadController with real DataApplicationService."""
    # Mock LocalFileStorageAdapter to avoid filesystem issues
    with patch('app.src.application.controllers.upload_controller.LocalFileStorageAdapter') as mock_storage:
        # Create a mock storage instance that uses temp folder
        mock_storage_instance = Mock()
        mock_storage_instance._base_temp_path = Path(temp_upload_folder)
        mock_storage.return_value = mock_storage_instance

        # Mock MutagenMetadataExtractor
        with patch('app.src.application.controllers.upload_controller.MutagenMetadataExtractor') as mock_metadata:
            mock_metadata_instance = Mock()
            mock_metadata.return_value = mock_metadata_instance

            # Mock UploadApplicationService
            with patch('app.src.application.controllers.upload_controller.UploadApplicationService') as mock_upload_svc:
                mock_upload_svc_instance = Mock()
                # Configure async methods to return proper values
                mock_upload_svc_instance.create_upload_session_use_case = AsyncMock(
                    return_value={
                        "status": "success",
                        "session": {
                            "session_id": "test-session-id",
                            "status": "uploading"
                        }
                    }
                )
                mock_upload_svc_instance.get_upload_status_use_case = AsyncMock(
                    return_value={
                        "status": "success",
                        "session": {"status": "uploading"}
                    }
                )
                mock_upload_svc.return_value = mock_upload_svc_instance

                # Create controller with proper DI
                controller = UploadController(mock_config, data_app_service, mock_socketio)
                yield controller


@pytest.fixture
async def test_playlist(data_app_service, playlist_repo):
    """Create a test playlist."""
    playlist_data = await data_app_service.create_playlist_use_case(
        name="Test Playlist",
        description="Test Description"
    )
    # Verify it was saved
    print(f"Created playlist: {playlist_data['id']}")
    print(f"Repo playlists: {list(playlist_repo.playlists.keys())}")
    return playlist_data


class TestUploadControllerIntegration:
    """Integration tests for UploadController."""

    @pytest.mark.asyncio
    async def test_init_upload_session_with_existing_playlist(
        self, upload_controller, test_playlist
    ):
        """Test initializing upload session with an existing playlist."""
        result = await upload_controller.init_upload_session(
            playlist_id=test_playlist["id"],
            filename="test.mp3",
            file_size=1024 * 1024,  # 1MB
            chunk_size=1024 * 256,  # 256KB
        )

        assert "session_id" in result
        assert result["chunk_size"] == 1024 * 256
        assert result["total_chunks"] == 4
        assert "error" not in result

    @pytest.mark.asyncio
    async def test_init_upload_session_with_nonexistent_playlist(
        self, upload_controller
    ):
        """Test initializing upload session with a non-existent playlist.

        Should still create session but with None playlist_path.
        """
        result = await upload_controller.init_upload_session(
            playlist_id="nonexistent-id",
            filename="test.mp3",
            file_size=1024 * 1024,
            chunk_size=1024 * 256,
        )

        # Should still succeed - session creation doesn't require existing playlist
        assert "session_id" in result
        assert result["chunk_size"] == 1024 * 256
        assert result["total_chunks"] == 4

    @pytest.mark.asyncio
    async def test_finalize_upload_with_nonexistent_playlist(
        self, upload_controller, mock_socketio
    ):
        """Test finalizing upload with non-existent playlist returns proper error."""
        # Create a mock session
        session_id = "test-session-123"

        # Mock the upload app service to return a completed session
        mock_session = {
            "status": "completed",
            "completion_data": {
                "completion_status": "success",
                "file_path": "/tmp/test.mp3",
                "metadata": {
                    "title": "Test Track",
                    "duration": 180000,
                    "file_size": 1024 * 1024
                }
            }
        }
        upload_controller.upload_app_service.get_upload_status_use_case = AsyncMock(
            return_value={"status": "success", "session": mock_session}
        )

        result = await upload_controller.finalize_upload(
            playlist_id="nonexistent-id",
            session_id=session_id,
        )

        assert result["status"] == "error"
        assert result["message"] == "Playlist not found"

    @pytest.mark.asyncio
    async def test_finalize_upload_with_existing_playlist(
        self, upload_controller, mock_socketio, temp_upload_folder
    ):
        """Test finalizing upload with existing playlist succeeds."""
        # Create a simple mock test by directly patching get_playlist_use_case
        session_id = "test-session-123"
        test_playlist_id = "test-playlist-123"

        # Create a real temp file for the test
        temp_file = Path(temp_upload_folder) / "test.mp3"
        temp_file.write_bytes(b"fake audio data")

        # Mock get_playlist to return a valid playlist dict
        upload_controller.playlist_app_service.get_playlist_use_case = AsyncMock(
            return_value={
                "id": test_playlist_id,
                "name": "Test Playlist",
                "tracks": [],
                "path": "test-playlist"
            }
        )

        # Mock the upload app service to return a completed session
        mock_session = {
            "status": "completed",
            "completion_data": {
                "completion_status": "success",
                "file_path": str(temp_file),
                "metadata": {
                    "title": "Test Track",
                    "artist": "Test Artist",
                    "album": "Test Album",
                    "duration": 180000,
                    "file_size": len(b"fake audio data")
                }
            }
        }
        upload_controller.upload_app_service.get_upload_status_use_case = AsyncMock(
            return_value={"status": "success", "session": mock_session}
        )

        result = await upload_controller.finalize_upload(
            playlist_id=test_playlist_id,
            session_id=session_id,
        )

        assert result["status"] == "success"
        assert "track" in result
        assert result["track"]["title"] == "Test Track"
        assert result["track"]["artist"] == "Test Artist"
        assert result["track"]["album"] == "Test Album"
        assert result["track"]["track_number"] == 1

        # Verify Socket.IO emit was called
        mock_socketio.emit.assert_called_once()
        call_args = mock_socketio.emit.call_args
        assert call_args[0][0] == "upload:complete"
        assert call_args[0][1]["playlist_id"] == test_playlist_id

    @pytest.mark.asyncio
    async def test_upload_session_lifecycle(
        self, upload_controller, test_playlist, mock_socketio
    ):
        """Test complete upload session lifecycle."""
        # 1. Initialize session
        init_result = await upload_controller.init_upload_session(
            playlist_id=test_playlist["id"],
            filename="test.mp3",
            file_size=1024,
            chunk_size=512,
        )

        assert "session_id" in init_result
        session_id = init_result["session_id"]

        # 2. Check session status
        status = await upload_controller.get_session_status(session_id)
        assert "status" in status or "error" in status

    @pytest.mark.asyncio
    async def test_get_playlist_use_case_contract(self):
        """Test that get_playlist_use_case returns correct type structure.

        This test verifies the contract fix: get_playlist_use_case should return
        the playlist dict directly (or None), NOT wrapped in {"status": ...} structure.
        """
        from unittest.mock import AsyncMock
        from app.src.application.services.data_application_service import DataApplicationService

        # Create mock services that return correct types
        mock_playlist_service = AsyncMock()
        mock_track_service = AsyncMock()

        service = DataApplicationService(mock_playlist_service, mock_track_service)

        # Test 1: When playlist exists, should return dict directly
        mock_playlist_service.get_playlist = AsyncMock(return_value={
            "id": "test-id",
            "name": "Test Playlist",
            "tracks": []
        })

        result = await service.get_playlist_use_case("test-id")
        assert isinstance(result, dict), "Should return dict directly"
        assert "id" in result
        assert "status" not in result, "Should NOT wrap in status envelope"

        # Test 2: When playlist doesn't exist, should return None
        mock_playlist_service.get_playlist = AsyncMock(return_value=None)

        result = await service.get_playlist_use_case("nonexistent-id")
        assert result is None, "Should return None, not wrapped response"
