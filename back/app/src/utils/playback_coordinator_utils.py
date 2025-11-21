# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Factory utilities for PlaybackCoordinator.

This module provides factory functions for creating PlaybackCoordinator instances
using proper dependency injection patterns.
"""

from typing import Optional
from app.src.monitoring import get_logger

logger = get_logger(__name__)


def create_playback_coordinator(socketio=None):
    """Create a new PlaybackCoordinator instance with proper backend.

    Args:
        socketio: Socket.IO server instance for state broadcasting (optional)

    Returns:
        PlaybackCoordinator instance
    """
    from app.src.application.controllers.playback_coordinator_controller import PlaybackCoordinator
    from app.src.infrastructure.di.container import get_container
    from app.src.dependencies import get_data_playlist_service

    # Get dependencies from DI container
    container = get_container()
    domain_bootstrap = container.get("domain_bootstrap")
    audio_domain_container = container.get("audio_domain_container")

    # Initialize domain if not already done
    if not domain_bootstrap.is_initialized:
        domain_bootstrap.initialize()

    # Get domain playlist service via DI
    playlist_service = get_data_playlist_service()

    # Get audio backend from domain container
    if audio_domain_container.is_initialized:
        audio_backend = audio_domain_container.backend
        logger.info(f"✅ Creating PlaybackCoordinator with backend: {type(audio_backend).__name__}")
        return PlaybackCoordinator(
            audio_backend,
            playlist_service=playlist_service,
            socketio=socketio
        )

    # Fallback: create with mock backend
    from app.src.domain.audio.backends.implementations.mock_audio_backend import MockAudioBackend
    logger.warning("⚠️ Using MockAudioBackend fallback for PlaybackCoordinator")
    return PlaybackCoordinator(
        MockAudioBackend(),
        playlist_service=playlist_service,
        socketio=socketio
    )


def set_playback_coordinator_socketio(socketio):
    """Set Socket.IO instance on the PlaybackCoordinator from DI container.

    This allows late binding of Socket.IO after coordinator initialization.

    Args:
        socketio: Socket.IO server instance
    """
    # Import at function level to avoid circular dependency
    from app.src.infrastructure.di.container import get_container
    from app.src.application.di.application_container import get_application_container

    try:
        app_container = get_application_container()
        coordinator = app_container.get("playback_coordinator")
        if coordinator is not None:
            coordinator._socketio = socketio
            logger.info("✅ Socket.IO instance set on PlaybackCoordinator")
        else:
            logger.warning("⚠️ PlaybackCoordinator is None, cannot set Socket.IO")
    except Exception as e:
        logger.warning(f"⚠️ Could not get PlaybackCoordinator to set Socket.IO: {e}")