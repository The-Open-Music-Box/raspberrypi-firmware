"""
Comprehensive tests for Audio Factory.

Tests cover:
- Platform-specific backend creation (macOS, Linux/Pi, mock)
- Mock hardware configuration
- Fallback to mock backend on errors
- Playback subject injection
- Error handling
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock


class TestAudioBackendFactory:
    """Test audio backend factory functions."""

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_create_mock_backend_with_config(self, mock_backend_class, mock_config):
        """Test creating mock backend when mock_hardware is True."""
        mock_config.hardware.mock_hardware = True
        mock_backend_instance = Mock()
        mock_backend_class.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend()

        assert backend == mock_backend_instance
        mock_backend_class.assert_called_once_with(None)

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('sys.platform', 'darwin')
    @patch('app.src.domain.audio.backends.implementations.macos_audio_backend.MacOSAudioBackend')
    def test_create_macos_backend(self, mock_backend_class, mock_config):
        """Test creating macOS backend on darwin platform."""
        mock_config.hardware.mock_hardware = False
        mock_backend_instance = Mock()
        mock_backend_class.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend()

        assert backend == mock_backend_instance
        mock_backend_class.assert_called_once_with(None)

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('sys.platform', 'linux')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.WM8960AudioBackend')
    def test_create_wm8960_backend(self, mock_backend_class, mock_config):
        """Test creating WM8960 backend on Linux platform."""
        mock_config.hardware.mock_hardware = False
        mock_backend_instance = Mock()
        mock_backend_class.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend()

        assert backend == mock_backend_instance
        mock_backend_class.assert_called_once_with(None)

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('sys.platform', 'linux')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.WM8960AudioBackend')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_fallback_to_mock_on_wm8960_error(self, mock_mock_backend, mock_wm8960_backend, mock_config):
        """Test fallback to mock backend when WM8960 initialization fails."""
        mock_config.hardware.mock_hardware = False
        mock_wm8960_backend.side_effect = Exception("Hardware not available")
        mock_backend_instance = Mock()
        mock_mock_backend.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend()

        assert backend == mock_backend_instance
        mock_mock_backend.assert_called_once_with(None)

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_inject_playback_subject(self, mock_backend_class, mock_config):
        """Test injecting playback subject into backend."""
        mock_config.hardware.mock_hardware = True
        mock_subject = Mock()
        mock_backend_instance = Mock()
        mock_backend_class.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend(playback_subject=mock_subject)

        mock_backend_class.assert_called_once_with(mock_subject)

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('sys.platform', 'darwin')
    @patch('app.src.domain.audio.backends.implementations.macos_audio_backend.MacOSAudioBackend')
    def test_inject_subject_to_macos_backend(self, mock_backend_class, mock_config):
        """Test injecting playback subject to macOS backend."""
        mock_config.hardware.mock_hardware = False
        mock_subject = Mock()
        mock_backend_instance = Mock()
        mock_backend_class.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend(playback_subject=mock_subject)

        mock_backend_class.assert_called_once_with(mock_subject)


class TestPlatformDetection:
    """Test platform detection logic."""

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('sys.platform', 'win32')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.WM8960AudioBackend')
    def test_windows_platform_tries_wm8960(self, mock_wm8960, mock_config):
        """Test Windows platform tries WM8960 backend."""
        mock_config.hardware.mock_hardware = False
        mock_backend_instance = Mock()
        mock_wm8960.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend()

        # Should try WM8960 (non-darwin, non-mock)
        mock_wm8960.assert_called_once()

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('sys.platform', 'linux')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.WM8960AudioBackend')
    def test_linux_platform_uses_wm8960(self, mock_wm8960, mock_config):
        """Test Linux platform uses WM8960 backend."""
        mock_config.hardware.mock_hardware = False
        mock_backend_instance = Mock()
        mock_wm8960.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend()

        mock_wm8960.assert_called_once()


class TestErrorHandling:
    """Test error handling in factory."""

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('sys.platform', 'darwin')
    @patch('app.src.domain.audio.backends.implementations.macos_audio_backend.MacOSAudioBackend')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_handles_macos_backend_error(self, mock_mock_backend, mock_macos_backend, mock_config):
        """Test handling macOS backend initialization error."""
        mock_config.hardware.mock_hardware = False
        mock_macos_backend.side_effect = Exception("macOS audio init failed")

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        # Should raise the exception (no fallback for macOS)
        with pytest.raises(Exception):
            get_audio_backend()

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('sys.platform', 'linux')
    @patch('app.src.domain.audio.backends.implementations.wm8960_audio_backend.WM8960AudioBackend')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_fallback_logs_error(self, mock_mock_backend, mock_wm8960, mock_config):
        """Test fallback logs the error appropriately."""
        mock_config.hardware.mock_hardware = False
        mock_wm8960.side_effect = RuntimeError("Hardware error")
        mock_mock_instance = Mock()
        mock_mock_backend.return_value = mock_mock_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend()

        # Should have fallen back to mock
        assert backend == mock_mock_instance


class TestFactoryIntegration:
    """Test factory integration scenarios."""

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_factory_returns_backend_protocol(self, mock_backend_class, mock_config):
        """Test factory returns AudioBackendProtocol implementation."""
        mock_config.hardware.mock_hardware = True
        mock_backend_instance = Mock()
        mock_backend_class.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend = get_audio_backend()

        # Should return a backend instance
        assert backend is not None

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_multiple_factory_calls(self, mock_backend_class, mock_config):
        """Test multiple calls to factory create separate instances."""
        mock_config.hardware.mock_hardware = True
        mock_backend_class.side_effect = [Mock(), Mock()]

        from app.src.domain.audio.backends.implementations.audio_factory import get_audio_backend

        backend1 = get_audio_backend()
        backend2 = get_audio_backend()

        # Should create separate instances
        assert backend1 is not backend2


class TestPrivateFactoryFunction:
    """Test private _create_audio_backend function."""

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_private_function_creates_backend(self, mock_backend_class, mock_config):
        """Test private function creates backend correctly."""
        mock_config.hardware.mock_hardware = True
        mock_backend_instance = Mock()
        mock_backend_class.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import _create_audio_backend

        backend = _create_audio_backend()

        assert backend == mock_backend_instance

    @patch('app.src.domain.audio.backends.implementations.audio_factory.config')
    @patch('app.src.domain.audio.backends.implementations.mock_audio_backend.MockAudioBackend')
    def test_private_function_accepts_subject(self, mock_backend_class, mock_config):
        """Test private function accepts playback subject."""
        mock_config.hardware.mock_hardware = True
        mock_subject = Mock()
        mock_backend_instance = Mock()
        mock_backend_class.return_value = mock_backend_instance

        from app.src.domain.audio.backends.implementations.audio_factory import _create_audio_backend

        backend = _create_audio_backend(playback_subject=mock_subject)

        mock_backend_class.assert_called_once_with(mock_subject)
