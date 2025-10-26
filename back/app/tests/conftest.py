# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Test configuration and fixtures for pytest.

This module provides common test fixtures and configuration for all tests
in the TheOpenMusicBox backend test suite.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.tests.mocks.mock_audio_service import MockAudioService
from app.tests.mocks.mock_controls_manager import MockControlsManager
from app.tests.mocks.mock_nfc_service import MockNfcService
from app.tests.mocks.mock_state_manager import MockStateManager
from app.tests.mocks.mock_upload_service import MockUploadService
from app.tests.mocks.mock_file_system import MockFileSystem


@pytest.fixture
def mock_config():
    """Provide a mock configuration object for testing."""
    config = Mock()
    config.playlists_directory = "/test/playlists"
    config.volume_default = 50
    config.volume_min = 0
    config.volume_max = 100
    config.volume_step = 5
    config.debounce_time = 0.2
    return config


@pytest.fixture
def mock_audio_service():
    """Provide a mock audio service for testing."""
    service = MockAudioService()
    service.reset()
    return service


@pytest.fixture
def mock_controls_manager():
    """Provide a mock controls manager for testing."""
    manager = MockControlsManager()
    manager.reset()
    return manager


@pytest.fixture
def mock_nfc_service():
    """Provide a mock NFC service for testing."""
    service = MockNfcService()
    service.reset()
    return service


@pytest.fixture
def mock_playlist_repository():
    """Provide a mock playlist repository for testing."""
    repo = Mock()
    repo.get_all.return_value = []
    repo.get_by_id.return_value = None
    repo.create.return_value = None
    repo.update.return_value = None
    repo.delete.return_value = False
    return repo


@pytest.fixture
def mock_track_repository():
    """Provide a mock track repository for testing."""
    repo = Mock()
    repo.get_by_playlist_id.return_value = []
    repo.create.return_value = None
    repo.update.return_value = None
    repo.delete.return_value = False
    repo.update_order.return_value = False
    return repo


@pytest.fixture
def sample_playlist_data():
    """Provide sample playlist data for testing."""
    return {
        "id": 1,
        "name": "Test Playlist",
        "description": "A test playlist",
        "tracks": [
            {"id": 1, "order": 1, "filename": "track1.mp3", "title": "Track 1"},
            {"id": 2, "order": 2, "filename": "track2.mp3", "title": "Track 2"},
            {"id": 3, "order": 3, "filename": "track3.mp3", "title": "Track 3"},
        ],
    }


@pytest.fixture
def sample_track_data():
    """Provide sample track data for testing."""
    return [
        {"id": 1, "order": 1, "filename": "track1.mp3", "title": "Track 1", "duration": 180},
        {"id": 2, "order": 2, "filename": "track2.mp3", "title": "Track 2", "duration": 210},
        {"id": 3, "order": 3, "filename": "track3.mp3", "title": "Track 3", "duration": 195},
    ]


@pytest.fixture
def mock_state_manager():
    """Provide a mock state manager for testing."""
    manager = MockStateManager()
    manager.reset()
    return manager


@pytest.fixture
def mock_upload_service():
    """Provide a mock upload service for testing."""
    service = MockUploadService()
    service.reset()
    return service


@pytest.fixture
def mock_file_system():
    """Provide a mock file system for testing."""
    fs = MockFileSystem()
    fs.reset()
    return fs


@pytest.fixture
def mock_audio_controller(mock_audio_service):
    """Provide a mock audio controller for testing."""
    from unittest.mock import AsyncMock

    controller = Mock()
    controller.handle_playback_control = AsyncMock(return_value={"status": "success"})
    controller.seek_to = Mock(return_value=True)
    controller.set_volume = Mock(return_value=True)
    controller.get_playback_state = Mock(return_value={})
    controller.audio_service = mock_audio_service
    return controller


@pytest.fixture
def mock_container(mock_audio_service, mock_nfc_service, mock_config, mock_audio_controller):
    """Provide a mock container with services for testing."""
    from app.src.controllers.audio_controller import AudioController

    container = Mock()
    container.audio = mock_audio_service
    container.nfc = mock_nfc_service
    container.config = mock_config
    container.state_manager = None  # Will be set by test fixtures

    def mock_get_service(service_class):
        if service_class == AudioController:
            return mock_audio_controller
        return None

    container.get_service = Mock(side_effect=mock_get_service)
    return container


