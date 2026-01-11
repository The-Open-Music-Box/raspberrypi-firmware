# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Comprehensive tests for headphone jack detection.

Tests cover:
- JackDetectionProtocol interface compliance
- MockJackDetection implementation
- GPIOJackDetection implementation (with mocked GPIO)
- JackDetectionFactory logic
- State change callbacks
- Lifecycle management (initialize/cleanup)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.src.domain.protocols.jack_detection_protocol import (
    JackDetectionProtocol,
    JackState,
)
from app.src.infrastructure.hardware.audio.mock_jack_detection import MockJackDetection


class TestJackState:
    """Test JackState enum."""

    def test_jack_state_values(self):
        """Test JackState enum has expected values."""
        assert JackState.DISCONNECTED.value == "disconnected"
        assert JackState.CONNECTED.value == "connected"
        assert JackState.UNKNOWN.value == "unknown"

    def test_jack_state_comparison(self):
        """Test JackState enum comparison."""
        assert JackState.CONNECTED != JackState.DISCONNECTED
        assert JackState.CONNECTED == JackState.CONNECTED


class TestMockJackDetection:
    """Test MockJackDetection implementation."""

    @pytest.fixture
    def mock_jack(self):
        """Create a MockJackDetection instance."""
        return MockJackDetection(enabled=True)

    @pytest.fixture
    def disabled_mock_jack(self):
        """Create a disabled MockJackDetection instance."""
        return MockJackDetection(enabled=False)

    def test_initial_state_unknown(self, mock_jack):
        """Test initial state is UNKNOWN."""
        assert mock_jack.get_state() == JackState.UNKNOWN

    def test_is_enabled(self, mock_jack, disabled_mock_jack):
        """Test is_enabled returns correct value."""
        assert mock_jack.is_enabled() is True
        assert disabled_mock_jack.is_enabled() is False

    def test_is_headphone_connected_initial(self, mock_jack):
        """Test is_headphone_connected returns False initially."""
        assert mock_jack.is_headphone_connected() is False

    @pytest.mark.asyncio
    async def test_initialize(self, mock_jack):
        """Test initialize sets state to DISCONNECTED."""
        result = await mock_jack.initialize()
        assert result is True
        assert mock_jack.get_state() == JackState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_jack):
        """Test cleanup succeeds."""
        await mock_jack.initialize()
        await mock_jack.cleanup()
        # Should not raise

    def test_simulate_connect(self, mock_jack):
        """Test simulate_connect changes state."""
        mock_jack.simulate_connect()
        assert mock_jack.get_state() == JackState.CONNECTED
        assert mock_jack.is_headphone_connected() is True

    def test_simulate_disconnect(self, mock_jack):
        """Test simulate_disconnect changes state."""
        mock_jack.simulate_connect()
        mock_jack.simulate_disconnect()
        assert mock_jack.get_state() == JackState.DISCONNECTED
        assert mock_jack.is_headphone_connected() is False

    def test_state_change_callback(self, mock_jack):
        """Test state change callback is called."""
        callback = Mock()
        mock_jack.set_state_change_handler(callback)

        mock_jack.simulate_connect()

        callback.assert_called_once_with(JackState.CONNECTED)

    def test_state_change_callback_on_disconnect(self, mock_jack):
        """Test state change callback is called on disconnect."""
        callback = Mock()
        mock_jack.set_state_change_handler(callback)

        mock_jack.simulate_connect()
        mock_jack.simulate_disconnect()

        assert callback.call_count == 2
        callback.assert_called_with(JackState.DISCONNECTED)

    def test_no_callback_if_state_unchanged(self, mock_jack):
        """Test callback not called if state doesn't change."""
        callback = Mock()
        mock_jack.set_state_change_handler(callback)

        mock_jack.simulate_connect()
        mock_jack.simulate_connect()  # Same state again

        # Should only be called once
        callback.assert_called_once()

    def test_get_status(self, mock_jack):
        """Test get_status returns expected structure."""
        status = mock_jack.get_status()

        assert "enabled" in status
        assert "state" in status
        assert "implementation" in status
        assert status["implementation"] == "mock"
        assert status["enabled"] is True

    def test_disabled_mock_state(self, disabled_mock_jack):
        """Test disabled mock has correct state."""
        assert disabled_mock_jack.is_enabled() is False
        # simulate_connect does NOT work when disabled (correct behavior)
        disabled_mock_jack.simulate_connect()
        # State remains UNKNOWN because simulation is disabled
        assert disabled_mock_jack.get_state() == JackState.UNKNOWN


