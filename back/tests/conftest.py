# tests/conftest.py
# Unified fixture file for all tests

import os
import sys
import warnings

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.src.dependencies import get_audio_service, get_config
from app.src.services.notification_service import PlaybackSubject


def pytest_configure(config):
    """Configure custom pytest markers for better test organization.

    These markers allow for more granular test selection and
    categorization.
    """
    # Test type markers
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "api: mark test as an API test")

    # Feature area markers
    config.addinivalue_line("markers", "nfc: test involves NFC functionality")
    config.addinivalue_line("markers", "audio: test involves audio functionality")
    config.addinivalue_line("markers", "playlist: test involves playlist functionality")

    # Performance markers
    config.addinivalue_line("markers", "slow: test is known to be slow")
    config.addinivalue_line("markers", "fast: test is known to be fast")
    
    # Comprehensive warning suppression
    import warnings
    import asyncio
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    # Set asyncio policy
    try:
        asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())
    except Exception:
        pass


# Fixture to reset the PlaybackSubject singleton between tests


@pytest.fixture
def reset_playback_subject():
    """Reset the PlaybackSubject singleton between tests."""
    # Store original instance
    original_instance = PlaybackSubject._instance
    original_socketio = PlaybackSubject._socketio

    # Reset for test
    PlaybackSubject._instance = None
    PlaybackSubject._socketio = None

    # Add a timeout to avoid infinite wait in tests that use get_instance
    import signal

    def handler(signum, frame):
        raise TimeoutError(
            "Test timed out: possible infinite loop in PlaybackSubject singleton."
        )

    signal.signal(signal.SIGALRM, handler)
    signal.alarm(2)

    yield

    # Restore after test
    signal.alarm(0)
    PlaybackSubject._instance = original_instance
    PlaybackSubject._socketio = original_socketio


# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # If dotenv is not installed, skip loading .env

# Ensure data domain services are registered for tests
@pytest.fixture(scope="session", autouse=True)
def ensure_data_domain_services():
    """Ensure data domain services are registered before tests run."""
    from app.src.infrastructure.di.data_container import register_data_domain_services
    try:
        register_data_domain_services()
    except Exception:
        # May already be registered, ignore
        pass
    yield

# Filter out specific deprecation warnings from rx library
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message="datetime.datetime.utcfromtimestamp.*",
    module="rx.internal.constants",
)
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message="datetime.datetime.utcnow.*",
    module="rx.internal.basic",
)

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add the app directory to the Python path
app_dir = os.path.join(project_root, "app")
sys.path.insert(0, app_dir)

# Add the tests directory to the Python path
tests_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, tests_dir)

# === API Test Fixtures (from app/tests/conftest.py) ===


class DummyAudio:
    def __init__(self):
        self.calls = []

    def play_track(self, track_number):
        self.calls.append(("play", track_number))

    def next_track(self):
        self.calls.append(("next",))

    def pause(self):
        self.calls.append(("pause",))

    def resume(self):
        self.calls.append(("resume",))

    def stop(self):
        self.calls.append(("stop",))

    def previous_track(self):
        self.calls.append(("previous",))


@pytest.fixture
def tmp_db_file(tmp_path):
    db_file = tmp_path / "test.db"
    yield str(db_file)
    if os.path.exists(db_file):
        os.remove(db_file)


@pytest.fixture
def test_client_with_mock_db(tmp_db_file):
    def get_test_config():
        from app.src.config import Config

        old_db_file = os.environ.get("DB_FILE")
        os.environ["DB_FILE"] = tmp_db_file
        config = Config()
        if old_db_file is not None:
            os.environ["DB_FILE"] = old_db_file
        else:
            del os.environ["DB_FILE"]
        return config

    app.dependency_overrides[get_config] = get_test_config
    return TestClient(app)


@pytest.fixture
def dummy_audio():
    audio = DummyAudio()
    app.dependency_overrides[get_audio_service] = lambda: audio
    return audio


@pytest.fixture
def mock_playlist_with_tracks(test_client_with_mock_db):
    """Creates a mock playlist with tracks in the test DB.

    Returns its id for use in tests.
    """
    # The test_client_with_mock_db parameter ensures the test DB is set up
    # before creating the playlist
    import uuid

    from app.src.config import Config
    from app.src.dependencies import get_playlist_repository_adapter

    repo = get_playlist_repository_adapter()
    playlist_id = str(uuid.uuid4())
    playlist_data = {
        "id": playlist_id,
        "type": "playlist",
        "title": "Mock Playlist",
        "path": "mock_playlist",
        "created_at": "2025-01-01T00:00:00Z",
        "tracks": [
            {
                "number": 1,
                "title": "Mock Song 1",
                "filename": "mock1.mp3",
                "duration": "3:00",
                "artist": "Mock Artist",
                "album": "Mock Album",
                "play_counter": 0,
            },
            {
                "number": 2,
                "title": "Mock Song 2",
                "filename": "mock2.mp3",
                "duration": "2:30",
                "artist": "Mock Artist",
                "album": "Mock Album",
                "play_counter": 0,
            },
        ],
    }
    # Note: The new pure DDD adapter requires async calls
    # This fixture may need to be converted to async or use a sync wrapper
    import asyncio
    asyncio.run(repo.create_playlist(playlist_data))
    
    yield playlist_id
    
    # Cleanup after fixture use (not needed for mock repositories)
    pass


@pytest.fixture(scope="session", autouse=True)
def session_database_cleanup():
    """Session-level fixture to ensure all database connections are cleaned up."""
    import warnings
    import gc
    
    yield
    
    # Comprehensive cleanup after all tests complete
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
        warnings.simplefilter("ignore", DeprecationWarning)
        
        try:
            # Legacy cleanup function no longer needed with new repository
            pass  # Cleanup not needed for in-memory mock repositories
        except ImportError:
            pass
        
        # Final cleanup
        try:
            gc.collect()
            gc.collect()  # Run twice for circular references
        except Exception:
            pass


# === Mock Fixtures from app/tests/conftest.py ===

import pytest
from unittest.mock import Mock, AsyncMock

from tests.mocks.mock_audio_service import MockAudioService
from tests.mocks.mock_controls_manager import MockControlsManager
from tests.mocks.mock_nfc_service import MockNfcService
from tests.mocks.mock_state_manager import MockStateManager
from tests.mocks.mock_upload_service import MockUploadService
from tests.mocks.mock_file_system import MockFileSystem


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
def mock_state_manager_fixture():
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
def test_app(mock_container, mock_state_manager_fixture, mock_audio_controller):
    """Provide a FastAPI test application with properly mocked services."""
    from fastapi import FastAPI
    
    app = FastAPI(title="Test TheOpenMusicBox API")

    # Set up app attributes that routes expect to find
    app.container = mock_container
    app.state_manager = mock_state_manager_fixture

    # Set up playlist_routes_ddd attribute for audio controller resolution
    mock_playlist_routes_ddd = Mock()
    mock_playlist_routes_ddd.audio_controller = mock_audio_controller
    app.playlist_routes_ddd = mock_playlist_routes_ddd

    # Link state_manager to container as well
    mock_container.state_manager = mock_state_manager_fixture

    return app


@pytest.fixture
def test_client(test_app):
    """Provide a test client for the FastAPI application."""
    return TestClient(test_app)


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    import warnings
    import asyncio

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
def reset_all_mocks():
    """Automatically reset all mock services after each test."""
    import warnings

    yield
    # This runs after each test to ensure clean state
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        warnings.simplefilter("ignore", RuntimeWarning)
