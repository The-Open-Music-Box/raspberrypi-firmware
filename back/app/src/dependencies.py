# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Dependency providers for FastAPI DI (Depends pattern).

This module provides clean dependency injection functions for FastAPI routes,
using the DI Container to avoid circular dependencies.
"""

from app.src.infrastructure.di.container import get_container
from app.src.application.di.application_container import get_application_container
from app.src.monitoring import get_logger

logger = get_logger(__name__)

# Note: Containers are retrieved via functions to avoid module-level caching
# Use get_container() and get_application_container() instead


def get_config():
    """Dependency provider for the config singleton.

    Returns:
        The configuration object from DI container.
    """
    return get_container().get("config")


def get_domain_bootstrap():
    """Get the domain bootstrap instance for pure DDD architecture.

    Returns:
        The domain bootstrap instance providing access to domain services.
    """
    return get_container().get("domain_bootstrap")


def get_audio_service():
    """Retrieve the audio application service from domain architecture.

    Returns:
        The audio application service instance.
    """
    return get_application_container().get("audio_application_service")


def get_playlist_repository():
    """Retrieve the pure DDD playlist repository instance.

    Returns:
        The pure DDD playlist repository implementation.
    """
    return get_container().get("playlist_repository")


def get_playlist_repository_adapter():
    """Retrieve the playlist repository adapter instance.

    Returns:
        The playlist repository adapter for domain operations.
    """
    return get_container().get("playlist_repository_adapter")


def get_data_application_service():
    """Retrieve the data application service for use cases.

    Returns:
        The data application service instance.
    """
    return get_application_container().get("data_application_service")


def get_audio_application_service():
    """Retrieve the audio application service for use cases.

    Returns:
        The audio application service instance.
    """
    return get_application_container().get("audio_application_service")


# Data Domain Dependencies


def get_data_playlist_service():
    """Retrieve the data playlist service.

    Returns:
        The data playlist service instance.
    """
    return get_container().get("data_playlist_service")


def get_data_track_service():
    """Retrieve the data track service.

    Returns:
        The data track service instance.
    """
    return get_container().get("data_track_service")


def get_nfc_application_service():
    """Retrieve the NFC application service.

    Returns:
        The NFC application service instance.
    """
    return get_application_container().get("nfc_application_service")


def get_upload_application_service():
    """Retrieve the upload application service.

    Returns:
        The upload application service instance.
    """
    return get_application_container().get("upload_application_service")


def get_playback_coordinator():
    """Retrieve the playback coordinator singleton.

    Returns:
        The playback coordinator instance.
    """
    return get_application_container().get("playback_coordinator")


def get_database_manager():
    """Retrieve the database manager singleton.

    Returns:
        The database manager instance.
    """
    return get_container().get("database_manager")


def get_player_state_service():
    """Retrieve the player state service.

    Returns:
        The player state service instance.
    """
    return get_container().get("player_state_service")


def get_socket_config():
    """Retrieve the socket configuration.

    Returns:
        The socket configuration instance.
    """
    return get_container().get("socket_config")


def get_monitoring_config():
    """Retrieve the monitoring configuration.

    Returns:
        The monitoring configuration instance.
    """
    return get_container().get("monitoring_config")


def get_error_tracker():
    """Retrieve the error tracker.

    Returns:
        The error tracker instance.
    """
    return get_container().get("error_tracker")


def get_unified_error_handler():
    """Retrieve the unified error handler.

    Returns:
        The unified error handler instance.
    """
    return get_container().get("unified_error_handler")
