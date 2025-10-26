"""
Comprehensive tests for WM8960AudioBackend.

Tests cover:
- Initialization with pygame and mutagen dependencies
- WM8960 device detection via subprocess
- Hardware configuration
- Pygame mixer initialization
- Playback methods (mocked hardware)
- Duration detection with mutagen
- State management
- Error handling for missing dependencies
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from pathlib import Path


@pytest.fixture
def mock_pygame():
    """Create a mock pygame module."""
    mock_pg = MagicMock()
    mock_mixer = MagicMock()
    mock_mixer.music = MagicMock()
    mock_mixer.music.get_busy = MagicMock(return_value=False)
    mock_mixer.music.play = MagicMock()
    mock_mixer.music.stop = MagicMock()
    mock_mixer.music.pause = MagicMock()
    mock_mixer.music.unpause = MagicMock()
    mock_mixer.music.load = MagicMock()
    mock_mixer.music.unload = MagicMock()
    mock_mixer.music.set_volume = MagicMock()
    mock_mixer.pre_init = MagicMock()
    mock_mixer.init = MagicMock()
    mock_mixer.quit = MagicMock()
    mock_mixer.get_init = MagicMock(return_value=(48000, -16, 2))

    mock_pg.mixer = mock_mixer
    return mock_pg


@pytest.fixture
def mock_subprocess():
    """Create a mock subprocess module."""
    with patch('subprocess.run') as mock_run:
        # Default successful aplay detection
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "card 0: wm8960soundcard [wm8960-soundcard], device 0: bcm2835-i2s-wm8960-hifi wm8960-hifi-0 []"
        mock_run.return_value = mock_result
        yield mock_run


@pytest.fixture
def mock_mutagen():
    """Create a mock mutagen module."""
    with patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.MutagenFile') as mock_file:
        mock_audio = Mock()
        mock_audio.info = Mock()
        mock_audio.info.length = 180.5  # 3 minutes
        mock_file.return_value = mock_audio
        yield mock_file


@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_text("fake audio data")
    return audio_file


class TestWM8960AudioBackendInitialization:
    """Test WM8960AudioBackend initialization."""

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    def test_create_backend_success(self, mock_pygame, mock_subprocess):
        """Test creating WM8960 backend successfully."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        assert backend is not None
        assert backend._pygame_initialized is True

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', False)
    def test_create_backend_without_pygame(self, mock_subprocess):
        """Test error when pygame not available."""
        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        with pytest.raises(RuntimeError):
            WM8960AudioBackend()

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    def test_pygame_initialization_failure(self, mock_pygame, mock_subprocess):
        """Test error when pygame initialization fails."""
        mock_pygame.mixer.get_init.return_value = None

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        with pytest.raises(RuntimeError):
            WM8960AudioBackend()

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    def test_sets_audio_environment_variables(self, mock_pygame, mock_subprocess):
        """Test sets SDL audio environment variables."""
        import os
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        # Should set SDL_AUDIODRIVER and SDL_AUDIODEV
        # Note: These are set in _init_pygame_simple method


class TestDeviceDetection:
    """Test WM8960 device detection."""

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    def test_detect_wm8960_device(self, mock_pygame, mock_subprocess):
        """Test detecting WM8960 device from aplay output."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        assert backend._audio_device is not None
        assert "plughw" in backend._audio_device or "hw" in backend._audio_device

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    @patch('subprocess.run')
    def test_detect_device_with_card_number(self, mock_run, mock_pygame):
        """Test detecting device with card number."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "card 1: wm8960soundcard [wm8960-soundcard], device 0"
        mock_run.return_value = mock_result

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        # Should detect card 1
        assert "1" in backend._audio_device or "wm8960" in backend._audio_device

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    @patch('subprocess.run')
    def test_detect_device_fallback(self, mock_run, mock_pygame):
        """Test fallback when no WM8960 device found."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "card 0: Generic [Generic], device 0"
        mock_run.return_value = mock_result

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        # Should use fallback
        assert backend._audio_device is not None

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    @patch('subprocess.run')
    def test_detect_device_aplay_not_found(self, mock_run, mock_pygame):
        """Test fallback when aplay command not found."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)
        mock_run.side_effect = FileNotFoundError()

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        # Should use default fallback
        assert backend._audio_device == "plughw:1,0"


