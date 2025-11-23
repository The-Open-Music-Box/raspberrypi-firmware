# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Application Controllers Package (DDD Architecture)

This package contains the clean architecture with separated responsibilities:

- PlaylistStateManager: Single source of truth for playlist state
- TrackResolver: File path resolution
- AudioPlayer: Pure audio control
- PlaylistController: Playlist management
- PlaybackCoordinator: Orchestration facade
- UnifiedController: Legacy unified controller
- PlaybackController: Legacy playback controller

Usage:
    from app.src.application.controllers import PlaybackCoordinator

    # Initialize with backend
    coordinator = PlaybackCoordinator(audio_backend)

    # Load and play playlist
    coordinator.load_playlist("playlist_id")
    coordinator.start_playlist()
"""

from .audio_player_controller import AudioPlayer, PlaybackState
from .physical_controls_controller import PhysicalControlsManager
from .playback_controller import PlaybackController
from .playback_coordinator_controller import PlaybackCoordinator
from .playlist_controller import PlaylistController
from .playlist_state_manager_controller import Playlist, PlaylistStateManager, Track
from .track_resolver_controller import TrackResolver
from .upload_controller import UploadController

__all__ = [
    "AudioPlayer",
    "PhysicalControlsManager",
    "PlaybackController",
    "PlaybackCoordinator",
    "PlaybackState",
    "Playlist",
    "PlaylistController",
    "PlaylistStateManager",
    "Track",
    "TrackResolver",
    "UploadController",
]
