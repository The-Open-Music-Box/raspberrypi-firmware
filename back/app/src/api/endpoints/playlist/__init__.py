# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Playlist API Module - Aggregator

This module provides a facade that aggregates all playlist API routers
while maintaining backward compatibility with the original monolithic structure.

Architecture Pattern: Facade + Direct Registration
Benefits:
- Single Responsibility: Each sub-module handles one concern
- Easy testing: Test each module independently
- Better maintainability: ~150 lines per file vs 898 lines
- Parallel development: No merge conflicts
- No router composition issues: Routes registered directly on main router
"""

from fastapi import APIRouter

from .playlist_read_api import PlaylistReadAPI
from .playlist_write_api import PlaylistWriteAPI
from .playlist_track_api import PlaylistTrackAPI
from .playlist_upload_api import PlaylistUploadAPI
from .playlist_nfc_api import PlaylistNfcAPI
from .playlist_playback_api import PlaylistPlaybackAPI


class PlaylistAPIRoutes:
    """
    Aggregator for all playlist API routes.

    This class maintains the same interface as the original monolithic class,
    but delegates to specialized sub-modules internally.

    Facade Pattern: Provides a unified interface to a set of interfaces in a subsystem.

    Updated Architecture:
    - Main router is created here with prefix
    - Sub-modules register routes directly on the main router
    - No router composition needed (avoids FastAPI limitations)
    """

    def __init__(
        self,
        playlist_service,
        broadcasting_service,
        operations_service=None,
        validation_service=None,
        upload_controller=None
    ):
        """Initialize playlist API routes aggregator.

        Args:
            playlist_service: Application service for playlist operations
            broadcasting_service: Service for real-time state broadcasting
            operations_service: Service for complex playlist operations (optional)
            validation_service: Service for request validation (optional)
            upload_controller: Controller for file upload operations (optional)
        """
        # Main router with prefix (matches original monolithic implementation)
        self.router = APIRouter(prefix="/api/playlists", tags=["playlists"])

        # Initialize all sub-modules by passing the main router
        # Each sub-module registers its routes directly on this router
        PlaylistReadAPI(playlist_service, self.router)
        PlaylistWriteAPI(
            playlist_service, broadcasting_service, self.router, validation_service
        )
        PlaylistTrackAPI(
            playlist_service, broadcasting_service, self.router, operations_service
        )
        PlaylistPlaybackAPI(
            playlist_service, broadcasting_service, self.router, operations_service
        )

        # Optional sub-modules (only if dependencies provided)
        if upload_controller:
            PlaylistUploadAPI(
                playlist_service, broadcasting_service, self.router, upload_controller
            )

        if operations_service:
            PlaylistNfcAPI(broadcasting_service, self.router, operations_service)

    def get_router(self) -> APIRouter:
        """Get the aggregated router.

        Returns:
            APIRouter: The router with all playlist endpoints registered.

        This method maintains backward compatibility with code that
        expects a single router object.
        """
        return self.router


# Backward compatibility: Export the main class
__all__ = ["PlaylistAPIRoutes"]
