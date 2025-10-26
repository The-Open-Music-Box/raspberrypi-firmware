# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
End-to-end integration tests for NFC playlist lookup flow.

This test ensures that the complete flow from NFC tag scan to playlist retrieval works correctly.
"""

import pytest
import uuid
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track
from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
from app.src.domain.data.services.playlist_service import PlaylistService
from app.src.domain.data.services.track_service import TrackService
from app.src.application.services.data_application_service import DataApplicationService
from app.src.application.controllers.playback_coordinator_controller import PlaybackCoordinator
from app.src.domain.audio.backends.implementations.mock_audio_backend import MockAudioBackend


@pytest.mark.asyncio
class TestNfcPlaylistLookupE2E:
    """End-to-end tests for NFC playlist lookup."""

    @pytest.fixture
    async def playlist_repo(self):
        """Get playlist repository instance."""
        return PureSQLitePlaylistRepository()

    @pytest.fixture
    async def track_service(self, playlist_repo):
        """Get track service instance."""
        # TrackService needs both track_repo and playlist_repo
        # PureSQLitePlaylistRepository handles both playlists and tracks
        return TrackService(playlist_repo, playlist_repo)

    @pytest.fixture
    async def playlist_service(self, playlist_repo, track_service):
        """Get playlist service instance."""
        return PlaylistService(playlist_repo, track_service._track_repo)

    @pytest.fixture
    async def data_app_service(self, playlist_service, track_service):
        """Get data application service instance."""
        return DataApplicationService(playlist_service, track_service)

    async def test_nfc_lookup_complete_flow(self, playlist_repo, playlist_service, data_app_service):
        """Test complete NFC lookup flow from tag scan to playlist retrieval.

        This test covers:
        1. Creating a playlist with tracks
        2. Associating an NFC tag with the playlist
        3. Looking up the playlist by NFC tag (simulating NFC scan)
        4. Verifying the retrieved playlist has all expected data
        """
        # Setup: Create a playlist with tracks
        test_nfc_tag = f"test-nfc-{uuid.uuid4().hex[:8]}"
        playlist_id = str(uuid.uuid4())

        # Create playlist entity with tracks
        playlist = Playlist(
            id=playlist_id,
            title=f"Test NFC Playlist {uuid.uuid4().hex[:8]}",
            description="Test playlist for NFC lookup",
            nfc_tag_id=test_nfc_tag,
            tracks=[
                Track(
                    id=str(uuid.uuid4()),
                    track_number=1,
                    title="Track 1",
                    filename="track1.mp3",
                    file_path="/fake/path/track1.mp3"
                ),
                Track(
                    id=str(uuid.uuid4()),
                    track_number=2,
                    title="Track 2",
                    filename="track2.mp3",
                    file_path="/fake/path/track2.mp3"
                )
            ]
        )

        # Save playlist with NFC tag association
        await playlist_repo.save(playlist)

        try:
            # ACT: Simulate NFC tag scan - lookup playlist by NFC tag
            # This is the exact flow that happens when an NFC tag is scanned
            result = await data_app_service.get_playlist_by_nfc_use_case(test_nfc_tag)

            # ASSERT: Verify playlist was found and has correct data
            assert result is not None, f"Playlist not found for NFC tag {test_nfc_tag}"
            assert result['id'] == playlist_id
            assert result['title'] == playlist.title or result['name'] == playlist.title
            assert result['nfc_tag_id'] == test_nfc_tag
            assert 'tracks' in result
            assert len(result['tracks']) == 2
            assert result['track_count'] == 2

            # Verify track data
            assert result['tracks'][0]['title'] == "Track 1"
            assert result['tracks'][1]['title'] == "Track 2"

        finally:
            # Cleanup: Delete test playlist
            await playlist_repo.delete(playlist_id)

    async def test_nfc_lookup_nonexistent_tag(self, data_app_service):
        """Test NFC lookup with a tag that doesn't exist."""
        nonexistent_tag = f"nonexistent-{uuid.uuid4().hex}"

        result = await data_app_service.get_playlist_by_nfc_use_case(nonexistent_tag)

        assert result is None, "Expected None for nonexistent NFC tag"

    async def test_nfc_lookup_repository_interface_compatibility(self, playlist_repo):
        """Test that repository correctly implements find_by_nfc_tag interface method.

        This test explicitly verifies that the repository has the correct method name
        as defined in the PlaylistRepositoryProtocol interface.
        """
        # Verify repository has the correct interface method
        assert hasattr(playlist_repo, 'find_by_nfc_tag'), \
            "Repository must implement find_by_nfc_tag method"

        # Verify method is callable
        assert callable(playlist_repo.find_by_nfc_tag), \
            "find_by_nfc_tag must be callable"

        # Test with nonexistent tag returns None
        result = await playlist_repo.find_by_nfc_tag("nonexistent-tag")
        assert result is None, "Expected None for nonexistent tag"

    async def test_nfc_lookup_repository_direct(self, playlist_repo):
        """Test NFC lookup directly on repository (bypasses service layers)."""
        # Create a playlist with NFC tag
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = f"test-nfc-{uuid.uuid4().hex[:8]}"

        playlist = Playlist(
            id=playlist_id,
            title=f"Direct Test Playlist {uuid.uuid4().hex[:8]}",
            description="Test playlist",
            nfc_tag_id=test_nfc_tag,
            tracks=[]
        )

        await playlist_repo.save(playlist)

        try:
            # Test direct repository lookup
            result = await playlist_repo.find_by_nfc_tag(test_nfc_tag)

            assert result is not None, f"Playlist not found via direct repository lookup for NFC tag {test_nfc_tag}"
            assert result.id == playlist_id
            assert result.nfc_tag_id == test_nfc_tag

        finally:
            # Cleanup
            await playlist_repo.delete(playlist_id)

    async def test_nfc_playback_triggers_socketio_broadcast(self, playlist_repo, playlist_service, data_app_service):
        """Test that NFC-triggered playlist playback broadcasts Socket.IO events.

        This test verifies the fix for the issue where NFC-triggered playback
        didn't broadcast state to the frontend, causing the UI to not show
        the playing playlist information.

        This test covers:
        1. Creating a playlist with NFC tag
        2. Creating a PlaybackCoordinator with mocked Socket.IO
        3. Simulating NFC tag scan via handle_tag_scanned
        4. Verifying Socket.IO broadcasts are triggered
        """
        import tempfile
        import os

        # Setup: Create a temporary audio file for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake audio file
            test_file_path = os.path.join(tmpdir, "test1.mp3")
            with open(test_file_path, 'w') as f:
                f.write("fake audio content")

            # Create a playlist with NFC tag and tracks
            test_nfc_tag = f"test-nfc-{uuid.uuid4().hex[:8]}"
            playlist_id = str(uuid.uuid4())

            playlist = Playlist(
                id=playlist_id,
                title=f"Test NFC Broadcast Playlist {uuid.uuid4().hex[:8]}",
                description="Test playlist for Socket.IO broadcast",
                nfc_tag_id=test_nfc_tag,
                tracks=[
                    Track(
                        id=str(uuid.uuid4()),
                        track_number=1,
                        title="Test Track 1",
                        filename="test1.mp3",
                        file_path=test_file_path,
                        duration_ms=180000
                    )
                ]
            )

            await playlist_repo.save(playlist)

            try:
                # Create a mock Socket.IO server
                mock_socketio = AsyncMock()
                mock_socketio.emit = AsyncMock()

                # Create mock audio backend
                mock_audio_backend = MockAudioBackend()

                # Create PlaybackCoordinator with Socket.IO (inject playlist_service and data_app_service)
                coordinator = PlaybackCoordinator(
                    audio_backend=mock_audio_backend,
                    playlist_service=playlist_service,
                    upload_folder=tmpdir,
                    socketio=mock_socketio,
                    data_application_service=data_app_service
                )

                # ACT: Simulate NFC tag scan
                await coordinator.handle_tag_scanned(test_nfc_tag)

                # Wait for async processing
                await asyncio.sleep(0.3)

                # ASSERT: Verify Socket.IO broadcasts were triggered
                # The coordinator should have called socketio.emit at least once
                assert mock_socketio.emit.called, \
                    "Socket.IO emit was not called - NFC playback did not broadcast state"

                # Get all the calls to socketio.emit
                emit_calls = mock_socketio.emit.call_args_list

                # Verify we have broadcast calls
                assert len(emit_calls) > 0, \
                    "No Socket.IO broadcasts were made during NFC playlist start"

                # Check for playlist_started event
                event_types = [call[0][0] for call in emit_calls]  # First positional arg is event type

                # We expect either:
                # 1. 'state:playlist_started' event
                # 2. 'state:player' event with operation 'playlist_started'
                has_playlist_started = any('playlist_started' in event for event in event_types)
                has_player_state = any('state:player' in event for event in event_types)

                assert has_playlist_started or has_player_state, \
                    f"Expected playlist_started or player state broadcast, got events: {event_types}"

            finally:
                # Cleanup
                coordinator.cleanup()
                await playlist_repo.delete(playlist_id)
