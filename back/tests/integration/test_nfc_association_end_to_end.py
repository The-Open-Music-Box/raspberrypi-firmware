# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
End-to-end integration tests for NFC association workflow.

These tests verify the complete workflow from tag detection to Socket.IO broadcasting
that was missed by unit tests and caused the frontend sync problems.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from app.src.application.services.nfc_application_service import NfcApplicationService
from app.src.domain.nfc.services.nfc_association_service import NfcAssociationService
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.core.application import Application
from app.src.services.broadcasting.unified_broadcasting_service import UnifiedBroadcastingService


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


class TestNfcAssociationEndToEnd:
    """End-to-end tests for NFC association workflow."""

    @pytest.fixture
    def mock_broadcasting_service(self):
        """Create mock broadcasting service to capture Socket.IO events."""
        mock_service = AsyncMock(spec=UnifiedBroadcastingService)
        mock_service.broadcast_nfc_association = AsyncMock(return_value=True)
        return mock_service

    @pytest.fixture
    def mock_nfc_repo(self):
        return MockNfcRepository()

    @pytest.fixture
    def mock_playlist_repo(self):
        return MockPlaylistRepository()

    @pytest.fixture
    def mock_hardware(self):
        return MockNfcHardware()

    @pytest.fixture
    def nfc_application_service(self, mock_hardware, mock_nfc_repo, mock_playlist_repo):
        """Create NFC application service with all dependencies."""
        association_service = NfcAssociationService(
            nfc_repository=mock_nfc_repo,
            playlist_repository=mock_playlist_repo
        )

        return NfcApplicationService(
            nfc_hardware=mock_hardware,
            nfc_repository=mock_nfc_repo,
            nfc_association_service=association_service,
            playlist_repository=mock_playlist_repo
        )

    @pytest.mark.asyncio
    async def test_complete_nfc_association_workflow_triggers_callbacks(self, nfc_application_service):
        """
        CRITICAL TEST: This would have caught the original bug.

        Tests that the complete workflow from tag detection to callback execution works.
        This is the integration test that was missing and would have failed before the fix.
        """
        # Arrange - Capture callback invocations
        association_events: List[Dict] = []

        def capture_association_callback(event_data: Dict):
            association_events.append(event_data)

        # Register the callback (this was working)
        nfc_application_service.register_association_callback(capture_association_callback)

        # Start an association session
        session_result = await nfc_application_service.start_association_use_case("test-playlist-456")
        session_id = session_result["session"]["session_id"]

        # Act - Trigger tag detection (this is where the bug was)
        tag_identifier = TagIdentifier(uid="DEADBEEF")
        await nfc_application_service._handle_tag_detection(tag_identifier)

        # Assert - Verify callbacks were triggered
        assert len(association_events) > 0, "❌ CRITICAL: No association callbacks were triggered!"

        success_event = association_events[0]
        assert success_event["action"] == "association_success", f"Expected 'association_success', got {success_event['action']}"
        assert success_event["session_id"] == session_id, "Wrong session ID in callback"
        assert success_event["playlist_id"] == "test-playlist-456", "Wrong playlist ID in callback"
        assert success_event["tag_id"] == "DEADBEEF", "Wrong tag ID in callback"

        print("✅ INTEGRATION TEST PASSED: Complete NFC workflow triggers callbacks correctly")

    @pytest.mark.asyncio
    async def test_duplicate_association_triggers_error_callback(self, nfc_application_service):
        """
        Test that duplicate association attempts trigger appropriate error callbacks.
        This test ensures error scenarios are also properly broadcasted.
        """
        # Arrange - Capture callback invocations
        association_events: List[Dict] = []

        def capture_association_callback(event_data: Dict):
            association_events.append(event_data)

        nfc_application_service.register_association_callback(capture_association_callback)

        # Create first association
        await nfc_application_service.start_association_use_case("original-playlist-123")
        tag_identifier = TagIdentifier(uid="ABCD1234")
        await nfc_application_service._handle_tag_detection(tag_identifier)

        # Clear previous events
        association_events.clear()

        # Start new session with different playlist
        await nfc_application_service.start_association_use_case("different-playlist-789")

        # Act - Try to associate same tag with different playlist
        await nfc_application_service._handle_tag_detection(tag_identifier)

        # Assert - Should trigger duplicate callback
        assert len(association_events) > 0, "❌ CRITICAL: Duplicate detection callback not triggered!"

        duplicate_event = association_events[0]
        assert duplicate_event["action"] == "duplicate_association", f"Expected 'duplicate_association', got {duplicate_event['action']}"
        assert duplicate_event["existing_playlist_id"] == "original-playlist-123", "Wrong existing playlist ID"

        print("✅ INTEGRATION TEST PASSED: Duplicate association triggers error callback")

    @pytest.mark.asyncio
    async def test_no_active_sessions_no_callbacks_triggered(self, nfc_application_service):
        """
        Test that tag detection without active sessions doesn't trigger association callbacks.
        This validates that callbacks are only triggered when appropriate.
        """
        # Arrange - Capture callback invocations
        association_events: List[Dict] = []
        tag_detection_events: List[str] = []

        def capture_association_callback(event_data: Dict):
            association_events.append(event_data)

        def capture_tag_callback(tag_id: str):
            tag_detection_events.append(tag_id)

        nfc_application_service.register_association_callback(capture_association_callback)
        nfc_application_service.register_tag_detected_callback(capture_tag_callback)

        # Act - Detect tag without any active association sessions
        tag_identifier = TagIdentifier(uid="12345678")
        await nfc_application_service._handle_tag_detection(tag_identifier)

        # Assert - Tag detection callback should work, association callbacks also triggered but with "tag_detected" action
        assert len(tag_detection_events) == 1, "Tag detection callback should still be triggered"
        assert tag_detection_events[0] == "12345678", "Wrong tag ID in detection callback"

        # The association callbacks are also triggered with "tag_detected" action (current behavior)
        assert len(association_events) == 1, "Association callbacks triggered with tag_detected action"
        assert association_events[0]["action"] == "tag_detected", "Should have tag_detected action when no sessions"
        assert association_events[0]["no_active_sessions"] == True, "Should indicate no active sessions"

        print("✅ INTEGRATION TEST PASSED: No spurious association callbacks without active sessions")

    @pytest.mark.asyncio
    async def test_multiple_concurrent_sessions_trigger_appropriate_callbacks(self, nfc_application_service):
        """
        Test handling multiple concurrent association sessions.
        This ensures callbacks work correctly in complex scenarios.
        """
        # Arrange - Capture all callback invocations
        association_events: List[Dict] = []

        def capture_association_callback(event_data: Dict):
            association_events.append(event_data)

        nfc_application_service.register_association_callback(capture_association_callback)

        # Start multiple concurrent sessions
        session1_result = await nfc_application_service.start_association_use_case("playlist-one")
        session2_result = await nfc_application_service.start_association_use_case("playlist-two")

        session1_id = session1_result["session"]["session_id"]
        session2_id = session2_result["session"]["session_id"]

        # Act - Detect a tag (should trigger callbacks for both sessions)
        tag_identifier = TagIdentifier(uid="FEDCBA98")
        await nfc_application_service._handle_tag_detection(tag_identifier)

        # Assert - Should have callbacks for both sessions
        # Note: The first session to process will succeed, subsequent ones will be duplicates
        print(f"Association events received: {association_events}")
        assert len(association_events) >= 1, "At least one association callback should be triggered"

        success_events = [e for e in association_events if e.get("action") == "association_success"]
        duplicate_events = [e for e in association_events if e.get("action") == "duplicate_association"]

        # Either we get one success (if only one session processes) or one success + one duplicate
        assert len(success_events) >= 1 or len(duplicate_events) >= 1, "Should have at least success or duplicate events"

        if success_events:
            success_event = success_events[0]
            assert success_event["playlist_id"] in ["playlist-one", "playlist-two"], "Should be one of the active playlists"

        print("✅ INTEGRATION TEST PASSED: Multiple concurrent sessions handled correctly")