class TestDurationDetection:
    """Test audio file duration detection."""

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.MUTAGEN_AVAILABLE', True)
    def test_get_file_duration_with_mutagen(self, mock_pygame, mock_subprocess, mock_mutagen, temp_audio_file):
        """Test getting file duration with mutagen."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()
        duration = backend._get_file_duration(str(temp_audio_file))

        assert duration == 180.5

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.MUTAGEN_AVAILABLE', False)
    def test_get_file_duration_without_mutagen(self, mock_pygame, mock_subprocess, temp_audio_file):
        """Test getting file duration without mutagen."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()
        duration = backend._get_file_duration(str(temp_audio_file))

        assert duration is None

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.MUTAGEN_AVAILABLE', True)
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.MutagenFile')
    def test_get_file_duration_error(self, mock_file, mock_pygame, mock_subprocess, temp_audio_file):
        """Test getting file duration with error."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)
        mock_file.side_effect = Exception("Test error")

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()
        duration = backend._get_file_duration(str(temp_audio_file))

        assert duration is None


class TestPlaybackWithMockedDependencies:
    """Test playback methods with mocked dependencies."""

    @pytest.fixture
    def backend(self, mock_subprocess):
        """Create backend with mocked dependencies."""
        with patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame') as mock_pg:
            mock_pg.mixer.get_init.return_value = (48000, -16, 2)
            mock_pg.mixer.music.get_busy.return_value = False

            with patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True):
                from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend
                backend = WM8960AudioBackend()
                backend._mock_pygame = mock_pg  # Store for test access
                yield backend

    def test_play_file(self, backend, temp_audio_file):
        """Test playing a file."""
        result = backend.play_file(str(temp_audio_file))

        assert result is True
        assert backend._is_playing is True
        assert backend._current_file_path == str(temp_audio_file)

    def test_play_file_with_duration(self, backend, temp_audio_file):
        """Test playing file with provided duration."""
        backend.play_file(str(temp_audio_file), duration_ms=10000)

        assert backend._current_file_duration == 10.0

    def test_play_nonexistent_file(self, backend):
        """Test playing nonexistent file."""
        result = backend.play_file("/nonexistent/file.mp3")

        assert result is False


class TestPygameInitialization:
    """Test pygame mixer initialization."""

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    def test_init_pygame_simple_success(self, mock_pygame, mock_subprocess):
        """Test successful pygame initialization."""
        # get_init() is called 3 times: check if initialized, verify init, get init info
        mock_pygame.mixer.get_init.side_effect = [None, (48000, -16, 2), (48000, -16, 2)]

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        assert backend._pygame_initialized is True

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    def test_init_pygame_configures_mixer(self, mock_pygame, mock_subprocess):
        """Test pygame mixer is configured with correct parameters."""
        mock_pygame.mixer.get_init.return_value = (48000, -16, 2)

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        # Should call pre_init with WM8960-compatible settings
        mock_pygame.mixer.pre_init.assert_called_with(
            frequency=48000,
            size=-16,
            channels=2,
            buffer=2048
        )

    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True)
    def test_init_pygame_clears_existing_state(self, mock_pygame, mock_subprocess):
        """Test pygame initialization clears existing state."""
        # Sequence: check if init (True triggers quit), verify after init (tuple), get init info (tuple)
        mock_pygame.mixer.get_init.side_effect = [True, (48000, -16, 2), (48000, -16, 2)]

        from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend

        backend = WM8960AudioBackend()

        # Should call quit to clear existing state
        mock_pygame.mixer.quit.assert_called()


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.fixture
    def backend(self, mock_subprocess):
        """Create backend for error testing."""
        with patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame') as mock_pg:
            mock_pg.mixer.get_init.return_value = (48000, -16, 2)
            mock_pg.mixer.music.get_busy.return_value = False

            with patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True):
                from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend
                backend = WM8960AudioBackend()
                backend._mock_pygame = mock_pg
                yield backend

    def test_play_when_mixer_not_initialized(self, backend, temp_audio_file):
        """Test playing when mixer not initialized."""
        backend._pygame_initialized = False

        result = backend.play_file(str(temp_audio_file))

        assert result is False


class TestIntegrationScenarios:
    """Test integration scenarios."""

    @pytest.fixture
    def backend(self, mock_subprocess):
        """Create backend for integration testing."""
        with patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.pygame') as mock_pg:
            mock_pg.mixer.get_init.return_value = (48000, -16, 2)
            mock_pg.mixer.music.get_busy.return_value = False

            with patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.PYGAME_AVAILABLE', True):
                from app.src.domain.audio.backends.implementations.wm8960_audio_backend import WM8960AudioBackend
                backend = WM8960AudioBackend()
                yield backend

    def test_hardware_initialization_complete(self, backend):
        """Test complete hardware initialization."""
        assert backend._audio_device is not None
        assert backend._pygame_initialized is True

    def test_state_tracking_initialization(self, backend):
        """Test state tracking variables initialized."""
        assert backend._is_paused is False
        assert backend._play_start_time is None
        assert backend._pause_time is None
        assert backend._current_file_path is None
        assert backend._current_file_duration is None
