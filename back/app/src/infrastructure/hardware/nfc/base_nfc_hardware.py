# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Base NFC Hardware Implementation.

This module provides a base class for NFC hardware implementations that extracts
common functionality shared between mock and real hardware implementations.
Follows Context7 principles with proper type safety and DDD architecture.
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any
from abc import abstractmethod
from rx.subject import Subject

from .nfc_hardware_interface import NFCHardwareInterface
from app.src.services.error.unified_error_decorator import handle_errors

logger = logging.getLogger(__name__)


def _handle_errors(operation_name: str):
    """Convenience wrapper for error handling decorator.

    Extracted to eliminate duplication across NFC implementations.

    Args:
        operation_name: Name of the operation being wrapped

    Returns:
        Decorator function
    """
    return handle_errors(operation_name)


class BaseNFCHardware(NFCHardwareInterface):
    """Base class for NFC hardware implementations.

    This class provides common functionality for NFC hardware, including:
    - Reader lifecycle management (start/stop)
    - Event handling through RxPy Subject
    - Task cancellation and cleanup
    - Common state tracking

    Subclasses must implement:
    - initialize(): Hardware-specific initialization
    - read_nfc(): Hardware-specific tag reading
    - _scan_loop_impl(): Hardware-specific scanning logic
    """

    def __init__(self):
        """Initialize base NFC hardware state.

        Sets up common state variables used by all NFC hardware implementations.
        Extracted from MockNFCHardware and PN532NFCHardware to eliminate duplication.
        """
        # RxPy Subject for tag detection events
        self._tag_subject = Subject()

        # Reader state
        self._running = False
        self._reader_task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

        logger.debug(f"{self.__class__.__name__}: Base NFC hardware state initialized")

    @property
    def tag_subject(self) -> Subject:
        """Get the RxPy Subject for tag detection events.

        This property is identical in all implementations, extracted to base class.

        Returns:
            Subject that emits tag data when tags are detected/removed
        """
        return self._tag_subject

    def is_running(self) -> bool:
        """Check if the NFC reader is currently running.

        This method is identical in all implementations, extracted to base class.

        Returns:
            True if the reader is actively scanning, False otherwise
        """
        return self._running

    async def start_nfc_reader(self) -> None:
        """Start the NFC reader scanning process.

        Common start logic extracted from both implementations.
        Creates and runs the scanning task.
        """
        if self._running:
            logger.warning(f"⚠️ {self.__class__.__name__} NFC reader already running")
            return

        self._stop_event.clear()
        self._running = True
        self._reader_task = asyncio.create_task(self._scan_loop_impl())

        logger.info(f"🚀 {self.__class__.__name__} NFC Reader started - scanning for tags...")

    async def stop_nfc_reader(self) -> None:
        """Stop the NFC reader scanning process.

        Common stop logic extracted from both MockNFCHardware and PN532NFCHardware.
        This method was duplicated as 9 identical lines (lines 63-80 in mock, 95-113 in pn532).
        Handles proper task cancellation with timeout and graceful shutdown.
        """
        if not self._running:
            return

        self._stop_event.set()
        self._running = False

        if self._reader_task and not self._reader_task.done():
            try:
                # Wait for task to complete with timeout
                # Timeout is 1.0s for mock, 2.0s for PN532 - use configurable value
                timeout = getattr(self, '_stop_timeout', 2.0)
                await asyncio.wait_for(self._reader_task, timeout=timeout)
            except asyncio.TimeoutError:
                # Force cancellation if timeout exceeded
                self._reader_task.cancel()
                try:
                    await self._reader_task
                except asyncio.CancelledError:
                    pass

        logger.info(f"⏹️ {self.__class__.__name__} NFC Reader stopped")

    def cleanup(self) -> None:
        """Clean up NFC hardware resources.

        Common cleanup logic extracted from both implementations.
        Schedules async stop if reader is running.
        """
        if self._running:
            # Schedule stop for async cleanup
            asyncio.create_task(self.stop_nfc_reader())

        logger.info(f"🧹 {self.__class__.__name__} NFC Hardware cleaned up")

    def _create_tag_data(
        self,
        uid: str,
        present: bool = True,
        hardware_name: Optional[str] = None,
        **extra_fields: Any
    ) -> Dict[str, Any]:
        """Create standardized tag data dictionary.

        Extracted helper to eliminate duplication of tag data structure
        between mock and real implementations.

        Args:
            uid: Tag unique identifier (hex string)
            present: Whether tag is present (True) or absent (False)
            hardware_name: Name of hardware implementation (defaults to class name)
            **extra_fields: Additional fields to include in tag data

        Returns:
            Dictionary with standardized tag data structure
        """
        tag_data = {
            "uid": uid,
            "present": present,
            "timestamp": time.time(),
            "hardware": hardware_name or self.__class__.__name__,
        }

        # Add any extra fields provided
        tag_data.update(extra_fields)

        return tag_data

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the NFC hardware.

        Must be implemented by subclasses to handle hardware-specific initialization.
        - Mock: no-op
        - PN532: initialize I2C and configure chip
        """
        pass

    @abstractmethod
    async def read_nfc(self) -> Optional[Dict[str, Any]]:
        """Read NFC tag data directly.

        Must be implemented by subclasses to handle hardware-specific tag reading.
        - Mock: simulate tag data
        - PN532: read from I2C bus

        Returns:
            Dictionary containing tag data if present, None otherwise
        """
        pass

    @abstractmethod
    async def _scan_loop_impl(self) -> None:
        """Implementation-specific scanning loop.

        Must be implemented by subclasses to define the main scanning logic.
        This method runs in a background task and should:
        - Check self._stop_event.is_set() to know when to stop
        - Emit events through self._tag_subject.on_next()
        - Handle implementation-specific tag detection

        Examples:
        - Mock: Timer-based simulation with periodic tag events
        - PN532: Hardware polling loop with I2C communication
        """
        pass
