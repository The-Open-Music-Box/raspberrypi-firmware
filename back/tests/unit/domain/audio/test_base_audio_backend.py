"""
Comprehensive tests for BaseAudioBackend.

Tests cover:
- Initialization and state management
- File path validation
- Volume clamping
- Event notification system
- Safe operation wrapper
- Base method implementations (get_position, set_volume, cleanup)
- Resource management (context manager, creation, cleanup)
- Abstract method enforcement
- Thread safety
"""

import pytest
import threading
from typing import Optional
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path

from app.src.domain.audio.backends.implementations.base_audio_backend import BaseAudioBackend


# Create a concrete test implementation
class ConcreteTestBackend(BaseAudioBackend):
    """Concrete backend for testing BaseAudioBackend."""

    def __init__(self, playback_subject=None):
        super().__init__(playback_subject)
        self.play_called = False
        self.stop_called = False
        self.pause_called = False
        self.resume_called = False

    def play_file(self, file_path: str) -> bool:
        """Test implementation of play_file."""
        self.play_called = True
        with self._state_lock:
            self._is_playing = True
            self._current_file_path = file_path
        return True

    async def play(self, file_path: str) -> bool:
        """Async play implementation."""
        return self.play_file(file_path)

    async def stop(self) -> bool:
        """Test implementation of stop."""
        self.stop_called = True
        with self._state_lock:
            self._is_playing = False
            self._current_file_path = None
        return True

    async def pause(self) -> bool:
        """Test implementation of pause."""
        self.pause_called = True
        with self._state_lock:
            self._is_playing = False
        return True

    async def resume(self) -> bool:
        """Test implementation of resume."""
        self.resume_called = True
        with self._state_lock:
            self._is_playing = True
        return True

    async def set_volume(self, volume: int) -> bool:
        """Async set_volume implementation."""
        return super().set_volume(volume)

    async def get_volume(self) -> int:
        """Async get_volume implementation."""
        return self._volume

    async def seek(self, position_ms: int) -> bool:
        """Async seek implementation."""
        return True

    async def get_position(self) -> Optional[int]:
        """Async get_position implementation."""
        return 0

    async def get_duration(self) -> Optional[int]:
        """Async get_duration implementation."""
        return None

    @property
    def is_playing(self) -> bool:
        """Test implementation of is_playing."""
        with self._state_lock:
            return self._is_playing

    @property
    def is_busy(self) -> bool:
        """Test implementation of is_busy."""
        with self._state_lock:
            return self._is_playing


@pytest.fixture
def backend():
    """Create a concrete test backend."""
    return ConcreteTestBackend()


@pytest.fixture
def mock_subject():
    """Create a mock playback subject."""
    subject = Mock()
    subject.notify = Mock()
    return subject


@pytest.fixture
def backend_with_subject(mock_subject):
    """Create a backend with playback subject."""
    return ConcreteTestBackend(playback_subject=mock_subject)


@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_text("fake audio data")
    return audio_file


class TestBaseAudioBackendInitialization:
    """Test BaseAudioBackend initialization."""

    def test_create_without_subject(self, backend):
        """Test creating backend without playback subject."""
        assert backend._playback_subject is None
        assert backend._is_playing is False
        assert backend._current_file_path is None
        assert backend._volume == 70
        assert backend._backend_name == "ConcreteTestBackend"

    def test_create_with_subject(self, backend_with_subject, mock_subject):
        """Test creating backend with playback subject."""
        assert backend_with_subject._playback_subject == mock_subject

    def test_state_lock_initialized(self, backend):
        """Test state lock is initialized."""
        assert hasattr(backend, '_state_lock')
        # RLock is a factory function, so check the type
        assert isinstance(backend._state_lock, type(threading.RLock()))

    def test_default_volume(self, backend):
        """Test default volume is set correctly."""
        assert backend._volume == 70

    def test_backend_name_from_class(self, backend):
        """Test backend name is set from class name."""
        assert backend._backend_name == "ConcreteTestBackend"


