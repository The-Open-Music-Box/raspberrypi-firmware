# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""
YouTube Routes Bootstrap

Bootstrap/factory class for YouTube integration routes.
Single Responsibility: Initialize and register YouTube API routes with dependencies.
"""

from fastapi import FastAPI
from socketio import AsyncServer

from app.src.monitoring import get_logger
from app.src.services.error.unified_error_decorator import handle_errors
from app.src.api.endpoints.youtube_api_routes import YouTubeAPIRoutes

logger = get_logger(__name__)


class YouTubeRoutes:
    """
    Bootstrap class for YouTube API routes.

    Responsibilities:
    - Initialize YouTubeAPIRoutes with dependencies
    - Register routes with FastAPI app
    - Provide YouTube service factory for dependency injection

    Does NOT handle:
    - HTTP request processing (delegated to YouTubeAPIRoutes)
    - Video downloading (delegated to YouTube service)
    - Search operations (delegated to YouTube service)
    """

    def __init__(self, app: FastAPI, socketio: AsyncServer):
        """Initialize YouTube routes bootstrap.

        Args:
            app: FastAPI application instance
            socketio: Socket.IO server for real-time events
        """
        self.app = app
        self.socketio = socketio
        self.api_routes = None

    @handle_errors("youtube_routes_init", return_response=False)
    def initialize(self):
        """Initialize YouTube API routes with dependency injection."""
        # Create YouTube service factory function
        def create_youtube_service(request):
            """Create YouTubeService instance with dependencies."""
            from app.src.application.services.youtube import YouTubeService

            # Get container from app state
            container = getattr(request.app, "container", None)
            config = container.get("config") if container else None

            return YouTubeService(self.socketio, config)

        # Initialize API routes
        self.api_routes = YouTubeAPIRoutes(
            youtube_service_factory=create_youtube_service
        )
        logger.info("✅ YouTube API routes initialized")

    def register(self):
        """Register YouTube routes with FastAPI app."""
        if not self.api_routes:
            self.initialize()

        # Register the router
        self.app.include_router(self.api_routes.get_router())
        logger.info("✅ YouTube routes registered successfully")