class TestGPIOJackDetection:
    """Test GPIOJackDetection.

    Note: GPIOJackDetection uses gpiozero which may not be available on all
    platforms. These tests create the class directly since it handles
    GPIO unavailability gracefully.
    """

    @pytest.fixture
    def mock_hardware_config(self):
        """Create a mock hardware config."""
        config = MagicMock()
        config.gpio_headphone_detect = 26
        config.headphone_detect_enabled = True
        config.headphone_detect_debounce_ms = 300
        config.headphone_detect_active_low = True
        return config

    def test_gpio_jack_detection_creation(self, mock_hardware_config):
        """Test GPIOJackDetection can be created (graceful degradation)."""
        from app.src.infrastructure.hardware.audio.gpio_jack_detection import (
            GPIOJackDetection,
        )

        jack = GPIOJackDetection(mock_hardware_config)
        assert jack is not None
        # Should be enabled in config, even if GPIO is not available
        assert jack.is_enabled() is True

    @pytest.mark.asyncio
    async def test_gpio_initialize_graceful_degradation(self, mock_hardware_config):
        """Test GPIOJackDetection initializes gracefully when GPIO unavailable."""
        from app.src.infrastructure.hardware.audio.gpio_jack_detection import (
            GPIOJackDetection,
        )

        jack = GPIOJackDetection(mock_hardware_config)
        # Should succeed even without GPIO hardware
        result = await jack.initialize()
        assert result is True

    def test_gpio_get_status_structure(self, mock_hardware_config):
        """Test GPIOJackDetection get_status returns expected fields."""
        from app.src.infrastructure.hardware.audio.gpio_jack_detection import (
            GPIOJackDetection,
        )

        jack = GPIOJackDetection(mock_hardware_config)
        status = jack.get_status()

        assert "enabled" in status
        assert "gpio_pin" in status
        assert status["gpio_pin"] == 26
        assert "gpio_available" in status
        assert "debounce_ms" in status


class TestJackDetectionFactory:
    """Test JackDetectionFactory."""

    @pytest.fixture
    def mock_config_mock_mode(self):
        """Create config for mock hardware mode."""
        config = MagicMock()
        config.mock_hardware = True
        config.headphone_detect_enabled = True
        config.gpio_headphone_detect = 26
        config.headphone_detect_debounce_ms = 300
        config.headphone_detect_active_low = True
        return config

    @pytest.fixture
    def mock_config_disabled(self):
        """Create config with disabled jack detection."""
        config = MagicMock()
        config.mock_hardware = False
        config.headphone_detect_enabled = False
        return config

    def test_factory_creates_mock_in_mock_mode(self, mock_config_mock_mode):
        """Test factory creates MockJackDetection in mock mode."""
        from app.src.infrastructure.hardware.audio.jack_detection_factory import (
            JackDetectionFactory,
        )

        jack = JackDetectionFactory.create(mock_config_mock_mode)

        assert isinstance(jack, MockJackDetection)
        assert jack.is_enabled() is True

    def test_factory_creates_disabled_mock_when_disabled(self, mock_config_disabled):
        """Test factory creates disabled mock when detection is disabled."""
        from app.src.infrastructure.hardware.audio.jack_detection_factory import (
            JackDetectionFactory,
        )

        jack = JackDetectionFactory.create(mock_config_disabled)

        assert isinstance(jack, MockJackDetection)
        assert jack.is_enabled() is False

    @patch.dict("os.environ", {"USE_MOCK_HARDWARE": "true"})
    def test_factory_respects_env_var(self, mock_config_mock_mode):
        """Test factory respects USE_MOCK_HARDWARE environment variable."""
        mock_config_mock_mode.mock_hardware = False

        from app.src.infrastructure.hardware.audio.jack_detection_factory import (
            JackDetectionFactory,
        )

        jack = JackDetectionFactory.create(mock_config_mock_mode)

        assert isinstance(jack, MockJackDetection)


