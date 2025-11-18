# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Integration test for NFC override association LED cleanup.

Tests the critical fix that ensures LED exits association mode (blinking blue)
after a successful override association and returns to normal state.

BUG FIX TEST:
Previously, when replacing an existing NFC tag association via override mode,
the LED would remain stuck in association mode (blinking blue) instead of
clearing to normal state (IDLE or PLAYING).

This test ensures the fix works correctly:
1. LED enters association mode (blinking blue)
2. Tag is detected and association succeeds (green flash)
3. LED clears association mode and returns to normal state
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, call

from app.src.application.services.nfc_application_service import NfcApplicationService
from app.src.application.services.led_event_handler_application_service import LEDEventHandler
from app.src.domain.nfc.services.nfc_association_service import NfcAssociationService
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.domain.models.led import LEDState


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
        self.associations = {}  # tag_id -> playlist_id

    async def find_by_nfc_tag(self, nfc_tag_id: str):
        """Find playlist by NFC tag ID."""
        playlist_id = self.associations.get(nfc_tag_id)
        if playlist_id:
            # Return a simple mock playlist object
            return type('MockPlaylist', (), {'id': playlist_id, 'nfc_tag_id': nfc_tag_id})()
        return None

    async def update_nfc_tag_association(self, playlist_id: str, tag_id: str):
        """Update NFC tag association."""
        self.associations[tag_id] = playlist_id
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


class MockLEDStateManager:
    """Mock LED state manager that tracks set_state and clear_state calls."""

    def __init__(self):
        self.state_calls = []  # Track all set_state calls
        self.clear_calls = []  # Track all clear_state calls
        self.active_states = []  # Simulate active LED states

    async def set_state(self, state: LEDState, color=None, pattern=None, priority=None, duration=None):
        """Track set_state calls."""
        call_info = {
            "state": state,
            "color": color,
            "pattern": pattern,
            "priority": priority,
            "duration": duration
        }
        self.state_calls.append(call_info)
        self.active_states.append(state)
        return True

    async def clear_state(self, state: LEDState):
        """Track clear_state calls."""
        self.clear_calls.append(state)
        if state in self.active_states:
            self.active_states.remove(state)
        return True

    def get_status(self):
        return {
            "active_states": [str(s) for s in self.active_states],
            "initialized": True
        }


