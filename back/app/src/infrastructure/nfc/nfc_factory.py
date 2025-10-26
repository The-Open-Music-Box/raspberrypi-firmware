# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Factory for creating configured NFC services.

Follows dependency injection principles for NFC infrastructure components.
"""

import asyncio
from typing import Optional, Any
import logging

from app.src.domain.nfc import NfcAssociationService, NfcHardwareProtocol, NfcRepositoryProtocol
from app.src.infrastructure.adapters.nfc.nfc_adapter import NFCHandlerAdapter
from app.src.infrastructure.hardware.nfc import create_nfc_hardware
from app.src.config.nfc_config import NFCConfig
from app.src.infrastructure.nfc.adapters.nfc_hardware_adapter import (
    NfcHardwareAdapter,
    MockNfcHardwareAdapter,
)
from app.src.infrastructure.nfc.repositories.nfc_memory_repository import NfcMemoryRepository

logger = logging.getLogger(__name__)


class NfcFactory:
    """Factory for creating NFC services with proper dependency injection."""

    @staticmethod
    def create_nfc_infrastructure_components(
        legacy_nfc_handler: Optional[Any] = None,
        use_mock_hardware: bool = False,
        repository: Optional[NfcRepositoryProtocol] = None,
    ) -> tuple[NfcHardwareProtocol, NfcRepositoryProtocol, NfcAssociationService]:
        """Create infrastructure components for NFC services.

        Args:
            legacy_nfc_handler: Legacy NFC handler for backward compatibility
            use_mock_hardware: Use mock hardware for testing
            repository: Custom repository implementation

        Returns:
            Tuple of (hardware, repository, domain_service) for use by Application layer
        """
        # Create repository
        nfc_repository = repository or NfcMemoryRepository()

        # Create hardware adapter
        if use_mock_hardware:
            nfc_hardware = MockNfcHardwareAdapter()
        else:
            nfc_hardware = NfcHardwareAdapter(legacy_nfc_handler)

        # Create domain service
        nfc_association_service = NfcAssociationService(nfc_repository)

        return nfc_hardware, nfc_repository, nfc_association_service

    @staticmethod
    def create_mock_nfc_components() -> tuple[NfcHardwareProtocol, NfcRepositoryProtocol, NfcAssociationService]:
        """Create NFC infrastructure components with mock hardware for testing.

        Returns:
            NFC infrastructure components with mock implementations
        """
        return NfcFactory.create_nfc_infrastructure_components(use_mock_hardware=True)

    @staticmethod
    async def create_nfc_handler_adapter(nfc_lock: Optional[asyncio.Lock] = None) -> NFCHandlerAdapter:
        """Factory function to get NFC handler with new infrastructure.

        Args:
            nfc_lock: Optional asyncio lock for I2C bus synchronization

        Returns:
            NFCHandlerAdapter wrapping the appropriate hardware implementation
        """
        logger.info("🏭 Creating NFC handler with new infrastructure...")

        # Create NFC configuration
        config = NFCConfig()

        # Create hardware implementation using factory
        hardware = await create_nfc_hardware(
            bus_lock=nfc_lock,
            config=config,
            force_mock=False,  # Let factory decide based on environment
        )

        # Wrap hardware in adapter
        adapter = NFCHandlerAdapter(hardware)

        hardware_info = "Mock" if adapter._is_mock else "Real PN532"
        logger.info(f"✅ NFC handler created with {hardware_info} hardware")

        return adapter