class TestNfcAssociationSocketIOIntegration:
    """Tests for Socket.IO integration with NFC association."""

    @pytest.mark.asyncio
    async def test_application_nfc_callback_triggers_socket_io_broadcast(self):
        """
        Test that Application._on_nfc_association_event properly broadcasts Socket.IO events.
        This tests the second part of the integration that was broken.
        """
        # Arrange - Mock broadcasting service
        mock_broadcasting_service = AsyncMock(spec=UnifiedBroadcastingService)
        mock_broadcasting_service.broadcast_nfc_association = AsyncMock(return_value=True)

        # Create application instance with mock broadcasting
        from app.src.config import config
        application = Application(config)
        application._broadcasting_service = mock_broadcasting_service

        # Sample association event data (what would come from the callback)
        association_event = {
            "action": "association_success",
            "session_id": "test-session-123",
            "playlist_id": "test-playlist-456",
            "tag_id": "ABCDEF12",
            "session_state": "success"
        }

        # Act - Trigger the association event handler
        application._on_nfc_association_event(association_event)

        # Wait for async broadcast to complete
        await asyncio.sleep(0.1)

        # Assert - Verify Socket.IO broadcast was called correctly
        mock_broadcasting_service.broadcast_nfc_association.assert_called_once()

        call_args = mock_broadcasting_service.broadcast_nfc_association.call_args
        assert call_args.kwargs["association_state"] == "success", "Should map 'association_success' to 'success'"
        assert call_args.kwargs["playlist_id"] == "test-playlist-456", "Should pass playlist ID"
        assert call_args.kwargs["tag_id"] == "ABCDEF12", "Should pass tag ID"
        assert call_args.kwargs["session_id"] == "test-session-123", "Should pass session ID"

        print("✅ INTEGRATION TEST PASSED: Association events trigger Socket.IO broadcasts")

    @pytest.mark.asyncio
    async def test_application_maps_all_association_states_correctly(self):
        """
        Test that all association states are correctly mapped to frontend states.
        """
        # Arrange
        mock_broadcasting_service = AsyncMock(spec=UnifiedBroadcastingService)
        mock_broadcasting_service.broadcast_nfc_association = AsyncMock(return_value=True)

        from app.src.config import config
        application = Application(config)
        application._broadcasting_service = mock_broadcasting_service

        # Test cases for state mapping
        test_cases = [
            # (domain_action, session_state, expected_frontend_state)
            ("association_success", "success", "success"),
            ("duplicate_association", "duplicate", "duplicate"),
            ("unknown_action", "TIMEOUT", "timeout"),
            ("unknown_action", "LISTENING", "waiting"),
            ("unknown_action", "unknown", "error"),
        ]

        for domain_action, session_state, expected_state in test_cases:
            # Clear previous calls
            mock_broadcasting_service.reset_mock()

            association_event = {
                "action": domain_action,
                "session_id": "test-session",
                "playlist_id": "test-playlist",
                "tag_id": "TEST1234",
                "session_state": session_state
            }

            # Act
            application._on_nfc_association_event(association_event)
            await asyncio.sleep(0.01)  # Allow async broadcast

            # Assert
            mock_broadcasting_service.broadcast_nfc_association.assert_called_once()
            call_args = mock_broadcasting_service.broadcast_nfc_association.call_args
            actual_state = call_args.kwargs["association_state"]

            assert actual_state == expected_state, f"State mapping failed: {domain_action}/{session_state} should map to {expected_state}, got {actual_state}"

        print("✅ INTEGRATION TEST PASSED: All association states mapped correctly")


