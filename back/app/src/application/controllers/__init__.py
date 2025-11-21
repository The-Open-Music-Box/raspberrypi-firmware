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

from .playlist_state_manager_controller import PlaylistStateManager, Playlist, Track
from .track_resolver_controller import TrackResolver
from .audio_player_controller import AudioPlayer, PlaybackState
from .playlist_controller import PlaylistController
from .playback_coordinator_controller import PlaybackCoordinator
from .playback_controller import PlaybackController
from .upload_controller import UploadController
from .physical_controls_controller import PhysicalControlsManager

__all__ = [
    "PlaylistStateManager",
    "Playlist",
    "Track",
    "TrackResolver",
    "AudioPlayer",
    "PlaybackState",
    "PlaylistController",
    "PlaybackCoordinator",
    "PlaybackController",
    "UploadController",
    "PhysicalControlsManager",
]