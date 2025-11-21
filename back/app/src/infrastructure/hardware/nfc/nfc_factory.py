# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Hardware Factory for Domain-Driven Architecture."""

import asyncio
import os
import sys
from typing import Optional, Any
import logging

from .nfc_hardware_interface import NFCHardwareInterface
from .mock_nfc_hardware import MockNFCHardware
from app.src.services.error.unified_error_decorator import handle_errors

logger = logging.getLogger(__name__)

def _handle_errors(operation_name: str):
    return handle_errors(operation_name)


@_handle_errors("create_nfc_hardware")
async def create_nfc_hardware(
    bus_lock: Optional[asyncio.Lock] = None,
    config: Optional[Any] = None,
    force_mock: bool = False,
) -> NFCHardwareInterface:
    """Create appropriate NFC hardware implementation.

    This factory function automatically selects the correct NFC hardware
    implementation based on the environment and availability of hardware.

    Args:
        bus_lock: Asyncio lock for I2C bus synchronization (required for real hardware)
        config: NFC configuration parameters
        force_mock: Force use of mock implementation even on Raspberry Pi

    Returns:
        Initialized NFC hardware implementation

    Raises:
        RuntimeError: If hardware initialization fails
    """
    if config is None:
        from app.src.config.nfc_config import NFCConfig
        config = NFCConfig()

    # Determine if we should use mock hardware
    use_mock = (
        force_mock
        or os.environ.get("USE_MOCK_HARDWARE", "").lower() == "true"
        or sys.platform == "darwin"  # macOS development
        or sys.platform == "win32"  # Windows development
    )

    if use_mock:
        logger.info("🎭 Creating Mock NFC hardware for development/testing")
        hardware = MockNFCHardware()
        await hardware.initialize()
        return hardware

    # Try to create real PN532 hardware
    logger.info("🔧 Attempting to create PN532 NFC hardware...")
    if not bus_lock:
        logger.warning("⚠️ No bus_lock provided, creating default lock")
        bus_lock = asyncio.Lock()
    # Import PN532 hardware
    from .pn532_nfc_hardware import PN532NFCHardware

    hardware = PN532NFCHardware(bus_lock, config)
    await hardware.initialize()
    logger.info("✅ PN532 NFC hardware created successfully")
    return hardware
    # Fallback to mock if real hardware fails
    logger.info("🎭 Falling back to Mock NFC hardware")
    hardware = MockNFCHardware()
    await hardware.initialize()
    return hardware


@_handle_errors("get_hardware_info")
def get_hardware_info() -> dict:
    """Get information about available NFC hardware options.

    Returns:
        Dictionary containing hardware availability information
    """
    info = {
        "platform": sys.platform,
        "mock_available": True,
        "pn532_libraries_available": False,
        "pn532_hardware_available": False,
        "environment_force_mock": os.environ.get("USE_MOCK_HARDWARE", "").lower() == "true",
    }

    # Check if PN532 libraries are available
    import adafruit_pn532.i2c
    import board
    import busio

    info["pn532_libraries_available"] = True
    logger.debug("✅ PN532 libraries are available")
    # Check if we're on a platform that could have PN532 hardware
    if sys.platform.startswith("linux") and info["pn532_libraries_available"]:
        # Could potentially have hardware, but we'd need to actually try to connect
        # to know for sure
        info["pn532_hardware_available"] = "unknown"

    return info


class NFCHardwareSelector:
    """Helper class for NFC hardware selection logic."""

    @staticmethod
    def should_use_mock(force_mock: bool = False) -> bool:
        """Determine if mock hardware should be used.

        Args:
            force_mock: Force use of mock implementation

        Returns:
            True if mock should be used, False otherwise
        """
        if force_mock:
            return True

        # Check environment variable
        if os.environ.get("USE_MOCK_HARDWARE", "").lower() == "true":
            return True

        # Check platform - use mock on development platforms
        if sys.platform in ["darwin", "win32"]:
            return True

        # On Linux, default to trying real hardware first
        return False

    @staticmethod
    def get_recommended_hardware() -> str:
        """Get recommended hardware type for current environment.

        Returns:
            String indicating recommended hardware type
        """
        if NFCHardwareSelector.should_use_mock():
            return "mock"
        else:
            return "pn532"
