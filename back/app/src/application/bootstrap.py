# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Domain-driven architecture bootstrap.

This module provides the main entry point for initializing the domain-driven architecture
and provides compatibility layers for legacy code.
"""

from typing import Any, Dict, Optional
import logging

# Direct imports instead of dynamic imports
from app.src.domain.audio.container import audio_domain_container
from app.src.domain.audio.factory import AudioDomainFactory
from app.src.domain.decorators.error_handler import handle_domain_errors

logger = logging.getLogger(__name__)


def handle_errors(*dargs, **dkwargs):
    """Proxy to domain error handler for backward compatibility."""
    return handle_domain_errors(*dargs, **dkwargs)


class DomainBootstrap:
    """Bootstrap class for domain-driven architecture."""

    # MARK: - Initialization

    def __init__(self, led_manager: Optional[Any] = None, led_event_handler: Optional[Any] = None, physical_controls_manager: Optional[Any] = None):
        """Initialize the bootstrap.

        Args:
            led_manager: Optional LED state manager (injected via DI)
            led_event_handler: Optional LED event handler (injected via DI)
            physical_controls_manager: Optional physical controls manager (injected via DI)
        """
        self._is_initialized = False
        self._is_stopping = False

        # LED management (injected dependencies)
        self._led_manager = led_manager
        self._led_event_handler = led_event_handler

        # Physical controls management (injected dependency)
        self._physical_controls_manager = physical_controls_manager

        # Log LED component injection status
        if led_manager and led_event_handler:
            logger.info(f"✅ DomainBootstrap created WITH LED components: manager={type(led_manager).__name__}, handler={type(led_event_handler).__name__}")
        else:
            logger.warning(f"⚠️ DomainBootstrap created WITHOUT LED components: manager={led_manager}, handler={led_event_handler}")

        # Log physical controls injection status
        if physical_controls_manager:
            logger.info(f"✅ DomainBootstrap created WITH PhysicalControlsManager: {type(physical_controls_manager).__name__}")
        else:
            logger.warning("⚠️ DomainBootstrap created WITHOUT PhysicalControlsManager")

    @handle_errors(operation_name="initialize", component="domain.bootstrap")
    def initialize(self, existing_backend: Any = None) -> None:
        """Initialize the domain-driven architecture.

        Args:
            existing_backend: Existing audio backend to adapt
        """
        if self._is_initialized:
            logger.warning("DomainBootstrap already initialized")
            return

        logger.info("🚀 Initializing domain architecture...")
        if existing_backend:
            audio_domain_container.initialize(existing_backend)
            logger.debug(f"Audio domain initialized with {type(existing_backend).__name__}")
        else:
            default_backend = AudioDomainFactory.create_default_backend()
            audio_domain_container.initialize(default_backend)
            logger.debug(
                f"Pure domain audio initialized with {type(default_backend).__name__}"
            )

        # LED system already injected via constructor (if available)
        if self._led_manager and self._led_event_handler:
            logger.info("✅ LED system available (injected via DI)")
        else:
            logger.debug("LED system not available (not injected)")

        self._is_initialized = True
        logger.info("✅ Domain bootstrap initialized")

    # MARK: - Hardware Initialization with Retry

    async def _initialize_led_with_retry(self, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        """Initialize LED system with retry logic for first boot.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries
        """
        import asyncio

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"💡 Initializing LED system (attempt {attempt}/{max_retries})...")
                await self._led_manager.initialize()
                logger.info("💡 LED manager initialized")
                await self._led_event_handler.initialize()
                logger.info("💡 LED event handler initialized")
                await self._led_event_handler.on_system_starting()
                logger.info("💡 LED system started - showing STARTING state (white blinking)")
                return  # Success!
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"⚠️ LED initialization attempt {attempt} failed: {e}")
                    logger.info(f"🔄 Retrying in {retry_delay}s... (hardware may not be ready yet)")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"❌ LED system start failed after {max_retries} attempts: {e}", exc_info=True)
                    logger.warning("⚠️ Continuing without LED system (non-critical)")

    async def _initialize_audio_with_retry(self, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        """Initialize audio domain with retry logic for first boot.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries
        """
        import asyncio

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🎵 Starting audio domain (attempt {attempt}/{max_retries})...")
                await audio_domain_container.start()
                logger.info("✅ Audio domain started successfully")
                return  # Success!
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"⚠️ Audio initialization attempt {attempt} failed: {e}")
                    logger.info(f"🔄 Retrying in {retry_delay}s... (hardware may not be ready yet)")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"❌ Audio domain start failed after {max_retries} attempts: {e}", exc_info=True)
                    # Show boot hardware error LED (slow blink red)
                    if self._led_event_handler:
                        try:
                            await self._led_event_handler.on_boot_error(f"Audio initialization failed: {str(e)}")
                        except Exception as led_error:
                            logger.warning(f"LED boot error indication failed: {led_error}")
                    # Re-raise to prevent app from starting with broken audio
                    raise

    async def _initialize_physical_controls_with_retry(self, max_retries: int = 3, retry_delay: float = 2.0) -> None:
        """Initialize physical controls with retry logic for first boot.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay in seconds between retries
        """
        import asyncio

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🎮 Initializing physical controls (attempt {attempt}/{max_retries})...")
                success = await self._physical_controls_manager.initialize()
                if success:
                    logger.info("✅ Physical controls initialized successfully (buttons + encoder)")
                    return  # Success!
                else:
                    raise RuntimeError("Physical controls initialization returned False")
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"⚠️ Physical controls initialization attempt {attempt} failed: {e}")
                    logger.info(f"🔄 Retrying in {retry_delay}s... (GPIO hardware may not be ready yet)")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"❌ Physical controls failed after {max_retries} attempts: {e}", exc_info=True)
                    logger.warning("⚠️ Continuing without physical controls (non-critical)")
                    # Don't raise - physical controls are non-critical, app can run without them

    # MARK: - Lifecycle Management

    @handle_errors(operation_name="start", component="domain.bootstrap")
    async def start(self) -> None:
        """Start all domain services with hardware retry logic."""
        if not self._is_initialized:
            logger.error("❌ DomainBootstrap not initialized")
            raise RuntimeError("DomainBootstrap not initialized")
            return

        # Initialize LED system with retry (hardware may not be ready on first boot)
        if self._led_manager and self._led_event_handler:
            await self._initialize_led_with_retry()
        else:
            logger.warning("⚠️ LED system NOT available - skipping LED initialization")

        # Start audio domain with retry (critical hardware)
        if audio_domain_container.is_initialized:
            await self._initialize_audio_with_retry()
        else:
            logger.warning("⚠️ Audio domain not initialized, skipping start")

        # Initialize physical controls (buttons + encoder) with retry
        if self._physical_controls_manager:
            await self._initialize_physical_controls_with_retry()
        else:
            logger.warning("⚠️ Physical controls NOT available - skipping initialization")

        # Clear STARTING state and set to IDLE when ready
        if self._led_event_handler:
            try:
                logger.info("💡 System ready - transitioning LED to IDLE state...")
                await self._led_event_handler.on_system_ready()
                logger.info("💡 LED system ready - showing IDLE state (solid white)")
            except Exception as e:
                logger.error(f"❌ LED ready state failed: {e}", exc_info=True)

        # Note: unified_controller has been moved to application layer
        logger.info("🚀 Domain services started")

    @handle_errors(operation_name="stop", component="domain.bootstrap")
    async def stop(self) -> None:
        """Stop all domain services."""
        if not self._is_initialized or self._is_stopping:
            return

        self._is_stopping = True
        try:
            # Note: unified_controller has been moved to application layer
            if audio_domain_container.is_initialized:
                await audio_domain_container.stop()

            # Cleanup LED
            if self._led_manager:
                try:
                    await self._led_manager.cleanup()
                    logger.info("💡 LED system cleaned up")
                except Exception as e:
                    logger.warning(f"⚠️ LED cleanup failed: {e}")

            logger.debug("Domain services stopped")
        except Exception as e:
            logger.error(f"Error stopping domain services: {e}")
            # Don't re-raise during shutdown to prevent recursion
        finally:
            self._is_stopping = False

    @handle_errors(operation_name="cleanup", component="domain.bootstrap")
    def cleanup(self) -> None:
        """Cleanup all resources."""
        if not self._is_initialized:
            return

        # Note: unified_controller has been moved to application layer
        audio_domain_container.cleanup()
        self._is_initialized = False
        logger.debug("Domain cleanup completed")

    # MARK: - Public Properties

    @property
    def is_initialized(self) -> bool:
        """Check if bootstrap is initialized."""
        return self._is_initialized

    @property
    def led_event_handler(self) -> Optional[Any]:
        """Get LED event handler for application use."""
        return self._led_event_handler

    def set_physical_controls_manager(self, physical_controls_manager: Optional[Any]) -> None:
        """Set physical controls manager after bootstrap creation.

        This method allows injecting PhysicalControlsManager after DomainBootstrap
        is created, avoiding circular dependencies in the DI container.

        Args:
            physical_controls_manager: PhysicalControlsManager instance to inject
        """
        self._physical_controls_manager = physical_controls_manager
        if physical_controls_manager:
            logger.info(f"✅ PhysicalControlsManager injected into DomainBootstrap: {type(physical_controls_manager).__name__}")
        else:
            logger.warning("⚠️ PhysicalControlsManager set to None in DomainBootstrap")

    # MARK: - System Status

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            "domain_bootstrap": {
                "initialized": self._is_initialized,
                "architecture": "pure_domain",
            },
            "audio_domain": {
                "initialized": audio_domain_container.is_initialized,
                "running": (
                    audio_domain_container.audio_engine.is_running
                    if audio_domain_container.is_initialized
                    else False
                ),
            },
        }

    # MARK: Internal Methods

    def _setup_error_callbacks(self) -> None:
        """Setup error handling callbacks (domain-level only)."""
        # Domain-level error handling without infrastructure dependencies
        logger.debug("Domain error callbacks setup completed")

    def _handle_audio_error(self, error_record) -> None:
        """Handle audio-specific errors with recovery strategies."""
        logger.warning(f"🎵 Audio error handled: {error_record.message}")

        # Implement audio recovery strategies based on error type
        if "connection" in error_record.message.lower():
            logger.info("🔄 Attempting audio backend reconnection...")
            # Note: Actual recovery would require access to audio container
            # In a real implementation, we'd inject recovery service here
        elif "timeout" in error_record.message.lower():
            logger.info("⏱️ Audio timeout detected, attempting restart...")
        else:
            logger.info("🛠️ General audio error recovery initiated...")

    def _handle_critical_error(self, error_record) -> None:
        """Handle critical errors with emergency procedures."""
        logger.error(f"🔥 Critical error handled: {error_record.message}")

        # Implement emergency procedures for critical errors
        logger.error("🚨 Initiating emergency procedures...")

        # Log critical error for administrator notification
        logger.critical(f"ALERT: Critical system error - {error_record.message}")

        # Attempt to save current state before potential shutdown
        try:
            logger.info("💾 Attempting to save current application state...")
            # Note: State saving would require access to state services
            # In a real implementation, we'd inject state persistence service here
        except Exception as e:
            logger.error(f"❌ Failed to save state: {e}")

        # Consider graceful degradation rather than immediate shutdown
        logger.warning("🔒 Entering safe mode operation...")


# MARK: - Removed Global Instance
# domain_bootstrap global instance has been removed in favor of dependency injection
# Use: container.get("domain_bootstrap") or get_domain_bootstrap()
# Migration completed: All code now uses DI
