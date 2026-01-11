# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Audio backend factory for creating platform-specific audio players.

Provides factory functions to create appropriate audio backends based on the
current platform and hardware configuration, supporting macOS, Raspberry Pi,
and mock implementations for testing.
"""

import sys
from typing import cast

from app.src.config import config
from app.src.domain.decorators.error_handler import (
    handle_domain_errors as handle_errors,
)
from app.src.domain.protocols.audio_backend_protocol import AudioBackendProtocol
from app.src.domain.protocols.jack_detection_protocol import JackDetectionProtocol
from app.src.domain.protocols.notification_protocol import (
    PlaybackNotifierProtocol as PlaybackSubject,
)
from app.src.monitoring import get_logger

logger = get_logger(__name__)

# Store jack detection instance for lifecycle management
_jack_detection_instance: JackDetectionProtocol | None = None


def get_audio_backend(
    playback_subject: PlaybackSubject | None = None,
) -> AudioBackendProtocol:
    """Create just the audio backend without unified player wrapper.

    This is the recommended way for new architecture using PlaybackCoordinator.

    Args:
        playback_subject: Optional notification service for playback events

    Returns:
        AudioBackendProtocol: Platform-appropriate audio backend
    """
    return cast(AudioBackendProtocol, _create_audio_backend(playback_subject))


@handle_errors("_create_audio_backend")
def _create_audio_backend(
    playback_subject: PlaybackSubject | None = None,
) -> AudioBackendProtocol:
    """Create the appropriate audio backend based on platform and configuration.

    Args:
        playback_subject: Optional notification service for playbook events

    Returns:
        AudioBackendProtocol: Platform-appropriate audio backend
    """
    if config.hardware.mock_hardware:
        from .mock_audio_backend import MockAudioBackend

        logger.info("🧪 Creating MockAudioBackend (mock hardware mode)")
        return MockAudioBackend(playback_subject)

    if sys.platform == "darwin":
        # Use macOS-specific audio backend with Core Audio
        from .macos_audio_backend import MacOSAudioBackend

        logger.info("🍎 Creating MacOSAudioBackend...")
        backend = MacOSAudioBackend(playback_subject)
        logger.info("✅ macOS Audio Backend initialized successfully")
        return cast(AudioBackendProtocol, backend)

    # Try to initialize hardware audio backend (WM8960 for Raspberry Pi/Linux)
    try:
        from .wm8960_audio_backend import WM8960AudioBackend

        logger.info("🔊 Creating WM8960AudioBackend...")

        # Create jack detection service
        jack_detection = _create_jack_detection()

        backend = WM8960AudioBackend(
            playback_subject,
            jack_detection=jack_detection,
        )
        logger.info("✅ WM8960 Audio Backend initialized successfully")
        return backend
    except Exception as e:
        logger.error(f"❌ Failed to initialize WM8960 audio: {e}")
        logger.warning("⚠️️ Falling back to MockAudioBackend")

        from .mock_audio_backend import MockAudioBackend

        return MockAudioBackend(playback_subject)


def _create_jack_detection() -> JackDetectionProtocol | None:
    """Create jack detection service if enabled.

    Returns:
        JackDetectionProtocol or None if disabled/unavailable.
    """
    global _jack_detection_instance

    # Return existing instance if already created
    if _jack_detection_instance is not None:
        return _jack_detection_instance

    # Check if jack detection is enabled
    if not config.hardware.headphone_detect_enabled:
        logger.info("🎧 Jack detection disabled in configuration")
        return None

    try:
        from app.src.infrastructure.hardware.audio import JackDetectionFactory

        logger.info("🎧 Creating jack detection service...")
        _jack_detection_instance = JackDetectionFactory.create(config.hardware)

        # Initialize jack detection (async initialization will be done lazily)
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            # If there's a running loop, schedule initialization
            loop.create_task(_initialize_jack_detection(_jack_detection_instance))
        except RuntimeError:
            # No running loop, run synchronously
            asyncio.run(_initialize_jack_detection(_jack_detection_instance))

        logger.info("✅ Jack detection service created")
        return _jack_detection_instance

    except Exception as e:
        logger.warning(f"⚠️ Failed to create jack detection: {e}")
        return None


async def _initialize_jack_detection(jack_detection: JackDetectionProtocol) -> None:
    """Initialize jack detection asynchronously."""
    try:
        await jack_detection.initialize()
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize jack detection: {e}")


def get_jack_detection() -> JackDetectionProtocol | None:
    """Get the jack detection instance if available.

    Returns:
        JackDetectionProtocol or None if not available.
    """
    return _jack_detection_instance


async def cleanup_jack_detection() -> None:
    """Clean up jack detection resources."""
    global _jack_detection_instance

    if _jack_detection_instance is not None:
        try:
            await _jack_detection_instance.cleanup()
            logger.info("🎧 Jack detection cleaned up")
        except Exception as e:
            logger.warning(f"⚠️ Error cleaning up jack detection: {e}")
        finally:
            _jack_detection_instance = None
