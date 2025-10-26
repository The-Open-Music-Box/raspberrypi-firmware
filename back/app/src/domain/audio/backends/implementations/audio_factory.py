# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Audio backend factory for creating platform-specific audio players.

Provides factory functions to create appropriate audio backends based on the
current platform and hardware configuration, supporting macOS, Raspberry Pi,
and mock implementations for testing.
"""

import sys
from typing import Optional

from app.src.config import config
from app.src.domain.protocols.notification_protocol import PlaybackNotifierProtocol as PlaybackSubject
from app.src.monitoring import get_logger
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors

from app.src.domain.protocols.audio_backend_protocol import AudioBackendProtocol

logger = get_logger(__name__)


def get_audio_backend(
    playback_subject: Optional[PlaybackSubject] = None,
) -> AudioBackendProtocol:
    """Create just the audio backend without unified player wrapper.

    This is the recommended way for new architecture using PlaybackCoordinator.

    Args:
        playback_subject: Optional notification service for playback events

    Returns:
        AudioBackendProtocol: Platform-appropriate audio backend
    """
    return _create_audio_backend(playback_subject)




@handle_errors("_create_audio_backend")
def _create_audio_backend(
    playback_subject: Optional[PlaybackSubject] = None,
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

    elif sys.platform == "darwin":
        # Use macOS-specific audio backend with Core Audio
        from .macos_audio_backend import MacOSAudioBackend

        logger.info("🍎 Creating MacOSAudioBackend...")
        backend = MacOSAudioBackend(playback_subject)
        logger.info("✅ macOS Audio Backend initialized successfully")
        return backend

    else:
        # Try to initialize hardware audio backend (WM8960 for Raspberry Pi/Linux)
        try:
            from .wm8960_audio_backend import WM8960AudioBackend

            logger.info("🔊 Creating WM8960AudioBackend...")
            backend = WM8960AudioBackend(playback_subject)
            logger.info("✅ WM8960 Audio Backend initialized successfully")
            return backend
        except Exception as e:
            logger.error(f"❌ Failed to initialize WM8960 audio: {e}")
            logger.warning("⚠️️ Falling back to MockAudioBackend")

            from .mock_audio_backend import MockAudioBackend

            return MockAudioBackend(playback_subject)
