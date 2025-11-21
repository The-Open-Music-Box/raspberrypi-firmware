# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Hardware Adapter Implementation."""

import asyncio
from typing import Optional, Callable, Any, Dict

from app.src.domain.nfc.protocols.nfc_hardware_protocol import NfcHardwareProtocol
from app.src.domain.nfc.value_objects.tag_identifier import TagIdentifier
from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors

logger = get_logger(__name__)


class NfcHardwareAdapter(NfcHardwareProtocol):
    """Hardware adapter for NFC operations.

    Adapts the existing NFC hardware implementation to the domain protocol.
    Handles the translation between hardware events and domain concepts.
    """

    def __init__(self, legacy_nfc_handler: Optional[Any] = None):
        """Initialize NFC hardware adapter.

        Args:
            legacy_nfc_handler: Legacy NFC handler instance (optional)
        """
        self._legacy_handler = legacy_nfc_handler
        self._detecting = False
        self._tag_detected_callback: Optional[Callable[[TagIdentifier], None]] = None
        self._tag_removed_callback: Optional[Callable[[], None]] = None

        # Setup legacy handler integration if available
        if self._legacy_handler and hasattr(self._legacy_handler, "tag_subject"):
            self._legacy_handler.tag_subject.subscribe(self._on_legacy_tag_event)

    @handle_errors("start_detection")
    async def start_detection(self) -> None:
        """Start NFC tag detection."""
        if self._legacy_handler:
            # Start legacy handler if available
            if hasattr(self._legacy_handler, "start_reading"):
                await self._legacy_handler.start_reading()
            elif hasattr(self._legacy_handler, "start"):
                await self._legacy_handler.start()
        self._detecting = True
        logger.info("✅ NFC hardware detection started")

    @handle_errors("stop_detection")
    async def stop_detection(self) -> None:
        """Stop NFC tag detection."""
        if self._legacy_handler:
            # Stop legacy handler if available
            if hasattr(self._legacy_handler, "stop_reading"):
                await self._legacy_handler.stop_reading()
            elif hasattr(self._legacy_handler, "stop"):
                await self._legacy_handler.stop()
        self._detecting = False
        logger.info("✅ NFC hardware detection stopped")

    def is_detecting(self) -> bool:
        """Check if currently detecting tags."""
        return self._detecting

    def set_tag_detected_callback(self, callback: Callable[[TagIdentifier], None]) -> None:
        """Set callback for when a tag is detected."""
        self._tag_detected_callback = callback

    def set_tag_removed_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for when a tag is removed."""
        self._tag_removed_callback = callback

    @handle_errors("get_hardware_status")
    async def get_hardware_status(self) -> Dict[str, Any]:
        """Get current hardware status."""
        status = {
            "detecting": self._detecting,
            "adapter_type": "NfcHardwareAdapter",
            "legacy_handler_available": self._legacy_handler is not None,
        }

        # Add legacy handler status if available
        if self._legacy_handler:
            if hasattr(self._legacy_handler, "get_status"):
                legacy_status = self._legacy_handler.get_status()
                status.update({"legacy_status": legacy_status})
            elif hasattr(self._legacy_handler, "is_connected"):
                status.update({"legacy_connected": self._legacy_handler.is_connected()})
        return status

    @handle_errors("_on_legacy_tag_event")
    def _on_legacy_tag_event(self, tag_data: Dict[str, Any]) -> None:
        """Handle tag events from legacy NFC handler.

        Args:
            tag_data: Raw tag data from legacy handler
        """
        # Extract tag identifier from legacy data
        tag_uid = None
        # Try different formats for UID extraction
        if isinstance(tag_data, dict):
            tag_uid = (
                tag_data.get("uid")
                or tag_data.get("tag_id")
                or tag_data.get("id")
                or tag_data.get("data")
            )
        elif isinstance(tag_data, str):
            tag_uid = tag_data
        else:
            tag_uid = str(tag_data)
        if not tag_uid:
            logger.warning("⚠️ Received tag event without UID")
            return
        # Create domain tag identifier
        tag_identifier = TagIdentifier.from_raw_data(tag_uid)
        # Notify callback
        if self._tag_detected_callback:
            self._tag_detected_callback(tag_identifier)
        logger.debug(f"📱 Tag detected: {tag_identifier}")

    @handle_errors("inject_test_tag")
    def inject_test_tag(self, tag_uid: str) -> None:
        """Inject a test tag for development/testing.

        Args:
            tag_uid: UID of test tag to inject
        """
        tag_identifier = TagIdentifier(uid=tag_uid)
        if self._tag_detected_callback:
            self._tag_detected_callback(tag_identifier)
        logger.info(f"🧪 Injected test tag: {tag_identifier}")


class MockNfcHardwareAdapter(NfcHardwareProtocol):
    """Mock NFC hardware adapter for testing."""

    def __init__(self):
        """Initialize mock adapter."""
        self._detecting = False
        self._tag_detected_callback: Optional[Callable[[TagIdentifier], None]] = None
        self._tag_removed_callback: Optional[Callable[[], None]] = None

    async def start_detection(self) -> None:
        """Start mock detection."""
        self._detecting = True
        logger.info("✅ Mock NFC detection started")

    async def start(self) -> None:
        """Start mock NFC hardware (legacy compatibility method)."""
        await self.start_detection()
        logger.info("✅ Mock NFC hardware started (legacy compatibility)")

    async def stop_detection(self) -> None:
        """Stop mock detection."""
        self._detecting = False
        logger.info("✅ Mock NFC detection stopped")

    async def stop(self) -> None:
        """Stop mock NFC hardware (legacy compatibility method)."""
        await self.stop_detection()
        logger.info("✅ Mock NFC hardware stopped (legacy compatibility)")

    def is_detecting(self) -> bool:
        """Check if mock is detecting."""
        return self._detecting

    def set_tag_detected_callback(self, callback: Callable[[TagIdentifier], None]) -> None:
        """Set mock tag detected callback."""
        self._tag_detected_callback = callback

    def set_tag_removed_callback(self, callback: Callable[[], None]) -> None:
        """Set mock tag removed callback."""
        self._tag_removed_callback = callback

    async def get_hardware_status(self) -> Dict[str, Any]:
        """Get mock hardware status."""
        return {
            "detecting": self._detecting,
            "adapter_type": "MockNfcHardwareAdapter",
            "mock": True,
        }

    def simulate_tag_detection(self, tag_uid: str) -> None:
        """Simulate tag detection for testing.

        Args:
            tag_uid: UID of tag to simulate
        """
        if self._tag_detected_callback:
            tag_identifier = TagIdentifier(uid=tag_uid)
            self._tag_detected_callback(tag_identifier)
            logger.info(f"🧪 Simulated tag detection: {tag_identifier}")

    def simulate_tag_removal(self) -> None:
        """Simulate tag removal for testing."""
        if self._tag_removed_callback:
            self._tag_removed_callback()
            logger.info("🧪 Simulated tag removal")
