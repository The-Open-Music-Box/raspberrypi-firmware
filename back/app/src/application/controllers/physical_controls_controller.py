# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Physical controls manager for handling hardware input devices.

This manager handles physical control devices such as buttons, rotary encoders,
and other GPIO-based input devices. It provides a clean interface between
hardware controls and the audio controller.
"""


from typing import Optional, Union, List

from app.src.application.controllers.audio_controller import AudioController
from app.src.domain.protocols.physical_controls_protocol import (
    PhysicalControlsProtocol,
    PhysicalControlEvent,
)
from app.src.infrastructure.hardware.controls.controls_factory import PhysicalControlsFactory
from app.src.application.services.button_action_application_service import ButtonActionDispatcher
from app.src.config.hardware_config import HardwareConfig
from app.src.config.button_actions_config import ButtonActionConfig, DEFAULT_BUTTON_CONFIGS
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors

logger = get_logger(__name__)


class PhysicalControlsManager:
    """Manager for physical control devices and hardware inputs.

    Handles initialization, event subscription, and cleanup of physical
    control devices. Coordinates between hardware events and audio control.
    """

    def __init__(
        self,
        audio_controller: Optional[Union[AudioController, 'PlaybackCoordinator']] = None,
        hardware_config: Optional[HardwareConfig] = None,
        button_configs: Optional[List[ButtonActionConfig]] = None
    ):
        """Initialize PhysicalControlsManager with real GPIO integration and configurable buttons.

        Args:
            audio_controller: AudioController or PlaybackCoordinator instance for handling audio operations
            hardware_config: Hardware configuration for GPIO pins
            button_configs: Optional button configurations (uses DEFAULT_BUTTON_CONFIGS if None)
        """
        # Use domain architecture directly if not provided
        if audio_controller is None:
            # PhysicalControlsManager requires an audio controller to be injected
            # It should NOT auto-create one to avoid tight coupling and circular dependencies
            # The caller (main.py) should create and inject PlaybackCoordinator
            logger.warning(
                "⚠️ PhysicalControlsManager created without audio_controller. "
                "Physical controls will be initialized but won't control playback until "
                "an audio controller is provided."
            )
            # Set to None - physical controls can still initialize for GPIO events
            audio_controller = None

        self.audio_controller = audio_controller
        self._controller_type = "PlaybackCoordinator" if hasattr(audio_controller, 'toggle_pause') else "AudioController"

        # Get hardware config if not provided
        if hardware_config is None:
            from app.src.config import config
            hardware_config = config.hardware_config

        self.hardware_config = hardware_config
        self._button_configs = button_configs or DEFAULT_BUTTON_CONFIGS
        self._is_initialized = False
        self._physical_controls: Optional[PhysicalControlsProtocol] = None
        self._button_dispatcher: Optional[ButtonActionDispatcher] = None

        # Store reference to main event loop for GPIO callbacks (which run in different threads)
        import asyncio
        try:
            self._main_loop = asyncio.get_running_loop()
            logger.debug(f"✅ Captured main event loop: {self._main_loop}")
        except RuntimeError:
            # No running loop yet - will be set during initialize()
            self._main_loop = None
            logger.debug("⚠️ No running loop yet - will capture during initialize()")

        # Create physical controls implementation with button configs
        self._physical_controls = PhysicalControlsFactory.create_controls(
            self.hardware_config,
            self._button_configs
        )

        # Create button action dispatcher (only for PlaybackCoordinator)
        if self._controller_type == "PlaybackCoordinator":
            self._button_dispatcher = ButtonActionDispatcher(
                self._button_configs,
                self.audio_controller
            )
            logger.info("✅ ButtonActionDispatcher created with configurable button support")

        logger.info("PhysicalControlsManager initialized with GPIO integration and configurable buttons")

    @handle_errors("initialize")
    async def initialize(self) -> bool:
        """Initialize physical controls with real GPIO integration.

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Capture the main event loop if not already done
            if self._main_loop is None:
                import asyncio
                try:
                    self._main_loop = asyncio.get_running_loop()
                    logger.info(f"✅ Captured main event loop during initialize: {self._main_loop}")
                except RuntimeError:
                    logger.error("❌ No running event loop - physical controls may not work properly")

            if not self.audio_controller:
                logger.warning("⚠️ No audio controller - physical controls will initialize but won't control playback")

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

        # Setup configurable button event handlers (BUTTON_0 through BUTTON_4)
        if self._button_dispatcher:
            for button_id in range(5):  # Buttons 0-4
                event = getattr(PhysicalControlEvent, f"BUTTON_{button_id}")
                self._physical_controls.set_event_handler(
                    event,
                    lambda bid=button_id: self._handle_configurable_button(bid)
                )
            logger.info("✅ Configurable button handlers registered (BUTTON_0 through BUTTON_4)")

        # Setup encoder event handlers (still use direct handlers)
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

    def _handle_configurable_button(self, button_id: int) -> None:
        """Handle configurable button press by dispatching to the configured action.

        Args:
            button_id: ID of the button that was pressed (0-4)
        """
        logger.info(f"🔘 [BUTTON] Button {button_id} pressed - starting dispatch")

        if not self._button_dispatcher:
            logger.warning(f"⚠️  [BUTTON] Button {button_id} pressed but no dispatcher available")
            return

        # Get action name for logging
        action = self._button_dispatcher.get_button_action(button_id)
        if action:
            logger.info(f"🎯 [BUTTON] Button {button_id} → Action: '{action.name}'")
        else:
            logger.warning(f"⚠️  [BUTTON] Button {button_id} has no configured action")
            return

        # Dispatch button press to configured action (sync wrapper)
        logger.debug(f"📤 [BUTTON] Dispatching button {button_id} to action '{action.name}'")
        result = self._button_dispatcher.dispatch_sync(button_id)

        if result:
            logger.info(f"✅ [BUTTON] Button {button_id} action '{action.name}' completed successfully")
        else:
            logger.error(f"❌ [BUTTON] Button {button_id} action '{action.name}' FAILED")

    async def _async_set_volume(self, volume: int, direction: str) -> None:
        """Helper to call async set_volume from sync context.

        Args:
            volume: New volume level (0-100)
            direction: Direction for logging ("up" or "down")
        """
        try:
            success = await self.audio_controller.set_volume(volume)
            if success:
                logger.info(f"✅ Volume {direction} to {volume}% via PlaybackCoordinator")
            else:
                logger.warning(f"⚠️ Volume {direction} failed via PlaybackCoordinator")
        except Exception as e:
            logger.error(f"❌ Error setting volume: {e}")

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

            # set_volume is async, need to schedule it in the main event loop
            # GPIO callbacks run in a different thread, so we need run_coroutine_threadsafe
            import asyncio
            try:
                if self._main_loop is None:
                    logger.error("❌ No main event loop available - cannot set volume")
                    return

                # Schedule the coroutine to run in the main loop from this GPIO thread
                future = asyncio.run_coroutine_threadsafe(
                    self._async_set_volume(new_volume, direction),
                    self._main_loop
                )
                # Don't block waiting for result - fire and forget
                # The async method will log success/failure
            except Exception as e:
                logger.error(f"❌ Failed to set volume: {e}")
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
            "configurable_buttons_enabled": self._button_dispatcher is not None,
        }

        # Add physical controls status if available
        if self._physical_controls:
            base_status.update(self._physical_controls.get_status())

        # Add dispatcher status if available
        if self._button_dispatcher:
            base_status["button_dispatcher"] = self._button_dispatcher.get_status()

        return base_status

    def get_physical_controls(self) -> Optional[PhysicalControlsProtocol]:
        """Get the physical controls implementation for testing.

        Returns:
            The physical controls implementation instance
        """
        return self._physical_controls
