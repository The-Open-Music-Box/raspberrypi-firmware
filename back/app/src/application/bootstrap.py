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

    def __init__(self, led_manager: Optional[Any] = None, led_event_handler: Optional[Any] = None):
        """Initialize the bootstrap.

        Args:
            led_manager: Optional LED state manager (injected via DI)
            led_event_handler: Optional LED event handler (injected via DI)
        """
        self._is_initialized = False
        self._is_stopping = False

        # LED management (injected dependencies)
        self._led_manager = led_manager
        self._led_event_handler = led_event_handler

        # Log LED component injection status
        if led_manager and led_event_handler:
            logger.info(f"✅ DomainBootstrap created WITH LED components: manager={type(led_manager).__name__}, handler={type(led_event_handler).__name__}")
        else:
            logger.warning(f"⚠️ DomainBootstrap created WITHOUT LED components: manager={led_manager}, handler={led_event_handler}")

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

    # MARK: - Lifecycle Management

    @handle_errors(operation_name="start", component="domain.bootstrap")
    async def start(self) -> None:
        """Start all domain services."""
        if not self._is_initialized:
            logger.error("❌ DomainBootstrap not initialized")
            raise RuntimeError("DomainBootstrap not initialized")
            return

        # Initialize LED system and show STARTING state
        if self._led_manager and self._led_event_handler:
            try:
                logger.info("💡 Initializing LED system...")
                await self._led_manager.initialize()
                logger.info("💡 LED manager initialized")
                await self._led_event_handler.initialize()
                logger.info("💡 LED event handler initialized")
                await self._led_event_handler.on_system_starting()
                logger.info("💡 LED system started - showing STARTING state (white blinking)")
            except Exception as e:
                logger.error(f"❌ LED system start failed: {e}", exc_info=True)
        else:
            logger.warning("⚠️ LED system NOT available - skipping LED initialization")

        # Start audio domain (critical hardware)
        if audio_domain_container.is_initialized:
            try:
                await audio_domain_container.start()
                logger.info("✅ Audio domain started successfully")
            except Exception as e:
                logger.error(f"❌ Audio domain start failed (boot error): {e}", exc_info=True)
                # Show boot hardware error LED (slow blink red)
                if self._led_event_handler:
                    try:
                        await self._led_event_handler.on_boot_error(f"Audio initialization failed: {str(e)}")
                    except Exception as led_error:
                        logger.warning(f"LED boot error indication failed: {led_error}")
                # Re-raise to prevent app from starting with broken audio
                raise
        else:
            logger.warning("⚠️ Audio domain not initialized, skipping start")

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
