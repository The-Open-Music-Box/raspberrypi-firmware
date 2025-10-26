# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Physical controls manager for handling hardware input devices.

This manager handles physical control devices such as buttons, rotary encoders,
and other GPIO-based input devices. It provides a clean interface between
hardware controls and the audio controller.
"""


from typing import Optional, Union

from app.src.application.controllers.audio_controller import AudioController
from app.src.domain.protocols.physical_controls_protocol import (
    PhysicalControlsProtocol,
    PhysicalControlEvent,
)
from app.src.infrastructure.hardware.controls.controls_factory import PhysicalControlsFactory
from app.src.config.hardware_config import HardwareConfig
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors

logger = get_logger(__name__)


class PhysicalControlsManager:
    """Manager for physical control devices and hardware inputs.

    Handles initialization, event subscription, and cleanup of physical
    control devices. Coordinates between hardware events and audio control.
    """

    def __init__(self, audio_controller: Optional[Union[AudioController, 'PlaybackCoordinator']] = None, hardware_config: Optional[HardwareConfig] = None):
        """Initialize PhysicalControlsManager with real GPIO integration.

        Args:
            audio_controller: AudioController or PlaybackCoordinator instance for handling audio operations
            hardware_config: Hardware configuration for GPIO pins
        """
        # Use domain architecture directly if not provided
        if audio_controller is None:
            try:
                # Use PlaybackCoordinator directly from domain architecture
                from app.src.application.controllers import PlaybackCoordinator
                from app.src.domain.audio.container import audio_domain_container

                if not audio_domain_container.is_initialized:
                    raise RuntimeError(
                        "Audio domain container is not initialized. "
                        "PhysicalControlsManager requires a valid audio controller."
                    )

                # Create PlaybackCoordinator with domain dependencies
                audio_backend = audio_domain_container._backend
                from app.src.dependencies import get_data_playlist_service
                playlist_service = get_data_playlist_service()

                audio_controller = PlaybackCoordinator(
                    audio_backend=audio_backend,
                    playlist_service=playlist_service
                )
                logger.info("✅ Using PlaybackCoordinator with domain architecture for physical controls")

            except ImportError as e:
                logger.error(f"❌ Failed to initialize PlaybackCoordinator for physical controls: {e}")
                raise RuntimeError(
                    f"Failed to import required components for PhysicalControlsManager: {e}"
                ) from e

        self.audio_controller = audio_controller
        self._controller_type = "PlaybackCoordinator" if hasattr(audio_controller, 'toggle_pause') else "AudioController"

        # Get hardware config if not provided
        if hardware_config is None:
            from app.src.config import config
            hardware_config = config.hardware_config

        self.hardware_config = hardware_config
        self._is_initialized = False
        self._physical_controls: Optional[PhysicalControlsProtocol] = None

        # Create physical controls implementation
        self._physical_controls = PhysicalControlsFactory.create_controls(self.hardware_config)

        logger.info("PhysicalControlsManager initialized with GPIO integration")

    @handle_errors("initialize")
    async def initialize(self) -> bool:
        """Initialize physical controls with real GPIO integration.

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            if not self.audio_controller:
                logger.error("No audio controller available for physical controls integration")
                return False

            if not self._physical_controls:
                logger.error("No physical controls implementation available")
                return False

            # Initialize the physical controls hardware
            success = await self._physical_controls.initialize()
            if not success:
                logger.error("Failed to initialize physical controls hardware")
                return False

            # Setup event handlers for GPIO events
            self._setup_event_handlers()

            self._is_initialized = True
            logger.info("✅ Physical controls manager initialized with GPIO integration")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize physical controls: {e}")
            return False

    def _setup_event_handlers(self) -> None:
        """Setup event handlers for physical control events."""
        if not self._physical_controls:
            return

        # Setup button event handlers
        self._physical_controls.set_event_handler(
            PhysicalControlEvent.BUTTON_NEXT_TRACK,
            self.handle_next_track
        )

        self._physical_controls.set_event_handler(
            PhysicalControlEvent.BUTTON_PREVIOUS_TRACK,
            self.handle_previous_track
        )

        self._physical_controls.set_event_handler(
            PhysicalControlEvent.BUTTON_PLAY_PAUSE,
            self.handle_play_pause
        )

        # Setup encoder event handlers
        self._physical_controls.set_event_handler(
            PhysicalControlEvent.ENCODER_VOLUME_UP,
            lambda: self.handle_volume_change("up")
        )

        self._physical_controls.set_event_handler(
            PhysicalControlEvent.ENCODER_VOLUME_DOWN,
            lambda: self.handle_volume_change("down")
        )

        logger.info("Physical control event handlers configured")

    @handle_errors("cleanup")
    async def cleanup(self) -> None:
        """Clean up physical controls resources."""
        if self._is_initialized and self._physical_controls:
            logger.info("Cleaning up physical controls manager")
            try:
                await self._physical_controls.cleanup()
                logger.info("✅ Physical controls hardware cleanup completed")
            except Exception as e:
                logger.error(f"❌ Error during physical controls cleanup: {e}")

            self._is_initialized = False

    def is_initialized(self) -> bool:
        """Check if physical controls are initialized.

        Returns:
            True if controls are initialized and ready, False otherwise
        """
        return self._is_initialized

    @handle_errors("handle_play_pause")
    def handle_play_pause(self) -> None:
        """Handle play/pause control for domain architecture."""
        logger.info(f"🎮 Physical Control: Play/Pause button pressed (controller: {self._controller_type})")

        # Try PlaybackCoordinator methods first (preferred)
        if hasattr(self.audio_controller, "toggle_pause"):
            # PlaybackCoordinator style
            success = self.audio_controller.toggle_pause()
            if success:
                logger.info("✅ Play/pause action completed successfully via PlaybackCoordinator")
            else:
                logger.warning("⚠️ Play/pause failed via PlaybackCoordinator")
        elif hasattr(self.audio_controller, "toggle_playback"):
            # AudioController style (backward compatibility)
            success = self.audio_controller.toggle_playback()
            if success:
                logger.info("✅ Play/pause action completed successfully via AudioController")
            else:
                logger.warning("⚠️ Play/pause failed via AudioController")
        else:
            logger.warning("⚠️ Play/pause not supported by current controller")

    @handle_errors("handle_volume_change")
    def handle_volume_change(self, direction: str) -> None:
        """Handle volume change control for domain architecture.

        Args:
            direction: Volume change direction ("up" or "down")
        """
        logger.info(f"🎮 Physical Control: Volume {direction} encoder rotated (controller: {self._controller_type})")

        # Try PlaybackCoordinator methods first
        if hasattr(self.audio_controller, "get_volume") and hasattr(self.audio_controller, "set_volume"):
            # PlaybackCoordinator style - get current volume and adjust
            current_volume = self.audio_controller.get_volume()
            if direction == "up":
                new_volume = min(100, current_volume + 5)  # Increase by 5%
            else:
                new_volume = max(0, current_volume - 5)  # Decrease by 5%

            success = self.audio_controller.set_volume(new_volume)
            if success:
                logger.info(f"✅ Volume {direction} to {new_volume}% via PlaybackCoordinator")
            else:
                logger.warning(f"⚠️ Volume {direction} failed via PlaybackCoordinator")
        elif direction == "up" and hasattr(self.audio_controller, "increase_volume"):
            # AudioController style (backward compatibility)
            success = self.audio_controller.increase_volume()
            if success:
                logger.info("✅ Volume increased successfully via AudioController")
            else:
                logger.warning("⚠️ Volume increase failed via AudioController")
        elif direction == "down" and hasattr(self.audio_controller, "decrease_volume"):
            success = self.audio_controller.decrease_volume()
            if success:
                logger.info("✅ Volume decreased successfully via AudioController")
            else:
                logger.warning("⚠️ Volume decrease failed via AudioController")
        else:
            logger.warning(f"⚠️ Volume {direction} not supported by current controller"
            )

    @handle_errors("handle_next_track")
    def handle_next_track(self) -> None:
        """Handle next track control for domain architecture."""
        logger.info(f"🎮 Physical Control: Next track button pressed (controller: {self._controller_type})")

        # Try PlaybackCoordinator method first (same name, different behavior)
        if hasattr(self.audio_controller, "next_track"):
            # Both controllers have next_track, but check which type we have
            if self._controller_type == "PlaybackCoordinator":
                success = self.audio_controller.next_track()
                if success:
                    logger.info("✅ Next track action completed successfully via PlaybackCoordinator")
                else:
                    logger.info("ℹ️ End of playlist reached")
            else:
                # AudioControllerAdapter - try sync wrapper first
                if hasattr(self.audio_controller, "next_track_sync"):
                    success = self.audio_controller.next_track_sync()
                else:
                    success = self.audio_controller.next_track()

                if success:
                    logger.info("✅ Next track action completed successfully via AudioController")
                else:
                    logger.warning("⚠️ Next track failed via AudioController")
        else:
            logger.warning("⚠️ Next track not supported by current controller")

    @handle_errors("handle_previous_track")
    def handle_previous_track(self) -> None:
        """Handle previous track control for domain architecture."""
        logger.info(f"🎮 Physical Control: Previous track button pressed (controller: {self._controller_type})")

        # Try PlaybackCoordinator method first (same name, different behavior)
        if hasattr(self.audio_controller, "previous_track"):
            # Both controllers have previous_track, but check which type we have
            if self._controller_type == "PlaybackCoordinator":
                success = self.audio_controller.previous_track()
                if success:
                    logger.info("✅ Previous track action completed successfully via PlaybackCoordinator")
                else:
                    logger.info("ℹ️ Beginning of playlist reached")
            else:
                # AudioControllerAdapter - try sync wrapper first
                if hasattr(self.audio_controller, "previous_track_sync"):
                    success = self.audio_controller.previous_track_sync()
                else:
                    success = self.audio_controller.previous_track()

                if success:
                    logger.info("✅ Previous track action completed successfully via AudioController")
                else:
                    logger.warning("⚠️ Previous track failed via AudioController")
        else:
            logger.warning("⚠️ Previous track not supported by current controller")

    def get_status(self) -> dict:
        """Get the current status of physical controls.

        Returns:
            Dictionary containing status information
        """
        base_status = {
            "initialized": self._is_initialized,
            "audio_controller_available": self.audio_controller is not None,
            "controller_type": self._controller_type,
            "domain_architecture": True,
            "gpio_integration": True,
        }

        # Add physical controls status if available
        if self._physical_controls:
            base_status.update(self._physical_controls.get_status())

        return base_status

    def get_physical_controls(self) -> Optional[PhysicalControlsProtocol]:
        """Get the physical controls implementation for testing.

        Returns:
            The physical controls implementation instance
        """
        return self._physical_controls
