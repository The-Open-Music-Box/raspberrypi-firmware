# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Domain Exceptions Module."""

from .nfc_exceptions import (
    NfcDomainError,
    TagIdentifierError,
    AssociationError,
    SessionError,
    HardwareError,
    DuplicateAssociationError,
    SessionTimeoutError,
    InvalidTagError,
    NfcHardwareUnavailableError,
)

__all__ = [
    "NfcDomainError",
    "TagIdentifierError",
    "AssociationError",
    "SessionError",
    "HardwareError",
    "DuplicateAssociationError",
    "SessionTimeoutError",
    "InvalidTagError",
    "NfcHardwareUnavailableError",
]