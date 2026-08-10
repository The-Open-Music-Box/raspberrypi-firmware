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


def setup_headphone_broadcasting(socketio, sequence_generator=None) -> bool:
    """Set up headphone status broadcasting via Socket.IO.

    This function connects the WM8960AudioBackend's headphone state change
    callback to Socket.IO broadcasting, enabling real-time frontend updates
    when headphones are plugged or unplugged.

    Args:
        socketio: Socket.IO server instance for broadcasting.
        sequence_generator: Optional SequenceGenerator for server_seq.
            If provided, uses global sequence for consistency with other events.
            If None, uses a local counter (fallback for standalone usage).

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
        import asyncio

        from app.src.common.socket_events import (
            SocketEventBuilder,
            SocketEventType,
        )

        # Use provided sequence generator or fall back to local counter
        _use_global_seq = sequence_generator is not None
        _local_seq = 0  # Fallback if no sequence generator provided

        # Capture the main event loop for thread-safe callback scheduling
        # GPIO callbacks run in a separate thread without an event loop
        try:
            _main_loop = asyncio.get_running_loop()
        except RuntimeError:
            # Without an event loop, broadcasts will never work - return False
            logger.warning(
                "⚠️ No running event loop during headphone broadcasting setup - "
                "broadcasts will not work"
            )
            return False

        async def broadcast_headphone_status(connected: bool) -> None:
            """Broadcast headphone status change to all clients."""
            nonlocal _local_seq

            try:
                # Get server_seq from global sequence generator or local counter
                if _use_global_seq:
                    server_seq = await sequence_generator.get_next_global_seq()
                else:
                    _local_seq += 1
                    server_seq = _local_seq

                event_data = SocketEventBuilder.create_headphone_status_event(
                    connected=connected,
                    server_seq=server_seq,
                )

                # Emit to the 'playlists' room (global state)
                await socketio.emit(
                    SocketEventType.STATE_HEADPHONE_STATUS.value,
                    event_data,
                    room="playlists",
                )

                logger.info(
                    f"🎧 Broadcasted headphone status: {'connected' if connected else 'disconnected'} "
                    f"(seq: {server_seq}, global={_use_global_seq})"
                )
            except Exception as e:
                logger.error(f"❌ Failed to broadcast headphone status: {e}")

        def on_headphone_state_changed(connected: bool) -> None:
            """Synchronous callback that schedules async broadcast.

            This callback is called from the GPIO thread, so we must use
            run_coroutine_threadsafe to schedule the async broadcast on
            the main event loop.
            """
            # Note: _main_loop is guaranteed to be set (we return False otherwise)
            # but check for closed loop in case of shutdown
            if _main_loop.is_closed():
                logger.warning("⚠️ Event loop closed - cannot broadcast headphone status")
                return

            try:
                # Schedule the coroutine on the main event loop from this thread
                asyncio.run_coroutine_threadsafe(
                    broadcast_headphone_status(connected),
                    _main_loop
                )
            except Exception as e:
                logger.error(f"❌ Failed to schedule headphone broadcast: {e}")

        # Register the callback with the audio backend
        backend.set_headphone_state_change_callback(on_headphone_state_changed)

        if _use_global_seq:
            logger.info("✅ Headphone status broadcasting enabled (using global sequence)")
        else:
            logger.info("✅ Headphone status broadcasting enabled (using local sequence)")
        return True

    except Exception as e:
        logger.warning(f"⚠️ Failed to setup headphone broadcasting: {e}")
        return False
