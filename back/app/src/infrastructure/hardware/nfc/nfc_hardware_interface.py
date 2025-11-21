# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Hardware Interface for Domain-Driven Architecture."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from rx.subject import Subject


class NFCHardwareInterface(ABC):
    """Abstract interface for NFC hardware implementations.

    This interface defines the contract that all NFC hardware implementations
    must follow, whether they are mock implementations for testing or real
    hardware implementations for production.
    """

    @property
    @abstractmethod
    def tag_subject(self) -> Subject:
        """RxPy Subject that emits NFC tag detection events.

        Returns:
            Subject that emits tag data when tags are detected
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the NFC hardware asynchronously.

        This method should prepare the hardware for operation.
        For mock implementations, this may be a no-op.
        For real hardware, this may include device initialization.
        """
        pass

    @abstractmethod
    async def start_nfc_reader(self) -> None:
        """Start the NFC reader scanning process.

        This method should begin actively scanning for NFC tags
        and emit events through the tag_subject when tags are detected.
        """
        pass

    @abstractmethod
    async def stop_nfc_reader(self) -> None:
        """Stop the NFC reader scanning process.

        This method should stop scanning and clean up resources.
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """Check if the NFC reader is currently running.

        Returns:
            True if the reader is actively scanning, False otherwise
        """
        pass

    @abstractmethod
    async def read_nfc(self) -> Optional[Dict[str, Any]]:
        """Read NFC tag data directly.

        This method provides a direct way to read tag data,
        separate from the event-driven tag_subject mechanism.

        Returns:
            Dictionary containing tag data if a tag is present, None otherwise
        """
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up hardware resources.

        This method should be called when the hardware is no longer needed
        to properly release resources.
        """
        pass