@pytest.fixture
def mock_socketio():
    """Provide a mock Socket.IO server for testing."""
    socketio = AsyncMock()
    socketio.emit = AsyncMock()
    socketio.on = Mock()
    return socketio


@pytest.fixture
def test_app(mock_container, mock_state_manager, mock_audio_controller):
    """Provide a FastAPI test application with properly mocked services."""
    app = FastAPI(title="Test TheOpenMusicBox API")

    # Set up app attributes that routes expect to find
    app.container = mock_container
    app.state_manager = mock_state_manager

    # Set up playlist_routes_ddd attribute for audio controller resolution
    mock_playlist_routes_ddd = Mock()
    mock_playlist_routes_ddd.audio_controller = mock_audio_controller
    app.playlist_routes_ddd = mock_playlist_routes_ddd

    # Link state_manager to container as well
    mock_container.state_manager = mock_state_manager

    return app


@pytest.fixture
def test_client(test_app):
    """Provide a test client for the FastAPI application."""
    return TestClient(test_app)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import warnings

    loop = asyncio.get_event_loop_policy().new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop

    # Comprehensive cleanup with warning suppression
    if not loop.is_closed():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            warnings.simplefilter("ignore", RuntimeWarning)

            # Cancel all pending tasks
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()

                # Wait for cancellation with timeout
                if pending:
                    loop.run_until_complete(
                        asyncio.wait_for(
                            asyncio.gather(*pending, return_exceptions=True), timeout=1.0
                        )
                    )
            except (asyncio.TimeoutError, RuntimeError):
                # Ignore timeout errors during cleanup
                pass

            # Force close the loop
            try:
                loop.close()
            except Exception:
                # Ignore any errors during loop closure
                pass


@pytest.fixture
def mock_get_client_id():
    """Provide a mock get_client_id function."""

    def _get_client_id(request):
        return "test_client_001"

    return _get_client_id


@pytest.fixture
def mock_validate_client_op_id():
    """Provide a mock validate_client_op_id function."""

    def _validate_client_op_id(client_op_id):
        return client_op_id or "auto_generated_op_id"

    return _validate_client_op_id


@pytest.fixture(autouse=True)
def reset_mocks():
    """Automatically reset all mock services after each test."""
    import warnings

    yield
    # This runs after each test to ensure clean state
    # Clean up singleton repository to prevent database connection warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        try:
            # Legacy cleanup function no longer needed with new repository
            # force_cleanup_all_connections() - This function is no longer available
            pass
        except ImportError:
            pass  # Module might not be available in all test contexts


def pytest_sessionstart(session):
    """Called after session starts - perform global setup."""
    import warnings
    import asyncio

    # Suppress all warnings during test collection and execution
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=ImportWarning)

    # Specific suppression for rx library datetime warnings
    warnings.filterwarnings(
        "ignore", message="datetime.datetime.utcfromtimestamp.*", category=DeprecationWarning
    )
    warnings.filterwarnings("ignore", message=".*utcfromtimestamp.*", category=DeprecationWarning)

    # Suppress external library warnings broadly
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="rx.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="rx.internal.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module=".*site-packages.*")

    # Set asyncio policy to avoid event loop warnings
    try:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    except Exception:
        pass


def pytest_sessionfinish(session, exitstatus):
    """Called after entire test session finishes - perform global cleanup."""
    import warnings
    import asyncio
    import gc

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        warnings.simplefilter("ignore", DeprecationWarning)

        # Clean up database connections
        try:
            # Legacy cleanup function no longer needed with new repository
            # force_cleanup_all_connections() - This function is no longer available
            pass
        except ImportError:
            pass

        # Clean up asyncio resources
        try:
            # Get current event loop if it exists
            try:
                loop = asyncio.get_running_loop()
                if not loop.is_closed():
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
            except RuntimeError:
                # No running loop, that's fine
                pass

            # Final garbage collection
            gc.collect()
            gc.collect()  # Run twice to catch circular references

        except Exception:
            # Ignore any cleanup errors
            pass
