# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Domain Module.

Contains all domain entities, value objects, services and interfaces
for NFC tag management according to Domain-Driven Design principles.
"""

from .entities.nfc_tag import NfcTag
from .entities.association_session import AssociationSession, SessionState
from .value_objects.tag_identifier import TagIdentifier
from .services.nfc_association_service import NfcAssociationService
from .services.nfc_event_publisher import NfcEventPublisher
from .protocols.nfc_hardware_protocol import NfcHardwareProtocol, NfcRepositoryProtocol
from .events import (
    NfcDomainEvent,
    TagDetectedEvent,
    TagAssociatedEvent,
    TagDissociatedEvent,
    TagRemovedEvent,
    AssociationSessionStartedEvent,
    AssociationSessionCompletedEvent,
    AssociationSessionExpiredEvent,
)
from .exceptions import (
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
    # Entities
    "NfcTag",
    "AssociationSession",
    "SessionState",
    # Value Objects
    "TagIdentifier",
    # Services
    "NfcAssociationService",
    "NfcEventPublisher",
    # Protocols
    "NfcHardwareProtocol",
    "NfcRepositoryProtocol",
    # Events
    "NfcDomainEvent",
    "TagDetectedEvent",
    "TagAssociatedEvent",
    "TagDissociatedEvent",
    "TagRemovedEvent",
    "AssociationSessionStartedEvent",
    "AssociationSessionCompletedEvent",
    "AssociationSessionExpiredEvent",
    # Exceptions
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
