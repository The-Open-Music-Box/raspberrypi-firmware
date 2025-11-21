# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
End-to-end integration tests for the complete NFC association workflow.

Tests the critical user flow:
1. User presses association button
2. System enters association mode
3. User scans NFC tag
4. Tag is associated with playlist in database
5. User scans same tag again
6. Playlist starts playing

This test caught the bug where playlist_repository was None in NfcApplicationService,
preventing associations from being persisted to the database.
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track
from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
from app.src.domain.data.services.playlist_service import PlaylistService
from app.src.domain.data.services.track_service import TrackService
from app.src.application.services.data_application_service import DataApplicationService
from app.src.application.services.nfc_application_service import NfcApplicationService
from app.src.infrastructure.nfc.repositories.nfc_memory_repository import NfcMemoryRepository
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier


class MockNfcHardware:
    """Mock NFC hardware for testing."""

    def __init__(self):
        self._tag_detected_callback = None
        self._tag_removed_callback = None
        self._detecting = False

    def set_tag_detected_callback(self, callback):
        """Set tag detected callback."""
        self._tag_detected_callback = callback

    def set_tag_removed_callback(self, callback):
        """Set tag removed callback."""
        self._tag_removed_callback = callback

    async def start_detection(self):
        """Start detection."""
        self._detecting = True

    async def stop_detection(self):
        """Stop detection."""
        self._detecting = False

    def is_detecting(self):
        """Check if detecting."""
        return self._detecting

    def get_hardware_status(self):
        """Get hardware status."""
        return {
            "available": True,
            "detecting": self._detecting,
            "hardware_type": "mock"
        }

    def simulate_tag_scan(self, tag_id: str):
        """Simulate a tag being scanned."""
        if self._tag_detected_callback:
            self._tag_detected_callback(tag_id)

    def simulate_tag_removal(self):
        """Simulate tag removal."""
        if self._tag_removed_callback:
            self._tag_removed_callback()