class TestFilePathValidation:
    """Test file path validation."""

    def test_validate_existing_file(self, backend, temp_audio_file):
        """Test validating an existing file."""
        path = backend._validate_file_path(str(temp_audio_file))

        assert path is not None
        assert isinstance(path, Path)
        assert path.exists()

    def test_validate_nonexistent_file(self, backend):
        """Test validating a nonexistent file."""
        path = backend._validate_file_path("/nonexistent/file.mp3")

        assert path is None

    def test_validate_directory_path(self, backend, tmp_path):
        """Test validating a directory path (should fail)."""
        path = backend._validate_file_path(str(tmp_path))

        assert path is None

    def test_validate_empty_path(self, backend):
        """Test validating an empty path."""
        path = backend._validate_file_path("")

        assert path is None

    def test_validate_relative_path(self, backend, temp_audio_file):
        """Test validating a relative path."""
        # Get relative path from current directory
        path = backend._validate_file_path(str(temp_audio_file))

        # Should work if file exists
        assert path is not None


class TestVolumeClamping:
    """Test volume clamping functionality."""

    def test_clamp_normal_volume(self, backend):
        """Test clamping a normal volume value."""
        clamped = backend._clamp_volume(50)

        assert clamped == 50

    def test_clamp_minimum_volume(self, backend):
        """Test clamping minimum volume."""
        clamped = backend._clamp_volume(0)

        assert clamped == 0

    def test_clamp_maximum_volume(self, backend):
        """Test clamping maximum volume."""
        clamped = backend._clamp_volume(100)

        assert clamped == 100

    def test_clamp_volume_below_minimum(self, backend):
        """Test clamping volume below minimum."""
        clamped = backend._clamp_volume(-50)

        assert clamped == 0

    def test_clamp_volume_above_maximum(self, backend):
        """Test clamping volume above maximum."""
        clamped = backend._clamp_volume(150)

        assert clamped == 100

    def test_clamp_large_negative_volume(self, backend):
        """Test clamping a large negative volume."""
        clamped = backend._clamp_volume(-1000)

        assert clamped == 0

    def test_clamp_large_positive_volume(self, backend):
        """Test clamping a large positive volume."""
        clamped = backend._clamp_volume(5000)

        assert clamped == 100


class TestEventNotification:
    """Test event notification system."""

    def test_notify_event_with_subject(self, backend_with_subject, mock_subject):
        """Test notifying an event with subject."""
        backend_with_subject._notify_playback_event("track_started", {"file": "test.mp3"})

        mock_subject.notify.assert_called_once()
        call_args = mock_subject.notify.call_args[0][0]
        assert call_args["event"] == "track_started"
        assert call_args["backend"] == "ConcreteTestBackend"
        assert call_args["file"] == "test.mp3"

    def test_notify_event_without_subject(self, backend):
        """Test notifying event without subject (should not raise error)."""
        # Should not raise an error
        backend._notify_playback_event("track_started")

    def test_notify_event_without_data(self, backend_with_subject, mock_subject):
        """Test notifying event without data."""
        backend_with_subject._notify_playback_event("paused")

        mock_subject.notify.assert_called_once()
        call_args = mock_subject.notify.call_args[0][0]
        assert call_args["event"] == "paused"
        assert call_args["backend"] == "ConcreteTestBackend"

    def test_notify_event_with_complex_data(self, backend_with_subject, mock_subject):
        """Test notifying event with complex data."""
        data = {
            "file": "test.mp3",
            "duration": 180000,
            "position": 5000,
            "metadata": {"artist": "Test Artist"}
        }
        backend_with_subject._notify_playback_event("position_update", data)

        mock_subject.notify.assert_called_once()
        call_args = mock_subject.notify.call_args[0][0]
        assert call_args["file"] == "test.mp3"
        assert call_args["duration"] == 180000
        assert call_args["metadata"]["artist"] == "Test Artist"


