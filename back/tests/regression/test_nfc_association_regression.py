# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Regression tests for NFC association broadcasting bug.

These tests specifically target the bug that was fixed where NFC association
events weren't being broadcasted to the frontend via Socket.IO.

🐛 Original Bug:
- NFC association dialog appeared when starting association
- Tag scanning worked in backend (domain logic correct)
- But dialog never received confirmation events
- Dialog remained stuck in "waiting" state

🔧 Root Cause:
- NfcApplicationService._handle_tag_detection() didn't trigger association callbacks
- Application._on_nfc_association_event() didn't broadcast Socket.IO events

These tests ensure this specific bug never happens again.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from app.src.application.services.nfc_application_service import NfcApplicationService
from app.src.domain.nfc.services.nfc_association_service import NfcAssociationService
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.core.application import Application


class TestNfcAssociationRegressionPrevention:
    """
    Regression tests to prevent the NFC association broadcasting bug from recurring.

    These tests specifically target the integration points that were broken.

    🐛 Original Bug:
    - NFC association dialog appeared when starting association
    - Tag scanning worked in backend (domain logic correct)
    - But dialog never received confirmation events
    - Dialog remained stuck in "waiting" state

    🔧 Root Cause:
    - NfcApplicationService._handle_tag_detection() didn't trigger association callbacks
    - Application._on_nfc_association_event() didn't broadcast Socket.IO events
    """

    @pytest.fixture
    def minimal_nfc_setup(self):
        """Minimal NFC setup for regression testing."""
        from tests.integration.test_nfc_association_end_to_end import (
            MockNfcRepository, MockPlaylistRepository, MockNfcHardware
        )

        mock_nfc_repo = MockNfcRepository()
        mock_playlist_repo = MockPlaylistRepository()
        mock_hardware = MockNfcHardware()

        association_service = NfcAssociationService(
            nfc_repository=mock_nfc_repo,
            playlist_repository=mock_playlist_repo
        )

        nfc_app_service = NfcApplicationService(
            nfc_hardware=mock_hardware,
            nfc_repository=mock_nfc_repo,
            nfc_association_service=association_service,
            playlist_repository=mock_playlist_repo
        )

        return {
            "nfc_service": nfc_app_service,
            "association_service": association_service,
            "repositories": {
                "nfc": mock_nfc_repo,
                "playlist": mock_playlist_repo
            },
            "hardware": mock_hardware
        }

    @pytest.mark.asyncio
    async def test_regression_nfc_callbacks_triggered_on_association(self, minimal_nfc_setup):
        """
        🐛 REGRESSION TEST: Ensure NFC association callbacks are always triggered.

        This test specifically targets the bug where _handle_tag_detection()
        wasn't calling association callbacks.

        ❌ Before Fix: This test would have FAILED
        ✅ After Fix: This test should PASS
        """
        nfc_service = minimal_nfc_setup["nfc_service"]

        # The critical test: Register callback and verify it gets called
        callback_invoked = False
        callback_data = None

        def regression_callback(data):
            nonlocal callback_invoked, callback_data
            callback_invoked = True
            callback_data = data

        nfc_service.register_association_callback(regression_callback)

        # Start association session
        await nfc_service.start_association_use_case("regression-playlist")

        # The critical action that was broken: tag detection
        tag = TagIdentifier(uid="ABCD1234")
        await nfc_service._handle_tag_detection(tag)

        # ❌ THIS ASSERTION WOULD HAVE FAILED BEFORE THE FIX
        assert callback_invoked, "🐛 REGRESSION: NFC association callback not triggered! Original bug has returned!"
        assert callback_data is not None, "🐛 REGRESSION: Callback triggered but no data received!"
        assert callback_data["action"] == "association_success", "🐛 REGRESSION: Wrong callback data format!"

        print("✅ REGRESSION TEST PASSED: NFC callbacks are triggered correctly")

    @pytest.mark.asyncio
    async def test_regression_socket_io_broadcast_on_association_event(self):
        """
        🐛 REGRESSION TEST: Ensure Socket.IO broadcasts are triggered on association events.

        This test targets the second part of the bug where Application._on_nfc_association_event()
        wasn't broadcasting Socket.IO events.

        ❌ Before Fix: This test would have FAILED
        ✅ After Fix: This test should PASS
        """
        # Setup application with mock broadcasting
        from app.src.config import config
        application = Application(config)

        broadcast_called = False
        broadcast_params = None

        async def regression_broadcast(association_state, playlist_id=None, tag_id=None, session_id=None):
            nonlocal broadcast_called, broadcast_params
            broadcast_called = True
            broadcast_params = {
                "association_state": association_state,
                "playlist_id": playlist_id,
                "tag_id": tag_id,
                "session_id": session_id
            }
            return True

        # Mock the broadcasting service
        mock_service = Mock()
        mock_service.broadcast_nfc_association = regression_broadcast
        application._broadcasting_service = mock_service

        # Simulate association event (what comes from the callback)
        association_event = {
            "action": "association_success",
            "session_id": "regression-session",
            "playlist_id": "regression-playlist",
            "tag_id": "ABCD5678",
            "session_state": "success"
        }

        # The critical action that was broken: event handler
        application._on_nfc_association_event(association_event)

        # Wait for async broadcast
        await asyncio.sleep(0.1)

        # ❌ THESE ASSERTIONS WOULD HAVE FAILED BEFORE THE FIX
        assert broadcast_called, "🐛 REGRESSION: Socket.IO broadcast not called! Original bug has returned!"
        assert broadcast_params is not None, "🐛 REGRESSION: Broadcast called but no parameters!"
        assert broadcast_params["association_state"] == "success", "🐛 REGRESSION: Wrong state mapping!"
        assert broadcast_params["playlist_id"] == "regression-playlist", "🐛 REGRESSION: Wrong playlist ID!"

        print("✅ REGRESSION TEST PASSED: Socket.IO broadcasts are triggered correctly")

    @pytest.mark.asyncio
    async def test_regression_end_to_end_workflow_integration(self, minimal_nfc_setup):
        """
        🐛 REGRESSION TEST: Complete end-to-end workflow integration.

        This test ensures the entire chain works together:
        1. Tag detection → Domain service → Application service → Callbacks → Socket.IO

        This is the most critical regression test as it covers the complete workflow
        that was broken.
        """
        nfc_service = minimal_nfc_setup["nfc_service"]

        # Setup complete workflow tracking
        callback_events = []
        socketio_events = []

        # 1. Track application service callbacks
        def track_callback(data):
            callback_events.append(data)

        nfc_service.register_association_callback(track_callback)

        # 2. Setup Application with Socket.IO tracking
        from app.src.config import config
        application = Application(config)

        async def track_socketio(association_state, playlist_id=None, tag_id=None, session_id=None):
            socketio_events.append({
                "state": association_state,
                "playlist_id": playlist_id,
                "tag_id": tag_id,
                "session_id": session_id
            })
            return True

        mock_service = Mock()
        mock_service.broadcast_nfc_association = track_socketio
        application._broadcasting_service = mock_service

        # 3. Execute complete workflow
        session_result = await nfc_service.start_association_use_case("e2e-regression-playlist")
        session_id = session_result["session"]["session_id"]

        # Critical: Tag detection (the original breaking point)
        tag = TagIdentifier(uid="E2EF1234")
        await nfc_service._handle_tag_detection(tag)

        # Simulate the callback reaching the Application layer
        if callback_events:
            application._on_nfc_association_event(callback_events[0])
            await asyncio.sleep(0.1)

        # ❌ ALL THESE ASSERTIONS WOULD HAVE FAILED BEFORE THE FIX

        # Verify callback chain
        assert len(callback_events) > 0, "🐛 REGRESSION: Callback chain broken! (Step 1/3 failed)"

        callback_event = callback_events[0]
        assert callback_event["action"] == "association_success", "🐛 REGRESSION: Wrong callback action!"
        assert callback_event["session_id"] == session_id, "🐛 REGRESSION: Wrong session ID in callback!"

        # Verify Socket.IO chain
        assert len(socketio_events) > 0, "🐛 REGRESSION: Socket.IO chain broken! (Step 2/3 failed)"

        socketio_event = socketio_events[0]
        assert socketio_event["state"] == "success", "🐛 REGRESSION: Wrong Socket.IO state!"
        assert socketio_event["playlist_id"] == "e2e-regression-playlist", "🐛 REGRESSION: Wrong playlist in Socket.IO!"

        print("✅ REGRESSION TEST PASSED: Complete end-to-end workflow integration working")

    @pytest.mark.asyncio
    async def test_regression_duplicate_association_broadcasts_error(self, minimal_nfc_setup):
        """
        🐛 REGRESSION TEST: Ensure duplicate associations broadcast error states correctly.

        This ensures error scenarios also work in the complete workflow.
        """
        nfc_service = minimal_nfc_setup["nfc_service"]

        # Track all callback events
        all_events = []

        def track_all_events(data):
            all_events.append(data)

        nfc_service.register_association_callback(track_all_events)

        # Setup Socket.IO tracking
        from app.src.config import config
        application = Application(config)

        socketio_broadcasts = []

        async def track_broadcasts(association_state, **kwargs):
            socketio_broadcasts.append({"state": association_state, **kwargs})
            return True

        mock_service = Mock()
        mock_service.broadcast_nfc_association = track_broadcasts
        application._broadcasting_service = mock_service

        # Create first association
        await nfc_service.start_association_use_case("first-playlist")
        tag = TagIdentifier(uid="AAAA1111")
        await nfc_service._handle_tag_detection(tag)

        # Clear events from first association
        all_events.clear()

        # Create second association with same tag (should trigger duplicate)
        await nfc_service.start_association_use_case("second-playlist")
        await nfc_service._handle_tag_detection(tag)  # Same tag!

        # Process the duplicate event through Socket.IO
        if all_events:
            application._on_nfc_association_event(all_events[0])
            await asyncio.sleep(0.1)

        # Verify duplicate handling works end-to-end
        assert len(all_events) > 0, "🐛 REGRESSION: Duplicate detection callback not triggered!"

        duplicate_event = all_events[0]
        assert duplicate_event["action"] == "duplicate_association", "🐛 REGRESSION: Should detect duplicate!"

        assert len(socketio_broadcasts) > 0, "🐛 REGRESSION: Duplicate error not broadcasted!"

        error_broadcast = socketio_broadcasts[0]
        assert error_broadcast["state"] == "duplicate", "🐛 REGRESSION: Should broadcast duplicate state for duplicate association!"

        print("✅ REGRESSION TEST PASSED: Duplicate association error workflow working")

    @pytest.mark.asyncio
    async def test_regression_callback_registration_contract(self, minimal_nfc_setup):
        """
        🐛 REGRESSION TEST: Ensure callback registration contract is maintained.

        This tests that the service properly maintains registered callbacks.
        """
        nfc_service = minimal_nfc_setup["nfc_service"]

        # Test multiple callback registrations
        callback1_called = False
        callback2_called = False

        def callback1(data):
            nonlocal callback1_called
            callback1_called = True

        def callback2(data):
            nonlocal callback2_called
            callback2_called = True

        # Register multiple callbacks
        nfc_service.register_association_callback(callback1)
        nfc_service.register_association_callback(callback2)

        # Start association and trigger
        await nfc_service.start_association_use_case("callback-contract-test")
        tag = TagIdentifier(uid="CCCC2222")
        await nfc_service._handle_tag_detection(tag)

        # ❌ THESE WOULD HAVE FAILED BEFORE THE FIX
        assert callback1_called, "🐛 REGRESSION: First callback not called!"
        assert callback2_called, "🐛 REGRESSION: Second callback not called!"

        print("✅ REGRESSION TEST PASSED: Callback registration contract maintained")

    def test_regression_state_mapping_consistency(self):
        """
        🐛 REGRESSION TEST: Ensure state mapping between domain and frontend is consistent.

        This tests the _map_action_to_state method in Application.
        """
        from app.src.config import config
        application = Application(config)

        # Test all expected state mappings
        test_cases = [
            ("association_success", "success", "success"),
            ("duplicate_association", "duplicate", "duplicate"),
            ("timeout_action", "TIMEOUT", "timeout"),
            ("unknown_action", "LISTENING", "waiting"),
            ("unknown_action", "CANCELLED", "cancelled"),
            ("unknown_action", "unknown_state", "error"),
        ]

        for domain_action, session_state, expected_frontend_state in test_cases:
            result = application._map_action_to_state(domain_action, session_state)
            assert result == expected_frontend_state, f"🐛 REGRESSION: State mapping broken! {domain_action}/{session_state} should map to {expected_frontend_state}, got {result}"

        print("✅ REGRESSION TEST PASSED: State mapping consistency maintained")


