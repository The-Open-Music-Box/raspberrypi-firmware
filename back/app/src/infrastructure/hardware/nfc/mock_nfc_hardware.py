# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Mock NFC Hardware Implementation for Testing and Development."""

import asyncio
import logging
import time
from typing import Any

from .base_nfc_hardware import BaseNFCHardware, _handle_errors

logger = logging.getLogger(__name__)


class MockNFCHardware(BaseNFCHardware):
    """Mock implementation of NFC hardware for testing and development.

    This implementation simulates NFC tag detection using a timer-based approach
    and provides all the event mechanisms that the real hardware would provide.

    Inherits common NFC hardware functionality from BaseNFCHardware.
    """

    def __init__(self):
        """Initialize the Mock NFC hardware."""
        super().__init__()

        # Mock-specific state
        self._scan_counter = 0
        self._last_simulated_tag: dict[str, Any] | None = None
        self._simulation_cycle = 0

        # Mock has shorter stop timeout
        self._stop_timeout = 1.0

        logger.info("✅ Mock NFC Hardware initialized")

    async def initialize(self) -> None:
        """Initialize the mock hardware (no-op for mock)."""
        logger.info("🔧 Mock NFC Hardware initialized (no-op)")

    async def read_nfc(self) -> dict[str, Any] | None:
        """Simulate reading an NFC tag directly.

        This method simulates finding a tag occasionally for direct reads.
        """
        # Simulate finding a tag 20% of the time for direct reads
        if self._scan_counter % 5 == 0:
            tag_data = self._generate_mock_tag()
            logger.debug(f"📱 Direct NFC read: {tag_data}")
            return tag_data
        return None

    @_handle_errors("_scan_loop_impl")
    async def _scan_loop_impl(self) -> None:
        """Main simulation loop for NFC tag detection."""
        logger.info("🔄 Mock NFC scanning loop started")
        last_info_log = 0

        while not self._stop_event.is_set():
            self._scan_counter += 1
            self._simulation_cycle = (self._simulation_cycle + 1) % 100
            # Simulate tag detection every ~8-12 seconds with some randomness
            should_simulate_tag = self._simulation_cycle % 80 == 0 or (  # Every 8 seconds
                self._simulation_cycle % 120 == 0 and self._scan_counter % 3 == 0
            )  # Random extra detection
            if should_simulate_tag:
                await self._simulate_tag_detection()
            # Log status every 5 seconds to show activity
            now = time.time()
            if now - last_info_log > 5:
                logger.info(
                    f"📡 Mock NFC: Waiting for tag... (cycle {self._simulation_cycle}, scans: {self._scan_counter})",
                )
                last_info_log = now  # type: ignore[assignment]
            # 100ms scan interval
            await asyncio.sleep(0.1)

    @_handle_errors("_simulate_tag_detection")
    async def _simulate_tag_detection(self) -> None:
        """Simulate detecting an NFC tag and emit the event."""
        tag_data = self._generate_mock_tag()
        self._last_simulated_tag = tag_data

        logger.info(f"🏷️ Mock tag detected: {tag_data['uid']}")

        # Emit the tag detection event through the subject
        self._tag_subject.on_next(tag_data)
        logger.debug("📤 Tag detection event emitted successfully")

    def _generate_mock_tag(self) -> dict[str, Any]:
        """Generate mock NFC tag data.

        Uses the base class _create_tag_data() helper for standardized tag structure.
        """
        # Cycle through different mock tag IDs (hexadecimal UIDs)
        mock_tags = [
            "abcd1234",
            "efab5678",
            "cafe9abc",
            "deadbeef",
            "fade1234",
        ]

        tag_index = (self._scan_counter // 50) % len(mock_tags)
        tag_uid = mock_tags[tag_index]

        return self._create_tag_data(
            uid=tag_uid,
            present=True,
            hardware_name="MockNFC",
            scan_count=self._scan_counter,
            mock_data=True,
        )

    # Additional method for manual tag simulation (for testing)
    def simulate_tag_manually(self, tag_uid: str = "manual_test_tag") -> None:
        """Manually trigger a tag detection event (for testing).

        Uses the base class _create_tag_data() helper for standardized tag structure.
        """
        if not self._running:
            logger.warning("⚠️ Cannot simulate tag - Mock NFC reader not running")
            return

        tag_data = self._create_tag_data(
            uid=tag_uid,
            present=True,
            hardware_name="MockNFC",
            scan_count=self._scan_counter,
            mock_data=True,
            manual=True,
        )

        logger.info(f"🎯 Manually triggering tag detection: {tag_uid}")
        self._tag_subject.on_next(tag_data)
