# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Server-Authoritative WebSocket Handlers

This module implements WebSocket event handlers for the server-authoritative
state management system. Clients can subscribe to state updates and send
commands, but never maintain authoritative state.

This factory creates and registers handler instances following DDD principles:
- NFCHandlers: Handles NFC association operations
- SubscriptionHandlers: Handles room subscription management
- SyncHandlers: Handles state synchronization and health monitoring
"""

import socketio

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_http_errors
from app.src.domain.audio.engine.state_manager import StateManager
from app.src.dependencies import (
    get_nfc_application_service,
    get_playback_coordinator,
    get_player_state_service,
)
from app.src.routes.handlers.nfc_handlers import NFCHandlers
from app.src.routes.handlers.subscription_handlers import SubscriptionHandlers
from app.src.routes.handlers.sync_handlers import SyncHandlers

logger = get_logger(__name__)


class WebSocketStateHandlers:
    """WebSocket handlers factory for server-authoritative state management.

    This factory creates and registers handler instances following clean architecture:
    - Enforces dependency injection (no getattr runtime lookups)
    - Separates concerns into focused handler classes
    - Maintains single source of truth (state_manager)
    """

    def __init__(self, sio: socketio.AsyncServer, app, state_manager: StateManager):
        self.sio = sio
        self.app = app
        self.state_manager = state_manager

        # Set the Socket.IO server in state manager
        self.state_manager.socketio = sio

        # Handler instances will be initialized lazily when register() is called
        # This allows tests to set up mocks before handler initialization
        self.nfc_handlers = None
        self.subscription_handlers = None
        self.sync_handlers = None

        logger.info("WebSocketStateHandlers initialized with server-authoritative architecture")

    def _initialize_handlers(self):
        """Initialize handler instances with proper dependency injection.

        This method retrieves services from the DI container and injects them
        into handler constructors, eliminating runtime getattr() lookups.

        This is called lazily from register() to allow tests to mock dependencies.
        In test contexts where services aren't available, we gracefully handle
        missing dependencies (tests will need to mock handlers directly).
        """
        try:
            # Get services from DI container
            nfc_service = get_nfc_application_service()
            playback_coordinator = get_playback_coordinator()
            player_state_service = get_player_state_service()

            # Create handler instances with injected dependencies
            self.nfc_handlers = NFCHandlers(
                sio=self.sio,
                state_manager=self.state_manager,
                nfc_service=nfc_service,
            )

            self.subscription_handlers = SubscriptionHandlers(
                sio=self.sio,
                state_manager=self.state_manager,
                nfc_service=nfc_service,
            )

            self.sync_handlers = SyncHandlers(
                sio=self.sio,
                state_manager=self.state_manager,
                playback_coordinator=playback_coordinator,
                player_state_service=player_state_service,
            )

            logger.info("Handler instances initialized with dependency injection")
        except KeyError as e:
            # In test contexts, services might not be available
            # Tests should mock the handlers directly
            logger.warning(
                f"Could not initialize handlers from DI container: {e}. "
                "This is expected in test contexts. Handlers should be mocked."
            )
            # Set handlers to None so tests can mock them
            self.nfc_handlers = None
            self.subscription_handlers = None
            self.sync_handlers = None

    def register(self):
        """Register all server-authoritative WebSocket event handlers.

        This method:
        1. Initializes handler instances (lazily, to allow test mocking)
        2. Registers connection/disconnection lifecycle handlers
        3. Delegates to specialized handler classes for domain events
        """
        # Initialize handlers lazily (allows tests to mock dependencies)
        if self.nfc_handlers is None:
            self._initialize_handlers()

        # Register connection lifecycle handlers (managed by this factory)
        self._register_connection_handlers()

        # Delegate to specialized handler classes (if initialized)
        if self.nfc_handlers is not None:
            self.nfc_handlers.register()
            self.subscription_handlers.register()
            self.sync_handlers.register()
            logger.info("Server-authoritative WebSocket handlers registered successfully")
        else:
            logger.warning(
                "Handlers not initialized (test context). "
                "WebSocket events will not be registered."
            )

    def _register_connection_handlers(self):
        """Register connection lifecycle event handlers."""

        @self.sio.event
        @handle_http_errors()
        async def connect(sid, environ):
            """Handle client connection and initial state sync."""
            logger.info(f"Client connected: {sid}")

            # Send connection acknowledgment with proper error handling
            await self.sio.emit(
                "connection_status",
                {
                    "status": "connected",
                    "sid": sid,
                    "server_seq": self.state_manager.get_global_sequence(),
                },
                room=sid,
            )

        @self.sio.event
        async def disconnect(sid):
            """Handle client disconnection and cleanup subscriptions."""
            logger.info(f"Client disconnected: {sid}")

            # Unsubscribe client from all rooms
            await self.state_manager.unsubscribe_client(sid)
