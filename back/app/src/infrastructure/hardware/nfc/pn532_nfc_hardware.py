# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""PN532 NFC Hardware Implementation for Raspberry Pi."""

import asyncio
import time
from typing import Optional, Dict, Any
from rx.subject import Subject
import logging

from .nfc_hardware_interface import NFCHardwareInterface
from app.src.services.error.unified_error_decorator import handle_errors

logger = logging.getLogger(__name__)

def _handle_errors(operation_name: str):
    return handle_errors(operation_name)


class PN532NFCHardware(NFCHardwareInterface):
    """PN532 NFC hardware implementation for Raspberry Pi.

    This implementation provides real NFC tag detection using the PN532 chip
    over I2C communication. It handles hardware initialization, scanning,
    and event emission for actual NFC tag detection.
    """

    def __init__(self, bus_lock: asyncio.Lock, config: Optional[Any] = None):
        """Initialize PN532 NFC hardware.

        Args:
            bus_lock: Asyncio lock for I2C bus synchronization
            config: NFC configuration parameters
        """
        self._bus_lock = bus_lock
        if config is None:
            from app.src.config.nfc_config import NFCConfig
            self._config = NFCConfig()
        else:
            self._config = config
        self._tag_subject = Subject()
        self._running = False
        self._reader_task = None
        self._stop_event = asyncio.Event()
        self._pn532 = None
        self._last_tag_uid = None
        self._tag_present = False
        self._consecutive_errors = 0

        logger.info("🔧 PN532 NFC Hardware initializing...")

    @property
    def tag_subject(self) -> Subject:
        """Get the RxPy Subject for tag detection events."""
        return self._tag_subject

    @_handle_errors("initialize")
    async def initialize(self) -> None:
        """Initialize the PN532 hardware."""
        # Import PN532 libraries (only available on Raspberry Pi)
        from adafruit_pn532.i2c import PN532_I2C
        import board
        import busio

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
        """Start the PN532 NFC reader scanning process."""
        if self._running:
            logger.warning("⚠️ PN532 NFC reader already running")
            return

        if not self._pn532:
            await self.initialize()

        self._stop_event.clear()
        self._running = True
        self._consecutive_errors = 0
        self._reader_task = asyncio.create_task(self._scan_loop())

        logger.info("🚀 PN532 NFC Reader started - scanning for tags...")

    async def stop_nfc_reader(self) -> None:
        """Stop the PN532 NFC reader scanning process."""
        if not self._running:
            return

        self._stop_event.set()
        self._running = False

        if self._reader_task and not self._reader_task.done():
            try:
                await asyncio.wait_for(self._reader_task, timeout=2.0)
            except asyncio.TimeoutError:
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass

        logger.info("⏹️ PN532 NFC Reader stopped")

    def is_running(self) -> bool:
        """Check if the PN532 reader is running."""
        return self._running

    @_handle_errors("read_nfc")
    async def read_nfc(self) -> Optional[Dict[str, Any]]:
        """Read NFC tag data directly from PN532."""
        if not self._pn532:
            return None

        async with self._bus_lock:
            # Try to read a MIFARE Classic card
            uid = self._pn532.read_passive_target(timeout=self._config.read_timeout)
            if uid:
                tag_uid = "".join([f"{b:02x}" for b in uid])
                return {
                    "uid": tag_uid,
                    "present": True,
                    "timestamp": time.time(),
                    "hardware": "PN532",
                    "raw_uid": uid.hex(),
                }
        return None

    def cleanup(self) -> None:
        """Clean up PN532 hardware resources."""
        if self._running:
            asyncio.create_task(self.stop_nfc_reader())

        self._pn532 = None
        logger.info("🧹 PN532 NFC Hardware cleaned up")

    @_handle_errors("_scan_loop")
    async def _scan_loop(self) -> None:
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
    async def _read_tag_with_retry(self) -> Optional[Dict[str, Any]]:
        """Read tag data with retry logic."""
        for attempt in range(self._config.max_retries):
            async with self._bus_lock:
                # Try to read a MIFARE Classic card
                uid = self._pn532.read_passive_target(timeout=self._config.read_timeout)
                if uid:
                    tag_uid = "".join([f"{b:02x}" for b in uid])
                    return {
                        "uid": tag_uid,
                        "present": True,
                        "timestamp": time.time(),
                        "hardware": "PN532",
                        "raw_uid": uid.hex(),
                        "attempt": attempt + 1,
                    }
        return None

    @_handle_errors("_handle_tag_present")
    async def _handle_tag_present(self, tag_data: Dict[str, Any]) -> None:
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
        """Handle when no tag is detected."""
        if self._tag_present:
            # Tag was present but now absent
            self._tag_present = False
            old_tag_uid = self._last_tag_uid
            self._last_tag_uid = None

            logger.info(f"🚫 PN532 tag removed: {old_tag_uid}")

            # Emit tag absence event
            absence_data = {
                "uid": old_tag_uid,
                "present": False,
                "absence": True,
                "timestamp": time.time(),
                "hardware": "PN532",
            }
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