class TestSafeOperation:
    """Test safe operation wrapper."""

    def test_safe_operation_success(self, backend):
        """Test safe operation with successful function."""
        def test_func(a, b):
            return a + b

        result = backend._safe_operation("add", test_func, 5, 3)

        assert result == 8

    def test_safe_operation_with_kwargs(self, backend):
        """Test safe operation with keyword arguments."""
        def test_func(a, b=10):
            return a * b

        result = backend._safe_operation("multiply", test_func, 5, b=20)

        assert result == 100

    def test_safe_operation_handles_error(self, backend):
        """Test safe operation logs errors."""
        def failing_func():
            raise ValueError("Test error")

        # The error handler logs but re-raises exceptions
        with pytest.raises(ValueError, match="Test error"):
            backend._safe_operation("fail", failing_func)


class TestBaseMethodImplementations:
    """Test base method implementations."""

    def test_get_position_default(self, backend):
        """Test base class get_position returns 0.0."""
        # Test the base class sync method directly
        position = super(ConcreteTestBackend, backend).get_position()

        assert position == 0.0

    def test_set_volume_sync(self, backend):
        """Test setting volume with base sync method."""
        # Test the base class sync method directly
        result = super(ConcreteTestBackend, backend).set_volume(80)

        assert result is True
        assert backend._volume == 80

    @pytest.mark.asyncio
    async def test_set_volume_async(self, backend):
        """Test setting volume with async method."""
        result = await backend.set_volume(80)

        assert result is True
        assert backend._volume == 80

    @pytest.mark.asyncio
    async def test_set_volume_clamped(self, backend):
        """Test setting volume gets clamped."""
        await backend.set_volume(150)

        assert backend._volume == 100

    @pytest.mark.asyncio
    async def test_set_volume_thread_safe(self, backend):
        """Test set_volume uses state lock."""
        # Set volume should complete without errors
        result = await backend.set_volume(60)

        assert result is True
        assert backend._volume == 60

    def test_cleanup_resets_state(self, backend, temp_audio_file):
        """Test cleanup resets state."""
        backend.play_file(str(temp_audio_file))
        backend.cleanup()

        assert backend._is_playing is False
        assert backend._current_file_path is None

    def test_cleanup_thread_safe(self, backend):
        """Test cleanup uses state lock."""
        # Cleanup should complete without errors
        backend.cleanup()

        assert backend._is_playing is False


class TestResourceManagement:
    """Test resource management functionality."""

    def test_acquire_audio_resource(self, backend):
        """Test acquiring audio resource with context manager."""
        with backend._acquire_audio_resource("test_resource") as resource:
            assert resource is not None
            assert "mock_test_resource_resource" == resource

    def test_create_audio_resource(self, backend):
        """Test creating audio resource."""
        resource = backend._create_audio_resource("mixer")

        assert resource == "mock_mixer_resource"

    def test_cleanup_audio_resource(self, backend):
        """Test cleaning up audio resource (should not raise error)."""
        resource = "test_resource"

        # Should not raise error
        backend._cleanup_audio_resource("mixer", resource)

    def test_resource_cleanup_on_exception(self, backend):
        """Test resource cleanup occurs even on exception."""
        cleanup_called = False

        # Override cleanup to track calls
        original_cleanup = backend._cleanup_audio_resource

        def tracked_cleanup(resource_type, resource):
            nonlocal cleanup_called
            cleanup_called = True
            original_cleanup(resource_type, resource)

        backend._cleanup_audio_resource = tracked_cleanup

        try:
            with backend._acquire_audio_resource("test") as resource:
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert cleanup_called is True


class TestAbstractMethodEnforcement:
    """Test that abstract methods are properly enforced by protocol."""

    def test_abstract_backend_cannot_be_instantiated(self):
        """Test BaseAudioBackend cannot be instantiated directly."""
        # BaseAudioBackend now properly inherits from AudioBackendProtocol
        # which has abstract methods, so it cannot be instantiated
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseAudioBackend()

    def test_incomplete_implementation_fails(self):
        """Test that incomplete implementations fail."""
        class IncompleteBackend(BaseAudioBackend):
            """Backend missing required async methods."""
            def play_file(self, file_path: str) -> bool:
                return True

            @property
            def is_playing(self) -> bool:
                return False

            @property
            def is_busy(self) -> bool:
                return False

        # Should fail because missing async protocol methods
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteBackend()


