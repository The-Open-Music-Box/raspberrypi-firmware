# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC adapter for domain-driven architecture."""

import asyncio
from typing import Optional, Callable, Protocol

from app.src.monitoring import get_logger
from app.src.domain.decorators.error_handler import handle_domain_errors as handle_errors


class NFCHardwareInterface(Protocol):
    """Protocol defining the interface for NFC hardware implementations."""

    def is_running(self) -> bool:
        """Check if NFC hardware is running."""
        ...

    async def start_nfc_reader(self) -> None:
        """Start the NFC reader."""
        ...

    async def stop_nfc_reader(self) -> None:
        """Stop the NFC reader."""
        ...

    async def read_nfc(self):
        """Read NFC tag asynchronously."""
        ...

    def cleanup(self) -> None:
        """Cleanup NFC hardware resources."""
        ...

logger = get_logger(__name__)


class NFCHandlerAdapter:
    """Adapter for NFC handling in domain architecture.

    This adapter wraps the new NFC hardware infrastructure and provides
    compatibility with the existing NFC service interface.
    """

    def __init__(self, hardware: NFCHardwareInterface):
        """Initialize NFC adapter with hardware implementation.

        Args:
            hardware: NFC hardware implementation (mock or real)
        """
        self._hardware = hardware
        self._is_mock = hardware.__class__.__name__ == "MockNFCHardware"
        self._tag_callbacks = []
        self._tag_removed_callbacks = []

        # Subscribe to hardware tag events if available
        if hasattr(hardware, "tag_subject"):
            hardware.tag_subject.subscribe(self._on_hardware_tag_event)
            logger.debug("🔗 NFCHandlerAdapter subscribed to hardware tag events")

        hardware_type = "Mock" if self._is_mock else "Real"
        logger.info(f"✅ NFCHandlerAdapter initialized with {hardware_type} hardware")

    @property
    def tag_subject(self):
        """Get the RxPy Subject for tag detection events."""
        return self._hardware.tag_subject

    def is_running(self) -> bool:
        """Check if NFC handler is running."""
        return self._hardware.is_running()

    async def start_nfc_reader(self) -> None:
        """Start the NFC reader scanning process."""
        await self._hardware.start_nfc_reader()

    async def stop_nfc_reader(self) -> None:
        """Stop the NFC reader scanning process."""
        await self._hardware.stop_nfc_reader()

    def read_tag(self):
        """Direct tag reading method (synchronous compatibility)."""
        # This is a compatibility method for legacy code
        # The preferred way is to use the tag_subject for event-driven detection
        logger.debug("Direct read_tag called (compatibility mode)")
        return None  # Return None as events should come through tag_subject

    async def read_nfc(self):
        """Asynchronous NFC tag reading."""
        return await self._hardware.read_nfc()

    def set_tag_detected_callback(self, callback: Callable[[str], None]) -> None:
        """Set callback for when a tag is detected.

        Args:
            callback: Function to call when tag is detected, receives tag UID as string
        """
        self._tag_callbacks.append(callback)
        logger.debug(f"✅ Tag detected callback registered (total: {len(self._tag_callbacks)})",
        )

    def set_tag_removed_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for when a tag is removed.

        Args:
            callback: Function to call when tag is removed
        """
        self._tag_removed_callbacks.append(callback)
        logger.debug(f"✅ Tag removed callback registered (total: {len(self._tag_removed_callbacks)})",
        )

    async def start_detection(self) -> None:
        """Start NFC tag detection - compatibility method for NfcApplicationService."""
        await self.start_nfc_reader()
        logger.debug("✅ NFC detection started via compatibility method")

    async def stop_detection(self) -> None:
        """Stop NFC tag detection - compatibility method for NfcApplicationService."""
        await self.stop_nfc_reader()
        logger.debug("✅ NFC detection stopped via compatibility method")

    def is_detecting(self) -> bool:
        """Check if currently detecting tags.

        Returns:
            True if NFC detection is active
        """
        return self.is_running()

    def get_hardware_status(self) -> dict:
        """Get hardware status information for NFC system.

        Returns:
            Dictionary with hardware status information
        """
        return {
            "is_available": True,
            "is_running": self.is_running(),
            "hardware_type": "Mock" if self._is_mock else "PN532",
            "status": "operational" if self.is_running() else "stopped",
        }

    @handle_errors("_on_hardware_tag_event")
    def _on_hardware_tag_event(self, tag_data):
        """Handle tag events from hardware.

        Args:
            tag_data: Tag event data from hardware (can be dict or other format)
        """
        logger.debug(f"🔄 NFCHandlerAdapter processing tag event: {tag_data}")
        # Extract tag UID from various possible formats
        tag_uid = None
        if isinstance(tag_data, dict):
            # Dictionary format: {"uid": "...", "action": "detected/removed"}
            tag_uid = tag_data.get("uid")
            action = tag_data.get("action", "detected")
            if tag_uid and action == "detected":
                # Call all registered tag detected callbacks
                for callback in self._tag_callbacks:
                    callback(tag_uid)

    def cleanup(self):
        """Cleanup NFC resources."""
        logger.info("🧹 NFCHandlerAdapter cleaning up...")
        self._hardware.cleanup()


# Factory function moved to Infrastructure layer to respect DDD boundaries
