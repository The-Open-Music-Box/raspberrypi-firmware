# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Integration tests for NEW NFC association features.

Tests the following NEW features implemented in Priority 1 & 2:
1. Playback prevention during association mode
2. Override/replace association functionality
3. 'Waiting' state broadcast on session start
4. Session cancellation endpoint
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import List, Dict

from app.src.application.services.nfc_application_service import NfcApplicationService
from app.src.domain.nfc.services.nfc_association_service import NfcAssociationService
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.domain.nfc.entities.association_session import SessionState


class MockNfcRepository:
    """Mock NFC repository for testing."""

    def __init__(self):
        self.tags = {}

    async def find_by_identifier(self, tag_identifier: TagIdentifier):
        return self.tags.get(str(tag_identifier))

    async def save_tag(self, tag):
        self.tags[str(tag.identifier)] = tag
        return True


class MockPlaylistRepository:
    """Mock playlist repository for testing."""

    def __init__(self):
        self.playlists = {}

    async def find_by_nfc_tag(self, nfc_tag_id: str):
        """Find playlist by NFC tag ID."""
        for playlist in self.playlists.values():
            if hasattr(playlist, 'nfc_tag_id') and playlist.nfc_tag_id == nfc_tag_id:
                return playlist
        return None

    async def update_nfc_tag_association(self, playlist_id: str, tag_id: str):
        return True


class MockNfcHardware:
    """Mock NFC hardware for testing."""

    def __init__(self):
        self._callbacks = {}

    def set_tag_detected_callback(self, callback):
        self._callbacks['tag_detected'] = callback

    def set_tag_removed_callback(self, callback):
        self._callbacks['tag_removed'] = callback

    async def start_detection(self):
        pass

    async def stop_detection(self):
        pass

    def get_hardware_status(self):
        return {"status": "available", "mock": True}

    def is_detecting(self):
        return True


class TestPlaybackPreventionDuringAssociation:
    """Tests for PRIORITY 1: Playback prevention during association mode."""

    @pytest.fixture
    def nfc_service(self):
        mock_repo = MockNfcRepository()
        mock_playlist_repo = MockPlaylistRepository()
        mock_hardware = MockNfcHardware()

        association_service = NfcAssociationService(
            nfc_repository=mock_repo,
            playlist_repository=mock_playlist_repo
        )

        return NfcApplicationService(
            nfc_hardware=mock_hardware,
            nfc_repository=mock_repo,
            nfc_association_service=association_service,
            playlist_repository=mock_playlist_repo
        )

    @pytest.mark.asyncio
    async def test_tag_detection_blocks_playback_when_association_active(self, nfc_service):
        """
        CRITICAL TEST: Verify that tag detection does NOT trigger playback
        callbacks when an association session is active.
        """
        # Track callback invocations
        tag_detection_callbacks_called = []
        association_callbacks_called = []

        def tag_detected_callback(tag_id: str):
            tag_detection_callbacks_called.append(tag_id)

        def association_callback(event_data: Dict):
            association_callbacks_called.append(event_data)

        nfc_service.register_tag_detected_callback(tag_detected_callback)
        nfc_service.register_association_callback(association_callback)

        # Start association session (activates association mode)
        await nfc_service.start_association_use_case("test-playlist-123")

        # Detect a tag (use hexadecimal UID)
        tag_identifier = TagIdentifier(uid="DEADBEEF01")
        await nfc_service._handle_tag_detection(tag_identifier)

        # CRITICAL ASSERTION: Tag detection callbacks should NOT be called
        assert len(tag_detection_callbacks_called) == 0, (
            f"❌ PLAYBACK PREVENTION FAILED: Tag detection callback was called "
            f"{len(tag_detection_callbacks_called)} times during association mode! "
            f"This means playback could be triggered during association."
        )

        # Association callbacks SHOULD be called
        assert len(association_callbacks_called) == 1, (
            "Association callbacks should be called once"
        )

        print("✅ PLAYBACK PREVENTION TEST PASSED: Tag detection blocked during association mode")

    @pytest.mark.asyncio
    async def test_tag_detection_triggers_playback_when_no_association_active(self, nfc_service):
        """
        Verify that tag detection DOES trigger playback callbacks
        when NO association session is active (normal mode).
        """
        # Track callback invocations
        tag_detection_callbacks_called = []

        def tag_detected_callback(tag_id: str):
            tag_detection_callbacks_called.append(tag_id)

        nfc_service.register_tag_detected_callback(tag_detected_callback)

        # Do NOT start any association session (normal playback mode)

        # Detect a tag (use hexadecimal UID)
        tag_identifier = TagIdentifier(uid="ABCD1234EF")
        await nfc_service._handle_tag_detection(tag_identifier)

        # ASSERTION: Tag detection callbacks SHOULD be called
        assert len(tag_detection_callbacks_called) == 1, (
            "Tag detection callback should be called once in normal mode"
        )
        assert tag_detection_callbacks_called[0] == "ABCD1234EF", (
            "Wrong tag ID in callback"
        )

        print("✅ NORMAL MODE TEST PASSED: Tag detection triggers playback in normal mode")


