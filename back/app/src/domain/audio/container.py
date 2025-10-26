# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Dependency injection container for the audio domain.

Provides centralized audio component initialization and lifecycle management.
"""

from typing import Optional, Any
import logging

from app.src.domain.decorators.error_handler import handle_domain_errors
from app.src.domain.audio.factory import AudioDomainFactory

logger = logging.getLogger(__name__)


def handle_errors(*dargs, **dkwargs):
    def _decorator(func):
        return handle_domain_errors(*dargs, **dkwargs)(func)

    return _decorator


class AudioDomainContainer:
    """Dependency injection container for audio domain components.

    Provides centralized configuration and lifecycle management
    for all audio domain components.
    """

    # MARK: - Initialization

    def __init__(self):
        self._audio_engine: Optional[Any] = None
        self._backend: Optional[Any] = None
        # Playlist manager removed - use data domain services
        self._event_bus: Optional[Any] = None
        self._state_manager: Optional[Any] = None

        self._is_initialized = False
        logger.info("AudioDomainContainer created")

    @handle_errors("initialize")
    def initialize(self, existing_backend: Any) -> None:
        """Initialize the container with an existing backend.

        Args:
            existing_backend: Existing audio backend implementation
        """
        if self._is_initialized:
            logger.warning("Container already initialized")
            return

        # Create complete audio system
        audio_engine, backend = AudioDomainFactory.create_complete_system(
            existing_backend
        )
        # Store references
        self._audio_engine = audio_engine
        self._backend = backend
        self._event_bus = audio_engine.event_bus
        self._state_manager = audio_engine.state_manager
        self._is_initialized = True
        logger.info("AudioDomainContainer initialized successfully")

    # MARK: - Lifecycle Management

    async def start(self) -> None:
        """Start the audio system."""
        if not self._is_initialized:
            raise RuntimeError("Container not initialized")

        await self._audio_engine.start()
        logger.info("Audio domain started")

    async def stop(self) -> None:
        """Stop the audio system."""
        if not self._is_initialized or not self._audio_engine:
            return

        try:
            await self._audio_engine.stop()
            logger.info("Audio domain stopped")
        except Exception as e:
            logger.error(f"Error stopping audio engine during shutdown: {e}")
            # Don't re-raise during shutdown to prevent recursion

    @handle_errors("cleanup")
    def cleanup(self) -> None:
        """Clean up all resources."""
        if not self._is_initialized:
            return

        # Playlist manager cleanup removed - use data domain services
        if self._backend:
            self._backend.cleanup()
        self._is_initialized = False
        logger.info("AudioDomainContainer cleanup completed")

    # MARK: - Component Access

    @property
    def audio_engine(self) -> Any:
        """Get the audio engine."""
        if not self._is_initialized:
            raise RuntimeError("Container not initialized")
        return self._audio_engine

    @property
    def backend(self) -> Any:
        """Get the audio backend."""
        if not self._is_initialized:
            raise RuntimeError("Container not initialized")
        return self._backend

    # Playlist manager property removed - use data domain services

    @property
    def event_bus(self) -> Any:
        """Get the event bus."""
        if not self._is_initialized:
            raise RuntimeError("Container not initialized")
        return self._event_bus

    @property
    def state_manager(self) -> Any:
        """Get the state manager."""
        if not self._is_initialized:
            raise RuntimeError("Container not initialized")
        return self._state_manager

    @property
    def is_initialized(self) -> bool:
        """Check if container is initialized."""
        return self._is_initialized


# Domain-internal instance
# This instance is managed by domain_bootstrap and is internal to the domain layer
# External code should access via DI: container.get("audio_domain_container")
# Lifecycle is managed via domain_bootstrap.initialize()
audio_domain_container = AudioDomainContainer()
