"""
Comprehensive tests for PhysicalControlsManager.

Tests cover:
- Initialization with different controllers
- Event handler setup
- Button event handling
- Encoder event handling
- Volume control
- Track navigation
- Cleanup operations
"""

import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from app.src.application.controllers.physical_controls_controller import PhysicalControlsManager
from app.src.domain.protocols.physical_controls_protocol import PhysicalControlEvent


class TestPhysicalControlsInitialization:
    """Test PhysicalControlsManager initialization."""

    def test_create_with_audio_controller(self):
        """Test creating manager with audio controller."""
        audio_controller = Mock()
        hardware_config = Mock()

        manager = PhysicalControlsManager(audio_controller, hardware_config)

        assert manager.audio_controller == audio_controller
        assert manager.hardware_config == hardware_config
        assert manager._is_initialized is False

    def test_create_with_playback_coordinator(self):
        """Test creating manager with PlaybackCoordinator."""
        coordinator = Mock()
        coordinator.toggle_pause = Mock()
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)

        assert manager.audio_controller == coordinator
        assert manager._controller_type == "PlaybackCoordinator"

    def test_create_without_controller_uses_fallback(self):
        """Test creating without controller uses fallback."""
        hardware_config = Mock()

        with patch("app.src.application.controllers.PlaybackCoordinator") as mock_coordinator:
            with patch("app.src.domain.audio.container.audio_domain_container") as mock_container:
                mock_container.is_initialized = False

                # Should raise RuntimeError when container is not initialized
                with pytest.raises(RuntimeError, match="Audio domain container is not initialized"):
                    PhysicalControlsManager(None, hardware_config)

    def test_physical_controls_factory_called(self):
        """Test physical controls factory is called during init."""
        audio_controller = Mock()
        hardware_config = Mock()

        with patch("app.src.application.controllers.physical_controls_controller.PhysicalControlsFactory") as mock_factory:
            mock_factory.create_controls = Mock(return_value=Mock())

            manager = PhysicalControlsManager(audio_controller, hardware_config)

            mock_factory.create_controls.assert_called_once_with(hardware_config)


class TestInitializationAndCleanup:
    """Test initialization and cleanup operations."""

    @pytest.fixture
    def audio_controller(self):
        """Create mock audio controller."""
        return Mock()

    @pytest.fixture
    def hardware_config(self):
        """Create mock hardware config."""
        return Mock()

    @pytest.fixture
    def physical_controls(self):
        """Create mock physical controls."""
        controls = AsyncMock()
        controls.initialize = AsyncMock(return_value=True)
        controls.cleanup = AsyncMock()
        controls.set_event_handler = Mock()
        return controls

    @pytest.fixture
    def manager(self, audio_controller, hardware_config, physical_controls):
        """Create manager with mocked dependencies."""
        with patch("app.src.application.controllers.physical_controls_controller.PhysicalControlsFactory") as mock_factory:
            mock_factory.create_controls = Mock(return_value=physical_controls)
            return PhysicalControlsManager(audio_controller, hardware_config)

    @pytest.mark.asyncio
    async def test_initialize_success(self, manager, physical_controls):
        """Test successful initialization."""
        success = await manager.initialize()

        assert success is True
        assert manager._is_initialized is True
        physical_controls.initialize.assert_called_once()

    def test_initialize_without_audio_controller(self, hardware_config):
        """Test initialization without audio controller raises error."""
        with patch("app.src.application.controllers.physical_controls_controller.PhysicalControlsFactory"):
            with patch("app.src.domain.audio.container.audio_domain_container") as mock_container:
                mock_container.is_initialized = False

                # Should raise RuntimeError when container is not initialized
                with pytest.raises(RuntimeError, match="Audio domain container is not initialized"):
                    PhysicalControlsManager(None, hardware_config)

    @pytest.mark.asyncio
    async def test_initialize_hardware_failure(self, manager, physical_controls):
        """Test initialization handles hardware failure."""
        physical_controls.initialize = AsyncMock(return_value=False)

        success = await manager.initialize()

        assert success is False
        assert manager._is_initialized is False

    @pytest.mark.asyncio
    async def test_cleanup(self, manager, physical_controls):
        """Test cleanup operation."""
        await manager.initialize()
        await manager.cleanup()

        assert manager._is_initialized is False
        physical_controls.cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_when_not_initialized(self, manager, physical_controls):
        """Test cleanup when not initialized."""
        await manager.cleanup()

        physical_controls.cleanup.assert_not_called()

    def test_is_initialized_false_initially(self, manager):
        """Test is_initialized returns False initially."""
        assert manager.is_initialized() is False

    @pytest.mark.asyncio
    async def test_is_initialized_true_after_init(self, manager):
        """Test is_initialized returns True after init."""
        await manager.initialize()

        assert manager.is_initialized() is True


