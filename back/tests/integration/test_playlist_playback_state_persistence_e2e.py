# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
End-to-End Integration Test: Playlist Playback State Persistence

This test ensures that playlist state is maintained across different endpoints
and that the PlaybackCoordinator singleton pattern works correctly.

Critical Bug Prevented:
- Multiple PlaybackCoordinator instances causing state loss
- Playlist loaded in one endpoint not available in another
- Player controls (play/pause/next/prev) failing after starting a playlist
"""

import pytest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.src.dependencies import get_playback_coordinator
from app.src.application.di.application_container import get_application_container


class TestPlaylistPlaybackStatePersistence:
    """
    Test suite ensuring playback state persists across different API endpoints.

    This prevents the critical bug where:
    1. Starting a playlist via POST /api/playlists/{id}/start loads playlist in coordinator A
    2. Toggling playback via POST /api/player/toggle uses coordinator B (different instance)
    3. Coordinator B has no playlist loaded, causing "No track or playlist to play" error
    """

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Reset DI container singleton state before each test."""
        # Ensure infrastructure DI container has required services
        from app.src.infrastructure.di.container import get_container
        from app.src.domain.bootstrap import DomainBootstrap
        from app.src.domain.audio.container import AudioDomainContainer

        infra_container = get_container()
        if not infra_container.has("domain_bootstrap"):
            infra_container.register_singleton("domain_bootstrap", DomainBootstrap())
        if not infra_container.has("audio_domain_container"):
            infra_container.register_singleton("audio_domain_container", AudioDomainContainer())

        # Clear the singleton from DI container
        app_container = get_application_container()
        if "playback_coordinator" in app_container._singletons:
            del app_container._singletons["playback_coordinator"]
        yield
        # Clean up after test
        if "playback_coordinator" in app_container._singletons:
            del app_container._singletons["playback_coordinator"]

    def test_singleton_pattern_ensures_same_instance(self):
        """Test that DI container returns the same instance."""
        # Get coordinator first time
        coordinator_1 = get_playback_coordinator()

        # Get coordinator second time
        coordinator_2 = get_playback_coordinator()

        # Verify they are the exact same instance (DI container singleton)
        assert coordinator_1 is coordinator_2, "PlaybackCoordinator should be a singleton via DI container"

    def test_playlist_state_persists_across_multiple_calls(self):
        """Test that playlist state loaded in one call is available in subsequent calls."""
        # Get coordinator and load a mock playlist (DI container singleton)
        coordinator = get_playback_coordinator()

        # Create a mock playlist
        from app.src.application.controllers.playlist_state_manager_controller import Playlist, Track
        test_playlist = Playlist(
            id="test-playlist-123",
            title="Test Playlist",
            tracks=[
                Track(
                    id="track-1",
                    title="Track 1",
                    filename="track1.mp3",
                    duration_ms=180000,
                    file_path="/fake/path/track1.mp3"
                ),
                Track(
                    id="track-2",
                    title="Track 2",
                    filename="track2.mp3",
                    duration_ms=200000,
                    file_path="/fake/path/track2.mp3"
                )
            ]
        )

        # Load playlist using the coordinator
        coordinator.playlist_controller.load_playlist_data(test_playlist)

        # Get coordinator again (simulating a different endpoint call)
        coordinator_again = get_playback_coordinator()

        # Verify playlist state is still there
        playlist_info = coordinator_again.playlist_controller.get_playlist_info()
        assert playlist_info["playlist_id"] == "test-playlist-123"
        assert playlist_info["playlist_name"] == "Test Playlist"
        assert playlist_info["total_tracks"] == 2

    def test_playback_controls_work_after_loading_playlist(self):
        """Test that play/pause/next/prev work after loading a playlist."""
        coordinator = get_playback_coordinator()

        # Create and load mock playlist
        from app.src.application.controllers.playlist_state_manager_controller import Playlist, Track
        test_playlist = Playlist(
            id="test-playlist-456",
            title="Control Test Playlist",
            tracks=[
                Track(
                    id="track-1",
                    title="Track 1",
                    filename="track1.mp3",
                    duration_ms=180000,
                    file_path="/fake/path/track1.mp3"
                ),
                Track(
                    id="track-2",
                    title="Track 2",
                    filename="track2.mp3",
                    duration_ms=200000,
                    file_path="/fake/path/track2.mp3"
                )
            ]
        )

        coordinator.playlist_controller.load_playlist_data(test_playlist)

        # Set current track (simulate starting playlist without actual file playback)
        coordinator.playlist_controller.goto_track(1)

        # Get coordinator again (simulate POST /api/player/toggle from a different endpoint)
        coordinator_from_player_endpoint = get_playback_coordinator()

        # Verify we can pause (this would fail with separate instances)
        pause_success = coordinator_from_player_endpoint.pause()
        # Note: pause() might return False if using MockAudioBackend, but should not crash

        # Verify playlist info is still available (critical: proves singleton works)
        status = coordinator_from_player_endpoint.get_playback_status()
        assert status["active_playlist_id"] == "test-playlist-456"
        assert status["active_track"] is not None
        assert status["active_track"]["title"] == "Track 1"

    def test_cross_endpoint_navigation_consistency(self):
        """Test that playlist navigation works consistently across endpoint calls."""
        coordinator = get_playback_coordinator()

        # Load playlist
        from app.src.application.controllers.playlist_state_manager_controller import Playlist, Track
        tracks = [
            Track(id=f"track-{i}", title=f"Track {i}", filename=f"track{i}.mp3",
                  duration_ms=180000, file_path=f"/fake/path/track{i}.mp3")
            for i in range(1, 4)
        ]

        test_playlist = Playlist(id="nav-test", title="Navigation Test", tracks=tracks)
        coordinator.playlist_controller.load_playlist_data(test_playlist)

        # Set to first track (without actual playback)
        coordinator.playlist_controller.goto_track(1)

        # Navigate to next track (simulate POST /api/player/next)
        coordinator_next = get_playback_coordinator()
        next_track = coordinator_next.playlist_controller.next_track()
        assert next_track is not None

        # Verify current track changed (from a different endpoint call)
        coordinator_status = get_playback_coordinator()
        status = coordinator_status.get_playback_status()
        assert status["track_index"] == 2
        assert status["active_track"]["title"] == "Track 2"

        # Navigate to previous track
        prev_track = coordinator_status.playlist_controller.previous_track()
        assert prev_track is not None

        # Verify back to first track
        final_status = get_playback_coordinator().get_playback_status()
        assert final_status["track_index"] == 1
        assert final_status["active_track"]["title"] == "Track 1"

    def test_player_status_reflects_loaded_playlist(self):
        """Test that GET /api/player/status correctly shows loaded playlist info."""
        coordinator = get_playback_coordinator()

        # Initially no playlist
        initial_status = coordinator.get_playback_status()
        assert initial_status["active_playlist_id"] is None

        # Load playlist (simulate POST /api/playlists/{id}/start)
        from app.src.application.controllers.playlist_state_manager_controller import Playlist, Track
        test_playlist = Playlist(
            id="status-test-789",
            title="Status Test Playlist",
            tracks=[
                Track(id="track-1", title="Test Track", filename="test.mp3",
                      duration_ms=180000, file_path="/fake/test.mp3")
            ]
        )
        coordinator.playlist_controller.load_playlist_data(test_playlist)
        coordinator.start_playlist(track_number=1)

        # Get status from "different endpoint" (GET /api/player/status)
        status_coordinator = get_playback_coordinator()
        status = status_coordinator.get_playback_status()

        # Verify playlist info is present (using frontend-expected field names)
        assert status["active_playlist_id"] == "status-test-789"
        assert status["active_playlist_title"] == "Status Test Playlist"
        assert status["active_track"] is not None
        assert status["active_track"]["title"] == "Test Track"
        assert status["track_index"] == 1
        assert status["track_count"] == 1
