# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Audio Services Factory (Infrastructure Layer).

This module handles the creation and lifecycle management of audio-related
infrastructure services, including jack detection. It serves as the integration
point between the infrastructure layer and the domain layer, respecting DDD
architecture boundaries.

The jack detection service is created here and injected into the domain's
audio backend factory to maintain proper dependency direction (infrastructure
depends on domain, not vice versa).
"""

import asyncio
from typing import TYPE_CHECKING

from app.src.config import config
from app.src.domain.protocols.jack_detection_protocol import JackDetectionProtocol
from app.src.monitoring import get_logger

from .jack_detection_factory import JackDetectionFactory

if TYPE_CHECKING:
    from app.src.domain.protocols.audio_backend_protocol import AudioBackendProtocol
    from app.src.domain.protocols.notification_protocol import PlaybackNotifierProtocol

logger = get_logger(__name__)

# Module-level storage for jack detection lifecycle management
_jack_detection_instance: JackDetectionProtocol | None = None


def create_jack_detection() -> JackDetectionProtocol | None:
    """Create jack detection service if enabled.

    This is the infrastructure-level factory function that creates the
    jack detection service. It handles configuration checking and
    initialization scheduling.

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
        logger.info("🎧 Creating jack detection service...")
        _jack_detection_instance = JackDetectionFactory.create(config.hardware)

        # Initialize jack detection (async initialization will be done lazily)
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


def create_audio_backend_with_jack_detection(
    playback_subject: "PlaybackNotifierProtocol | None" = None,
) -> "AudioBackendProtocol":
    """Create audio backend with jack detection injected.

    This is the main factory function that creates the audio backend
    with proper dependency injection of jack detection. It respects
    DDD architecture by keeping infrastructure concerns in this layer.

    Args:
        playback_subject: Optional notification service for playback events.

    Returns:
        AudioBackendProtocol: Configured audio backend with jack detection.
    """
    from app.src.domain.audio.backends.implementations.audio_factory import (
        get_audio_backend,
    )

    # Create jack detection service
    jack_detection = create_jack_detection()

    # Create and return audio backend with jack detection injected
    return get_audio_backend(
        playback_subject=playback_subject,
        jack_detection=jack_detection,
    )