@pytest.mark.asyncio
class TestNfcAssociationToPlaybackE2E:
    """End-to-end tests for complete NFC association and playback workflow."""

    @pytest.fixture
    async def playlist_repo(self):
        """Get playlist repository instance."""
        return PureSQLitePlaylistRepository()

    @pytest.fixture
    async def track_service(self, playlist_repo):
        """Get track service instance."""
        return TrackService(playlist_repo, playlist_repo)

    @pytest.fixture
    async def playlist_service(self, playlist_repo, track_service):
        """Get playlist service instance."""
        return PlaylistService(playlist_repo, track_service._track_repo)

    @pytest.fixture
    async def data_app_service(self, playlist_service, track_service):
        """Get data application service instance."""
        return DataApplicationService(playlist_service, track_service)

    @pytest.fixture
    async def nfc_hardware(self):
        """Get mock NFC hardware."""
        return MockNfcHardware()

    @pytest.fixture
    async def nfc_app_service(self, nfc_hardware, playlist_repo):
        """Get NFC application service with proper playlist repository."""
        nfc_repository = NfcMemoryRepository()
        # CRITICAL: Pass the playlist repository to enable database persistence
        service = NfcApplicationService(
            nfc_hardware=nfc_hardware,
            nfc_repository=nfc_repository,
            playlist_repository=playlist_repo  # This was None in the bug!
        )
        await service.start_nfc_system()
        return service

    async def test_complete_association_to_playback_flow(
        self,
        playlist_repo,
        playlist_service,
        data_app_service,
        nfc_app_service,
        nfc_hardware
    ):
        """
        Test the complete user workflow from association to playback.

        This is the exact scenario that was broken:
        1. User has a playlist
        2. User presses associate button and scans NFC tag
        3. Tag is associated with playlist
        4. User removes tag
        5. User scans tag again
        6. System should find the playlist and start playback

        This test FAILED before the fix because playlist_repository was None,
        so the association was never persisted to the database.
        """
        # Setup: Create a test playlist with tracks
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = uuid.uuid4().hex[:12]  # Hexadecimal format for TagIdentifier validation

        playlist = Playlist(
            id=playlist_id,
            title=f"Test Music Playlist {uuid.uuid4().hex[:8]}",
            description="Test playlist for association workflow",
            nfc_tag_id=None,  # No tag initially
            tracks=[
                Track(
                    id=str(uuid.uuid4()),
                    track_number=1,
                    title="Song One",
                    filename="song1.mp3",
                    file_path="/fake/path/song1.mp3",
                    duration_ms=180000
                ),
                Track(
                    id=str(uuid.uuid4()),
                    track_number=2,
                    title="Song Two",
                    filename="song2.mp3",
                    file_path="/fake/path/song2.mp3",
                    duration_ms=200000
                )
            ]
        )

        await playlist_repo.save(playlist)

        try:
            # Step 1: User presses association button (starts association session)
            session_result = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_id,
                timeout_seconds=60
            )
            assert session_result["status"] == "success", "Failed to start association session"
            session_id = session_result["session"]["session_id"]

            # Step 2: User scans NFC tag (hardware detects tag)
            # This triggers the association process
            nfc_hardware.simulate_tag_scan(test_nfc_tag)

            # Wait a bit for async processing
            import asyncio
            await asyncio.sleep(0.2)

            # Step 3: Verify association was saved to database
            # This is THE CRITICAL CHECK that failed before the fix
            playlist_from_db = await playlist_repo.find_by_id(playlist_id)
            assert playlist_from_db is not None, "Playlist not found in database"
            assert playlist_from_db.nfc_tag_id == test_nfc_tag, \
                f"NFC tag not persisted to database! Expected {test_nfc_tag}, got {playlist_from_db.nfc_tag_id}"

            # Step 4: User removes tag (optional, but part of real workflow)
            nfc_hardware.simulate_tag_removal()
            await asyncio.sleep(0.1)

            # Step 5: User scans tag again (to start playback)
            # This should find the playlist by NFC tag
            found_playlist = await data_app_service.get_playlist_by_nfc_use_case(test_nfc_tag)

            # Step 6: Verify the playlist was found and can be played
            assert found_playlist is not None, \
                f"Playlist not found by NFC tag {test_nfc_tag}! Association was not persisted."
            assert found_playlist['id'] == playlist_id
            assert found_playlist['nfc_tag_id'] == test_nfc_tag
            assert len(found_playlist['tracks']) == 2
            assert found_playlist['tracks'][0]['title'] == "Song One"

        finally:
            # Cleanup
            await playlist_repo.delete(playlist_id)
            await nfc_app_service.stop_nfc_system()

    async def test_association_persists_across_service_restarts(
        self,
        playlist_repo,
        nfc_hardware
    ):
        """
        Test that associations survive service restarts.

        This ensures the association is in the database, not just in memory.
        """
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = uuid.uuid4().hex[:12]  # Hexadecimal format

        # Create playlist
        playlist = Playlist(
            id=playlist_id,
            title=f"Persistent Test {uuid.uuid4().hex[:8]}",
            description="Test persistence",
            nfc_tag_id=None,
            tracks=[]
        )
        await playlist_repo.save(playlist)

        try:
            # First NFC service instance
            nfc_repo1 = NfcMemoryRepository()
            nfc_service1 = NfcApplicationService(
                nfc_hardware=nfc_hardware,
                nfc_repository=nfc_repo1,
                playlist_repository=playlist_repo  # MUST have this!
            )
            await nfc_service1.start_nfc_system()

            # Associate tag
            session_result = await nfc_service1.start_association_use_case(playlist_id)
            assert session_result["status"] == "success"

            nfc_hardware.simulate_tag_scan(test_nfc_tag)
            import asyncio
            await asyncio.sleep(0.2)

            await nfc_service1.stop_nfc_system()

            # Verify in database
            playlist_from_db = await playlist_repo.find_by_id(playlist_id)
            assert playlist_from_db.nfc_tag_id == test_nfc_tag, \
                "Association not persisted to database!"

            # Create NEW NFC service instance (simulating restart)
            nfc_repo2 = NfcMemoryRepository()  # Fresh memory repository
            nfc_service2 = NfcApplicationService(
                nfc_hardware=nfc_hardware,
                nfc_repository=nfc_repo2,
                playlist_repository=playlist_repo
            )
            await nfc_service2.start_nfc_system()

            # Should still find the playlist via database
            found_playlist = await playlist_repo.find_by_nfc_tag(test_nfc_tag)
            assert found_playlist is not None, \
                "Association lost after service restart! Not persisted properly."
            assert found_playlist.id == playlist_id

            await nfc_service2.stop_nfc_system()

        finally:
            # Cleanup
            await playlist_repo.delete(playlist_id)

    async def test_association_rejects_without_playlist_repository(
        self,
        nfc_hardware
    ):
        """
        Test that highlights the bug: when playlist_repository is None,
        associations are not persisted.

        This test documents the original bug behavior.
        """
        playlist_id = str(uuid.uuid4())
        test_nfc_tag = uuid.uuid4().hex[:12]  # Hexadecimal format

        # Create NFC service WITHOUT playlist repository (the bug!)
        nfc_repo = NfcMemoryRepository()
        buggy_service = NfcApplicationService(
            nfc_hardware=nfc_hardware,
            nfc_repository=nfc_repo,
            playlist_repository=None  # This was the bug!
        )
        await buggy_service.start_nfc_system()

        try:
            # Try to associate
            session_result = await buggy_service.start_association_use_case(playlist_id)
            assert session_result["status"] == "success"

            nfc_hardware.simulate_tag_scan(test_nfc_tag)
            import asyncio
            await asyncio.sleep(0.2)

            # Association will succeed in NFC memory, but NOT in playlist database
            # This is the bug: the UI shows success but the association isn't persistent!

        finally:
            await buggy_service.stop_nfc_system()
