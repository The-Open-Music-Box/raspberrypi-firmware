# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""NFC Domain Events Module."""

from .nfc_events import (
    NfcDomainEvent,
    TagDetectedEvent,
    TagAssociatedEvent,
    TagDissociatedEvent,
    AssociationSessionStartedEvent,
    AssociationSessionCompletedEvent,
    AssociationSessionExpiredEvent,
    TagRemovedEvent,
)

__all__ = [
    "NfcDomainEvent",
    "TagDetectedEvent",
    "TagAssociatedEvent",
    "TagDissociatedEvent",
    "AssociationSessionStartedEvent",
    "AssociationSessionCompletedEvent",
    "AssociationSessionExpiredEvent",
    "TagRemovedEvent",
]