class TestOverrideReplaceAssociation:
    """Tests for PRIORITY 1: Override/replace association functionality."""

    @pytest.fixture
    def association_service(self):
        mock_repo = MockNfcRepository()
        mock_playlist_repo = MockPlaylistRepository()

        return NfcAssociationService(
            nfc_repository=mock_repo,
            playlist_repository=mock_playlist_repo
        )

    @pytest.mark.asyncio
    async def test_override_mode_replaces_existing_association(self, association_service):
        """
        Test that override_mode=True forces association even if tag
        is already associated with another playlist.
        """
        # Create initial association
        session1 = await association_service.start_association_session("playlist-A")
        tag = TagIdentifier(uid="CAFE123456")

        # Associate tag with playlist-A
        from app.src.domain.nfc.entities.nfc_tag import NfcTag
        nfc_tag = NfcTag(identifier=tag)
        nfc_tag.associate_with_playlist("playlist-A")
        await association_service._nfc_repository.save_tag(nfc_tag)

        # Start new session with override_mode=True for playlist-B
        session2 = await association_service.start_association_session(
            "playlist-B",
            override_mode=True
        )

        assert session2.override_mode == True, "Session should have override_mode=True"

        # Process tag detection for session2 (should force replace)
        result = await association_service._process_tag_for_session(nfc_tag, session2)

        # CRITICAL ASSERTION: Should succeed, not return duplicate error
        assert result["action"] == "association_success", (
            f"Override mode should force association, got action: {result.get('action')}"
        )
        assert result["playlist_id"] == "playlist-B", (
            "Tag should now be associated with playlist-B"
        )

        # Verify tag is now associated with playlist-B
        assert nfc_tag.get_associated_playlist_id() == "playlist-B", (
            "Tag should be associated with playlist-B after override"
        )

        print("✅ OVERRIDE MODE TEST PASSED: Override replaces existing association")

    @pytest.mark.asyncio
    async def test_normal_mode_returns_duplicate_error(self, association_service):
        """
        Test that normal mode (override_mode=False) returns duplicate
        error for already associated tags.
        """
        # Create initial association
        tag = TagIdentifier(uid="FEED987654")

        from app.src.domain.nfc.entities.nfc_tag import NfcTag
        nfc_tag = NfcTag(identifier=tag)
        nfc_tag.associate_with_playlist("playlist-original")
        await association_service._nfc_repository.save_tag(nfc_tag)

        # Start new session WITHOUT override mode
        session = await association_service.start_association_session("playlist-new")
        assert session.override_mode == False, "Session should have override_mode=False by default"

        # Process tag detection (should return duplicate error)
        result = await association_service._process_tag_for_session(nfc_tag, session)

        # ASSERTION: Should return duplicate error
        assert result["action"] == "duplicate_association", (
            f"Normal mode should return duplicate error, got: {result.get('action')}"
        )
        assert result["existing_playlist_id"] == "playlist-original", (
            "Should indicate which playlist tag is currently associated with"
        )

        print("✅ NORMAL MODE TEST PASSED: Duplicate detection works correctly")


class TestSessionCancellation:
    """Tests for PRIORITY 2: Session cancellation endpoint."""

    @pytest.fixture
    def association_service(self):
        mock_repo = MockNfcRepository()
        mock_playlist_repo = MockPlaylistRepository()

        return NfcAssociationService(
            nfc_repository=mock_repo,
            playlist_repository=mock_playlist_repo
        )

    @pytest.mark.asyncio
    async def test_cancel_association_session_marks_cancelled(self, association_service):
        """
        Test that cancelling a session marks it with CANCELLED state.
        """
        # Start session
        session = await association_service.start_association_session("test-cancel-playlist")
        session_id = session.session_id

        assert session.state == SessionState.LISTENING, "Session should start in LISTENING state"

        # Cancel session
        success = await association_service.stop_association_session(session_id)

        assert success == True, "Cancellation should succeed"

        # Verify session state is CANCELLED
        cancelled_session = await association_service.get_association_session(session_id)
        assert cancelled_session.state == SessionState.CANCELLED, (
            f"Session should be in CANCELLED state, got: {cancelled_session.state}"
        )

        print("✅ CANCELLATION TEST PASSED: Session marked as CANCELLED")

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_session_returns_false(self, association_service):
        """
        Test that attempting to cancel non-existent session returns False.
        """
        success = await association_service.stop_association_session("nonexistent-session-id")

        assert success == False, "Cancelling non-existent session should return False"

        print("✅ CANCELLATION ERROR HANDLING PASSED: Non-existent session handled correctly")


if __name__ == "__main__":
    print("🧪 Running NEW NFC association features integration tests...")
    print("Tests verify Priority 1 & 2 implementations:")
    print("  1. Playback prevention during association mode")
    print("  2. Override/replace association functionality")
    print("  3. Session cancellation endpoint")
    print("\nRun with: python -m pytest tests/integration/test_nfc_association_new_features_e2e.py -v")