class TestJackDetectionIntegration:
    """Integration tests for jack detection."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full jack detection lifecycle."""
        jack = MockJackDetection(enabled=True)

        # Initialize
        result = await jack.initialize()
        assert result is True
        assert jack.get_state() == JackState.DISCONNECTED

        # Connect headphones
        jack.simulate_connect()
        assert jack.is_headphone_connected() is True

        # Disconnect headphones
        jack.simulate_disconnect()
        assert jack.is_headphone_connected() is False

        # Cleanup
        await jack.cleanup()

    @pytest.mark.asyncio
    async def test_callback_chain(self):
        """Test callback receives all state changes."""
        jack = MockJackDetection(enabled=True)
        states_received = []

        def callback(state):
            states_received.append(state)

        jack.set_state_change_handler(callback)

        await jack.initialize()
        jack.simulate_connect()
        jack.simulate_disconnect()
        jack.simulate_connect()

        assert len(states_received) == 3
        assert states_received[0] == JackState.CONNECTED
        assert states_received[1] == JackState.DISCONNECTED
        assert states_received[2] == JackState.CONNECTED


class TestHeadphoneBroadcasting:
    """Test headphone status broadcasting setup."""

    @pytest.fixture
    def mock_socketio(self):
        """Create a mock Socket.IO server."""
        socketio = MagicMock()
        socketio.emit = AsyncMock()
        return socketio

    def test_setup_headphone_broadcasting_success(self, mock_socketio):
        """Test setup_headphone_broadcasting returns True on success."""
        mock_container = MagicMock()
        mock_container.is_initialized = True
        mock_backend = MagicMock()
        mock_backend.set_headphone_state_change_callback = MagicMock()
        mock_container.backend = mock_backend

        with patch(
            "app.src.domain.audio.container.audio_domain_container",
            mock_container
        ):
            from app.src.domain.audio.backends.implementations.audio_factory import (
                setup_headphone_broadcasting,
            )

            result = setup_headphone_broadcasting(mock_socketio)

            assert result is True
            mock_backend.set_headphone_state_change_callback.assert_called_once()

    def test_setup_headphone_broadcasting_not_initialized(self, mock_socketio):
        """Test setup returns False when audio not initialized."""
        mock_container = MagicMock()
        mock_container.is_initialized = False

        with patch(
            "app.src.domain.audio.container.audio_domain_container",
            mock_container
        ):
            from app.src.domain.audio.backends.implementations.audio_factory import (
                setup_headphone_broadcasting,
            )

            result = setup_headphone_broadcasting(mock_socketio)

            assert result is False

    def test_setup_headphone_broadcasting_no_callback_support(self, mock_socketio):
        """Test setup returns False when backend doesn't support callback."""
        mock_container = MagicMock()
        mock_container.is_initialized = True
        mock_container.backend = MagicMock(spec=[])  # No attributes

        with patch(
            "app.src.domain.audio.container.audio_domain_container",
            mock_container
        ):
            from app.src.domain.audio.backends.implementations.audio_factory import (
                setup_headphone_broadcasting,
            )

            result = setup_headphone_broadcasting(mock_socketio)

            assert result is False


class TestSocketEventsHeadphone:
    """Test Socket.IO event types for headphone status."""

    def test_headphone_status_event_type_exists(self):
        """Test STATE_HEADPHONE_STATUS event type exists."""
        from app.src.common.socket_events import SocketEventType

        assert hasattr(SocketEventType, "STATE_HEADPHONE_STATUS")
        assert SocketEventType.STATE_HEADPHONE_STATUS.value == "state:headphone_status"

    def test_headphone_status_state_event_type_exists(self):
        """Test HEADPHONE_STATUS in StateEventType."""
        from app.src.common.socket_events import StateEventType

        assert hasattr(StateEventType, "HEADPHONE_STATUS")
        assert StateEventType.HEADPHONE_STATUS.value == "state:headphone_status"

    def test_headphone_status_payload_model(self):
        """Test HeadphoneStatusPayload model."""
        from app.src.common.socket_events import HeadphoneStatusPayload

        payload = HeadphoneStatusPayload(connected=True, server_seq=1)

        assert payload.connected is True
        assert payload.server_seq == 1
        assert payload.timestamp > 0

    def test_headphone_status_event_builder(self):
        """Test SocketEventBuilder.create_headphone_status_event."""
        from app.src.common.socket_events import SocketEventBuilder

        event_data = SocketEventBuilder.create_headphone_status_event(
            connected=True, server_seq=42
        )

        assert event_data["connected"] is True
        assert event_data["server_seq"] == 42
        assert "timestamp" in event_data

    def test_headphone_event_room_mapping(self):
        """Test headphone status event room mapping."""
        from app.src.common.socket_events import EVENT_ROOM_MAPPING, SocketEventType

        room = EVENT_ROOM_MAPPING.get(SocketEventType.STATE_HEADPHONE_STATUS)
        assert room == "playlists"