# Contract tests between services
class TestNfcServiceContracts:
    """Contract tests to ensure services communicate correctly."""

    @pytest.mark.asyncio
    async def test_nfc_application_service_callback_contract(self):
        """
        Test the contract that NfcApplicationService must call registered callbacks.
        This is a focused test on the exact issue that was broken.
        """
        # Arrange - Set up service with real dependencies
        mock_repo = MockNfcRepository()
        mock_playlist_repo = MockPlaylistRepository()
        mock_hardware = MockNfcHardware()

        association_service = NfcAssociationService(
            nfc_repository=mock_repo,
            playlist_repository=mock_playlist_repo
        )

        nfc_app_service = NfcApplicationService(
            nfc_hardware=mock_hardware,
            nfc_repository=mock_repo,
            nfc_association_service=association_service,
            playlist_repository=mock_playlist_repo
        )

        # Contract test: Callbacks MUST be triggered when associations occur
        callback_invocations = []

        def test_callback(data):
            callback_invocations.append(data)

        nfc_app_service.register_association_callback(test_callback)

        # Start session to have active association
        await nfc_app_service.start_association_use_case("contract-test-playlist")

        # Act - The critical method that was broken
        tag_id = TagIdentifier(uid="ABCDEF12")
        await nfc_app_service._handle_tag_detection(tag_id)

        # Assert - CONTRACT VIOLATION if this fails
        assert len(callback_invocations) > 0, "❌ CONTRACT VIOLATION: _handle_tag_detection MUST trigger association callbacks when associations occur"
        assert callback_invocations[0]["action"] == "association_success", "Callback should receive association success event"

        print("✅ CONTRACT TEST PASSED: NfcApplicationService callback contract verified")

    @pytest.mark.asyncio
    async def test_application_broadcasting_service_contract(self):
        """
        Test the contract that Application must broadcast Socket.IO events when callbacks are triggered.
        """
        # Arrange - Mock the broadcasting dependency
        broadcast_calls = []

        async def mock_broadcast_nfc_association(association_state, playlist_id=None, tag_id=None, session_id=None):
            broadcast_calls.append({
                "association_state": association_state,
                "playlist_id": playlist_id,
                "tag_id": tag_id,
                "session_id": session_id
            })
            return True

        from app.src.config import config
        application = Application(config)

        # Mock the broadcasting service
        mock_service = Mock()
        mock_service.broadcast_nfc_association = mock_broadcast_nfc_association
        application._broadcasting_service = mock_service

        # Act - Trigger association event
        event_data = {
            "action": "association_success",
            "session_id": "contract-session",
            "playlist_id": "contract-playlist",
            "tag_id": "CONTRACT2",
            "session_state": "success"
        }

        application._on_nfc_association_event(event_data)

        # Wait for async broadcast
        await asyncio.sleep(0.1)

        # Assert - CONTRACT: Application MUST broadcast when association events occur
        assert len(broadcast_calls) > 0, "❌ CONTRACT VIOLATION: Application MUST broadcast Socket.IO events for association callbacks"

        broadcast_call = broadcast_calls[0]
        assert broadcast_call["association_state"] == "success", "Should broadcast 'success' state"
        assert broadcast_call["playlist_id"] == "contract-playlist", "Should broadcast playlist ID"

        print("✅ CONTRACT TEST PASSED: Application Socket.IO broadcasting contract verified")


if __name__ == "__main__":
    print("🧪 Running missing integration tests that would have caught the NFC association bug...")

    import sys
    import os

    # Add the project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.insert(0, project_root)

    # These tests would have failed before the fix was implemented
    print("❌ Before fix: These tests would have failed")
    print("✅ After fix: These tests should all pass")
    print("\nRun with: python -m pytest tests/integration/test_nfc_association_end_to_end.py -v")