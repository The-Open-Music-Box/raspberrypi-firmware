# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Domain Exceptions Module."""

from .nfc_exceptions import (
    AssociationError,
    DuplicateAssociationError,
    HardwareError,
    InvalidTagError,
    NfcDomainError,
    NfcHardwareUnavailableError,
    SessionError,
    SessionTimeoutError,
    TagIdentifierError,
)

__all__ = [
    "AssociationError",
    "DuplicateAssociationError",
    "HardwareError",
    "InvalidTagError",
    "NfcDomainError",
    "NfcHardwareUnavailableError",
    "SessionError",
    "SessionTimeoutError",
    "TagIdentifierError",
]
