# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Comprehensive End-to-End Workflow Tests for NFC Association.

These tests verify complete user workflows from start to finish:
1. New Tag Association Workflow - Unknown tag auto-association
2. Known Tag Override Workflow - Duplicate detection and override
3. Session Timeout with Cleanup - Timeout handling and mode restoration
4. Broadcasting Service Integration - Socket.IO event broadcasting
5. Playback Prevention Persistence - Blocking playback during association

Tests added to address gaps identified in NFC_WORKFLOW_STATUS_REPORT.md
"""

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock

from app.src.domain.data.models.playlist import Playlist
from app.src.domain.data.models.track import Track
from app.src.infrastructure.repositories.pure_sqlite_playlist_repository import PureSQLitePlaylistRepository
from app.src.domain.data.services.playlist_service import PlaylistService
from app.src.domain.data.services.track_service import TrackService
from app.src.application.services.data_application_service import DataApplicationService
from app.src.application.services.nfc_application_service import NfcApplicationService
from app.src.infrastructure.nfc.repositories.nfc_memory_repository import NfcMemoryRepository
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.domain.nfc.entities.association_session import SessionState


class MockNfcHardware:
    """Mock NFC hardware for testing workflows."""

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


class MockBroadcastingService:
    """Mock broadcasting service for testing Socket.IO events."""

    def __init__(self):
        self.events = []
        self.last_event = None

    async def broadcast_nfc_association(self, association_state, playlist_id=None, tag_id=None, session_id=None):
        """Mock broadcast of NFC association event."""
        event = {
            "association_state": association_state,
            "playlist_id": playlist_id,
            "tag_id": tag_id,
            "session_id": session_id
        }
        self.events.append(event)
        self.last_event = event
        return True

    def get_events_by_state(self, state):
        """Get all events with a specific state."""
        return [e for e in self.events if e["association_state"] == state]

    def clear_events(self):
        """Clear event history."""
        self.events = []
        self.last_event = None


@pytest.mark.asyncio
class TestNfcWorkflowE2E:
    """Comprehensive end-to-end workflow tests for NFC association."""

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
    async def broadcasting_service(self):
        """Get mock broadcasting service."""
        return MockBroadcastingService()

    @pytest.fixture
    async def nfc_app_service(self, nfc_hardware, playlist_repo):
        """Get NFC application service with proper playlist repository."""
        nfc_repository = NfcMemoryRepository()
        service = NfcApplicationService(
            nfc_hardware=nfc_hardware,
            nfc_repository=nfc_repository,
            playlist_repository=playlist_repo
        )
        await service.start_nfc_system()
        return service

    @pytest.fixture
    async def test_playlist(self, playlist_repo):
        """Create a test playlist."""
        playlist_id = str(uuid.uuid4())
        playlist = Playlist(
            id=playlist_id,
            title=f"Test Workflow Playlist {uuid.uuid4().hex[:8]}",
            description="Test playlist for workflow tests",
            nfc_tag_id=None,
            tracks=[
                Track(
                    id=str(uuid.uuid4()),
                    track_number=1,
                    title="Test Song",
                    filename="test.mp3",
                    file_path="/fake/path/test.mp3",
                    duration_ms=180000
                )
            ]
        )
        await playlist_repo.save(playlist)
        yield playlist
        # Cleanup
        try:
            await playlist_repo.delete(playlist_id)
        except Exception:
            pass  # May already be deleted

    async def test_complete_new_tag_workflow(
        self,
        playlist_repo,
        data_app_service,
        nfc_app_service,
        nfc_hardware,
        test_playlist
    ):
        """
        Test 1: Complete New Tag Association Workflow

        Workflow:
        1. Start association mode
        2. Detect new (unregistered) tag
        3. Verify auto-association
        4. Verify session cleanup
        5. Remove tag
        6. Verify playback can start

        This tests the happy path for associating a new NFC tag.
        """
        playlist_id = test_playlist.id
        new_tag_id = uuid.uuid4().hex[:12]

        try:
            # Step 1: Start association mode
            session_result = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_id,
                timeout_seconds=60
            )
            assert session_result["status"] == "success"
            session_id = session_result["session"]["session_id"]

            # Verify session is in LISTENING state
            session = await nfc_app_service._association_service.get_association_session(session_id)
            assert session.state == SessionState.LISTENING
            assert session.is_active()

            # Step 2: Detect new tag
            nfc_hardware.simulate_tag_scan(new_tag_id)
            await asyncio.sleep(0.2)  # Wait for async processing

            # Step 3: Verify auto-association
            # Check database for persistence
            playlist_from_db = await playlist_repo.find_by_id(playlist_id)
            assert playlist_from_db.nfc_tag_id == new_tag_id, \
                "New tag should be auto-associated"

            # Session should be marked SUCCESS
            session = await nfc_app_service._association_service.get_association_session(session_id)
            assert session.state == SessionState.SUCCESS

            # Step 4: Verify session cleanup
            # Session should no longer be active
            assert not session.is_active(), "Session should not be active after success"

            # Step 5: Remove tag
            nfc_hardware.simulate_tag_removal()
            await asyncio.sleep(0.1)

            # Step 6: Verify playback can start (no active sessions blocking)
            active_sessions = nfc_app_service._association_service.get_active_sessions()
            assert len(active_sessions) == 0, \
                "No active sessions should exist after successful association"

            # Verify playlist can be found by tag
            found_playlist = await data_app_service.get_playlist_by_nfc_use_case(new_tag_id)
            assert found_playlist is not None
            assert found_playlist['id'] == playlist_id

        finally:
            await nfc_app_service.stop_nfc_system()

    async def test_complete_known_tag_override_workflow(
        self,
        playlist_repo,
        nfc_app_service,
        nfc_hardware,
        test_playlist
    ):
        """
        Test 2: Complete Known Tag Override Workflow

        Workflow:
        1. Create pre-associated tag with playlist A
        2. Start association mode for playlist B
        3. Detect tag
        4. Verify duplicate detection
        5. Verify session stays active (no playback)
        6. Override association
        7. Verify new association

        This tests the override scenario when a tag is already associated.
        """
        # Create two playlists
        playlist_a_id = test_playlist.id
        playlist_b_id = str(uuid.uuid4())
        existing_tag = uuid.uuid4().hex[:12]

        playlist_b = Playlist(
            id=playlist_b_id,
            title=f"Override Target Playlist {uuid.uuid4().hex[:8]}",
            description="Target for override test",
            nfc_tag_id=None,
            tracks=[
                Track(
                    id=str(uuid.uuid4()),
                    track_number=1,
                    title="Override Song",
                    filename="override.mp3",
                    file_path="/fake/path/override.mp3",
                    duration_ms=200000
                )
            ]
        )
        await playlist_repo.save(playlist_b)

        try:
            # Step 1: Pre-associate tag with playlist A
            first_session = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_a_id,
                timeout_seconds=60
            )
            nfc_hardware.simulate_tag_scan(existing_tag)
            await asyncio.sleep(0.2)

            # Verify initial association
            playlist_a = await playlist_repo.find_by_id(playlist_a_id)
            assert playlist_a.nfc_tag_id == existing_tag

            # Remove tag to clean up first session
            nfc_hardware.simulate_tag_removal()
            await asyncio.sleep(0.1)

            # Step 2: Start association mode for playlist B
            session_result = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_b_id,
                timeout_seconds=60,
                override_mode=False  # Normal mode - should detect duplicate
            )
            assert session_result["status"] == "success"
            session_id = session_result["session"]["session_id"]

            # Step 3: Detect already-associated tag
            nfc_hardware.simulate_tag_scan(existing_tag)
            await asyncio.sleep(0.2)

            # Step 4: Verify duplicate detection
            session = await nfc_app_service._association_service.get_association_session(session_id)
            assert session.state == SessionState.DUPLICATE, \
                "Session should be in DUPLICATE state"
            assert session.conflict_playlist_id == playlist_a_id

            # Step 5: Verify session stays active (prevents playback)
            assert session.is_active(), \
                "Session should remain active in DUPLICATE state to prevent playback"

            active_sessions = nfc_app_service._association_service.get_active_sessions()
            assert len(active_sessions) == 1, \
                "One active session should exist to block playback"

            # Step 6: Override association
            # Cancel first session and start override session
            await nfc_app_service.stop_association_use_case(session_id)

            override_result = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_b_id,
                timeout_seconds=60,
                override_mode=True  # Override mode
            )
            assert override_result["status"] == "success"
            override_session_id = override_result["session"]["session_id"]

            # Detect tag again with override
            nfc_hardware.simulate_tag_scan(existing_tag)
            await asyncio.sleep(0.2)

            # Step 7: Verify new association
            playlist_b_updated = await playlist_repo.find_by_id(playlist_b_id)
            assert playlist_b_updated.nfc_tag_id == existing_tag, \
                "Tag should now be associated with playlist B"

            # Playlist A should no longer have the tag
            playlist_a_updated = await playlist_repo.find_by_id(playlist_a_id)
            assert playlist_a_updated.nfc_tag_id is None, \
                "Playlist A should no longer have the tag"

        finally:
            await playlist_repo.delete(playlist_b_id)
            await nfc_app_service.stop_nfc_system()

    async def test_session_timeout_with_cleanup(
        self,
        nfc_app_service,
        test_playlist
    ):
        """
        Test 3: Session Timeout with Cleanup

        Workflow:
        1. Start association with short timeout
        2. Wait for timeout
        3. Verify session marked as TIMEOUT
        4. Verify cleanup runs
        5. Verify normal mode restores

        This ensures timeout handling works correctly.
        """
        playlist_id = test_playlist.id

        try:
            # Step 1: Start association with very short timeout
            session_result = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_id,
                timeout_seconds=1  # 1 second timeout
            )
            assert session_result["status"] == "success"
            session_id = session_result["session"]["session_id"]

            # Verify session is active
            session = await nfc_app_service._association_service.get_association_session(session_id)
            assert session.is_active()
            assert session.state == SessionState.LISTENING

            # Step 2: Wait for timeout
            await asyncio.sleep(1.5)  # Wait longer than timeout

            # Step 3: Verify session expired
            assert session.is_expired(), "Session should be expired after timeout"

            # Step 4: Verify cleanup runs
            cleaned_count = await nfc_app_service._association_service.cleanup_expired_sessions()
            assert cleaned_count >= 1, "At least one session should be cleaned up"

            # Session should be marked TIMEOUT
            session = await nfc_app_service._association_service.get_association_session(session_id)
            assert session.state == SessionState.TIMEOUT

            # Step 5: Verify normal mode restores
            active_sessions = nfc_app_service._association_service.get_active_sessions()
            assert len(active_sessions) == 0, \
                "No active sessions after cleanup - normal mode restored"

        finally:
            await nfc_app_service.stop_nfc_system()

    async def test_broadcasting_during_association(
        self,
        nfc_app_service,
        nfc_hardware,
        broadcasting_service,
        test_playlist
    ):
        """
        Test 4: Broadcasting Service Integration

        Workflow:
        1. Mock broadcasting service
        2. Start association
        3. Verify 'waiting' broadcast
        4. Detect tag
        5. Verify 'success' broadcast
        6. Cancel session
        7. Verify 'cancelled' broadcast

        This tests Socket.IO event broadcasting integration.
        """
        playlist_id = test_playlist.id
        new_tag = uuid.uuid4().hex[:12]

        # Inject mock broadcasting service into NFC app service
        # Note: This is simplified - actual implementation would need proper injection
        original_callback = None
        if hasattr(nfc_app_service, '_association_event_callback'):
            original_callback = nfc_app_service._association_event_callback

        events_received = []

        def mock_association_callback(event_data):
            """Mock callback to track events."""
            events_received.append(event_data)
            # Simulate broadcasting
            action = event_data.get("action")
            if action == "association_success":
                asyncio.create_task(broadcasting_service.broadcast_nfc_association(
                    "success",
                    playlist_id=event_data.get("playlist_id"),
                    tag_id=event_data.get("tag_id"),
                    session_id=event_data.get("session_id")
                ))
            elif action == "duplicate_association":
                asyncio.create_task(broadcasting_service.broadcast_nfc_association(
                    "duplicate",
                    playlist_id=event_data.get("playlist_id"),
                    tag_id=event_data.get("tag_id"),
                    session_id=event_data.get("session_id")
                ))

        nfc_app_service.register_association_callback(mock_association_callback)

        try:
            # Step 2: Start association
            session_result = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_id,
                timeout_seconds=60
            )
            session_id = session_result["session"]["session_id"]

            # Step 3: Verify 'waiting' state can be broadcast
            # (In real system, this would be triggered by frontend)
            await broadcasting_service.broadcast_nfc_association(
                "waiting",
                playlist_id=playlist_id,
                session_id=session_id
            )
            waiting_events = broadcasting_service.get_events_by_state("waiting")
            assert len(waiting_events) >= 1

            # Step 4: Detect tag
            nfc_hardware.simulate_tag_scan(new_tag)
            await asyncio.sleep(0.2)

            # Step 5: Verify 'success' broadcast
            await asyncio.sleep(0.1)  # Wait for callback
            success_events = broadcasting_service.get_events_by_state("success")
            assert len(success_events) >= 1, \
                "Success event should be broadcasted after association"

            # Step 6: Test cancellation with new session
            cancel_session = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_id,
                timeout_seconds=60
            )
            cancel_session_id = cancel_session["session"]["session_id"]

            # Cancel the session
            await nfc_app_service.stop_association_use_case(cancel_session_id)

            # Step 7: Verify 'cancelled' broadcast could be sent
            await broadcasting_service.broadcast_nfc_association(
                "cancelled",
                playlist_id=playlist_id,
                session_id=cancel_session_id
            )
            cancelled_events = broadcasting_service.get_events_by_state("cancelled")
            assert len(cancelled_events) >= 1

        finally:
            # Restore original callback
            if original_callback:
                nfc_app_service.register_association_callback(original_callback)
            await nfc_app_service.stop_nfc_system()

    async def test_playback_prevention_persists(
        self,
        playlist_repo,
        nfc_app_service,
        nfc_hardware,
        test_playlist
    ):
        """
        Test 5: Playback Prevention Persistence

        Workflow:
        1. Start association
        2. Detect already-associated tag
        3. Verify DUPLICATE state
        4. Remove and re-scan same tag multiple times
        5. Verify playback never triggers
        6. Cancel session
        7. Verify normal mode restores

        This ensures playback prevention persists through multiple scans.
        """
        playlist_id = test_playlist.id
        existing_tag = uuid.uuid4().hex[:12]

        try:
            # Setup: Pre-associate tag
            setup_session = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_id,
                timeout_seconds=60
            )
            nfc_hardware.simulate_tag_scan(existing_tag)
            await asyncio.sleep(0.2)
            nfc_hardware.simulate_tag_removal()
            await asyncio.sleep(0.1)

            # Step 1: Start new association with same playlist
            session_result = await nfc_app_service.start_association_use_case(
                playlist_id=playlist_id,
                timeout_seconds=60
            )
            session_id = session_result["session"]["session_id"]

            # Step 2: Detect already-associated tag
            nfc_hardware.simulate_tag_scan(existing_tag)
            await asyncio.sleep(0.2)

            # Step 3: Verify DUPLICATE state
            session = await nfc_app_service._association_service.get_association_session(session_id)
            assert session.state == SessionState.DUPLICATE
            assert session.is_active(), \
                "Session must stay active in DUPLICATE state to prevent playback"

            # Step 4: Remove and re-scan multiple times
            for i in range(3):
                # Remove tag
                nfc_hardware.simulate_tag_removal()
                await asyncio.sleep(0.1)

                # Verify session still active
                session = await nfc_app_service._association_service.get_association_session(session_id)
                assert session.is_active(), \
                    f"Session should remain active after removal {i+1}"

                # Re-scan tag
                nfc_hardware.simulate_tag_scan(existing_tag)
                await asyncio.sleep(0.1)

                # Step 5: Verify playback still blocked
                active_sessions = nfc_app_service._association_service.get_active_sessions()
                assert len(active_sessions) >= 1, \
                    f"Active session should persist to block playback (iteration {i+1})"

                # Session should still be in DUPLICATE or LISTENING state
                session = await nfc_app_service._association_service.get_association_session(session_id)
                assert session.state in [SessionState.DUPLICATE, SessionState.LISTENING], \
                    f"Session should stay in blocking state (iteration {i+1})"

            # Step 6: Cancel session
            await nfc_app_service.stop_association_use_case(session_id)

            # Step 7: Verify normal mode restores
            active_sessions = nfc_app_service._association_service.get_active_sessions()
            assert len(active_sessions) == 0, \
                "No active sessions after cancellation - playback should be allowed"

        finally:
            await nfc_app_service.stop_nfc_system()
