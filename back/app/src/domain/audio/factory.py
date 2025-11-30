# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Factory for creating audio domain components.

This factory implements singleton pattern for audio backend to prevent multiple
initialization attempts of hardware resources like pygame.mixer and ALSA devices.
"""

import threading
from typing import Any, cast

from app.src.domain.decorators.error_handler import (
    handle_domain_errors as handle_errors,
)
from app.src.domain.protocols.audio_backend_protocol import AudioBackendProtocol
from app.src.domain.protocols.audio_engine_protocol import AudioEngineProtocol

# PlaylistManagerProtocol removed - use data domain services
from app.src.domain.protocols.event_bus_protocol import EventBusProtocol
from app.src.domain.protocols.state_manager_protocol import StateManagerProtocol
from app.src.monitoring import get_logger

from .engine.audio_engine import AudioEngine
from .engine.event_bus import EventBus
from .engine.state_manager import StateManager

logger = get_logger(__name__)


class AudioDomainFactory:
    """Factory for creating audio domain components with dependency injection.

    This factory implements singleton pattern for audio backend creation to prevent
    multiple attempts to initialize hardware resources (pygame.mixer, ALSA devices).
    The singleton ensures only one audio backend instance exists application-wide.
    """

    # Singleton instance cache for audio backend (thread-safe)
    _cached_backend: AudioBackendProtocol | None = None
    _backend_lock: threading.Lock = threading.Lock()
    _backend_creation_attempted: bool = False
    _backend_creation_failed: bool = False

    @classmethod
    def get_cached_backend(cls) -> AudioBackendProtocol | None:
        """Get the cached audio backend if available.

        Returns:
            AudioBackendProtocol | None: Cached backend or None if not created yet
        """
        return cls._cached_backend

    @classmethod
    def has_cached_backend(cls) -> bool:
        """Check if a backend has been cached.

        Returns:
            bool: True if a backend is cached
        """
        return cls._cached_backend is not None

    @classmethod
    def backend_creation_was_attempted(cls) -> bool:
        """Check if backend creation was already attempted.

        This is useful to prevent multiple creation attempts when the first one failed.

        Returns:
            bool: True if creation was attempted (success or failure)
        """
        return cls._backend_creation_attempted

    @classmethod
    def clear_cached_backend(cls) -> None:
        """Clear the cached backend (for testing or cleanup).

        This should only be called during application shutdown or in tests.
        """
        with cls._backend_lock:
            if cls._cached_backend is not None:
                logger.info("🧹 Clearing cached audio backend")
                cls._cached_backend = None
            cls._backend_creation_attempted = False
            cls._backend_creation_failed = False

    @staticmethod
    def create_event_bus() -> EventBusProtocol:
        """Create a new event bus."""
        return EventBus()

    @staticmethod
    def create_state_manager() -> StateManagerProtocol:
        """Create a new state manager."""
        return StateManager()

    @staticmethod
    def create_backend_adapter(backend: Any) -> AudioBackendProtocol:
        """Return the backend directly (domain backends already implement the protocol).

        Args:
            backend: Domain backend implementation

        Returns:
            AudioBackendProtocol: The backend itself
        """
        # Domain backends already implement AudioBackendProtocol via BaseAudioBackend
        if isinstance(backend, AudioBackendProtocol):
            logger.debug(f"Backend already implements AudioBackendProtocol: {type(backend).__name__}",
                         )
            return backend

        logger.warning(f"Backend {type(backend).__name__} doesn't implement AudioBackendProtocol",
                       )
        return cast(AudioBackendProtocol, backend)

    # PlaylistManager removed - use data domain services

    @staticmethod
    def create_audio_engine(
        backend: AudioBackendProtocol,
        event_bus: EventBusProtocol | None = None,
        state_manager: StateManagerProtocol | None = None,
    ) -> AudioEngineProtocol:
        """Create a complete audio engine.

        Args:
            backend: Audio backend
            event_bus: Optional event bus (creates one if None)
            state_manager: Optional state manager (creates one if None)

        Returns:
            AudioEngineProtocol: Complete audio engine
        """
        if event_bus is None:
            event_bus = AudioDomainFactory.create_event_bus()

        if state_manager is None:
            state_manager = AudioDomainFactory.create_state_manager()

        return AudioEngine(backend, event_bus, state_manager)

    @staticmethod
    def create_complete_system(
        existing_backend: Any,
    ) -> tuple[AudioEngineProtocol, AudioBackendProtocol]:
        """Create a complete audio system from an existing backend.

        Args:
            existing_backend: Existing audio backend implementation

        Returns:
            tuple: (audio_engine, backend_adapter, playlist_manager)
        """
        logger.info(f"Creating complete audio system with {type(existing_backend).__name__}"
                    )

        # Create adapted backend
        backend = AudioDomainFactory.create_backend_adapter(existing_backend)

        # Create supporting components
        event_bus = AudioDomainFactory.create_event_bus()
        state_manager = AudioDomainFactory.create_state_manager()

        # Create main engine
        audio_engine = AudioDomainFactory.create_audio_engine(
            backend, event_bus, state_manager
        )

        logger.info("Complete audio system created successfully")

        return audio_engine, backend

    @classmethod
    @handle_errors("create_default_backend")
    def create_default_backend(cls) -> AudioBackendProtocol:
        """Create a default audio backend for pure domain architecture.

        This method implements singleton pattern to prevent multiple audio backend
        initialization attempts. On Linux, pygame.mixer and ALSA can only be
        initialized once - subsequent attempts cause "device busy" errors.

        If a backend is already cached, returns the cached instance.
        If creation was attempted and failed, raises the original error to prevent
        infinite retry loops.

        Returns:
            AudioBackendProtocol: Default audio backend (singleton)

        Raises:
            RuntimeError: If backend creation fails and no fallback is available
        """
        # Fast path: return cached backend if available
        if cls._cached_backend is not None:
            logger.info(f"🔄 Returning cached audio backend: {type(cls._cached_backend).__name__}")
            return cls._cached_backend

        # Thread-safe singleton creation
        with cls._backend_lock:
            # Double-check after acquiring lock
            if cls._cached_backend is not None:
                logger.info(f"🔄 Returning cached audio backend: {type(cls._cached_backend).__name__}")
                return cls._cached_backend

            # Prevent multiple creation attempts if first attempt failed
            if cls._backend_creation_attempted and cls._backend_creation_failed:
                logger.warning("⚠️ Audio backend creation was already attempted and failed, using mock fallback")
                return cls._create_mock_fallback_backend()

            # Mark that we're attempting creation
            cls._backend_creation_attempted = True

            try:
                backend = cls._create_platform_backend()
                cls._cached_backend = backend
                cls._backend_creation_failed = False
                return backend
            except Exception as e:
                logger.error(f"❌ Failed to create audio backend: {e}")
                cls._backend_creation_failed = True
                # Fall back to mock backend for graceful degradation
                logger.warning("🎭 Falling back to mock audio backend for graceful degradation")
                fallback = cls._create_mock_fallback_backend()
                cls._cached_backend = fallback
                return fallback

    @classmethod
    def _create_mock_fallback_backend(cls) -> AudioBackendProtocol:
        """Create a mock audio backend as fallback.

        Returns:
            AudioBackendProtocol: Mock audio backend
        """
        from app.src.domain.protocols.notification_protocol import MockPlaybackNotifier
        from .backends.implementations.mock_audio_backend import MockAudioBackend

        playback_subject = MockPlaybackNotifier.get_instance()
        mock_backend = MockAudioBackend(playback_subject)
        logger.info(f"✅ Created mock fallback backend: {type(mock_backend).__name__}")
        return cls.create_backend_adapter(mock_backend)

    @classmethod
    def _create_platform_backend(cls) -> AudioBackendProtocol:
        """Create platform-specific audio backend.

        Returns:
            AudioBackendProtocol: Platform-appropriate audio backend

        Raises:
            RuntimeError: If platform backend creation fails
        """
        import os
        import sys

        from app.src.domain.protocols.notification_protocol import MockPlaybackNotifier

        logger.info("Creating default audio backend for pure domain architecture")
        playback_subject = MockPlaybackNotifier.get_instance()

        # Check if we should use mock hardware
        use_mock_env = os.getenv("USE_MOCK_HARDWARE", "false").lower()
        use_mock = use_mock_env in ("true", "1", "yes", "on")

        if use_mock:
            logger.info("🎭 Using mock audio backend (USE_MOCK_HARDWARE=true)")
            from .backends.implementations.mock_audio_backend import MockAudioBackend

            mock_backend = MockAudioBackend(playback_subject)
            logger.info(f"✅ Created mock audio backend: {type(mock_backend).__name__}")
            return cls.create_backend_adapter(mock_backend)

        # Platform-specific backend selection
        if sys.platform == "darwin":
            logger.info("🍎 Detected macOS platform")
            try:
                from .backends.implementations.macos_audio_backend import (
                    MacOSAudioBackend,
                )

                macos_backend = MacOSAudioBackend(playback_subject)
                logger.info(f"✅ Created macOS audio backend: {type(macos_backend).__name__}")
                return cls.create_backend_adapter(macos_backend)
            except ImportError as e:
                logger.warning(f"⚠️ macOS audio backend failed ({e}), falling back to mock")
                from .backends.implementations.mock_audio_backend import (
                    MockAudioBackend,
                )

                fallback_backend = MockAudioBackend(playback_subject)
                logger.info(f"✅ Created fallback mock backend: {type(fallback_backend).__name__}")
                return cls.create_backend_adapter(fallback_backend)

        elif sys.platform == "linux":
            logger.info("🐧 Detected Linux platform")
            from .backends.implementations.wm8960_audio_backend import (
                WM8960AudioBackend,
            )

            wm8960_backend = WM8960AudioBackend(playback_subject)
            logger.info(f"✅ Created WM8960 audio backend: {type(wm8960_backend).__name__}")
            return cls.create_backend_adapter(wm8960_backend)

        else:
            logger.warning(f"⚠️ Unsupported platform {sys.platform}, falling back to mock backend")
            from .backends.implementations.mock_audio_backend import MockAudioBackend

            fallback_backend = MockAudioBackend(playback_subject)
            logger.info(f"✅ Created fallback mock backend: {type(fallback_backend).__name__}")
            return cls.create_backend_adapter(fallback_backend)