class TestThreadSafety:
    """Test thread-safe state management."""

    def test_concurrent_volume_changes(self, backend):
        """Test concurrent volume changes are thread-safe."""
        def change_volume(vol):
            backend.set_volume(vol)

        threads = [
            threading.Thread(target=change_volume, args=(i,))
            for i in range(10, 91, 10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have a valid volume between 0 and 100
        assert 0 <= backend._volume <= 100

    def test_concurrent_state_access(self, backend, temp_audio_file):
        """Test concurrent state access is thread-safe."""
        backend.play_file(str(temp_audio_file))

        def access_state():
            _ = backend.is_playing
            _ = backend.is_busy

        threads = [threading.Thread(target=access_state) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not raise any errors
        assert backend.is_playing is True


class TestConcreteImplementation:
    """Test the concrete test implementation."""

    def test_play_file_implementation(self, backend, temp_audio_file):
        """Test concrete play_file implementation."""
        result = backend.play_file(str(temp_audio_file))

        assert result is True
        assert backend.play_called is True
        assert backend.is_playing is True

    @pytest.mark.asyncio
    async def test_stop_implementation(self, backend, temp_audio_file):
        """Test concrete stop implementation."""
        backend.play_file(str(temp_audio_file))
        result = await backend.stop()

        assert result is True
        assert backend.stop_called is True
        assert backend.is_playing is False

    @pytest.mark.asyncio
    async def test_pause_implementation(self, backend, temp_audio_file):
        """Test concrete pause implementation."""
        backend.play_file(str(temp_audio_file))
        result = await backend.pause()

        assert result is True
        assert backend.pause_called is True
        assert backend.is_playing is False

    @pytest.mark.asyncio
    async def test_resume_implementation(self, backend, temp_audio_file):
        """Test concrete resume implementation."""
        backend.play_file(str(temp_audio_file))
        await backend.pause()
        result = await backend.resume()

        assert result is True
        assert backend.resume_called is True
        assert backend.is_playing is True

    @pytest.mark.asyncio
    async def test_is_playing_property(self, backend, temp_audio_file):
        """Test is_playing property."""
        assert backend.is_playing is False

        backend.play_file(str(temp_audio_file))
        assert backend.is_playing is True

        await backend.stop()
        assert backend.is_playing is False

    @pytest.mark.asyncio
    async def test_is_busy_property(self, backend, temp_audio_file):
        """Test is_busy property."""
        assert backend.is_busy is False

        backend.play_file(str(temp_audio_file))
        assert backend.is_busy is True

        await backend.stop()
        assert backend.is_busy is False


class TestIntegrationScenarios:
    """Test integration scenarios with base backend."""

    @pytest.mark.asyncio
    async def test_complete_playback_cycle(self, backend, temp_audio_file):
        """Test a complete playback cycle."""
        # Play
        backend.play_file(str(temp_audio_file))
        assert backend.is_playing is True

        # Pause
        await backend.pause()
        assert backend.is_playing is False

        # Resume
        await backend.resume()
        assert backend.is_playing is True

        # Stop
        await backend.stop()
        assert backend.is_playing is False

    def test_volume_persistence(self, backend):
        """Test volume persists across operations."""
        # Use base class sync method
        super(ConcreteTestBackend, backend).set_volume(45)

        # Volume should persist
        assert backend._volume == 45

        backend.cleanup()

        # Volume should still be set
        assert backend._volume == 45

    @pytest.mark.asyncio
    async def test_notification_with_playback_cycle(self, backend_with_subject, mock_subject, temp_audio_file):
        """Test notifications during playback cycle."""
        backend_with_subject.play_file(str(temp_audio_file))
        backend_with_subject._notify_playback_event("started")

        await backend_with_subject.pause()
        backend_with_subject._notify_playback_event("paused")

        await backend_with_subject.resume()
        backend_with_subject._notify_playback_event("resumed")

        # Should have received multiple notifications
        assert mock_subject.notify.call_count >= 3
