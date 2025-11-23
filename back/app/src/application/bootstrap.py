# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Application-level bootstrap with hardware management.

This module extends the domain bootstrap with application-specific concerns:
- LED management and visual feedback
- Physical controls (buttons and encoder)
- Hardware initialization with retry logic for Raspberry Pi boot reliability
"""

import logging
from typing import TYPE_CHECKING

from app.src.application.utils.hardware_retry import retry_hardware_init
from app.src.domain.audio.container import audio_domain_container

# Domain imports
from app.src.domain.bootstrap import DomainBootstrap

if TYPE_CHECKING:
    from app.src.application.controllers.physical_controls_controller import (
        PhysicalControlsManager,
    )
    from app.src.application.services.led_event_handler_application_service import (
        LEDEventHandler,
    )
    from app.src.application.services.led_state_manager_application_service import (
        LEDStateManager,
    )

logger = logging.getLogger(__name__)


class ApplicationBootstrap(DomainBootstrap):
    """Application-level bootstrap extending domain bootstrap.

    Adds application-specific features:
    - LED system management for visual feedback
    - Physical controls (buttons + rotary encoder)
    - Hardware initialization retry logic (critical for Raspberry Pi first boot)

    Inherits domain-level audio and lifecycle management from DomainBootstrap.
    """

    # MARK: - Initialization

    def __init__(
        self,
        led_manager: 'LEDStateManager | None' = None,
        led_event_handler: 'LEDEventHandler | None' = None,
        physical_controls_manager: 'PhysicalControlsManager | None' = None
    ):
        """Initialize the application bootstrap with hardware components.

        Args:
            led_manager: Optional LED state manager (injected via DI)
            led_event_handler: Optional LED event handler (injected via DI)
            physical_controls_manager: Optional physical controls manager (injected via DI)
        """
        # Initialize domain bootstrap (audio, lifecycle)
        super().__init__()

        # Application-specific: LED management
        self._led_manager = led_manager
        self._led_event_handler = led_event_handler

        # Application-specific: Physical controls
        self._physical_controls_manager = physical_controls_manager

        # Log component injection status
        if led_manager and led_event_handler:
            logger.info(
                f"✅ ApplicationBootstrap created WITH LED components: "
                f"manager={type(led_manager).__name__}, "
                f"handler={type(led_event_handler).__name__}"
            )
        else:
            logger.warning(
                f"⚠️ ApplicationBootstrap created WITHOUT LED components: "
                f"manager={led_manager}, handler={led_event_handler}"
            )

        if physical_controls_manager:
            logger.info(
                f"✅ ApplicationBootstrap created WITH PhysicalControlsManager: "
                f"{type(physical_controls_manager).__name__}"
            )
        else:
            logger.warning("⚠️ ApplicationBootstrap created WITHOUT PhysicalControlsManager")

    # MARK: - Lifecycle Management (Override)

    async def start(self) -> None:
        """Start all services with hardware retry logic.

        Overrides domain start() to add:
        - LED system initialization with retry
        - Physical controls initialization with retry
        - Visual feedback for system state

        Raises:
            RuntimeError: If bootstrap not initialized or critical hardware fails
        """
        if not self._is_initialized:
            logger.error("❌ ApplicationBootstrap not initialized")
            raise RuntimeError("ApplicationBootstrap not initialized")

        # Initialize LED system (non-critical)
        if self._led_manager and self._led_event_handler:
            success, _ = await retry_hardware_init(
                "LED system",
                self._init_led_system,
                max_retries=3,
                retry_delay=2.0,
                critical=False
            )
            if not success:
                logger.warning("⚠️ LED system unavailable - continuing without visual feedback")
        else:
            logger.warning("⚠️ LED system NOT injected - skipping LED initialization")

        # Start audio domain (critical hardware)
        if audio_domain_container.is_initialized:
            try:
                success, _ = await retry_hardware_init(
                    "Audio domain",
                    audio_domain_container.start,
                    max_retries=3,
                    retry_delay=2.0,
                    critical=True
                )
            except RuntimeError as e:
                # Show boot error on LED if available
                if self._led_event_handler:
                    try:
                        await self._led_event_handler.on_boot_error(
                            f"Audio initialization failed: {e}"
                        )
                    except Exception as led_error:
                        logger.warning(f"LED boot error indication failed: {led_error}")
                raise  # Re-raise to prevent app from starting without audio
        else:
            logger.warning("⚠️ Audio domain not initialized, skipping start")

        # Initialize physical controls (non-critical)
        if self._physical_controls_manager:
            success, _ = await retry_hardware_init(
                "Physical controls",
                self._physical_controls_manager.initialize,
                max_retries=3,
                retry_delay=2.0,
                critical=False
            )
            if not success:
                logger.warning("⚠️ Physical controls unavailable - app accessible via web only")
        else:
            logger.warning("⚠️ Physical controls NOT injected - skipping initialization")

        # Set system ready state
        if self._led_event_handler:
            try:
                logger.info("💡 System ready - transitioning LED to IDLE state...")
                await self._led_event_handler.on_system_ready()
                logger.info("💡 LED system ready - showing IDLE state (solid white)")
            except Exception as e:
                logger.error(f"❌ LED ready state failed: {e}", exc_info=True)

        logger.info("🚀 Application services started")

    async def stop(self) -> None:
        """Stop all services including LED cleanup.

        Extends domain stop() to add LED system cleanup.
        """
        if not self._is_initialized or self._is_stopping:
            return

        # Call parent stop (domain services)
        await super().stop()

        # Application-specific: Cleanup LED
        if self._led_manager:
            try:
                await self._led_manager.cleanup()
                logger.info("💡 LED system cleaned up")
            except Exception as e:
                logger.warning(f"⚠️ LED cleanup failed: {e}")

    # MARK: - Hardware Initialization Helpers

    async def _init_led_system(self) -> None:
        """Initialize LED system components.

        Returns:
            None (success indicated by not raising exception)

        Raises:
            Exception: If LED initialization fails
        """
        if not self._led_manager or not self._led_event_handler:
            raise RuntimeError("LED components not available")

        logger.info("💡 Initializing LED manager...")
        await self._led_manager.initialize()
        logger.info("💡 LED manager initialized")

        logger.info("💡 Initializing LED event handler...")
        await self._led_event_handler.initialize()
        logger.info("💡 LED event handler initialized")

        logger.info("💡 Setting STARTING state...")
        await self._led_event_handler.on_system_starting()
        logger.info("💡 LED system started - showing STARTING state (white blinking)")

    # MARK: - Public Properties

    @property
    def led_event_handler(self) -> 'LEDEventHandler | None':
        """Get LED event handler for application use.

        Returns:
            LED event handler instance or None if not available
        """
        return self._led_event_handler

    def set_physical_controls_manager(
        self,
        physical_controls_manager: 'PhysicalControlsManager | None'
    ) -> None:
        """Set physical controls manager after bootstrap creation.

        This method allows injecting PhysicalControlsManager after bootstrap
        is created, avoiding circular dependencies in the DI container.

        Args:
            physical_controls_manager: PhysicalControlsManager instance to inject or None
        """
        self._physical_controls_manager = physical_controls_manager
        if physical_controls_manager:
            logger.info(
                f"✅ PhysicalControlsManager injected into ApplicationBootstrap: "
                f"{type(physical_controls_manager).__name__}"
            )
        else:
            logger.warning("⚠️ PhysicalControlsManager set to None in ApplicationBootstrap")


# MARK: - Removed Global Instance
# Bootstrap instances now managed by dependency injection
# Use: container.get("application_bootstrap") or get_application_bootstrap()
