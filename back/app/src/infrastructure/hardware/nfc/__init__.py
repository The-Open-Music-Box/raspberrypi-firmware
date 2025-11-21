# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Hardware Infrastructure for Domain-Driven Architecture."""

from .nfc_hardware_interface import NFCHardwareInterface
from .mock_nfc_hardware import MockNFCHardware
from .nfc_factory import create_nfc_hardware, get_hardware_info, NFCHardwareSelector

# Conditional import for PN532 (only available on Raspberry Pi)
try:
    from .pn532_nfc_hardware import PN532NFCHardware

    __all__ = [
        "NFCHardwareInterface",
        "MockNFCHardware",
        "PN532NFCHardware",
        "create_nfc_hardware",
        "get_hardware_info",
        "NFCHardwareSelector",
    ]
except ImportError:
    # PN532 libraries not available (development environment)
    __all__ = [
        "NFCHardwareInterface",
        "MockNFCHardware",
        "create_nfc_hardware",
        "get_hardware_info",
        "NFCHardwareSelector",
    ]