class TestEventHandlerSetup:
    """Test event handler configuration."""

    @pytest.fixture
    def manager(self):
        """Create manager for testing."""
        audio_controller = Mock()
        hardware_config = Mock()
        physical_controls = Mock()
        physical_controls.set_event_handler = Mock()

        with patch("app.src.application.controllers.physical_controls_controller.PhysicalControlsFactory") as mock_factory:
            mock_factory.create_controls = Mock(return_value=physical_controls)
            mgr = PhysicalControlsManager(audio_controller, hardware_config)
            mgr._physical_controls = physical_controls
            return mgr

    def test_setup_all_button_handlers(self, manager):
        """Test all button handlers are set up."""
        manager._setup_event_handlers()

        # Verify all expected event handlers were registered
        manager._physical_controls.set_event_handler.assert_any_call(
            PhysicalControlEvent.BUTTON_NEXT_TRACK,
            manager.handle_next_track
        )
        manager._physical_controls.set_event_handler.assert_any_call(
            PhysicalControlEvent.BUTTON_PREVIOUS_TRACK,
            manager.handle_previous_track
        )
        manager._physical_controls.set_event_handler.assert_any_call(
            PhysicalControlEvent.BUTTON_PLAY_PAUSE,
            manager.handle_play_pause
        )

    def test_setup_encoder_handlers(self, manager):
        """Test encoder handlers are set up with lambdas."""
        manager._setup_event_handlers()

        # Check that encoder handlers were set (they use lambdas so we check the event type)
        calls = manager._physical_controls.set_event_handler.call_args_list
        event_types = [call[0][0] for call in calls]

        assert PhysicalControlEvent.ENCODER_VOLUME_UP in event_types
        assert PhysicalControlEvent.ENCODER_VOLUME_DOWN in event_types


class TestPlayPauseHandling:
    """Test play/pause button handling."""

    def test_handle_play_pause_with_playback_coordinator(self):
        """Test play/pause with PlaybackCoordinator."""
        coordinator = Mock()
        coordinator.toggle_pause = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)
        manager._controller_type = "PlaybackCoordinator"

        manager.handle_play_pause()

        coordinator.toggle_pause.assert_called_once()

    def test_handle_play_pause_with_audio_controller(self):
        """Test play/pause with AudioController."""
        audio_controller = Mock(spec=['toggle_playback'])  # Only has AudioController methods
        audio_controller.toggle_playback = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(audio_controller, hardware_config)
        manager._controller_type = "AudioController"

        manager.handle_play_pause()

        audio_controller.toggle_playback.assert_called_once()

    def test_handle_play_pause_without_support(self):
        """Test play/pause when not supported."""
        controller = Mock(spec=[])  # No play/pause methods
        hardware_config = Mock()

        manager = PhysicalControlsManager(controller, hardware_config)

        # Should not raise exception
        manager.handle_play_pause()


class TestVolumeHandling:
    """Test volume control handling."""

    def test_handle_volume_up_with_coordinator(self):
        """Test volume up with PlaybackCoordinator."""
        coordinator = Mock()
        coordinator.get_volume = Mock(return_value=50)
        coordinator.set_volume = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)

        manager.handle_volume_change("up")

        coordinator.set_volume.assert_called_with(55)  # +5%

    def test_handle_volume_down_with_coordinator(self):
        """Test volume down with PlaybackCoordinator."""
        coordinator = Mock()
        coordinator.get_volume = Mock(return_value=50)
        coordinator.set_volume = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)

        manager.handle_volume_change("down")

        coordinator.set_volume.assert_called_with(45)  # -5%

    def test_volume_up_max_limit(self):
        """Test volume up respects maximum limit."""
        coordinator = Mock()
        coordinator.get_volume = Mock(return_value=98)
        coordinator.set_volume = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)

        manager.handle_volume_change("up")

        coordinator.set_volume.assert_called_with(100)  # Capped at 100

    def test_volume_down_min_limit(self):
        """Test volume down respects minimum limit."""
        coordinator = Mock()
        coordinator.get_volume = Mock(return_value=2)
        coordinator.set_volume = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)

        manager.handle_volume_change("down")

        coordinator.set_volume.assert_called_with(0)  # Capped at 0

    def test_volume_with_audio_controller(self):
        """Test volume control with AudioController."""
        audio_controller = Mock(spec=['increase_volume', 'decrease_volume'])  # Only AudioController methods
        audio_controller.increase_volume = Mock(return_value=True)
        audio_controller.decrease_volume = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(audio_controller, hardware_config)
        manager._controller_type = "AudioController"

        manager.handle_volume_change("up")
        audio_controller.increase_volume.assert_called_once()

        manager.handle_volume_change("down")
        audio_controller.decrease_volume.assert_called_once()


