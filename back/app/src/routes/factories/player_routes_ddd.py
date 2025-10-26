# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Clean DDD Player Routes

Pure Domain-Driven Design implementation replacing PlayerRoutes.
Single Responsibility: Route registration and dependency coordination.
"""

from typing import Optional
from fastapi import FastAPI
from socketio import AsyncServer

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors
from app.src.application.services.unified_state_manager import UnifiedStateManager

# DDD Components
from app.src.api.endpoints.player_api_routes import PlayerAPIRoutes
from app.src.api.services.player_broadcasting_service import PlayerBroadcastingService
from app.src.api.services.player_operations_service import PlayerOperationsService

# Application Services
from app.src.application.services.player_application_service import PlayerApplicationService

logger = get_logger(__name__)


class PlayerRoutesDDD:
    """
    Clean DDD player routes implementation.

    Single Responsibility: Route registration and dependency coordination.

    Responsibilities:
    - Initialize DDD components with proper dependencies
    - Register API routes with FastAPI
    - Coordinate service dependencies
    - Manage player operations lifecycle

    Does NOT handle:
    - HTTP request processing (delegated to API routes)
    - Business logic (delegated to application services)
    - State broadcasting (delegated to broadcasting service)
    - Complex operations (delegated to operations service)
    """

    @handle_errors("player_routes_ddd_init", return_response=False)
    def __init__(self, app: FastAPI, socketio: AsyncServer, playback_coordinator, config=None):
        """Initialize clean DDD player routes.

        Args:
            app: FastAPI application instance
            socketio: Socket.IO server for real-time events
            playback_coordinator: PlaybackCoordinator for player operations
            config: Application configuration object
        """
        self.app = app
        self.socketio = socketio
        self.config = config
        self.playback_coordinator = playback_coordinator

        # Initialize core services
        self._initialize_core_services()

        # Initialize DDD components
        self._initialize_ddd_components()

        # Register routes
        self._register_routes()

        logger.info("✅ Clean DDD player routes initialized")

    def _initialize_core_services(self):
        """Initialize core services required by DDD components."""
        # Initialize state management system
        self.state_manager = UnifiedStateManager(self.socketio)

        logger.info("✅ Player core services initialized")

    def _initialize_ddd_components(self):
        """Initialize DDD components following clean architecture."""
        # Initialize application service with state manager for server_seq
        self.player_application_service = PlayerApplicationService(self.playback_coordinator, self.state_manager)

        # CRITICAL FIX: Inject player service into state manager for player state snapshots
        # This ensures clients receive current player state when joining playlists room
        self.state_manager.set_player_application_service(self.player_application_service)

        # Initialize broadcasting service
        self.broadcasting_service = PlayerBroadcastingService(self.state_manager)

        # Initialize operations service
        self.operations_service = PlayerOperationsService(self.player_application_service)

        # Initialize API routes with dependencies
        self.api_routes = PlayerAPIRoutes(
            player_service=self.player_application_service,
            broadcasting_service=self.broadcasting_service,
            operations_service=self.operations_service
        )

        logger.info("✅ Player DDD components initialized")

    def _register_routes(self):
        """Register all player routes with FastAPI."""
        # Register API routes
        self.app.include_router(self.api_routes.get_router())

        logger.info("✅ Player API routes registered")

    def get_player_application_service(self):
        """Get player application service instance.

        Returns:
            PlayerApplicationService instance
        """
        return self.player_application_service

    def get_broadcasting_service(self):
        """Get broadcasting service instance.

        Returns:
            PlayerBroadcastingService instance
        """
        return self.broadcasting_service

    def get_operations_service(self):
        """Get operations service instance.

        Returns:
            PlayerOperationsService instance
        """
        return self.operations_service

    def get_state_manager(self):
        """Get state manager instance.

        Returns:
            StateManager instance
        """
        return self.state_manager

    async def cleanup(self):
        """Clean up resources when shutting down."""
        try:
            logger.info("🧹 Cleaning up player routes resources")
            # Add any cleanup logic if needed
            logger.info("✅ Player routes cleanup completed")
        except Exception as e:
            logger.error(f"❌ Error during player routes cleanup: {str(e)}")