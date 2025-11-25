# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Domain Events Module."""

from .nfc_events import (
    AssociationSessionCompletedEvent,
    AssociationSessionExpiredEvent,
    AssociationSessionStartedEvent,
    NfcDomainEvent,
    TagAssociatedEvent,
    TagDetectedEvent,
    TagDissociatedEvent,
    TagRemovedEvent,
)

__all__ = [
    "AssociationSessionCompletedEvent",
    "AssociationSessionExpiredEvent",
    "AssociationSessionStartedEvent",
    "NfcDomainEvent",
    "TagAssociatedEvent",
    "TagDetectedEvent",
    "TagDissociatedEvent",
    "TagRemovedEvent",
]
