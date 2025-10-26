# tests/conftest.py
# Merged fixture file combining fixtures from app/tests/conftest.py and
# tests/conftest.py

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
