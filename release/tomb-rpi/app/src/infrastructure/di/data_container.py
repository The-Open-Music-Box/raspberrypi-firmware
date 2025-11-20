# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Data domain dependency injection container.

Provides registration of data domain services following Clean Architecture principles.
"""

import logging

from app.src.infrastructure.di.container import get_container
from app.src.domain.data.services.playlist_service import PlaylistService
from app.src.domain.data.services.track_service import TrackService
from app.src.infrastructure.repositories.data_playlist_repository import DataPlaylistRepository
from app.src.infrastructure.repositories.data_track_repository import DataTrackRepository
from app.src.infrastructure.adapters.pure_playlist_repository_adapter import PurePlaylistRepositoryAdapter

logger = logging.getLogger(__name__)


def register_data_domain_services() -> None:
    """Register all data domain services in the DI container."""
    container = get_container()

    # Register database manager
    def create_database_manager():
        from app.src.data.database_manager import DatabaseManager
        return DatabaseManager()

    # Register base playlist repository (PureSQLitePlaylistRepository)
    def create_playlist_repository():
        from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
        return PureSQLitePlaylistRepository()

    # Register repository factories
    def create_data_playlist_repository():
        # Get the existing SQLite repository
        sqlite_repo = container.get("playlist_repository")
        return DataPlaylistRepository(sqlite_repo)

    def create_data_track_repository():
        # Get the existing SQLite repository
        sqlite_repo = container.get("playlist_repository")
        return DataTrackRepository(sqlite_repo)

    def create_playlist_service():
        # PlaylistService expects PureSQLitePlaylistRepository, not DataPlaylistRepository wrapper
        playlist_repo = container.get("playlist_repository")
        track_repo = container.get("playlist_repository")  # TrackService also uses playlist_repository
        return PlaylistService(playlist_repo, track_repo)

    def create_track_service():
        # TrackService expects DataTrackRepository which provides the track protocol methods
        track_repo = container.get("data_track_repository")
        playlist_repo = container.get("playlist_repository")
        return TrackService(track_repo, playlist_repo)

    def create_playlist_repository_adapter():
        # PurePlaylistRepositoryAdapter provides domain-level repository access
        return PurePlaylistRepositoryAdapter()

    # Application services moved to ApplicationContainer for Clean Architecture

    # Register services
    container.register_factory("database_manager", create_database_manager)
    container.register_factory("playlist_repository", create_playlist_repository)
    container.register_factory("data_playlist_repository", create_data_playlist_repository)
    container.register_factory("data_track_repository", create_data_track_repository)
    container.register_factory("data_playlist_service", create_playlist_service)
    container.register_factory("data_track_service", create_track_service)
    container.register_factory("playlist_repository_adapter", create_playlist_repository_adapter)
    # Data application service registered in ApplicationContainer

    logger.info("✅ Data domain services registered in DI container")


def get_data_playlist_service() -> PlaylistService:
    """Get the data playlist service.

    Returns:
        PlaylistService instance
    """
    return get_container().get("data_playlist_service")


def get_data_track_service() -> TrackService:
    """Get the data track service.

    Returns:
        TrackService instance
    """
    return get_container().get("data_track_service")


# get_data_application_service moved to dependencies.py using ApplicationContainer
