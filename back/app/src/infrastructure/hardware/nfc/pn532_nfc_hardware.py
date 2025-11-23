# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""PN532 NFC Hardware Implementation for Raspberry Pi."""

import asyncio
import logging
import time
from typing import Any

from .base_nfc_hardware import BaseNFCHardware, _handle_errors

logger = logging.getLogger(__name__)


class PN532NFCHardware(BaseNFCHardware):
    """PN532 NFC hardware implementation for Raspberry Pi.

    This implementation provides real NFC tag detection using the PN532 chip
    over I2C communication. It handles hardware initialization, scanning,
    and event emission for actual NFC tag detection.

    Inherits common NFC hardware functionality from BaseNFCHardware.
    """

    def __init__(self, bus_lock: asyncio.Lock, config: Any | None = None):
        """Initialize PN532 NFC hardware.

        Args:
            bus_lock: Asyncio lock for I2C bus synchronization
            config: NFC configuration parameters
        """
        super().__init__()

        # PN532-specific state
        self._bus_lock = bus_lock
        if config is None:
            from app.src.config.nfc_config import NFCConfig
            self._config = NFCConfig()
        else:
            self._config = config

        self._pn532 = None
        self._last_tag_uid: str | None = None
        self._tag_present = False
        self._consecutive_errors = 0

        # PN532 has longer stop timeout
        self._stop_timeout = 2.0

        logger.info("🔧 PN532 NFC Hardware initializing...")

    @_handle_errors("initialize")
    async def initialize(self) -> None:
        """Initialize the PN532 hardware."""
        # Import PN532 libraries (only available on Raspberry Pi)
        import board
        import busio
        from adafruit_pn532.i2c import PN532_I2C

        # Initialize I2C
        i2c = busio.I2C(board.SCL, board.SDA)
        # Initialize PN532 with I2C
        self._pn532 = PN532_I2C(i2c, debug=False, reset=None, irq=None)
        # Configure PN532
        ic, ver, rev, support = self._pn532.firmware_version
        logger.info(f"✅ PN532 found - Firmware version: {ver}.{rev}, IC: 0x{ic:02x}")
        # Configure the PN532 for NFC card detection
        self._pn532.SAM_configuration()
        logger.info("🚀 PN532 NFC Hardware initialized successfully")

    async def start_nfc_reader(self) -> None:
        """Start the PN532 NFC reader scanning process.

        Extends base class to ensure hardware initialization before starting.
        """
        if not self._pn532:
            await self.initialize()

        # Reset error counter when starting
        self._consecutive_errors = 0

        # Call base class implementation
        await super().start_nfc_reader()

    @_handle_errors("read_nfc")
    async def read_nfc(self) -> dict[str, Any] | None:
        """Read NFC tag data directly from PN532.

        Uses the base class _create_tag_data() helper for standardized tag structure.
        """
        if not self._pn532:
            return None

        async with self._bus_lock:
            # Try to read a MIFARE Classic card
            uid = self._pn532.read_passive_target(timeout=self._config.read_timeout)
            if uid:
                tag_uid = "".join([f"{b:02x}" for b in uid])
                return self._create_tag_data(
                    uid=tag_uid,
                    present=True,
                    hardware_name="PN532",
                    raw_uid=uid.hex(),
                )
        return None

    def cleanup(self) -> None:
        """Clean up PN532 hardware resources.

        Extends base class cleanup to also release hardware reference.
        """
        # Call base class cleanup (handles stop_nfc_reader)
        super().cleanup()

        # PN532-specific cleanup
        self._pn532 = None

    @_handle_errors("_scan_loop_impl")
    async def _scan_loop_impl(self) -> None:
        """Main scanning loop for PN532 tag detection."""
        logger.info("🔄 PN532 scanning loop started")
        last_status_log = 0
        scan_count = 0

        while not self._stop_event.is_set():
            scan_count += 1
            # Read tag with timeout
            tag_data = await self._read_tag_with_retry()
            if tag_data:
                await self._handle_tag_present(tag_data)
            else:
                await self._handle_tag_absent()
            # Reset error count on successful scan
            self._consecutive_errors = 0
            # Log status periodically (reduced verbosity)
            now = time.time()
            if now - last_status_log > 30:  # Increased from 10s to 30s
                status = "tag present" if self._tag_present else "waiting"
                logger.debug(
                    f"📡 PN532: {status} (scans: {scan_count}, errors: {self._consecutive_errors})",
                )
                last_status_log = now
            # Short delay between scans
            await asyncio.sleep(self._config.debounce_time)

    @_handle_errors("_read_tag_with_retry")
    async def _read_tag_with_retry(self) -> dict[str, Any] | None:
        """Read tag data with retry logic.

        Uses the base class _create_tag_data() helper for standardized tag structure.
        """
        for attempt in range(self._config.max_retries):
            async with self._bus_lock:
                # Try to read a MIFARE Classic card
                uid = self._pn532.read_passive_target(timeout=self._config.read_timeout)
                if uid:
                    tag_uid = "".join([f"{b:02x}" for b in uid])
                    return self._create_tag_data(
                        uid=tag_uid,
                        present=True,
                        hardware_name="PN532",
                        raw_uid=uid.hex(),
                        attempt=attempt + 1,
                    )
        return None

    @_handle_errors("_handle_tag_present")
    async def _handle_tag_present(self, tag_data: dict[str, Any]) -> None:
        """Handle when a tag is detected."""
        tag_uid = tag_data["uid"]

        # Check if this is a new tag or the same tag
        if not self._tag_present or self._last_tag_uid != tag_uid:
            # New tag detected
            self._tag_present = True
            self._last_tag_uid = tag_uid

            logger.info(f"🏷️ PN532 tag detected: {tag_uid}")

            # Emit tag detection event
            self._tag_subject.on_next(tag_data)
            logger.debug("📤 Tag detection event emitted successfully")

    @_handle_errors("_handle_tag_absent")
    async def _handle_tag_absent(self) -> None:
        """Handle when no tag is detected.

        Uses the base class _create_tag_data() helper for standardized tag structure.
        """
        if self._tag_present:
            # Tag was present but now absent
            self._tag_present = False
            old_tag_uid = self._last_tag_uid
            self._last_tag_uid = None

            logger.info(f"🚫 PN532 tag removed: {old_tag_uid}")

            # Emit tag absence event
            absence_data = self._create_tag_data(
                uid=old_tag_uid or "",
                present=False,
                hardware_name="PN532",
                absence=True,
            )
            self._tag_subject.on_next(absence_data)
            logger.debug("📤 Tag absence event emitted successfully")

    async def _attempt_recovery(self) -> None:
        """Attempt to recover from consecutive errors."""
        try:
            logger.info("🔄 Attempting PN532 recovery...")

            # Try to reinitialize the PN532
            await self.initialize()

            self._consecutive_errors = 0
            logger.info("✅ PN532 recovery successful")

        except Exception as e:
            logger.error(f"❌ PN532 recovery failed: {e}")
            # Continue with elevated error count - will retry later
