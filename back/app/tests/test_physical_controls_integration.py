# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Test Physical Controls Integration.

Tests for the complete physical controls implementation including GPIO integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from app.src.application.controllers.physical_controls_controller import PhysicalControlsManager
from app.src.domain.protocols.physical_controls_protocol import PhysicalControlEvent
from app.src.infrastructure.hardware.controls.mock_controls_implementation import MockPhysicalControls
from app.src.infrastructure.hardware.controls.controls_factory import PhysicalControlsFactory
from app.src.config.hardware_config import HardwareConfig


class TestPhysicalControlsIntegration:
    """Test physical controls integration with audio system."""

    @pytest.fixture
    def hardware_config(self):
        """Create test hardware configuration."""
        return HardwareConfig(
            gpio_next_track_button=26,
            gpio_previous_track_button=16,
            gpio_volume_encoder_clk=8,
            gpio_volume_encoder_dt=12,
            gpio_volume_encoder_sw=7,
            mock_hardware=True
        )

    @pytest.fixture
    def mock_audio_controller(self):
        """Create mock audio controller that supports both AudioController and PlaybackCoordinator methods."""
        controller = Mock()
        # PlaybackCoordinator style methods (preferred)
        controller.next_track = Mock(return_value=True)
        controller.previous_track = Mock(return_value=True)
        controller.toggle_pause = Mock(return_value=True)
        controller.get_volume = Mock(return_value=50)
        controller.set_volume = Mock(return_value=True)

        # AudioController style methods (fallback)
        controller.toggle_playback = Mock(return_value=True)
        controller.increase_volume = Mock(return_value=True)
        controller.decrease_volume = Mock(return_value=True)
        return controller

    @pytest.fixture
    async def physical_controls_manager(self, mock_audio_controller, hardware_config):
        """Create physical controls manager for testing."""
        manager = PhysicalControlsManager(mock_audio_controller, hardware_config)
        yield manager
        # Cleanup after test
        if manager.is_initialized():
            await manager.cleanup()

    def test_hardware_config_validation(self, hardware_config):
        """Test hardware configuration validation."""
        # Should not raise any exception
        hardware_config.validate()

        # Test invalid pin assignment
        with pytest.raises(ValueError, match="GPIO pin .* is out of valid range"):
            invalid_config = HardwareConfig(gpio_next_track_button=50)
            invalid_config.validate()

        # Test duplicate pin assignment
        with pytest.raises(ValueError, match="Duplicate GPIO pin assignments detected"):
            duplicate_config = HardwareConfig(
                gpio_next_track_button=26,
                gpio_previous_track_button=26  # Same pin as next
            )
            duplicate_config.validate()

    def test_controls_factory_creates_mock_implementation(self, hardware_config):
        """Test that factory creates mock implementation when requested."""
        controls = PhysicalControlsFactory.create_controls(hardware_config)
        assert isinstance(controls, MockPhysicalControls)

    @pytest.mark.asyncio
    async def test_physical_controls_manager_initialization(self, physical_controls_manager):
        """Test physical controls manager initialization."""
        # Initially not initialized
        assert not physical_controls_manager.is_initialized()

        # Initialize
        success = await physical_controls_manager.initialize()
        assert success is True
        assert physical_controls_manager.is_initialized()

        # Get status
        status = physical_controls_manager.get_status()
        assert status["initialized"] is True
        assert status["gpio_integration"] is True
        assert status["mock_mode"] is True

    @pytest.mark.asyncio
    async def test_button_event_handlers(self, physical_controls_manager, mock_audio_controller):
        """Test that button events trigger correct audio controller methods."""
        # Initialize
        await physical_controls_manager.initialize()

        # Test next track
        physical_controls_manager.handle_next_track()
        mock_audio_controller.next_track.assert_called_once()

        # Test previous track
        physical_controls_manager.handle_previous_track()
        mock_audio_controller.previous_track.assert_called_once()

        # Test play/pause
        physical_controls_manager.handle_play_pause()
        mock_audio_controller.toggle_pause.assert_called_once()

    @pytest.mark.asyncio
    async def test_volume_control_handlers(self, physical_controls_manager, mock_audio_controller):
        """Test that volume control events trigger correct audio methods."""
        # Initialize
        await physical_controls_manager.initialize()

        # Test volume up
        physical_controls_manager.handle_volume_change("up")
        mock_audio_controller.set_volume.assert_called_once_with(55)  # 50 + 5

        # Reset mocks for next test
        mock_audio_controller.reset_mock()
        mock_audio_controller.get_volume.return_value = 50

        # Test volume down
        physical_controls_manager.handle_volume_change("down")
        mock_audio_controller.set_volume.assert_called_once_with(45)  # 50 - 5

    @pytest.mark.asyncio
    async def test_mock_controls_simulation(self, physical_controls_manager):
        """Test mock controls simulation capabilities."""
        # Initialize
        await physical_controls_manager.initialize()

        # Get mock controls instance
        mock_controls = physical_controls_manager.get_physical_controls()
        assert isinstance(mock_controls, MockPhysicalControls)

        # Test simulation methods exist
        assert hasattr(mock_controls, 'simulate_next_track')
        assert hasattr(mock_controls, 'simulate_previous_track')
        assert hasattr(mock_controls, 'simulate_play_pause')
        assert hasattr(mock_controls, 'simulate_volume_up')
        assert hasattr(mock_controls, 'simulate_volume_down')

    @pytest.mark.asyncio
    async def test_controls_cleanup(self, physical_controls_manager):
        """Test proper cleanup of physical controls."""
        # Initialize
        await physical_controls_manager.initialize()
        assert physical_controls_manager.is_initialized()

        # Cleanup
        await physical_controls_manager.cleanup()
        assert not physical_controls_manager.is_initialized()

    @pytest.mark.asyncio
    async def test_event_handler_integration(self, hardware_config, mock_audio_controller):
        """Test event handler integration with mock controls."""
        manager = PhysicalControlsManager(mock_audio_controller, hardware_config)

        try:
            # Initialize
            await manager.initialize()

            # Get mock controls
            mock_controls = manager.get_physical_controls()

            # Simulate button presses
            await mock_controls.simulate_next_track()
            mock_audio_controller.next_track.assert_called_once()

            await mock_controls.simulate_previous_track()
            mock_audio_controller.previous_track.assert_called_once()

            await mock_controls.simulate_play_pause()
            mock_audio_controller.toggle_pause.assert_called_once()

            # Reset mock for next test
            mock_audio_controller.reset_mock()
            mock_audio_controller.get_volume.return_value = 50

            await mock_controls.simulate_volume_up()
            mock_audio_controller.set_volume.assert_called_once_with(55)  # 50 + 5

            # Reset mock for next test
            mock_audio_controller.reset_mock()
            mock_audio_controller.get_volume.return_value = 50

            await mock_controls.simulate_volume_down()
            mock_audio_controller.set_volume.assert_called_once_with(45)  # 50 - 5

        finally:
            await manager.cleanup()

    def test_error_handling_no_audio_controller(self, hardware_config):
        """Test error handling when no audio controller is provided."""
        # Should raise RuntimeError when audio_domain_container is not initialized
        with pytest.raises(RuntimeError, match="Audio domain container is not initialized"):
            PhysicalControlsManager(None, hardware_config)

    @pytest.mark.asyncio
    async def test_initialization_failure_handling(self, hardware_config):
        """Test handling of initialization failures."""
        mock_audio_controller = Mock()

        # Test with mock that has no required methods
        mock_audio_controller.next_track = None

        manager = PhysicalControlsManager(mock_audio_controller, hardware_config)

        # Should still initialize (GPIO part)
        success = await manager.initialize()
        assert success is True  # GPIO initialization should succeed

        await manager.cleanup()


@pytest.mark.integration
class TestPhysicalControlsRealHardware:
    """Integration tests for real hardware (when available)."""

    @pytest.mark.skipif(
        True,  # Skip by default - only run on actual hardware
        reason="Requires real GPIO hardware"
    )
    @pytest.mark.asyncio
    async def test_gpio_initialization_real_hardware(self):
        """Test GPIO initialization on real hardware."""
        hardware_config = HardwareConfig(mock_hardware=False)
        mock_audio_controller = Mock()

        manager = PhysicalControlsManager(mock_audio_controller, hardware_config)

        try:
            # This would test real GPIO initialization
            success = await manager.initialize()
            # On real hardware with proper permissions, this should succeed
            # Without hardware or permissions, it should gracefully fail

            if success:
                assert manager.is_initialized()
                status = manager.get_status()
                assert "gpio_available" in status

        finally:
            await manager.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])