# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
Server-Authoritative API Routes Integration

This module provides the integration layer for the server-authoritative state
management system, replacing the original api_routes.py with state broadcasting.
"""

from fastapi import FastAPI

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors
from app.src.routes.factories.nfc_unified_routes import UnifiedNFCRoutes
from app.src.routes.factories.player_routes_ddd import PlayerRoutesDDD
from app.src.routes.factories.playlist_routes_ddd import PlaylistRoutesDDD
from app.src.routes.factories.system_routes import SystemRoutes
from app.src.routes.factories.upload_routes import UploadRoutes
from app.src.routes.factories.web_routes import WebRoutes
from app.src.routes.factories.youtube_routes import YouTubeRoutes

logger = get_logger(__name__)


class APIRoutesState:
    """
    Server-authoritative API routes organizer.

    This class replaces APIRoutes to integrate the server-authoritative
    state management system across all route handlers.
    """

    @handle_errors("api_routes_state_init", return_response=False)
    def __init__(self, app: FastAPI, socketio, config=None):
        """Initialize API routes with domain architecture.

        Args:
            app: FastAPI application instance
            socketio: Socket.IO server for real-time events
            config: Application configuration object
        """
        self.app = app
        self.socketio = socketio
        self.config = config

        # Initialize routes with server-authoritative state management
        self.web_routes = WebRoutes(app)

        # Initialize clean DDD playlist routes
        self.playlist_routes = PlaylistRoutesDDD(app, socketio, config)

        # Initialize DDD player routes
        from app.src.utils.playback_coordinator_utils import set_playback_coordinator_socketio
        from app.src.dependencies import get_playback_coordinator

        # CRITICAL FIX: Set Socket.IO instance on coordinator for NFC event broadcasting
        # This ensures NFC-triggered playlist starts broadcast state to the frontend
        set_playback_coordinator_socketio(socketio)

        playback_coordinator = get_playback_coordinator()
        self.player_routes = PlayerRoutesDDD(app, socketio, playback_coordinator, config)

        # CRITICAL FIX: Inject player service into playlist state manager for WebSocket snapshots
        # WebSocket handlers use playlist_routes.state_manager, so we must inject player service there
        # This fixes the issue where player state was not sent to clients on connection
        if hasattr(self.player_routes, 'player_application_service'):
            self.playlist_routes.state_manager.set_player_application_service(
                self.player_routes.player_application_service
            )
            logger.info("✅ Player service injected into playlist state_manager for WebSocket handlers")
        else:
            logger.warning("⚠️ Player service not available for injection into playlist state_manager")

        # Initialize domain-driven NFC routes
        self.nfc_routes = UnifiedNFCRoutes(app, socketio)
        # NFC state management is handled internally by UnifiedNFCRoutes
        logger.info("Domain-driven NFC routes initialized")
        self.youtube_routes = YouTubeRoutes(app, socketio)
        # NFC routes now unified - removed nfc_associate_routes
        self.upload_routes = UploadRoutes(app, socketio)
        self.system_routes = SystemRoutes(app)

    @handle_errors("api_routes_state_init")
    def init_routes(self):
        """Initialize all application routes with server-authoritative state management."""
        logger.debug("Starting route registration...")
        logger.info("🔧 Registering clean DDD playlist routes...")
        # Register server-authoritative playlist routes first
        self.playlist_routes.register()
        logger.debug("Playlist routes registered")
        logger.info("🔧 Player routes (DDD) already registered during initialization")
        logger.debug("Player routes registered")
        logger.info("🔧 Registering NFC routes...")
        # Register other routes
        if self.nfc_routes:
            self.nfc_routes.register_with_app()
        logger.debug("NFC routes registered")
        logger.info("🔧 Registering YouTube routes...")
        self.youtube_routes.register()
        logger.debug("YouTube routes registered")
        logger.info("🔧 Registering upload routes...")
        self.upload_routes.register_with_app()
        logger.debug("Upload routes registered")
        logger.info("🔧 Registering system routes...")
        self.system_routes.register()
        logger.debug("System routes registered")
        logger.info("🔧 Registering web routes...")
        self.web_routes.register()
        logger.debug("Web routes registered")
        logger.info("🔧 Starting background services...")
        # Start TrackProgressService after all routes are registered
        import asyncio

        logger.info("🚀 ATTEMPTING to start TrackProgressService...")
        loop = asyncio.get_running_loop()
        logger.info(f"📋 Event loop status: running={loop.is_running()}")
        if loop.is_running():
            # Service is already initialized in PlaylistRoutesDDD, just start it
            if hasattr(self.playlist_routes, "progress_service"):
                logger.info("✅ TrackProgressService found, starting...")
                # Get service reference first
                service = self.playlist_routes.progress_service
                loop.create_task(service.start())
                logger.info(f"🎵 TrackProgressService started successfully - should emit position events every {int(service.interval * 1000)}ms",
                )
                # Log service configuration
                logger.info(f"🔧 TrackProgressService config: interval={service.interval}s, running={service.is_running}",
                )
            else:
                logger.error("❌ TrackProgressService NOT FOUND in playlist_routes!")
            # Start StateManager cleanup task for periodic maintenance
            logger.info("🔧 Starting StateManager cleanup task...")
            loop.create_task(self.playlist_routes.state_manager.start_cleanup_task())
            logger.info("✅ StateManager cleanup task started successfully")
            logger.info("✅ All background services started successfully")
        else:
            logger.warning("Event loop not running, background services will start with app"
            )
        logger.debug("Route initialization completed")


def init_api_routes_state(app: FastAPI, socketio, config=None):
    """Entry point for server-authoritative API route initialization with domain architecture."""
    # CRITICAL FIX: Initialize and inject broadcasting service for Socket.IO events
    # This enables frontend communication for NFC association, state changes, etc.
    from app.src.services.broadcasting.unified_broadcasting_service import UnifiedBroadcastingService

    broadcasting_service = UnifiedBroadcastingService(socketio)
    app._broadcasting_service = broadcasting_service
    logger.info("✅ UnifiedBroadcastingService created and attached to FastAPI app")

    # Inject into Application instance if available
    if hasattr(app, 'application') and app.application:
        app.application._broadcasting_service = broadcasting_service
        logger.info("✅ Broadcasting service injected into Application instance")
    else:
        logger.warning("⚠️ Application instance not yet available, broadcasting service will be set later")

    routes_organizer = APIRoutesState(app, socketio, config)
    routes_organizer.init_routes()
    return routes_organizer
