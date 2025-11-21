# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Unit tests for NFC active tag state management.

Tests the critical fix that prevents multiple playlist triggers from the same tag.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock
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

    def simulate_tag_detection(self, tag_uid: str):
        """Simulate a tag being detected."""
        if self._tag_detected_callback:
            tag_identifier = TagIdentifier(uid=tag_uid)
            self._tag_detected_callback(tag_identifier)

    def simulate_tag_removal(self):
        """Simulate tag removal."""
        if self._tag_removed_callback:
            self._tag_removed_callback()


@pytest.mark.asyncio
class TestNfcActiveTagStateManagement:
    """Unit tests for NFC active tag state management."""

    @pytest.fixture
    async def nfc_hardware(self):
        """Get mock NFC hardware."""
        return MockNfcHardware()

    @pytest.fixture
    async def nfc_app_service(self, nfc_hardware):
        """Get NFC application service."""
        nfc_repository = NfcMemoryRepository()
        service = NfcApplicationService(
            nfc_hardware=nfc_hardware,
            nfc_repository=nfc_repository,
            playlist_repository=None  # Not needed for state management tests
        )
        await service.start_nfc_system()
        return service

    async def test_initial_state_is_empty(self, nfc_app_service):
        """Test that initial state has no active tag."""
        assert nfc_app_service._current_active_tag is None
        assert nfc_app_service._tag_triggered_playback is False
        assert nfc_app_service._last_trigger_time is None

    async def test_first_tag_detection_sets_state(self, nfc_app_service, nfc_hardware):
        """Test that first tag detection sets active tag state."""
        # Arrange
        tag_uid = "abc123def456"  # Hexadecimal UID
        playback_triggered = False

        def playback_callback(tag_id: str):
            nonlocal playback_triggered
            playback_triggered = True

        nfc_app_service.register_tag_detected_callback(playback_callback)

        # Act
        nfc_hardware.simulate_tag_detection(tag_uid)
        await asyncio.sleep(0.1)  # Wait for async processing

        # Assert
        assert nfc_app_service._current_active_tag == tag_uid
        assert nfc_app_service._tag_triggered_playback is True
        assert nfc_app_service._last_trigger_time is not None
        assert playback_triggered is True

    async def test_duplicate_tag_detection_ignored(self, nfc_app_service, nfc_hardware):
        """Test that duplicate detections of same tag are ignored."""
        # Arrange
        tag_uid = "abc123def456"  # Hexadecimal UID
        playback_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)

        # Act - Detect same tag multiple times
        nfc_hardware.simulate_tag_detection(tag_uid)
        await asyncio.sleep(0.1)

        nfc_hardware.simulate_tag_detection(tag_uid)
        await asyncio.sleep(0.1)

        nfc_hardware.simulate_tag_detection(tag_uid)
        await asyncio.sleep(0.1)

        # Assert - Playback should only trigger once
        assert playback_count == 1
        assert nfc_app_service._current_active_tag == tag_uid

    async def test_tag_removal_resets_state(self, nfc_app_service, nfc_hardware):
        """Test that tag removal resets the active tag state."""
        # Arrange
        tag_uid = "abc123def456"  # Hexadecimal UID
        playback_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)

        # Act - Detect tag
        nfc_hardware.simulate_tag_detection(tag_uid)
        await asyncio.sleep(0.1)

        # Remove tag
        nfc_hardware.simulate_tag_removal()
        await asyncio.sleep(0.1)

        # Assert - State should be reset
        assert nfc_app_service._current_active_tag is None
        assert nfc_app_service._tag_triggered_playback is False
        assert nfc_app_service._last_trigger_time is None

    async def test_tag_redetection_after_removal(self, nfc_app_service, nfc_hardware):
        """Test that same tag can trigger playback again after removal."""
        # Arrange
        tag_uid = "abc123def456"  # Hexadecimal UID
        playback_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)

        # Act - Detect → Remove → Detect again
        nfc_hardware.simulate_tag_detection(tag_uid)
        await asyncio.sleep(0.1)

        nfc_hardware.simulate_tag_removal()
        await asyncio.sleep(0.1)

        nfc_hardware.simulate_tag_detection(tag_uid)
        await asyncio.sleep(0.1)

        # Assert - Playback should trigger twice (once per insertion)
        assert playback_count == 2

    async def test_different_tag_triggers_playback(self, nfc_app_service, nfc_hardware):
        """Test that a different tag triggers playback even without removal."""
        # Arrange
        tag_uid_1 = "aaa111bbb222"  # Hexadecimal UID
        tag_uid_2 = "ccc333ddd444"  # Hexadecimal UID
        playback_count = 0
        detected_tags = []

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1
            detected_tags.append(tag_id)

        nfc_app_service.register_tag_detected_callback(playback_callback)

        # Act - Detect different tags
        nfc_hardware.simulate_tag_detection(tag_uid_1)
        await asyncio.sleep(0.1)

        nfc_hardware.simulate_tag_detection(tag_uid_2)
        await asyncio.sleep(0.1)

        # Assert - Both tags should trigger playback
        assert playback_count == 2
        assert detected_tags[0] == tag_uid_1
        assert detected_tags[1] == tag_uid_2

    async def test_removal_without_active_tag_is_safe(self, nfc_app_service, nfc_hardware):
        """Test that tag removal without active tag doesn't cause errors."""
        # Act - Remove tag when none was detected
        nfc_hardware.simulate_tag_removal()
        await asyncio.sleep(0.1)

        # Assert - No errors, state remains empty
        assert nfc_app_service._current_active_tag is None
        assert nfc_app_service._tag_triggered_playback is False

    async def test_association_mode_bypasses_state_check(self, nfc_app_service, nfc_hardware):
        """Test that association mode works regardless of active tag state."""
        # Arrange
        tag_uid = "abc123def456"  # Hexadecimal UID
        playback_count = 0
        association_count = 0

        def playback_callback(tag_id: str):
            nonlocal playback_count
            playback_count += 1

        def association_callback(result: dict):
            nonlocal association_count
            association_count += 1

        nfc_app_service.register_tag_detected_callback(playback_callback)
        nfc_app_service.register_association_callback(association_callback)

        # Start association session
        session_result = await nfc_app_service.start_association_use_case(
            playlist_id="test_playlist",
            timeout_seconds=60
        )
        assert session_result["status"] == "success"

        # Act - Detect tag in association mode
        nfc_hardware.simulate_tag_detection(tag_uid)
        await asyncio.sleep(0.2)

        # Assert - Association should work, playback should NOT trigger
        assert association_count > 0
        assert playback_count == 0

    async def test_cleanup(self, nfc_app_service):
        """Test cleanup of NFC service."""
        await nfc_app_service.stop_nfc_system()
        # No assertions needed, just ensure cleanup doesn't error