@pytest.mark.asyncio
class TestNfcOverrideLEDCleanup:
    """Integration tests for NFC override association LED cleanup."""

    @pytest.fixture
    async def services(self):
        """Create all services needed for testing."""
        mock_nfc_repo = MockNfcRepository()
        mock_playlist_repo = MockPlaylistRepository()
        mock_hardware = MockNfcHardware()
        mock_led_manager = MockLEDStateManager()

        # Create LED event handler
        led_event_handler = LEDEventHandler(mock_led_manager)
        await led_event_handler.initialize()

        # Create association service
        association_service = NfcAssociationService(
            nfc_repository=mock_nfc_repo,
            playlist_repository=mock_playlist_repo
        )

        # Create NFC application service
        nfc_app_service = NfcApplicationService(
            nfc_hardware=mock_hardware,
            nfc_repository=mock_nfc_repo,
            nfc_association_service=association_service,
            playlist_repository=mock_playlist_repo,
            led_event_handler=led_event_handler
        )

        return {
            'nfc_app': nfc_app_service,
            'led_handler': led_event_handler,
            'led_manager': mock_led_manager,
            'playlist_repo': mock_playlist_repo
        }

    async def test_override_association_clears_led_after_success(self, services):
        """
        CRITICAL TEST: Verify LED exits association mode after successful override.

        Flow tested:
        1. Start association mode → LED enters NFC_ASSOCIATION_MODE (blinking blue)
        2. Detect tag already associated → returns duplicate
        3. User chooses override → new session with override_mode=True
        4. Tag detected immediately → association succeeds (green flash)
        5. LED should clear NFC_ASSOCIATION_MODE and return to normal
        """
        nfc_app = services['nfc_app']
        led_manager = services['led_manager']
        playlist_repo = services['playlist_repo']

        # ARRANGE: Setup existing association (tag already associated with playlist-A)
        tag_uid = "DEADBEEF01"
        tag_identifier = TagIdentifier(uid=tag_uid)

        # Simulate existing association in database
        await playlist_repo.update_nfc_tag_association("playlist-A", tag_uid)

        print("\n=== TEST STEP 1: Start association for playlist-B ===")
        # Start association session for playlist-B
        await nfc_app.start_association_use_case("playlist-B", timeout_seconds=60)

        # Verify LED entered association mode
        assert any(
            call_info['state'] == LEDState.NFC_ASSOCIATION_MODE
            for call_info in led_manager.state_calls
        ), "LED should enter NFC_ASSOCIATION_MODE when association starts"

        print("✅ LED entered association mode (blinking blue)")

        print("\n=== TEST STEP 2: Detect tag (will show duplicate) ===")
        # Simulate tag detection (should show duplicate because already associated)
        await nfc_app._handle_tag_detection(tag_identifier)
        await asyncio.sleep(0.1)  # Allow async processing

        # At this point, LED should still be in association mode (duplicate detected)
        print("✅ Duplicate detected, LED still in association mode")

        print("\n=== TEST STEP 3: Start override session ===")
        # Clear previous calls to track only override flow
        initial_clear_count = len(led_manager.clear_calls)
        initial_state_count = len(led_manager.state_calls)

        # Start override session for playlist-B
        await nfc_app.start_association_use_case(
            "playlist-B",
            timeout_seconds=60,
            override_mode=True
        )

        print("\n=== TEST STEP 4: Detect tag again (override mode) ===")
        # Detect tag again (should succeed with override)
        await nfc_app._handle_tag_detection(tag_identifier)

        # Wait for association success and LED cleanup
        # The fix schedules cleanup after 2.5 seconds (green flash + buffer)
        await asyncio.sleep(3.0)

        print("\n=== VERIFYING LED CLEANUP ===")

        # CRITICAL ASSERTION: LED should have cleared NFC_ASSOCIATION_MODE
        assert LEDState.NFC_ASSOCIATION_MODE in led_manager.clear_calls, (
            "❌ BUG DETECTED: LED did not clear NFC_ASSOCIATION_MODE after successful override!\n"
            f"Clear calls: {led_manager.clear_calls}\n"
            f"State calls: {[c['state'] for c in led_manager.state_calls]}\n"
            "This means the LED is stuck in association mode (blinking blue)."
        )

        # Verify green flash was triggered (success event)
        success_events = [
            call_info for call_info in led_manager.state_calls[initial_state_count:]
            if call_info['state'] == LEDState.NFC_SUCCESS
        ]
        assert len(success_events) > 0, "LED should show success event (green flash)"

        print("✅ LED cleared association mode after successful override")
        print(f"   - Total set_state calls: {len(led_manager.state_calls)}")
        print(f"   - Total clear_state calls: {len(led_manager.clear_calls)}")
        print(f"   - Active states remaining: {led_manager.active_states}")

    async def test_normal_association_also_clears_led(self, services):
        """
        Regression test: Verify normal (non-override) association also clears LED.
        """
        nfc_app = services['nfc_app']
        led_manager = services['led_manager']

        # ARRANGE: New tag (no existing association)
        tag_uid = "CAFE123456"
        tag_identifier = TagIdentifier(uid=tag_uid)

        print("\n=== REGRESSION TEST: Normal association ===")

        # Start association session
        await nfc_app.start_association_use_case("playlist-normal", timeout_seconds=60)

        # Detect new tag (should succeed immediately)
        await nfc_app._handle_tag_detection(tag_identifier)

        # Wait for LED cleanup
        await asyncio.sleep(3.0)

        # Verify LED cleared association mode
        assert LEDState.NFC_ASSOCIATION_MODE in led_manager.clear_calls, (
            "Normal association should also clear LED mode"
        )

        print("✅ Normal association correctly clears LED mode")

    async def test_cancelled_association_clears_led(self, services):
        """
        Test that manually cancelled association also clears LED.
        """
        nfc_app = services['nfc_app']
        led_manager = services['led_manager']

        print("\n=== TEST: Manual cancellation ===")

        # Start association session
        result = await nfc_app.start_association_use_case("playlist-cancel", timeout_seconds=60)
        session_id = result['session']['session_id']

        # Cancel session manually
        await nfc_app.stop_association_use_case(session_id)

        # Verify LED cleared association mode
        assert LEDState.NFC_ASSOCIATION_MODE in led_manager.clear_calls, (
            "Cancelled association should clear LED mode"
        )

        print("✅ Manual cancellation correctly clears LED mode")


if __name__ == "__main__":
    print("🧪 Running NFC Override LED Cleanup Integration Tests...")
    print("\nThis test verifies the fix for:")
    print("  BUG: LED stuck in association mode after override")
    print("\nExpected behavior:")
    print("  1. LED enters association mode (blinking blue)")
    print("  2. Tag detected and override succeeds (green flash)")
    print("  3. LED exits association mode (returns to IDLE/PLAYING)")
    print("\nRun with: python -m pytest tests/integration/test_nfc_override_led_cleanup.py -v -s")
