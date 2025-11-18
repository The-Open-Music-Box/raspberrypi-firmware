# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Tests for MDNSService

Comprehensive tests for the mDNS/Bonjour service including registration,
unregistration, IP detection, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import socket
import sys

# Mock zeroconf module before importing MDNSService
mock_zeroconf = MagicMock()
mock_zeroconf.IPVersion = MagicMock()
mock_zeroconf.ServiceInfo = MagicMock()
mock_zeroconf.Zeroconf = MagicMock()
sys.modules['zeroconf'] = mock_zeroconf

# Import the actual decorator
from app.src.services.error.unified_error_decorator import handle_service_errors

# Now import MDNSService - the decorator will be available
from app.src.services.mdns_service import MDNSService


class TestMDNSService:
    """Test suite for MDNSService."""

    @pytest.fixture
    def mock_config(self):
        """Mock application config."""
        with patch('app.src.config.config') as mock_cfg:
            mock_cfg.socketio_port = 8000
            mock_cfg.mdns_service_type = "_http._tcp.local."
            mock_cfg.mdns_service_name = "OpenMusicBox._http._tcp.local."
            mock_cfg.mdns_service_path = "/api"
            mock_cfg.mdns_service_version = "1.0.0"
            mock_cfg.mdns_service_friendly_name = "OpenMusicBox"
            mock_cfg.mdns_service_hostname = "openmusicbox.local."
            yield mock_cfg

    @pytest.fixture
    def mdns_service(self, mock_config):
        """Create MDNSService instance."""
        return MDNSService()

    # ================================================================================
    # Test __init__()
    # ================================================================================

    def test_init_sets_config(self, mock_config):
        """Test initialization sets config correctly."""
        # Act
        service = MDNSService()

        # Assert
        assert service.config == mock_config

    def test_init_sets_zeroconf_instance_none(self, mock_config):
        """Test initialization sets zeroconf_instance to None."""
        # Act
        service = MDNSService()

        # Assert
        assert service.zeroconf_instance is None

    def test_init_sets_service_info_none(self, mock_config):
        """Test initialization sets service_info to None."""
        # Act
        service = MDNSService()

        # Assert
        assert service.service_info is None

    def test_init_sets_is_registered_false(self, mock_config):
        """Test initialization sets _is_registered to False."""
        # Act
        service = MDNSService()

        # Assert
        assert service._is_registered is False

    # ================================================================================
    # Test _get_local_ip()
    # ================================================================================

    def test_get_local_ip_success(self, mdns_service):
        """Test successful IP address retrieval."""
        # Arrange
        mock_socket = MagicMock()
        mock_socket.getsockname.return_value = ("192.168.1.100", 12345)

        with patch('socket.socket', return_value=mock_socket):
            # Act
            ip = mdns_service._get_local_ip()

            # Assert
            assert ip == "192.168.1.100"
            mock_socket.connect.assert_called_once_with(("8.8.8.8", 80))
            mock_socket.close.assert_called_once()

    def test_get_local_ip_socket_error(self, mdns_service):
        """Test IP retrieval when socket error occurs."""
        # Arrange
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = OSError("Network unreachable")

        with patch('socket.socket', return_value=mock_socket):
            # Act
            ip = mdns_service._get_local_ip()

            # Assert
            assert ip is None
            mock_socket.close.assert_called_once()

    def test_get_local_ip_exception(self, mdns_service):
        """Test IP retrieval when general exception occurs."""
        # Arrange
        with patch('socket.socket', side_effect=Exception("Socket creation failed")):
            # Act
            ip = mdns_service._get_local_ip()

            # Assert
            assert ip is None

    # ================================================================================
    # Test register_service()
    # ================================================================================

    @patch('app.src.services.mdns_service.Zeroconf')
    @patch('app.src.services.mdns_service.ServiceInfo')
    @patch('socket.inet_aton')
    def test_register_service_success(self, mock_inet_aton, mock_service_info_class, mock_zeroconf_class, mdns_service):
        """Test successful service registration."""
        # Arrange
        mock_zeroconf_instance = MagicMock()
        mock_zeroconf_class.return_value = mock_zeroconf_instance
        mock_service_info = MagicMock()
        mock_service_info_class.return_value = mock_service_info
        mock_inet_aton.return_value = b'\xc0\xa8\x01d'  # 192.168.1.100

        with patch.object(mdns_service, '_get_local_ip', return_value="192.168.1.100"):
            # Act
            result = mdns_service.register_service()

            # Assert
            assert result is True
            assert mdns_service._is_registered is True
            assert mdns_service.zeroconf_instance == mock_zeroconf_instance
            assert mdns_service.service_info == mock_service_info
            mock_zeroconf_instance.register_service.assert_called_once_with(mock_service_info)

    def test_register_service_no_ip(self, mdns_service):
        """Test service registration when IP cannot be determined."""
        # Arrange
        with patch.object(mdns_service, '_get_local_ip', return_value=None):
            # Act
            result = mdns_service.register_service()

            # Assert
            assert result is False
            assert mdns_service._is_registered is False

    @patch('app.src.services.mdns_service.Zeroconf')
    @patch('app.src.services.mdns_service.ServiceInfo')
    @patch('socket.inet_aton')
    def test_register_service_uses_existing_zeroconf(self, mock_inet_aton, mock_service_info_class, mock_zeroconf_class, mdns_service):
        """Test that registration uses existing zeroconf instance if available."""
        # Arrange
        existing_zeroconf = MagicMock()
        mdns_service.zeroconf_instance = existing_zeroconf
        mock_service_info = MagicMock()
        mock_service_info_class.return_value = mock_service_info
        mock_inet_aton.return_value = b'\xc0\xa8\x01d'

        with patch.object(mdns_service, '_get_local_ip', return_value="192.168.1.100"):
            # Act
            result = mdns_service.register_service()

            # Assert
            assert result is True
            assert mdns_service.zeroconf_instance == existing_zeroconf
            mock_zeroconf_class.assert_not_called()  # Should not create new instance

    @patch('app.src.services.mdns_service.Zeroconf')
    @patch('app.src.services.mdns_service.ServiceInfo')
    @patch('socket.inet_aton')
    def test_register_service_creates_service_info_correctly(self, mock_inet_aton, mock_service_info_class, mock_zeroconf_class, mdns_service):
        """Test that ServiceInfo is created with correct parameters."""
        # Arrange
        mock_zeroconf_instance = MagicMock()
        mock_zeroconf_class.return_value = mock_zeroconf_instance
        mock_service_info = MagicMock()
        mock_service_info_class.return_value = mock_service_info
        mock_inet_aton.return_value = b'\xc0\xa8\x01d'

        with patch.object(mdns_service, '_get_local_ip', return_value="192.168.1.100"):
            # Act
            result = mdns_service.register_service()

            # Assert
            assert result is True
            mock_service_info_class.assert_called_once()
            call_kwargs = mock_service_info_class.call_args[1]
            assert call_kwargs["port"] == 8000
            assert call_kwargs["weight"] == 0
            assert call_kwargs["priority"] == 0
            assert "path" in call_kwargs["properties"]
            assert "version" in call_kwargs["properties"]
            assert "name" in call_kwargs["properties"]

    # ================================================================================
    # Test unregister_service()
    # ================================================================================

    def test_unregister_service_when_not_registered(self, mdns_service):
        """Test unregistering when service was never registered."""
        # Arrange
        mdns_service._is_registered = False

        # Act
        result = mdns_service.unregister_service()

        # Assert
        assert result is True

    def test_unregister_service_when_no_zeroconf_instance(self, mdns_service):
        """Test unregistering when zeroconf instance is None."""
        # Arrange
        mdns_service._is_registered = True
        mdns_service.zeroconf_instance = None

        # Act
        result = mdns_service.unregister_service()

        # Assert
        assert result is True

    def test_unregister_service_success(self, mdns_service):
        """Test successful service unregistration."""
        # Arrange
        mock_zeroconf = MagicMock()
        mock_service_info = MagicMock()
        mdns_service.zeroconf_instance = mock_zeroconf
        mdns_service.service_info = mock_service_info
        mdns_service._is_registered = True

        with patch.object(mdns_service, '_cleanup_zeroconf') as mock_cleanup:
            # Act
            result = mdns_service.unregister_service()

            # Assert
            assert result is True
            mock_zeroconf.unregister_service.assert_called_once_with(mock_service_info)
            mock_cleanup.assert_called_once()

    def test_unregister_service_no_service_info(self, mdns_service):
        """Test unregistering when service_info is None."""
        # Arrange
        mock_zeroconf = MagicMock()
        mdns_service.zeroconf_instance = mock_zeroconf
        mdns_service.service_info = None
        mdns_service._is_registered = True

        with patch.object(mdns_service, '_cleanup_zeroconf') as mock_cleanup:
            # Act
            result = mdns_service.unregister_service()

            # Assert
            assert result is True
            mock_zeroconf.unregister_service.assert_not_called()
            mock_cleanup.assert_called_once()

    # ================================================================================
    # Test _cleanup_zeroconf()
    # ================================================================================

    def test_cleanup_zeroconf_with_instance(self, mdns_service):
        """Test cleanup when zeroconf instance exists."""
        # Arrange
        mock_zeroconf = MagicMock()
        mdns_service.zeroconf_instance = mock_zeroconf

        # Act
        mdns_service._cleanup_zeroconf()

        # Assert
        mock_zeroconf.close.assert_called_once()

    def test_cleanup_zeroconf_without_instance(self, mdns_service):
        """Test cleanup when zeroconf instance is None."""
        # Arrange
        mdns_service.zeroconf_instance = None

        # Act (should not raise exception)
        mdns_service._cleanup_zeroconf()

        # Assert - no exception raised

    # ================================================================================
    # Test integration scenarios
    # ================================================================================

    @patch('app.src.services.mdns_service.Zeroconf')
    @patch('app.src.services.mdns_service.ServiceInfo')
    @patch('socket.inet_aton')
    def test_register_then_unregister(self, mock_inet_aton, mock_service_info_class, mock_zeroconf_class, mdns_service):
        """Test complete registration and unregistration cycle."""
        # Arrange
        mock_zeroconf_instance = MagicMock()
        mock_zeroconf_class.return_value = mock_zeroconf_instance
        mock_service_info = MagicMock()
        mock_service_info_class.return_value = mock_service_info
        mock_inet_aton.return_value = b'\xc0\xa8\x01d'

        # Act - Register
        with patch.object(mdns_service, '_get_local_ip', return_value="192.168.1.100"):
            register_result = mdns_service.register_service()

        # Act - Unregister
        unregister_result = mdns_service.unregister_service()

        # Assert
        assert register_result is True
        assert unregister_result is True
        mock_zeroconf_instance.register_service.assert_called_once_with(mock_service_info)
        mock_zeroconf_instance.unregister_service.assert_called_once_with(mock_service_info)
        mock_zeroconf_instance.close.assert_called_once()