class TestNfcRegressionTestSuite:
    """Meta-test to ensure regression test suite is comprehensive."""

    def test_regression_suite_covers_critical_paths(self):
        """
        Test that our regression suite covers all critical paths that were broken.
        """
        # Verify all critical test methods exist in the regression suite
        regression_class = TestNfcAssociationRegressionPrevention

        critical_tests = [
            "test_regression_nfc_callbacks_triggered_on_association",
            "test_regression_socket_io_broadcast_on_association_event",
            "test_regression_end_to_end_workflow_integration",
            "test_regression_duplicate_association_broadcasts_error",
            "test_regression_callback_registration_contract",
            "test_regression_state_mapping_consistency"
        ]

        for test_name in critical_tests:
            assert hasattr(regression_class, test_name), f"🐛 CRITICAL: Regression suite missing test: {test_name}"

        print("✅ REGRESSION SUITE: All critical paths covered")

    def test_regression_suite_documentation(self):
        """
        Verify that regression tests are properly documented with bug context.
        """
        import inspect

        regression_class = TestNfcAssociationRegressionPrevention
        class_doc = inspect.getdoc(regression_class)

        # Verify documentation mentions the original bug
        assert "Original Bug" in class_doc, "Regression suite should document original bug"
        assert "Root Cause" in class_doc, "Regression suite should document root cause"
        assert "Socket.IO" in class_doc, "Regression suite should mention Socket.IO issue"

        print("✅ REGRESSION SUITE: Properly documented with bug context")


if __name__ == "__main__":
    print("🐛 Running NFC association regression tests...")
    print("These tests ensure the original bug never comes back.")
    print("\n❌ Before fix: These tests would have FAILED")
    print("✅ After fix: These tests should all PASS")
    print("\nIf any of these tests fail in the future, the original bug has returned!")
    print("\nRun with: python -m pytest tests/regression/test_nfc_association_regression.py -v")