# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
WebSocket Event Handlers

This module provides modular WebSocket event handlers following the Single
Responsibility Principle. Each handler class focuses on a specific domain:
- ConnectionHandlers: Client connection lifecycle
- SubscriptionHandlers: Room subscription management
- NFCHandlers: NFC association operations
- SyncHandlers: State synchronization and health monitoring
"""

from app.src.routes.handlers.connection_handlers import ConnectionHandlers
from app.src.routes.handlers.subscription_handlers import SubscriptionHandlers
from app.src.routes.handlers.nfc_handlers import NFCHandlers
from app.src.routes.handlers.sync_handlers import SyncHandlers

__all__ = [
    "ConnectionHandlers",
    "SubscriptionHandlers",
    "NFCHandlers",
    "SyncHandlers",
]