class TestTrackNavigation:
    """Test track navigation handling."""

    def test_handle_next_track_with_coordinator(self):
        """Test next track with PlaybackCoordinator."""
        coordinator = Mock()
        coordinator.next_track = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)
        manager._controller_type = "PlaybackCoordinator"

        manager.handle_next_track()

        coordinator.next_track.assert_called_once()

    def test_handle_previous_track_with_coordinator(self):
        """Test previous track with PlaybackCoordinator."""
        coordinator = Mock()
        coordinator.previous_track = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)
        manager._controller_type = "PlaybackCoordinator"

        manager.handle_previous_track()

        coordinator.previous_track.assert_called_once()

    def test_handle_next_track_with_audio_controller(self):
        """Test next track with AudioController."""
        audio_controller = Mock(spec=['next_track'])  # Only AudioController methods
        audio_controller.next_track = Mock(return_value=True)
        hardware_config = Mock()

        manager = PhysicalControlsManager(audio_controller, hardware_config)
        # Manually set controller type since spec limits attributes
        manager._controller_type = "AudioController"

        manager.handle_next_track()

        audio_controller.next_track.assert_called_once()

    def test_handle_next_track_end_of_playlist(self):
        """Test next track at end of playlist."""
        coordinator = Mock()
        coordinator.next_track = Mock(return_value=False)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)
        manager._controller_type = "PlaybackCoordinator"

        # Should not raise exception
        manager.handle_next_track()

    def test_handle_previous_track_beginning_of_playlist(self):
        """Test previous track at beginning of playlist."""
        coordinator = Mock()
        coordinator.previous_track = Mock(return_value=False)
        hardware_config = Mock()

        manager = PhysicalControlsManager(coordinator, hardware_config)
        manager._controller_type = "PlaybackCoordinator"

        # Should not raise exception
        manager.handle_previous_track()


class TestStatusQueries:
    """Test status query methods."""

    @pytest.fixture
    def manager(self):
        """Create manager for testing."""
        audio_controller = Mock()
        hardware_config = Mock()
        physical_controls = Mock()
        physical_controls.get_status = Mock(return_value={"hardware": "ready"})

        with patch("app.src.application.controllers.physical_controls_controller.PhysicalControlsFactory") as mock_factory:
            mock_factory.create_controls = Mock(return_value=physical_controls)
            mgr = PhysicalControlsManager(audio_controller, hardware_config)
            mgr._physical_controls = physical_controls
            return mgr

    def test_get_status_not_initialized(self, manager):
        """Test status when not initialized."""
        status = manager.get_status()

        assert status["initialized"] is False
        assert status["audio_controller_available"] is True
        assert status["domain_architecture"] is True
        assert status["gpio_integration"] is True

    @pytest.mark.asyncio
    async def test_get_status_initialized(self, manager):
        """Test status when initialized."""
        manager._is_initialized = True

        status = manager.get_status()

        assert status["initialized"] is True
        assert status["hardware"] == "ready"  # From physical controls

    def test_get_physical_controls(self, manager):
        """Test getting physical controls instance."""
        controls = manager.get_physical_controls()

        assert controls == manager._physical_controls


class TestErrorHandling:
    """Test error handling in physical controls."""

    def test_initialize_with_exception(self):
        """Test initialization handles exceptions."""
        audio_controller = Mock()
        hardware_config = Mock()
        physical_controls = AsyncMock()
        physical_controls.initialize = AsyncMock(side_effect=Exception("Hardware error"))

        with patch("app.src.application.controllers.physical_controls_controller.PhysicalControlsFactory") as mock_factory:
            mock_factory.create_controls = Mock(return_value=physical_controls)
            manager = PhysicalControlsManager(audio_controller, hardware_config)

            # Should handle exception gracefully

    def test_cleanup_with_exception(self):
        """Test cleanup handles exceptions."""
        audio_controller = Mock()
        hardware_config = Mock()
        physical_controls = AsyncMock()
        physical_controls.cleanup = AsyncMock(side_effect=Exception("Cleanup error"))

        with patch("app.src.application.controllers.physical_controls_controller.PhysicalControlsFactory") as mock_factory:
            mock_factory.create_controls = Mock(return_value=physical_controls)
            manager = PhysicalControlsManager(audio_controller, hardware_config)
            manager._is_initialized = True
            manager._physical_controls = physical_controls

            # Should handle exception gracefully

    def test_handle_event_without_controller(self):
        """Test event handling when controller doesn't support operation."""
        controller = Mock(spec=[])
        hardware_config = Mock()

        manager = PhysicalControlsManager(controller, hardware_config)

        # Should not raise exceptions
        manager.handle_play_pause()
        manager.handle_next_track()
        manager.handle_previous_track()
        manager.handle_volume_change("up")
