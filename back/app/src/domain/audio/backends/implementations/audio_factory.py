# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Audio backend factory for creating platform-specific audio players.

Provides factory functions to create appropriate audio backends based on the
current platform and hardware configuration, supporting macOS, Raspberry Pi,
and mock implementations for testing.

Note: Jack detection is created via infrastructure layer and injected via
dependency injection to maintain DDD architecture boundaries.
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


def get_audio_backend(
    playback_subject: PlaybackSubject | None = None,
    jack_detection: JackDetectionProtocol | None = None,
) -> AudioBackendProtocol:
    """Create just the audio backend without unified player wrapper.

    This is the recommended way for new architecture using PlaybackCoordinator.

    Args:
        playback_subject: Optional notification service for playback events
        jack_detection: Optional jack detection service (injected from infrastructure)

    Returns:
        AudioBackendProtocol: Platform-appropriate audio backend
    """
    return cast(AudioBackendProtocol, _create_audio_backend(playback_subject, jack_detection))


@handle_errors("_create_audio_backend")
def _create_audio_backend(
    playback_subject: PlaybackSubject | None = None,
    jack_detection: JackDetectionProtocol | None = None,
) -> AudioBackendProtocol:
    """Create the appropriate audio backend based on platform and configuration.

    Args:
        playback_subject: Optional notification service for playbook events
        jack_detection: Optional jack detection service (injected from infrastructure)

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


def setup_headphone_broadcasting(socketio) -> bool:
    """Set up headphone status broadcasting via Socket.IO.

    This function connects the WM8960AudioBackend's headphone state change
    callback to Socket.IO broadcasting, enabling real-time frontend updates
    when headphones are plugged or unplugged.

    Args:
        socketio: Socket.IO server instance for broadcasting.

    Returns:
        bool: True if broadcasting was set up successfully, False otherwise.
    """
    try:
        from app.src.domain.audio.container import audio_domain_container

        # Check if audio domain is initialized
        if not audio_domain_container.is_initialized:
            logger.warning("⚠️ Audio domain not initialized, cannot setup headphone broadcasting")
            return False

        backend = audio_domain_container.backend

        # Check if backend supports headphone state change callback
        if not hasattr(backend, "set_headphone_state_change_callback"):
            logger.info("ℹ️ Audio backend does not support headphone detection")
            return False

        # Import socket events here to avoid circular imports
        from app.src.common.socket_events import (
            SocketEventBuilder,
            SocketEventType,
        )

        # Create a sequence generator for server_seq
        _headphone_broadcast_seq = 0

        async def broadcast_headphone_status(connected: bool) -> None:
            """Broadcast headphone status change to all clients."""
            nonlocal _headphone_broadcast_seq
            _headphone_broadcast_seq += 1

            try:
                event_data = SocketEventBuilder.create_headphone_status_event(
                    connected=connected,
                    server_seq=_headphone_broadcast_seq,
                )

                # Emit to the 'playlists' room (global state)
                await socketio.emit(
                    SocketEventType.STATE_HEADPHONE_STATUS.value,
                    event_data,
                    room="playlists",
                )

                logger.info(
                    f"🎧 Broadcasted headphone status: {'connected' if connected else 'disconnected'}"
                )
            except Exception as e:
                logger.error(f"❌ Failed to broadcast headphone status: {e}")

        def on_headphone_state_changed(connected: bool) -> None:
            """Synchronous callback that schedules async broadcast."""
            import asyncio

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(broadcast_headphone_status(connected))
            except RuntimeError:
                # No running event loop, log warning
                logger.warning("⚠️ No event loop for headphone status broadcast")

        # Register the callback with the audio backend
        backend.set_headphone_state_change_callback(on_headphone_state_changed)
        logger.info("✅ Headphone status broadcasting enabled")
        return True

    except Exception as e:
        logger.warning(f"⚠️ Failed to setup headphone broadcasting: {e}")
        return False
